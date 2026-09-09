"""Background scan API endpoints."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project, Scan, ScanStatus
from app.schemas import ScanRead
from app.services.scan_tasks import run_scan

router = APIRouter(prefix="/api", tags=["scans"])


@router.post(
    "/projects/{project_id}/scan",
    response_model=ScanRead,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_scan(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> Scan:
    """Create and enqueue a scan without blocking on pipeline execution."""

    if db.get(Project, project_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )

    scan = Scan(project_id=project_id, status=ScanStatus.PENDING)
    db.add(scan)
    db.commit()
    db.refresh(scan)
    try:
        run_scan.delay(str(scan.id))
    except Exception as exc:
        scan.status = ScanStatus.FAILED
        scan.completed_at = datetime.now(timezone.utc)
        scan.error_message = "Unable to enqueue scan."
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scan queue is unavailable.",
        ) from exc
    return scan


@router.get("/scans/{scan_id}", response_model=ScanRead)
def get_scan(
    scan_id: UUID,
    db: Session = Depends(get_db),
) -> Scan:
    """Return the current state of a background scan."""

    scan = db.get(Scan, scan_id)
    if scan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scan not found.",
        )
    return scan
