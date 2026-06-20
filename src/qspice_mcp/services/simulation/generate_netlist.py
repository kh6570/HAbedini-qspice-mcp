"""Service for resolving or staging derived netlist artifacts."""

from __future__ import annotations

from importlib import import_module
from shutil import copy2
from typing import TYPE_CHECKING, Protocol, cast

from qspice_mcp.core.exceptions import ArtifactMissingError, BackendUnavailableError, QSpiceError
from qspice_mcp.infra.config import QSpiceSettings
from qspice_mcp.services._shared.paths import resolve_workspace_path, validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec
from qspice_mcp.services.simulation._clean_room_netlist import (
    dll_component_references,
    netlist_covers_dll_references,
    render_clean_room_netlist,
)
from qspice_mcp.services.simulation._netlist_result import GeneratedNetlist, NetlistBackend
from qspice_mcp.services.simulation._qux_netlist import generate_netlist_with_qux

if TYPE_CHECKING:
    from pathlib import Path

_NETLIST_SUFFIXES = (".net", ".cir")
_EDITOR_MODULE_CANDIDATES: tuple[str, ...] = ("qspice_mcp.services._backends._qsch_editor",)
_DLL_OMISSION_WARNING = (
    "The schematic contains DLL/C-block components that the clean-room parser omits; "
    "simulation may fail unless QSpice and companion QUX.exe are configured."
)


class _QschEditor(Protocol):
    """Minimal runtime protocol for editor-backed netlist generation."""

    def save_netlist(self, path: str) -> None:
        """Write a derived netlist to the requested destination."""


class _QschEditorFactory(Protocol):
    """Callable protocol for constructing a schematic editor instance."""

    def __call__(self, path: str) -> _QschEditor:
        """Create an editor bound to one schematic path."""


SERVICE_SPEC = ServiceSpec(
    name="generate_netlist",
    title="Generate Netlist",
    summary="Resolve or stage the derived netlist used for QSpice execution.",
    phase="implemented",
    read_only=False,
    idempotent=True,
)


def _resolve_output_path(
    output_path: str | Path | None,
    *,
    workspace_root: Path,
    default: Path,
) -> Path:
    """Resolve an optional netlist output path within the workspace."""

    if output_path is None:
        return default.resolve(strict=False)
    resolved = resolve_workspace_path(output_path, workspace_root=workspace_root)
    if resolved.suffix.lower() not in _NETLIST_SUFFIXES:
        raise ValueError("Netlist output path must end in .net or .cir")
    return resolved


def _find_existing_derived_netlist(schematic_path: Path) -> Path | None:
    """Return a sibling derived netlist if one already exists."""

    for suffix in _NETLIST_SUFFIXES:
        candidate = schematic_path.with_suffix(suffix)
        if candidate.is_file():
            return candidate.resolve(strict=False)
    return None


def _derived_netlist_is_stale(schematic_path: Path, netlist_path: Path) -> bool:
    """Return whether a schematic is newer than its sibling derived netlist."""

    return schematic_path.stat().st_mtime > netlist_path.stat().st_mtime


def _copy_if_needed(source: Path, destination: Path) -> bool:
    """Copy a netlist only when the destination differs from the source."""

    if source == destination:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    copy2(source, destination)
    return True


def _effective_settings(
    workspace_root: Path,
    settings: QSpiceSettings | None,
) -> QSpiceSettings:
    """Normalize settings while preserving the caller workspace root."""

    if settings is None:
        return QSpiceSettings(workspace_root=workspace_root).normalized()
    normalized = settings.normalized()
    if normalized.workspace_root.resolve(strict=False) == workspace_root.resolve(strict=False):
        return normalized
    return QSpiceSettings(
        workspace_root=workspace_root,
        exe=normalized.exe,
        log_level=normalized.log_level,
        telemetry_enabled=normalized.telemetry_enabled,
    ).normalized()


def _needs_netlist_refresh(
    schematic_path: Path,
    existing_netlist: Path | None,
    dll_refs: tuple[str, ...],
) -> bool:
    """Return whether a schematic requires netlist regeneration."""

    if existing_netlist is None:
        return True
    if _derived_netlist_is_stale(schematic_path, existing_netlist):
        return True
    if dll_refs:
        netlist_text = existing_netlist.read_text(encoding="utf-8", errors="replace")
        if not netlist_covers_dll_references(netlist_text, dll_refs):
            return True
    return False


def _load_qsch_editor_factory() -> tuple[_QschEditorFactory | None, str | None]:
    """Return the first locally available schematic editor backend."""

    for module_name in _EDITOR_MODULE_CANDIDATES:
        try:
            module = import_module(module_name)
        except ImportError:
            continue
        editor_class = getattr(module, "QschEditor", None)
        if editor_class is None:
            continue
        return cast("_QschEditorFactory", editor_class), module_name
    return None, None


def _generate_netlist_with_editor_backend(
    schematic_path: Path,
    destination: Path,
) -> GeneratedNetlist:
    """Generate a derived netlist through an installed qspice-compatible editor."""

    editor_factory, backend_name = _load_qsch_editor_factory()
    if editor_factory is None or backend_name is None:
        raise BackendUnavailableError(
            "No derived .net or .cir exists for this schematic, and no compatible local "
            "QschEditor backend "
            "QschEditor backend is installed for editor-driven generation."
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        editor = editor_factory(str(schematic_path))
        editor.save_netlist(str(destination))
    except Exception as exc:
        raise QSpiceError(
            f"Failed to generate a derived netlist from {schematic_path.name} "
            f"using {backend_name}.QschEditor."
        ) from exc

    if not destination.is_file():
        raise ArtifactMissingError(
            f"{backend_name}.QschEditor did not create the requested netlist artifact: "
            f"{destination}"
        )

    return GeneratedNetlist(
        source_path=schematic_path,
        netlist_path=destination,
        source_kind="schematic",
        refreshed=True,
        copied=False,
        netlist_backend="editor",
        warnings=(
            f"Generated a derived netlist from the schematic via the installed "
            f"{backend_name}.QschEditor backend.",
        ),
    )


def _generate_netlist_with_clean_room_parser(
    schematic_path: Path,
    destination: Path,
    *,
    dll_refs: tuple[str, ...] = (),
) -> GeneratedNetlist:
    """Generate a derived netlist through the repo-owned clean-room qsch parser."""

    parsed = render_clean_room_netlist(schematic_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(parsed.netlist_text, encoding="utf-8")
    warnings: list[str] = [
        "Generated a derived netlist from the schematic via the repo-owned clean-room parser.",
    ]
    if dll_refs:
        warnings.append(_DLL_OMISSION_WARNING)
    return GeneratedNetlist(
        source_path=schematic_path,
        netlist_path=destination,
        source_kind="schematic",
        refreshed=True,
        copied=False,
        netlist_backend="clean_room",
        warnings=tuple(warnings),
    )


def _try_generate_netlist_with_qux(
    schematic_path: Path,
    destination: Path,
    *,
    settings: QSpiceSettings,
) -> GeneratedNetlist | None:
    """Generate a derived netlist through QUX when the companion executable is available."""

    try:
        return generate_netlist_with_qux(
            schematic_path,
            destination,
            settings=settings,
        )
    except BackendUnavailableError:
        return None


def _regenerate_schematic_netlist(
    schematic_path: Path,
    destination: Path,
    *,
    settings: QSpiceSettings,
    dll_refs: tuple[str, ...],
) -> GeneratedNetlist:
    """Regenerate a derived netlist for one schematic input."""

    if dll_refs:
        qux_generated = _try_generate_netlist_with_qux(
            schematic_path,
            destination,
            settings=settings,
        )
        if qux_generated is not None:
            return qux_generated

    clean_room_error: QSpiceError | None = None
    try:
        return _generate_netlist_with_clean_room_parser(
            schematic_path,
            destination,
            dll_refs=dll_refs,
        )
    except QSpiceError as exc:
        clean_room_error = exc

    try:
        return _generate_netlist_with_editor_backend(schematic_path, destination)
    except BackendUnavailableError as exc:
        if clean_room_error is None:
            raise
        raise QSpiceError(
            "The supported clean-room parser could not regenerate the schematic "
            f"({clean_room_error}), and no compatible local QschEditor backend is installed "
            "for editor-driven generation."
        ) from exc


def generate_netlist(
    raw_path: str | Path,
    *,
    workspace_root: Path,
    output_path: str | Path | None = None,
    settings: QSpiceSettings | None = None,
) -> GeneratedNetlist:
    """Resolve an existing derived netlist or stage it to a requested location."""

    normalized_workspace = workspace_root.resolve(strict=False)
    effective_settings = _effective_settings(normalized_workspace, settings)
    source_path = validate_existing_file(
        raw_path,
        workspace_root=normalized_workspace,
        suffixes=(".qsch", ".net", ".cir"),
    )

    if source_path.suffix.lower() in _NETLIST_SUFFIXES:
        destination = _resolve_output_path(
            output_path,
            workspace_root=normalized_workspace,
            default=source_path,
        )
        copied = _copy_if_needed(source_path, destination)
        return GeneratedNetlist(
            source_path=source_path,
            netlist_path=destination,
            source_kind="netlist",
            refreshed=False,
            copied=copied,
            netlist_backend="existing",
            warnings=("Source path is already a derived netlist artifact.",),
        )

    dll_refs = dll_component_references(source_path)
    existing_netlist = _find_existing_derived_netlist(source_path)
    destination = _resolve_output_path(
        output_path,
        workspace_root=normalized_workspace,
        default=(existing_netlist or source_path.with_suffix(".net")),
    )

    if _needs_netlist_refresh(source_path, existing_netlist, dll_refs):
        return _regenerate_schematic_netlist(
            source_path,
            destination,
            settings=effective_settings,
            dll_refs=dll_refs,
        )

    assert existing_netlist is not None
    copied = _copy_if_needed(existing_netlist, destination)
    return GeneratedNetlist(
        source_path=source_path,
        netlist_path=destination,
        source_kind="schematic",
        refreshed=False,
        copied=copied,
        netlist_backend="existing",
        warnings=(
            "Using an existing derived netlist artifact instead of regenerating the schematic.",
        ),
    )


__all__ = ["SERVICE_SPEC", "GeneratedNetlist", "NetlistBackend", "generate_netlist"]
