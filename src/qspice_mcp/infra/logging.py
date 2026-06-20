"""Structured logging helpers for qspice-mcp."""

from __future__ import annotations

import logging

import structlog

from qspice_mcp.infra.mcp_client_log import mcp_client_log_processor

Logger = structlog.stdlib.BoundLogger


def configure_logging(level: str = "info") -> None:
    """Configure stdlib and structlog logging once per process."""

    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=False),
            mcp_client_log_processor,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.dev.ConsoleRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(**context: object) -> Logger:
    """Return a bound logger for qspice-mcp."""

    logger: Logger = structlog.get_logger("qspice_mcp")
    if context:
        bound_logger: Logger = logger.bind(**context)
        return bound_logger
    return logger
