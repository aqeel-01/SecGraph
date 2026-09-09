from pathlib import Path

import pytest
from fastapi import HTTPException

from app.core.auth import require_api_key
from app.core.config import Settings
from app.services.project_upload import InvalidProjectArchive, extract_project_zip


def test_production_api_key_is_required() -> None:
    settings = Settings(
        environment="production",
        api_auth_enabled=True,
        api_keys="expected-key",
    )
    with pytest.raises(HTTPException) as error:
        require_api_key("wrong-key", settings)
    assert error.value.status_code == 401
    require_api_key("expected-key", settings)


def test_archive_uncompressed_size_is_bounded(tmp_path: Path) -> None:
    import io
    import zipfile

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as zip_file:
        zip_file.writestr("large.py", "0123456789")

    settings = Settings(max_archive_uncompressed_bytes=5)
    with pytest.raises(InvalidProjectArchive, match="uncompressed"):
        extract_project_zip(archive.getvalue(), tmp_path / "project", settings)
