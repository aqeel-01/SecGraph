"""Frontend dashboard response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.scan import ScanStatus


class ProjectListItem(BaseModel):
    """Public project fields used in project lists."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    source_type: str
    source_url: str | None = None
    source_ref: str | None = None
    backend_framework: str | None = None
    python_version: str | None = None
    created_at: datetime
    updated_at: datetime


class ScanSummary(BaseModel):
    """Compact scan history item."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: ScanStatus
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None


class ProjectDetail(ProjectListItem):
    """Project details with dashboard counts."""

    file_count: int
    scan_count: int
    latest_scan: ScanSummary | None = None


class AIAnalysisRead(BaseModel):
    """Validated or safely failed AI analysis information."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    decision: str
    status: str
    provider: str | None = None
    model: str | None = None
    ai_confidence: float | None = None
    response: str | None = None
    explanation_status: str | None = None
    structured_output: dict | None = None
    validation_error: str | None = None
    created_at: datetime


class FindingRead(BaseModel):
    """Finding details for dashboard display."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    rule_id: str
    title: str
    severity: str
    confidence: float
    file: str
    line: int | None
    endpoint: str | None
    description: str
    evidence: str
    remediation: str
    context_package: dict
    ai_analysis: AIAnalysisRead | None = None


class SecuritySummary(BaseModel):
    """Project-level security finding summary."""

    project_id: UUID
    total_findings: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    overall_security_score: float
