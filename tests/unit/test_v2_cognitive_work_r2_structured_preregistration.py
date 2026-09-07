from __future__ import annotations

import json
import re

import pytest

from tools import v2_cognitive_work_r2_preregistration as original
from tools import v2_cognitive_work_r2_replacement_preregistration as replacement
from tools import v2_cognitive_work_r2_structured_preregistration as structured
from tools import v2_cognitive_work_structured_output_qualification as sopq


_COMMIT_A = "3" * 40
_COMMIT_B = "4" * 40


def _task(preregistration, regime: str):
    return next(task for task in preregistration.tasks if task.hidden_regime == regime)


def _user_payload(messages: tuple[dict[str, str], ...]) -> dict[str, object]:
    value = json.loads(messages[1]["content"])
    assert isinstance(value, dict)
    return value


def test_structured_seed_domain_is_third_distinct_commit_bound_identity():
    root = structured.derive_root_seed(_COMMIT_A)
    assert root.startswith("sha256:")
    assert root == structured.derive_root_seed(_COMMIT_A.upper())
    assert root != original.derive_root_seed(_COMMIT_A)
    assert root != replacement.derive_root_seed(_COMMIT_A)
    assert root != structured.derive_root_seed(_COMMIT_B)
    assert structured.ROOT_SEED_DOMAIN != original.ROOT_SEED_DOMAIN
    assert structured.ROOT_SEED_DOMAIN != replacement.ROOT_SEED_DOMAIN
    with pytest.raises(structured.R2PreregistrationError, match="40 hex"):
        structured.derive_root_seed("not-a-commit")


def test_structured_suite_is_unseen_relative_to_both_prior_seed_domains():
    original_prereg = original.build_preregistration(_COMMIT_A)
    replacement_prereg = replacement.build_preregistration(_COMMIT_A)
    new = structured.build_preregistration(_COMMIT_A)

    new_ids = {task.task_id for task in new.tasks}
    assert new.root_seed != original_prereg.root_seed
    assert new.root_seed != replacement_prereg.root_seed
    assert new_ids.isdisjoint({task.task_id for task in original_prereg.tasks})
    assert new_ids.isdisjoint({task.task_id for task in replacement_prereg.tasks})
    assert len(new.tasks) == structured.TOTAL_TASKS == 40
    assert len(new_ids) == 40
    for task in new.tasks:
        assert re.fullmatch(r"r2-[0-9a-f]{16}", task.task_id)
        assert task.hidden_regime not in task.task_id


def test_structured_preserves_scientific_constants_policy_and_messages():
    assert structured.REGIMES == replacement.REGIMES == original.REGIMES
    assert structured.OPERATIONS == replacement.OPERATIONS == original.OPERATIONS
    assert structured.TASKS_PER_REGIME == replacement.TASKS_PER_REGIME == 8
    assert structured.TOTAL_TASKS == replacement.TOTAL_TASKS == 40
    assert structured.CONTEXT_LIMIT == replacement.CONTEXT_LIMIT == 8192
    assert structured.BOOTSTRAP_RESAMPLES == replacement.BOOTSTRAP_RESAMPLES == 10_000
    assert structured.EXACT_TEST_ALPHA == replacement.EXACT_TEST_ALPHA
    assert structured.MATERIAL_TASK_GAIN == replacement.MATERIAL_TASK_GAIN
    assert structured.HEURISTIC_ORACLE_GAP_MAX == replacement.HEURISTIC_ORACLE_GAP_MAX
    assert structured.a0_policy is replacement.a0_policy
    assert structured.a1_policy is replacement.a1_policy
    assert structured.a3_oracle is replacement.a3_oracle
    assert structured.interpret_r2 is replacement.interpret_r2
    assert structured.paired_bootstrap_interval is replacement.paired_bootstrap_interval
    assert structured.paired_directional_exact_pvalue is replacement.paired_directional_exact_pvalue
    assert structured.answer_messages is replacement.answer_messages
    assert structured.revision_messages is replacement.revision_messages
    assert structured.allocator_messages is replacement.allocator_messages


def test_structured_generator_preserves_balanced_regimes_and_external_units():
    preregistration = structured.build_preregistration(_COMMIT_A)
    for regime in structured.REGIMES:
        assert sum(task.hidden_regime == regime for task in preregistration.tasks) == 8
    assert sum(task.retrieval_available for task in preregistration.tasks) == 8
    assert sum(task.observation_available for task in preregistration.tasks) == 8
    assert all(
        not (task.retrieval_available and task.observation_available)
        for task in preregistration.tasks
    )


def test_structured_model_messages_keep_evaluator_truth_quarantined():
    preregistration = structured.build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        answer = structured.answer_messages(task)
        allocator = structured.allocator_messages(task, base_answer="BASE")
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


def test_structured_packet_still_appears_only_after_selected_external_operation():
    preregistration = structured.build_preregistration(_COMMIT_A)
    retrieval = _task(preregistration, "RETRIEVAL_BENEFICIAL")
    observation = _task(preregistration, "OBSERVATION_BENEFICIAL")

    think = json.dumps(
        structured.revision_messages(
            retrieval,
            base_answer="UNKNOWN",
            operation="THINK",
        )
    )
    retrieved = json.dumps(
        structured.revision_messages(
            retrieval,
            base_answer="UNKNOWN",
            operation="RETRIEVE",
        )
    )
    observed = json.dumps(
        structured.revision_messages(
            observation,
            base_answer="UNKNOWN",
            operation="OBSERVE",
        )
    )

    assert retrieval.retrieval_packet not in think
    assert retrieval.retrieval_packet in retrieved
    assert observation.observation_packet in observed


def test_structured_call_plan_and_budget_shape_remain_exactly_frozen():
    preregistration = structured.build_preregistration(_COMMIT_A)
    plan = structured.physical_call_plan(preregistration.tasks)
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


def test_structured_transport_is_exactly_the_physically_qualified_sopq_identity():
    structured.validate_qualified_transport()
    assert structured.QUALIFIED_TRANSPORT_VERSION == sopq.QUALIFICATION_VERSION
    assert sopq.ANSWER_SCHEMA_DIGEST == structured.EXPECTED_ANSWER_SCHEMA_DIGEST
    assert sopq.OPERATION_SCHEMA_DIGEST == structured.EXPECTED_OPERATION_SCHEMA_DIGEST
    assert (
        sopq.ANSWER_RESPONSE_FORMAT_DIGEST
        == structured.EXPECTED_ANSWER_RESPONSE_FORMAT_DIGEST
    )
    assert (
        sopq.OPERATION_RESPONSE_FORMAT_DIGEST
        == structured.EXPECTED_OPERATION_RESPONSE_FORMAT_DIGEST
    )
    assert sopq.QUALIFICATION_PLAN_DIGEST == structured.EXPECTED_QUALIFICATION_PLAN_DIGEST
    assert structured.QUALIFICATION_RESULT_SHA256.endswith(
        "1b0972ed92e6e3a8afad38c43b547877881935c7e7fe2318926677543aba8ed8"
    )
    assert structured.QUALIFICATION_IDENTITY_FINGERPRINT.endswith(
        "dcd432572adb8716d187dd899a0417ae0ff55ffb56047c53b25ea98e239268de"
    )
    assert structured.QUALIFIED_EXECUTION_BINDING_DIGEST.endswith(
        "8cad3e68cf6bfe1c4ea6db3d925569815c3326462fd1c359d2da073f5b8ca9d6"
    )


def test_structured_assigns_operation_schema_only_to_allocator_calls():
    preregistration = structured.build_preregistration(_COMMIT_A)
    plan = structured.physical_call_plan(preregistration.tasks)
    kinds = [structured.schema_kind_for_call(item) for item in plan]
    assert kinds.count("answer") == 96
    assert kinds.count("operation") == 40
    for item, kind in zip(plan, kinds, strict=True):
        expected = "operation" if item.role == "A2_ALLOCATE" else "answer"
        assert kind == expected
        assert structured.response_format_for_call(item) == sopq.response_format_for(kind)


def test_structured_parser_requires_qualified_answer_shape_and_legal_operation():
    assert structured.parse_answer('{"answer":"87"}') == "87"
    with pytest.raises(structured.R2PreregistrationError, match="non-empty string"):
        structured.parse_answer('{"answer":87}')
    with pytest.raises(structured.R2PreregistrationError, match="strict whole-response JSON"):
        structured.parse_answer('```json\n{"answer":"87"}\n```')

    retrieval = _task(structured.build_preregistration(_COMMIT_A), "RETRIEVAL_BENEFICIAL")
    assert structured.parse_operation('{"operation":"RETRIEVE"}', task=retrieval) == "RETRIEVE"
    with pytest.raises(structured.R2PreregistrationError, match="illegal"):
        structured.parse_operation('{"operation":"OBSERVE"}', task=retrieval)


def test_structured_digest_commits_to_transport_and_new_scientific_identity():
    preregistration = structured.build_preregistration(_COMMIT_A)
    assert structured.ANSWER_PROTOCOL_VERSION == "qualified-json-schema-string-v3"
    assert structured.ROOT_SEED_DOMAIN not in {
        original.ROOT_SEED_DOMAIN,
        replacement.ROOT_SEED_DOMAIN,
    }
    assert preregistration.digest.startswith("sha256:")
    assert preregistration.digest != replacement.build_preregistration(_COMMIT_A).digest
