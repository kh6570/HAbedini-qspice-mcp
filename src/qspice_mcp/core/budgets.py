# In the name of God, the Most Gracious, the Most Merciful
"""Size budgets. The limits are implemented in mcp-app-core."""

from __future__ import annotations

from mcp_app_core.budgets import DataBudget as _CoreBudget
from mcp_app_core.budgets import DownsampleStrategy
from mcp_app_core.errors import ValidationError as _CoreValidationError

from qspice_mcp.core.exceptions import ValidationError

__all__ = ["DEFAULT_BUDGET", "DataBudget", "DownsampleStrategy"]


class DataBudget(_CoreBudget):
    """Budget that raises QSpice validation errors."""

    def __post_init__(self) -> None:
        try:
            super().__post_init__()
        except _CoreValidationError as exc:
            raise ValidationError(str(exc)) from exc


DEFAULT_BUDGET = DataBudget()
