"""Safe project archive validation and extraction."""

from io import BytesIO
from pathlib import Path, PurePosixPath
import ntpath
import shutil
import stat
import zipfile

from app.core.config import Settings


class InvalidProjectArchive(ValueError):
    """Raised when an uploaded archive is invalid or unsafe."""


def _safe_member_path(name: str) -> Path:
    """Validate an archive member name and return a safe relative path."""

    if not name or "\x00" in name:
        raise InvalidProjectArchive("Archive contains an invalid path.")

    normalized = name.replace("\\", "/")
    drive, _ = ntpath.splitdrive(normalized)
    if drive or normalized.startswith("/") or normalized.startswith("//"):
        raise InvalidProjectArchive("Archive contains an absolute path.")

    path = PurePosixPath(normalized)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise InvalidProjectArchive("Archive contains an unsafe path.")

    return Path(*path.parts)


def extract_project_zip(
    archive_data: bytes,
    destination: Path,
    settings: Settings | None = None,
) -> None:
    """Validate and extract a ZIP archive without following unsafe paths."""

    if not zipfile.is_zipfile(BytesIO(archive_data)):
        raise InvalidProjectArchive("Uploaded file is not a valid ZIP archive.")

    destination.mkdir(parents=True, exist_ok=False)
    try:
        with zipfile.ZipFile(BytesIO(archive_data)) as archive:
            members: list[tuple[zipfile.ZipInfo, Path]] = []
            max_uncompressed = (
                settings.max_archive_uncompressed_bytes
                if settings is not None
                else 250 * 1024 * 1024
            )
            max_member = (
                settings.max_archive_member_bytes
                if settings is not None
                else 25 * 1024 * 1024
            )
            max_members = settings.max_archive_members if settings is not None else 10_000
            archive_members = archive.infolist()
            if len(archive_members) > max_members:
                raise InvalidProjectArchive("Archive contains too many files.")
            total_uncompressed = 0
            for info in archive_members:
                relative_path = _safe_member_path(info.filename)
                if info.file_size < 0 or info.file_size > max_member:
                    raise InvalidProjectArchive("Archive member exceeds the size limit.")
                total_uncompressed += info.file_size
                if total_uncompressed > max_uncompressed:
                    raise InvalidProjectArchive(
                        "Archive uncompressed size exceeds the limit."
                    )
                mode = (info.external_attr >> 16) & 0xFFFF
                if stat.S_ISLNK(mode):
                    raise InvalidProjectArchive(
                        "Archive contains an unsupported symbolic link."
                    )
                members.append((info, relative_path))

            root = destination.resolve()
            for info, relative_path in members:
                output_path = (destination / relative_path).resolve()
                if output_path != root and root not in output_path.parents:
                    raise InvalidProjectArchive("Archive extraction escaped storage.")

                if info.is_dir():
                    output_path.mkdir(parents=True, exist_ok=True)
                    continue

                output_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(info) as source, output_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
    except (zipfile.BadZipFile, OSError) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise InvalidProjectArchive("Unable to safely extract the ZIP archive.") from exc
    except InvalidProjectArchive:
        shutil.rmtree(destination, ignore_errors=True)
        raise
