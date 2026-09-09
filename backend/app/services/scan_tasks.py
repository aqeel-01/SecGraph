"""Celery background execution for the complete scan pipeline."""

from datetime import datetime, timezone
import logging
from pathlib import Path
from uuid import UUID

from celery import Celery

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Project, Scan, ScanStatus, SecurityFinding
from app.services.ai.explanation import AIExplanationService
from app.services.ast_indexing import index_project
from app.services.graph import build_project_graph
from app.services.incremental import synchronize_project_files
from app.services.preprocessing import (
    preprocess_directory,
)
from app.services.security_engine import run_static_analysis

logger = logging.getLogger(__name__)
settings = get_settings()
celery_app = Celery(
    "secgraph",
    broker=settings.redis_url,
    backend=settings.redis_url,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
)


def execute_scan(
    scan_id: UUID,
    db,
    explanation_service: AIExplanationService | None = None,
) -> dict[str, str]:
    """Execute a scan synchronously inside a worker-owned database session."""

    scan = db.get(Scan, scan_id)
    if scan is None:
        raise LookupError(f"Scan {scan_id} was not found.")

    has_previous_scan = db.query(Scan).filter(
        Scan.project_id == scan.project_id,
        Scan.id != scan.id,
    ).first() is not None
    scan.status = ScanStatus.RUNNING
    scan.started_at = datetime.now(timezone.utc)
    scan.error_message = None
    db.commit()
    logger.info("Scan %s started", scan_id)

    try:
        project = db.get(Project, scan.project_id)
        if project is None:
            raise LookupError(f"Project for scan {scan_id} was not found.")

        project_root = Path(project.storage_path)
        if not project_root.is_dir():
            raise FileNotFoundError(
                f"Project storage directory does not exist: {project_root}"
            )
        preprocessing_result = preprocess_directory(project_root)
        changes = synchronize_project_files(
            project,
            preprocessing_result,
            db,
            force_all=not has_previous_scan,
        )
        should_process = not has_previous_scan or changes.has_changes
        findings = []
        if should_process:
            index_project(project, db, changes.affected_file_ids)
            build_project_graph(project, db)
            run_static_analysis(
                project,
                db,
                file_ids=changes.affected_file_ids,
            )
            db.flush()

            explainer = explanation_service or AIExplanationService()
            findings = db.query(SecurityFinding).filter(
                SecurityFinding.project_id == project.id,
                SecurityFinding.project_file_id.in_(changes.affected_file_ids),
            ).all()
            for finding in findings:
                explainer.explain(finding, finding.context_package, db)
        else:
            logger.info("Scan %s found no changed files; reused existing index", scan_id)

        scan.status = ScanStatus.COMPLETED
        scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Scan %s completed with %d findings", scan_id, len(findings))
        return {"scan_id": str(scan_id), "status": ScanStatus.COMPLETED.value}
    except Exception as exc:
        db.rollback()
        failed_scan = db.get(Scan, scan_id)
        if failed_scan is not None:
            failed_scan.status = ScanStatus.FAILED
            failed_scan.completed_at = datetime.now(timezone.utc)
            failed_scan.error_message = str(exc)[:2000]
            db.commit()
        logger.exception("Scan %s failed", scan_id)
        return {"scan_id": str(scan_id), "status": ScanStatus.FAILED.value}


@celery_app.task(name="secgraph.run_scan")
def run_scan(scan_id: str) -> dict[str, str]:
    """Celery entry point for a background scan."""

    with SessionLocal() as db:
        return execute_scan(UUID(scan_id), db)
