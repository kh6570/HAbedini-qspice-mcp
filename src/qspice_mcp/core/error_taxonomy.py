"""Published stable error-code taxonomy for MCP clients."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DEFAULT_ERROR_CODE = "qspice_error"
ERRORS_DOCUMENT_PATH = "docs/errors.md"

ErrorCodeStatus = Literal["implemented", "reserved"]


@dataclass(frozen=True, slots=True)
class ErrorCodeDefinition:
    """One published error code and its current implementation status."""

    code: str
    title: str
    summary: str
    status: ErrorCodeStatus
    mapped_exceptions: tuple[str, ...] = ()

    def summary_dict(self) -> dict[str, object]:
        """Return a JSON-serializable summary for capability reporting."""

        return {
            "code": self.code,
            "title": self.title,
            "summary": self.summary,
            "status": self.status,
            "mapped_exceptions": list(self.mapped_exceptions),
        }


ERROR_CODE_DEFINITIONS: tuple[ErrorCodeDefinition, ...] = (
    ErrorCodeDefinition(
        code=DEFAULT_ERROR_CODE,
        title="Generic QSpice Error",
        summary=(
            "Fallback code for domain failures that do not yet expose a more specific stable code."
        ),
        status="implemented",
        mapped_exceptions=("QSpiceError",),
    ),
    ErrorCodeDefinition(
        code="backend_unavailable",
        title="Backend Unavailable",
        summary=(
            "A required local adapter, editor backend, raw backend, or "
            "companion executable is unavailable."
        ),
        status="implemented",
        mapped_exceptions=("AdapterNotFoundError", "BackendUnavailableError"),
    ),
    ErrorCodeDefinition(
        code="artifact_missing",
        title="Artifact Missing",
        summary="A requested or expected derived artifact was not created or could not be found.",
        status="implemented",
        mapped_exceptions=("ArtifactMissingError",),
    ),
    ErrorCodeDefinition(
        code="schematic_invalid",
        title="Schematic Invalid",
        summary="The schematic structure is invalid or incomplete for the requested operation.",
        status="reserved",
        mapped_exceptions=("SchematicInvalidError",),
    ),
    ErrorCodeDefinition(
        code="batch_conflict",
        title="Batch Conflict",
        summary=(
            "The requested retained-batch or resume operation conflicts with "
            "existing persisted batch state."
        ),
        status="reserved",
        mapped_exceptions=("BatchConflictError",),
    ),
    ErrorCodeDefinition(
        code="timeout_exceeded",
        title="Timeout Exceeded",
        summary="The requested simulation or companion operation exceeded its configured timeout.",
        status="implemented",
        mapped_exceptions=("SimulationTimeoutError",),
    ),
    ErrorCodeDefinition(
        code="simulation_failed",
        title="Simulation Failed",
        summary="QSpice or a companion execution completed unsuccessfully.",
        status="implemented",
        mapped_exceptions=("SimulationError",),
    ),
    ErrorCodeDefinition(
        code="convergence_failed",
        title="Convergence Failed",
        summary="QSpice failed to converge on the requested analysis.",
        status="implemented",
        mapped_exceptions=("ConvergenceError",),
    ),
    ErrorCodeDefinition(
        code="parse_failed",
        title="Parse Failed",
        summary=(
            "A netlist, waveform, or related derived artifact could not be parsed successfully."
        ),
        status="implemented",
        mapped_exceptions=("ParseError",),
    ),
    ErrorCodeDefinition(
        code="budget_exceeded",
        title="Budget Exceeded",
        summary="Configured waveform size limits could not be satisfied even after downsampling.",
        status="implemented",
        mapped_exceptions=("BudgetExceededError",),
    ),
    ErrorCodeDefinition(
        code="sandbox_violation",
        title="Sandbox Violation",
        summary="A requested filesystem path escaped the configured workspace sandbox.",
        status="implemented",
        mapped_exceptions=("SandboxViolationError",),
    ),
    ErrorCodeDefinition(
        code="validation_failed",
        title="Validation Failed",
        summary=(
            "Caller-supplied input failed a precondition such as a suffix, "
            "axis range, or required field check before the request reached "
            "an adapter or backend."
        ),
        status="implemented",
        mapped_exceptions=("ValidationError",),
    ),
    ErrorCodeDefinition(
        code="unsupported_manifest_version",
        title="Unsupported Manifest Version",
        summary=(
            "A persisted batch manifest, prepared plan, or related saved artifact "
            "uses a schema_version this server does not support."
        ),
        status="implemented",
        mapped_exceptions=("UnsupportedManifestVersionError",),
    ),
    ErrorCodeDefinition(
        code="configuration_invalid",
        title="Configuration Invalid",
        summary=(
            "The server runtime configuration is missing a required value or "
            "contains a value that cannot be honored."
        ),
        status="reserved",
        mapped_exceptions=("ConfigurationError",),
    ),
)


def describe_error_taxonomy() -> dict[str, object]:
    """Return the published error taxonomy in a JSON-serializable form."""

    return {
        "document_path": ERRORS_DOCUMENT_PATH,
        "default_code": DEFAULT_ERROR_CODE,
        "codes": [definition.summary_dict() for definition in ERROR_CODE_DEFINITIONS],
    }


__all__ = [
    "DEFAULT_ERROR_CODE",
    "ERRORS_DOCUMENT_PATH",
    "ERROR_CODE_DEFINITIONS",
    "ErrorCodeDefinition",
    "ErrorCodeStatus",
    "describe_error_taxonomy",
]
