"""Bundled reference-circuit recipe discovery tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.recipes.describe_reference_circuit_recipe import (
    describe_reference_circuit_recipe as describe_reference_circuit_recipe_service,
)
from qspice_mcp.services.recipes.list_reference_circuit_recipes import (
    list_reference_circuit_recipes as list_reference_circuit_recipes_service,
)

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsSettingsRuntime as _RuntimeWithSettings
else:
    _RuntimeWithSettings = object

RECIPES_HANDLER_NAMES = (
    "list_reference_circuit_recipes",
    "describe_reference_circuit_recipe",
)


class RecipesToolMixin:
    """Handlers for bundled reference-circuit recipe discovery."""

    def list_reference_circuit_recipes(self: _RuntimeWithSettings) -> dict[str, object]:
        result = list_reference_circuit_recipes_service()
        return to_json_object(result)

    def describe_reference_circuit_recipe(
        self: _RuntimeWithSettings,
        recipe_id: str,
    ) -> dict[str, object]:
        result = describe_reference_circuit_recipe_service(recipe_id)
        return to_json_object(result)


__all__ = ["RECIPES_HANDLER_NAMES", "RecipesToolMixin"]
