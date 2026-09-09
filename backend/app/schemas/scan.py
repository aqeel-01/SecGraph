"""Scan API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.scan import ScanStatus


class ScanCreate(BaseModel):
    """Fields required to create a scan record."""

    project_id: UUID
    status: ScanStatus


class ScanRead(ScanCreate):
    """Scan representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_message: str | None = None
