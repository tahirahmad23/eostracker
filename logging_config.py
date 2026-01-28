"""
Central logging configuration (stdout/stderr only).

Goals:
- Single entry point: configure_logging()
- Environment-driven: LOG_LEVEL, LOG_FORMAT
- Works consistently in Docker/dev/prod (no env-specific branching)
- Structured output (JSON by default), to container stdout/stderr
"""

from __future__ import annotations

import json
import logging
import logging.config
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional


_CONFIGURED = False


class _MaxLevelFilter(logging.Filter):
    """Allow records up to and including max_level."""

    def __init__(self, max_level: int) -> None:
        super().__init__()
        self._max_level = max_level

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: A003 (filter name is stdlib)
        return record.levelno <= self._max_level


class _JsonFormatter(logging.Formatter):
    """
    Minimal JSON formatter.
    Avoids inspecting request bodies/headers or adding any PII automatically.
    """

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }

        # Helpful debugging context; safe and non-PII by default.
        payload["module"] = record.module
        payload["func"] = record.funcName
        payload["line"] = record.lineno

        # Include exception info if present (stacktrace as string).
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Include selected "extra" fields if present (e.g. middleware request metadata).
        for key in ("method", "path", "status_code", "duration_ms"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)

        return json.dumps(payload, ensure_ascii=False)


def _parse_level(value: Optional[str]) -> str:
    level = (value or "INFO").strip().upper()
    if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
        return level
    return "INFO"


def _parse_format(value: Optional[str]) -> str:
    fmt = (value or "json").strip().lower()
    if fmt in {"json", "text"}:
        return fmt
    return "json"


def configure_logging() -> None:
    """
    Configure logging for the entire process.

    Safe to call multiple times; subsequent calls are no-ops.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    log_level = _parse_level(os.getenv("LOG_LEVEL"))
    log_format = _parse_format(os.getenv("LOG_FORMAT"))

    formatter_name = "json" if log_format == "json" else "text"

    # Route ERROR+ to stderr, everything else to stdout.
    config: Dict[str, Any] = {
        "version": 1,
        # Keep existing third-party loggers alive; we standardize handlers/formatters.
        "disable_existing_loggers": False,
        "filters": {
            "max_info": {"()": _MaxLevelFilter, "max_level": logging.WARNING},
        },
        "formatters": {
            "json": {"()": _JsonFormatter},
            "text": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            },
        },
        "handlers": {
            "stdout": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": formatter_name,
                "filters": ["max_info"],
                "stream": "ext://sys.stdout",
            },
            "stderr": {
                "class": "logging.StreamHandler",
                "level": "ERROR",
                "formatter": formatter_name,
                "stream": "ext://sys.stderr",
            },
        },
        "root": {"level": log_level, "handlers": ["stdout", "stderr"]},
        # Ensure common server/framework loggers propagate to root for consistent formatting.
        "loggers": {
            "uvicorn": {"level": log_level, "handlers": [], "propagate": True},
            "uvicorn.error": {"level": log_level, "handlers": [], "propagate": True},
            "uvicorn.access": {"level": log_level, "handlers": [], "propagate": True},
            "apscheduler": {"level": log_level, "handlers": [], "propagate": True},
            "sqlalchemy": {"level": log_level, "handlers": [], "propagate": True},
        },
    }

    # Force our configuration to win even if something called basicConfig earlier.
    # Python's dictConfig doesn't have a "force" option, so we remove handlers first.
    root = logging.getLogger()
    for h in list(root.handlers):
        root.removeHandler(h)

    logging.config.dictConfig(config)

    # Use UTC timestamps for the stdlib time-based formatter (text mode).
    logging.Formatter.converter = time.gmtime

    _CONFIGURED = True


async def request_logging_middleware(request, call_next):
    """
    FastAPI/Starlette middleware (function style).
    Logs method/path/status/duration only (no headers, no querystring, no body).
    """
    logger = logging.getLogger("http")
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    except Exception:
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        # Log minimal request context; avoid query string and headers (may contain secrets).
        logger.exception(
            "Unhandled exception during request",
            extra={
                "method": request.method,
                "path": request.url.path,
                "duration_ms": duration_ms,
            },
        )
        raise
    finally:
        # If an exception happened, response won't exist; don't double-log.
        pass


async def request_access_log_middleware(request, call_next):
    """
    Separate middleware for successful responses so exceptions aren't double-logged.
    """
    logger = logging.getLogger("http")
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = round((time.perf_counter() - start) * 1000, 2)
    logger.info(
        "Request",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": getattr(response, "status_code", None),
            "duration_ms": duration_ms,
        },
    )
    return response

