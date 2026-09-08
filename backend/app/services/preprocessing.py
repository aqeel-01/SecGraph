"""Project source discovery and deterministic metadata extraction."""

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import os
import re
import tomllib
from typing import Protocol

from sqlalchemy.orm import Session

from app.models import Project, ProjectFile

IGNORED_DIRECTORIES = {
    ".git",
    "__pycache__",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
}


@dataclass(frozen=True)
class SourceFile:
    """A UTF-8 Python source file discovered in a project."""

    relative_path: str
    size_bytes: int
    sha256: str
    text: str


@dataclass(frozen=True)
class PreprocessingResult:
    """The deterministic results produced for an uploaded project."""

    files: list[SourceFile]
    python_version: str | None
    backend_framework: str | None


class FrameworkDetector(Protocol):
    """Interface for adding backend framework detectors."""

    name: str

    def detect(self, root: Path, files: list[SourceFile]) -> bool:
        """Return whether this framework is used by the project."""


class FastAPIDetector:
    """Detect FastAPI imports or dependency declarations."""

    name = "FastAPI"

    def detect(self, root: Path, files: list[SourceFile]) -> bool:
        if any(
            re.search(r"^\s*(?:from\s+fastapi|import\s+fastapi)\b", file.text, re.MULTILINE)
            for file in files
        ):
            return True

        for dependency_file in (
            "requirements.txt",
            "requirements-dev.txt",
            "pyproject.toml",
            "setup.py",
        ):
            path = root / dependency_file
            if path.is_file():
                try:
                    content = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                if re.search(r"\bfastapi\b", content, re.IGNORECASE):
                    return True
        return False


def discover_python_files(root: Path) -> list[SourceFile]:
    """Discover non-binary Python files under a project root."""

    discovered: list[SourceFile] = []
    for current_root, directories, filenames in os.walk(
        root,
        topdown=True,
        followlinks=False,
    ):
        directories[:] = [
            directory
            for directory in directories
            if directory.lower() not in IGNORED_DIRECTORIES
            and not (Path(current_root) / directory).is_symlink()
        ]
        for filename in filenames:
            path = Path(current_root) / filename
            if path.suffix.lower() != ".py" or path.is_symlink():
                continue
            content = path.read_bytes()
            if b"\x00" in content:
                continue
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                continue
            discovered.append(
                SourceFile(
                    relative_path=path.relative_to(root).as_posix(),
                    size_bytes=len(content),
                    sha256=sha256(content).hexdigest(),
                    text=text,
                )
            )
    return sorted(discovered, key=lambda file: file.relative_path)


def detect_python_version(root: Path) -> str | None:
    """Detect a declared Python version without executing project code."""

    for filename in (".python-version", "runtime.txt"):
        path = root / filename
        if path.is_file():
            try:
                value = path.read_text(encoding="utf-8").strip().splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            if value and value[0]:
                return value[0].removeprefix("python-")

    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
            data = {}
        project_requires = data.get("project", {}).get("requires-python")
        if isinstance(project_requires, str):
            return project_requires
        poetry_requires = (
            data.get("tool", {}).get("poetry", {}).get("dependencies", {}).get("python")
        )
        if isinstance(poetry_requires, str):
            return poetry_requires

    setup_py = root / "setup.py"
    if setup_py.is_file():
        try:
            content = setup_py.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            content = ""
        match = re.search(r"python_requires\s*=\s*['\"]([^'\"]+)", content)
        if match:
            return match.group(1)
    return None


def detect_backend_framework(
    root: Path,
    files: list[SourceFile],
    detectors: tuple[FrameworkDetector, ...] = (FastAPIDetector(),),
) -> str | None:
    """Return the first matching framework from the detector registry."""

    for detector in detectors:
        if detector.detect(root, files):
            return detector.name
    return None


def preprocess_directory(
    root: Path,
    detectors: tuple[FrameworkDetector, ...] = (FastAPIDetector(),),
) -> PreprocessingResult:
    """Scan one extracted project directory for deterministic metadata."""

    files = discover_python_files(root)
    return PreprocessingResult(
        files=files,
        python_version=detect_python_version(root),
        backend_framework=detect_backend_framework(root, files, detectors),
    )


def persist_preprocessing_result(
    project: Project,
    result: PreprocessingResult,
    db: Session,
) -> None:
    """Store preprocessing output on a project and its file records."""

    project.python_version = result.python_version
    project.backend_framework = result.backend_framework
    project.files.clear()
    project.files.extend(
        ProjectFile(
            relative_path=file.relative_path,
            size_bytes=file.size_bytes,
            sha256=file.sha256,
            language="python",
        )
        for file in result.files
    )
    db.add(project)
