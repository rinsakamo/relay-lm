from __future__ import annotations

import json
import re

import pytest

from tools import v2_cognitive_work_r2_structured_preregistration as r2
from tools import v2_cognitive_work_structured_output_qualification as sopq
from tools import v2_cognitive_work_r3_uniform_preregistration as r3


_COMMIT_A = "5" * 40
_COMMIT_B = "6" * 40


def _user_payload(messages: tuple[dict[str, str], ...]) -> dict[str, object]:
    value = json.loads(messages[1]["content"])
    assert isinstance(value, dict)
    return value


def _vector(true_count: int) -> tuple[bool, ...]:
    return (True,) * true_count + (False,) * (r3.TASK_COUNT - true_count)


def test_r3_seed_domain_is_fresh_commit_bound_and_distinct_from_r2():
    root = r3.derive_root_seed(_COMMIT_A)
    assert root.startswith("sha256:")
    assert root == r3.derive_root_seed(_COMMIT_A.upper())
    assert root != r2.derive_root_seed(_COMMIT_A)
    assert root != r3.derive_root_seed(_COMMIT_B)
    assert r3.ROOT_SEED_DOMAIN != r2.ROOT_SEED_DOMAIN
    with pytest.raises(r3.R3PreregistrationError, match="40 hex"):
        r3.derive_root_seed("not-a-commit")


def test_r3_generates_exactly_16_fresh_uniform_retrieval_tasks():
    preregistration = r3.build_preregistration(_COMMIT_A)
    task_ids = {task.task_id for task in preregistration.tasks}
    r2_ids = {task.task_id for task in r2.build_preregistration(_COMMIT_A).tasks}

    assert len(preregistration.tasks) == r3.TASK_COUNT == 16
    assert len(task_ids) == 16
    assert task_ids.isdisjoint(r2_ids)
    for task in preregistration.tasks:
        assert re.fullmatch(r"r3u-[0-9a-f]{16}", task.task_id)
        assert task.hidden_regime == r3.UNIFORM_REGIME
        assert task.retrieval_available is True
        assert task.observation_available is False
        assert task.retrieval_packet is not None
        assert task.observation_packet is None
        assert task.hidden_regime not in task.task_id


def test_r3_preserves_r2_tested_policies_messages_parsers_and_statistics():
    assert r3.CONTEXT_LIMIT == r2.CONTEXT_LIMIT == 8192
    assert r3.BOOTSTRAP_RESAMPLES == r2.BOOTSTRAP_RESAMPLES == 10_000
    assert r3.EXACT_TEST_ALPHA == r2.EXACT_TEST_ALPHA == 0.05
    assert r3.MATERIAL_TASK_GAIN == r2.MATERIAL_TASK_GAIN == 4
    assert r3.HEURISTIC_ORACLE_GAP_MAX == r2.HEURISTIC_ORACLE_GAP_MAX == 2
    assert r3.a0_policy is r2.a0_policy
    assert r3.a1_policy is r2.a1_policy
    assert r3.a3_oracle is r2.a3_oracle
    assert r3.counterfactual_outcome is r2.counterfactual_outcome
    assert r3.answer_messages is r2.answer_messages
    assert r3.revision_messages is r2.revision_messages
    assert r3.allocator_messages is r2.allocator_messages
    assert r3.parse_answer is r2.parse_answer
    assert r3.parse_operation is r2.parse_operation
    assert r3.paired_directional_exact_pvalue is r2.paired_directional_exact_pvalue
    assert r3.paired_bootstrap_interval is r2.paired_bootstrap_interval


def test_r3_policy_behavior_is_fixed_think_heuristic_retrieve():
    preregistration = r3.build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        assert r3.a0_policy(task) == "THINK"
        assert r3.a1_policy(task) == "RETRIEVE"
        assert task.legal_operations() == ("ZERO", "THINK", "RETRIEVE")


def test_r3_model_messages_keep_uniform_label_and_evaluator_truth_quarantined():
    preregistration = r3.build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        answer = r3.answer_messages(task)
        allocator = r3.allocator_messages(task, base_answer="UNKNOWN")
        for messages in (answer, allocator):
            payload = _user_payload(messages)
            assert "hidden_regime" not in payload
            assert "expected_answer" not in payload
            serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
            assert r3.UNIFORM_REGIME not in serialized
            assert task.expected_answer not in serialized
            assert task.retrieval_packet not in serialized

        think = json.dumps(
            r3.revision_messages(task, base_answer="UNKNOWN", operation="THINK"),
            ensure_ascii=False,
        )
        retrieved = json.dumps(
            r3.revision_messages(task, base_answer="UNKNOWN", operation="RETRIEVE"),
            ensure_ascii=False,
        )
        assert task.retrieval_packet not in think
        assert task.retrieval_packet in retrieved


def test_r3_call_plan_is_exactly_64_calls_with_no_observation():
    preregistration = r3.build_preregistration(_COMMIT_A)
    plan = r3.physical_call_plan(preregistration.tasks)

    assert len(plan) == 64
    assert sum(item.role == "BASE" for item in plan) == 16
    assert sum(item.role == "A2_ALLOCATE" for item in plan) == 16
    assert sum(item.role == "BANK" and item.operation == "THINK" for item in plan) == 16
    assert sum(item.role == "BANK" and item.operation == "RETRIEVE" for item in plan) == 16
    assert sum(item.role == "BANK" and item.operation == "OBSERVE" for item in plan) == 0

    for offset in range(0, len(plan), 4):
        task_plan = plan[offset : offset + 4]
        assert [item.role for item in task_plan] == ["BASE", "A2_ALLOCATE", "BANK", "BANK"]
        assert [item.operation for item in task_plan] == [None, None, "THINK", "RETRIEVE"]
        assert len({item.task_id for item in task_plan}) == 1


def test_r3_budget_is_derived_from_uniform_64_call_plan():
    budget = r3.build_preregistration(_COMMIT_A).budget
    assert budget.task_count == 16
    assert budget.bank_provider_call_max == 48
    assert budget.a2_allocator_call_max == 16
    assert budget.physical_provider_call_max == 64
    assert budget.treatment_call_ceiling_per_arm == 48
    assert budget.retrieval_unit_ceiling_per_arm == 16
    assert budget.observation_unit_ceiling_per_arm == 0
    assert budget.context_limit == 8192
    assert budget.aggregate_input_token_ceiling is None
    assert budget.aggregate_output_token_ceiling is None
    assert budget.automatic_retry is False
    assert budget.semantic_retry is False


def test_r3_uses_exact_qualified_structured_transport_per_call():
    r3.validate_qualified_transport()
    plan = r3.physical_call_plan(r3.build_preregistration(_COMMIT_A).tasks)
    kinds = [r3.schema_kind_for_call(item) for item in plan]
    assert kinds.count("answer") == 48
    assert kinds.count("operation") == 16
    assert r3.QUALIFIED_TRANSPORT_VERSION == sopq.QUALIFICATION_VERSION
    for item, kind in zip(plan, kinds, strict=True):
        expected = "operation" if item.role == "A2_ALLOCATE" else "answer"
        assert kind == expected
        assert r3.response_format_for_call(item) == sopq.response_format_for(kind)


def test_r3_interpretation_marks_heuristic_sufficient_when_a1_is_near_oracle():
    result = r3.interpret_r3_uniform(
        {
            "A0": _vector(0),
            "A1": _vector(16),
            "A2": _vector(15),
            "A3": _vector(16),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.category == "HEURISTIC_SUFFICIENT_UNIFORM"
    assert result.oracle_headroom_over_fixed == 16
    assert result.heuristic_oracle_gap == 0
    assert result.adaptive_minus_heuristic == -1


def test_r3_interpretation_detects_preregistered_uniform_null_violation():
    result = r3.interpret_r3_uniform(
        {
            "A0": _vector(0),
            "A1": _vector(0),
            "A2": _vector(5),
            "A3": _vector(16),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.adaptive_minus_heuristic == 5
    assert result.a2_vs_a1_pvalue <= r3.EXACT_TEST_ALPHA
    assert result.category == "UNIFORM_NULL_VIOLATION"


def test_r3_interpretation_distinguishes_no_headroom_and_generic_null_consistency():
    no_headroom = r3.interpret_r3_uniform(
        {
            "A0": _vector(13),
            "A1": _vector(16),
            "A2": _vector(16),
            "A3": _vector(16),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert no_headroom.category == "NO_USEFUL_WORK_HEADROOM"

    null_consistent = r3.interpret_r3_uniform(
        {
            "A0": _vector(0),
            "A1": _vector(10),
            "A2": _vector(12),
            "A3": _vector(16),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert null_consistent.category == "UNIFORM_NULL_CONSISTENT"
    assert null_consistent.adaptive_minus_heuristic == 2
    assert null_consistent.heuristic_oracle_gap == 6


def test_r3_interpretation_fails_closed_on_accounting_or_protocol_defect():
    values = {arm: _vector(16) for arm in ("A0", "A1", "A2", "A3")}
    result = r3.interpret_r3_uniform(
        values,
        resource_accounting_complete=False,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.category == "INCONCLUSIVE"

    with pytest.raises(r3.R3PreregistrationError, match="exactly 16 booleans"):
        r3.interpret_r3_uniform(
            {"A0": (True,), "A1": (True,), "A2": (True,), "A3": (True,)},
            resource_accounting_complete=True,
            hard_constraint_violations=0,
            protocol_invalid_count=0,
        )


def test_r3_digest_commits_to_uniform_design_transport_and_fresh_identity():
    preregistration = r3.build_preregistration(_COMMIT_A)
    assert r3.PREREGISTRATION_VERSION == "relaylm2-cognitive-work-r3-uniform-v1"
    assert preregistration.root_seed != r2.build_preregistration(_COMMIT_A).root_seed
    assert preregistration.digest.startswith("sha256:")
    assert preregistration.digest != r2.build_preregistration(_COMMIT_A).digest
