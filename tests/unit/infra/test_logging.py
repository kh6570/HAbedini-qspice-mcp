"""Tests for logging configuration and the optional file handler."""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from qspice_mcp.infra.logging import configure_logging, get_logger


def _rotating_file_handlers() -> list[RotatingFileHandler]:
    return [
        handler
        for handler in logging.getLogger().handlers
        if isinstance(handler, RotatingFileHandler)
    ]


def _remove_handlers(handlers: list[RotatingFileHandler]) -> None:
    root = logging.getLogger()
    for handler in handlers:
        root.removeHandler(handler)
        handler.close()


def test_configure_logging_attaches_rotating_file_handler(tmp_path: Path) -> None:
    log_folder = tmp_path / "logs"
    added: list[RotatingFileHandler] = []
    try:
        configure_logging("debug", log_folder=log_folder)
        added = _rotating_file_handlers()

        assert log_folder.is_dir()
        assert any(
            Path(handler.baseFilename).parent == log_folder.resolve(strict=False)
            for handler in added
        )
    finally:
        _remove_handlers(added)


def test_configure_logging_does_not_duplicate_file_handler(tmp_path: Path) -> None:
    log_folder = tmp_path / "logs"
    added: list[RotatingFileHandler] = []
    try:
        configure_logging("info", log_folder=log_folder)
        configure_logging("info", log_folder=log_folder)
        added = [
            handler
            for handler in _rotating_file_handlers()
            if Path(handler.baseFilename).parent == log_folder.resolve(strict=False)
        ]

        assert len(added) == 1
    finally:
        _remove_handlers(added)


def test_get_logger_binds_context() -> None:
    logger = get_logger(component="test")

    assert logger is not None
