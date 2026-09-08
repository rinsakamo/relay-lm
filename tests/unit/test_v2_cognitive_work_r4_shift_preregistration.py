from __future__ import annotations

import json
import re

import pytest

from tools import v2_cognitive_work_r2_structured_preregistration as r2
from tools import v2_cognitive_work_r3_uniform_preregistration as r3
from tools import v2_cognitive_work_r4_shift_preregistration as r4
from tools import v2_cognitive_work_structured_output_qualification as sopq


_COMMIT_A = "7" * 40
_COMMIT_B = "8" * 40


def _user_payload(messages: tuple[dict[str, str], ...]) -> dict[str, object]:
    value = json.loads(messages[1]["content"])
    assert isinstance(value, dict)
    return value


def _vector(true_count: int) -> tuple[bool, ...]:
    return (True,) * true_count + (False,) * (r4.TASK_COUNT - true_count)


def test_r4_seed_domain_is_fresh_commit_bound_and_distinct_from_r2_r3():
    root = r4.derive_root_seed(_COMMIT_A)
    assert root.startswith("sha256:")
    assert root == r4.derive_root_seed(_COMMIT_A.upper())
    assert root != r2.derive_root_seed(_COMMIT_A)
    assert root != r3.derive_root_seed(_COMMIT_A)
    assert root != r4.derive_root_seed(_COMMIT_B)
    assert r4.ROOT_SEED_DOMAIN not in {r2.ROOT_SEED_DOMAIN, r3.ROOT_SEED_DOMAIN}
    with pytest.raises(r4.R4PreregistrationError, match="40 hex"):
        r4.derive_root_seed("not-a-commit")


def test_r4_generates_balanced_20_task_shift_with_both_public_operations():
    preregistration = r4.build_preregistration(_COMMIT_A)
    task_ids = {task.task_id for task in preregistration.tasks}
    assert len(preregistration.tasks) == r4.TASK_COUNT == 20
    assert len(task_ids) == 20
    counts = {regime: 0 for regime in r4.REGIMES}
    for task in preregistration.tasks:
        counts[task.hidden_regime] += 1
        assert re.fullmatch(r"r4s-[0-9a-f]{16}", task.task_id)
        assert task.retrieval_available is True
        assert task.observation_available is True
        assert task.retrieval_packet
        assert task.observation_packet
        assert task.legal_operations() == ("ZERO", "THINK", "RETRIEVE", "OBSERVE")
        assert task.hidden_regime not in task.task_id
    assert set(counts.values()) == {r4.TASKS_PER_REGIME}


def test_r4_relevant_packet_semantics_and_auxiliary_packets_do_not_leak_target():
    preregistration = r4.build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        if task.hidden_regime == "RETRIEVAL_BENEFICIAL":
            assert task.expected_answer in task.retrieval_packet
            assert task.expected_answer not in task.observation_packet
        elif task.hidden_regime == "OBSERVATION_BENEFICIAL":
            assert task.expected_answer in task.observation_packet
            assert task.expected_answer not in task.retrieval_packet
        else:
            assert task.expected_answer not in task.retrieval_packet
            assert task.expected_answer not in task.observation_packet


def test_r4_preserves_r2_tested_policies_messages_parsers_and_statistics():
    assert r4.CONTEXT_LIMIT == r2.CONTEXT_LIMIT == 8192
    assert r4.BOOTSTRAP_RESAMPLES == r2.BOOTSTRAP_RESAMPLES == 10_000
    assert r4.EXACT_TEST_ALPHA == r2.EXACT_TEST_ALPHA == 0.05
    assert r4.MATERIAL_TASK_GAIN == r2.MATERIAL_TASK_GAIN == 4
    assert r4.HEURISTIC_ORACLE_GAP_MAX == r2.HEURISTIC_ORACLE_GAP_MAX == 2
    assert r4.a0_policy is r2.a0_policy
    assert r4.a1_policy is r2.a1_policy
    assert r4.a3_oracle is r2.a3_oracle
    assert r4.counterfactual_outcome is r2.counterfactual_outcome
    assert r4.answer_messages is r2.answer_messages
    assert r4.revision_messages is r2.revision_messages
    assert r4.allocator_messages is r2.allocator_messages
    assert r4.parse_answer is r2.parse_answer
    assert r4.parse_operation is r2.parse_operation
    assert r4.paired_directional_exact_pvalue is r2.paired_directional_exact_pvalue
    assert r4.paired_bootstrap_interval is r2.paired_bootstrap_interval


def test_r4_frozen_heuristic_routes_retrieve_on_every_shift_task():
    preregistration = r4.build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        assert r4.a0_policy(task) == "THINK"
        assert r4.a1_policy(task) == "RETRIEVE"


def test_r4_model_messages_quarantine_hidden_truth_and_reveal_only_purchased_packet():
    preregistration = r4.build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        answer = r4.answer_messages(task)
        allocator = r4.allocator_messages(task, base_answer="UNKNOWN")
        for messages in (answer, allocator):
            payload = _user_payload(messages)
            assert "hidden_regime" not in payload
            assert "expected_answer" not in payload
            serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
            assert task.hidden_regime not in serialized
            assert task.retrieval_packet not in serialized
            assert task.observation_packet not in serialized

        think = json.dumps(
            r4.revision_messages(task, base_answer="UNKNOWN", operation="THINK"),
            ensure_ascii=False,
        )
        retrieved = json.dumps(
            r4.revision_messages(task, base_answer="UNKNOWN", operation="RETRIEVE"),
            ensure_ascii=False,
        )
        observed = json.dumps(
            r4.revision_messages(task, base_answer="UNKNOWN", operation="OBSERVE"),
            ensure_ascii=False,
        )
        assert task.retrieval_packet not in think
        assert task.observation_packet not in think
        assert task.retrieval_packet in retrieved
        assert task.observation_packet not in retrieved
        assert task.observation_packet in observed
        assert task.retrieval_packet not in observed


def test_r4_call_plan_is_exactly_100_calls_and_uniform_five_call_shape():
    preregistration = r4.build_preregistration(_COMMIT_A)
    plan = r4.physical_call_plan(preregistration.tasks)
    assert len(plan) == 100
    assert sum(item.role == "BASE" for item in plan) == 20
    assert sum(item.role == "A2_ALLOCATE" for item in plan) == 20
    assert sum(item.role == "BANK" and item.operation == "THINK" for item in plan) == 20
    assert sum(item.role == "BANK" and item.operation == "RETRIEVE" for item in plan) == 20
    assert sum(item.role == "BANK" and item.operation == "OBSERVE" for item in plan) == 20
    for offset in range(0, len(plan), 5):
        task_plan = plan[offset : offset + 5]
        assert [item.role for item in task_plan] == [
            "BASE",
            "A2_ALLOCATE",
            "BANK",
            "BANK",
            "BANK",
        ]
        assert [item.operation for item in task_plan] == [
            None,
            None,
            "THINK",
            "RETRIEVE",
            "OBSERVE",
        ]
        assert len({item.task_id for item in task_plan}) == 1


def test_r4_budget_is_derived_from_100_call_shift_plan():
    budget = r4.build_preregistration(_COMMIT_A).budget
    assert budget.task_count == 20
    assert budget.bank_provider_call_max == 80
    assert budget.a2_allocator_call_max == 20
    assert budget.physical_provider_call_max == 100
    assert budget.treatment_call_ceiling_per_arm == 60
    assert budget.retrieval_unit_ceiling_per_arm == 20
    assert budget.observation_unit_ceiling_per_arm == 20
    assert budget.context_limit == 8192
    assert budget.aggregate_input_token_ceiling is None
    assert budget.aggregate_output_token_ceiling is None
    assert budget.automatic_retry is False
    assert budget.semantic_retry is False


def test_r4_uses_exact_qualified_structured_transport_per_call():
    r4.validate_qualified_transport()
    plan = r4.physical_call_plan(r4.build_preregistration(_COMMIT_A).tasks)
    kinds = [r4.schema_kind_for_call(item) for item in plan]
    assert kinds.count("answer") == 80
    assert kinds.count("operation") == 20
    assert r4.QUALIFIED_TRANSPORT_VERSION == sopq.QUALIFICATION_VERSION
    for item, kind in zip(plan, kinds, strict=True):
        expected = "operation" if item.role == "A2_ALLOCATE" else "answer"
        assert kind == expected
        assert r4.response_format_for_call(item) == sopq.response_format_for(kind)


def test_r4_interpretation_marks_heuristic_transfer_sufficient_near_oracle():
    result = r4.interpret_r4_shift(
        {"A0": _vector(10), "A1": _vector(18), "A2": _vector(17), "A3": _vector(20)},
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.category == "HEURISTIC_TRANSFER_SUFFICIENT"
    assert result.shift_headroom_over_heuristic == 2


def test_r4_interpretation_detects_adaptive_transfer_signal():
    result = r4.interpret_r4_shift(
        {"A0": _vector(10), "A1": _vector(10), "A2": _vector(15), "A3": _vector(20)},
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.adaptive_minus_heuristic == 5
    assert result.a2_vs_a1_pvalue <= r4.EXACT_TEST_ALPHA
    assert result.category == "ADAPTIVE_TRANSFER_SIGNAL"


def test_r4_interpretation_detects_fixed_sufficiency_and_uncaptured_shift_headroom():
    fixed = r4.interpret_r4_shift(
        {"A0": _vector(16), "A1": _vector(8), "A2": _vector(11), "A3": _vector(20)},
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert fixed.category == "SIMPLE_FIXED_BASELINE_SUFFICIENT"

    uncaptured = r4.interpret_r4_shift(
        {"A0": _vector(10), "A1": _vector(10), "A2": _vector(12), "A3": _vector(20)},
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert uncaptured.category == "SHIFT_HEADROOM_UNCAPTURED"


def test_r4_interpretation_distinguishes_nonmaterial_shift_and_fails_closed():
    no_material = r4.interpret_r4_shift(
        {"A0": _vector(17), "A1": _vector(17), "A2": _vector(17), "A3": _vector(20)},
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert no_material.category == "NO_MATERIAL_SHIFT_HEADROOM"

    invalid = r4.interpret_r4_shift(
        {arm: _vector(20) for arm in ("A0", "A1", "A2", "A3")},
        resource_accounting_complete=False,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert invalid.category == "INCONCLUSIVE"

    with pytest.raises(r4.R4PreregistrationError, match="exactly 20 booleans"):
        r4.interpret_r4_shift(
            {"A0": (True,), "A1": (True,), "A2": (True,), "A3": (True,)},
            resource_accounting_complete=True,
            hard_constraint_violations=0,
            protocol_invalid_count=0,
        )


def test_r4_digest_commits_to_shift_design_transport_and_fresh_identity():
    preregistration = r4.build_preregistration(_COMMIT_A)
    assert r4.PREREGISTRATION_VERSION == "relaylm2-cognitive-work-r4-availability-shift-v1"
    assert preregistration.root_seed != r2.build_preregistration(_COMMIT_A).root_seed
    assert preregistration.root_seed != r3.build_preregistration(_COMMIT_A).root_seed
    assert preregistration.digest.startswith("sha256:")
    assert preregistration.digest != r2.build_preregistration(_COMMIT_A).digest
    assert preregistration.digest != r3.build_preregistration(_COMMIT_A).digest
