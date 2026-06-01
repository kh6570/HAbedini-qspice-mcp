"""Tests for data budgets."""

from __future__ import annotations

import pytest

from qspice_mcp.core.budgets import DataBudget


def test_budget_fits_when_under_both_limits() -> None:
    budget = DataBudget(max_points=10, max_bytes=1024)
    assert budget.fits(10)


def test_budget_rejects_point_overflow() -> None:
    budget = DataBudget(max_points=9, max_bytes=1024)
    assert not budget.fits(10)


def test_budget_rejects_byte_overflow() -> None:
    budget = DataBudget(max_points=200, max_bytes=1024)
    assert not budget.fits(200)


def test_budget_target_points_respects_byte_limit() -> None:
    budget = DataBudget(max_points=200, max_bytes=1024)
    assert budget.target_points(1000) == 128


@pytest.mark.parametrize(
    ("max_points", "max_bytes", "message"),
    [
        (2, 64_000, "max_points must be >= 3"),
        (2000, 512, "max_bytes must be >= 1024"),
    ],
)
def test_budget_validation(max_points: int, max_bytes: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        DataBudget(max_points=max_points, max_bytes=max_bytes)
