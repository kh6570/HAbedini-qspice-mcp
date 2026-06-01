"""Domain models, error taxonomy, and shared contracts for qspice-mcp.

This subpackage holds the stable types that other layers (services, MCP
runtime, adapters, infra) and external consumers can rely on. Importing
from ``qspice_mcp.core`` is preferred over reaching into sibling modules
such as ``qspice_mcp.core.exceptions`` directly.
"""

from __future__ import annotations

from qspice_mcp.core.error_taxonomy import (
    DEFAULT_ERROR_CODE,
    ERROR_CODE_DEFINITIONS,
    ERRORS_DOCUMENT_PATH,
    ErrorCodeDefinition,
    ErrorCodeStatus,
    describe_error_taxonomy,
)
from qspice_mcp.core.exceptions import (
    AdapterNotFoundError,
    ArtifactMissingError,
    BackendUnavailableError,
    BatchConflictError,
    BudgetExceededError,
    ConfigurationError,
    ConvergenceError,
    ParseError,
    QSpiceError,
    SandboxViolationError,
    SchematicInvalidError,
    SimulationError,
    SimulationTimeoutError,
    ValidationError,
)

__all__ = [
    "DEFAULT_ERROR_CODE",
    "ERRORS_DOCUMENT_PATH",
    "ERROR_CODE_DEFINITIONS",
    "AdapterNotFoundError",
    "ArtifactMissingError",
    "BackendUnavailableError",
    "BatchConflictError",
    "BudgetExceededError",
    "ConfigurationError",
    "ConvergenceError",
    "ErrorCodeDefinition",
    "ErrorCodeStatus",
    "ParseError",
    "QSpiceError",
    "SandboxViolationError",
    "SchematicInvalidError",
    "SimulationError",
    "SimulationTimeoutError",
    "ValidationError",
    "describe_error_taxonomy",
]
