"""Tests for the read_measures service."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from qspice_mcp.services.waveform.read_log import LogInspection, LogMeasurement, LogStepVariable
from qspice_mcp.services.waveform.read_measures import read_measures

measure_service = importlib.import_module("qspice_mcp.services.waveform.read_measures")


def test_read_measures_filters_rows_by_step_filters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    log_path = tmp_path / "demo.log"
    tmp_path / "demo.meas"

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
        del settings, max_lines, include_measures, refresh_measures
        assert Path(raw_path) == log_path
        assert workspace_root == tmp_path.resolve(strict=False)
        _meas_path = meas_path.resolve(strict=False) if meas_path is not None else None
        return LogInspection(
            log_path=log_path.resolve(strict=False),
            line_count=0,
            excerpt="",
            step_count=2,
            step_variables=(LogStepVariable(name="vin", values=(10, 12)),),
            measures=(
                LogMeasurement(
                    name="delay",
                    analysis="tran",
                    expression="TRIG V(out)",
                    columns=("step", "delay", "delay_1"),
                    rows=((1, 0.1, 0.2), (2, 0.3, 0.4)),
                ),
            ),
            meas_path=_meas_path,
            qpost_command=None,
        )

    monkeypatch.setattr(measure_service, "read_log", fake_read_log)

    result = read_measures(
        log_path,
        workspace_root=tmp_path,
        measures=("delay",),
        step_filters={"VIN": 12},
    )

    assert result.resolved_step == 1
    assert len(result.measures) == 1
    assert result.measures[0].name == "delay"
    assert result.measures[0].value_columns == ("delay", "delay_1")
    assert result.measures[0].rows == (
        measure_service.MeasureRow(step=1, values={"delay": 0.3, "delay_1": 0.4}),
    )


def test_read_measures_rejects_unknown_measure_name(
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
    ) -> LogInspection:
        del (
            raw_path,
            workspace_root,
            settings,
            max_lines,
            include_measures,
            refresh_measures,
            meas_path,
        )
        return LogInspection(
            log_path=log_path.resolve(strict=False),
            line_count=0,
            excerpt="",
            step_count=0,
            step_variables=(),
            measures=(
                LogMeasurement(
                    name="vmax",
                    analysis="tran",
                    expression="MAX V(out)",
                    columns=("vmax",),
                    rows=((3.2,),),
                ),
            ),
            meas_path=None,
            qpost_command=None,
        )

    monkeypatch.setattr(measure_service, "read_log", fake_read_log)

    with pytest.raises(ValueError, match=r"Requested measure\(s\) were not found"):
        read_measures(log_path, workspace_root=tmp_path, measures=("delay",))


def test_read_measures_forwards_timeout_to_read_log(
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
        assert timeout_s == 3.0
        return LogInspection(
            log_path=log_path.resolve(strict=False),
            line_count=0,
            excerpt="",
            step_count=0,
            step_variables=(),
            measures=(
                LogMeasurement(
                    name="vmax",
                    analysis="tran",
                    expression="MAX V(out)",
                    columns=("vmax",),
                    rows=((3.2,),),
                ),
            ),
            meas_path=None,
            qpost_command=None,
        )

    monkeypatch.setattr(measure_service, "read_log", fake_read_log)

    result = read_measures(
        log_path,
        workspace_root=tmp_path,
        measures=("vmax",),
        timeout_s=3.0,
    )

    assert result.measures[0].rows == (measure_service.MeasureRow(step=None, values={"vmax": 3.2}),)
