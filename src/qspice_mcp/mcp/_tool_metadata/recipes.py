"""Bundled reference-circuit recipe tool metadata."""

from __future__ import annotations

from .common import _ann

RECIPES_TOOL_METADATA: dict[str, dict[str, object]] = {
    "list_reference_circuit_recipes": {
        "title": "List Reference Circuit Recipes",
        "description": (
            "List bundled reference-circuit recipe ids, titles, and short summaries "
            "from package data (Track B discovery)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
    "describe_reference_circuit_recipe": {
        "title": "Describe Reference Circuit Recipe",
        "description": (
            "Return one bundled recipe manifest, workflow entries, bundled file list, "
            "and a lightweight topology digest from the bundled schematic."
        ),
        "input_schema": {
            "type": "object",
            "required": ["recipe_id"],
            "properties": {
                "recipe_id": {"type": "string"},
            },
        },
        "annotations": _ann(read_only=True, idempotent=True),
    },
}

__all__ = ["RECIPES_TOOL_METADATA"]
