"""
RoadPulse AI - Rate Limiting & Abuse Prevention Middleware
Implements in-memory sliding-window rate limiting for authentication endpoints
to defend against brute force credential stuffing and DoS attempts.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette import status

from ..core.config import settings


class AuthRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        # Tracks timestamp list per client IP: {client_ip: [timestamp1, timestamp2, ...]}
        self.request_history: Dict[str, List[float]] = defaultdict(list)
        self.protected_paths = {
            f"{settings.API_V1_STR}/auth/login",
            f"{settings.API_V1_STR}/auth/register",
        }

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if request.method == "POST" and path in self.protected_paths:
            client_ip = request.client.host if request.client else "127.0.0.1"
            now = time.time()
            window_start = now - settings.AUTH_RATE_LIMIT_WINDOW_SECONDS

            # Filter old requests outside sliding window
            timestamps = [t for t in self.request_history[client_ip] if t > window_start]
            self.request_history[client_ip] = timestamps

            if len(timestamps) >= settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS:
                retry_after = int(settings.AUTH_RATE_LIMIT_WINDOW_SECONDS - (now - timestamps[0]))
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "success": False,
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": f"Too many authentication attempts. Please try again in {retry_after} seconds.",
                            "retry_after_seconds": max(1, retry_after),
                        }
                    },
                    headers={"Retry-After": str(max(1, retry_after))},
                )

            # Record this attempt
            self.request_history[client_ip].append(now)

        return await call_next(request)
