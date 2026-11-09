"""
RoadPulse AI - Request Logging Middleware
Captures HTTP request telemetry, execution latency, and injects performance headers.
"""

import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("roadpulse.access")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        try:
            response = await call_next(request)
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            response.headers["X-Process-Time"] = f"{duration_ms:.2f}ms"

            # Suppress noisy health checks from log files
            if path != "/api/status" and not path.startswith("/dashboard"):
                logger.info(f"{method} {path} - {response.status_code} ({duration_ms:.1f}ms) [{client_ip}]")

            return response
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000.0
            logger.error(f"{method} {path} - FAILED ({duration_ms:.1f}ms) [{client_ip}]: {str(exc)}")
            raise exc
