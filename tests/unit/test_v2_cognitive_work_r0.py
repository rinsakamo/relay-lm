from __future__ import annotations

import pytest

from relaylm.v2_interventions import Operation, ResourceVector
from tools.v2_cognitive_work_r0 import (
    AllocationArm,
    CognitiveWorkAdmissionError,
    CognitiveWorkCampaign,
    ExecutionBinding,
    admit_arm,
    assert_matched_deployable_arms,
    freeze_cognitive_start,
)
from tools.v2_event_semantic_kernel import EventSemanticKernel


def _binding(**overrides: object) -> ExecutionBinding:
    values: dict[str, object] = {
        "model_identity": "model@artifact",
        "runtime_identity": "provider@runtime",
        "hardware_identity": "gpu@class",
        "tokenizer_identity": "tokenizer@revision",
        "template_identity": "chat-template@digest",
        "context_limit": 8192,
        "decoding_identity": "temperature=0;top_p=1",
        "reasoning_identity": "reasoning=off",
    }
    values.update(overrides)
    return ExecutionBinding(**values)  # type: ignore[arg-type]


def _campaign(
    *,
    kernel: EventSemanticKernel | None = None,
    execution: ExecutionBinding | None = None,
    task_digest: str = "task-family@digest",
    ordinary_information_ids: tuple[str, ...] = ("task", "public-constraint"),
    operations: tuple[Operation, ...] | None = None,
    envelope: ResourceVector | None = None,
) -> CognitiveWorkCampaign:
    kernel = kernel or EventSemanticKernel()
    if not kernel.occurrences:
        kernel.ingest("task observation", logical_ingress_id="task-ingress")
    operations = operations or (
        Operation("THINK", ResourceVector(calls=1, input_tokens=20, output_tokens=10)),
        Operation("RETRIEVE", ResourceVector(retrieval_units=1, input_tokens=10)),
        Operation("CRYSTALLIZE", ResourceVector(calls=1, input_tokens=15, output_tokens=5)),
    )
    return CognitiveWorkCampaign(
        start=freeze_cognitive_start(kernel, lineage_id="lineage-1"),
        execution=execution or _binding(),
        task_digest=task_digest,
        ordinary_information_ids=ordinary_information_ids,
        operations=operations,
        envelope=envelope
        or ResourceVector(
            calls=4,
            input_tokens=100,
            output_tokens=50,
            latency_units=10,
            observation_units=2,
            retrieval_units=4,
            memory_units=4,
        ),
    )


def _arm(
    arm_id: str,
    policy_class: str,
    *,
    plan: tuple[str, ...] = (),
    decision_cost: ResourceVector = ResourceVector(),
    information: tuple[str, ...] = ("task", "public-constraint"),
    privileged: bool = False,
) -> AllocationArm:
    return AllocationArm(
        arm_id=arm_id,
        policy_class=policy_class,
        plan=plan,
        decision_cost=decision_cost,
        initial_information_ids=information,
        privileged=privileged,
    )


def test_r0_start_preserves_repeated_equal_content_as_distinct_occurrences():
    kernel = EventSemanticKernel()
    a = kernel.ingest("進めて")
    b = kernel.ingest("進めて")
    start = freeze_cognitive_start(kernel, lineage_id="lineage")
    assert start.occurrence_ids == (a.occurrence_id, b.occurrence_id)
    assert a.occurrence_id != b.occurrence_id


def test_r0_start_freezes_exact_parent_head_and_canonical_digest():
    kernel = EventSemanticKernel()
    before = freeze_cognitive_start(kernel, lineage_id="lineage")
    kernel.settle(kernel.propose_value("progress", 1))
    after = freeze_cognitive_start(kernel, lineage_id="lineage")
    assert before.head_id != after.head_id
    assert before.canonical_digest != after.canonical_digest


def test_r0_deployable_arms_share_campaign_but_may_choose_different_work():
    campaign = _campaign()
    fixed = admit_arm(campaign, _arm("A0", "fixed", plan=("THINK",)))
    heuristic = admit_arm(campaign, _arm("A1", "heuristic", plan=("RETRIEVE",)))
    adaptive = admit_arm(
        campaign,
        _arm(
            "A2",
            "adaptive",
            plan=("THINK", "CRYSTALLIZE"),
            decision_cost=ResourceVector(calls=1, input_tokens=5, output_tokens=2),
        ),
    )
    matched = assert_matched_deployable_arms(fixed, heuristic, adaptive)
    assert matched.campaign_fingerprint == campaign.fingerprint
    assert matched.arm_ids == ("A0", "A1", "A2")
    assert fixed.start == heuristic.start == adaptive.start
    assert fixed.operation_names == heuristic.operation_names == adaptive.operation_names
    assert fixed.envelope == heuristic.envelope == adaptive.envelope
    assert fixed.ordinary_information_ids == heuristic.ordinary_information_ids
    assert fixed.ordinary_information_ids == adaptive.ordinary_information_ids
    assert fixed.plan != heuristic.plan != adaptive.plan


def test_r0_adaptive_decision_cost_is_charged_not_free():
    campaign = _campaign()
    decision = ResourceVector(calls=1, input_tokens=7, output_tokens=3, latency_units=1)
    adaptive = admit_arm(
        campaign,
        _arm("A2", "adaptive", plan=("THINK",), decision_cost=decision),
    )
    think = next(operation for operation in campaign.operations if operation.name == "THINK")
    assert adaptive.resource_total == decision + think.cost


def test_r0_zero_work_is_legal_without_sleep_state():
    campaign = _campaign()
    zero = admit_arm(campaign, _arm("A0", "fixed", plan=()))
    assert zero.plan == ()
    assert zero.resource_total.is_zero()
    assert all("sleep" not in name.lower() for name in zero.operation_names)


def test_r0_crystallization_is_optional_work_not_mandatory_phase():
    campaign = _campaign()
    skip = admit_arm(campaign, _arm("A0", "fixed", plan=("THINK",)))
    use = admit_arm(campaign, _arm("A1", "heuristic", plan=("CRYSTALLIZE",)))
    assert "CRYSTALLIZE" in skip.operation_names
    assert "CRYSTALLIZE" not in skip.plan
    assert use.plan == ("CRYSTALLIZE",)


def test_r0_deployable_arm_cannot_receive_extra_initial_information():
    campaign = _campaign()
    with pytest.raises(CognitiveWorkAdmissionError, match="initial information differs"):
        admit_arm(
            campaign,
            _arm(
                "A2",
                "adaptive",
                information=("task", "public-constraint", "hidden-answer"),
            ),
        )


def test_r0_deployable_arm_cannot_drop_ordinary_information():
    campaign = _campaign()
    with pytest.raises(CognitiveWorkAdmissionError, match="initial information differs"):
        admit_arm(campaign, _arm("A1", "heuristic", information=("task",)))


def test_r0_non_oracle_policy_cannot_claim_privilege():
    campaign = _campaign()
    with pytest.raises(CognitiveWorkAdmissionError, match="cannot claim privileged"):
        admit_arm(campaign, _arm("A2", "adaptive", privileged=True))


def test_r0_oracle_must_be_explicitly_privileged():
    campaign = _campaign()
    with pytest.raises(CognitiveWorkAdmissionError, match="oracle arm must be privileged"):
        admit_arm(campaign, _arm("A3", "oracle"))


def test_r0_oracle_may_receive_quarantined_extra_information_but_not_enter_comparison():
    campaign = _campaign()
    oracle = admit_arm(
        campaign,
        _arm(
            "A3",
            "oracle",
            information=("task", "public-constraint", "oracle-label"),
            privileged=True,
        ),
    )
    fixed = admit_arm(campaign, _arm("A0", "fixed"))
    assert oracle.privileged
    with pytest.raises(CognitiveWorkAdmissionError, match="cannot enter deployable"):
        assert_matched_deployable_arms(fixed, oracle)


def test_r0_deployable_arm_cannot_select_privileged_operation():
    campaign = _campaign(
        operations=(
            Operation("THINK", ResourceVector(calls=1)),
            Operation("ORACLE_PEEK", ResourceVector(observation_units=1), privileged=True),
        )
    )
    with pytest.raises(CognitiveWorkAdmissionError, match="selected privileged operation"):
        admit_arm(campaign, _arm("A2", "adaptive", plan=("ORACLE_PEEK",)))


def test_r0_undeclared_operation_fails_closed():
    campaign = _campaign()
    with pytest.raises(CognitiveWorkAdmissionError, match="undeclared cognitive operation"):
        admit_arm(campaign, _arm("A0", "fixed", plan=("MAGIC",)))


def test_r0_resource_envelope_includes_policy_and_operation_cost():
    campaign = _campaign(envelope=ResourceVector(calls=1, input_tokens=100, output_tokens=100))
    with pytest.raises(CognitiveWorkAdmissionError, match="resource envelope rejected"):
        admit_arm(
            campaign,
            _arm(
                "A2",
                "adaptive",
                plan=("THINK",),
                decision_cost=ResourceVector(calls=1),
            ),
        )


def test_r0_execution_binding_is_part_of_campaign_identity():
    a = _campaign(execution=_binding(runtime_identity="runtime-A"))
    b = _campaign(execution=_binding(runtime_identity="runtime-B"))
    assert a.fingerprint != b.fingerprint


def test_r0_task_information_and_operation_surface_are_part_of_campaign_identity():
    base = _campaign()
    changed_task = _campaign(task_digest="other-task")
    changed_info = _campaign(ordinary_information_ids=("task", "different-public-info"))
    changed_ops = _campaign(
        operations=(Operation("THINK", ResourceVector(calls=1)),)
    )
    assert len({base.fingerprint, changed_task.fingerprint, changed_info.fingerprint, changed_ops.fingerprint}) == 4


def test_r0_matched_comparison_rejects_different_start_head():
    kernel_a = EventSemanticKernel()
    kernel_a.ingest("task observation", logical_ingress_id="task-ingress")
    campaign_a = _campaign(kernel=kernel_a)

    kernel_b = EventSemanticKernel()
    kernel_b.ingest("task observation", logical_ingress_id="task-ingress")
    kernel_b.settle(kernel_b.propose_value("hidden", "different"))
    campaign_b = _campaign(kernel=kernel_b)

    a = admit_arm(campaign_a, _arm("A0", "fixed"))
    b = admit_arm(campaign_b, _arm("A1", "heuristic"))
    with pytest.raises(CognitiveWorkAdmissionError, match="differ outside allocation"):
        assert_matched_deployable_arms(a, b)


def test_r0_matched_comparison_rejects_different_physical_binding():
    a_campaign = _campaign(execution=_binding(hardware_identity="hardware-A"))
    b_campaign = _campaign(execution=_binding(hardware_identity="hardware-B"))
    a = admit_arm(a_campaign, _arm("A0", "fixed"))
    b = admit_arm(b_campaign, _arm("A1", "heuristic"))
    with pytest.raises(CognitiveWorkAdmissionError, match="differ outside allocation"):
        assert_matched_deployable_arms(a, b)


def test_r0_execution_binding_rejects_missing_identity_or_invalid_context():
    with pytest.raises(ValueError, match="must not be empty"):
        _binding(model_identity="")
    with pytest.raises(ValueError, match="context_limit must be positive"):
        _binding(context_limit=0)
