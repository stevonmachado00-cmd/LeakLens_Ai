import time
import json
from fastapi import Request
from loguru import logger
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request as StarletteRequest
from typing import Callable

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable):
        start_time = time.time()

        # Read and preserve request body for downstream
        try:
            body_bytes = await request.body()
        except Exception:
            body_bytes = b""

        async def _receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        # Build a new request for call_next so downstream can read body
        downstream_request = StarletteRequest(request.scope, _receive)

        response = await call_next(downstream_request)
        process_time = time.time() - start_time

        # Attempt to read response body (may not be available for streaming responses)
        response_body = None
        try:
            # Many Response types expose .body or .render()
            if hasattr(response, "body") and response.body is not None:
                response_body = response.body
            else:
                # Try to render body
                rendered = await response.body()
                response_body = rendered
        except Exception:
            response_body = b"<unable to capture response body>"

        # Truncate long bodies for log safety
        def _short(b: bytes | str | None, limit: int = 2000):
            if b is None:
                return None
            s = b if isinstance(b, str) else (b.decode('utf-8', errors='replace') if isinstance(b, (bytes, bytearray)) else str(b))
            if len(s) > limit:
                return s[:limit] + '...<truncated>'
            return s

        request_body_str = None
        try:
            request_body_str = body_bytes.decode("utf-8") if body_bytes else None
        except Exception:
            request_body_str = str(body_bytes)

        logger.info(
            "HTTP {method} {path} -> {status} ({time:.3f}s)\nRequest body: {req}\nResponse body: {res}",
            method=request.method,
            path=str(request.url),
            status=getattr(response, 'status_code', '<no-status>'),
            time=process_time,
            req=_short(request_body_str),
            res=_short(response_body),
        )

        return response
