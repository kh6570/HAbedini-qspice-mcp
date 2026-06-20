"""Materialize server-bundled reference circuit recipes into the workspace."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import resolve_workspace_path
from qspice_mcp.services.recipes._catalog import load_recipe_manifest, recipe_bundle_path
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from typing import Any

_FILE_ENCODING = Literal["binary", "text"]


@dataclass(frozen=True, slots=True)
class MaterializedFile:
    """One file written by a reference-circuit materialization."""

    relative_path: str
    output_path: Path
    overwritten: bool


@dataclass(frozen=True, slots=True)
class MaterializedReferenceCircuit:
    """Metadata for one materialized reference-circuit recipe."""

    recipe_id: str
    title: str
    description: str
    output_dir: Path
    files: tuple[MaterializedFile, ...]
    build_required: bool
    build_hint: str | None


SERVICE_SPEC = ServiceSpec(
    name="materialize_reference_circuit",
    title="Materialize Reference Circuit",
    summary=(
        "Write server-bundled reference circuit files into the workspace "
        "so an empty folder can reproduce a canonical bundled recipe from package data."
    ),
    phase="implemented",
    read_only=False,
)


def _write_materialized_file(
    *,
    recipe_id: str,
    file_entry: dict[str, Any],
    destination: Path,
    overwrite: bool,
) -> MaterializedFile:
    relative_path = str(file_entry["relative_path"])
    bundle_name = str(file_entry.get("bundle_name", Path(relative_path).name))
    encoding = str(file_entry.get("encoding", "binary"))
    if encoding not in ("binary", "text"):
        raise ValidationError(f"Unsupported bundle encoding {encoding!r} for {relative_path}")

    bundle_path = recipe_bundle_path(recipe_id, bundle_name)
    try:
        bundle_bytes = bundle_path.read_bytes()
    except FileNotFoundError as exc:
        raise ValidationError(
            f"Bundled file missing for recipe {recipe_id!r}: {bundle_name!r}"
        ) from exc

    if destination.exists() and not overwrite:
        raise ValidationError(f"File already exists (set overwrite=true): {destination}")

    overwritten = destination.exists()
    destination.parent.mkdir(parents=True, exist_ok=True)
    if encoding == "text":
        destination.write_text(bundle_bytes.decode("utf-8"), encoding="utf-8", newline="\n")
    else:
        destination.write_bytes(bundle_bytes)

    return MaterializedFile(
        relative_path=relative_path,
        output_path=destination,
        overwritten=overwritten,
    )


def materialize_reference_circuit(
    recipe_id: str,
    *,
    workspace_root: Path,
    output_dir: str | Path | None = None,
    overwrite: bool = False,
) -> MaterializedReferenceCircuit:
    """Write one bundled reference circuit recipe into the workspace."""

    manifest = load_recipe_manifest(recipe_id)
    if output_dir is None:
        resolved_output_dir = workspace_root.resolve(strict=False)
    else:
        resolved_output_dir = resolve_workspace_path(output_dir, workspace_root=workspace_root)
        if resolved_output_dir.is_file():
            raise ValidationError(f"output_dir must be a directory: {resolved_output_dir}")

    resolved_output_dir.mkdir(parents=True, exist_ok=True)

    file_entries = manifest.get("files")
    if not isinstance(file_entries, list) or not file_entries:
        raise ValidationError(f"Recipe {recipe_id!r} manifest has no files.")

    materialized_files: list[MaterializedFile] = []
    for file_entry in file_entries:
        if not isinstance(file_entry, dict):
            raise ValidationError(f"Invalid file entry in recipe {recipe_id!r} manifest.")
        relative_path = str(file_entry["relative_path"])
        destination = resolved_output_dir / relative_path
        materialized_files.append(
            _write_materialized_file(
                recipe_id=recipe_id,
                file_entry=file_entry,
                destination=destination,
                overwrite=overwrite,
            )
        )

    return MaterializedReferenceCircuit(
        recipe_id=recipe_id,
        title=str(manifest.get("title", recipe_id)),
        description=str(manifest.get("description", "")),
        output_dir=resolved_output_dir,
        files=tuple(materialized_files),
        build_required=bool(manifest.get("build_required", False)),
        build_hint=(
            None if manifest.get("build_hint") is None else str(manifest.get("build_hint"))
        ),
    )


__all__ = [
    "SERVICE_SPEC",
    "MaterializedFile",
    "MaterializedReferenceCircuit",
    "materialize_reference_circuit",
]
