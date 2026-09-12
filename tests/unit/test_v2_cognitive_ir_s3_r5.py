from __future__ import annotations

import json

import pytest

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    build_margin_p2_formation_messages,
)
from relaylm.v2_cognitive_ir_s3_r4 import (
    S3_R4_LABEL,
    S3_R4_PREREGISTRATION_SHA256,
    S3_R4_SEEDS,
    validate_s3_r4_preregistration,
)
from relaylm.v2_cognitive_ir_s3_r5 import (
    S3R5BindingError,
    S3_R5_ACTIVE_COORDINATES,
    S3_R5_FAMILIES_PER_REGIME,
    S3_R5_LABEL,
    S3_R5_MAX_OUTPUT_TOKENS,
    S3_R5_PREREGISTRATION_SCHEMA,
    S3_R5_PREREGISTRATION_SHA256,
    S3_R5_SEEDS,
    S3_R5_SELECTED_DIFFICULTY,
    S3_R5_SHARD_CALLS,
    S3_R5_TOTAL_INPUT_TOKEN_REQUESTS,
    S3_R5_TOTAL_SEMANTIC_CALLS,
    activate_s3_r5_preregistration,
    derive_s3_r5_seed,
    exact_first_arm_superiority_p,
    generate_s3_r5_family,
    paired_outcome_cells,
    s3_r5_call_plan,
    validate_s3_r5_preregistration,
    weakly_pareto_dominates,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_s3_r5_llama_cpp import S3R5LlamaCppClient
import tools.v2_cognitive_ir_s3_r4_llama_cpp_wsl as r4_wsl
import tools.v2_cognitive_ir_s3_r5_llama_cpp_wsl as r5_wsl


_BASE_FIELDS = (
    "S3_PREREGISTRATION_SCHEMA",
    "S3_PREREGISTRATION_SHA256",
    "S3_LABEL",
    "S3_SEEDS",
    "S3_SHARD_CALLS",
    "S3_TOTAL_SEMANTIC_CALLS",
    "S3_TOTAL_INPUT_TOKEN_REQUESTS",
    "generate_s3_family",
    "form_s2_representations",
    "run_s3_shard",
    "validate_frozen_seeds",
)


def _base_snapshot() -> dict[str, object]:
    return {name: getattr(base, name) for name in _BASE_FIELDS}


def _restore_base(snapshot: dict[str, object]) -> None:
    for name, value in snapshot.items():
        setattr(base, name, value)


def _all_rules(family: object) -> tuple[object, ...]:
    return tuple(dict.fromkeys((family.source_rule, *family.target_rules)))


def _assert_rule_is_k3(rule: object) -> None:
    assert tuple(rule.permutation) == (0, 1, 2, 3)
    assert rule.modulus == 10
    active = [value for value in rule.offsets if value != 0]
    assert len(active) == S3_R5_ACTIVE_COORDINATES == 3
    assert set(active) <= {1, 2, 3}


def _assert_family_has_no_wrap(family: object) -> None:
    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    for rule in _all_rules(family):
        for vector in vectors:
            for output_index, input_index in enumerate(rule.permutation):
                assert vector[input_index] + rule.offsets[output_index] < rule.modulus


def test_s3_r5_exact_preregistration_identity_and_call_ledger() -> None:
    validate_s3_r5_preregistration()
    assert S3_R5_PREREGISTRATION_SCHEMA == "relaylm2-cognitive-ir-s3-prereg-v5"
    assert S3_R5_PREREGISTRATION_SHA256 == (
        "2f2dc45283af1ce2e4c921d483d16ea2908151ae7e55c50378ee92eecda15d65"
    )
    assert S3_R5_LABEL == "relaylm2-cognitive-ir-s3-semantic-invariance-v5-k3"
    assert S3_R5_SELECTED_DIFFICULTY == "K3_THREE_ACTIVE"
    assert S3_R5_FAMILIES_PER_REGIME == 6
    assert S3_R5_MAX_OUTPUT_TOKENS == 1024
    assert {
        regime: tuple(derive_s3_r5_seed(regime, index) for index in range(6))
        for regime in base.S3_REGIMES
    } == dict(S3_R5_SEEDS)
    flattened = [seed for seeds in S3_R5_SEEDS.values() for seed in seeds]
    assert len(flattened) == len(set(flattened)) == 24
    assert dict(S3_R5_SHARD_CALLS) == {
        "shared": 246,
        "null": 246,
        "mismatch": 246,
        "shift": 258,
    }
    assert S3_R5_TOTAL_SEMANTIC_CALLS == 996
    assert S3_R5_TOTAL_INPUT_TOKEN_REQUESTS == 1992
    assert {
        regime: len(s3_r5_call_plan(regime)) for regime in base.S3_REGIMES
    } == dict(S3_R5_SHARD_CALLS)
    assert sum(S3_R5_SHARD_CALLS.values()) == 996


def test_s3_r5_all_24_families_have_exact_k3_geometry_and_regime_relations() -> None:
    for regime in base.S3_REGIMES:
        for index in range(6):
            family = generate_s3_r5_family(regime, index)
            assert family.seed == S3_R5_SEEDS[regime][index]
            assert family.regime == regime
            assert family.modulus == 10
            assert len(family.source_examples) == 4
            assert len(family.target_steps) == 4
            for rule in _all_rules(family):
                _assert_rule_is_k3(rule)
            _assert_family_has_no_wrap(family)

            if regime == "shared":
                assert family.shift_index is None
                assert all(rule == family.source_rule for rule in family.target_rules)
            elif regime == "null":
                assert family.shift_index is None
                assert family.target_rules[0] != family.source_rule
                assert len(set(family.target_rules)) == 1
            elif regime == "mismatch":
                assert family.shift_index is None
                target = family.target_rules[0]
                assert len(set(family.target_rules)) == 1
                assert target != family.source_rule
                changed = [
                    coordinate
                    for coordinate, pair in enumerate(
                        zip(family.source_rule.offsets, target.offsets, strict=True)
                    )
                    if pair[0] != pair[1]
                ]
                assert len(changed) == 1
                coordinate = changed[0]
                assert family.source_rule.offsets[coordinate] != 0
                assert target.offsets[coordinate] != 0
            else:
                assert regime == "shift"
                assert family.shift_index == 2
                assert family.target_rules[:2] == (family.source_rule, family.source_rule)
                assert family.target_rules[2] == family.target_rules[3]
                assert family.target_rules[2] != family.source_rule


def test_s3_r5_activation_rebinds_only_campaign_shape_and_stays_valid_after_activation() -> None:
    snapshot = _base_snapshot()
    historical_identity = (
        S3_R4_LABEL,
        S3_R4_PREREGISTRATION_SHA256,
        dict(S3_R4_SEEDS),
    )
    try:
        validate_s3_r4_preregistration()
        activate_s3_r5_preregistration()
        assert base.S3_PREREGISTRATION_SCHEMA == S3_R5_PREREGISTRATION_SCHEMA
        assert base.S3_PREREGISTRATION_SHA256 == S3_R5_PREREGISTRATION_SHA256
        assert base.S3_LABEL == S3_R5_LABEL
        assert dict(base.S3_SEEDS) == dict(S3_R5_SEEDS)
        assert dict(base.S3_SHARD_CALLS) == dict(S3_R5_SHARD_CALLS)
        assert base.S3_TOTAL_SEMANTIC_CALLS == 996
        assert base.S3_TOTAL_INPUT_TOKEN_REQUESTS == 1992
        base.validate_frozen_seeds()
        family = base.generate_s3_family("shared", 0)
        _assert_rule_is_k3(family.source_rule)
    finally:
        _restore_base(snapshot)

    assert historical_identity == (
        "relaylm2-cognitive-ir-s3-semantic-invariance-v4",
        "deb10b356f1cfe4fd18275b790f1a5bcb5972b1b841e874c26a8827ffd20dae4",
        dict(S3_R4_SEEDS),
    )
    validate_s3_r4_preregistration()


class _FormationStub:
    def __init__(self, family: object) -> None:
        self.family = family
        self.messages: list[tuple[dict[str, str], ...]] = []
        self.completions = [
            ExperimentCompletion(
                content="A concise ordinary recap.",
                input_tokens=11,
                output_tokens=7,
                response_id="p2",
            ),
            ExperimentCompletion(
                content="A compact semantic gist.",
                input_tokens=12,
                output_tokens=6,
                response_id="p3",
            ),
            ExperimentCompletion(
                content=json.dumps(
                    {
                        "permutation": list(family.source_rule.permutation),
                        "offsets": list(family.source_rule.offsets),
                        "modulus": family.modulus,
                    }
                ),
                input_tokens=13,
                output_tokens=9,
                response_id="p4",
            ),
        ]

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
    ) -> ExperimentCompletion:
        self.messages.append(messages)
        return self.completions[len(self.messages) - 1]


def test_s3_r5_inherits_r4_p2_and_shared_p4_p5_p6_lineage() -> None:
    snapshot = _base_snapshot()
    try:
        activate_s3_r5_preregistration()
        family = base.generate_s3_family("shared", 0)
        stub = _FormationStub(family)
        representations = base.form_s2_representations(stub, family)

        assert stub.messages[0] == build_margin_p2_formation_messages(family)
        assert stub.messages[1] == build_s2_formation_messages("P3_SEMANTIC_CACHE", family)
        assert stub.messages[2] == build_s2_formation_messages(
            "P4_MEMORY_PLUS_STRUCTURE", family
        )
        assert (
            representations["P4_MEMORY_PLUS_STRUCTURE"].formation_completion
            is representations["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"].formation_completion
            is representations["P6_GENERIC_EQUAL_INFORMATION"].formation_completion
        )
        assert base.semantic_digest(
            "P4_MEMORY_PLUS_STRUCTURE",
            json.loads(representations["P4_MEMORY_PLUS_STRUCTURE"].serialized),
        ) == base.semantic_digest(
            "P6_GENERIC_EQUAL_INFORMATION",
            json.loads(representations["P6_GENERIC_EQUAL_INFORMATION"].serialized),
        )
    finally:
        _restore_base(snapshot)


def test_s3_r5_inherits_surface_semantic_and_option_value_panel_shape() -> None:
    assert base.S3_SURFACE_VARIANTS == (
        "S1_ROLE_LABEL_NEUTRAL",
        "S2_KEY_RENAME_REORDER",
        "S3_LOSSLESS_LIST_PROSE_SERIALIZATION",
        "S4_PROMPT_PARAPHRASE_FORMAT",
    )
    assert base.S3_SEMANTIC_INTERVENTIONS == (
        "M1_RULE_OFFSET_FLIP",
        "M2_EXCEPTION_CHANGE",
        "M3_SCOPE_CHANGE",
        "M4_RELATION_REPLACE",
    )
    assert (
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    ) == (0.15, 0.20, 0.15)
    shared_plan = s3_r5_call_plan("shared")
    assert sum(":surface:" in item for item in shared_plan) == 48
    assert sum(":semantic:" in item for item in shared_plan) == 96
    assert sum(":option:" in item for item in shared_plan) == 42
    assert not any(":anchor:" in item for item in shared_plan)
    shift_plan = s3_r5_call_plan("shift")
    assert sum(":anchor:" in item for item in shift_plan) == 12


def test_s3_r5_exact_paired_helpers_cover_preregistered_boundaries() -> None:
    assert paired_outcome_cells(
        (True, True, False, False),
        (False, True, True, False),
    ) == {
        "first_only": 1,
        "second_only": 1,
        "both_correct": 1,
        "both_wrong": 1,
    }
    assert exact_first_arm_superiority_p(0, 0) == 1.0
    assert exact_first_arm_superiority_p(5, 0) == pytest.approx(0.03125)
    assert exact_first_arm_superiority_p(4, 0) == pytest.approx(0.0625)
    assert exact_first_arm_superiority_p(5, 1) == pytest.approx(0.109375)
    with pytest.raises(S3R5BindingError, match="equal length"):
        paired_outcome_cells((True,), (True, False))


def test_s3_r5_pareto_helper_uses_vector_dominance_without_scalarization() -> None:
    cheap = {"calls": 1, "tokens": 10, "bytes": 20}
    expensive = {"calls": 2, "tokens": 10, "bytes": 21}
    crossed = {"calls": 0, "tokens": 11, "bytes": 19}
    assert weakly_pareto_dominates(cheap, expensive) is True
    assert weakly_pareto_dominates(expensive, cheap) is False
    assert weakly_pareto_dominates(cheap, crossed) is False
    assert weakly_pareto_dominates(crossed, cheap) is False


def test_s3_r5_runtime_and_route_cannot_silently_fall_back_to_r4() -> None:
    assert r4_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_s3_r4_llama_cpp_transaction"
    )
    assert r5_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_s3_r5_llama_cpp_transaction"
    )
    with pytest.raises(StructureProposalError, match="output ceiling"):
        S3R5LlamaCppClient(
            base_url="http://127.0.0.1:1234/v1",
            model="model.gguf",
            call_plan=("q",),
            max_output_tokens=512,
        )
    with pytest.raises(StructureProposalError, match="temperature must be zero"):
        S3R5LlamaCppClient(
            base_url="http://127.0.0.1:1234/v1",
            model="model.gguf",
            call_plan=("q",),
            temperature=0.1,
        )
    with pytest.raises(StructureProposalError, match="request seed must be null"):
        S3R5LlamaCppClient(
            base_url="http://127.0.0.1:1234/v1",
            model="model.gguf",
            call_plan=("q",),
            seed=1,
        )
