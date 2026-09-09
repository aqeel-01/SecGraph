"""Redis-backed request limiting with a fail-closed production mode."""

import time

from fastapi import Request
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply a fixed-window limit per client IP."""

    def __init__(self, app, settings: Settings) -> None:
        super().__init__(app)
        self.settings = settings
        self.redis: Redis = Redis.from_url(settings.redis_url)

    async def dispatch(self, request: Request, call_next):
        if (
            not self.settings.rate_limit_enabled
            or self.settings.environment == "development"
            or request.url.path == "/health"
        ):
            return await call_next(request)
        client_ip = request.client.host if request.client else "unknown"
        window = int(time.time()) // self.settings.rate_limit_window_seconds
        key = f"secgraph:rate:{client_ip}:{window}"
        try:
            count = await self.redis.incr(key)
            if count == 1:
                await self.redis.expire(key, self.settings.rate_limit_window_seconds)
            if count > self.settings.rate_limit_requests:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded."},
                    headers={"Retry-After": str(self.settings.rate_limit_window_seconds)},
                )
        except Exception:
            if self.settings.environment == "production":
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Rate limiting service is unavailable."},
                )
        return await call_next(request)
