"""Register MCP prompts with the FastMCP application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import PromptDefinition, render_prompt_message

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def _messages_from_text(text: str) -> list[dict[str, object]]:
    return [{"role": "user", "content": {"type": "text", "text": text}}]


def register_prompts(app: FastMCP, definitions: tuple[PromptDefinition, ...]) -> None:
    """Bind prompt handlers for all bundled workflow definitions."""

    del definitions

    @app.prompt(
        name="qspice_buck_converter_from_scratch",
        title="Buck Converter From Scratch",
        description=(
            "Guide authoring a buck converter schematic, generating a netlist, "
            "and running a transient simulation."
        ),
    )
    def buck_prompt(vin: str = "12", vout: str = "5", iout: str = "1") -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message(
                "qspice_buck_converter_from_scratch",
                vin=vin,
                vout=vout,
                iout=iout,
            )
        )

    @app.prompt(
        name="qspice_debug_convergence",
        title="Debug Convergence",
        description="Structured workflow for diagnosing a non-converging QSpice simulation.",
    )
    def debug_prompt(log_path: str) -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message("qspice_debug_convergence", log_path=log_path)
        )

    @app.prompt(
        name="qspice_run_and_measure",
        title="Run And Measure",
        description="Run a simulation and read bounded waveform measurements for key signals.",
    )
    def measure_prompt(schematic_path: str, signals: str = "V(out)") -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message(
                "qspice_run_and_measure",
                schematic_path=schematic_path,
                signals=signals,
            )
        )

    @app.prompt(
        name="qspice_author_dll_device",
        title="Author DLL Device",
        description="Scaffold and build a mixed-signal C-block/DLL device for QSpice.",
    )
    def dll_prompt(device_kind: str = "control") -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message("qspice_author_dll_device", device_kind=device_kind)
        )

    @app.prompt(
        name="qspice_sweep_design",
        title="Sweep Design Parameter",
        description="Plan and execute a parameter sweep on an existing schematic.",
    )
    def sweep_prompt(schematic_path: str, param: str, sweep_range: str) -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message(
                "qspice_sweep_design",
                schematic_path=schematic_path,
                param=param,
                sweep_range=sweep_range,
            )
        )


__all__ = ["register_prompts"]
