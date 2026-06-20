"""Shared JSON-schema fragments for service MCP contracts."""

from __future__ import annotations

_SCALAR_VALUE = {"oneOf": [{"type": "string"}, {"type": "number"}]}
_STEP_FILTER_VALUE = {"oneOf": [{"type": "string"}, {"type": "number"}, {"type": "boolean"}]}
_STEP_FILTERS = {
    "type": "object",
    "propertyNames": {"type": "string"},
    "additionalProperties": _STEP_FILTER_VALUE,
}
_COMPONENT = {
    "type": "string",
    "enum": ["auto", "real", "imag", "magnitude", "phase"],
}
_RETAINED_ARTIFACT_POLICY = {
    "type": "string",
    "enum": ["cleanup", "keep_orphans", "keep_stale", "keep_all"],
}


__all__ = [
    "_COMPONENT",
    "_RETAINED_ARTIFACT_POLICY",
    "_SCALAR_VALUE",
    "_STEP_FILTERS",
    "_STEP_FILTER_VALUE",
]
