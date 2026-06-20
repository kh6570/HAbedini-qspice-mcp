"""Service listing bundled reference-circuit recipes."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.services.recipes._catalog import (
    list_recipe_index_entries,
    load_recipe_manifest,
)
from qspice_mcp.services.recipes._catalog_guidance import RECIPE_CATALOG_DISCOVERY_GUIDANCE
from qspice_mcp.services.service_spec import ServiceSpec

SERVICE_SPEC = ServiceSpec(
    name="list_reference_circuit_recipes",
    title="List Reference Circuit Recipes",
    summary="List bundled reference-circuit recipe ids and short summaries.",
    phase="implemented",
    read_only=True,
)


@dataclass(frozen=True, slots=True)
class ReferenceCircuitRecipeSummary:
    """One bundled reference-circuit recipe row."""

    recipe_id: str
    title: str
    summary: str | None


@dataclass(frozen=True, slots=True)
class ReferenceCircuitRecipeList:
    """Catalog of bundled reference-circuit recipes."""

    discovery_guidance: str
    recipes: tuple[ReferenceCircuitRecipeSummary, ...]


def list_reference_circuit_recipes() -> ReferenceCircuitRecipeList:
    """Return every bundled reference-circuit recipe."""

    recipes: list[ReferenceCircuitRecipeSummary] = []
    for index_entry in list_recipe_index_entries():
        manifest = load_recipe_manifest(index_entry.recipe_id)
        description = str(manifest.get("description", "")).strip()
        recipes.append(
            ReferenceCircuitRecipeSummary(
                recipe_id=index_entry.recipe_id,
                title=index_entry.title,
                summary=description or None,
            )
        )
    return ReferenceCircuitRecipeList(
        discovery_guidance=RECIPE_CATALOG_DISCOVERY_GUIDANCE,
        recipes=tuple(recipes),
    )


__all__ = [
    "SERVICE_SPEC",
    "ReferenceCircuitRecipeList",
    "ReferenceCircuitRecipeSummary",
    "list_reference_circuit_recipes",
]
