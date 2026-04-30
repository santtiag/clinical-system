"""
Structured logging configuration for microservices.
"""

import sys
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from contextvars import ContextVar
from pythonjsonlogger import jsonlogger

from common.config import settings


# Context variables for request tracing
trace_id_var: ContextVar[Optional[str]] = ContextVar("trace_id", default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)


class CustomJsonFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields."""

    def add_fields(self, log_record, record, message_dict):
        super().add_fields(log_record, record, message_dict)

        # Add timestamp
        log_record["timestamp"] = datetime.now(timezone.utc).isoformat()

        # Add service name
        log_record["service"] = settings.SERVICE_NAME

        # Add log level
        log_record["level"] = record.levelname

        # Add context from context vars
        trace_id = trace_id_var.get()
        if trace_id:
            log_record["trace_id"] = trace_id

        request_id = request_id_var.get()
        if request_id:
            log_record["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            log_record["user_id"] = user_id

        # Add logger name
        log_record["logger"] = record.name

        # Add location
        log_record["location"] = f"{record.filename}:{record.lineno}"


def setup_logging() -> None:
    """
    Configure structured JSON logging for the service.
    In production, logs go to stdout for container log collection.
    """
    # Get root logger
    root_logger = logging.getLogger()

    # Clear existing handlers
    root_logger.handlers.clear()

    # Set log level from settings
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # Create handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)

    # Use JSON formatter in production, text in development
    if settings.LOG_FORMAT == "json" or settings.ENVIRONMENT == "production":
        formatter = CustomJsonFormatter(
            "%(timestamp)s %(level)s %(name)s %(message)s"
        )
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_request(
    method: str,
    path: str,
    status_code: int,
    duration_ms: float,
    trace_id: Optional[str] = None
) -> None:
    """Log an HTTP request."""
    logger = get_logger("http")
    logger.info(
        "HTTP Request",
        extra={
            "method": method,
            "path": path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "type": "http_request"
        }
    )


def log_event(
    event_name: str,
    data: dict,
    level: str = "info"
) -> None:
    """
    Log a domain event.

    Args:
        event_name: Name of the event
        data: Event data dictionary
        level: Log level (info, warning, error)
    """
    logger = get_logger("domain_events")
    log_func = getattr(logger, level, logger.info)
    log_func(
        event_name,
        extra={
            **data,
            "type": "domain_event",
            "event_name": event_name
        }
    )