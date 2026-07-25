"""Tests for domain exceptions."""

from __future__ import annotations

import re
from pathlib import Path

from qspice_mcp.core import error_taxonomy
from qspice_mcp.core.exceptions import (
    AdapterNotFoundError,
    ArtifactMissingError,
    BackendUnavailableError,
    BudgetExceededError,
    ConfigurationError,
    ConvergenceError,
    ParseError,
    QSpiceError,
    SandboxViolationError,
    SimulationError,
    SimulationTimeoutError,
    UnsupportedManifestVersionError,
    ValidationError,
)


def test_exception_hierarchy() -> None:
    assert issubclass(AdapterNotFoundError, QSpiceError)
    assert issubclass(ParseError, QSpiceError)
    assert issubclass(SimulationError, QSpiceError)
    assert issubclass(ConvergenceError, SimulationError)
    assert issubclass(SimulationTimeoutError, SimulationError)
    assert issubclass(ValidationError, QSpiceError)
    assert issubclass(ValidationError, ValueError)
    assert issubclass(UnsupportedManifestVersionError, ValidationError)
    assert issubclass(ConfigurationError, QSpiceError)


def test_simulation_error_stores_context() -> None:
    error = SimulationError("failed", exit_code=2, stderr="boom")
    assert error.exit_code == 2
    assert error.stderr == "boom"


def test_parse_error_stores_location() -> None:
    error = ParseError("invalid line", line=7, column=3)
    assert error.line == 7
    assert error.column == 3


def test_exceptions_expose_stable_error_codes() -> None:
    assert QSpiceError("failed").error_code == error_taxonomy.DEFAULT_ERROR_CODE
    assert AdapterNotFoundError("missing").error_code == "backend_unavailable"
    assert BackendUnavailableError("missing backend").error_code == "backend_unavailable"
    assert ArtifactMissingError("missing artifact").error_code == "artifact_missing"
    assert SimulationError("failed").error_code == "simulation_failed"
    assert ConvergenceError("failed").error_code == "convergence_failed"
    assert ParseError("bad raw").error_code == "parse_failed"
    assert SimulationTimeoutError("timeout").error_code == "timeout_exceeded"
    assert BudgetExceededError("budget").error_code == "budget_exceeded"
    assert SandboxViolationError("sandbox").error_code == "sandbox_violation"
    assert ValidationError("bad input").error_code == "validation_failed"
    assert (
        UnsupportedManifestVersionError("bad version").error_code == "unsupported_manifest_version"
    )
    assert ConfigurationError("bad config").error_code == "configuration_invalid"


def test_errors_document_matches_error_taxonomy() -> None:
    """docs/errors.md code rows must not drift from ERROR_CODE_DEFINITIONS."""
    repo_root = Path(__file__).resolve().parents[3]
    document = (repo_root / error_taxonomy.ERRORS_DOCUMENT_PATH).read_text(encoding="utf-8")
    row_pattern = re.compile(r"^\|\s*`(?P<code>[a-z_]+)`\s*\|\s*(?P<status>\w+)\s*\|", re.MULTILINE)
    documented = {
        match.group("code"): match.group("status") for match in row_pattern.finditer(document)
    }

    published = {
        definition.code: definition.status for definition in error_taxonomy.ERROR_CODE_DEFINITIONS
    }

    assert documented == published


def test_error_taxonomy_publishes_documented_codes() -> None:
    published_codes = {definition.code for definition in error_taxonomy.ERROR_CODE_DEFINITIONS}

    assert error_taxonomy.ERRORS_DOCUMENT_PATH == "docs/errors.md"
    assert {
        "backend_unavailable",
        "artifact_missing",
        "schematic_invalid",
        "batch_conflict",
        "timeout_exceeded",
        "validation_failed",
        "unsupported_manifest_version",
        "configuration_invalid",
    }.issubset(published_codes)
