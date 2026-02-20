"""Skill parameter validation layer.

Task card: S3-4
- Missing required params return clear error with field name
- Type validation for known parameter schemas
- Runs before execute() to reject invalid calls early

Architecture: docs/architecture/03-Skill Section 2
"""

from __future__ import annotations

from typing import Any

from src.skill.core.protocol import ValidationError, ValidationResult


def validate_required_params(
    params: dict[str, Any],
    required: list[str],
) -> ValidationResult:
    """Validate that all required parameters are present and non-empty.

    Args:
        params: Input parameters to validate.
        required: List of required parameter names.

    Returns:
        ValidationResult with valid=True if all present, errors otherwise.
    """
    errors: list[ValidationError] = []
    for field_name in required:
        value = params.get(field_name)
        if value is None:
            errors.append(
                ValidationError(
                    field=field_name,
                    message=f"Missing required parameter: {field_name}",
                )
            )
        elif isinstance(value, str) and not value.strip():
            errors.append(
                ValidationError(
                    field=field_name,
                    message=f"Parameter '{field_name}' cannot be empty",
                )
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_param_types(
    params: dict[str, Any],
    type_specs: dict[str, type],
) -> ValidationResult:
    """Validate parameter types against a type specification.

    Args:
        params: Input parameters to validate.
        type_specs: Mapping of parameter name to expected type.

    Returns:
        ValidationResult with type mismatch errors.
    """
    errors: list[ValidationError] = []
    for field_name, expected_type in type_specs.items():
        value = params.get(field_name)
        if value is not None and not isinstance(value, expected_type):
            errors.append(
                ValidationError(
                    field=field_name,
                    message=(
                        f"Parameter '{field_name}' expected type "
                        f"{expected_type.__name__}, got {type(value).__name__}"
                    ),
                )
            )

    return ValidationResult(valid=len(errors) == 0, errors=errors)


def validate_params(
    params: dict[str, Any],
    required: list[str],
    type_specs: dict[str, type] | None = None,
) -> ValidationResult:
    """Combined validation: required params + type checks.

    Args:
        params: Input parameters.
        required: Required parameter names.
        type_specs: Optional type specifications.

    Returns:
        Merged ValidationResult.
    """
    req_result = validate_required_params(params, required)
    if not req_result.valid:
        return req_result

    if type_specs:
        type_result = validate_param_types(params, type_specs)
        if not type_result.valid:
            return type_result

    return ValidationResult(valid=True)
