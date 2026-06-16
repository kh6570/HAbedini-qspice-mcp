"""Generate a manifest scaffold for the optional live GUI orchestration layer."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING

from qspice_mcp.services._internals.simulation_batch import slugify
from qspice_mcp.services._shared.paths import resolve_workspace_output_path, validate_existing_file
from qspice_mcp.services.service_spec import ServiceSpec

if TYPE_CHECKING:
    from collections.abc import Sequence
    from pathlib import Path

    from qspice_mcp.infra.config import QSpiceSettings


_BRIDGE_COMMAND_QUEUE_NAME = "bridge.commands.jsonl"
_BRIDGE_EVENT_LOG_NAME = "bridge.events.jsonl"


@dataclass(frozen=True, slots=True)
class LiveGuiSessionScaffold:
    """Metadata for one scaffolded live GUI session manifest."""

    session_name: str
    manifest_path: Path
    schematic_path: Path | None
    launch_command: tuple[str, ...]
    waveform_names: tuple[str, ...]
    cross_probe_signals: tuple[str, ...]
    notes: tuple[str, ...] = ()


SERVICE_SPEC = ServiceSpec(
    name="scaffold_live_gui_session",
    title="Scaffold Live GUI Session",
    summary=(
        "Generate a version-gated JSON manifest that an external Windows-message bridge can "
        "use for optional live GUI orchestration and cross-probing."
    ),
    phase="implemented",
)


def _normalize_entries(values: Sequence[str] | None, *, field_name: str) -> tuple[str, ...]:
    """Normalize an optional ordered list of non-empty session entries."""

    if values is None:
        return ()
    normalized: list[str] = []
    for value in values:
        item = value.strip()
        if not item:
            raise ValueError(f"{field_name} entries must not be empty.")
        normalized.append(item)
    return tuple(normalized)


def _bridge_command_queue_path(manifest_path: Path) -> Path:
    return (manifest_path.parent / _BRIDGE_COMMAND_QUEUE_NAME).resolve(strict=False)


def _bridge_event_log_path(manifest_path: Path) -> Path:
    return (manifest_path.parent / _BRIDGE_EVENT_LOG_NAME).resolve(strict=False)


def scaffold_live_gui_session(
    session_name: str,
    *,
    workspace_root: Path,
    settings: QSpiceSettings,
    schematic_path: str | Path | None = None,
    waveform_names: Sequence[str] | None = None,
    cross_probe_signals: Sequence[str] | None = None,
    output_path: str | Path | None = None,
) -> LiveGuiSessionScaffold:
    """Write a live GUI session manifest for an external optional bridge layer."""

    normalized_name = session_name.strip()
    if not normalized_name:
        raise ValueError("session_name must not be empty.")

    effective_settings = settings.normalized()
    resolved_schematic = (
        None
        if schematic_path is None
        else validate_existing_file(
            schematic_path,
            workspace_root=workspace_root.resolve(strict=False),
            suffixes=(".qsch",),
        )
    )
    normalized_waveforms = _normalize_entries(waveform_names, field_name="waveform_names")
    normalized_cross_probe_signals = _normalize_entries(
        cross_probe_signals,
        field_name="cross_probe_signals",
    )

    manifest_path = resolve_workspace_output_path(
        output_path,
        workspace_root=workspace_root,
        default=workspace_root / "artifacts" / "live_gui" / f"{slugify(normalized_name)}.json",
        suffixes=(".json",),
    )

    launch_command: tuple[str, ...] = ()
    if effective_settings.exe is not None and effective_settings.exe.is_file():
        launch_command = (str(effective_settings.exe),)
        if resolved_schematic is not None:
            launch_command = (*launch_command, str(resolved_schematic))

    notes = [
        (
            "This manifest does not execute QSpice directly; it is a contract "
            "for an external Windows-only bridge."
        ),
        (
            "The bridge layer remains version-gated because the Windows-message "
            "appendix is not treated as a stable always-on dependency."
        ),
        (
            "The bridge_protocol section exposes JSONL command and event files "
            "that the external bridge can translate into Windows messages."
        ),
    ]
    if sys.platform != "win32":
        notes.append(
            "The current host platform is not Windows, so this scaffold is for planning only."
        )
    if not launch_command:
        notes.append(
            "No launch command was embedded because a configured QSpice "
            "executable was not available."
        )
    elif resolved_schematic is None:
        notes.append(
            "A QSpice executable was found, but no schematic path was supplied "
            "for launch scaffolding."
        )
    else:
        notes.append(
            "The launch command opens the requested schematic, but an external "
            "bridge still owns all live message transport."
        )

    manifest_payload = {
        "schema_version": 1,
        "session_name": normalized_name,
        "transport": "windows_messages",
        "windows_only": True,
        "version_gated": True,
        "external_bridge_required": True,
        "bridge_protocol": {
            "command_queue": {
                "format": "jsonl",
                "path": str(_bridge_command_queue_path(manifest_path)),
            },
            "event_log": {
                "format": "jsonl",
                "path": str(_bridge_event_log_path(manifest_path)),
            },
        },
        "launch": {
            "qspice_exe": None if effective_settings.exe is None else str(effective_settings.exe),
            "schematic_path": None if resolved_schematic is None else str(resolved_schematic),
            "command": list(launch_command),
        },
        "waveform_names": list(normalized_waveforms),
        "cross_probe_signals": list(normalized_cross_probe_signals),
        "notes": notes,
    }

    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest_payload, indent=2), encoding="utf-8")

    return LiveGuiSessionScaffold(
        session_name=normalized_name,
        manifest_path=manifest_path,
        schematic_path=resolved_schematic,
        launch_command=launch_command,
        waveform_names=normalized_waveforms,
        cross_probe_signals=normalized_cross_probe_signals,
        notes=tuple(notes),
    )


__all__ = ["SERVICE_SPEC", "LiveGuiSessionScaffold", "scaffold_live_gui_session"]
