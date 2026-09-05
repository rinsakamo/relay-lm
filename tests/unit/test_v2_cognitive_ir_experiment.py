from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_experiment import (
    CognitiveIRExperimentError,
    REPRESENTATION_KINDS,
    assert_r0_admission,
    decode_semantic_payload,
    neutralize_typed_payload,
    prepare_r0_representation_arms,
    render_surface_variant,
    semantic_digest,
)
from relaylm.v2_transfer_experiment import generate_transfer_family


def test_r0_declares_all_required_representation_arms():
    assert REPRESENTATION_KINDS == (
        "P0_RAW_HISTORY",
        "P1_RETRIEVAL_ONLY",
        "P2_ORDINARY_SUMMARY",
        "P3_SEMANTIC_CACHE",
        "P4_MEMORY_PLUS_STRUCTURE",
        "P5_STRUCTURE_ONLY_RECONSTRUCTABLE",
        "P6_GENERIC_EQUAL_INFORMATION",
    )


def test_r0_all_arms_share_source_target_and_provenance_identity():
    family = generate_transfer_family(seed=2211, regime="shared")
    arms = prepare_r0_representation_arms(family)

    assert tuple(arms) == REPRESENTATION_KINDS
    source_digests = {arm.source_history_digest for arm in arms.values()}
    target_digests = {arm.target_task_digest for arm in arms.values()}
    provenance_sets = {arm.provenance_handles for arm in arms.values()}

    assert len(source_digests) == 1
    assert len(target_digests) == 1
    assert len(provenance_sets) == 1
    assert all(arm.r0_oracle_upper_bound for arm in arms.values())
    assert all(not arm.empirical_claim_allowed for arm in arms.values())

    report = assert_r0_admission(arms)
    assert report.clean
    assert report.typed_generic_semantic_equal
    assert report.shared_source_identity
    assert report.shared_target_identity
    assert report.shared_provenance_identity


def test_r0_p4_to_p6_neutralization_preserves_semantics_without_ontology_labels():
    family = generate_transfer_family(seed=41, regime="shared")
    arms = prepare_r0_representation_arms(family)
    typed = arms["P4_MEMORY_PLUS_STRUCTURE"]
    generic = arms["P6_GENERIC_EQUAL_INFORMATION"]

    typed_payload = json.loads(typed.serialized)
    neutralized = neutralize_typed_payload(typed_payload)

    assert neutralized == json.loads(generic.serialized)
    assert decode_semantic_payload(typed.kind, typed_payload) == decode_semantic_payload(
        generic.kind,
        neutralized,
    )
    assert semantic_digest(typed.kind, typed_payload) == semantic_digest(
        generic.kind,
        neutralized,
    )

    generic_text = generic.serialized.lower()
    for forbidden in ("memory", "structure", "crystal"):
        assert forbidden not in generic_text


def test_r0_surface_variants_preserve_meaning_while_semantic_intervention_changes_it():
    family = generate_transfer_family(seed=303, regime="shared")
    arms = prepare_r0_representation_arms(family)
    typed = arms["P4_MEMORY_PLUS_STRUCTURE"]
    canonical = json.loads(typed.serialized)
    base_digest = semantic_digest(typed.kind, canonical)

    renamed = render_surface_variant(typed.kind, canonical, variant="neutral_keys")
    reordered = render_surface_variant(typed.kind, canonical, variant="reordered")

    assert semantic_digest("P6_GENERIC_EQUAL_INFORMATION", renamed) == base_digest
    assert semantic_digest(typed.kind, reordered) == base_digest

    changed = json.loads(typed.serialized)
    changed["structure"]["offsets"][0] = (
        changed["structure"]["offsets"][0] + 1
    ) % changed["structure"]["modulus"]
    assert semantic_digest(typed.kind, changed) != base_digest


def test_r0_structure_only_keeps_reconstruction_path_but_does_not_project_episode_payloads():
    family = generate_transfer_family(seed=505, regime="shared")
    arms = prepare_r0_representation_arms(family)
    p5 = arms["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"]
    encoded = json.loads(p5.serialized)

    assert p5.reconstruction_handles == p5.provenance_handles
    assert encoded["reusable_relation"]
    assert "records" not in encoded
    assert "episodes" not in encoded
    assert all(handle not in p5.serialized for handle in p5.provenance_handles)


def test_r0_raw_and_retrieval_preserve_episode_records_without_compiled_rule():
    family = generate_transfer_family(seed=606, regime="shared")
    arms = prepare_r0_representation_arms(family)

    raw = json.loads(arms["P0_RAW_HISTORY"].serialized)
    retrieval = json.loads(arms["P1_RETRIEVAL_ONLY"].serialized)

    assert raw["records"] == retrieval["records"]
    assert retrieval["selected_refs"] == [record["ref"] for record in retrieval["records"]]
    assert "structure" not in arms["P0_RAW_HISTORY"].serialized.lower()
    assert "structure" not in arms["P1_RETRIEVAL_ONLY"].serialized.lower()
    assert "permutation" not in arms["P0_RAW_HISTORY"].serialized.lower()
    assert "offsets" not in arms["P1_RETRIEVAL_ONLY"].serialized.lower()


def test_r0_summary_is_faithful_episode_recap_not_oracle_rule_dump():
    family = generate_transfer_family(seed=707, regime="shared")
    arms = prepare_r0_representation_arms(family)
    summary = json.loads(arms["P2_ORDINARY_SUMMARY"].serialized)

    assert set(summary) == {"recap"}
    assert len(summary["recap"]) == len(family.source_examples)
    assert all("input" in item and "output" in item for item in summary["recap"])
    encoded = arms["P2_ORDINARY_SUMMARY"].serialized.lower()
    assert "permutation" not in encoded
    assert "offsets" not in encoded
    assert "modulus" not in encoded


def test_r0_semantic_cache_is_explicitly_oracle_upper_bound_not_primary_evidence():
    family = generate_transfer_family(seed=808, regime="shared")
    arms = prepare_r0_representation_arms(family)
    cache = arms["P3_SEMANTIC_CACHE"]
    payload = json.loads(cache.serialized)

    assert payload["r0_fixture"] == "oracle_upper_bound"
    assert cache.r0_oracle_upper_bound
    assert not cache.empirical_claim_allowed

    with pytest.raises(CognitiveIRExperimentError, match="R0 oracle"):
        cache.require_empirical_claim_eligibility()


def test_r0_admission_fails_closed_if_generic_payload_drops_semantic_information():
    family = generate_transfer_family(seed=909, regime="shared")
    arms = prepare_r0_representation_arms(family)
    generic = arms["P6_GENERIC_EQUAL_INFORMATION"]
    payload = json.loads(generic.serialized)
    payload["relation"]["b"] = payload["relation"]["b"][:-1]
    generic.serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))

    with pytest.raises(CognitiveIRExperimentError, match="typed/generic semantic mismatch"):
        assert_r0_admission(arms)
