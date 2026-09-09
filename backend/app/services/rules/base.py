"""Common rule and finding contracts."""

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.models import Project


@dataclass(frozen=True)
class Finding:
    """Normalized output shared by every static security rule."""

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
    project_file_id: UUID | None = None
    route_id: UUID | None = None


@dataclass(frozen=True)
class RuleContext:
    """Read-only project data supplied to security rules."""

    project: Project
    sources: dict[UUID, str]
    file_ids: frozenset[UUID] | None = None

    def source_for(self, project_file_id: UUID) -> str:
        return self.sources.get(project_file_id, "")

    @property
    def files(self):
        """Return only files included in this rule evaluation."""

        if self.file_ids is None:
            return self.project.files
        return [
            project_file
            for project_file in self.project.files
            if project_file.id in self.file_ids
        ]


class SecurityRule(Protocol):
    """Interface implemented by every deterministic security rule."""

    rule_id: str

    def evaluate(self, context: RuleContext) -> list[Finding]:
        """Return normalized findings for the supplied project."""
