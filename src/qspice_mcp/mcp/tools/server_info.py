"""Server-level introspection tool handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from qspice_mcp.mcp.capabilities import (
    describe_server_capabilities as describe_server_capabilities_runtime,
)

from .shared import to_json_object

if TYPE_CHECKING:
    from ._protocols import SupportsToolCatalogRuntime as _RuntimeWithToolCatalog
else:
    _RuntimeWithToolCatalog = object

SERVER_INFO_HANDLER_NAMES = ("describe_server_capabilities",)


class ServerInfoToolMixin:
    """Handlers for server-level capability discovery."""

    def describe_server_capabilities(self: _RuntimeWithToolCatalog) -> dict[str, object]:
        return to_json_object(
            describe_server_capabilities_runtime(settings=self.settings, tools=self.tools)
        )


__all__ = ["SERVER_INFO_HANDLER_NAMES", "ServerInfoToolMixin"]
