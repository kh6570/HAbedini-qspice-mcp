"""Tests for the list_steps service."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2
from typing import TYPE_CHECKING

from qspice_mcp.services.waveform.list_steps import list_steps

if TYPE_CHECKING:
    import pytest

step_service = importlib.import_module("qspice_mcp.services.waveform.list_steps")
waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "qraw"
EXTERNAL_STEPPED_RAW_FIXTURE = FIXTURE_ROOT / "external-stepped-tran.qraw"
EXTERNAL_STEPPED_LOG_FIXTURE = FIXTURE_ROOT / "external-stepped-tran.log"


class FakeRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose

    def get_trace_names(self) -> list[str]:
        return ["time", "V(out)"]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(2)

    def has_axis(self) -> bool:
        return True

    def get_axis(self, step: int = 0) -> list[float]:
        del step
        return [0.0, 1.0]

    def get_wave(self, trace_ref: str | int, step: int = 0) -> list[float]:
        del trace_ref, step
        return [0.0, 1.0]

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_list_steps_uses_sibling_log_metadata(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    log_path = tmp_path / "demo.log"
    log_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )
    log_path.write_text(
        " 1 of 2 steps: .step vin=10 temp=25\n 2 of 2 steps: .step vin=12 temp=50\n",
        encoding="utf-8",
    )

    result = list_steps(raw_path, workspace_root=tmp_path)

    assert result.step_count == 2
    assert result.log_path == log_path.resolve(strict=False)
    assert result.step_variables[0].name == "vin"
    assert result.steps[0].index == 0
    assert result.steps[0].values == {"vin": 10, "temp": 25}
    assert result.steps[1].values == {"vin": 12, "temp": 50}


def test_list_steps_warns_without_sibling_log(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    result = list_steps(raw_path, workspace_root=tmp_path)

    assert result.log_path is None
    assert result.step_count == 2
    assert result.steps[0].values == {}
    assert "No sibling .log file" in result.warnings[0]


def test_list_steps_reads_external_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / EXTERNAL_STEPPED_RAW_FIXTURE.name
    log_path = tmp_path / EXTERNAL_STEPPED_LOG_FIXTURE.name
    copy2(EXTERNAL_STEPPED_RAW_FIXTURE, raw_path)
    copy2(EXTERNAL_STEPPED_LOG_FIXTURE, log_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = list_steps(raw_path, workspace_root=tmp_path)

    assert result.log_path == log_path.resolve(strict=False)
    assert result.step_count == 2
    assert result.steps[0].values == {"vin": 10, "temp": 25}
    assert result.steps[1].values == {"vin": 12, "temp": 50}
