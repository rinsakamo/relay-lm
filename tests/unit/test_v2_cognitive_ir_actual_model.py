from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_actual_model import (
    S2ExperimentError,
    S2_FORMATION_CALLS_PER_FAMILY,
    S2_TOTAL_CALLS_PER_FAMILY,
    build_s2_formation_messages,
    form_s2_representations,
    run_s2_smoke,
)
from relaylm.v2_cognitive_ir_experiment import (
    REPRESENTATION_KINDS,
    decode_semantic_payload,
    semantic_digest,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from relaylm.v2_transfer_experiment import generate_transfer_family


class QueueClient:
    def __init__(self, completions: list[ExperimentCompletion]) -> None:
        self.completions = list(completions)
        self.messages: list[tuple[dict[str, str], ...]] = []

    def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
        self.messages.append(messages)
        if not self.completions:
            raise AssertionError("unexpected provider call")
        return self.completions.pop(0)


def _completion(content: str, *, input_tokens: int = 11, output_tokens: int = 5) -> ExperimentCompletion:
    return ExperimentCompletion(
        content=content,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
    )


def _learned_rule_json(family) -> str:
    return json.dumps(
        {
            "permutation": list(family.source_rule.permutation),
            "offsets": list(family.source_rule.offsets),
            "modulus": family.modulus,
        },
        separators=(",", ":"),
    )


def _formation_client(family) -> QueueClient:
    return QueueClient(
        [
            _completion('{"summary":"Four observed input/output episodes with a consistent vector mapping."}'),
            _completion('{"gist":"A compact recurring vector relation appears across the observed episodes."}'),
            _completion(_learned_rule_json(family), input_tokens=13, output_tokens=7),
        ]
    )


def test_s2_formation_messages_share_exact_source_packet_without_oracle_rule():
    family = generate_transfer_family(seed=2211, regime="shared")

    messages = {
        kind: build_s2_formation_messages(kind, family)
        for kind in (
            "P2_ORDINARY_SUMMARY",
            "P3_SEMANTIC_CACHE",
            "P4_MEMORY_PLUS_STRUCTURE",
        )
    }

    source_packets = [json.loads(value[1]["content"]) for value in messages.values()]
    assert source_packets[0] == source_packets[1] == source_packets[2]
    packet = source_packets[0]
    assert set(packet) == {"modulus", "examples"}
    assert len(packet["examples"]) == len(family.source_examples)

    encoded = messages["P4_MEMORY_PLUS_STRUCTURE"][1]["content"].lower()
    assert "permutation" not in encoded
    assert "offsets" not in encoded
    assert family.source_rule.fingerprint() not in encoded


def test_s2_forms_all_arms_with_three_physical_build_calls_and_no_oracle_fixture():
    family = generate_transfer_family(seed=42, regime="shared")
    client = _formation_client(family)

    representations = form_s2_representations(client, family)

    assert tuple(representations) == REPRESENTATION_KINDS
    assert len(client.messages) == S2_FORMATION_CALLS_PER_FAMILY == 3
    assert all(rep.empirical_source == "model_or_direct" for rep in representations.values())
    assert all(not rep.r0_oracle_upper_bound for rep in representations.values())

    assert representations["P0_RAW_HISTORY"].formation_calls == 0
    assert representations["P1_RETRIEVAL_ONLY"].formation_calls == 0
    assert representations["P2_ORDINARY_SUMMARY"].formation_calls == 1
    assert representations["P3_SEMANTIC_CACHE"].formation_calls == 1
    assert representations["P4_MEMORY_PLUS_STRUCTURE"].formation_calls == 1
    assert representations["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"].formation_calls == 1
    assert representations["P6_GENERIC_EQUAL_INFORMATION"].formation_calls == 1


def test_s2_p4_and_p6_share_one_learned_semantic_payload_but_different_surface_type():
    family = generate_transfer_family(seed=77, regime="shared")
    representations = form_s2_representations(_formation_client(family), family)
    p4 = representations["P4_MEMORY_PLUS_STRUCTURE"]
    p6 = representations["P6_GENERIC_EQUAL_INFORMATION"]

    p4_payload = json.loads(p4.serialized)
    p6_payload = json.loads(p6.serialized)

    assert p4.formation_completion is p6.formation_completion
    assert p4.formation_input_tokens == p6.formation_input_tokens
    assert p4.formation_output_tokens == p6.formation_output_tokens
    assert decode_semantic_payload(p4.kind, p4_payload) == decode_semantic_payload(
        p6.kind,
        p6_payload,
    )
    assert semantic_digest(p4.kind, p4_payload) == semantic_digest(p6.kind, p6_payload)
    assert "memory" in p4.serialized.lower()
    assert "structure" in p4.serialized.lower()
    assert "memory" not in p6.serialized.lower()
    assert "structure" not in p6.serialized.lower()
    assert "crystal" not in p6.serialized.lower()


def test_s2_structure_only_reuses_learned_rule_and_keeps_provenance_out_of_projection():
    family = generate_transfer_family(seed=91, regime="shared")
    representations = form_s2_representations(_formation_client(family), family)
    p4 = representations["P4_MEMORY_PLUS_STRUCTURE"]
    p5 = representations["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"]

    assert p5.formation_completion is p4.formation_completion
    assert p5.reconstruction_handles == p4.provenance_handles
    assert p5.provenance_handles == p4.provenance_handles
    assert all(handle not in p5.serialized for handle in p5.provenance_handles)
    assert json.loads(p5.serialized)["reusable_relation"]


def test_s2_summary_and_cache_are_strong_independent_model_formed_controls():
    family = generate_transfer_family(seed=112, regime="shared")
    representations = form_s2_representations(_formation_client(family), family)

    summary = json.loads(representations["P2_ORDINARY_SUMMARY"].serialized)
    cache = json.loads(representations["P3_SEMANTIC_CACHE"].serialized)

    assert set(summary) == {"summary"}
    assert summary["summary"]
    assert set(cache) == {"gist"}
    assert cache["gist"]
    assert "oracle" not in representations["P2_ORDINARY_SUMMARY"].serialized.lower()
    assert "oracle" not in representations["P3_SEMANTIC_CACHE"].serialized.lower()


def test_s2_smoke_runs_three_build_calls_plus_exactly_one_target_probe_per_arm():
    family = generate_transfer_family(seed=808, regime="shared")
    expected = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
    client = QueueClient(
        _formation_client(family).completions
        + [_completion(expected, input_tokens=23, output_tokens=4) for _ in REPRESENTATION_KINDS]
    )

    result = run_s2_smoke(client, family, step_index=0, examples_visible=0)

    assert result.non_citable
    assert result.provider_calls == S2_TOTAL_CALLS_PER_FAMILY == 10
    assert len(client.messages) == 10
    assert tuple(result.arms) == REPRESENTATION_KINDS
    assert len({arm.target_task_digest for arm in result.arms.values()}) == 1
    assert all(arm.verification.correct for arm in result.arms.values())
    assert all(arm.target_calls == 1 for arm in result.arms.values())


def test_s2_target_wrapper_is_identical_across_arms_except_prior_context():
    family = generate_transfer_family(seed=904, regime="shared")
    expected = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
    client = QueueClient(
        _formation_client(family).completions
        + [_completion(expected) for _ in REPRESENTATION_KINDS]
    )

    result = run_s2_smoke(client, family, step_index=0, examples_visible=1)

    target_messages = client.messages[S2_FORMATION_CALLS_PER_FAMILY:]
    system_prompts = {messages[0]["content"] for messages in target_messages}
    assert len(system_prompts) == 1

    user_packets = [json.loads(messages[1]["content"]) for messages in target_messages]
    tasks = [packet["task"] for packet in user_packets]
    assert all(task == tasks[0] for task in tasks)
    assert all(set(packet) == {"prior_context", "task"} for packet in user_packets)
    assert len({arm.target_task_digest for arm in result.arms.values()}) == 1


def test_s2_cost_ledger_charges_formation_and_projection_without_hidden_calls():
    family = generate_transfer_family(seed=1005, regime="shared")
    expected = json.dumps(list(family.expected_output(0)), separators=(",", ":"))
    client = QueueClient(
        _formation_client(family).completions
        + [_completion(expected, input_tokens=29, output_tokens=4) for _ in REPRESENTATION_KINDS]
    )

    result = run_s2_smoke(client, family, step_index=0, examples_visible=0)

    p0 = result.arms["P0_RAW_HISTORY"]
    p2 = result.arms["P2_ORDINARY_SUMMARY"]
    p4 = result.arms["P4_MEMORY_PLUS_STRUCTURE"]
    p6 = result.arms["P6_GENERIC_EQUAL_INFORMATION"]

    assert p0.total_calls == 1
    assert p2.total_calls == 2
    assert p4.total_calls == 2
    assert p6.total_calls == 2
    assert p4.formation_input_tokens == p6.formation_input_tokens == 13
    assert p4.formation_output_tokens == p6.formation_output_tokens == 7
    assert p4.projected_bytes == len(p4.representation.serialized.encode("utf-8"))
    assert p6.projected_bytes == len(p6.representation.serialized.encode("utf-8"))
    assert result.physical_provider_calls == len(client.messages) == 10


def test_s2_rejects_malformed_learned_structure_before_target_probes():
    family = generate_transfer_family(seed=1206, regime="shared")
    client = QueueClient(
        [
            _completion('{"summary":"faithful recap"}'),
            _completion('{"gist":"compact gist"}'),
            _completion('{"permutation":[0,1,2],"offsets":[0,0,0,0],"modulus":10}'),
        ]
    )

    with pytest.raises(S2ExperimentError, match="permutation"):
        form_s2_representations(client, family)
    assert len(client.messages) == 3


def test_s2_rejects_unbounded_or_invalid_probe_coordinates():
    family = generate_transfer_family(seed=1307, regime="shared")
    client = _formation_client(family)
    representations = form_s2_representations(client, family)

    from relaylm.v2_cognitive_ir_actual_model import build_s2_target_messages

    with pytest.raises(S2ExperimentError, match="step_index"):
        build_s2_target_messages(
            representations["P0_RAW_HISTORY"],
            family,
            step_index=len(family.target_steps),
            examples_visible=0,
        )
    with pytest.raises(S2ExperimentError, match="examples_visible"):
        build_s2_target_messages(
            representations["P0_RAW_HISTORY"],
            family,
            step_index=0,
            examples_visible=99,
        )
