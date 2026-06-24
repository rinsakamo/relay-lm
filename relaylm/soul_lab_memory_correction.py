"""Strict SOUL Lab request contracts for auditable Primary MEM Correct."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .relaymem_primary_correction import (
    APPLY_REQUEST_SCHEMA,
    PREFLIGHT_REQUEST_SCHEMA,
)


class _ExactModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LabMemoryCorrectPreflightRequest(_ExactModel):
    schema: Literal["relaylm.lab.memory_correct_preflight_request.v0"] = PREFLIGHT_REQUEST_SCHEMA
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    corrected_title: str = Field(max_length=160)
    corrected_summary: str = Field(min_length=1, max_length=2048)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)

    @field_validator("corrected_title", "corrected_summary", "reason", "operation_id")
    @classmethod
    def validate_bounded_text(cls, value: str, info):
        if value != value.strip() or _unsafe(value):
            raise ValueError(f"{info.field_name}_invalid")
        if info.field_name == "operation_id" and any(char in value for char in "\n\r\t"):
            raise ValueError("operation_id_invalid")
        return value


class LabMemoryCorrectApplyRequest(_ExactModel):
    schema: Literal["relaylm.lab.memory_correct_apply_request.v0"] = APPLY_REQUEST_SCHEMA
    operation_id: str = Field(min_length=1, max_length=128)
    apply_token: str = Field(min_length=1, max_length=8192)
    expected_revision: int = Field(ge=1, le=2_147_483_647)

    @field_validator("operation_id", "apply_token")
    @classmethod
    def validate_token_text(cls, value: str, info):
        if value != value.strip() or _unsafe(value) or any(char in value for char in "\n\r\t"):
            raise ValueError(f"{info.field_name}_invalid")
        return value


def _unsafe(value: str) -> bool:
    return any(
        ord(char) < 32
        or ord(char) in {0x2028, 0x2029}
        or 0xD800 <= ord(char) <= 0xDFFF
        for char in value
    )


__all__ = ["LabMemoryCorrectApplyRequest", "LabMemoryCorrectPreflightRequest"]
