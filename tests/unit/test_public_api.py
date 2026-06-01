"""Pin the curated public API surface for the top-level package and core."""

from __future__ import annotations

import qspice_mcp
from qspice_mcp import core


def test_top_level_package_exposes_minimal_curated_surface() -> None:
    assert qspice_mcp.__version__
    assert qspice_mcp.QSpiceError is core.QSpiceError
    assert set(qspice_mcp.__all__) == {"QSpiceError", "__version__"}


def test_core_subpackage_reexports_full_error_taxonomy() -> None:
    expected = {
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
    }
    assert expected.issubset(set(core.__all__))
    for name in expected:
        assert hasattr(core, name), f"qspice_mcp.core is missing {name!r}"
