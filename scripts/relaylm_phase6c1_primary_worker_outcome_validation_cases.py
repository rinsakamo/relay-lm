"""Fail-closed validation cases for the Phase 6-C1 outcome smoke."""
from dataclasses import dataclass, replace

from relaylm_phase6c1_primary_worker_outcome_support import (
    M3E_SCHEMA,
    assert_shape,
    classify,
    m3e_applied,
    m3g,
    m3h,
)


def run_validation_cases() -> tuple[object, ...]:
    no_audit = classify(m3e_applied(), m3g(), None)
    assert_shape(
        no_audit,
        transition_kind="blocked_invalid_input",
        terminal=False,
    )
    incompatible = classify(
        replace(
            m3e_applied(),
            status="blocked",
            page_applied=False,
            writes_memory=False,
        ),
        m3g(),
        m3h(),
    )
    assert_shape(
        incompatible,
        transition_kind="blocked_invalid_input",
        retryable=False,
    )
    unknown = classify(
        m3e_applied(),
        replace(m3g(), status="future_status"),
        None,
    )
    assert_shape(unknown, transition_kind="blocked_invalid_input")
    wrong_schema = classify(
        replace(
            m3e_applied(),
            schema_version="relaymem.primary_page_write_apply.v9",
        ),
        m3g(),
        m3h(),
    )
    assert_shape(wrong_schema, transition_kind="blocked_invalid_input")

    @dataclass(frozen=True)
    class M3eWithUnknownField:
        schema_version: str = M3E_SCHEMA
        status: str = "applied"
        unknown_field: str = "not-accepted"

    unknown_field = classify(M3eWithUnknownField(), m3g(), m3h())
    assert "exact_m3e_result_required" in unknown_field.blocked_reason_ids
    bool_int = classify(
        replace(m3e_applied(), page_applied=1),
        m3g(),
        m3h(),
    )
    assert "m3e_page_applied_invalid" in bool_int.blocked_reason_ids
    generic = classify(m3e_applied().__dict__, m3g(), m3h())
    assert "exact_m3e_result_required" in generic.blocked_reason_ids
    return (
        no_audit,
        incompatible,
        unknown,
        wrong_schema,
        unknown_field,
        bool_int,
        generic,
    )
