"""Tests for waveform backend helpers."""

from __future__ import annotations

import numpy as np
import pytest

from qspice_mcp.core.budgets import DataBudget
from qspice_mcp.services._backends.waveform import (
    apply_axis_window,
    apply_budget,
    build_budget,
    get_axis_name,
    infer_axis_unit,
    infer_signal_unit,
    read_axis_array,
    resolve_signal_name,
    select_component,
    to_axis_array,
    to_wave_array,
)


class TestBuildBudget:
    def test_default_budget(self) -> None:
        budget = build_budget()
        assert budget.max_points == 2000
        assert budget.max_bytes == 64_000

    def test_custom_max_points(self) -> None:
        budget = build_budget(max_points=500)
        assert budget.max_points == 500
        assert budget.max_bytes == 64_000

    def test_custom_max_bytes(self) -> None:
        budget = build_budget(max_bytes=16_000)
        assert budget.max_points == 2000
        assert budget.max_bytes == 16_000

    def test_both_custom(self) -> None:
        budget = build_budget(max_points=100, max_bytes=8_000)
        assert budget.max_points == 100
        assert budget.max_bytes == 8_000

    def test_strategy_preserved(self) -> None:
        budget = build_budget()
        assert budget.strategy == "lttb"


class TestToAxisArray:
    def test_ndarray_passthrough(self) -> None:
        arr = np.array([1.0, 2.0, 3.0])
        result = to_axis_array(arr)
        assert result.shape == (3,)
        assert result.dtype == np.float64

    def test_list_converted(self) -> None:
        result = to_axis_array([1.0, 2.0])
        assert result.shape == (2,)
        assert result.dtype == np.float64

    def test_ravels_multi_dim(self) -> None:
        arr = np.array([[1.0, 2.0], [3.0, 4.0]])
        result = to_axis_array(arr)
        assert result.shape == (4,)

    def test_complex_axis_uses_real_part_when_imaginary_is_zero(self) -> None:
        arr = np.array([10.0 + 0.0j, 100.0 + 0.0j])
        result = to_axis_array(arr)
        assert result.tolist() == [10.0, 100.0]

    def test_complex_axis_rejects_nonzero_imaginary_values(self) -> None:
        arr = np.array([10.0 + 1.0j, 100.0 + 0.0j])
        with pytest.raises(ValueError, match="Waveform axis must be real-valued"):
            to_axis_array(arr)


class TestToWaveArray:
    def test_float_array(self) -> None:
        arr = np.array([1.0, 2.0])
        result = to_wave_array(arr)
        assert result.shape == (2,)

    def test_complex_array(self) -> None:
        arr = np.array([1 + 2j, 3 + 4j])
        result = to_wave_array(arr)
        assert result.shape == (2,)
        assert np.iscomplexobj(result)


class TestInferAxisUnit:
    def test_time(self) -> None:
        assert infer_axis_unit("time") == "s"

    def test_frequency(self) -> None:
        assert infer_axis_unit("frequency") == "Hz"

    def test_none(self) -> None:
        assert infer_axis_unit(None) == "index"

    def test_unknown(self) -> None:
        assert infer_axis_unit("some_axis") == "arb"

    def test_case_insensitive(self) -> None:
        assert infer_axis_unit("Time") == "s"
        assert infer_axis_unit("FREQUENCY") == "Hz"


class TestInferSignalUnit:
    def test_current(self) -> None:
        assert infer_signal_unit("I(R1)", "real") == "A"
        assert infer_signal_unit("i(vcc)", "magnitude") == "A"

    def test_voltage(self) -> None:
        assert infer_signal_unit("V(out)", "real") == "V"
        assert infer_signal_unit("v(in)", "magnitude") == "V"

    def test_power(self) -> None:
        assert infer_signal_unit("P(total)", "real") == "W"
        assert infer_signal_unit("p(out)", "magnitude") == "W"

    def test_phase(self) -> None:
        assert infer_signal_unit("V(out)", "phase") == "deg"

    def test_unknown(self) -> None:
        assert infer_signal_unit("gain", "real") == "arb"


class TestSelectComponent:
    def test_real_auto_returns_real(self) -> None:
        values = np.array([1.0, 2.0, 3.0])
        component, result, complex_source = select_component(values, "auto")
        assert component == "real"
        assert list(result) == [1.0, 2.0, 3.0]
        assert complex_source is False

    def test_real_magnitude_returns_abs(self) -> None:
        values = np.array([-1.0, -2.0, 3.0])
        _, result, _ = select_component(values, "magnitude")
        assert list(result) == [1.0, 2.0, 3.0]

    def test_complex_auto_defaults_to_magnitude(self) -> None:
        values = np.array([3 + 4j, 6 + 8j])
        component, result, complex_source = select_component(values, "auto")
        assert component == "magnitude"
        assert result[0] == pytest.approx(5.0)
        assert result[1] == pytest.approx(10.0)
        assert complex_source is True

    def test_complex_real(self) -> None:
        values = np.array([3 + 4j, 5 + 6j])
        component, result, _ = select_component(values, "real")
        assert component == "real"
        assert list(result) == [3.0, 5.0]

    def test_complex_imag(self) -> None:
        values = np.array([3 + 4j, 5 + 6j])
        component, result, _ = select_component(values, "imag")
        assert component == "imag"
        assert list(result) == [4.0, 6.0]

    def test_complex_phase(self) -> None:
        values = np.array([1 + 0j, 0 + 1j])
        _, result, _ = select_component(values, "phase")
        assert result[0] == pytest.approx(0.0)
        assert result[1] == pytest.approx(90.0)

    def test_real_imag_raises(self) -> None:
        values = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="complex data"):
            select_component(values, "imag")

    def test_real_phase_raises(self) -> None:
        values = np.array([1.0, 2.0])
        with pytest.raises(ValueError, match="complex data"):
            select_component(values, "phase")


class TestApplyAxisWindow:
    def test_no_window_returns_all(self) -> None:
        axis = np.array([0.0, 1.0, 2.0, 3.0])
        values = np.array([10.0, 20.0, 30.0, 40.0])
        fx, fy = apply_axis_window(axis, values, t_start=None, t_end=None)
        assert list(fx) == [0.0, 1.0, 2.0, 3.0]
        assert list(fy) == [10.0, 20.0, 30.0, 40.0]

    def test_t_start_cuts_lower(self) -> None:
        axis = np.array([0.0, 1.0, 2.0, 3.0])
        values = np.array([10.0, 20.0, 30.0, 40.0])
        fx, fy = apply_axis_window(axis, values, t_start=1.0, t_end=None)
        assert list(fx) == [1.0, 2.0, 3.0]
        assert list(fy) == [20.0, 30.0, 40.0]

    def test_t_end_cuts_upper(self) -> None:
        axis = np.array([0.0, 1.0, 2.0, 3.0])
        values = np.array([10.0, 20.0, 30.0, 40.0])
        fx, fy = apply_axis_window(axis, values, t_start=None, t_end=1.0)
        assert list(fx) == [0.0, 1.0]
        assert list(fy) == [10.0, 20.0]

    def test_both_bounds(self) -> None:
        axis = np.array([0.0, 1.0, 2.0, 3.0])
        values = np.array([10.0, 20.0, 30.0, 40.0])
        fx, fy = apply_axis_window(axis, values, t_start=1.0, t_end=2.0)
        assert list(fx) == [1.0, 2.0]
        assert list(fy) == [20.0, 30.0]

    def test_empty_result_raises(self) -> None:
        axis = np.array([0.0, 1.0])
        values = np.array([10.0, 20.0])
        with pytest.raises(ValueError, match="No waveform samples"):
            apply_axis_window(axis, values, t_start=5.0, t_end=10.0)

    def test_inverted_window_raises(self) -> None:
        axis = np.array([0.0, 1.0])
        values = np.array([10.0, 20.0])
        with pytest.raises(ValueError, match="t_end must be"):
            apply_axis_window(axis, values, t_start=5.0, t_end=1.0)


class TestApplyBudget:
    def test_fits_within_budget_no_downsample(self) -> None:
        axis = np.linspace(0, 1, 10)
        values = np.linspace(0, 10, 10)
        budget = DataBudget(max_points=100, max_bytes=100_000)
        fx, _fy, downsampled = apply_budget(axis, values, budget=budget)
        assert downsampled is False
        assert len(fx) == 10

    def test_exceeds_point_limit_downsamples(self) -> None:
        axis = np.linspace(0, 1, 100)
        values = np.linspace(0, 100, 100)
        budget = DataBudget(max_points=20, max_bytes=1_000_000)
        fx, _fy, downsampled = apply_budget(axis, values, budget=budget)
        assert downsampled is True
        assert len(fx) <= 20

    def test_exceeds_byte_limit_downsamples(self) -> None:
        axis = np.linspace(0, 1, 100)
        values = np.linspace(0, 100, 100)
        budget = DataBudget(max_points=1000, max_bytes=1024)
        fx, _fy, downsampled = apply_budget(axis, values, budget=budget)
        assert downsampled is True
        assert len(fx) < 100

    def test_exact_points_at_budget_boundary(self) -> None:
        axis = np.linspace(0, 1, 64)
        values = np.linspace(0, 100, 64)
        budget = DataBudget(max_points=1000, max_bytes=1024)
        fx, _fy, downsampled = apply_budget(axis, values, budget=budget)
        assert downsampled is False
        assert len(fx) == 64


class TestResolveSignalName:
    def _make_mock_reader(self, names: tuple[str, ...]) -> object:
        class MockReader:
            def get_trace_names(self) -> tuple[str, ...]:
                return names

        return MockReader()

    def test_exact_match(self) -> None:
        reader = self._make_mock_reader(("V(out)", "I(R1)"))
        assert resolve_signal_name(reader, "V(out)") == "V(out)"

    def test_case_insensitive_match(self) -> None:
        reader = self._make_mock_reader(("V(out)", "I(R1)"))
        assert resolve_signal_name(reader, "v(OUT)") == "V(out)"

    def test_not_found_raises(self) -> None:
        reader = self._make_mock_reader(("V(out)",))
        with pytest.raises(ValueError, match="Signal not found"):
            resolve_signal_name(reader, "V(in)")


class TestAxisReaders:
    def test_read_axis_array_falls_back_to_axis_trace(self) -> None:
        class MockReader:
            has_axis = True

            def get_trace_names(self) -> tuple[str, ...]:
                return ("Frequency", "OpenLoopGain")

            def get_axis(self, step: int = 0) -> np.ndarray:
                raise RuntimeError("This RAW file does not have an axis.")

            def get_wave(self, trace_ref: str | int, step: int = 0) -> np.ndarray:
                assert trace_ref == "Frequency"
                return np.array([100.0, 1_000.0, 10_000.0])

        reader = MockReader()

        assert get_axis_name(reader) == "Frequency"
        assert list(read_axis_array(reader, step=0)) == [100.0, 1_000.0, 10_000.0]

    def test_resolve_signal_name_excludes_axis_when_has_axis_is_boolean(self) -> None:
        class MockReader:
            has_axis = True

            def get_trace_names(self) -> tuple[str, ...]:
                return ("Frequency", "OpenLoopGain")

        reader = MockReader()

        assert resolve_signal_name(reader, "OpenLoopGain") == "OpenLoopGain"
        with pytest.raises(ValueError, match="Signal not found"):
            resolve_signal_name(reader, "Frequency")
