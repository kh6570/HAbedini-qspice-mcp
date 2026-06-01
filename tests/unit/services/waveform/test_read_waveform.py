"""Tests for the RawRead-backed read_waveform service."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2

import numpy as np
import pytest

from qspice_mcp.core.budgets import DEFAULT_BUDGET
from qspice_mcp.core.exceptions import BudgetExceededError
from qspice_mcp.services.waveform.read_waveform import read_waveform

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "qraw"
QUX_EXPORT_RAW_FIXTURE = FIXTURE_ROOT / "qux_export_source.qraw"
EXTERNAL_VALUES_RAW_FIXTURE = FIXTURE_ROOT / "external-values.qraw"
EXTERNAL_FASTACCESS_RAW_FIXTURE = FIXTURE_ROOT / "external-fastaccess-ac.qraw"


def _write_supported_external_double_binary_raw(
    destination: Path,
    *,
    plot_name: str,
    axis_name: str,
    signal_name: str,
    points: tuple[tuple[float, float], ...],
) -> None:
    header = (
        "\n".join(
            (
                "Title: * supported external binary raw",
                f"Plotname: {plot_name}",
                "Flags: real forward double",
                "No. Variables: 2",
                f"No. Points: {len(points)}",
                "Variables:",
                f"\t0\t{axis_name}\t{axis_name.lower()}",
                f"\t1\t{signal_name}\tvoltage",
                "Binary:",
            )
        ).encode("ascii")
        + b"\n"
    )
    payload = bytearray()
    for axis_value, trace_value in points:
        payload.extend(np.asarray([axis_value], dtype="<f8").tobytes())
        payload.extend(np.asarray([trace_value], dtype="<f8").tobytes())
    destination.write_bytes(header + payload)


def _write_supported_external_complex_values_raw(
    destination: Path,
    *,
    plot_name: str,
    axis_name: str,
    signal_name: str,
    points: tuple[tuple[float, complex], ...],
) -> None:
    header = "\n".join(
        (
            "Title: * supported external values raw",
            f"Plotname: {plot_name}",
            "Flags: complex forward",
            "No. Variables: 2",
            f"No. Points: {len(points)}",
            "Variables:",
            f"\t0\t{axis_name}\t{axis_name.lower()}",
            f"\t1\t{signal_name}\tvoltage",
            "Values:",
        )
    )
    lines = [header]
    for point_index, (axis_value, trace_value) in enumerate(points):
        lines.append(f"{point_index}\t{axis_value:.16e}")
        lines.append(f"{trace_value.real:.16e},{trace_value.imag:.16e}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


class FakeRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._axis = np.array([0.0, 0.5, 1.0, 1.5, 2.0], dtype=np.float64)
        self._waves = {
            "V(out)": np.array([0.0, 1.0, 2.0, 3.0, 4.0], dtype=np.float64),
            "V(ac)": np.array([1 + 1j, 2 + 2j, 3 + 3j, 4 + 4j, 5 + 5j], dtype=np.complex128),
        }

    def get_trace_names(self) -> list[str]:
        return ["time", *self._waves.keys()]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(1)

    def has_axis(self) -> bool:
        return True

    def get_axis(self, step: int = 0) -> np.ndarray:
        del step
        return self._axis

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        del step
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        if trace_ref == "time":
            return self._axis
        return self._waves[trace_ref]

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_read_waveform_filters_by_axis_window(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    result = read_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="v(out)",
        t_start=0.5,
        t_end=1.5,
        max_points=8,
    )

    assert result.signal == "V(out)"
    assert result.axis_name == "time"
    assert result.component == "real"
    assert result.complex_source is False
    assert result.x_unit == "s"
    assert result.original_point_count == 3
    assert result.point_count == 3
    assert result.downsampled is False
    assert result.x_values == (0.5, 1.0, 1.5)
    assert result.y_values == (1.0, 2.0, 3.0)


def test_read_waveform_reads_external_double_binary_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "external-double-binary.qraw"
    _write_supported_external_double_binary_raw(
        raw_path,
        plot_name="Transient Analysis",
        axis_name="Time",
        signal_name="V(out)",
        points=((0.0, 1.25), (0.5, 2.5), (1.0, 3.75)),
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = read_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
    )

    assert result.axis_name == "Time"
    assert result.component == "real"
    assert result.complex_source is False
    assert result.x_values == pytest.approx((0.0, 0.5, 1.0))
    assert result.y_values == pytest.approx((1.25, 2.5, 3.75))


def test_read_waveform_downsamples_complex_data_with_auto_component(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    result = read_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(ac)",
        max_points=3,
    )

    assert result.component == "magnitude"
    assert result.complex_source is True
    assert result.downsampled is True
    assert result.point_count == 3
    assert result.original_point_count == 5
    assert result.y_values == pytest.approx((2**0.5, 3 * (2**0.5), 5 * (2**0.5)))


def test_read_waveform_rejects_budget_requests_above_response_ceiling(tmp_path: Path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")

    with pytest.raises(
        BudgetExceededError, match="plot_waveforms, export_waveform_csv, or export_derived_raw"
    ):
        read_waveform(
            raw_path,
            workspace_root=tmp_path,
            signal="V(out)",
            max_points=DEFAULT_BUDGET.max_points + 1,
        )


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
            1: np.array([0.0, 1.0, 2.0], dtype=np.float64),
        }
        self._waves = {
            0: {"V(out)": np.array([0.0, 1.0, 2.0], dtype=np.float64)},
            1: {"V(out)": np.array([5.0, 6.0, 7.0], dtype=np.float64)},
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


class FakeAxislessRawRead:
    def __init__(
        self,
        raw_filename: str | Path,
        traces_to_read: None | str | list[str] | tuple[str, ...] = None,
        dialect: str | None = None,
        verbose: bool = True,
    ) -> None:
        del raw_filename, traces_to_read, dialect, verbose
        self._wave = np.array([2.0, 4.0, 6.0], dtype=np.float64)

    def get_trace_names(self) -> list[str]:
        return ["V(out)"]

    def get_steps(self, **kwargs: object) -> range:
        del kwargs
        return range(1)

    def has_axis(self) -> bool:
        return False

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        del step
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        assert trace_ref == "V(out)"
        return self._wave

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_read_waveform_resolves_step_filters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeSteppedRawRead, "fake-backend")
    )
    monkeypatch.setattr(
        waveform_backend,
        "_read_step_variables_for_raw",
        lambda raw_path, *, workspace_root: (
            waveform_backend.LogStepVariable(name="vin", values=(10, 12)),
        ),
    )

    result = read_waveform(
        raw_path, workspace_root=tmp_path, signal="V(out)", step_filters={"vin": 12}
    )

    assert result.step == 1
    assert result.x_values == (0.0, 1.0, 2.0)
    assert result.y_values == (5.0, 6.0, 7.0)


def test_read_waveform_falls_back_to_sample_index_without_axis(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend,
        "_load_rawread_factory",
        lambda: (FakeAxislessRawRead, "fake-backend"),
    )

    result = read_waveform(raw_path, workspace_root=tmp_path, signal="V(out)")

    assert result.axis_name is None
    assert result.x_unit == "index"
    assert result.x_values == (0.0, 1.0, 2.0)
    assert result.y_values == (2.0, 4.0, 6.0)


def test_read_waveform_reads_external_transient_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / QUX_EXPORT_RAW_FIXTURE.name
    copy2(QUX_EXPORT_RAW_FIXTURE, raw_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = read_waveform(raw_path, workspace_root=tmp_path, signal="V(out)")

    assert result.plot_name == "Transient Analysis"
    assert result.axis_name == "Time"
    assert result.component == "real"
    assert result.point_count == 1249
    assert result.x_values[:3] == pytest.approx((0.0, 3.2e-12, 6.4e-12))
    assert result.y_values[-1] == pytest.approx(0.24181295697526017)


def test_read_waveform_reads_external_values_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / EXTERNAL_VALUES_RAW_FIXTURE.name
    copy2(EXTERNAL_VALUES_RAW_FIXTURE, raw_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = read_waveform(raw_path, workspace_root=tmp_path, signal="V(out)")

    assert result.axis_name == "Time"
    assert result.component == "real"
    assert result.x_values == pytest.approx((0.0, 0.5, 1.0))
    assert result.y_values == pytest.approx((1.25, 2.5, 3.75))


def test_read_waveform_reads_external_complex_values_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / "external-complex-values.qraw"
    _write_supported_external_complex_values_raw(
        raw_path,
        plot_name="AC Analysis",
        axis_name="Frequency",
        signal_name="V(out)",
        points=((10.0, 1.0 + 1.0j), (100.0, 1.0 + 1.7320508075688772j)),
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = read_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        component="phase",
    )

    assert result.axis_name == "Frequency"
    assert result.component == "phase"
    assert result.complex_source is True
    assert result.x_values == pytest.approx((10.0, 100.0))
    assert result.y_values == pytest.approx((45.0, 60.0), abs=1e-9)


def test_read_waveform_reads_external_fastaccess_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / EXTERNAL_FASTACCESS_RAW_FIXTURE.name
    copy2(EXTERNAL_FASTACCESS_RAW_FIXTURE, raw_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = read_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        step=1,
        component="phase",
    )

    assert result.plot_name == "AC Analysis"
    assert result.axis_name == "Frequency"
    assert result.component == "phase"
    assert result.x_values == pytest.approx((20.0, 200.0))
    assert result.y_values == pytest.approx((50.19442890773481, 48.81407483429035))
