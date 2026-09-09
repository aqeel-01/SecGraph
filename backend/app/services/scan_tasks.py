"""Celery background execution for the complete scan pipeline."""

from datetime import datetime, timezone
import logging
from pathlib import Path
import shutil
from typing import Any
from uuid import UUID

from celery import Celery

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models import Project, Scan, ScanStatus, SecurityFinding
from app.services.ai.explanation import AIExplanationService
from app.services.ast_indexing import index_project
from app.services.graph import build_project_graph
from app.services.github import (
    GitHubAPIError,
    changed_pull_request_files,
    download_repository_at_ref,
    post_pull_request_comment,
)
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
    project_root: Path | None = None,
    commit_results: bool = True,
) -> dict[str, Any]:
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
    if commit_results:
        db.commit()
    else:
        db.flush()
    logger.info("Scan %s started", scan_id)

    try:
        project = db.get(Project, scan.project_id)
        if project is None:
            raise LookupError(f"Project for scan {scan_id} was not found.")

        scan_root = project_root or Path(project.storage_path)
        if not scan_root.is_dir():
            raise FileNotFoundError(
                f"Project storage directory does not exist: {scan_root}"
            )
        preprocessing_result = preprocess_directory(scan_root)
        changes = synchronize_project_files(
            project,
            preprocessing_result,
            db,
            force_all=not has_previous_scan,
        )
        should_process = not has_previous_scan or changes.has_changes
        findings = []
        if should_process:
            index_project(project, db, changes.affected_file_ids, scan_root)
            build_project_graph(project, db)
            run_static_analysis(
                project,
                db,
                file_ids=changes.affected_file_ids,
                scan_root=scan_root,
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
        if commit_results:
            db.commit()
        else:
            db.flush()
        logger.info("Scan %s completed with %d findings", scan_id, len(findings))
        return {
            "scan_id": str(scan_id),
            "status": ScanStatus.COMPLETED.value,
            "affected_file_ids": [str(file_id) for file_id in changes.affected_file_ids],
            "finding_count": len(findings),
        }
    except Exception as exc:
        db.rollback()
        failed_scan = db.get(Scan, scan_id)
        if failed_scan is not None:
            failed_scan.status = ScanStatus.FAILED
            failed_scan.completed_at = datetime.now(timezone.utc)
            failed_scan.error_message = "Scan failed. Check server logs for details."
            db.commit()
        logger.exception("Scan %s failed", scan_id)
        return {"scan_id": str(scan_id), "status": ScanStatus.FAILED.value}


def execute_pull_request_scan(
    scan_id: UUID,
    repository_url: str,
    pull_request_number: int,
    head_sha: str,
    db,
    head_repository_url: str | None = None,
) -> dict[str, Any]:
    """Analyze a PR snapshot, then restore the configured project checkout."""

    settings = get_settings()
    project = (
        db.query(Project)
        .filter(
            Project.source_type == "github",
            Project.source_url == repository_url.rstrip("/"),
        )
        .first()
    )
    if project is None:
        raise LookupError("No configured GitHub project matches this repository.")

    changed_files = changed_pull_request_files(
        repository_url,
        pull_request_number,
        settings,
    )
    backend_files = [
        item for item in changed_files
        if item["filename"].lower().endswith(".py")
    ]
    if not backend_files:
        scan = db.get(Scan, scan_id)
        if scan is not None:
            scan.status = ScanStatus.COMPLETED
            scan.completed_at = datetime.now(timezone.utc)
            db.commit()
        return {
            "scan_id": str(scan_id),
            "status": ScanStatus.COMPLETED.value,
            "skipped": True,
            "reason": "No Python backend files changed.",
        }

    temporary_root = (
        Path(settings.storage_dir).expanduser().resolve()
        / ".pull-requests"
        / str(scan_id)
    )
    savepoint = db.begin_nested()
    result: dict[str, Any] = {
        "scan_id": str(scan_id),
        "status": ScanStatus.FAILED.value,
    }
    try:
        download_repository_at_ref(
            head_repository_url or repository_url,
            head_sha,
            temporary_root,
            settings,
        )
        result = execute_scan(
            scan_id,
            db,
            project_root=temporary_root,
            commit_results=False,
        )
        affected_ids = {
            UUID(file_id)
            for file_id in result.get("affected_file_ids", [])
        }
        findings = (
            db.query(SecurityFinding)
            .filter(
                SecurityFinding.project_id == project.id,
                SecurityFinding.project_file_id.in_(affected_ids),
            )
            .order_by(SecurityFinding.severity.desc(), SecurityFinding.file)
            .all()
            if affected_ids
            else []
        )
        try:
            post_pull_request_comment(
                repository_url,
                pull_request_number,
                format_pull_request_comment(
                    pull_request_number,
                    head_sha,
                    findings,
                ),
                settings,
            )
        except GitHubAPIError:
            logger.exception(
                "Could not post security review for PR %s in %s",
                pull_request_number,
                repository_url,
            )
        return {
            **result,
            "pull_request_number": pull_request_number,
            "finding_count": len(findings),
        }
    finally:
        if savepoint.is_active:
            savepoint.rollback()
        db.expire_all()
        scan = db.get(Scan, scan_id)
        if scan is not None:
            scan.status = (
                ScanStatus.COMPLETED
                if result.get("status") == ScanStatus.COMPLETED.value
                else ScanStatus.FAILED
            )
            scan.completed_at = datetime.now(timezone.utc)
        db.commit()
        shutil.rmtree(temporary_root, ignore_errors=True)


def format_pull_request_comment(
    pull_request_number: int,
    head_sha: str,
    findings: list[SecurityFinding],
) -> str:
    """Create a concise, bounded PR summary from persisted findings."""

    lines = [
        f"## SecGraph security review",
        f"Analyzed PR `#{pull_request_number}` at `{head_sha[:12]}`.",
        "",
    ]
    if not findings:
        lines.append("✅ No security findings were detected in the affected backend code.")
        return "\n".join(lines)
    lines.append(f"⚠️ Found **{len(findings)}** security finding(s) in affected code:")
    for finding in findings[:20]:
        location = finding.file
        if finding.line:
            location += f":{finding.line}"
        lines.append(
            f"- **{_escape_markdown(finding.severity.upper())}** — "
            f"{_escape_markdown(finding.title)} (`{_escape_markdown(location)}`)"
        )
    if len(findings) > 20:
        lines.append(f"- …and {len(findings) - 20} more findings in the dashboard.")
    lines.extend(
        [
            "",
            "This review was generated by the existing SecGraph incremental scan.",
        ]
    )
    return "\n".join(lines)


def _escape_markdown(value: str) -> str:
    """Prevent analyzed repository text from changing comment formatting."""

    escaped = value.replace("\\", "\\\\")
    for character in ("`", "*", "_", "[", "]", "(", ")", "#", ">", "|"):
        escaped = escaped.replace(character, f"\\{character}")
    return escaped.replace("\r", " ").replace("\n", " ")


@celery_app.task(name="secgraph.run_scan")
def run_scan(scan_id: str) -> dict[str, Any]:
    """Celery entry point for a background scan."""

    with SessionLocal() as db:
        return execute_scan(UUID(scan_id), db)


@celery_app.task(name="secgraph.run_pull_request_scan")
def run_pull_request_scan(payload: dict[str, Any]) -> dict[str, Any]:
    """Celery entry point for a validated GitHub pull request event."""

    with SessionLocal() as db:
        scan = Scan(
            project_id=_project_id_for_repository(payload["repository_url"], db),
            status=ScanStatus.PENDING,
            trigger_type="pull_request",
            pull_request_number=payload["pull_request_number"],
            pull_request_sha=payload["head_sha"],
        )
        db.add(scan)
        db.commit()
        db.refresh(scan)
        try:
            return execute_pull_request_scan(
                scan.id,
                payload["repository_url"],
                payload["pull_request_number"],
                payload["head_sha"],
                db,
                payload.get("head_repository_url"),
            )
        except Exception as exc:
            scan.status = ScanStatus.FAILED
            scan.completed_at = datetime.now(timezone.utc)
            scan.error_message = "Pull request scan failed. Check server logs for details."
            db.commit()
            logger.exception("Pull request scan failed")
            return {
                "scan_id": str(scan.id),
                "status": ScanStatus.FAILED.value,
            }


def _project_id_for_repository(repository_url: str, db) -> UUID:
    project = (
        db.query(Project)
        .filter(
            Project.source_type == "github",
            Project.source_url == repository_url.rstrip("/"),
        )
        .first()
    )
    if project is None:
        raise LookupError("No configured GitHub project matches this repository.")
    return project.id
