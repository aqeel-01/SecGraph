"""GitHub repository API schemas."""

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.scan import ScanRead
from app.schemas.project import ProjectRead


class GitHubProjectCreate(BaseModel):
    """Repository selected for a security scan."""

    repository_url: HttpUrl
    repository_ref: str = Field(default="main", min_length=1, max_length=255)


class GitHubProjectResponse(BaseModel):
    """Created project and its queued background scan."""

    project: ProjectRead
    scan: ScanRead
