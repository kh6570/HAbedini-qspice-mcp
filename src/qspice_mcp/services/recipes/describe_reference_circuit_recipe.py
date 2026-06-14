"""Service describing one bundled reference-circuit recipe."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services.recipes._catalog import load_recipe_manifest, recipe_bundle_path
from qspice_mcp.services.schematic.inspect_schematic import inspect_schematic_bytes
from qspice_mcp.services.service_spec import ServiceSpec

SERVICE_SPEC = ServiceSpec(
    name="describe_reference_circuit_recipe",
    title="Describe Reference Circuit Recipe",
    summary=(
        "Return one bundled reference-circuit manifest, workflow entries, "
        "and a lightweight topology digest from the bundled schematic."
    ),
    phase="implemented",
    read_only=True,
)


@dataclass(frozen=True, slots=True)
class RecipeFileEntry:
    """One file declared in a recipe manifest."""

    relative_path: str
    bundle_name: str
    encoding: str


@dataclass(frozen=True, slots=True)
class RecipeWorkflowSummary:
    """One workflow instruction row from a recipe manifest."""

    instruction_id: str
    title: str
    summary: str
    track: str
    document: str
    related_instruction_id: str | None


@dataclass(frozen=True, slots=True)
class TopologyComponentDigest:
    """One component row in a bundled schematic topology digest."""

    refdes: str
    kind: str


@dataclass(frozen=True, slots=True)
class TopologyDigest:
    """Lightweight read-only summary of a bundled schematic."""

    schematic_file: str
    component_count: int
    components: tuple[TopologyComponentDigest, ...]
    analyses: tuple[str, ...]
    parameters: tuple[str, ...]
    size_bytes: int


@dataclass(frozen=True, slots=True)
class ReferenceCircuitRecipeDescription:
    """Full description of one bundled reference-circuit recipe."""

    recipe_id: str
    title: str
    description: str
    files: tuple[RecipeFileEntry, ...]
    build_required: bool
    build_hint: str | None
    workflows: tuple[RecipeWorkflowSummary, ...]
    topology_digest: TopologyDigest | None


def _parse_file_entries(raw_files: object, *, recipe_id: str) -> tuple[RecipeFileEntry, ...]:
    if not isinstance(raw_files, list):
        raise ValidationError(f"Recipe {recipe_id!r} files must be an array.")
    entries: list[RecipeFileEntry] = []
    for raw_entry in raw_files:
        if not isinstance(raw_entry, dict):
            raise ValidationError(f"Recipe {recipe_id!r} file entries must be JSON objects.")
        relative_path = str(raw_entry.get("relative_path", "")).strip()
        if not relative_path:
            raise ValidationError(f"Recipe {recipe_id!r} file entries require relative_path.")
        bundle_name = str(raw_entry.get("bundle_name", relative_path)).strip()
        encoding = str(raw_entry.get("encoding", "binary")).strip()
        entries.append(
            RecipeFileEntry(
                relative_path=relative_path,
                bundle_name=bundle_name,
                encoding=encoding,
            )
        )
    return tuple(entries)


def _parse_workflow_entries(
    raw_workflows: object,
    *,
    recipe_id: str,
) -> tuple[RecipeWorkflowSummary, ...]:
    if raw_workflows is None:
        return ()
    if not isinstance(raw_workflows, list):
        raise ValidationError(f"Recipe {recipe_id!r} workflows must be an array when present.")
    entries: list[RecipeWorkflowSummary] = []
    for raw_workflow in raw_workflows:
        if not isinstance(raw_workflow, dict):
            raise ValidationError("Each workflow entry must be a JSON object.")
        instruction_id = str(raw_workflow.get("instruction_id", "")).strip()
        document = str(raw_workflow.get("document", "")).strip()
        if not instruction_id or not document:
            raise ValidationError(
                f"Recipe {recipe_id!r} workflows require instruction_id and document."
            )
        entries.append(
            RecipeWorkflowSummary(
                instruction_id=instruction_id,
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


def _find_schematic_file_entry(
    files: tuple[RecipeFileEntry, ...],
) -> RecipeFileEntry | None:
    for file_entry in files:
        if file_entry.relative_path.lower().endswith(".qsch"):
            return file_entry
    return None


def _build_topology_digest(
    *,
    recipe_id: str,
    schematic_entry: RecipeFileEntry,
) -> TopologyDigest:
    bundle_path = recipe_bundle_path(recipe_id, schematic_entry.bundle_name)
    try:
        raw_bytes = bundle_path.read_bytes()
    except FileNotFoundError as exc:
        raise ValidationError(
            f"Bundled schematic missing for recipe {recipe_id!r}: {schematic_entry.bundle_name!r}"
        ) from exc

    inspection = inspect_schematic_bytes(raw_bytes)
    return TopologyDigest(
        schematic_file=schematic_entry.relative_path,
        component_count=inspection.component_count,
        components=tuple(
            TopologyComponentDigest(refdes=component.refdes, kind=component.kind)
            for component in inspection.components
        ),
        analyses=tuple(analysis.raw for analysis in inspection.analyses),
        parameters=inspection.parameters,
        size_bytes=inspection.size_bytes,
    )


def describe_reference_circuit_recipe(recipe_id: str) -> ReferenceCircuitRecipeDescription:
    """Return manifest metadata and a topology digest for one bundled recipe."""

    manifest: dict[str, Any] = load_recipe_manifest(recipe_id)
    normalized_recipe_id = str(manifest["recipe_id"])
    files = _parse_file_entries(manifest.get("files"), recipe_id=normalized_recipe_id)
    workflows = _parse_workflow_entries(
        manifest.get("workflows"),
        recipe_id=normalized_recipe_id,
    )
    schematic_entry = _find_schematic_file_entry(files)
    topology_digest = (
        _build_topology_digest(recipe_id=normalized_recipe_id, schematic_entry=schematic_entry)
        if schematic_entry is not None
        else None
    )
    build_required = bool(manifest.get("build_required", False))
    build_hint_raw = manifest.get("build_hint")
    build_hint = str(build_hint_raw).strip() if build_hint_raw else None
    return ReferenceCircuitRecipeDescription(
        recipe_id=normalized_recipe_id,
        title=str(manifest.get("title", normalized_recipe_id)).strip(),
        description=str(manifest.get("description", "")).strip(),
        files=files,
        build_required=build_required,
        build_hint=build_hint,
        workflows=workflows,
        topology_digest=topology_digest,
    )


__all__ = [
    "SERVICE_SPEC",
    "RecipeFileEntry",
    "RecipeWorkflowSummary",
    "ReferenceCircuitRecipeDescription",
    "TopologyComponentDigest",
    "TopologyDigest",
    "describe_reference_circuit_recipe",
]
