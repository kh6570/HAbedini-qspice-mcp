# Error Codes

This document defines the stable error codes that MCP clients can branch on.
The server publishes the same taxonomy through `describe_server_capabilities`
under `error_taxonomy`.

Reserved codes are published early so clients can prepare for them before the
first emitting tool lands. Until a more specific code is available,
`qspice_error` remains the default catch-all.

## Published Codes

| Code | Status | Meaning | Current mappings |
| --- | --- | --- | --- |
| `qspice_error` | implemented | Generic fallback for domain failures without a more specific stable code. | `QSpiceError` |
| `backend_unavailable` | implemented | A required local adapter, editor backend, raw backend, or companion executable is unavailable. | `AdapterNotFoundError`, `BackendUnavailableError` |
| `artifact_missing` | implemented | A requested or expected derived artifact was not created or could not be found. | `ArtifactMissingError` |
| `schematic_invalid` | reserved | The schematic structure is invalid or incomplete for the requested operation. | `SchematicInvalidError` |
| `batch_conflict` | reserved | A retained-batch or resume request conflicts with persisted batch state. | `BatchConflictError` |
| `timeout_exceeded` | implemented | A simulation or companion operation exceeded its configured timeout. | `SimulationTimeoutError` |
| `simulation_failed` | implemented | QSpice or a companion execution completed unsuccessfully. | `SimulationError` |
| `convergence_failed` | implemented | QSpice failed to converge on the requested analysis. | `ConvergenceError` |
| `parse_failed` | implemented | A netlist, waveform, or related derived artifact could not be parsed successfully. | `ParseError` |
| `budget_exceeded` | implemented | Configured waveform size limits could not be satisfied even after downsampling. | `BudgetExceededError` |
| `sandbox_violation` | implemented | A requested filesystem path escaped the configured workspace sandbox. | `SandboxViolationError` |
| `validation_failed` | implemented | Caller-supplied input failed a precondition such as a suffix, axis range, or required field check before the request reached an adapter or backend. | `ValidationError` |
| `unsupported_manifest_version` | implemented | A persisted batch manifest, prepared plan, or related saved artifact uses a schema_version this server does not support. | `UnsupportedManifestVersionError` |
| `configuration_invalid` | implemented | The server runtime configuration is missing a required value or contains a value that cannot be honored. | `ConfigurationError` |

## Notes

- Stable codes are intended for client control flow; messages may still evolve.
- MCP tool failures now surface the same stable code in `error.data.error_code` when a tool raises a `QSpiceError` subclass.
- Tool-specific payload fields can add more context, but they should not replace the stable `error_code`.
- The reserved codes above are part of the public contract even where the first emitting tool has not shipped yet.