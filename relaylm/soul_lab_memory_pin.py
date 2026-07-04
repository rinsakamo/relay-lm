"""Strict SOUL Lab request contracts for Primary MEM Pin / Unpin."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from .soul_lab_contracts import StrictLabRequestModel, validate_lab_request_text


class LabMemoryPinPreflightRequest(StrictLabRequestModel):
    schema: Literal["relaylm.lab.memory_pin_preflight_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)

    @field_validator("reason", "operation_id")
    @classmethod
    def validate_bounded_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


class LabMemoryUnpinPreflightRequest(StrictLabRequestModel):
    schema: Literal["relaylm.lab.memory_unpin_preflight_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)

    @field_validator("reason", "operation_id")
    @classmethod
    def validate_bounded_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


class LabMemoryPinApplyRequest(StrictLabRequestModel):
    schema: Literal["relaylm.lab.memory_pin_apply_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)
    apply_token: str = Field(min_length=1, max_length=8192)

    @field_validator("reason", "operation_id", "apply_token")
    @classmethod
    def validate_token_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


class LabMemoryUnpinApplyRequest(StrictLabRequestModel):
    schema: Literal["relaylm.lab.memory_unpin_apply_request.v0"]
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)
    apply_token: str = Field(min_length=1, max_length=8192)

    @field_validator("reason", "operation_id", "apply_token")
    @classmethod
    def validate_token_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


__all__ = [
    "LabMemoryPinApplyRequest",
    "LabMemoryPinPreflightRequest",
    "LabMemoryUnpinApplyRequest",
    "LabMemoryUnpinPreflightRequest",
]
