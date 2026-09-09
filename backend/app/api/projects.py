"""Project upload endpoints."""

from pathlib import Path
import shutil
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Project
from app.models import Scan, ScanStatus
from app.schemas import GitHubProjectCreate, GitHubProjectResponse, ProjectRead
from app.services.project_upload import (
    InvalidProjectArchive,
    extract_project_zip,
)
from app.services.preprocessing import (
    persist_preprocessing_result,
    preprocess_directory,
)
from app.services.ast_indexing import index_project
from app.services.graph import build_project_graph
from app.services.security_engine import run_static_analysis
from app.services.github import InvalidGitHubRepository, download_repository
from app.services.scan_tasks import run_scan

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post(
    "/upload",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_project(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> Project:
    """Validate, store, and register an uploaded project ZIP."""

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A ZIP file is required.",
        )

    archive_data = await file.read(settings.max_upload_size_bytes + 1)
    if len(archive_data) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Uploaded file exceeds the size limit.",
        )

    project_id = uuid4()
    storage_root = Path(settings.storage_dir).expanduser().resolve()
    project_directory = storage_root / str(project_id)
    project_name = Path(file.filename).stem.strip()[:255] or "Uploaded project"

    try:
        extract_project_zip(archive_data, project_directory, settings)
    except InvalidProjectArchive as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    project = Project(
        id=project_id,
        name=project_name,
        source_type="upload",
        storage_path=str(project_directory),
    )
    try:
        preprocessing_result = preprocess_directory(project_directory)
        persist_preprocessing_result(project, preprocessing_result, db)
        index_project(project, db)
        build_project_graph(project, db)
        run_static_analysis(project, db)
        db.add(project)
        db.commit()
        db.refresh(project)
    except (OSError, SQLAlchemyError) as exc:
        db.rollback()
        shutil.rmtree(project_directory, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Project could not be stored.",
        ) from exc

    return project


@router.post(
    "/github",
    response_model=GitHubProjectResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Import a GitHub repository",
)
def import_github_project(
    payload: GitHubProjectCreate,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> GitHubProjectResponse:
    """Download a validated GitHub repository and enqueue the normal scan."""

    project_id = uuid4()
    storage_root = Path(settings.storage_dir).expanduser().resolve()
    project_directory = storage_root / str(project_id)
    try:
        source_url, source_ref = download_repository(
            str(payload.repository_url),
            project_directory,
            settings,
            payload.repository_ref,
        )
    except InvalidGitHubRepository as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    repository_name = source_url.rstrip("/").rsplit("/", maxsplit=1)[-1]
    project = Project(
        id=project_id,
        name=repository_name,
        source_type="github",
        storage_path=str(project_directory),
        source_url=source_url,
        source_ref=source_ref,
    )
    scan = Scan(project_id=project_id, status=ScanStatus.PENDING)
    try:
        db.add_all([project, scan])
        db.commit()
        db.refresh(project)
        db.refresh(scan)
    except SQLAlchemyError as exc:
        db.rollback()
        shutil.rmtree(project_directory, ignore_errors=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="GitHub project could not be stored.",
        ) from exc
    try:
        run_scan.delay(str(scan.id))
    except Exception as exc:
        scan.status = ScanStatus.FAILED
        scan.error_message = "Unable to enqueue scan."
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scan queue is unavailable.",
        ) from exc
    return GitHubProjectResponse(project=project, scan=scan)
