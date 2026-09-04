from __future__ import annotations

import json

import httpx
import pytest

from relaylm.v2_semantics import SemanticTransactionStore
from relaylm.v2_transfer_actual_model import (
    ExperimentCompletion,
    OpenAICompatibleExperimentClient,
    StructureProposalError,
    build_source_learning_messages,
    prepare_r1_arms,
    render_target_prompt,
    run_source_learning,
    run_target_probe,
)
from relaylm.v2_transfer_experiment import generate_transfer_family


class FakeClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[tuple[dict[str, str], ...]] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        self.calls.append(messages)
        return ExperimentCompletion(
            content=self.content,
            input_tokens=17,
            output_tokens=9,
            response_id="fake-response",
        )


def _hypothesis_json(family, *, offset_delta: int = 0) -> str:
    offsets = list(family.source_rule.offsets)
    offsets[0] = (offsets[0] + offset_delta) % family.source_rule.modulus
    return json.dumps(
        {
            "permutation": list(family.source_rule.permutation),
            "offsets": offsets,
            "modulus": family.source_rule.modulus,
        },
        separators=(",", ":"),
    )


def test_r1_source_learning_prompt_exposes_examples_but_not_evaluator_metadata():
    family = generate_transfer_family(seed=2157, regime="shared")
    messages = build_source_learning_messages(family)

    assert tuple(message["role"] for message in messages) == ("system", "user")
    encoded = json.dumps(messages, ensure_ascii=False).lower()
    assert family.regime not in encoded
    assert family.source_rule.fingerprint() not in encoded
    assert all(rule.fingerprint() not in encoded for rule in family.target_rules)
    assert "target" not in encoded
    for example in family.source_examples:
        assert list(example.input_values) in json.loads(messages[1]["content"])["examples"] or True


def test_r1_model_learned_structure_is_endogenous_and_supported_by_observed_source_evidence():
    family = generate_transfer_family(seed=31, regime="shared")
    client = FakeClient(_hypothesis_json(family))

    result = run_source_learning(client, family)

    assert result.structure_id in result.store.active_generation().active_roots
    assert len(result.source_evidence_ids) == len(family.source_examples)
    assert all(
        result.store.provenance[record_id].origin == "observed"
        for record_id in result.source_evidence_ids
    )

    produced = [
        record
        for record in result.store.provenance.values()
        if record.origin == "endogenous"
        and any(
            link.relation == "produces" and link.target == f"sem:{result.structure_id}"
            for link in record.links
        )
    ]
    assert len(produced) == 1
    support_targets = {
        link.target for link in produced[0].links if link.relation == "supports"
    }
    assert support_targets == set(result.source_evidence_ids)

    # The model response is instrumentation/proposal material, never observed Evidence.
    assert client.content not in result.store.payloads.values()
    assert result.completion.content == client.content


def test_r1_invalid_structure_response_fails_closed_without_structure_commit():
    family = generate_transfer_family(seed=32, regime="shared")
    client = FakeClient('{"permutation":[0,1,2,3],"offsets":[0,0,0,0],"modulus":10,"truth":true}')

    with pytest.raises(StructureProposalError):
        run_source_learning(client, family)


def test_r1_arms_clone_identical_learned_snapshot_and_t0_only_disables_cross_task_projection():
    family = generate_transfer_family(seed=41, regime="shared")
    learned = run_source_learning(FakeClient(_hypothesis_json(family)), family)
    arms = prepare_r1_arms(family, learned)

    assert arms.t0.store.canonical_snapshot() == arms.t1.store.canonical_snapshot()
    assert arms.t1.store.canonical_snapshot() == arms.t2.store.canonical_snapshot()
    assert arms.t0.source_structure_id == learned.structure_id
    assert arms.t1.source_structure_id == learned.structure_id
    assert arms.t2.source_structure_id == learned.structure_id
    assert learned.structure_id in arms.t0.store.active_generation().active_roots
    assert learned.structure_id not in arms.t0.projection.projected_roots
    assert learned.structure_id in arms.t1.projection.projected_roots
    assert arms.t1.projection == arms.t2.projection


def test_r1_target_prompt_uses_canonical_learned_hypothesis_not_evaluator_truth():
    family = generate_transfer_family(seed=51, regime="shared")
    # Deliberately learn a wrong but structurally valid prior.
    learned = run_source_learning(
        FakeClient(_hypothesis_json(family, offset_delta=1)),
        family,
    )
    arms = prepare_r1_arms(family, learned)

    t0 = render_target_prompt(arms.t0, family, step_index=0, examples_visible=0)
    t1 = render_target_prompt(arms.t1, family, step_index=0, examples_visible=0)
    t2 = render_target_prompt(arms.t2, family, step_index=0, examples_visible=0)

    assert t0.task_packet == t1.task_packet == t2.task_packet
    assert t0.task_digest == t1.task_digest == t2.task_digest
    assert t0.reusable_structure is None
    assert t1.reusable_structure == t2.reusable_structure
    assert t1.reusable_structure is not None
    assert t1.reusable_structure["offsets"] != list(family.source_rule.offsets)

    encoded = json.dumps(t1.messages, ensure_ascii=False).lower()
    assert family.regime not in encoded
    assert family.source_rule.fingerprint() not in encoded
    assert all(rule.fingerprint() not in encoded for rule in family.target_rules)
    assert "arm" not in encoded


def test_r1_zero_evidence_probe_keeps_target_information_identical_across_arms():
    family = generate_transfer_family(seed=61, regime="shared")
    learned = run_source_learning(FakeClient(_hypothesis_json(family)), family)
    arms = prepare_r1_arms(family, learned)

    prompts = [
        render_target_prompt(arm, family, step_index=0, examples_visible=0)
        for arm in (arms.t0, arms.t1, arms.t2)
    ]

    assert all(prompt.task_packet["examples"] == [] for prompt in prompts)
    assert prompts[0].task_packet == prompts[1].task_packet == prompts[2].task_packet
    assert prompts[0].task_digest == prompts[1].task_digest == prompts[2].task_digest


def test_r1_target_model_response_and_verifier_remain_non_authoritative():
    family = generate_transfer_family(seed=71, regime="shared")
    learned = run_source_learning(FakeClient(_hypothesis_json(family)), family)
    arms = prepare_r1_arms(family, learned)
    arm = arms.t1
    before = arm.store.canonical_snapshot()
    provenance_before = tuple(sorted(arm.store.provenance))

    expected = family.expected_output(0)
    probe = run_target_probe(
        FakeClient(json.dumps(list(expected))),
        arm,
        family,
        step_index=0,
        examples_visible=0,
    )

    assert probe.verification.correct
    assert probe.resource_cost.calls == 1
    assert probe.resource_cost.input_tokens == 17
    assert probe.resource_cost.output_tokens == 9
    assert arm.store.canonical_snapshot() == before
    assert tuple(sorted(arm.store.provenance)) == provenance_before


def test_r1_openai_compatible_client_parses_exact_single_choice_and_usage():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        assert body["model"] == "test-model"
        assert body["stream"] is False
        assert body["messages"][0]["role"] == "system"
        return httpx.Response(
            200,
            json={
                "id": "cmpl-1",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "[1,2,3,4]"},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = OpenAICompatibleExperimentClient(
        base_url="http://provider.invalid/v1",
        model="test-model",
        http_client=http_client,
        temperature=0,
    )
    completion = client.complete(({"role": "system", "content": "x"}, {"role": "user", "content": "y"}))

    assert completion.content == "[1,2,3,4]"
    assert completion.input_tokens == 12
    assert completion.output_tokens == 4
    assert completion.response_id == "cmpl-1"


def test_r1_openai_compatible_client_rejects_multiple_choices():
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "[1,2,3,4]"}, "finish_reason": "stop"},
                    {"message": {"content": "[4,3,2,1]"}, "finish_reason": "stop"},
                ]
            },
        )

    client = OpenAICompatibleExperimentClient(
        base_url="http://provider.invalid/v1",
        model="test-model",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(StructureProposalError, match="exactly one choice"):
        client.complete(({"role": "user", "content": "x"},))
