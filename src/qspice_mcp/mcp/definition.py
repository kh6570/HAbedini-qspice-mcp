"""Server metadata used by the MCP bootstrap layer."""

from __future__ import annotations

from dataclasses import dataclass

from qspice_mcp.infra.config import QSpiceFeatures


@dataclass(frozen=True, slots=True)
class ServerParameter:
    """A user-configurable server parameter."""

    name: str
    description: str
    env_var: str | None = None
    required: bool = False


@dataclass(frozen=True, slots=True)
class ServerDefinition:
    """Top-level description of the qspice MCP server."""

    name: str
    title: str
    instructions: str
    features: QSpiceFeatures
    parameters: tuple[ServerParameter, ...]


def build_server_definition(features: QSpiceFeatures | None = None) -> ServerDefinition:
    """Return the current server definition used by the bootstrap layer."""

    return ServerDefinition(
        name="qspice-mcp",
        title="QSpice MCP Server",
        instructions=(
            "Treat .qsch files as the source of truth, keep netlists and waveform "
            "artifacts derived, and prefer bounded signal summaries over raw dumps."
        ),
        features=features or QSpiceFeatures(),
        parameters=(
            ServerParameter(
                name="qspice-exe",
                description="Absolute path to the QSpice executable.",
                env_var="QSPICE_EXE",
            ),
            ServerParameter(
                name="workspace-root",
                description=(
                    "Workspace root used to resolve relative paths and sandbox file access."
                ),
            ),
            ServerParameter(
                name="log-level",
                description="Minimum structured log level.",
                env_var="QSPICE_LOG_LEVEL",
            ),
        ),
    )
