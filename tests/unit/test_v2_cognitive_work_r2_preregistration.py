from __future__ import annotations

import json
import re

import pytest

from relaylm.v2_interventions import ResourceVector
from tools.v2_cognitive_work_r2_preregistration import (
    REGIMES,
    TASKS_PER_REGIME,
    TOTAL_TASKS,
    OperationResult,
    R2PreregistrationError,
    TaskOperationBank,
    a0_policy,
    a1_policy,
    a3_oracle,
    allocator_messages,
    build_preregistration,
    counterfactual_outcome,
    derive_root_seed,
    generate_tasks,
    interpret_r2,
    paired_bootstrap_interval,
    paired_directional_exact_pvalue,
    parse_answer,
    parse_operation,
    physical_call_plan,
    revision_messages,
)


_COMMIT_A = "1" * 40
_COMMIT_B = "2" * 40


def _task(preregistration, regime: str):
    return next(task for task in preregistration.tasks if task.hidden_regime == regime)


def _vector(count: int) -> tuple[bool, ...]:
    return tuple(index < count for index in range(TOTAL_TASKS))


def _user_payload(messages: tuple[dict[str, str], ...]) -> dict[str, object]:
    value = json.loads(messages[1]["content"])
    assert isinstance(value, dict)
    return value


def test_r2_root_seed_requires_exact_merged_commit_identity():
    assert derive_root_seed(_COMMIT_A).startswith("sha256:")
    assert derive_root_seed(_COMMIT_A.upper()) == derive_root_seed(_COMMIT_A)
    with pytest.raises(R2PreregistrationError, match="40 hex"):
        derive_root_seed("not-a-commit")


def test_r2_generator_is_deterministic_balanced_and_commit_bound():
    a = build_preregistration(_COMMIT_A)
    again = build_preregistration(_COMMIT_A)
    b = build_preregistration(_COMMIT_B)

    assert a == again
    assert a.digest == again.digest
    assert a.digest != b.digest
    assert a.tasks != b.tasks
    assert len(a.tasks) == TOTAL_TASKS == 40
    assert len({task.task_id for task in a.tasks}) == TOTAL_TASKS
    for regime in REGIMES:
        assert sum(task.hidden_regime == regime for task in a.tasks) == TASKS_PER_REGIME == 8


def test_r2_task_ids_are_opaque_and_do_not_encode_hidden_regime():
    preregistration = build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        assert re.fullmatch(r"r2-[0-9a-f]{16}", task.task_id)
        assert task.hidden_regime not in task.task_id
        assert not any(regime in task.task_id for regime in REGIMES)


def test_r2_public_task_surface_quarantines_hidden_evaluator_information():
    preregistration = build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        public = task.public_mapping()
        assert "hidden_regime" not in public
        assert "expected_answer" not in public
        serialized = json.dumps(public, ensure_ascii=False, sort_keys=True)
        assert task.hidden_regime not in serialized
        if task.retrieval_packet is not None:
            assert task.retrieval_packet not in serialized
        if task.observation_packet is not None:
            assert task.observation_packet not in serialized


def test_r2_external_packet_availability_is_exactly_one_regime_each():
    tasks = generate_tasks(_COMMIT_A)
    retrieval = [task for task in tasks if task.retrieval_available]
    observation = [task for task in tasks if task.observation_available]
    assert len(retrieval) == len(observation) == 8
    assert {task.hidden_regime for task in retrieval} == {"RETRIEVAL_BENEFICIAL"}
    assert {task.hidden_regime for task in observation} == {"OBSERVATION_BENEFICIAL"}
    assert all(not (task.retrieval_available and task.observation_available) for task in tasks)


def test_r2_fixed_and_cheap_policies_are_frozen():
    preregistration = build_preregistration(_COMMIT_A)
    assert all(a0_policy(task) == "THINK" for task in preregistration.tasks)
    assert a1_policy(_task(preregistration, "EASY_SATURATED")) == "ZERO"
    assert a1_policy(_task(preregistration, "DEPTH_BENEFICIAL")) == "ZERO"
    assert a1_policy(_task(preregistration, "UNCERTAINTY_TRAP")) == "ZERO"
    assert a1_policy(_task(preregistration, "RETRIEVAL_BENEFICIAL")) == "RETRIEVE"
    assert a1_policy(_task(preregistration, "OBSERVATION_BENEFICIAL")) == "OBSERVE"


def test_r2_allocator_message_cannot_see_evaluator_fields_or_packets():
    preregistration = build_preregistration(_COMMIT_A)
    for task in preregistration.tasks:
        messages = allocator_messages(task, base_answer="BASE")
        payload = _user_payload(messages)
        assert "hidden_regime" not in payload
        assert "expected_answer" not in payload
        assert "retrieval_packet" not in payload
        assert "observation_packet" not in payload
        serialized = json.dumps(messages, ensure_ascii=False, sort_keys=True)
        if task.retrieval_packet is not None:
            assert task.retrieval_packet not in serialized
        if task.observation_packet is not None:
            assert task.observation_packet not in serialized


def test_r2_packet_appears_only_after_the_corresponding_operation_is_selected():
    preregistration = build_preregistration(_COMMIT_A)
    retrieval = _task(preregistration, "RETRIEVAL_BENEFICIAL")
    observation = _task(preregistration, "OBSERVATION_BENEFICIAL")

    think = json.dumps(revision_messages(retrieval, base_answer="UNKNOWN", operation="THINK"))
    retrieved = json.dumps(
        revision_messages(retrieval, base_answer="UNKNOWN", operation="RETRIEVE")
    )
    observed = json.dumps(
        revision_messages(observation, base_answer="UNKNOWN", operation="OBSERVE")
    )

    assert retrieval.retrieval_packet not in think
    assert retrieval.retrieval_packet in retrieved
    assert observation.observation_packet in observed
    with pytest.raises(R2PreregistrationError, match="not legal"):
        revision_messages(retrieval, base_answer="UNKNOWN", operation="OBSERVE")


def test_r2_strict_answer_parser_rejects_extra_and_duplicate_members():
    assert parse_answer('{"answer":"2"}') == "2"
    with pytest.raises(R2PreregistrationError, match="exactly answer"):
        parse_answer('{"answer":"2","extra":1}')
    with pytest.raises(R2PreregistrationError, match="strict JSON"):
        parse_answer('{"answer":"2","answer":"3"}')
    with pytest.raises(R2PreregistrationError, match="non-empty"):
        parse_answer('{"answer":""}')


def test_r2_strict_allocator_parser_rejects_illegal_external_operation():
    preregistration = build_preregistration(_COMMIT_A)
    easy = _task(preregistration, "EASY_SATURATED")
    retrieval = _task(preregistration, "RETRIEVAL_BENEFICIAL")
    assert parse_operation('{"operation":"ZERO"}', task=easy) == "ZERO"
    assert parse_operation('{"operation":"RETRIEVE"}', task=retrieval) == "RETRIEVE"
    with pytest.raises(R2PreregistrationError, match="illegal operation"):
        parse_operation('{"operation":"RETRIEVE"}', task=easy)
    with pytest.raises(R2PreregistrationError, match="exactly operation"):
        parse_operation('{"operation":"ZERO","why":"cheap"}', task=easy)


def test_r2_physical_call_plan_freezes_allocator_before_nonpublic_bank_results():
    preregistration = build_preregistration(_COMMIT_A)
    plan = physical_call_plan(preregistration.tasks)
    assert len(plan) == 136
    assert sum(item.role == "BASE" for item in plan) == 40
    assert sum(item.role == "A2_ALLOCATE" for item in plan) == 40
    assert sum(item.role == "BANK" and item.operation == "THINK" for item in plan) == 40
    assert sum(item.role == "BANK" and item.operation == "RETRIEVE" for item in plan) == 8
    assert sum(item.role == "BANK" and item.operation == "OBSERVE" for item in plan) == 8

    for task in preregistration.tasks:
        task_plan = [item for item in plan if item.task_id == task.task_id]
        assert task_plan[0].role == "BASE"
        assert task_plan[1].role == "A2_ALLOCATE"
        assert task_plan[2].role == "BANK"
        assert task_plan[2].operation == "THINK"
        assert all(item.role == "BANK" for item in task_plan[2:])


def test_r2_budget_is_derived_from_protocol_structure_not_r1_token_overflow():
    preregistration = build_preregistration(_COMMIT_A)
    budget = preregistration.budget

    assert budget.task_count == 40
    assert budget.bank_provider_call_max == 96
    assert budget.a2_allocator_call_max == 40
    assert budget.physical_provider_call_max == 136
    assert budget.treatment_call_ceiling_per_arm == 120
    assert budget.retrieval_unit_ceiling_per_arm == 8
    assert budget.observation_unit_ceiling_per_arm == 8
    assert budget.context_limit == 8192
    assert budget.aggregate_input_token_ceiling is None
    assert budget.aggregate_output_token_ceiling is None
    assert budget.automatic_retry is False
    assert budget.semantic_retry is False


def test_r2_counterfactual_outcome_charges_base_allocator_and_selected_work():
    task = _task(build_preregistration(_COMMIT_A), "RETRIEVAL_BENEFICIAL")
    bank = TaskOperationBank(
        task_id=task.task_id,
        base_answer="UNKNOWN",
        base_correct=False,
        base_cost=ResourceVector(calls=1, input_tokens=70, output_tokens=5),
        operation_results=(
            OperationResult(
                "THINK",
                "UNKNOWN",
                False,
                ResourceVector(calls=1, input_tokens=90, output_tokens=5),
            ),
            OperationResult(
                "RETRIEVE",
                task.expected_answer,
                True,
                ResourceVector(
                    calls=1,
                    input_tokens=110,
                    output_tokens=7,
                    retrieval_units=1,
                ),
            ),
        ),
    )
    allocator = ResourceVector(calls=1, input_tokens=150, output_tokens=4)
    outcome = counterfactual_outcome(
        task,
        bank,
        arm_id="A2",
        operation="RETRIEVE",
        allocator_cost=allocator,
    )
    assert outcome.correct is True
    assert outcome.cost == ResourceVector(
        calls=3,
        input_tokens=330,
        output_tokens=16,
        retrieval_units=1,
    )


def test_r2_zero_counterfactual_has_no_task_work_call():
    task = _task(build_preregistration(_COMMIT_A), "EASY_SATURATED")
    bank = TaskOperationBank(
        task_id=task.task_id,
        base_answer=task.expected_answer,
        base_correct=True,
        base_cost=ResourceVector(calls=1, input_tokens=70, output_tokens=5),
        operation_results=(
            OperationResult(
                "THINK",
                task.expected_answer,
                True,
                ResourceVector(calls=1, input_tokens=80, output_tokens=5),
            ),
        ),
    )
    outcome = counterfactual_outcome(task, bank, arm_id="A1", operation="ZERO")
    assert outcome.cost.calls == 1
    assert outcome.cost.input_tokens == 70


def test_r2_oracle_is_quarantined_counterfactual_and_tie_breaks_to_cheapest_correct():
    task = _task(build_preregistration(_COMMIT_A), "RETRIEVAL_BENEFICIAL")
    bank = TaskOperationBank(
        task_id=task.task_id,
        base_answer="UNKNOWN",
        base_correct=False,
        base_cost=ResourceVector(calls=1),
        operation_results=(
            OperationResult(
                "THINK",
                task.expected_answer,
                True,
                ResourceVector(calls=1, input_tokens=20),
            ),
            OperationResult(
                "RETRIEVE",
                task.expected_answer,
                True,
                ResourceVector(calls=1, input_tokens=30, retrieval_units=1),
            ),
        ),
    )
    decision = a3_oracle(task, bank)
    assert decision.operation == "THINK"
    assert decision.correct is True
    assert decision.oracle_no_headroom is False


def test_r2_oracle_records_no_headroom_instead_of_inventing_success():
    task = _task(build_preregistration(_COMMIT_A), "DEPTH_BENEFICIAL")
    bank = TaskOperationBank(
        task_id=task.task_id,
        base_answer="wrong",
        base_correct=False,
        base_cost=ResourceVector(calls=1),
        operation_results=(
            OperationResult("THINK", "still-wrong", False, ResourceVector(calls=1)),
        ),
    )
    decision = a3_oracle(task, bank)
    assert decision.correct is False
    assert decision.oracle_no_headroom is True
    assert decision.operation == "ZERO"


def test_r2_exact_paired_test_is_directional_and_preregistered():
    treatment = (True,) * 5 + (False,) * 35
    baseline = (False,) * 40
    assert paired_directional_exact_pvalue(treatment, baseline) == pytest.approx(0.03125)
    assert paired_directional_exact_pvalue(baseline, treatment) > 0.95


def test_r2_bootstrap_interval_is_deterministic_for_the_frozen_seed():
    treatment = _vector(30)
    baseline = _vector(20)
    a = paired_bootstrap_interval(treatment, baseline, seed="frozen", resamples=200)
    b = paired_bootstrap_interval(treatment, baseline, seed="frozen", resamples=200)
    assert a == b
    assert a[0] <= 0.25 <= a[1]


def test_r2_interpretation_no_oracle_headroom_relative_to_fixed_baseline():
    result = interpret_r2(
        {arm: _vector(30) for arm in ("A0", "A1", "A2", "A3")},
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.category == "NO_ORACLE_HEADROOM"
    assert result.oracle_headroom_over_fixed == 0


def test_r2_interpretation_heuristic_sufficient_when_a1_captures_fixed_headroom():
    result = interpret_r2(
        {
            "A0": _vector(25),
            "A1": _vector(34),
            "A2": _vector(32),
            "A3": _vector(35),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.oracle_headroom_over_fixed == 10
    assert result.category == "HEURISTIC_SUFFICIENT"


def test_r2_interpretation_allocator_failure_when_oracle_headroom_remains():
    result = interpret_r2(
        {
            "A0": _vector(24),
            "A1": _vector(25),
            "A2": _vector(27),
            "A3": _vector(35),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.oracle_headroom_over_fixed == 11
    assert result.category == "ALLOCATOR_FAILURE"


def test_r2_interpretation_adaptive_signal_requires_both_baselines():
    result = interpret_r2(
        {
            "A0": _vector(20),
            "A1": _vector(20),
            "A2": _vector(30),
            "A3": _vector(35),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=0,
        protocol_invalid_count=0,
    )
    assert result.category == "ADAPTIVE_SIGNAL"
    assert result.a2_minus_a0 == result.a2_minus_a1 == 10
    assert result.a2_vs_a0_pvalue <= 0.05
    assert result.a2_vs_a1_pvalue <= 0.05


def test_r2_interpretation_hard_failure_is_inconclusive():
    result = interpret_r2(
        {
            "A0": _vector(20),
            "A1": _vector(20),
            "A2": _vector(30),
            "A3": _vector(35),
        },
        resource_accounting_complete=True,
        hard_constraint_violations=1,
        protocol_invalid_count=0,
    )
    assert result.category == "INCONCLUSIVE"


def test_r2_interpretation_rejects_oracle_below_deployable_accuracy():
    with pytest.raises(R2PreregistrationError, match="oracle accuracy"):
        interpret_r2(
            {
                "A0": _vector(31),
                "A1": _vector(20),
                "A2": _vector(30),
                "A3": _vector(29),
            },
            resource_accounting_complete=True,
            hard_constraint_violations=0,
            protocol_invalid_count=0,
        )
