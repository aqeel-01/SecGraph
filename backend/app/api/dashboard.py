"""REST endpoints consumed by the security dashboard."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Project, Scan, SecurityFinding
from app.schemas import (
    AIAnalysisRead,
    FindingRead,
    ProjectDetail,
    ProjectListItem,
    ScanSummary,
    SecuritySummary,
)

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get(
    "/projects",
    response_model=list[ProjectListItem],
    summary="List projects",
)
def list_projects(
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Project]:
    """Return projects ordered newest first."""

    return db.query(Project).order_by(
        Project.created_at.desc()
    ).offset(offset).limit(limit).all()


@router.get(
    "/projects/{project_id}",
    response_model=ProjectDetail,
    summary="Get project details",
)
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> ProjectDetail:
    """Return project metadata and dashboard counts."""

    project = _get_project(project_id, db)
    latest_scan = db.query(Scan).filter(
        Scan.project_id == project_id
    ).order_by(
        Scan.completed_at.desc().nullslast(),
        Scan.started_at.desc().nullslast(),
    ).first()
    base = ProjectListItem.model_validate(project).model_dump()
    return ProjectDetail(
        **base,
        file_count=len(project.files),
        scan_count=db.query(Scan).filter(Scan.project_id == project_id).count(),
        latest_scan=ScanSummary.model_validate(latest_scan)
        if latest_scan is not None
        else None,
    )


@router.get(
    "/projects/{project_id}/summary",
    response_model=SecuritySummary,
    summary="Get project security summary",
)
@router.get(
    "/projects/{project_id}/security-summary",
    response_model=SecuritySummary,
    summary="Get project security summary",
)
def get_project_summary(
    project_id: UUID,
    db: Session = Depends(get_db),
) -> SecuritySummary:
    """Return finding counts and a bounded overall security score."""

    _get_project(project_id, db)
    rows = db.query(
        SecurityFinding.severity,
        func.count(SecurityFinding.id),
    ).filter(
        SecurityFinding.project_id == project_id
    ).group_by(SecurityFinding.severity).all()
    counts = {str(severity).lower(): count for severity, count in rows}
    total = sum(counts.values())
    score = max(
        0.0,
        min(
            100.0,
            100.0
            - counts.get("critical", 0) * 25.0
            - counts.get("high", 0) * 15.0
            - counts.get("medium", 0) * 8.0
            - counts.get("low", 0) * 3.0,
        ),
    )
    return SecuritySummary(
        project_id=project_id,
        total_findings=total,
        critical_count=counts.get("critical", 0),
        high_count=counts.get("high", 0),
        medium_count=counts.get("medium", 0),
        low_count=counts.get("low", 0),
        overall_security_score=score,
    )


@router.get(
    "/projects/{project_id}/findings",
    response_model=list[FindingRead],
    summary="List project findings",
)
def list_findings(
    project_id: UUID,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    severity: str | None = Query(None),
    endpoint: str | None = Query(None),
    rule: str | None = Query(None),
    rule_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[FindingRead]:
    """List findings with optional severity, endpoint, and rule filters."""

    _get_project(project_id, db)
    query = db.query(SecurityFinding).filter(
        SecurityFinding.project_id == project_id
    )
    if severity:
        query = query.filter(func.lower(SecurityFinding.severity) == severity.lower())
    if endpoint:
        query = query.filter(SecurityFinding.endpoint == endpoint)
    selected_rule = rule or rule_id
    if selected_rule:
        query = query.filter(SecurityFinding.rule_id == selected_rule)
    findings = query.order_by(
        SecurityFinding.severity,
        SecurityFinding.file,
        SecurityFinding.line,
    ).offset(offset).limit(limit).all()
    return [_finding_response(finding) for finding in findings]


@router.get(
    "/findings",
    response_model=list[FindingRead],
    summary="List findings",
)
def list_all_findings(
    project_id: UUID | None = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    severity: str | None = Query(None),
    endpoint: str | None = Query(None),
    rule: str | None = Query(None),
    rule_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> list[FindingRead]:
    """List findings across projects or for one optional project."""

    if project_id is not None:
        _get_project(project_id, db)
    query = db.query(SecurityFinding)
    if project_id is not None:
        query = query.filter(SecurityFinding.project_id == project_id)
    if severity:
        query = query.filter(func.lower(SecurityFinding.severity) == severity.lower())
    if endpoint:
        query = query.filter(SecurityFinding.endpoint == endpoint)
    selected_rule = rule or rule_id
    if selected_rule:
        query = query.filter(SecurityFinding.rule_id == selected_rule)
    findings = query.order_by(
        SecurityFinding.severity,
        SecurityFinding.file,
        SecurityFinding.line,
    ).offset(offset).limit(limit).all()
    return [_finding_response(finding) for finding in findings]


@router.get(
    "/projects/{project_id}/findings/{finding_id}",
    response_model=FindingRead,
    summary="Get finding details",
)
def get_project_finding(
    project_id: UUID,
    finding_id: UUID,
    db: Session = Depends(get_db),
) -> FindingRead:
    """Return one finding belonging to a project."""

    finding = db.query(SecurityFinding).filter(
        SecurityFinding.id == finding_id,
        SecurityFinding.project_id == project_id,
    ).first()
    if finding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found.",
        )
    return _finding_response(finding)


@router.get(
    "/findings/{finding_id}",
    response_model=FindingRead,
    summary="Get finding details",
)
def get_finding(
    finding_id: UUID,
    db: Session = Depends(get_db),
) -> FindingRead:
    """Return one finding by ID."""

    finding = db.get(SecurityFinding, finding_id)
    if finding is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Finding not found.",
        )
    return _finding_response(finding)


def _get_project(project_id: UUID, db: Session) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found.",
        )
    return project


def _finding_response(finding: SecurityFinding) -> FindingRead:
    latest_analysis = max(
        finding.ai_analyses,
        key=lambda analysis: analysis.created_at,
        default=None,
    )
    return FindingRead(
        id=finding.id,
        project_id=finding.project_id,
        rule_id=finding.rule_id,
        title=finding.title,
        severity=finding.severity,
        confidence=finding.confidence,
        file=finding.file,
        line=finding.line,
        endpoint=finding.endpoint,
        description=finding.description,
        evidence=finding.evidence,
        remediation=finding.remediation,
        context_package=finding.context_package,
        ai_analysis=(
            AIAnalysisRead.model_validate(latest_analysis)
            if latest_analysis is not None
            else None
        ),
    )
