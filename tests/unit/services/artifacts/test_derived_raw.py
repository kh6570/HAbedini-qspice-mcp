"""Tests for derived raw export."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2

import numpy as np
import pytest

# Load the optional waveform-writing backend (may be qspice or a compatible package).
pytest.skip("No waveform-write backend available", allow_module_level=True)
# ruff: noqa: E402, F821

from qspice_mcp.services._backends.waveform import load_waveform
from qspice_mcp.services.artifacts.export_derived_raw import export_derived_raw
from qspice_mcp.services.waveform.list_steps import list_steps

raw_write_helpers = importlib.import_module("qspice_mcp.services.artifacts._raw_write")
waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
BODE_RAW_FIXTURE = REPO_ROOT / "tmp" / "bode_probe_only" / "bode-only.qraw"


class FakeSteppedRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axes = {
            0: np.array([0.0, 0.5, 1.0], dtype=np.float64),
            1: np.array([0.0, 1.0], dtype=np.float64),
        }
        self._waves = {
            0: {"V(out)": np.array([1.0, 2.0, 3.0], dtype=np.float64)},
            1: {"V(out)": np.array([5.0, 6.0], dtype=np.float64)},
        }

    def get_trace_names(self) -> list[str]:
        return ["time", "V(out)"]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(2)

    def has_axis(self) -> bool:
        return True

    def get_axis(self, step: int = 0) -> np.ndarray:
        return self._axes[step]

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        if trace_ref == "time":
            return self._axes[step]
        return self._waves[step][trace_ref]

    def get_plot_name(self) -> str:
        return "Transient Analysis"


class FakeComplexSteppedRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axes = {
            0: np.array([10.0, 100.0, 1_000.0], dtype=np.float64),
            1: np.array([10.0, 50.0], dtype=np.float64),
        }
        self._waves = {
            0: {
                "OpenLoopGain": np.array(
                    [1.0 + 2.0j, 3.0 + 4.0j, 5.0 + 6.0j],
                    dtype=np.complex128,
                )
            },
            1: {
                "OpenLoopGain": np.array(
                    [7.0 + 8.0j, 9.0 + 10.0j],
                    dtype=np.complex128,
                )
            },
        }

    def get_trace_names(self) -> list[str]:
        return ["frequency", "OpenLoopGain"]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(2)

    def has_axis(self) -> bool:
        return True

    def get_axis(self, step: int = 0) -> np.ndarray:
        return self._axes[step]

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        if trace_ref == "frequency":
            return self._axes[step]
        return self._waves[step][trace_ref]

    def get_plot_name(self) -> str:
        return "AC Analysis"


def test_export_derived_raw_round_trips_filtered_waveform(tmp_path: Path) -> None:
    raw_path = tmp_path / "source.qraw"
    writer = _spice_lib.RawWrite(plot_name="Transient Analysis")
    writer.add_trace(
        _spice_lib.Trace("time", np.array([0.0, 1.0, 2.0, 3.0], dtype=float), whattype="time")
    )
    writer.add_trace(
        _spice_lib.Trace(
            "V(out)",
            np.array([0.5, 1.5, 2.5, 3.5], dtype=float),
            whattype="voltage",
        )
    )
    writer.save(raw_path)

    exported = export_derived_raw(
        raw_path,
        workspace_root=tmp_path,
        signals=["V(out)"],
        t_start=1.0,
        t_end=2.0,
    )
    round_tripped = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="V(out)",
    )

    assert exported.output_path.suffix.lower() == ".qraw"
    assert exported.point_count == 2
    assert exported.trace_names == ("V(out)",)
    assert round_tripped.x.tolist() == [1.0, 2.0]
    assert round_tripped.y.tolist() == [1.5, 2.5]


def test_export_derived_raw_round_trips_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "source.qraw"
    writer = _spice_lib.RawWrite(plot_name="Transient Analysis")
    writer.add_trace(
        _spice_lib.Trace(
            "time",
            np.array([0.0, 1.0, 2.0], dtype=float),
            whattype="time",
        )
    )
    writer.add_trace(
        _spice_lib.Trace(
            "V(out)",
            np.array([1.0, 2.0, 3.0], dtype=float),
            whattype="voltage",
        )
    )
    writer.save(raw_path)

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    exported = export_derived_raw(
        raw_path,
        workspace_root=tmp_path,
        signals=["V(out)"],
    )
    round_tripped = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="V(out)",
    )
    header_text = exported.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert "Title: * qspice_mcp clean-room raw writer" in header_text
    assert round_tripped.x.tolist() == [0.0, 1.0, 2.0]
    assert round_tripped.y.tolist() == [1.0, 2.0, 3.0]


def test_export_derived_raw_frequency_round_trips_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / BODE_RAW_FIXTURE.name
    copy2(BODE_RAW_FIXTURE, raw_path)

    source = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="magnitude",
    )

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    exported = export_derived_raw(
        raw_path,
        workspace_root=tmp_path,
        signals=["OpenLoopGain"],
        component="magnitude",
    )
    round_tripped = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal=exported.trace_names[0],
    )
    header_text = exported.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert exported.plot_name == "Frequency Response Analysis"
    assert "Plotname: Frequency Response Analysis" in header_text
    assert round_tripped.axis_name is not None
    assert round_tripped.axis_name.lower() == "frequency"
    assert round_tripped.x.tolist() == pytest.approx(source.x.tolist())
    assert round_tripped.y.tolist() == pytest.approx(source.y.tolist())


def test_export_derived_raw_frequency_preserves_native_complex_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / BODE_RAW_FIXTURE.name
    copy2(BODE_RAW_FIXTURE, raw_path)

    source_real = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="real",
    )
    source_imag = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="imag",
    )
    source_magnitude = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="magnitude",
    )
    source_phase = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="phase",
    )

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    exported = export_derived_raw(
        raw_path,
        workspace_root=tmp_path,
        signals=["OpenLoopGain"],
    )
    exported_real = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="real",
    )
    exported_imag = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="imag",
    )
    exported_magnitude = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="magnitude",
    )
    exported_phase = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="phase",
    )
    header_text = exported.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert exported.plot_name == "AC Analysis"
    assert exported.trace_names == ("OpenLoopGain",)
    assert exported.components == ("auto",)
    assert "Flags: complex" in header_text
    assert exported_real.x.tolist() == pytest.approx(source_real.x.tolist())
    assert exported_real.y.tolist() == pytest.approx(source_real.y.tolist())
    assert exported_imag.y.tolist() == pytest.approx(source_imag.y.tolist())
    assert exported_magnitude.y.tolist() == pytest.approx(source_magnitude.y.tolist())
    assert exported_phase.y.tolist() == pytest.approx(source_phase.y.tolist())


def test_export_derived_raw_all_steps_round_trips_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "source.qraw"
    raw_path.write_text("", encoding="utf-8")
    raw_path.with_suffix(".log").write_text(
        " 1 of 2 steps: .step vin=10 temp=25\n 2 of 2 steps: .step vin=12 temp=50\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        waveform_backend,
        "_load_rawread_factory",
        lambda: (FakeSteppedRawRead, "fake-backend"),
    )
    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    exported = export_derived_raw(
        raw_path,
        workspace_root=tmp_path,
        signals=["V(out)"],
        all_steps=True,
    )
    step_catalog = list_steps(exported.output_path, workspace_root=tmp_path)
    step0 = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="V(out)",
        step=0,
    )
    step1 = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="V(out)",
        step=1,
    )
    header_text = exported.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert exported.step is None
    assert exported.step_count == 2
    assert exported.resolved_steps == (0, 1)
    assert exported.point_count == 5
    assert exported.output_log_path == exported.output_path.with_suffix(".log")
    assert exported.output_log_path.is_file()
    assert "Flags: real stepped fastaccess" in header_text
    assert step_catalog.step_count == 2
    assert step_catalog.steps[0].values == {"vin": 10, "temp": 25}
    assert step_catalog.steps[1].values == {"vin": 12, "temp": 50}
    assert step0.x.tolist() == pytest.approx([0.0, 0.5, 1.0])
    assert step0.y.tolist() == pytest.approx([1.0, 2.0, 3.0])
    assert step1.x.tolist() == pytest.approx([0.0, 1.0])
    assert step1.y.tolist() == pytest.approx([5.0, 6.0])


def test_export_derived_raw_all_steps_preserves_native_complex_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "source-ac.qraw"
    raw_path.write_text("", encoding="utf-8")
    raw_path.with_suffix(".log").write_text(
        " 1 of 2 steps: .step corner=slow\n 2 of 2 steps: .step corner=fast\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        waveform_backend,
        "_load_rawread_factory",
        lambda: (FakeComplexSteppedRawRead, "fake-backend"),
    )
    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    exported = export_derived_raw(
        raw_path,
        workspace_root=tmp_path,
        signals=["OpenLoopGain"],
        all_steps=True,
    )
    step_catalog = list_steps(exported.output_path, workspace_root=tmp_path)
    step0_magnitude = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=0,
        component="magnitude",
    )
    step0_phase = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=0,
        component="phase",
    )
    step1_magnitude = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=1,
        component="magnitude",
    )
    step1_phase = load_waveform(
        exported.output_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=1,
        component="phase",
    )
    header_text = exported.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert exported.step is None
    assert exported.step_count == 2
    assert exported.trace_names == ("OpenLoopGain",)
    assert exported.components == ("auto",)
    assert exported.output_log_path == exported.output_path.with_suffix(".log")
    assert exported.output_log_path.is_file()
    assert "Flags: complex stepped" in header_text
    assert step_catalog.step_count == 2
    assert step_catalog.steps[0].values == {"corner": "slow"}
    assert step_catalog.steps[1].values == {"corner": "fast"}
    assert step0_magnitude.x.tolist() == pytest.approx([10.0, 100.0, 1_000.0])
    assert step0_magnitude.y.tolist() == pytest.approx(
        np.abs(np.array([1.0 + 2.0j, 3.0 + 4.0j, 5.0 + 6.0j])).tolist()
    )
    assert step0_phase.y.tolist() == pytest.approx(
        np.angle(np.array([1.0 + 2.0j, 3.0 + 4.0j, 5.0 + 6.0j]), deg=True).tolist()
    )
    assert step1_magnitude.x.tolist() == pytest.approx([10.0, 50.0])
    assert step1_magnitude.y.tolist() == pytest.approx(
        np.abs(np.array([7.0 + 8.0j, 9.0 + 10.0j])).tolist()
    )
    assert step1_phase.y.tolist() == pytest.approx(
        np.angle(np.array([7.0 + 8.0j, 9.0 + 10.0j]), deg=True).tolist()
    )
