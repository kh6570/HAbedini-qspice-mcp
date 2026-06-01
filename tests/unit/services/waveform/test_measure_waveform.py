"""Tests for the scalar measure_waveform service."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2

import numpy as np
import pytest

from qspice_mcp.services.waveform.measure_waveform import measure_waveform

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "qraw"
EXTERNAL_VALUES_RAW_FIXTURE = FIXTURE_ROOT / "external-values.qraw"


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


def test_measure_waveform_computes_rms(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    result = measure_waveform(raw_path, workspace_root=tmp_path, signal="V(out)", operation="rms")

    assert result.operation == "rms"
    assert result.component == "real"
    assert result.y_unit == "V"
    assert result.sample_count == 5
    assert result.value == pytest.approx(
        float(np.sqrt(np.mean(np.square(np.array([0.0, 1.0, 2.0, 3.0, 4.0])))))
    )


def test_measure_waveform_uses_requested_complex_component(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    raw_path.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        waveform_backend, "_load_rawread_factory", lambda: (FakeRawRead, "fake-backend")
    )

    result = measure_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(ac)",
        operation="mean",
        component="magnitude",
    )

    assert result.operation == "mean"
    assert result.component == "magnitude"
    assert result.value == pytest.approx(
        float(np.mean(np.abs(np.array([1 + 1j, 2 + 2j, 3 + 3j, 4 + 4j, 5 + 5j]))))
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
        self._axis = np.array([0.0, 1.0, 2.0], dtype=np.float64)
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
        del step
        return self._axis

    def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
        if isinstance(trace_ref, int):
            trace_ref = self.get_trace_names()[trace_ref]
        if trace_ref == "time":
            return self._axis
        return self._waves[step][trace_ref]

    def get_plot_name(self) -> str:
        return "Transient Analysis"


def test_measure_waveform_resolves_step_filters(
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

    result = measure_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        operation="mean",
        step_filters={"VIN": 12},
    )

    assert result.step == 1
    assert result.value == pytest.approx(6.0)


def test_measure_waveform_reads_external_values_fixture_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    raw_path = tmp_path / EXTERNAL_VALUES_RAW_FIXTURE.name
    copy2(EXTERNAL_VALUES_RAW_FIXTURE, raw_path)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = measure_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        operation="max",
    )

    assert result.axis_name == "Time"
    assert result.component == "real"
    assert result.sample_count == 3
    assert result.value == pytest.approx(3.75)


def test_measure_waveform_reads_external_complex_values_raw_without_backend(
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

    result = measure_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        component="magnitude",
        operation="max",
    )

    assert result.axis_name == "Frequency"
    assert result.component == "magnitude"
    assert result.sample_count == 2
    assert result.value == pytest.approx(2.0)


def test_measure_waveform_reads_external_double_binary_raw_without_backend(
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

    result = measure_waveform(
        raw_path,
        workspace_root=tmp_path,
        signal="V(out)",
        operation="max",
    )

    assert result.axis_name == "Time"
    assert result.component == "real"
    assert result.sample_count == 3
    assert result.value == pytest.approx(3.75)
