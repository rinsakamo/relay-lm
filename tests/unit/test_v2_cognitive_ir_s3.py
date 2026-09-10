from __future__ import annotations

import json

from relaylm.v2_cognitive_ir_s3 import (
    S3_PREREGISTRATION_SHA256,
    S3_REGIMES,
    S3_SEEDS,
    S3_SEMANTIC_INTERVENTIONS,
    S3_SHARD_CALLS,
    S3_SURFACE_VARIANTS,
    S3_TOTAL_INPUT_TOKEN_REQUESTS,
    S3_TOTAL_SEMANTIC_CALLS,
    derive_s3_seed,
    generate_s3_family,
    option_value_oracle,
    primary_step_index,
    render_s3_surface_variant,
    run_s3_shard,
    s3_call_plan,
    s3_campaign_plan,
    semantic_intervention,
    semantic_invariance_gate,
    validate_frozen_seeds,
)
from relaylm.v2_cognitive_ir_actual_model import form_s2_representations
from relaylm.v2_transfer_actual_model import ExperimentCompletion


class _FakeS3Client:
    def __init__(self, regime: str) -> None:
        self.regime = regime
        self.plan = s3_call_plan(regime)
        self.provider_attempts = 0
        self.provider_completions = 0
        self.input_count_attempts = 0
        self.input_count_completions = 0
        self._index = 0

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        assert question_id == self.plan[self._index]
        parts = question_id.split(":")
        family_index = int(parts[1])
        family = generate_s3_family(self.regime, family_index)
        self.provider_attempts += 1
        self.provider_completions += 1
        self.input_count_attempts += 2
        self.input_count_completions += 2
        self._index += 1

        if output_kind == "text":
            content = "faithful compact source recap"
        elif output_kind == "rule":
            rule = family.source_rule
            content = json.dumps(
                {
                    "permutation": list(rule.permutation),
                    "offsets": list(rule.offsets),
                    "modulus": rule.modulus,
                }
            )
        elif output_kind == "index":
            content = json.dumps({"index": option_value_oracle(family)})
        else:
            if ":semantic:" in question_id:
                name = next(
                    name for name in S3_SEMANTIC_INTERVENTIONS if f":{name}:" in question_id
                )
                expected = semantic_intervention(
                    family,
                    name,
                    step_index=primary_step_index(family),
                ).expected
                if question_id.endswith(":STALE_ORIGINAL"):
                    values = list(expected)
                    values[0] = (values[0] + 1) % family.modulus
                    content = json.dumps(values)
                else:
                    content = json.dumps(list(expected))
            elif ":anchor:" in question_id:
                content = json.dumps(list(family.expected_output(1)))
            else:
                content = json.dumps(list(family.expected_output(primary_step_index(family))))
        return ExperimentCompletion(content=content, input_tokens=11, output_tokens=3)


def test_frozen_seed_identity_and_campaign_counts() -> None:
    validate_frozen_seeds()
    assert S3_PREREGISTRATION_SHA256 == (
        "2448d147e8bbb1ab17446fbc54e464fa6d8746a18d19fad7f92627a039384c69"
    )
    assert {
        regime: tuple(derive_s3_seed(regime, index) for index in range(3))
        for regime in S3_REGIMES
    } == dict(S3_SEEDS)
    assert [len(s3_call_plan(regime)) for regime in S3_REGIMES] == [123, 123, 123, 129]
    assert sum(S3_SHARD_CALLS.values()) == S3_TOTAL_SEMANTIC_CALLS == 498
    assert S3_TOTAL_INPUT_TOKEN_REQUESTS == 996
    assert len(s3_campaign_plan()) == 498
    assert len(set(s3_campaign_plan())) == 498


def test_generator_stays_identity_offset_and_no_wrap() -> None:
    for regime in S3_REGIMES:
        for index in range(3):
            family = generate_s3_family(regime, index)
            assert family.source_rule.permutation == (0, 1, 2, 3)
            assert all(1 <= value <= 3 for value in family.source_rule.offsets)
            for rule in family.target_rules:
                assert rule.permutation == (0, 1, 2, 3)
                assert all(1 <= value <= 3 for value in rule.offsets)
            for example in family.source_examples:
                assert all(
                    example.input_values[i] + family.source_rule.offsets[i] < family.modulus
                    for i in range(4)
                )
            for step_index, step in enumerate(family.target_steps):
                rule = family.target_rules[step_index]
                for values in [*(item.input_values for item in step.examples), step.query]:
                    assert all(values[i] + rule.offsets[i] < family.modulus for i in range(4))
            if regime == "shared":
                assert all(rule == family.source_rule for rule in family.target_rules)
            elif regime == "shift":
                assert family.shift_index == 2
                assert family.target_rules[:2] == (family.source_rule, family.source_rule)
                assert family.target_rules[2] != family.source_rule
            else:
                assert family.target_rules[0] != family.source_rule


def test_surface_variants_round_trip_exact_semantics_and_option_oracle() -> None:
    family = generate_s3_family("shared", 0)

    class FormationClient:
        def __init__(self) -> None:
            self.calls = 0

        def complete(self, messages: tuple[dict[str, str], ...]) -> ExperimentCompletion:
            self.calls += 1
            if self.calls < 3:
                return ExperimentCompletion(content="summary or gist", input_tokens=1, output_tokens=1)
            rule = family.source_rule
            return ExperimentCompletion(
                content=json.dumps(
                    {
                        "permutation": list(rule.permutation),
                        "offsets": list(rule.offsets),
                        "modulus": rule.modulus,
                    }
                ),
                input_tokens=1,
                output_tokens=1,
            )

    representations = form_s2_representations(FormationClient(), family)
    for arm in ("P4_MEMORY_PLUS_STRUCTURE", "P6_GENERIC_EQUAL_INFORMATION"):
        expected = None
        for variant in S3_SURFACE_VARIANTS:
            material = render_s3_surface_variant(representations[arm], variant)
            if expected is None:
                expected = material.canonical_semantics
            assert material.canonical_semantics == expected
            assert material.serialized
    assert 0 <= option_value_oracle(family) < 4


def test_semantic_interventions_change_declared_truth() -> None:
    family = generate_s3_family("shared", 1)
    step = primary_step_index(family)
    original = family.expected_output(step)
    for name in S3_SEMANTIC_INTERVENTIONS:
        intervention = semantic_intervention(family, name, step_index=step)
        assert intervention.query == family.target_steps[step].query
        assert intervention.expected != original
        assert intervention.update["kind"]


def test_full_shards_follow_frozen_call_ledger_and_primary_gate() -> None:
    for regime in S3_REGIMES:
        client = _FakeS3Client(regime)
        result = run_s3_shard(client, regime)
        assert result.semantic_calls == S3_SHARD_CALLS[regime]
        assert client.provider_attempts == S3_SHARD_CALLS[regime]
        assert client.provider_completions == S3_SHARD_CALLS[regime]
        assert client.input_count_attempts == 2 * S3_SHARD_CALLS[regime]
        assert client.input_count_completions == 2 * S3_SHARD_CALLS[regime]
        assert result.surface_perturbation_effect == 0.0
        assert result.semantic_intervention_effect == 1.0
        assert result.semantic_invariance_gate is True
        assert all(item.p4_p6_semantic_equal for item in result.families)
        assert all(item.shared_formation_lineage for item in result.families)
        assert all(item.provenance_audit_changed for item in result.families)


def test_semantic_invariance_gate_is_fail_closed() -> None:
    assert semantic_invariance_gate(0.0, 1.0) is True
    assert semantic_invariance_gate(0.16, 1.0) is False
    assert semantic_invariance_gate(0.0, 0.19) is False
    assert semantic_invariance_gate(0.10, 0.20) is False
