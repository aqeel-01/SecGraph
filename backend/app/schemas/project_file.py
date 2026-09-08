"""Project file metadata schemas."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectFileRead(BaseModel):
    """Metadata for a processed Python source file."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    relative_path: str
    size_bytes: int
    sha256: str
    language: str
