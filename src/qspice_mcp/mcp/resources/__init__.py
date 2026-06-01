"""MCP resource metadata and bundled markdown bodies."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files

_RESOURCE_BODY_FILES: dict[str, str] = {
    "guidelines://qspice-artifacts": "qspice-artifacts.md",
    "guidelines://qspice-measurements": "qspice-measurements.md",
}


@dataclass(frozen=True, slots=True)
class ResourceDefinition:
    """Metadata for a resource exposed by the MCP layer."""

    name: str
    uri: str
    description: str
    mime_type: str = "text/markdown"


def get_resource_definitions() -> tuple[ResourceDefinition, ...]:
    """Return the planned resource definitions for the server."""

    return (
        ResourceDefinition(
            name="qspice_artifact_model",
            uri="guidelines://qspice-artifacts",
            description="Explains the qsch-first artifact model and the role of derived outputs.",
        ),
        ResourceDefinition(
            name="qspice_measurement_guidance",
            uri="guidelines://qspice-measurements",
            description="Documents the intended measurement and waveform-budget conventions.",
        ),
    )


@lru_cache(maxsize=1)
def _resource_content_map() -> dict[str, str]:
    """Load bundled markdown bodies for registered MCP resources."""

    package_root = files(__name__)
    return {
        uri: (package_root / file_name).read_text(encoding="utf-8")
        for uri, file_name in _RESOURCE_BODY_FILES.items()
    }


def get_resource_content(uri: str) -> str | None:
    """Return bundled markdown content for one resource URI when available."""

    return _resource_content_map().get(uri)


__all__ = ["ResourceDefinition", "get_resource_content", "get_resource_definitions"]
