import os
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

# Routes that don't require an API key
_PUBLIC = {"/", "/health", "/docs", "/redoc", "/openapi.json"}
_PUBLIC_PREFIXES = ("/static/",)


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.api_key = os.environ.get("API_KEY", "").strip()

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # Skip auth for public routes
        if path in _PUBLIC or any(path.startswith(p) for p in _PUBLIC_PREFIXES):
            return await call_next(request)

        # If no API_KEY is configured, allow all (dev mode)
        if not self.api_key:
            return await call_next(request)

        # Check header: X-API-Key or Authorization: Bearer <key>
        key = request.headers.get("X-API-Key") or _bearer(request)
        if key != self.api_key:
            return JSONResponse({"detail": "Invalid or missing API key"}, status_code=401)

        return await call_next(request)


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return None
