import json
import logging
import sys
from datetime import UTC, datetime


class JSONFormatter(logging.Formatter):
    """
    Structured JSON log formatter for production logging.
    Transforms standard LogRecord structures into a flat JSON format.
    """
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
        }

        # Inject standard correlation tracking parameters
        for attr in ["request_id", "user_id", "execution_time_ms", "endpoint", "status_code"]:
            if hasattr(record, attr):
                log_data[attr] = getattr(record, attr)

        # Format exception stack traces
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)

def setup_logging(debug: bool = False) -> None:
    """
    Configures root logging handlers with JSONFormatter.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Flush existing handlers
    root_logger.handlers.clear()

    # Direct output to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Tune external framework logger verbosity
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
