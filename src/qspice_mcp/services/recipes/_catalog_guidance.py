"""Shared guidance for discovering bundled reference-circuit recipes."""

from __future__ import annotations

RECIPE_CATALOG_DISCOVERY_GUIDANCE = (
    "Discover bundled circuits before copying or simulating: call "
    "list_reference_circuit_recipes for compact ids and summaries, then "
    "describe_reference_circuit_recipe for manifest files, workflow entries, "
    "and a topology digest. Use materialize_reference_circuit only when you "
    "need workspace-local copies; prefer read_workflow_instruction for "
    "step-by-step authoring prompts."
)

__all__ = ["RECIPE_CATALOG_DISCOVERY_GUIDANCE"]
