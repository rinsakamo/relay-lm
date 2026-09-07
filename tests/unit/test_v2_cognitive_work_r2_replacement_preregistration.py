from __future__ import annotations

import json
import re

import pytest

from tools import v2_cognitive_work_r2_preregistration as original
from tools import v2_cognitive_work_r2_replacement_preregistration as replacement


_COMMIT_A = "1" * 40
_COMMIT_B = "2" * 40


def _task(preregistration, regime: str):
    return next(task for task in preregistration.tasks if task.hidden_regime == regime)


def _user_payload(messages: tuple[dict[str, str], ...]) -> dict[str, object]:
    value = json.loads(messages[1]["content"])
    assert isinstance(value, dict)
    return value


def test_replacement_answer_protocol_canonicalizes_string_or_integer_only():
    assert replacement.parse_answer('{"answer":"87"}') == "87"
    assert replacement.parse_answer('{"answer":87}') == "87"
    assert replacement.parse_answer('{"answer":" UNKNOWN "}') == "UNKNOWN"

    invalid = (
        '{"answer":true}',
        '{"answer":1.0}',
        '{"answer":null}',
        '{"answer":{}}',
        '{"answer":[]}',
        '{"answer":""}',
        '{"answer":"   "}',
    )
    for payload in invalid:
        with pytest.raises(replacement.R2PreregistrationError, match="string or integer"):
            replacement.parse_answer(payload)


def test_replacement_answer_protocol_remains_strict_json_and_one_key_only():
    with pytest.raises(replacement.R2PreregistrationError, match="exactly answer"):
        replacement.parse_answer('{"answer":"87","extra":1}')
    with pytest.raises(replacement.R2PreregistrationError, match="duplicate JSON member"):
        replacement.parse_answer('{"answer":"87","answer":"88"}')
    with pytest.raises(replacement.R2PreregistrationError, match="non-standard JSON"):
        replacement.parse_answer('{"answer":NaN}')
    with pytest.raises(replacement.R2PreregistrationError, match="non-standard JSON"):
        replacement.parse_answer('{"answer":Infinity}')


def test_replacement_seed_domain_is_new_deterministic_and_commit_bound():
    root = replacement.derive_root_seed(_COMMIT_A)
    assert root.startswith("sha256:")
    assert root == replacement.derive_root_seed(_COMMIT_A.upper())
    assert root != original.derive_root_seed(_COMMIT_A)
    assert root != replacement.derive_root_seed(_COMMIT_B)
    with pytest.raises(replacement.R2PreregistrationError, match="40 hex"):
        replacement.derive_root_seed("not-a-commit")


def test_replacement_suite_is_unseen_relative_to_original_seed_domain():
    old = original.build_preregistration(_COMMIT_A)
    new = replacement.build_preregistration(_COMMIT_A)

    assert old.root_seed != new.root_seed
    assert {task.task_id for task in old.tasks}.isdisjoint(
        {task.task_id for task in new.tasks}
    )
    assert len(new.tasks) == replacement.TOTAL_TASKS == 40
    assert len({task.task_id for task in new.tasks}) == 40
    for task in new.tasks:
        assert re.fullmatch(r"r2-[0-9a-f]{16}", task.task_id)
        assert task.hidden_regime not in task.task_id


def test_replacement_preserves_scientific_constants_and_policy_functions():
    assert replacement.REGIMES == original.REGIMES
    assert replacement.OPERATIONS == original.OPERATIONS
    assert replacement.TASKS_PER_REGIME == original.TASKS_PER_REGIME == 8
    assert replacement.TOTAL_TASKS == original.TOTAL_TASKS == 40
    assert replacement.CONTEXT_LIMIT == original.CONTEXT_LIMIT == 8192
    assert replacement.BOOTSTRAP_RESAMPLES == original.BOOTSTRAP_RESAMPLES == 10_000
    assert replacement.EXACT_TEST_ALPHA == original.EXACT_TEST_ALPHA
    assert replacement.MATERIAL_TASK_GAIN == original.MATERIAL_TASK_GAIN
    assert replacement.HEURISTIC_ORACLE_GAP_MAX == original.HEURISTIC_ORACLE_GAP_MAX
    assert replacement.a0_policy is original.a0_policy
    assert replacement.a1_policy is original.a1_policy
    assert replacement.a3_oracle is original.a3_oracle
    assert replacement.interpret_r2 is original.interpret_r2
    assert replacement.paired_bootstrap_interval is original.paired_bootstrap_interval
    assert replacement.paired_directional_exact_pvalue is original.paired_directional_exact_pvalue


def test_replacement_generator_preserves_balanced_regimes_and_external_units():
    preregistration = replacement.build_preregistration(_COMMIT_A)
    for regime in replacement.REGIMES:
        assert sum(task.hidden_regime == regime for task in preregistration.tasks) == 8
    assert sum(task.retrieval_available for task in preregistration.tasks) == 8
    assert sum(task.observation_available for task in preregistration.tasks) == 8
    assert all(
        not (task.retrieval_available and task.observation_available)
        for task in preregistration.tasks
    )


def test_replacement_preserves_frozen_a0_a1_policy_meaning():
    preregistration = replacement.build_preregistration(_COMMIT_A)
    assert all(replacement.a0_policy(task) == "THINK" for task in preregistration.tasks)
    assert replacement.a1_policy(_task(preregistration, "EASY_SATURATED")) == "ZERO"
    assert replacement.a1_policy(_task(preregistration, "DEPTH_BENEFICIAL")) == "ZERO"
    assert replacement.a1_policy(_task(preregistration, "UNCERTAINTY_TRAP")) == "ZERO"
    assert replacement.a1_policy(_task(preregistration, "RETRIEVAL_BENEFICIAL")) == "RETRIEVE"
    assert replacement.a1_policy(_task(preregistration, "OBSERVATION_BENEFICIAL")) == "OBSERVE"


def test_replacement_model_messages_keep_evaluator_truth_quarantined():
    preregistration = replacement.build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        answer = replacement.answer_messages(task)
        allocator = replacement.allocator_messages(task, base_answer="BASE")
        for messages in (answer, allocator):
            payload = _user_payload(messages)
            assert "hidden_regime" not in payload
            assert "expected_answer" not in payload
            serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
            assert task.hidden_regime not in serialized
            if task.retrieval_packet is not None:
                assert task.retrieval_packet not in serialized
            if task.observation_packet is not None:
                assert task.observation_packet not in serialized


def test_replacement_packet_still_appears_only_after_selected_external_operation():
    preregistration = replacement.build_preregistration(_COMMIT_A)
    retrieval = _task(preregistration, "RETRIEVAL_BENEFICIAL")
    observation = _task(preregistration, "OBSERVATION_BENEFICIAL")

    think = json.dumps(
        replacement.revision_messages(
            retrieval,
            base_answer="UNKNOWN",
            operation="THINK",
        )
    )
    retrieved = json.dumps(
        replacement.revision_messages(
            retrieval,
            base_answer="UNKNOWN",
            operation="RETRIEVE",
        )
    )
    observed = json.dumps(
        replacement.revision_messages(
            observation,
            base_answer="UNKNOWN",
            operation="OBSERVE",
        )
    )

    assert retrieval.retrieval_packet not in think
    assert retrieval.retrieval_packet in retrieved
    assert observation.observation_packet in observed


def test_replacement_call_plan_and_budget_shape_remain_exactly_frozen():
    preregistration = replacement.build_preregistration(_COMMIT_A)
    plan = replacement.physical_call_plan(preregistration.tasks)
    budget = preregistration.budget

    assert len(plan) == 136
    assert sum(item.role == "BASE" for item in plan) == 40
    assert sum(item.role == "A2_ALLOCATE" for item in plan) == 40
    assert sum(item.role == "BANK" and item.operation == "THINK" for item in plan) == 40
    assert sum(item.role == "BANK" and item.operation == "RETRIEVE" for item in plan) == 8
    assert sum(item.role == "BANK" and item.operation == "OBSERVE" for item in plan) == 8

    assert budget.physical_provider_call_max == 136
    assert budget.treatment_call_ceiling_per_arm == 120
    assert budget.retrieval_unit_ceiling_per_arm == 8
    assert budget.observation_unit_ceiling_per_arm == 8
    assert budget.context_limit == 8192
    assert budget.aggregate_input_token_ceiling is None
    assert budget.aggregate_output_token_ceiling is None
    assert budget.automatic_retry is False
    assert budget.semantic_retry is False


def test_replacement_answer_instructions_truthfully_describe_scalar_domain():
    task = _task(replacement.build_preregistration(_COMMIT_A), "EASY_SATURATED")
    base_system = replacement.answer_messages(task)[0]["content"]
    think_system = replacement.revision_messages(
        task,
        base_answer="87",
        operation="THINK",
    )[0]["content"]
    for instruction in (base_system, think_system):
        assert "non-empty JSON string or a JSON integer" in instruction
        assert "exactly one key named answer" in instruction


def test_replacement_digest_versions_answer_protocol_and_seed_domain():
    preregistration = replacement.build_preregistration(_COMMIT_A)
    assert replacement.ANSWER_PROTOCOL_VERSION == "canonical-string-or-integer-v2"
    assert replacement.ROOT_SEED_DOMAIN != replacement.ORIGINAL_ROOT_SEED_DOMAIN
    assert preregistration.digest.startswith("sha256:")
