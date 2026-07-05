"""Strict SOUL Lab request contracts for Held Apply / Discard governance."""
from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from .soul_lab_contracts import StrictLabRequestModel, validate_lab_request_text

# StrictLabRequestModel preserves ConfigDict(extra="forbid", strict=True).


class LabHeldGovernancePreflightRequest(StrictLabRequestModel):
    schema_: Literal["relaylm.lab.held_governance_preflight_request.v0"] = Field(alias="schema")
    operation_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)

    @field_validator("operation_id", "reason")
    @classmethod
    def validate_bounded_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


class LabHeldGovernanceDecisionRequest(StrictLabRequestModel):
    schema_: Literal["relaylm.lab.held_governance_decision_request.v0"] = Field(alias="schema")
    operation_id: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1, max_length=512)
    apply_token: str = Field(min_length=1, max_length=8192)

    @field_validator("operation_id", "reason", "apply_token")
    @classmethod
    def validate_token_text(cls, value: str, info):
        return validate_lab_request_text(value, info.field_name)


__all__ = ["LabHeldGovernanceDecisionRequest", "LabHeldGovernancePreflightRequest"]
