"""HTTP API routes."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return service availability."""

    return {"status": "ok"}
