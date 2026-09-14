from __future__ import annotations

import json

import pytest

import relaylm.v2_cognitive_ir_role_accessible_generic as rag
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_experiment import neutralize_typed_payload
from relaylm.v2_transfer_actual_model import ExperimentCompletion


SYNTHETIC_SEED = 91_2900_000_000_001
LEARNED_RULE = {
    "permutation": [0, 1, 2, 3],
    "offsets": [1, 2, 3, 0],
    "modulus": 10,
}
PROVENANCE = ("source:synthetic:0", "source:synthetic:1")


def _prepared():
    return rag.prepare_synthetic_representations(
        seed=SYNTHETIC_SEED,
        learned_rule=LEARNED_RULE,
        provenance_handles=PROVENANCE,
    )


def test_validate_binding_materializes_no_official_family(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(seed: int):
        raise AssertionError(
            f"official family materialized during binding validation: {seed}"
        )

    monkeypatch.setattr(rag, "_generate_shared_family", fail_if_called)
    rag.validate_repository_binding()


def test_exact_seed_derivation_and_historical_collision_fence() -> None:
    assert rag.preregistered_seeds() == rag.FROZEN_SEEDS
    assert len(set(rag.FROZEN_SEEDS)) == rag.FAMILY_COUNT == 24
    assert not (set(rag.FROZEN_SEEDS) & rag.historical_family_seeds())
    rag.validate_seed_admission()


@pytest.mark.parametrize("seed", rag.FROZEN_SEEDS)
def test_synthetic_helpers_reject_official_seeds(seed: int) -> None:
    with pytest.raises(rag.RoleAccessibleGenericError):
        rag.generate_synthetic_shared_family(seed)
    with pytest.raises(rag.RoleAccessibleGenericError):
        rag.prepare_synthetic_representations(
            seed=seed,
            learned_rule=LEARNED_RULE,
            provenance_handles=PROVENANCE,
        )


def test_synthetic_family_is_fresh_shared_k3_no_wrap() -> None:
    family = rag.generate_synthetic_shared_family(SYNTHETIC_SEED)
    assert family.regime == "shared"
    assert family.modulus == 10
    assert len(family.source_examples) == 4
    assert len(family.target_steps) == 4
    assert family.shift_index is None
    assert family.target_rules == (family.source_rule,) * 4
    offsets = family.source_rule.offsets
    assert sum(value != 0 for value in offsets) == 3
    assert all(value in (0, 1, 2, 3) for value in offsets)
    vectors = [example.input_values for example in family.source_examples]
    for step in family.target_steps:
        vectors.extend(example.input_values for example in step.examples)
        vectors.append(step.query)
    assert all(
        vector[index] + offsets[index] < family.modulus
        for vector in vectors
        for index in range(4)
    )


def test_formation_prompt_is_exact_existing_p4_prompt() -> None:
    family = rag.generate_synthetic_shared_family(SYNTHETIC_SEED)
    assert rag.build_formation_messages(family) == build_s2_formation_messages(
        "P4_MEMORY_PLUS_STRUCTURE", family
    )
    text = json.dumps(rag.build_formation_messages(family), ensure_ascii=False)
    assert "target rule" not in text.lower()


def test_formation_parser_is_exact_existing_p4_parser() -> None:
    completion = ExperimentCompletion(
        content='{"permutation":[0,1,2,3],"offsets":[1,2,3,0],"modulus":10}',
        input_tokens=10,
        output_tokens=10,
    )
    assert rag.parse_learned_rule_completion(
        completion, expected_modulus=10
    ) == LEARNED_RULE
    with pytest.raises(Exception):
        rag.parse_learned_rule_completion(
            ExperimentCompletion(
                content='{"permutation":[0,1,2,3],"offsets":[1,2,3,0],"modulus":11}',
                input_tokens=10,
                output_tokens=10,
            ),
            expected_modulus=10,
        )


def test_t_g_l_are_literal_distinct_equal_semantics_and_preserve_historical_p6() -> None:
    prepared = _prepared()
    serialized = prepared.serialized_by_surface
    assert len(set(serialized.values())) == 3

    typed = json.loads(serialized[rag.TYPED_SURFACE])
    generic = json.loads(serialized[rag.ROLE_FUNCTIONAL_SURFACE])
    legacy = json.loads(serialized[rag.LEGACY_SURFACE])

    assert typed == {
        "memory": {"origin_refs": list(PROVENANCE)},
        "structure": {
            "operation": "affine_permutation",
            "permutation": [0, 1, 2, 3],
            "offsets": [1, 2, 3, 0],
            "modulus": 10,
        },
    }
    assert legacy == neutralize_typed_payload(typed)
    assert generic == {
        "context": {"source_handles": list(PROVENANCE)},
        "relation": {
            "transform_kind": "affine_permutation",
            "index_reordering": [0, 1, 2, 3],
            "additive_shifts": [1, 2, 3, 0],
            "modular_divisor": 10,
        },
    }
    decoded = {
        surface: rag.decode_surface(surface, json.loads(serialized[surface]))
        for surface in rag.SURFACES
    }
    assert len({json.dumps(value, sort_keys=True) for value in decoded.values()}) == 1
    assert next(iter(decoded.values())) == prepared.canonical_truth


def test_generic_role_functional_vocabulary_has_no_privileged_ontology_label() -> None:
    assert rag.GENERIC_CONTEXT_KEY == "source_handles"
    assert rag.GENERIC_RELATION_KEYS == (
        "transform_kind",
        "index_reordering",
        "additive_shifts",
        "modular_divisor",
    )
    field_text = " ".join(
        (rag.GENERIC_CONTEXT_KEY, *rag.GENERIC_RELATION_KEYS)
    ).lower()
    assert all(label not in field_text for label in rag.PRIVILEGED_ONTOLOGY_LABELS)


def test_target_prompt_is_same_r5_interface_across_surfaces() -> None:
    family = rag.generate_synthetic_shared_family(SYNTHETIC_SEED)
    prepared = _prepared()
    prompts = {
        surface: rag.build_target_messages(surface, prepared, family)
        for surface in rag.SURFACES
    }
    assert len({prompt.task_digest for prompt in prompts.values()}) == 1
    system_messages = {prompt.messages[0]["content"] for prompt in prompts.values()}
    assert system_messages == {
        "Solve the formal vector task. prior_context is fallible material derived from "
        "earlier observations; use it when useful, but current target examples override "
        "it on conflict. Return only one JSON integer array of length 4."
    }
    for prompt in prompts.values():
        assert prompt.task_packet["examples"] == []
        assert len(prompt.task_packet["query"]) == 4


def test_exact_call_and_input_count_ledgers() -> None:
    plan = rag.semantic_call_plan()
    assert len(plan) == rag.SEMANTIC_PROVIDER_CALLS == 96
    assert rag.FORMATION_CALLS == 24
    assert rag.DOWNSTREAM_TARGET_CALLS == 72
    assert rag.INPUT_TOKEN_REQUESTS_PER_SEMANTIC_CALL == 2
    assert rag.SCIENTIFIC_INPUT_TOKEN_REQUESTS == 192
    for index in range(24):
        chunk = plan[index * 4 : index * 4 + 4]
        assert tuple(item[2] for item in chunk) == ("FORM_P4", *rag.SURFACES)
        assert len({item[0] for item in chunk}) == 1
        assert len({item[1] for item in chunk}) == 1


def test_confirmatory_analysis_is_exactly_two_holm_tests() -> None:
    h1 = [(True, False)] * 24
    h2 = [(True, True)] * 24
    analysis = rag.confirmatory_analysis(
        h1_typed_vs_role_functional=h1,
        h2_role_functional_vs_legacy=h2,
    )
    assert tuple(analysis) == rag.CONFIRMATORY_CONTRASTS
    assert analysis[rag.CONFIRMATORY_CONTRASTS[0]].table.left_only == 24
    assert analysis[rag.CONFIRMATORY_CONTRASTS[0]].holm_reject is True
    assert analysis[rag.CONFIRMATORY_CONTRASTS[1]].raw_p_value == 1.0
    assert analysis[rag.CONFIRMATORY_CONTRASTS[1]].holm_reject is False


def test_typed_vs_legacy_is_descriptive_only() -> None:
    table = rag.descriptive_typed_vs_legacy([(True, False)] * 24)
    assert table.left_only == 24
    assert not hasattr(table, "raw_p_value")
    assert rag.DESCRIPTIVE_ONLY_CONTRAST == "T_VS_L_DESCRIPTIVE_ONLY"


def test_repository_authority_is_zero_gpu_and_zero_rescue() -> None:
    assert rag.PHYSICAL_EXECUTION_AUTHORIZED is False
    assert rag.ARCHITECTURE_CONSEQUENCE == "NONE"
    assert set(rag.FORBIDDEN_RESCUE_COUNTS) == {
        "semantic_retry",
        "replay",
        "reseed",
        "fallback",
        "hidden_repair",
        "judge",
    }
    assert all(value == 0 for value in rag.FORBIDDEN_RESCUE_COUNTS.values())
    rag.validate_repository_binding()
