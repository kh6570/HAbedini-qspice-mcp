"""Tests for the evaluate_waveform_expression service."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

import numpy as np
import pytest

from qspice_mcp.core.exceptions import QSpiceError
from qspice_mcp.services.waveform.evaluate_waveform_expression import (
    evaluate_waveform_expression,
)

if TYPE_CHECKING:
    from pathlib import Path

waveform_backend = importlib.import_module("qspice_mcp.services._backends.waveform")


def _write_two_signal_double_binary_raw(
    destination: Path,
    *,
    axis: tuple[float, ...],
    out_values: tuple[float, ...],
    in_values: tuple[float, ...],
) -> None:
    header = (
        "\n".join(
            (
                "Title: * two-signal raw",
                "Plotname: Transient Analysis",
                "Flags: real forward double",
                "No. Variables: 3",
                f"No. Points: {len(axis)}",
                "Variables:",
                "\t0\tTime\ttime",
                "\t1\tV(out)\tvoltage",
                "\t2\tV(in)\tvoltage",
                "Binary:",
            )
        ).encode("ascii")
        + b"\n"
    )
    payload = bytearray()
    for index, axis_value in enumerate(axis):
        payload.extend(np.asarray([axis_value], dtype="<f8").tobytes())
        payload.extend(np.asarray([out_values[index]], dtype="<f8").tobytes())
        payload.extend(np.asarray([in_values[index]], dtype="<f8").tobytes())
    destination.write_bytes(header + payload)


def test_evaluate_waveform_expression_computes_difference(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    _write_two_signal_double_binary_raw(
        raw_path,
        axis=(0.0, 1.0, 2.0),
        out_values=(5.0, 6.0, 7.0),
        in_values=(1.0, 2.0, 3.0),
    )
    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = evaluate_waveform_expression(
        raw_path,
        workspace_root=tmp_path,
        expression="V(out)-V(in)",
    )

    assert result.expression == "V(out)-V(in)"
    assert set(result.signals) == {"V(out)", "V(in)"}
    assert result.y_values == (4.0, 4.0, 4.0)
    assert result.point_count == 3


def test_evaluate_waveform_expression_supports_scaling(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    _write_two_signal_double_binary_raw(
        raw_path,
        axis=(0.0, 1.0),
        out_values=(2.0, 4.0),
        in_values=(1.0, 1.0),
    )
    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    result = evaluate_waveform_expression(
        raw_path,
        workspace_root=tmp_path,
        expression="2*V(out)",
    )

    assert result.y_values == (4.0, 8.0)


def test_evaluate_waveform_expression_rejects_signal_free_expression(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    raw_path = tmp_path / "demo.qraw"
    _write_two_signal_double_binary_raw(
        raw_path,
        axis=(0.0, 1.0),
        out_values=(2.0, 4.0),
        in_values=(1.0, 1.0),
    )
    monkeypatch.setattr(waveform_backend, "_load_rawread_factory", lambda: (None, None))

    with pytest.raises(QSpiceError):
        evaluate_waveform_expression(raw_path, workspace_root=tmp_path, expression="1+2")
