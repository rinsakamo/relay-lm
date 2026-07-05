"""Shared strict request-contract helpers for SOUL Lab APIs."""
from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


class StrictLabRequestModel(BaseModel):
    """Strict base model for SOUL Lab request payloads."""

    model_config = ConfigDict(extra="forbid", strict=True)


def unsafe_bounded_text(value: str, *, max_length: int, field_name: str) -> str:
    """Validate bounded SOUL Lab operator text without broadening accepted input."""

    if not isinstance(value, str) or len(value) > max_length:
        raise ValueError(f"{field_name}_invalid")
    if value != value.strip() or _unsafe(value):
        raise ValueError(f"{field_name}_invalid")
    return value


def validate_memory_id(value: str) -> str:
    """Validate a canonical Primary MEM identifier."""

    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError("memory_id_invalid")
    return value


def validate_reason(value: str) -> str:
    return unsafe_bounded_text(value, max_length=512, field_name="reason")


def validate_operation_id(value: str) -> str:
    value = unsafe_bounded_text(value, max_length=128, field_name="operation_id")
    if any(char in value for char in "\n\r\t"):
        raise ValueError("operation_id_invalid")
    return value


def validate_apply_token(value: str) -> str:
    value = unsafe_bounded_text(value, max_length=8192, field_name="apply_token")
    if any(char in value for char in "\n\r\t"):
        raise ValueError("apply_token_invalid")
    return value


def validate_corrected_title(value: str) -> str:
    return unsafe_bounded_text(value, max_length=160, field_name="corrected_title")


def validate_corrected_summary(value: str) -> str:
    return unsafe_bounded_text(value, max_length=2048, field_name="corrected_summary")


def validate_lab_request_text(value: str, field_name: str) -> str:
    """Dispatch validation for repeated SOUL Lab request text fields."""

    if field_name == "memory_id":
        return validate_memory_id(value)
    if field_name == "reason":
        return validate_reason(value)
    if field_name == "operation_id":
        return validate_operation_id(value)
    if field_name == "apply_token":
        return validate_apply_token(value)
    if field_name == "corrected_title":
        return validate_corrected_title(value)
    if field_name == "corrected_summary":
        return validate_corrected_summary(value)
    raise ValueError(f"{field_name}_invalid")


def _unsafe(value: str) -> bool:
    return any(
        ord(char) < 32
        or ord(char) in {0x2028, 0x2029}
        or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    )


__all__ = [
    "StrictLabRequestModel",
    "unsafe_bounded_text",
    "validate_apply_token",
    "validate_corrected_summary",
    "validate_corrected_title",
    "validate_lab_request_text",
    "validate_memory_id",
    "validate_operation_id",
    "validate_reason",
]
