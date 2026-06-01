"""Tests for the list_measures service."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import TYPE_CHECKING

from qspice_mcp.services.waveform.list_measures import list_measures
from qspice_mcp.services.waveform.read_log import LogInspection, LogMeasurement, LogStepVariable

if TYPE_CHECKING:
    import pytest

measure_service = importlib.import_module("qspice_mcp.services.waveform.list_measures")


def test_list_measures_summarizes_measure_blocks(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "demo.log"
    resolved_meas_path = tmp_path / "demo.meas"

    def fake_read_log(
        raw_path: str | Path,
        *,
        workspace_root: Path,
        settings: object | None = None,
        max_lines: int = 80,
        include_measures: bool = True,
        refresh_measures: bool = True,
        meas_path: str | Path | None = None,
    ) -> LogInspection:
        del settings, max_lines, include_measures, refresh_measures, meas_path
        assert Path(raw_path) == log_path
        assert workspace_root == tmp_path.resolve(strict=False)
        return LogInspection(
            log_path=log_path.resolve(strict=False),
            line_count=0,
            excerpt="",
            step_count=2,
            step_variables=(LogStepVariable(name="vin", values=(10, 12)),),
            measures=(
                LogMeasurement(
                    name="vmax",
                    analysis="tran",
                    expression="MAX V(out)",
                    columns=("step", "vmax"),
                    rows=((1, 3.2), (2, 3.4)),
                ),
            ),
            meas_path=resolved_meas_path.resolve(strict=False),
            qpost_command=None,
        )

    monkeypatch.setattr(measure_service, "read_log", fake_read_log)

    result = list_measures(log_path, workspace_root=tmp_path)

    assert result.measure_count == 1
    assert result.step_count == 2
    assert result.measures[0].name == "vmax"
    assert result.measures[0].value_columns == ("vmax",)
    assert result.measures[0].row_count == 2
    assert result.measures[0].stepped is True


def test_list_measures_forwards_timeout_to_read_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "demo.log"

    def fake_read_log(
        raw_path: str | Path,
        *,
        workspace_root: Path,
        settings: object | None = None,
        max_lines: int = 80,
        include_measures: bool = True,
        refresh_measures: bool = True,
        meas_path: str | Path | None = None,
        timeout_s: float | None = None,
    ) -> LogInspection:
        del settings, max_lines, include_measures, refresh_measures, meas_path
        assert Path(raw_path) == log_path
        assert workspace_root == tmp_path.resolve(strict=False)
        assert timeout_s == 2.0
        return LogInspection(
            log_path=log_path.resolve(strict=False),
            line_count=0,
            excerpt="",
            step_count=0,
            step_variables=(),
            measures=(),
            meas_path=None,
            qpost_command=None,
        )

    monkeypatch.setattr(measure_service, "read_log", fake_read_log)

    result = list_measures(log_path, workspace_root=tmp_path, timeout_s=2.0)

    assert result.measure_count == 0
