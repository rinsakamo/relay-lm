"""Strict SOUL Lab request contracts for Primary MEM Pin / Unpin."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _ExactModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LabMemoryPinPreflightRequest(_ExactModel):
    schema: Literal["relaylm.lab.memory_pin_preflight_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)

    @field_validator("reason", "operation_id")
    @classmethod
    def validate_bounded_text(cls, value: str, info):
        if value != value.strip() or _unsafe(value):
            raise ValueError(f"{info.field_name}_invalid")
        if info.field_name == "operation_id" and any(char in value for char in "\n\r\t"):
            raise ValueError("operation_id_invalid")
        return value


class LabMemoryUnpinPreflightRequest(_ExactModel):
    schema: Literal["relaylm.lab.memory_unpin_preflight_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)

    @field_validator("reason", "operation_id")
    @classmethod
    def validate_bounded_text(cls, value: str, info):
        if value != value.strip() or _unsafe(value):
            raise ValueError(f"{info.field_name}_invalid")
        if info.field_name == "operation_id" and any(char in value for char in "\n\r\t"):
            raise ValueError("operation_id_invalid")
        return value


class LabMemoryPinApplyRequest(_ExactModel):
    schema: Literal["relaylm.lab.memory_pin_apply_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)
    apply_token: str = Field(min_length=1, max_length=8192)

    @field_validator("reason", "operation_id", "apply_token")
    @classmethod
    def validate_token_text(cls, value: str, info):
        if value != value.strip() or _unsafe(value):
            raise ValueError(f"{info.field_name}_invalid")
        if info.field_name in {"operation_id", "apply_token"} and any(char in value for char in "\n\r\t"):
            raise ValueError(f"{info.field_name}_invalid")
        return value


class LabMemoryUnpinApplyRequest(_ExactModel):
    schema: Literal["relaylm.lab.memory_unpin_apply_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)
    apply_token: str = Field(min_length=1, max_length=8192)

    @field_validator("reason", "operation_id", "apply_token")
    @classmethod
    def validate_token_text(cls, value: str, info):
        if value != value.strip() or _unsafe(value):
            raise ValueError(f"{info.field_name}_invalid")
        if info.field_name in {"operation_id", "apply_token"} and any(char in value for char in "\n\r\t"):
            raise ValueError(f"{info.field_name}_invalid")
        return value


def _unsafe(value: str) -> bool:
    return any(ord(char) < 32 or ord(char) in {0x2028, 0x2029} or 0xD800 <= ord(char) <= 0xDFFF for char in value)


__all__ = [
    "LabMemoryPinApplyRequest",
    "LabMemoryPinPreflightRequest",
    "LabMemoryUnpinApplyRequest",
    "LabMemoryUnpinPreflightRequest",
]
