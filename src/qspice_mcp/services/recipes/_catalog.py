"""Load bundled circuit recipes and workflow instructions from package data."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cache
from importlib.resources import files
from typing import TYPE_CHECKING, Any

from qspice_mcp.core.exceptions import ValidationError

if TYPE_CHECKING:
    from importlib.resources.abc import Traversable

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
def _recipes_root() -> Traversable:
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

    manifest: dict[str, Any] = json.loads(manifest_text)
    if manifest.get("recipe_id") != normalized_recipe_id:
        raise ValidationError(
            f"Recipe manifest recipe_id mismatch: expected {normalized_recipe_id!r}, "
            f"got {manifest.get('recipe_id')!r}"
        )
    return manifest


def recipe_bundle_path(recipe_id: str, bundle_name: str) -> Traversable:
    """Return one artifact path inside a recipe bundle."""

    return _recipes_root() / recipe_id.strip() / bundle_name


def read_recipe_manifest_text(recipe_id: str) -> str:
    """Return one recipe manifest as formatted JSON text."""

    manifest = load_recipe_manifest(recipe_id)
    return json.dumps(manifest, indent=2, sort_keys=True)


def _resolve_schematic_bundle_name(manifest: dict[str, Any], *, recipe_id: str) -> str:
    raw_files = manifest.get("files")
    if not isinstance(raw_files, list):
        raise ValidationError(f"Recipe {recipe_id!r} files must be an array.")
    for raw_entry in raw_files:
        if not isinstance(raw_entry, dict):
            continue
        relative_path = str(raw_entry.get("relative_path", "")).strip()
        if not relative_path.lower().endswith(".qsch"):
            continue
        bundle_name = str(raw_entry.get("bundle_name", relative_path)).strip()
        if bundle_name:
            return bundle_name
    raise ValidationError(f"Recipe {recipe_id!r} does not declare a bundled schematic.")


def read_recipe_schematic_bytes(recipe_id: str) -> bytes:
    """Return the bundled schematic bytes for one recipe."""

    manifest = load_recipe_manifest(recipe_id)
    normalized_recipe_id = str(manifest["recipe_id"])
    bundle_name = _resolve_schematic_bundle_name(manifest, recipe_id=normalized_recipe_id)
    bundle_path = recipe_bundle_path(normalized_recipe_id, bundle_name)
    try:
        return bundle_path.read_bytes()
    except FileNotFoundError as exc:
        raise ValidationError(
            f"Bundled schematic missing for recipe {normalized_recipe_id!r}: {bundle_name!r}"
        ) from exc


def _allowed_recipe_documents(manifest: dict[str, Any]) -> set[str]:
    allowed: set[str] = set()
    raw_files = manifest.get("files")
    if isinstance(raw_files, list):
        for raw_entry in raw_files:
            if not isinstance(raw_entry, dict):
                continue
            for key in ("relative_path", "bundle_name"):
                value = str(raw_entry.get(key, "")).strip()
                if value:
                    allowed.add(value)
    raw_workflows = manifest.get("workflows")
    if isinstance(raw_workflows, list):
        for raw_workflow in raw_workflows:
            if not isinstance(raw_workflow, dict):
                continue
            document = str(raw_workflow.get("document", "")).strip()
            if document:
                allowed.add(document)
    return allowed


def read_recipe_document(recipe_id: str, document: str) -> str:
    """Read one bundled recipe document such as a workflow markdown file."""

    normalized_document = document.strip()
    if not normalized_document:
        raise ValidationError("document must not be empty.")
    if "/" in normalized_document or "\\" in normalized_document:
        raise ValidationError("document must be a bundle file name without path separators.")
    manifest = load_recipe_manifest(recipe_id)
    normalized_recipe_id = str(manifest["recipe_id"])
    allowed_documents = _allowed_recipe_documents(manifest)
    if normalized_document not in allowed_documents:
        known = ", ".join(sorted(allowed_documents))
        raise ValidationError(
            f"Unknown recipe document {normalized_document!r} for {normalized_recipe_id!r}. "
            f"Known documents: {known or '(none)'}"
        )
    document_path = recipe_bundle_path(normalized_recipe_id, normalized_document)
    try:
        return document_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ValidationError(
            f"Recipe document missing for {normalized_recipe_id!r}: {normalized_document!r}"
        ) from exc


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
    "read_recipe_document",
    "read_recipe_manifest_text",
    "read_recipe_schematic_bytes",
    "read_workflow_instruction_markdown",
    "recipe_bundle_path",
    "resolve_workflow_instruction_entry",
]
