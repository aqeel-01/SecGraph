"""FastAPI application entry point."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.projects import router as project_router
from app.api.routes import router
from app.api.scans import router as scan_router
from app.core.config import get_settings
from app.core.logging import configure_logging

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
app.include_router(router)
app.include_router(project_router)
app.include_router(scan_router)
