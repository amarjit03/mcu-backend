import time
import traceback
import uuid
from typing import Any

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import logger, request_id_var, user_id_var


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    ASGI middleware class for Request ID tracing, structured request execution logging,
    and unhandled exceptions stack trace reporting.
    """
    async def dispatch(self, request: Request, call_next: Any) -> Response:
        # 1. Fetch or generate a unique tracking Request ID
        req_id = request.headers.get("X-Request-ID")
        if not req_id:
            req_id = uuid.uuid4().hex[:7]

        # 2. Store Request ID in thread-local ContextVar
        token_req = request_id_var.set(req_id)
        token_user = user_id_var.set(None)

        client_ip = request.client.host if request.client else "127.0.0.1"
        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            process_time_ms = int((time.perf_counter() - start_time) * 1000)

            # Log standard HTTP request details
            logger.info(
                f"{request.method} {request.url.path} {response.status_code} ({process_time_ms}ms)",
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                execution_time=f"{process_time_ms}ms",
                client_ip=client_ip,
            )

            # Return tracking ID back to the client in response headers
            response.headers["X-Request-ID"] = req_id
            return response  # type: ignore[no-any-return]

        except Exception as exc:
            process_time_ms = int((time.perf_counter() - start_time) * 1000)
            user_id = user_id_var.get()
            tb = traceback.format_exc()

            # Log unhandled exception details
            logger.critical(
                f"Unhandled Exception: {exc.__class__.__name__}\n"
                f"Endpoint: {request.url.path}\n"
                f"User: {user_id if user_id else 'Anonymous'}\n"
                f"Request: {req_id}\n"
                f"Traceback:\n{tb}",
                method=request.method,
                endpoint=request.url.path,
                execution_time=f"{process_time_ms}ms",
                client_ip=client_ip,
                exception=exc.__class__.__name__,
            )

            # Return uniform 500 error response to hide internal details
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal Server Error"},
                headers={"X-Request-ID": req_id},
            )

        finally:
            # Reset ContextVars for cleanup
            request_id_var.reset(token_req)
            user_id_var.reset(token_user)
