"""Token and size budgets for data-returning operations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DownsampleStrategy = Literal["lttb", "decimate", "minmax"]
_MIN_POINTS = 3
_MIN_BYTES = 1024


@dataclass(frozen=True, slots=True)
class DataBudget:
    """Limits how much data a tool may return."""

    max_points: int = 2000
    max_bytes: int = 64_000
    strategy: DownsampleStrategy = "lttb"

    def __post_init__(self) -> None:
        if self.max_points < _MIN_POINTS:
            raise ValueError(f"max_points must be >= {_MIN_POINTS}")
        if self.max_bytes < _MIN_BYTES:
            raise ValueError(f"max_bytes must be >= {_MIN_BYTES}")

    def fits(self, n_points: int, dtype_size: int = 8) -> bool:
        """Return True if n_points samples fit within both caps."""
        return n_points <= self.max_points and n_points * dtype_size <= self.max_bytes

    def target_points(self, n_points: int, dtype_size: int = 8) -> int:
        """Compute the largest sample count that fits within both caps."""
        by_points = min(n_points, self.max_points)
        by_bytes = self.max_bytes // dtype_size
        return min(by_points, by_bytes)


DEFAULT_BUDGET = DataBudget()
