"""QSpice MCP package.

Public re-exports are intentionally narrow: the base error type plus the
package version. Anything beyond that should be imported from its
subpackage (``qspice_mcp.core``, ``qspice_mcp.services``,
``qspice_mcp.mcp``) so this top-level surface stays stable as the rest of
the package evolves.
"""

from __future__ import annotations

from qspice_mcp.core.exceptions import QSpiceError

__all__ = [
    "QSpiceError",
    "__version__",
]

__version__ = "0.0.1"
