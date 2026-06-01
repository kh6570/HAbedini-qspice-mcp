"""Load bundled circuit recipes and workflow instructions from package data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import Any

from qspice_mcp.core.exceptions import ValidationError

_RECIPES_ROOT = "qspice_mcp.data.recipes"


@dataclass(frozen=True, slots=True)
class RecipeIndexEntry:
    """One recipe row from the top-level catalog."""

    recipe_id: str
    title: str


@dataclass(frozen=True, slots=True)
class WorkflowInstructionEntry:
    """One workflow instruction row from a recipe manifest."""

    instruction_id: str
    recipe_id: str
    title: str
    summary: str
    track: str
    document: str
    related_instruction_id: str | None


@cache
def _recipes_root():
    return files(_RECIPES_ROOT)


def list_recipe_index_entries() -> tuple[RecipeIndexEntry, ...]:
    """Return every recipe listed in the top-level catalog."""

    index_path = _recipes_root() / "index.json"
    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValidationError("Recipe index is missing from package data.") from exc
    raw_recipes = payload.get("recipes")
    if not isinstance(raw_recipes, list):
        raise ValidationError("Recipe index must include a recipes array.")

    entries: list[RecipeIndexEntry] = []
    for raw_entry in raw_recipes:
        if not isinstance(raw_entry, dict):
            raise ValidationError("Each recipe index entry must be a JSON object.")
        recipe_id = str(raw_entry.get("recipe_id", "")).strip()
        if not recipe_id:
            raise ValidationError("Recipe index entries require recipe_id.")
        entries.append(
            RecipeIndexEntry(
                recipe_id=recipe_id,
                title=str(raw_entry.get("title", recipe_id)).strip(),
            )
        )
    return tuple(entries)


@cache
def load_recipe_manifest(recipe_id: str) -> dict[str, Any]:
    """Load and validate one recipe manifest."""

    normalized_recipe_id = recipe_id.strip()
    if not normalized_recipe_id:
        raise ValidationError("recipe_id must not be empty.")

    manifest_path = _recipes_root() / normalized_recipe_id / "recipe.json"
    try:
        manifest_text = manifest_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(f"Unknown recipe_id: {recipe_id!r}") from exc

    manifest = json.loads(manifest_text)
    if manifest.get("recipe_id") != normalized_recipe_id:
        raise ValidationError(
            f"Recipe manifest recipe_id mismatch: expected {normalized_recipe_id!r}, "
            f"got {manifest.get('recipe_id')!r}"
        )
    return manifest


def recipe_bundle_path(recipe_id: str, bundle_name: str):
    """Return one artifact path inside a recipe bundle."""

    return _recipes_root() / recipe_id.strip() / bundle_name


def list_workflow_instruction_entries() -> tuple[WorkflowInstructionEntry, ...]:
    """Return every workflow instruction declared across all recipes."""

    entries: list[WorkflowInstructionEntry] = []
    for recipe_entry in list_recipe_index_entries():
        manifest = load_recipe_manifest(recipe_entry.recipe_id)
        raw_workflows = manifest.get("workflows")
        if raw_workflows is None:
            continue
        if not isinstance(raw_workflows, list):
            raise ValidationError(
                f"Recipe {recipe_entry.recipe_id!r} workflows must be an array when present."
            )
        for raw_workflow in raw_workflows:
            if not isinstance(raw_workflow, dict):
                raise ValidationError("Each workflow entry must be a JSON object.")
            instruction_id = str(raw_workflow.get("instruction_id", "")).strip()
            document = str(raw_workflow.get("document", "")).strip()
            if not instruction_id or not document:
                raise ValidationError(
                    f"Recipe {recipe_entry.recipe_id!r} workflows require "
                    "instruction_id and document."
                )
            entries.append(
                WorkflowInstructionEntry(
                    instruction_id=instruction_id,
                    recipe_id=recipe_entry.recipe_id,
                    title=str(raw_workflow.get("title", instruction_id)).strip(),
                    summary=str(raw_workflow.get("summary", "")).strip(),
                    track=str(raw_workflow.get("track", "")).strip(),
                    document=document,
                    related_instruction_id=(
                        str(raw_workflow["related_instruction_id"]).strip()
                        if raw_workflow.get("related_instruction_id")
                        else None
                    ),
                )
            )
    return tuple(entries)


def resolve_workflow_instruction_entry(instruction_id: str) -> WorkflowInstructionEntry:
    """Resolve one instruction id to its recipe workflow entry."""

    normalized_id = instruction_id.strip()
    if not normalized_id:
        raise ValidationError("instruction_id must not be empty.")
    for entry in list_workflow_instruction_entries():
        if entry.instruction_id == normalized_id:
            return entry
    known = ", ".join(item.instruction_id for item in list_workflow_instruction_entries())
    raise ValidationError(
        f"Unknown instruction_id: {normalized_id!r}. Known instructions: {known or '(none)'}"
    )


def read_workflow_instruction_markdown(instruction_id: str) -> str:
    """Read one workflow instruction document from its recipe bundle."""

    entry = resolve_workflow_instruction_entry(instruction_id)
    document_path = _recipes_root() / entry.recipe_id / entry.document
    try:
        return document_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(
            f"Instruction document for {instruction_id!r} is missing: {entry.document}"
        ) from exc


__all__ = [
    "RecipeIndexEntry",
    "WorkflowInstructionEntry",
    "list_recipe_index_entries",
    "list_workflow_instruction_entries",
    "load_recipe_manifest",
    "read_workflow_instruction_markdown",
    "recipe_bundle_path",
    "resolve_workflow_instruction_entry",
]
