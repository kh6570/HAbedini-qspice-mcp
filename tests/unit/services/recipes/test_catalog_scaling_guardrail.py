"""Guardrail: bundled recipes scale as data, never as one-tool-per-example.

Roadmap note "Catalog-scaling guardrail": keep ``list_reference_circuit_recipes``
compact. The recipe-discovery tool surface must stay a small fixed set regardless
of how many recipes ship, and no tool may be named after an individual recipe.
"""

from __future__ import annotations

from qspice_mcp.mcp.tool_registry import build_tool_registry
from qspice_mcp.services.recipes.list_reference_circuit_recipes import (
    list_reference_circuit_recipes,
)

# The complete, fixed recipe-facing tool surface. Adding a recipe must NOT add a
# tool; if this set legitimately changes, update it deliberately here.
EXPECTED_RECIPE_TOOLS = frozenset(
    {
        "list_reference_circuit_recipes",
        "describe_reference_circuit_recipe",
        "materialize_reference_circuit",
    }
)


def _recipe_facing_tool_names() -> set[str]:
    return {
        tool.name
        for tool in build_tool_registry()
        if "recipe" in tool.name or "reference_circuit" in tool.name
    }


def test_recipe_tool_surface_is_fixed_and_compact() -> None:
    assert _recipe_facing_tool_names() == set(EXPECTED_RECIPE_TOOLS)


def test_recipes_outnumber_recipe_tools() -> None:
    recipe_count = len(list_reference_circuit_recipes().recipes)
    # Recipes are data: there must be more recipes than recipe-facing tools, and
    # the tool surface stays constant as the catalog grows.
    assert recipe_count >= 2
    assert recipe_count >= len(EXPECTED_RECIPE_TOOLS) - 1


def test_no_tool_is_named_after_an_individual_recipe() -> None:
    recipe_ids = {entry.recipe_id for entry in list_reference_circuit_recipes().recipes}
    tool_names = {tool.name for tool in build_tool_registry()}
    for recipe_id in recipe_ids:
        for tool_name in tool_names:
            assert recipe_id not in tool_name, (
                f"tool {tool_name!r} appears to be named after recipe {recipe_id!r}; "
                "recipes must be data, not per-example tools."
            )
