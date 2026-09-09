"""Secure GitHub repository validation and archive download."""

from pathlib import Path
import re
from urllib.parse import quote, urlparse

import httpx

from app.core.config import Settings
from app.services.project_upload import InvalidProjectArchive, extract_project_zip

GITHUB_HOSTS = {"github.com", "www.github.com"}
REPOSITORY_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


class InvalidGitHubRepository(ValueError):
    """Raised when a repository URL or archive cannot be safely used."""


class GitHubAPIError(RuntimeError):
    """Raised when GitHub rejects or cannot fulfill an API request."""


def parse_repository_url(repository_url: str) -> tuple[str, str]:
    """Accept only canonical public GitHub repository URLs."""

    parsed = urlparse(repository_url.strip())
    if parsed.scheme != "https" or parsed.hostname not in GITHUB_HOSTS:
        raise InvalidGitHubRepository(
            "Repository URL must use HTTPS and point to github.com."
        )
    try:
        port = parsed.port
    except ValueError as exc:
        raise InvalidGitHubRepository("Repository URL contains an invalid port.") from exc
    if parsed.username or parsed.password or port or parsed.query or parsed.fragment:
        raise InvalidGitHubRepository("Repository URL contains unsupported components.")
    parts = [part for part in parsed.path.strip("/").split("/") if part]
    if len(parts) != 2:
        raise InvalidGitHubRepository("Repository URL must be /owner/repository.")
    owner, repository = parts
    if repository.endswith(".git"):
        repository = repository[:-4]
    if not owner or not repository or not all(
        REPOSITORY_PART.fullmatch(part) for part in (owner, repository)
    ):
        raise InvalidGitHubRepository("Repository URL contains an invalid name.")
    return owner, repository


def validate_ref(repository_ref: str) -> str:
    """Reject branch/ref values that could escape the archive URL."""

    ref = repository_ref.strip()
    if not ref or ref.startswith("/") or ".." in ref.split("/"):
        raise InvalidGitHubRepository("Repository ref is invalid.")
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", ref):
        raise InvalidGitHubRepository("Repository ref contains unsupported characters.")
    return ref


def download_repository(
    repository_url: str,
    destination: Path,
    settings: Settings,
    repository_ref: str = "main",
) -> tuple[str, str]:
    """Download a bounded GitHub ZIP archive into isolated project storage."""

    owner, repository = parse_repository_url(repository_url)
    ref = validate_ref(repository_ref)
    return _download_archive(
        owner,
        repository,
        ref,
        destination,
        settings,
        f"https://github.com/{owner}/{repository}/archive/refs/heads/"
        f"{quote(ref, safe='/')}.zip",
    )


def download_repository_at_ref(
    repository_url: str,
    repository_ref: str,
    destination: Path,
    settings: Settings,
) -> tuple[str, str]:
    """Download a repository snapshot by immutable branch, tag, or commit ref."""

    owner, repository = parse_repository_url(repository_url)
    ref = validate_ref(repository_ref)
    return _download_archive(
        owner,
        repository,
        ref,
        destination,
        settings,
        f"https://github.com/{owner}/{repository}/archive/"
        f"{quote(ref, safe='')}.zip",
    )


def _download_archive(
    owner: str,
    repository: str,
    ref: str,
    destination: Path,
    settings: Settings,
    archive_url: str,
) -> tuple[str, str]:
    """Download and safely extract one bounded archive."""

    headers = {"Accept": "application/vnd.github+json"}
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"

    try:
        with httpx.Client(
            timeout=settings.github_timeout_seconds,
            follow_redirects=True,
        ) as client:
            with client.stream("GET", archive_url, headers=headers) as response:
                if response.status_code >= 400:
                    raise InvalidGitHubRepository(
                        f"GitHub returned HTTP {response.status_code}."
                    )
                content_length = response.headers.get("content-length")
                if content_length:
                    try:
                        declared_length = int(content_length)
                    except ValueError as exc:
                        raise InvalidGitHubRepository(
                            "GitHub returned an invalid archive size."
                        ) from exc
                    if declared_length > settings.max_upload_size_bytes:
                        raise InvalidGitHubRepository(
                            "Repository archive exceeds the size limit."
                        )
                chunks: list[bytes] = []
                total = 0
                for chunk in response.iter_bytes():
                    total += len(chunk)
                    if total > settings.max_upload_size_bytes:
                        raise InvalidGitHubRepository(
                            "Repository archive exceeds the size limit."
                        )
                    chunks.append(chunk)
    except InvalidGitHubRepository:
        raise
    except httpx.TimeoutException as exc:
        raise InvalidGitHubRepository("GitHub download timed out.") from exc
    except httpx.RequestError as exc:
        raise InvalidGitHubRepository("GitHub repository could not be downloaded.") from exc

    try:
        extract_project_zip(b"".join(chunks), destination, settings)
    except InvalidProjectArchive as exc:
        raise InvalidGitHubRepository(
            "GitHub returned an invalid or unsafe repository archive."
        ) from exc
    return f"https://github.com/{owner}/{repository}", ref


def changed_pull_request_files(
    repository_url: str,
    pull_request_number: int,
    settings: Settings,
) -> list[dict[str, str]]:
    """Return changed PR files, capped to protect the worker."""

    owner, repository = parse_repository_url(repository_url)
    headers = _api_headers(settings)
    files: list[dict[str, str]] = []
    try:
        with httpx.Client(timeout=settings.github_timeout_seconds) as client:
            for page in range(1, 11):
                response = client.get(
                    f"{settings.github_api_url.rstrip('/')}/repos/{owner}/{repository}"
                    f"/pulls/{pull_request_number}/files",
                    headers=headers,
                    params={"per_page": 100, "page": page},
                )
                if response.status_code >= 400:
                    raise GitHubAPIError(
                        f"GitHub returned HTTP {response.status_code} while reading PR files."
                    )
                page_files = response.json()
                if not isinstance(page_files, list):
                    raise GitHubAPIError("GitHub returned an invalid PR file list.")
                files.extend(
                    {
                        "filename": str(item.get("filename", "")),
                        "status": str(item.get("status", "")),
                    }
                    for item in page_files
                    if isinstance(item, dict)
                )
                if len(page_files) < 100:
                    break
            else:
                raise GitHubAPIError("Pull request contains too many changed files.")
    except GitHubAPIError:
        raise
    except httpx.TimeoutException as exc:
        raise GitHubAPIError("GitHub PR file lookup timed out.") from exc
    except (httpx.RequestError, ValueError) as exc:
        raise GitHubAPIError("GitHub PR file list could not be read.") from exc
    return files


def post_pull_request_comment(
    repository_url: str,
    pull_request_number: int,
    body: str,
    settings: Settings,
) -> None:
    """Post one concise review comment to a pull request."""

    owner, repository = parse_repository_url(repository_url)
    try:
        with httpx.Client(timeout=settings.github_timeout_seconds) as client:
            response = client.post(
                f"{settings.github_api_url.rstrip('/')}/repos/{owner}/{repository}"
                f"/issues/{pull_request_number}/comments",
                headers=_api_headers(settings),
                json={"body": body[:65000]},
            )
            if response.status_code >= 400:
                raise GitHubAPIError(
                    f"GitHub returned HTTP {response.status_code} while posting PR review."
                )
    except GitHubAPIError:
        raise
    except httpx.TimeoutException as exc:
        raise GitHubAPIError("GitHub PR comment timed out.") from exc
    except httpx.RequestError as exc:
        raise GitHubAPIError("GitHub PR comment could not be posted.") from exc


def _api_headers(settings: Settings) -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers
