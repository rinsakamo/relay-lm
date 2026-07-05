"""Strict SOUL Lab request contracts for auditable Primary MEM Correct."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from .soul_lab_contracts import StrictLabRequestModel, validate_lab_request_text


class LabMemoryCorrectPreflightRequest(StrictLabRequestModel):
    schema_: Literal["relaylm.lab.memory_correct_preflight_request.v0"] = Field(alias="schema")
    expected_revision: int = Field(ge=1, le=2_147_483_647)
    corrected_title: str = Field(max_length=160)
    corrected_summary: str = Field(min_length=1, max_length=2048)
    reason: str = Field(min_length=1, max_length=512)
    operation_id: str = Field(min_length=1, max_length=128)

    @field_validator("corrected_title", "corrected_summary", "reason", "operation_id")
    @classmethod
    def validate_bounded_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


class LabMemoryCorrectApplyRequest(StrictLabRequestModel):
    schema_: Literal["relaylm.lab.memory_correct_apply_request.v0"] = Field(alias="schema")
    operation_id: str = Field(min_length=1, max_length=128)
    apply_token: str = Field(min_length=1, max_length=8192)
    expected_revision: int = Field(ge=1, le=2_147_483_647)

    @field_validator("operation_id", "apply_token")
    @classmethod
    def validate_token_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


__all__ = ["LabMemoryCorrectApplyRequest", "LabMemoryCorrectPreflightRequest"]
