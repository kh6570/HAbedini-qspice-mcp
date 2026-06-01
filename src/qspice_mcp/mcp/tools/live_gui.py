"""Live GUI support and session scaffold tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.services.live_gui.describe_live_gui_support import (
    describe_live_gui_support as describe_live_gui_support_service,
)
from qspice_mcp.services.live_gui.open_schematic_in_gui import (
    open_schematic_in_gui as open_schematic_in_gui_service,
)
from qspice_mcp.services.live_gui.refresh_schematic_in_gui import (
    RefreshStrategy,
)
from qspice_mcp.services.live_gui.refresh_schematic_in_gui import (
    refresh_schematic_in_gui as refresh_schematic_in_gui_service,
)
from qspice_mcp.services.live_gui.scaffold_live_gui_session import (
    scaffold_live_gui_session as scaffold_live_gui_session_service,
)

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsLiveGuiRuntime as _RuntimeWithLiveGui
else:
    _RuntimeWithLiveGui = object

LIVE_GUI_HANDLER_NAMES = (
    "refresh_schematic_in_gui",
    "open_schematic_in_gui",
    "describe_live_gui_support",
    "scaffold_live_gui_session",
    "launch_live_gui_session",
    "poll_live_gui_session",
    "send_live_gui_session_command",
    "poll_live_gui_session_events",
    "close_live_gui_session",
)


class LiveGuiToolMixin:
    """Handlers for the optional live GUI capability layer."""

    def refresh_schematic_in_gui(
        self: _RuntimeWithLiveGui,
        schematic_path: str,
        strategy: RefreshStrategy = "reopen_via_association",
        force_restart: bool = False,
    ) -> dict[str, object]:
        refreshed = refresh_schematic_in_gui_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            strategy=strategy,
            force_restart=force_restart,
        )
        return to_json_object(refreshed)

    def open_schematic_in_gui(
        self: _RuntimeWithLiveGui,
        schematic_path: str,
    ) -> dict[str, object]:
        opened = open_schematic_in_gui_service(
            schematic_path,
            workspace_root=self.settings.workspace_root,
        )
        return to_json_object(opened)

    def describe_live_gui_support(self: _RuntimeWithLiveGui) -> dict[str, object]:
        inspection = describe_live_gui_support_service(settings=self.settings)
        return to_json_object(inspection)

    def scaffold_live_gui_session(
        self: _RuntimeWithLiveGui,
        session_name: str,
        schematic_path: str | None = None,
        waveform_names: list[str] | None = None,
        cross_probe_signals: list[str] | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        scaffold = scaffold_live_gui_session_service(
            session_name,
            workspace_root=self.settings.workspace_root,
            settings=self.settings,
            schematic_path=schematic_path,
            waveform_names=waveform_names,
            cross_probe_signals=cross_probe_signals,
            output_path=output_path,
        )
        return to_json_object(scaffold)

    def launch_live_gui_session(
        self: _RuntimeWithLiveGui,
        session_name: str,
        schematic_path: str | None = None,
        waveform_names: list[str] | None = None,
        cross_probe_signals: list[str] | None = None,
        output_path: str | None = None,
    ) -> dict[str, object]:
        launched = self._live_gui_manager.launch_live_gui_session(
            session_name=session_name,
            schematic_path=schematic_path,
            waveform_names=waveform_names,
            cross_probe_signals=cross_probe_signals,
            output_path=output_path,
        )
        return to_json_object(launched)

    def poll_live_gui_session(
        self: _RuntimeWithLiveGui,
        session_id: str,
    ) -> dict[str, object]:
        return to_json_object(self._live_gui_manager.poll_live_gui_session(session_id))

    def send_live_gui_session_command(
        self: _RuntimeWithLiveGui,
        session_id: str,
        command: str,
        signal: str | None = None,
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        return to_json_object(
            self._live_gui_manager.send_live_gui_session_command(
                session_id,
                command=command,
                signal=signal,
                payload=payload,
            )
        )

    def poll_live_gui_session_events(
        self: _RuntimeWithLiveGui,
        session_id: str,
        after_sequence: int = 0,
        limit: int = 50,
    ) -> dict[str, object]:
        return to_json_object(
            self._live_gui_manager.poll_live_gui_session_events(
                session_id,
                after_sequence=after_sequence,
                limit=limit,
            )
        )

    def close_live_gui_session(
        self: _RuntimeWithLiveGui,
        session_id: str,
        delete_manifest: bool = False,
    ) -> dict[str, object]:
        return to_json_object(
            self._live_gui_manager.close_live_gui_session(
                session_id,
                delete_manifest=delete_manifest,
            )
        )


__all__ = ["LIVE_GUI_HANDLER_NAMES", "LiveGuiToolMixin"]
