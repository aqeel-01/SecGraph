"""GitHub webhook endpoints."""

import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from redis.asyncio import Redis

from app.core.config import Settings, get_settings
from app.services.github import InvalidGitHubRepository, parse_repository_url
from app.services.scan_tasks import run_pull_request_scan

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/webhooks", tags=["github"])
SUPPORTED_ACTIONS = {"opened", "reopened", "synchronize"}


@router.post("/github", status_code=status.HTTP_202_ACCEPTED)
async def github_webhook(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_github_event: str | None = Header(default=None),
    x_hub_signature_256: str | None = Header(default=None),
    x_github_delivery: str | None = Header(default=None),
) -> dict[str, str]:
    """Validate and queue supported GitHub pull request events."""

    if not settings.github_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub webhook integration is not configured.",
        )
    body = await request.body()
    if not _valid_signature(body, x_hub_signature_256, settings.github_webhook_secret):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid GitHub webhook signature.",
        )
    if settings.environment == "production" and not x_github_delivery:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing GitHub delivery identifier.",
        )
    if x_github_delivery:
        try:
            redis = Redis.from_url(settings.redis_url)
            accepted = await redis.set(
                f"secgraph:webhook:{x_github_delivery[:256]}",
                "1",
                ex=86_400,
                nx=True,
            )
            await redis.aclose()
            if not accepted:
                return {"status": "duplicate"}
        except Exception as exc:
            if settings.environment == "production":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Webhook replay protection is unavailable.",
                ) from exc
    if x_github_event != "pull_request":
        return {"status": "ignored"}

    try:
        payload = json.loads(body)
        action = payload.get("action")
        pull_request = payload["pull_request"]
        repository = payload["repository"]
        if not isinstance(pull_request, dict) or not isinstance(repository, dict):
            raise ValueError("Invalid pull request payload objects.")
        number = int(payload["number"])
        head_sha = str(pull_request["head"]["sha"])
        repository_url = _canonical_repository_url(str(repository["html_url"]))
        head_repository = pull_request.get("head", {}).get("repo")
        if head_repository is not None and not isinstance(head_repository, dict):
            raise ValueError("Invalid pull request head repository.")
        head_repository_url = (
            _canonical_repository_url(str(head_repository["html_url"]))
            if head_repository and head_repository.get("html_url")
            else repository_url
        )
        if action not in SUPPORTED_ACTIONS or len(head_sha) != 40:
            return {"status": "ignored"}
        task_payload = {
            "repository_url": repository_url,
            "pull_request_number": number,
            "head_sha": head_sha,
            "head_repository_url": head_repository_url,
        }
    except (AttributeError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Malformed GitHub pull request webhook payload.",
        ) from exc

    try:
        run_pull_request_scan.delay(task_payload)
    except Exception as exc:
        logger.exception("Could not enqueue GitHub pull request scan")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pull request scan queue is unavailable.",
        ) from exc
    return {"status": "queued"}


def _valid_signature(
    body: bytes,
    signature: str | None,
    secret: str,
) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature.removeprefix("sha256="), expected)


def _canonical_repository_url(repository_url: str) -> str:
    try:
        owner, repository = parse_repository_url(repository_url)
    except InvalidGitHubRepository as exc:
        raise ValueError("Webhook repository URL is invalid.") from exc
    return f"https://github.com/{owner}/{repository}"
