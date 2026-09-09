"""Hash-based incremental project synchronization."""

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from sqlalchemy.orm import Session

from app.models import Project, ProjectFile
from app.services.preprocessing import PreprocessingResult, SourceFile


@dataclass(frozen=True)
class IncrementalChanges:
    """Files whose indexed data may need to be refreshed."""

    added: tuple[str, ...]
    modified: tuple[str, ...]
    deleted: tuple[str, ...]
    unchanged: tuple[str, ...]
    affected_file_ids: frozenset[UUID]

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.modified or self.deleted)


def synchronize_project_files(
    project: Project,
    current: PreprocessingResult,
    db: Session,
    *,
    force_all: bool = False,
) -> IncrementalChanges:
    """Compare hashes and update only changed project-file metadata.

    Existing ``ProjectFile`` rows are retained for unchanged hashes, which
    allows their AST/index records to be reused.
    """

    existing = {
        project_file.relative_path: project_file
        for project_file in project.files
    }
    current_by_path = {
        source_file.relative_path: source_file
        for source_file in current.files
    }
    added: list[str] = []
    modified: list[str] = []
    unchanged: list[str] = []
    affected_ids: set[UUID] = set()
    changed_module_names = {
        Path(path).stem
        for path in set(existing) ^ set(current_by_path)
    }

    for path, source_file in current_by_path.items():
        previous = existing.get(path)
        if previous is None:
            project_file = _new_project_file(source_file)
            project.files.append(project_file)
            db.add(project_file)
            db.flush()
            added.append(path)
            affected_ids.add(project_file.id)
            changed_module_names.add(Path(path).stem)
        elif previous.sha256 != source_file.sha256 or force_all:
            previous.size_bytes = source_file.size_bytes
            previous.sha256 = source_file.sha256
            previous.language = "python"
            modified.append(path)
            affected_ids.add(previous.id)
            changed_module_names.add(Path(path).stem)
        else:
            unchanged.append(path)

    deleted: list[str] = []
    for path, project_file in existing.items():
        if path in current_by_path:
            continue
        deleted.append(path)
        affected_ids.add(project_file.id)
        project.files.remove(project_file)

    db.flush()

    # A file importing a changed module has dependent analysis that must be
    # refreshed even when its own content hash did not change.
    for project_file in project.files:
        if project_file.id in affected_ids:
            continue
        if any(
            (item.module or "").split(".")[-1] in changed_module_names
            for item in project_file.imports
        ):
            affected_ids.add(project_file.id)

    project.python_version = current.python_version
    project.backend_framework = current.backend_framework
    db.add(project)
    return IncrementalChanges(
        added=tuple(sorted(added)),
        modified=tuple(sorted(modified)),
        deleted=tuple(sorted(deleted)),
        unchanged=tuple(sorted(unchanged)),
        affected_file_ids=frozenset(affected_ids),
    )


def _new_project_file(source_file: SourceFile) -> ProjectFile:
    return ProjectFile(
        relative_path=source_file.relative_path,
        size_bytes=source_file.size_bytes,
        sha256=source_file.sha256,
        language="python",
    )
