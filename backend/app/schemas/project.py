"""Project API schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ProjectCreate(BaseModel):
    """Fields required to create a project."""

    name: str = Field(min_length=1, max_length=255)
    source_type: str = Field(min_length=1, max_length=50)


class ProjectRead(ProjectCreate):
    """Project representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    storage_path: str
    created_at: datetime
    updated_at: datetime
