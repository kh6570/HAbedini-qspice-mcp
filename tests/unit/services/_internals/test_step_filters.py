"""Tests for step filter helpers."""

from __future__ import annotations

import pytest

from qspice_mcp.services._internals.step_filters import (
    _coerce_step_filter_value,
    _values_match,
    build_step_value_maps,
    normalize_step_filters,
    resolve_step_selection,
)


class FakeStepVariable:
    def __init__(self, name: str, values: list[str | int | float]) -> None:
        self.name = name
        self.values = tuple(values)


class TestCoerceStepFilterValue:
    def test_bool_to_int(self) -> None:
        assert _coerce_step_filter_value(True) == 1
        assert _coerce_step_filter_value(False) == 0

    def test_numbers_pass_through(self) -> None:
        assert _coerce_step_filter_value(42) == 42
        assert _coerce_step_filter_value(3.14) == 3.14

    def test_string_passes_through(self) -> None:
        assert _coerce_step_filter_value("hello") == "hello"

    def test_unknown_type_becomes_string(self) -> None:
        result = _coerce_step_filter_value(object())
        assert isinstance(result, str)
        assert "object" in result


class TestNormalizeStepFilters:
    def test_none_returns_empty(self) -> None:
        assert normalize_step_filters(None) == {}

    def test_empty_dict_returns_empty(self) -> None:
        assert normalize_step_filters({}) == {}

    def test_lowers_keys(self) -> None:
        result = normalize_step_filters({"Vin": 12})
        assert result == {"vin": 12}

    def test_strips_whitespace_from_keys(self) -> None:
        result = normalize_step_filters({" vin ": 5})
        assert result == {"vin": 5}

    def test_coerces_bool_values(self) -> None:
        result = normalize_step_filters({"enable": True})
        assert result["enable"] == 1


class TestValuesMatch:
    def test_same_int(self) -> None:
        assert _values_match(42, 42)

    def test_different_int(self) -> None:
        assert not _values_match(42, 43)

    def test_same_float_close(self) -> None:
        assert _values_match(1.0, 1.0 + 1e-13)

    def test_int_and_float_match(self) -> None:
        assert _values_match(5, 5.0)

    def test_same_string(self) -> None:
        assert _values_match("abc", "abc")

    def test_case_insensitive_string(self) -> None:
        assert _values_match("ABC", "abc")

    def test_stripped_string(self) -> None:
        assert _values_match(" abc ", "abc")

    def test_different_types_fall_back_to_string(self) -> None:
        assert _values_match("12", 12)


class TestBuildStepValueMaps:
    def test_two_vars_three_steps(self) -> None:
        variables = [
            FakeStepVariable("vin", [1, 2, 3]),
            FakeStepVariable("temp", [25, 50, 75]),
        ]
        result = build_step_value_maps(variables, 3)
        assert len(result) == 3
        assert result[0] == {"vin": 1, "temp": 25}
        assert result[1] == {"vin": 2, "temp": 50}
        assert result[2] == {"vin": 3, "temp": 75}

    def test_empty_variables(self) -> None:
        result = build_step_value_maps([], 2)
        assert result == ({}, {})

    def test_partial_values_omits_index(self) -> None:
        variables = [
            FakeStepVariable("vin", [1]),
        ]
        result = build_step_value_maps(variables, 3)
        assert result[0] == {"vin": 1}
        assert result[1] == {}
        assert result[2] == {}

    def test_lowered_keys(self) -> None:
        variables = [FakeStepVariable("VIN", [5])]
        result = build_step_value_maps(variables, 1)
        assert result[0] == {"vin": 5}


class TestResolveStepSelection:
    def _make_vars(self, *names_and_values: tuple) -> tuple:
        return tuple(FakeStepVariable(n, list(v)) for n, v in names_and_values)

    def test_default_step_when_no_filters(self) -> None:
        step_vars = self._make_vars(("vin", [1, 2, 3]))
        result = resolve_step_selection(step_vars, 3)
        assert result == 0

    def test_explicit_step_index(self) -> None:
        step_vars = self._make_vars(("vin", [1, 2, 3]))
        result = resolve_step_selection(step_vars, 3, step=2)
        assert result == 2

    def test_step_filters_single_match(self) -> None:
        step_vars = self._make_vars(("vin", [1, 2, 3]))
        result = resolve_step_selection(step_vars, 3, step_filters={"vin": 2})
        assert result == 1

    def test_step_filters_no_match(self) -> None:
        step_vars = self._make_vars(("vin", [1, 2, 3]))
        with pytest.raises(ValueError, match="No simulation step matched"):
            resolve_step_selection(step_vars, 3, step_filters={"vin": 99})

    def test_step_filters_multiple_matches_raises(self) -> None:
        step_vars = self._make_vars(("vin", [5, 5]))
        with pytest.raises(ValueError, match="multiple simulation steps"):
            resolve_step_selection(step_vars, 2, step_filters={"vin": 5})

    def test_step_and_filters_resolve_same(self) -> None:
        step_vars = self._make_vars(("vin", [1, 2, 3]))
        result = resolve_step_selection(step_vars, 3, step=1, step_filters={"vin": 2})
        assert result == 1

    def test_step_and_filters_conflict_raises(self) -> None:
        step_vars = self._make_vars(("vin", [1, 2, 3]))
        with pytest.raises(ValueError, match="different simulation steps"):
            resolve_step_selection(step_vars, 3, step=0, step_filters={"vin": 2})

    def test_no_steps_raises(self) -> None:
        with pytest.raises(ValueError, match="No simulation steps"):
            resolve_step_selection((), 0)

    def test_step_out_of_range_raises(self) -> None:
        step_vars = self._make_vars(("vin", [1]))
        with pytest.raises(ValueError, match="Step index"):
            resolve_step_selection(step_vars, 1, step=5)

    def test_filters_without_step_variables_raises(self) -> None:
        with pytest.raises(ValueError, match="step_filters require step metadata"):
            resolve_step_selection((), 1, step_filters={"vin": 1})

    def test_default_step_parameter(self) -> None:
        step_vars = self._make_vars(("vin", [1, 2, 3]))
        result = resolve_step_selection(step_vars, 3, default_step=2)
        assert result == 2

    def test_step_filters_case_insensitive_key_and_value(self) -> None:
        step_vars = self._make_vars(("VIN", ["A", "B"]))
        result = resolve_step_selection(step_vars, 2, step_filters={"vin": "a"})
        assert result == 0
