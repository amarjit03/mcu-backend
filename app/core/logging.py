from __future__ import annotations

import contextvars
import logging
import sys
from typing import TYPE_CHECKING, Any

from loguru import logger as _logger

if TYPE_CHECKING:
    from loguru import Record

# Context variables to trace Request ID and authenticated User ID
request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
user_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("user_id", default=None)

# Intercept handler to redirect standard Python library logs (uvicorn, etc.) to Loguru
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        level: str | int
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame: Any = sys._getframe(6)
        depth = 6
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


class CustomLogger:
    """
    Wrapper for Loguru's logger class.
    Automatically binds keyword arguments as extra contextual metadata
    to support syntax like: logger.info("message", key=value).
    """
    def __init__(self, loguru_logger: Any):
        self._logger = loguru_logger

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.bind(**kwargs).debug(msg, *args)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.bind(**kwargs).info(msg, *args)

    def success(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.bind(**kwargs).success(msg, *args)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.bind(**kwargs).warning(msg, *args)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.bind(**kwargs).error(msg, *args)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.bind(**kwargs).critical(msg, *args)

    def bind(self, **kwargs: Any) -> CustomLogger:
        return CustomLogger(self._logger.bind(**kwargs))

    def opt(self, **kwargs: Any) -> Any:
        return self._logger.opt(**kwargs)


# Create the final logger instance
logger = CustomLogger(_logger)


def patch_record(record: Record) -> None:
    """
    Loguru patcher.
    Extracts Request ID and User ID from context variables and injects them
    into the log record's 'extra' metadata block.
    """
    req_id = request_id_var.get()
    u_id = user_id_var.get()
    record["extra"]["request_id"] = req_id if req_id else "-"
    record["extra"]["user_id"] = u_id if u_id else "-"


def console_formatter(record: Record) -> str:
    """
    Colorizes log levels for local console debugging.
    Injects context parameters in a clean structured format.
    """
    req_id = record["extra"].get("request_id", "-")
    req_part = f"req={req_id}" if req_id != "-" else "req=-"

    level_name = record["level"].name
    color_start = ""
    color_end = ""

    if level_name == "INFO":
        color_start = "<blue>"
        color_end = "</blue>"
    elif level_name == "SUCCESS":
        color_start = "<green>"
        color_end = "</green>"
    elif level_name == "WARNING":
        color_start = "<yellow>"
        color_end = "</yellow>"
    elif level_name == "ERROR":
        color_start = "<red>"
        color_end = "</red>"
    elif level_name == "CRITICAL":
        color_start = "<light-red><bold>"
        color_end = "</bold></light-red>"

    return (
        f"<green>{{time:YYYY-MM-DD HH:mm:ss}}</green> | "
        f"{color_start}{{level: <8}}{color_end} | "
        f"<cyan>{req_part}</cyan> | "
        f"<magenta>{{name}}</magenta> - {{message}}\n"
    )


def setup_logging(env: str = "dev", debug: bool = False) -> None:
    """
    Initializes Loguru handles, intercepts standard logs,
    and suppresses noisy third-party frameworks.
    """
    # 1. Clean default Loguru configurations
    _logger.remove()

    # 2. Add Patcher to automatically inject request correlation ids
    patched_logger = _logger.patch(patch_record)

    # 3. Console log handler (Colorized format in Dev, JSON serialization in Prod)
    log_level = "DEBUG" if debug else ("INFO" if env.lower() == "prod" else "DEBUG")

    if env.lower() == "prod":
        patched_logger.add(
            sys.stdout,
            level=log_level,
            serialize=True,  # Production logs formatted as JSON structures
        )
    else:
        patched_logger.add(
            sys.stdout,
            level=log_level,
            format=console_formatter,
        )

    # 4. Intercept standard loggers and pipe them to Loguru
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # 8. Suppress noisy library loggers (unless DEBUG=True)
    noisy_loggers = [
        "watchfiles",
        "watchfiles.main",
        "uvicorn.access",
        "urllib3",
        "asyncio",
        "httpx",
        "git",
    ]

    target_level = logging.WARNING if not debug else logging.INFO
    for logger_name in noisy_loggers:
        logging.getLogger(logger_name).setLevel(target_level)


__all__ = ["logger", "setup_logging", "request_id_var", "user_id_var"]
