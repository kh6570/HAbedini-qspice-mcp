"""Tests for shared raw write helpers."""

from __future__ import annotations

import importlib
from pathlib import Path
from shutil import copy2

import numpy as np
import pytest

from qspice_mcp.services._backends.waveform import load_waveform
from qspice_mcp.services.artifacts._raw_write import (
    RawStepBlock,
    RawTraceSeries,
    write_single_step_raw,
    write_stepped_raw,
)

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")
REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURE_ROOT = REPO_ROOT / "tests" / "fixtures" / "qraw"
BODE_RAW_FIXTURE = FIXTURE_ROOT / "bode-only.qraw"
BODE_DEBUG_RAW_FIXTURE = FIXTURE_ROOT / "bode-debug.qraw"
QUX_EXPORT_RAW_FIXTURE = REPO_ROOT / "tests" / "fixtures" / "qraw" / "qux_export_source.qraw"


def _write_supported_external_ascii_raw(
    destination: Path,
    *,
    plot_name: str,
    axis_name: str,
    signal_name: str,
    steps: tuple[tuple[np.ndarray, np.ndarray], ...],
    complex_data: bool = False,
) -> None:
    flags = ["complex" if complex_data else "real"]
    if len(steps) > 1:
        flags.append("stepped")
    point_count = sum(int(axis_values.shape[0]) for axis_values, _ in steps)
    header = (
        "\n".join(
            (
                "Title: * supported external ascii raw",
                f"Plotname: {plot_name}",
                f"Flags: {' '.join(flags)}",
                "No. Variables: 2",
                f"No. Points: {point_count}",
                "Variables:",
                f"\t0\t{axis_name}\t{axis_name.lower()}",
                f"\t1\t{signal_name}\tvoltage",
                "Binary:",
            )
        ).encode("ascii")
        + b"\n"
    )
    payload = bytearray()
    for axis_values, trace_values in steps:
        for axis_value, trace_value in zip(axis_values, trace_values, strict=True):
            payload.extend(np.asarray([axis_value], dtype="<f8").tobytes())
            payload.extend(
                np.asarray(
                    [trace_value],
                    dtype="<c16" if complex_data else "<f4",
                ).tobytes()
            )
    destination.write_bytes(header + payload)


def _write_supported_external_values_raw(
    destination: Path,
    *,
    plot_name: str,
    axis_name: str,
    signal_name: str,
    points: tuple[tuple[float, complex | float], ...],
    flags: tuple[str, ...] = (),
    complex_data: bool = False,
    title: str = "Title: * supported external values raw",
) -> None:
    rendered_flags = " ".join(["complex" if complex_data else "real", *flags])
    header = "\n".join(
        (
            title,
            f"Plotname: {plot_name}",
            f"Flags: {rendered_flags}",
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
        if complex_data:
            complex_value = complex(trace_value)
            lines.append(f"{complex_value.real:.16e},{complex_value.imag:.16e}")
        else:
            lines.append(f"{complex(trace_value).real:.16e}")
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_supported_external_fastaccess_raw(
    destination: Path,
    *,
    plot_name: str,
    axis_name: str,
    signal_name: str,
    steps: tuple[tuple[np.ndarray, np.ndarray], ...],
    complex_data: bool = False,
    header_encoding: str = "ascii",
) -> None:
    flags = ["complex" if complex_data else "real", "fastaccess"]
    if len(steps) > 1:
        flags.append("stepped")
    axis_values = np.concatenate([axis for axis, _ in steps]).astype("<f8", copy=False)
    trace_values = np.concatenate([trace for _, trace in steps]).astype(
        "<c16" if complex_data else "<f4",
        copy=False,
    )
    header_text = "\n".join(
        (
            "Title: * supported external fastaccess raw",
            f"Plotname: {plot_name}",
            f"Flags: {' '.join(flags)}",
            "No. Variables: 2",
            f"No. Points: {int(axis_values.shape[0])}",
            "Variables:",
            f"\t0\t{axis_name}\t{axis_name.lower()}",
            f"\t1\t{signal_name}\tvoltage",
            "Binary:",
        )
    )
    header = header_text.encode(header_encoding) + "\n".encode(header_encoding)
    destination.write_bytes(header + axis_values.tobytes() + trace_values.tobytes())


def test_write_single_step_raw_round_trips_complex_frequency_artifact(tmp_path: Path) -> None:
    destination = tmp_path / "derived-ac.qraw"
    axis_values = np.array([10.0, 100.0, 1_000.0], dtype=float)
    trace_values = np.array([1.0 + 2.0j, 3.0 + 4.0j, 5.0 + 6.0j], dtype=np.complex128)

    plot_name, axis_trace_name = write_single_step_raw(
        destination=destination,
        plot_name="AC Analysis",
        axis_name_value="frequency",
        axis_values=axis_values,
        traces=(
            RawTraceSeries(
                trace_name="OpenLoopGain",
                source_signal="V(loop)",
                values=trace_values,
            ),
        ),
    )

    magnitude = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="magnitude",
    )
    phase = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="phase",
    )
    real = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="real",
    )
    imag = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="imag",
    )
    header_text = destination.read_bytes().decode("utf_16_le", errors="ignore")

    assert plot_name == "AC Analysis"
    assert axis_trace_name == "frequency"
    assert "Flags: complex" in header_text
    assert magnitude.complex_source is True
    assert magnitude.axis_name is not None
    assert magnitude.axis_name.lower() == "frequency"
    assert magnitude.x.tolist() == pytest.approx(axis_values.tolist())
    assert real.y.tolist() == pytest.approx([1.0, 3.0, 5.0])
    assert imag.y.tolist() == pytest.approx([2.0, 4.0, 6.0])
    assert magnitude.y.tolist() == pytest.approx(np.abs(trace_values).tolist())
    assert phase.y.tolist() == pytest.approx(np.angle(trace_values, deg=True).tolist())


def test_write_stepped_raw_round_trips_complex_frequency_artifact(tmp_path: Path) -> None:
    destination = tmp_path / "derived-stepped-ac.qraw"
    step0_axis = np.array([10.0, 100.0, 1_000.0], dtype=float)
    step1_axis = np.array([10.0, 50.0], dtype=float)
    step0_values = np.array([1.0 + 2.0j, 3.0 + 4.0j, 5.0 + 6.0j], dtype=np.complex128)
    step1_values = np.array([7.0 + 8.0j, 9.0 + 10.0j], dtype=np.complex128)
    destination.with_suffix(".log").write_text(
        " 1 of 2 steps: .step corner=slow\n 2 of 2 steps: .step corner=fast\n",
        encoding="utf-8",
    )

    plot_name, axis_trace_name = write_stepped_raw(
        destination=destination,
        plot_name="AC Analysis",
        axis_name_value="frequency",
        steps=(
            RawStepBlock(
                axis_values=step0_axis,
                traces=(
                    RawTraceSeries(
                        trace_name="OpenLoopGain",
                        source_signal="V(loop)",
                        values=step0_values,
                    ),
                ),
            ),
            RawStepBlock(
                axis_values=step1_axis,
                traces=(
                    RawTraceSeries(
                        trace_name="OpenLoopGain",
                        source_signal="V(loop)",
                        values=step1_values,
                    ),
                ),
            ),
        ),
    )

    magnitude_step0 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=0,
        component="magnitude",
    )
    phase_step0 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=0,
        component="phase",
    )
    magnitude_step1 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=1,
        component="magnitude",
    )
    phase_step1 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        step=1,
        component="phase",
    )
    header_text = destination.read_bytes().decode("utf_16_le", errors="ignore")

    assert plot_name == "AC Analysis"
    assert axis_trace_name == "frequency"
    assert "Flags: complex stepped" in header_text
    assert magnitude_step0.axis_name is not None
    assert magnitude_step0.axis_name.lower() == "frequency"
    assert magnitude_step0.x.tolist() == pytest.approx(step0_axis.tolist())
    assert magnitude_step0.y.tolist() == pytest.approx(np.abs(step0_values).tolist())
    assert phase_step0.y.tolist() == pytest.approx(np.angle(step0_values, deg=True).tolist())
    assert magnitude_step1.x.tolist() == pytest.approx(step1_axis.tolist())
    assert magnitude_step1.y.tolist() == pytest.approx(np.abs(step1_values).tolist())
    assert phase_step1.y.tolist() == pytest.approx(np.angle(step1_values, deg=True).tolist())


def test_load_waveform_reads_supported_utf16_raw_without_repo_title(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "compatible-ac.qraw"
    axis_values = np.array([10.0, 100.0, 1_000.0], dtype=float)
    trace_values = np.array([1.0 + 2.0j, 3.0 + 4.0j, 5.0 + 6.0j], dtype=np.complex128)

    write_single_step_raw(
        destination=destination,
        plot_name="AC Analysis",
        axis_name_value="frequency",
        axis_values=axis_values,
        traces=(
            RawTraceSeries(
                trace_name="OpenLoopGain",
                source_signal="V(loop)",
                values=trace_values,
            ),
        ),
    )
    destination.write_bytes(
        destination.read_bytes().replace(
            "Title: * qspice_mcp clean-room raw writer".encode("utf_16_le"),
            "Title: * compatible utf16 raw".encode("utf_16_le"),
            1,
        )
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    magnitude = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="magnitude",
    )
    phase = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="phase",
    )

    assert magnitude.axis_name is not None
    assert magnitude.axis_name.lower() == "frequency"
    assert magnitude.x.tolist() == pytest.approx(axis_values.tolist())
    assert magnitude.y.tolist() == pytest.approx(np.abs(trace_values).tolist())
    assert phase.y.tolist() == pytest.approx(np.angle(trace_values, deg=True).tolist())


def test_load_waveform_reads_external_ascii_complex_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / BODE_RAW_FIXTURE.name
    copy2(BODE_RAW_FIXTURE, destination)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    magnitude = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="magnitude",
    )
    phase = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="OpenLoopGain",
        component="phase",
    )

    assert magnitude.axis_name is not None
    assert magnitude.axis_name.lower() == "frequency"
    assert magnitude.x[:3].tolist() == pytest.approx(
        [100.0, 100.79657375881209, 101.34901781576646]
    )
    assert magnitude.y[:3].tolist() == pytest.approx(
        [0.1682035675227684, 0.16819675307439413, 0.16819840961864374]
    )
    assert phase.y[:3].tolist() == pytest.approx(
        [-178.37190582939897, -178.35406910427133, -178.34060994537592]
    )
    assert magnitude.x[-1] == pytest.approx(100000.0)
    assert magnitude.y[-1] == pytest.approx(4.946991379322913)
    assert phase.y[-1] == pytest.approx(-91.94251202785975)


def test_load_waveform_reads_external_ascii_stepped_real_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "external-stepped-tran.qraw"
    _write_supported_external_ascii_raw(
        destination,
        plot_name="Transient Analysis",
        axis_name="Time",
        signal_name="V(out)",
        steps=(
            (
                np.array([0.0, 1.0, 2.0], dtype=float),
                np.array([1.0, 2.0, 3.0], dtype=float),
            ),
            (
                np.array([0.0, 1.0], dtype=float),
                np.array([4.0, 5.0], dtype=float),
            ),
        ),
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    step0 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
        step=0,
    )
    step1 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
        step=1,
    )

    assert step0.axis_name is not None
    assert step0.axis_name.lower() == "time"
    assert step0.x.tolist() == pytest.approx([0.0, 1.0, 2.0])
    assert step0.y.tolist() == pytest.approx([1.0, 2.0, 3.0])
    assert step1.x.tolist() == pytest.approx([0.0, 1.0])
    assert step1.y.tolist() == pytest.approx([4.0, 5.0])


def test_load_waveform_reads_external_qspice_real_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / QUX_EXPORT_RAW_FIXTURE.name
    copy2(QUX_EXPORT_RAW_FIXTURE, destination)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    waveform = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
    )

    assert waveform.axis_name is not None
    assert waveform.axis_name.lower() == "time"
    assert waveform.x[:5].tolist() == pytest.approx([0.0, 3.2e-12, 6.4e-12, 1.28e-11, 2.56e-11])
    assert waveform.y[:5].tolist() == pytest.approx(
        [
            0.0,
            2.6824099196671884e-15,
            1.0634507709401246e-14,
            4.233405974268095e-14,
            1.6874044698494828e-13,
        ]
    )
    assert waveform.x[-1] == pytest.approx(0.001)
    assert waveform.y[-1] == pytest.approx(0.24181295697526017)


def test_load_waveform_reads_external_frequency_response_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / BODE_DEBUG_RAW_FIXTURE.name
    copy2(BODE_DEBUG_RAW_FIXTURE, destination)

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    waveform = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
    )

    assert waveform.axis_name is not None
    assert waveform.axis_name.lower() == "time"
    assert waveform.x[:5].tolist() == pytest.approx(
        [
            0.0,
            0.00027954297522546443,
            0.0006117266381517623,
            0.0009439103010780601,
            0.001276093964004358,
        ]
    )
    assert waveform.y[:5].tolist() == pytest.approx(
        [
            5.117280495236177,
            5.129982213496358,
            5.14285749704981,
            5.153070165338331,
            5.160439174004427,
        ]
    )
    assert waveform.x[-1] == pytest.approx(0.34015607083686117)
    assert waveform.y[-1] == pytest.approx(5.0106260968052)


def test_load_waveform_reads_external_values_raw_with_metadata_flags_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "external-values.qraw"
    _write_supported_external_values_raw(
        destination,
        plot_name="Transient Analysis",
        axis_name="Time",
        signal_name="V(out)",
        points=((0.0, 1.25), (0.5, 2.5), (1.0, 3.75)),
        flags=("forward", "log", "double"),
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    waveform = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
    )

    assert waveform.axis_name is not None
    assert waveform.axis_name.lower() == "time"
    assert waveform.x.tolist() == pytest.approx([0.0, 0.5, 1.0])
    assert waveform.y.tolist() == pytest.approx([1.25, 2.5, 3.75])


def test_load_waveform_reads_repo_titled_values_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "clean-room-values.qraw"
    _write_supported_external_values_raw(
        destination,
        plot_name="Transient Analysis",
        axis_name="Time",
        signal_name="V(out)",
        points=((0.0, 1.25), (0.5, 2.5), (1.0, 3.75)),
        title="Title: * qspice_mcp clean-room raw writer",
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    waveform = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
    )

    assert waveform.axis_name is not None
    assert waveform.axis_name.lower() == "time"
    assert waveform.x.tolist() == pytest.approx([0.0, 0.5, 1.0])
    assert waveform.y.tolist() == pytest.approx([1.25, 2.5, 3.75])


def test_load_waveform_reads_external_fastaccess_complex_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "external-fastaccess-ac.qraw"
    step0_axis = np.array([10.0, 100.0], dtype=float)
    step1_axis = np.array([20.0, 200.0], dtype=float)
    step0_values = np.array([1.0 + 2.0j, 3.0 + 4.0j], dtype=np.complex128)
    step1_values = np.array([5.0 + 6.0j, 7.0 + 8.0j], dtype=np.complex128)
    _write_supported_external_fastaccess_raw(
        destination,
        plot_name="AC Analysis",
        axis_name="Frequency",
        signal_name="V(out)",
        steps=((step0_axis, step0_values), (step1_axis, step1_values)),
        complex_data=True,
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    magnitude_step0 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
        step=0,
        component="magnitude",
    )
    phase_step1 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
        step=1,
        component="phase",
    )

    assert magnitude_step0.axis_name is not None
    assert magnitude_step0.axis_name.lower() == "frequency"
    assert magnitude_step0.x.tolist() == pytest.approx(step0_axis.tolist())
    assert magnitude_step0.y.tolist() == pytest.approx(np.abs(step0_values).tolist())
    assert phase_step1.x.tolist() == pytest.approx(step1_axis.tolist())
    assert phase_step1.y.tolist() == pytest.approx(np.angle(step1_values, deg=True).tolist())


def test_load_waveform_reads_external_utf16_fastaccess_complex_raw_without_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "external-fastaccess-ac-utf16.qraw"
    step0_axis = np.array([10.0, 100.0], dtype=float)
    step1_axis = np.array([20.0, 200.0], dtype=float)
    step0_values = np.array([1.0 + 2.0j, 3.0 + 4.0j], dtype=np.complex128)
    step1_values = np.array([5.0 + 6.0j, 7.0 + 8.0j], dtype=np.complex128)
    _write_supported_external_fastaccess_raw(
        destination,
        plot_name="AC Analysis",
        axis_name="Frequency",
        signal_name="V(out)",
        steps=((step0_axis, step0_values), (step1_axis, step1_values)),
        complex_data=True,
        header_encoding="utf_16_le",
    )

    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    magnitude_step0 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
        step=0,
        component="magnitude",
    )
    phase_step1 = load_waveform(
        destination,
        workspace_root=tmp_path,
        signal="V(out)",
        step=1,
        component="phase",
    )

    assert magnitude_step0.axis_name is not None
    assert magnitude_step0.axis_name.lower() == "frequency"
    assert magnitude_step0.x.tolist() == pytest.approx(step0_axis.tolist())
    assert magnitude_step0.y.tolist() == pytest.approx(np.abs(step0_values).tolist())
    assert phase_step1.x.tolist() == pytest.approx(step1_axis.tolist())
    assert phase_step1.y.tolist() == pytest.approx(np.angle(step1_values, deg=True).tolist())
