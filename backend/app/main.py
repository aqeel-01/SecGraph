"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.projects import router as project_router
from app.api.routes import router
from app.api.scans import router as scan_router
from app.api.dashboard import router as dashboard_router
from app.api.github import router as github_router
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.core.auth import require_api_key
from app.core.rate_limit import RateLimitMiddleware

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Manage application startup and shutdown hooks."""

    logger.info("Starting %s in %s environment", settings.app_name, settings.environment)
    yield
    logger.info("Shutting down %s", settings.app_name)


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(RateLimitMiddleware, settings=settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.cors_origins.split(",")
        if origin.strip()
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(project_router, dependencies=[Depends(require_api_key)])
app.include_router(scan_router, dependencies=[Depends(require_api_key)])
app.include_router(dashboard_router, dependencies=[Depends(require_api_key)])
app.include_router(github_router)
