"""Shared schema fragments for MCP tool metadata."""

from __future__ import annotations


def _ann(
    *,
    read_only: bool = False,
    destructive: bool = False,
    idempotent: bool = False,
    open_world: bool = False,
) -> dict[str, bool]:
    return {
        "read_only_hint": read_only,
        "destructive_hint": destructive,
        "idempotent_hint": idempotent,
        "open_world_hint": open_world,
    }


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
    "_ann",
]
