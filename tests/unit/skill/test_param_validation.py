"""S3-4: Skill parameter validation tests.

Tests: missing required params, empty strings, type mismatches, combined validation.
"""

from __future__ import annotations

from src.skill.core.validation import (
    validate_param_types,
    validate_params,
    validate_required_params,
)


class TestRequiredParams:
    def test_all_present(self) -> None:
        result = validate_required_params({"a": "x", "b": 1}, ["a", "b"])
        assert result.valid is True
        assert len(result.errors) == 0

    def test_missing_single(self) -> None:
        result = validate_required_params({"a": "x"}, ["a", "b"])
        assert result.valid is False
        assert len(result.errors) == 1
        assert result.errors[0].field == "b"
        assert "Missing required" in result.errors[0].message

    def test_missing_multiple(self) -> None:
        result = validate_required_params({}, ["a", "b", "c"])
        assert result.valid is False
        assert len(result.errors) == 3

    def test_empty_string_rejected(self) -> None:
        result = validate_required_params({"name": "  "}, ["name"])
        assert result.valid is False
        assert result.errors[0].field == "name"
        assert "cannot be empty" in result.errors[0].message

    def test_none_value_rejected(self) -> None:
        result = validate_required_params({"name": None}, ["name"])
        assert result.valid is False

    def test_zero_is_valid(self) -> None:
        result = validate_required_params({"count": 0}, ["count"])
        assert result.valid is True

    def test_empty_list_is_valid(self) -> None:
        result = validate_required_params({"tags": []}, ["tags"])
        assert result.valid is True

    def test_no_required_always_valid(self) -> None:
        result = validate_required_params({}, [])
        assert result.valid is True


class TestParamTypes:
    def test_correct_types(self) -> None:
        result = validate_param_types(
            {"name": "hello", "count": 5},
            {"name": str, "count": int},
        )
        assert result.valid is True

    def test_wrong_type(self) -> None:
        result = validate_param_types(
            {"name": 123},
            {"name": str},
        )
        assert result.valid is False
        assert result.errors[0].field == "name"
        assert "expected type str" in result.errors[0].message
        assert "got int" in result.errors[0].message

    def test_missing_param_not_type_checked(self) -> None:
        """Missing params are not type-checked (handled by required check)."""
        result = validate_param_types({}, {"name": str})
        assert result.valid is True

    def test_multiple_type_errors(self) -> None:
        result = validate_param_types(
            {"a": 1, "b": "x"},
            {"a": str, "b": int},
        )
        assert result.valid is False
        assert len(result.errors) == 2


class TestCombinedValidation:
    def test_required_check_first(self) -> None:
        """Required check runs before type check."""
        result = validate_params(
            {},
            required=["name"],
            type_specs={"name": str},
        )
        assert result.valid is False
        assert "Missing required" in result.errors[0].message

    def test_type_check_after_required(self) -> None:
        result = validate_params(
            {"name": 123},
            required=["name"],
            type_specs={"name": str},
        )
        assert result.valid is False
        assert "expected type" in result.errors[0].message

    def test_all_valid(self) -> None:
        result = validate_params(
            {"name": "hello", "count": 5},
            required=["name"],
            type_specs={"name": str, "count": int},
        )
        assert result.valid is True

    def test_no_type_specs(self) -> None:
        result = validate_params({"name": "x"}, required=["name"])
        assert result.valid is True

    def test_error_message_contains_field_name(self) -> None:
        """Task card requirement: error messages contain field name."""
        result = validate_params({}, required=["brand_name", "platform"])
        assert result.valid is False
        field_names = {e.field for e in result.errors}
        assert "brand_name" in field_names
        assert "platform" in field_names
