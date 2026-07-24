"""Register MCP prompts with the FastMCP application."""

from __future__ import annotations

from typing import TYPE_CHECKING

from . import PromptDefinition, render_prompt_message

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP


def _messages_from_text(text: str) -> list[dict[str, object]]:
    return [{"role": "user", "content": {"type": "text", "text": text}}]


def register_prompts(app: FastMCP, definitions: tuple[PromptDefinition, ...]) -> None:
    """Bind prompt handlers, driving each prompt's metadata from ``definitions``.

    Every handler resolves its title and description from the matching
    :class:`PromptDefinition`, so the registered MCP metadata cannot drift from
    :func:`get_prompt_definitions`. A missing definition raises ``KeyError`` at
    registration time rather than silently shipping a hard-coded prompt.
    """

    by_name = {definition.name: definition for definition in definitions}

    def _meta(name: str) -> tuple[str, str, str]:
        definition = by_name.get(name)
        if definition is None:
            raise KeyError(f"No PromptDefinition registered for prompt {name!r}.")
        return definition.name, definition.title, definition.description

    buck_name, buck_title, buck_description = _meta("qspice_buck_converter_from_scratch")

    @app.prompt(name=buck_name, title=buck_title, description=buck_description)
    def buck_prompt(vin: str = "12", vout: str = "5", iout: str = "1") -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message(
                "qspice_buck_converter_from_scratch",
                vin=vin,
                vout=vout,
                iout=iout,
            )
        )

    debug_name, debug_title, debug_description = _meta("qspice_debug_convergence")

    @app.prompt(name=debug_name, title=debug_title, description=debug_description)
    def debug_prompt(log_path: str) -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message("qspice_debug_convergence", log_path=log_path)
        )

    measure_name, measure_title, measure_description = _meta("qspice_run_and_measure")

    @app.prompt(name=measure_name, title=measure_title, description=measure_description)
    def measure_prompt(schematic_path: str, signals: str = "V(out)") -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message(
                "qspice_run_and_measure",
                schematic_path=schematic_path,
                signals=signals,
            )
        )

    dll_name, dll_title, dll_description = _meta("qspice_author_dll_device")

    @app.prompt(name=dll_name, title=dll_title, description=dll_description)
    def dll_prompt(device_kind: str = "control") -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message("qspice_author_dll_device", device_kind=device_kind)
        )

    sweep_name, sweep_title, sweep_description = _meta("qspice_sweep_design")

    @app.prompt(name=sweep_name, title=sweep_title, description=sweep_description)
    def sweep_prompt(schematic_path: str, param: str, sweep_range: str) -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message(
                "qspice_sweep_design",
                schematic_path=schematic_path,
                param=param,
                sweep_range=sweep_range,
            )
        )

    loop_name, loop_title, loop_description = _meta("qspice_smps_loop_gain")

    @app.prompt(name=loop_name, title=loop_title, description=loop_description)
    def smps_loop_gain_prompt(
        schematic_path: str,
        perturbation_source: str = "Vinj",
        settling_time: str = "2m",
    ) -> list[dict[str, object]]:
        return _messages_from_text(
            render_prompt_message(
                "qspice_smps_loop_gain",
                schematic_path=schematic_path,
                perturbation_source=perturbation_source,
                settling_time=settling_time,
            )
        )


__all__ = ["register_prompts"]
