from __future__ import annotations

import asyncio
from unittest.mock import patch

import relaylm.evaluation_continuity_lifecycle as evaluation_module
from relaylm.evaluation_continuity_lifecycle import evaluate_continuity_lifecycle


def test_continuity_lifecycle_component_uses_real_validation_api() -> None:
    with patch.object(
        evaluation_module,
        "apply_continuity_candidates",
        wraps=evaluation_module.apply_continuity_candidates,
    ) as validator:
        result = asyncio.run(evaluate_continuity_lifecycle())

    assert validator.call_count == 7
    assert result.scenario_id == "continuity_lifecycle"
    assert result.status == "pass"
    assert {check.check_id for check in result.checks} == {
        "known_user_assertion_admitted",
        "accepted_value_is_deeply_immutable",
        "duplicate_is_noop_without_lifetime_refresh",
        "changed_same_key_supersedes",
        "unknown_source_is_rejected",
        "same_kind_resolve_removes_item",
        "expiry_advances_before_candidate_processing",
        "capacity_evicts_oldest_deterministically",
    }
    assert {check.boundary for check in result.checks} == {"continuity_validation"}
    assert result.metrics == {
        "validation_call_count": 7,
        "accepted_decision_count": 4,
        "noop_decision_count": 1,
        "rejected_decision_count": 1,
        "expired_item_count": 1,
        "evicted_item_count": 1,
    }
