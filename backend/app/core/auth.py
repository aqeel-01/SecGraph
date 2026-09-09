"""Minimal production API-key authentication."""

import secrets

from fastapi import Depends, Header, HTTPException, status

from app.core.config import Settings, get_settings


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    """Require one of the configured API keys outside local development."""

    configured_keys = {
        item.strip()
        for item in settings.api_keys.split(",")
        if item.strip()
    }
    if not settings.api_auth_enabled:
        return
    if settings.environment == "development" and not configured_keys:
        return
    if not configured_keys:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API authentication is not configured.",
        )
    if x_api_key is None or not any(
        secrets.compare_digest(x_api_key, configured)
        for configured in configured_keys
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key.",
            headers={"WWW-Authenticate": "ApiKey"},
        )
