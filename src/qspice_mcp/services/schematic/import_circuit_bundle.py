"""Import a user-supplied schematic bundle and sidecars into the workspace."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path  # noqa: TC003
from typing import TYPE_CHECKING

from qspice_mcp.core.exceptions import ValidationError
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from typing import Literal

_ARTIFACT_SUFFIXES = frozenset({".net", ".log", ".qraw", ".meas", ".fir", ".raw"})
_SIDECAR_SUFFIXES = frozenset(
    {
        ".cpp",
        ".c",
        ".cc",
        ".cxx",
        ".h",
        ".hpp",
        ".dll",
        ".lib",
        ".inc",
        ".cir",
        ".qdef",
        ".txt",
        ".md",
        ".json",
    }
)


@dataclass(frozen=True, slots=True)
class ImportedCircuitFile:
    """One file copied by a circuit bundle import."""

    relative_path: str
    output_path: Path
    overwritten: bool
    encoding: Literal["binary", "text"]


@dataclass(frozen=True, slots=True)
class ImportedCircuitBundle:
    """Metadata for one imported schematic bundle."""

    source_schematic: Path
    output_dir: Path
    files: tuple[ImportedCircuitFile, ...]


SERVICE_SPEC = ServiceSpec(
    name="import_circuit_bundle",
    title="Import Circuit Bundle",
    summary=(
        "Copy one workspace-local `.qsch` schematic and sibling sidecar files "
        "into a destination folder."
    ),
    phase="implemented",
    read_only=False,
)


def _should_copy_sidecar(path: Path) -> bool:
    suffix = path.suffix.lower()
    if suffix in _ARTIFACT_SUFFIXES:
        return False
    if suffix == ".qsch":
        return True
    return suffix in _SIDECAR_SUFFIXES


def import_circuit_bundle(
    schematic_path: str | Path,
    *,
    workspace_root: Path,
    output_dir: str | Path | None = None,
    overwrite: bool = False,
) -> ImportedCircuitBundle:
    """Copy one schematic and sibling sidecars into a workspace destination."""

    normalized_workspace = workspace_root.resolve(strict=False)
    source_schematic = validate_existing_file(
        schematic_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch",),
    )
    destination_root = (
        resolve_workspace_path(output_dir, workspace_root=normalized_workspace)
        if output_dir is not None
        else source_schematic.parent.resolve(strict=False)
    )
    destination_root.mkdir(parents=True, exist_ok=True)

    copied: list[ImportedCircuitFile] = []
    source_dir = source_schematic.parent.resolve(strict=False)
    for candidate in sorted(source_dir.iterdir()):
        if not candidate.is_file() or not _should_copy_sidecar(candidate):
            continue
        relative_path = candidate.name
        destination = (destination_root / relative_path).resolve(strict=False)
        if destination.exists() and not overwrite:
            raise ValidationError(f"File already exists (set overwrite=true): {destination}")
        overwritten = destination.exists()
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate, destination)
        text_suffixes = {".cpp", ".c", ".h", ".md", ".txt", ".json"}
        encoding: Literal["binary", "text"] = (
            "text" if candidate.suffix.lower() in text_suffixes else "binary"
        )
        copied.append(
            ImportedCircuitFile(
                relative_path=relative_path,
                output_path=destination,
                overwritten=overwritten,
                encoding=encoding,
            )
        )

    if not copied:
        raise ValidationError("No schematic or sidecar files were found to import.")

    return ImportedCircuitBundle(
        source_schematic=source_schematic,
        output_dir=destination_root,
        files=tuple(copied),
    )


__all__ = [
    "SERVICE_SPEC",
    "ImportedCircuitBundle",
    "ImportedCircuitFile",
    "import_circuit_bundle",
]
