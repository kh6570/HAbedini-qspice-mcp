"""Tests for waveform merge export."""

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
from qspice_mcp.services.artifacts.merge_waveforms import merge_waveforms
from qspice_mcp.services.waveform.list_steps import list_steps

raw_write_helpers = importlib.import_module("qspice_mcp.services.artifacts._raw_write")
REPO_ROOT = Path(__file__).resolve().parents[4]
BODE_RAW_FIXTURE = REPO_ROOT / "tmp" / "bode_probe_only" / "bode-only.qraw"


def _write_step_log(raw_path: Path) -> None:
    raw_path.with_suffix(".log").write_text(
        " 1 of 2 steps: .step temp=25\n 2 of 2 steps: .step temp=85\n",
        encoding="utf-8",
    )


def _write_real_stepped_source_raw(
    raw_path: Path,
    *,
    step0_values: list[float],
    step1_values: list[float],
) -> None:
    raw_write_helpers.write_stepped_raw(
        destination=raw_path,
        plot_name="Transient Analysis",
        axis_name_value="time",
        steps=(
            raw_write_helpers.RawStepBlock(
                axis_values=np.array([0.0, 1.0, 2.0], dtype=float),
                traces=(
                    raw_write_helpers.RawTraceSeries(
                        trace_name="V(out)",
                        source_signal="V(out)",
                        values=np.array(step0_values, dtype=float),
                    ),
                ),
            ),
            raw_write_helpers.RawStepBlock(
                axis_values=np.array([0.0, 1.0], dtype=float),
                traces=(
                    raw_write_helpers.RawTraceSeries(
                        trace_name="V(out)",
                        source_signal="V(out)",
                        values=np.array(step1_values, dtype=float),
                    ),
                ),
            ),
        ),
    )
    _write_step_log(raw_path)


def _write_complex_stepped_source_raw(
    raw_path: Path,
    *,
    step0_values: list[complex],
    step1_values: list[complex],
) -> None:
    raw_write_helpers.write_stepped_raw(
        destination=raw_path,
        plot_name="AC Analysis",
        axis_name_value="frequency",
        steps=(
            raw_write_helpers.RawStepBlock(
                axis_values=np.array([10.0, 100.0], dtype=float),
                traces=(
                    raw_write_helpers.RawTraceSeries(
                        trace_name="OpenLoopGain",
                        source_signal="OpenLoopGain",
                        values=np.array(step0_values, dtype=np.complex128),
                    ),
                ),
            ),
            raw_write_helpers.RawStepBlock(
                axis_values=np.array([10.0, 1000.0], dtype=float),
                traces=(
                    raw_write_helpers.RawTraceSeries(
                        trace_name="OpenLoopGain",
                        source_signal="OpenLoopGain",
                        values=np.array(step1_values, dtype=np.complex128),
                    ),
                ),
            ),
        ),
    )
    _write_step_log(raw_path)


def test_merge_waveforms_round_trips_multiple_inputs(tmp_path: Path) -> None:
    raw_a = tmp_path / "source-a.qraw"
    writer_a = _spice_lib.RawWrite(plot_name="Transient Analysis")
    writer_a.add_trace(
        _spice_lib.Trace("time", np.array([0.0, 1.0, 2.0], dtype=float), whattype="time")
    )
    writer_a.add_trace(
        _spice_lib.Trace("V(out)", np.array([1.0, 2.0, 3.0], dtype=float), whattype="voltage")
    )
    writer_a.save(raw_a)

    raw_b = tmp_path / "source-b.qraw"
    writer_b = _spice_lib.RawWrite(plot_name="Transient Analysis")
    writer_b.add_trace(
        _spice_lib.Trace("time", np.array([0.0, 1.0, 2.0], dtype=float), whattype="time")
    )
    writer_b.add_trace(
        _spice_lib.Trace("V(out)", np.array([4.0, 5.0, 6.0], dtype=float), whattype="voltage")
    )
    writer_b.save(raw_b)

    merged = merge_waveforms(
        [
            {"raw_path": raw_a, "signal": "V(out)", "label": "baseline"},
            {"raw_path": raw_b, "signal": "V(out)", "label": "candidate"},
        ],
        workspace_root=tmp_path,
    )
    baseline = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="baseline",
    )
    candidate = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="candidate",
    )

    assert merged.output_path.suffix.lower() == ".qraw"
    assert merged.input_count == 2
    assert merged.trace_names == ("baseline", "candidate")
    assert baseline.y.tolist() == [1.0, 2.0, 3.0]
    assert candidate.y.tolist() == [4.0, 5.0, 6.0]


def test_merge_waveforms_round_trips_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_a = tmp_path / "source-a.qraw"
    writer_a = _spice_lib.RawWrite(plot_name="Transient Analysis")
    writer_a.add_trace(
        _spice_lib.Trace("time", np.array([0.0, 1.0, 2.0], dtype=float), whattype="time")
    )
    writer_a.add_trace(
        _spice_lib.Trace("V(out)", np.array([1.0, 2.0, 3.0], dtype=float), whattype="voltage")
    )
    writer_a.save(raw_a)

    raw_b = tmp_path / "source-b.qraw"
    writer_b = _spice_lib.RawWrite(plot_name="Transient Analysis")
    writer_b.add_trace(
        _spice_lib.Trace("time", np.array([0.0, 1.0, 2.0], dtype=float), whattype="time")
    )
    writer_b.add_trace(
        _spice_lib.Trace("V(out)", np.array([4.0, 5.0, 6.0], dtype=float), whattype="voltage")
    )
    writer_b.save(raw_b)

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    merged = merge_waveforms(
        [
            {"raw_path": raw_a, "signal": "V(out)", "label": "baseline"},
            {"raw_path": raw_b, "signal": "V(out)", "label": "candidate"},
        ],
        workspace_root=tmp_path,
    )
    baseline = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="baseline",
    )
    candidate = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="candidate",
    )
    header_text = merged.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert "Title: * qspice_mcp clean-room raw writer" in header_text
    assert baseline.y.tolist() == [1.0, 2.0, 3.0]
    assert candidate.y.tolist() == [4.0, 5.0, 6.0]


def test_merge_waveforms_frequency_round_trips_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / BODE_RAW_FIXTURE.name
    copy2(BODE_RAW_FIXTURE, raw_path)

    magnitude = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="magnitude",
    )
    phase = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="phase",
    )

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    merged = merge_waveforms(
        [
            {
                "raw_path": raw_path,
                "signal": "OpenLoopGain",
                "label": "baseline",
                "component": "magnitude",
            },
            {
                "raw_path": raw_path,
                "signal": "OpenLoopGain",
                "label": "candidate",
                "component": "phase",
            },
        ],
        workspace_root=tmp_path,
    )
    baseline = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="baseline",
    )
    candidate = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="candidate",
    )
    header_text = merged.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert merged.plot_name == "Frequency Response Analysis"
    assert "Plotname: Frequency Response Analysis" in header_text
    assert baseline.axis_name is not None
    assert baseline.axis_name.lower() == "frequency"
    assert baseline.x.tolist() == pytest.approx(magnitude.x.tolist())
    assert baseline.y.tolist() == pytest.approx(magnitude.y.tolist())
    assert candidate.y.tolist() == pytest.approx(phase.y.tolist())


def test_merge_waveforms_frequency_preserves_native_complex_without_rawwrite_backend(
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
    source_phase = load_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="phase",
    )

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    merged = merge_waveforms(
        [
            {
                "raw_path": raw_path,
                "signal": "OpenLoopGain",
                "label": "baseline",
            },
            {
                "raw_path": raw_path,
                "signal": "OpenLoopGain",
                "label": "candidate",
            },
        ],
        workspace_root=tmp_path,
    )
    baseline_real = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="baseline",
        component="real",
    )
    baseline_phase = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="baseline",
        component="phase",
    )
    candidate_imag = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="candidate",
        component="imag",
    )
    header_text = merged.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert merged.plot_name == "AC Analysis"
    assert merged.trace_names == ("baseline", "candidate")
    assert merged.components == ("auto", "auto")
    assert "Flags: complex" in header_text
    assert baseline_real.axis_name is not None
    assert baseline_real.axis_name.lower() == "frequency"
    assert baseline_real.x.tolist() == pytest.approx(source_real.x.tolist())
    assert baseline_real.y.tolist() == pytest.approx(source_real.y.tolist())
    assert baseline_phase.y.tolist() == pytest.approx(source_phase.y.tolist())
    assert candidate_imag.y.tolist() == pytest.approx(source_imag.y.tolist())


def test_merge_waveforms_all_steps_round_trips_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_a = tmp_path / "source-a.qraw"
    _write_real_stepped_source_raw(
        raw_a,
        step0_values=[1.0, 2.0, 3.0],
        step1_values=[5.0, 6.0],
    )

    raw_b = tmp_path / "source-b.qraw"
    _write_real_stepped_source_raw(
        raw_b,
        step0_values=[10.0, 11.0, 12.0],
        step1_values=[20.0, 21.0],
    )

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    merged = merge_waveforms(
        [
            {"raw_path": raw_a, "signal": "V(out)", "label": "baseline"},
            {"raw_path": raw_b, "signal": "V(out)", "label": "candidate"},
        ],
        workspace_root=tmp_path,
        all_steps=True,
    )
    baseline_step_0 = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="baseline",
        step=0,
    )
    candidate_step_1 = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="candidate",
        step=1,
    )
    step_catalog = list_steps(merged.output_path, workspace_root=tmp_path)
    header_text = merged.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert merged.step is None
    assert merged.step_count == 2
    assert merged.resolved_steps == (0, 1)
    assert merged.output_log_path == merged.output_path.with_suffix(".log").resolve(strict=False)
    assert merged.output_log_path is not None
    assert merged.output_log_path.is_file()
    assert merged.trace_names == ("baseline", "candidate")
    assert "Flags: real stepped fastaccess" in header_text
    assert step_catalog.step_count == 2
    assert step_catalog.steps[0].values == {"temp": 25}
    assert step_catalog.steps[1].values == {"temp": 85}
    assert baseline_step_0.axis_name is not None
    assert baseline_step_0.axis_name.lower() == "time"
    assert baseline_step_0.y.tolist() == [1.0, 2.0, 3.0]
    assert candidate_step_1.y.tolist() == [20.0, 21.0]


def test_merge_waveforms_all_steps_preserves_native_complex_without_rawwrite_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_a = tmp_path / "source-a.qraw"
    _write_complex_stepped_source_raw(
        raw_a,
        step0_values=[1.0 + 2.0j, 2.0 + 4.0j],
        step1_values=[3.0 + 1.0j, 4.0 + 0.5j],
    )

    raw_b = tmp_path / "source-b.qraw"
    _write_complex_stepped_source_raw(
        raw_b,
        step0_values=[5.0 - 1.0j, 6.0 - 2.0j],
        step1_values=[7.0 - 3.0j, 8.0 - 4.0j],
    )

    monkeypatch.setattr(raw_write_helpers, "load_rawwrite_api", lambda: (None, None, None))

    merged = merge_waveforms(
        [
            {"raw_path": raw_a, "signal": "OpenLoopGain", "label": "baseline"},
            {"raw_path": raw_b, "signal": "OpenLoopGain", "label": "candidate"},
        ],
        workspace_root=tmp_path,
        all_steps=True,
    )
    baseline_real_step_0 = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="baseline",
        step=0,
        component="real",
    )
    candidate_phase_step_1 = load_waveform(
        merged.output_path,
        workspace_root=tmp_path,
        signal="candidate",
        step=1,
        component="phase",
    )
    header_text = merged.output_path.read_bytes().decode("utf_16_le", errors="ignore")

    assert merged.plot_name == "AC Analysis"
    assert merged.step is None
    assert merged.step_count == 2
    assert merged.components == ("auto", "auto")
    assert "Flags: complex stepped" in header_text
    assert baseline_real_step_0.axis_name is not None
    assert baseline_real_step_0.axis_name.lower() == "frequency"
    assert baseline_real_step_0.y.tolist() == pytest.approx([1.0, 2.0])
    assert candidate_phase_step_1.y.tolist() == pytest.approx(
        np.angle(np.array([7.0 - 3.0j, 8.0 - 4.0j]), deg=True).tolist()
    )


def test_merge_waveforms_all_steps_rejects_per_input_step(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="all_steps"):
        merge_waveforms(
            [{"raw_path": "source.qraw", "signal": "V(out)", "step": 0}],
            workspace_root=tmp_path,
            all_steps=True,
        )
