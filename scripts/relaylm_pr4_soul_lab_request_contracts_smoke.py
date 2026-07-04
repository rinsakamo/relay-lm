"""Smoke-test shared SOUL Lab request contract helpers."""
from __future__ import annotations

from pydantic import ValidationError

from relaylm.soul_lab_contracts import (
    validate_apply_token,
    validate_memory_id,
    validate_operation_id,
    validate_reason,
)
from relaylm.soul_lab_held_governance import (
    LabHeldGovernanceDecisionRequest,
    LabHeldGovernancePreflightRequest,
)
from relaylm.soul_lab_memory_correction import (
    LabMemoryCorrectApplyRequest,
    LabMemoryCorrectPreflightRequest,
)
from relaylm.soul_lab_memory_forget import (
    LabMemoryForgetApplyRequest,
    LabMemoryForgetPreflightRequest,
)
from relaylm.soul_lab_memory_pin import (
    LabMemoryPinApplyRequest,
    LabMemoryPinPreflightRequest,
    LabMemoryUnpinApplyRequest,
    LabMemoryUnpinPreflightRequest,
)


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def expect_valid(model, payload: dict[str, object]) -> None:
    parsed = model.model_validate(payload)
    require(parsed.model_dump() == payload, (model, parsed.model_dump(), payload))


def expect_invalid(model, payload: dict[str, object]) -> None:
    try:
        model.model_validate(payload)
    except ValidationError:
        return
    raise AssertionError((model, payload))


def expect_value_error(func, value: str) -> None:
    try:
        func(value)
    except ValueError:
        return
    raise AssertionError((func.__name__, value))


def valid_pin_payload(schema: str) -> dict[str, object]:
    return {
        "schema": schema,
        "expected_revision": 1,
        "reason": "operator-requested",
        "operation_id": "op-1",
    }


def valid_apply_payload(schema: str) -> dict[str, object]:
    payload = valid_pin_payload(schema)
    payload["apply_token"] = "apply-token-1"
    return payload


def check_pin_unpin() -> None:
    expect_valid(
        LabMemoryPinPreflightRequest,
        valid_pin_payload("relaylm.lab.memory_pin_preflight_request.v0"),
    )
    expect_valid(
        LabMemoryUnpinPreflightRequest,
        valid_pin_payload("relaylm.lab.memory_unpin_preflight_request.v0"),
    )
    expect_valid(
        LabMemoryPinApplyRequest,
        valid_apply_payload("relaylm.lab.memory_pin_apply_request.v0"),
    )
    expect_valid(
        LabMemoryUnpinApplyRequest,
        valid_apply_payload("relaylm.lab.memory_unpin_apply_request.v0"),
    )
    payload = valid_pin_payload("relaylm.lab.memory_pin_preflight_request.v0")
    payload["extra"] = "forbidden"
    expect_invalid(LabMemoryPinPreflightRequest, payload)


def check_forget() -> None:
    preflight = {
        "schema": "relaylm.lab.memory_forget_preflight_request.v0",
        "expected_revision": 1,
        "expected_lifecycle_state": "active",
        "reason": "operator-requested",
        "operation_id": "op-1",
    }
    apply = dict(preflight)
    apply["schema"] = "relaylm.lab.memory_forget_apply_request.v0"
    apply["apply_token"] = "apply-token-1"
    expect_valid(LabMemoryForgetPreflightRequest, preflight)
    expect_valid(LabMemoryForgetApplyRequest, apply)


def check_correction() -> None:
    expect_valid(
        LabMemoryCorrectPreflightRequest,
        {
            "schema": "relaylm.lab.memory_correct_preflight_request.v0",
            "expected_revision": 1,
            "corrected_title": "Corrected title",
            "corrected_summary": "Corrected summary",
            "reason": "operator-requested",
            "operation_id": "op-1",
        },
    )
    expect_valid(
        LabMemoryCorrectApplyRequest,
        {
            "schema": "relaylm.lab.memory_correct_apply_request.v0",
            "operation_id": "op-1",
            "apply_token": "apply-token-1",
            "expected_revision": 1,
        },
    )


def check_held_governance() -> None:
    expect_valid(
        LabHeldGovernancePreflightRequest,
        {
            "schema": "relaylm.lab.held_governance_preflight_request.v0",
            "operation_id": "op-1",
            "reason": "operator-requested",
        },
    )
    expect_valid(
        LabHeldGovernanceDecisionRequest,
        {
            "schema": "relaylm.lab.held_governance_decision_request.v0",
            "operation_id": "op-1",
            "reason": "operator-requested",
            "apply_token": "apply-token-1",
        },
    )


def check_rejections() -> None:
    invalid = valid_pin_payload("relaylm.lab.memory_pin_preflight_request.v0")
    invalid["reason"] = " leading"
    expect_invalid(LabMemoryPinPreflightRequest, invalid)

    invalid = valid_pin_payload("relaylm.lab.memory_pin_preflight_request.v0")
    invalid["operation_id"] = "op\n1"
    expect_invalid(LabMemoryPinPreflightRequest, invalid)

    invalid_apply = valid_apply_payload("relaylm.lab.memory_pin_apply_request.v0")
    invalid_apply["apply_token"] = "token\t1"
    expect_invalid(LabMemoryPinApplyRequest, invalid_apply)

    expect_value_error(validate_memory_id, "not-a-sha")
    expect_value_error(validate_reason, " trailing ")
    expect_value_error(validate_operation_id, "op\n1")
    expect_value_error(validate_apply_token, "token\t1")
    require(validate_memory_id("a" * 64) == "a" * 64, "valid memory_id rejected")


def main() -> int:
    check_pin_unpin()
    check_forget()
    check_correction()
    check_held_governance()
    check_rejections()
    print("SOUL Lab request contract helper smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
