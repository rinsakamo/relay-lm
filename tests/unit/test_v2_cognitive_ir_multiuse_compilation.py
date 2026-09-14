from __future__ import annotations

import json

import pytest

import relaylm.v2_cognitive_ir_multiuse_compilation as muc
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_QUAL_V2_CONTRACT,
    build_margin_p2_formation_messages,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion


SYNTHETIC_SEED = 91_2919_000_000_001
FAMILY_INDEX = 7
RULE_COMPLETION = ExperimentCompletion(
    content='{"permutation":[0,1,2,3],"offsets":[1,2,3,0],"modulus":10}',
    input_tokens=41,
    output_tokens=19,
)
SUMMARY_COMPLETION = ExperimentCompletion(
    content="The examples show a stable coordinate-wise additive pattern under modulus ten.",
    input_tokens=42,
    output_tokens=17,
)
CACHE_COMPLETION = ExperimentCompletion(
    content="Likely reusable pattern: each coordinate has a stable additive relation.",
    input_tokens=43,
    output_tokens=15,
)


def _family():
    return muc.generate_synthetic_shared_family(FAMILY_INDEX, SYNTHETIC_SEED)


def _prepared():
    return muc.prepare_representations(
        _family(),
        summary_completion=SUMMARY_COMPLETION,
        cache_completion=CACHE_COMPLETION,
        rule_completion=RULE_COMPLETION,
    )


def test_validate_binding_materializes_no_official_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(family_index: int, seed: int):
        raise AssertionError(
            f"official family materialized during binding validation: {family_index=} {seed=}"
        )

    monkeypatch.setattr(muc, "_generate_shared_family", fail_if_called)
    muc.validate_repository_binding()


def test_exact_seed_derivation_and_full_historical_collision_fence() -> None:
    assert muc.preregistered_seeds() == muc.FROZEN_SEEDS
    assert len(set(muc.FROZEN_SEEDS)) == muc.FAMILY_COUNT == 24
    assert not (set(muc.FROZEN_SEEDS) & muc.historical_family_seeds())
    muc.validate_seed_admission()


@pytest.mark.parametrize("seed", muc.FROZEN_SEEDS)
def test_synthetic_family_rejects_every_official_seed(seed: int) -> None:
    with pytest.raises(muc.MultiuseCompilationError):
        muc.generate_synthetic_shared_family(0, seed)


def test_synthetic_family_is_fresh_shared_k3_with_three_distinct_probes() -> None:
    family = _family()
    assert family.regime == "shared"
    assert family.modulus == 10
    assert family.source_rule.permutation == (0, 1, 2, 3)
    assert len(family.source_examples) == 4
    assert len(family.target_steps) == 3
    assert family.target_rules == (family.source_rule,) * 3
    assert family.shift_index is None

    offsets = family.source_rule.offsets
    assert sum(value != 0 for value in offsets) == 3
    assert all(value in (0, 1, 2, 3) for value in offsets)

    queries = tuple(step.query for step in family.target_steps)
    assert len(set(queries)) == 3

    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    assert all(
        vector[index] + offsets[index] < family.modulus
        for vector in vectors
        for index in range(4)
    )


def test_s_c_k_formation_contracts_are_inherited_and_share_source_packet() -> None:
    family = _family()
    bundle = muc.formation_message_bundle(family)

    assert muc.build_summary_formation_messages(
        family
    ) == build_margin_p2_formation_messages(family)
    assert muc.build_cache_formation_messages(
        family
    ) == build_s2_formation_messages("P3_SEMANTIC_CACHE", family)
    assert muc.build_rule_formation_messages(
        family
    ) == build_s2_formation_messages("P4_MEMORY_PLUS_STRUCTURE", family)

    assert P2_BOUNDEDNESS_QUAL_V2_CONTRACT in bundle[muc.SUMMARY_ARM][0]["content"]
    assert len({messages[1]["content"] for messages in bundle.values()}) == 1
    user_packet = json.loads(bundle[muc.RULE_ARM][1]["content"])
    assert set(user_packet) == {"modulus", "examples"}
    assert "query" not in user_packet


def test_representations_are_one_build_three_reuse_and_k_is_role_functional() -> None:
    family = _family()
    prepared = _prepared()

    assert tuple(prepared.by_arm) == muc.ARMS
    assert prepared.for_arm(muc.RETRIEVAL_ARM).formation_calls == 0
    assert prepared.for_arm(muc.SUMMARY_ARM).formation_calls == 1
    assert prepared.for_arm(muc.CACHE_ARM).formation_calls == 1
    assert prepared.for_arm(muc.RULE_ARM).formation_calls == 1

    k_payload = json.loads(prepared.for_arm(muc.RULE_ARM).serialized)
    assert k_payload == {
        "context": {
            "source_handles": list(prepared.provenance_handles),
        },
        "relation": {
            "transform_kind": "affine_permutation",
            "index_reordering": [0, 1, 2, 3],
            "additive_shifts": [1, 2, 3, 0],
            "modular_divisor": 10,
        },
    }
    field_text = " ".join(
        (
            *k_payload["context"].keys(),
            *k_payload["relation"].keys(),
        )
    ).lower()
    assert all(label not in field_text for label in muc.PRIVILEGED_ONTOLOGY_LABELS)

    identities = {
        arm: id(prepared.for_arm(arm))
        for arm in (muc.SUMMARY_ARM, muc.CACHE_ARM, muc.RULE_ARM)
    }
    for probe_index in range(3):
        for arm in identities:
            muc.build_target_messages(
                arm,
                prepared,
                family,
                probe_index=probe_index,
            )
            assert id(prepared.for_arm(arm)) == identities[arm]


def test_target_interface_is_identical_across_arms_for_each_probe() -> None:
    family = _family()
    prepared = _prepared()
    task_digests: list[str] = []

    for probe_index in range(3):
        prompts = {
            arm: muc.build_target_messages(
                arm,
                prepared,
                family,
                probe_index=probe_index,
            )
            for arm in muc.ARMS
        }
        assert len({prompt.task_digest for prompt in prompts.values()}) == 1
        assert len({prompt.messages[0]["content"] for prompt in prompts.values()}) == 1
        for prompt in prompts.values():
            assert prompt.task_packet["examples"] == []
            assert prompt.task_packet["query"] == list(
                family.target_steps[probe_index].query
            )
        task_digests.append(next(iter(prompts.values())).task_digest)

    assert len(set(task_digests)) == 3


def test_exact_call_and_input_count_ledgers() -> None:
    plan = muc.semantic_call_plan()
    assert len(plan) == muc.SEMANTIC_PROVIDER_CALLS == 360
    assert muc.FORMATION_CALLS == 72
    assert muc.DOWNSTREAM_TARGET_CALLS == 288
    assert muc.INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL == 2
    assert muc.SCIENTIFIC_INPUT_TOKEN_REQUESTS == 720
    assert muc.MECHANICAL_PREFLIGHT_INPUT_TOKEN_REQUESTS == 2

    expected = (
        "FORM_S",
        "FORM_C",
        "FORM_K",
        "PROBE_0_DIRECT_RETRIEVAL",
        "PROBE_0_STRONG_ORDINARY_SUMMARY",
        "PROBE_0_SEMANTIC_CACHE",
        "PROBE_0_GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
        "PROBE_1_DIRECT_RETRIEVAL",
        "PROBE_1_STRONG_ORDINARY_SUMMARY",
        "PROBE_1_SEMANTIC_CACHE",
        "PROBE_1_GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
        "PROBE_2_DIRECT_RETRIEVAL",
        "PROBE_2_STRONG_ORDINARY_SUMMARY",
        "PROBE_2_SEMANTIC_CACHE",
        "PROBE_2_GENERIC_ROLE_FUNCTIONAL_REUSABLE_RULE",
    )
    for family_index in range(24):
        start = family_index * muc.SEMANTIC_CALLS_PER_FAMILY
        chunk = plan[start : start + muc.SEMANTIC_CALLS_PER_FAMILY]
        assert tuple(item[2] for item in chunk) == expected
        assert len({item[0] for item in chunk}) == 1
        assert len({item[1] for item in chunk}) == 1


def test_future_success_count_is_family_level_three_probe_score() -> None:
    assert muc.future_success_count((True, False, True)) == 2
    with pytest.raises(muc.MultiuseCompilationError):
        muc.future_success_count((True, False))


def test_confirmatory_analysis_is_family_level_one_sided_and_holm_exactly_two() -> None:
    rule = [3] * 24
    summary = [0] * 24
    cache = [3] * 24
    analysis = muc.confirmatory_analysis(
        rule_scores=rule,
        summary_scores=summary,
        cache_scores=cache,
    )

    assert tuple(analysis) == muc.CONFIRMATORY_CONTRASTS
    h1 = analysis[muc.CONFIRMATORY_CONTRASTS[0]]
    h2 = analysis[muc.CONFIRMATORY_CONTRASTS[1]]
    assert h1.table.left_higher == 24
    assert h1.table.right_higher == 0
    assert h1.table.tied == 0
    assert h1.raw_p_value == 2**-24
    assert h1.holm_reject is True
    assert h2.table.tied == 24
    assert h2.raw_p_value == 1.0
    assert h2.holm_reject is False
    assert (
        muc.classify_completed_panel(analysis)
        == "REUSABLE_RULE_ADVANTAGE_OVER_SUMMARY_ONLY_DETECTED"
    )


def test_direct_and_summary_cache_comparisons_are_descriptive_only() -> None:
    table = muc.descriptive_family_comparison([3] * 24, [2] * 24)
    assert table.left_higher == 24
    assert not hasattr(table, "raw_p_value")
    assert muc.DESCRIPTIVE_ONLY_CONTRASTS == (
        "RULE_VS_DIRECT_RETRIEVAL_DESCRIPTIVE_ONLY",
        "SUMMARY_VS_CACHE_DESCRIPTIVE_ONLY",
    )


def test_horizon3_work_is_component_vector_without_scalarization() -> None:
    work = muc.Horizon3Work(
        formation_calls=1,
        formation_input_tokens=40,
        formation_output_tokens=20,
        formation_wall_seconds=1.5,
        retained_bytes=120,
        projected_bytes_by_probe=(120, 120, 120),
        target_calls=3,
        target_input_tokens=150,
        target_output_tokens=30,
        target_wall_seconds=2.5,
    )
    mapping = work.as_mapping()
    assert tuple(mapping) == (
        "C_build",
        "C_store",
        "C_project",
        "C_model",
        "C_total_horizon3",
    )
    assert mapping["C_total_horizon3"] == {
        "component_names": ["C_build", "C_store", "C_project", "C_model"],
        "scalarized": False,
    }
    assert "total" not in mapping["C_total_horizon3"]
    assert "scalar" not in mapping["C_total_horizon3"]


def test_repository_authority_is_zero_gpu_and_zero_rescue() -> None:
    assert muc.PHYSICAL_EXECUTION_AUTHORIZED is False
    assert muc.ARCHITECTURE_CONSEQUENCE == "NONE"
    assert set(muc.FORBIDDEN_RESCUE_COUNTS) == {
        "semantic_retry",
        "replay",
        "reseed",
        "fallback",
        "hidden_repair",
        "judge",
    }
    assert all(value == 0 for value in muc.FORBIDDEN_RESCUE_COUNTS.values())
    muc.validate_repository_binding()
