from hashlib import sha256
from pathlib import Path

from app.services.preprocessing import (
    FastAPIDetector,
    discover_python_files,
    detect_backend_framework,
    detect_python_version,
    preprocess_directory,
)


def test_preprocessing_discovers_hashes_and_ignores_unnecessary_files(
    tmp_path: Path,
) -> None:
    source = tmp_path / "app" / "main.py"
    source.parent.mkdir()
    source.write_text("print('hello')\n", encoding="utf-8")
    ignored = tmp_path / ".venv" / "ignored.py"
    ignored.parent.mkdir()
    ignored.write_text("print('ignored')", encoding="utf-8")
    binary = tmp_path / "binary.py"
    binary.write_bytes(b"\x00\x01\x02")
    (tmp_path / ".python-version").write_text("3.12\n", encoding="utf-8")

    files = discover_python_files(tmp_path)

    assert len(files) == 1
    assert files[0].relative_path == "app/main.py"
    assert files[0].size_bytes == source.stat().st_size
    assert files[0].sha256 == sha256(source.read_bytes()).hexdigest()
    assert detect_python_version(tmp_path) == "3.12"


def test_fastapi_framework_detector_is_replaceable(tmp_path: Path) -> None:
    source = tmp_path / "main.py"
    source.write_text("from fastapi import FastAPI\n", encoding="utf-8")

    result = preprocess_directory(tmp_path, detectors=(FastAPIDetector(),))

    assert result.backend_framework == "FastAPI"
    assert detect_backend_framework(tmp_path, result.files) == "FastAPI"
