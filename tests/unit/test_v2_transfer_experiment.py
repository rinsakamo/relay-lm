from __future__ import annotations

import json

import pytest

from relaylm.v2_interventions import (
    InterventionError,
    ResourceLedger,
    ResourceLimitError,
    ResourceVector,
    assert_clean_intervention,
    compare_arms,
)
from relaylm.v2_semantics import TransactionRequest
from relaylm.v2_transfer_experiment import (
    REGIMES,
    generate_transfer_family,
    prepare_r0_arms,
    r0_transfer_spec,
    snapshot_r0_arm,
)


def _observe(store, observation):
    result = store.transact(
        TransactionRequest(
            base_generation=store.current_generation,
            observations=(observation,),
        )
    )
    return result.observation_records[0]


def test_r0_generator_is_deterministic_from_seed_and_regime():
    for regime in REGIMES:
        left = generate_transfer_family(seed=2157, regime=regime)
        right = generate_transfer_family(seed=2157, regime=regime)
        other_seed = generate_transfer_family(seed=2158, regime=regime)

        assert left == right
        assert left.public_target_digest == right.public_target_digest
        assert left.evidence_schedule_digest == right.evidence_schedule_digest
        assert left.public_target_digest != other_seed.public_target_digest


def test_r0_generator_relation_regimes_are_predeclared_and_hidden():
    shared = generate_transfer_family(seed=7, regime="shared")
    null = generate_transfer_family(seed=7, regime="null")
    mismatch = generate_transfer_family(seed=7, regime="mismatch")
    shift = generate_transfer_family(seed=7, regime="shift")

    assert shared.source_rule == shared.target_rules[0]
    assert all(rule == shared.source_rule for rule in shared.target_rules)

    assert null.target_rules[0] != null.source_rule
    assert all(rule == null.target_rules[0] for rule in null.target_rules)

    assert mismatch.target_rules[0] != mismatch.source_rule
    assert all(rule == mismatch.target_rules[0] for rule in mismatch.target_rules)

    assert shift.shift_index is not None
    assert all(
        rule == shift.source_rule
        for rule in shift.target_rules[: shift.shift_index]
    )
    assert all(
        rule != shift.source_rule
        for rule in shift.target_rules[shift.shift_index :]
    )

    for family in (shared, null, mismatch, shift):
        packet = json.loads(family.model_packet(0).decode("utf-8"))
        assert set(packet) == {"instruction", "examples", "query"}
        encoded = family.model_packet(0).decode("utf-8").lower()
        assert family.regime not in encoded
        assert family.source_rule.fingerprint() not in encoded
        assert all(rule.fingerprint() not in encoded for rule in family.target_rules)
        assert "expected" not in packet
        assert "rule" not in packet
        assert "arm" not in packet


def test_r0_hidden_verifier_accepts_exact_output_and_rejects_wrong_output():
    family = generate_transfer_family(seed=41, regime="shared")

    for step_index in range(len(family.target_steps)):
        expected = family.expected_output(step_index)
        good = family.verify_response(step_index, json.dumps(list(expected)))
        bad_values = list(expected)
        bad_values[0] = (bad_values[0] + 1) % family.modulus
        bad = family.verify_response(step_index, json.dumps(bad_values))
        malformed = family.verify_response(step_index, "not-json")

        assert good.correct
        assert good.parsed_output == expected
        assert not bad.correct
        assert not malformed.correct
        assert malformed.error == "invalid_json"


def test_r0_t0_t1_t2_share_canonical_start_and_only_projection_eligibility_differs():
    family = generate_transfer_family(seed=101, regime="shared")
    arms = prepare_r0_arms(family)

    assert arms.t0.store.canonical_snapshot() == arms.t1.store.canonical_snapshot()
    assert arms.t1.store.canonical_snapshot() == arms.t2.store.canonical_snapshot()
    assert arms.t0.task_digest == arms.t1.task_digest == arms.t2.task_digest
    assert (
        arms.t0.evidence_schedule_digest
        == arms.t1.evidence_schedule_digest
        == arms.t2.evidence_schedule_digest
    )
    assert (
        arms.t0.source_structure_id
        == arms.t1.source_structure_id
        == arms.t2.source_structure_id
    )
    assert arms.t0.source_structure_id in arms.t0.store.active_generation().active_roots
    assert arms.t0.source_structure_id not in arms.t0.projection.projected_roots
    assert arms.t1.source_structure_id in arms.t1.projection.projected_roots
    assert arms.t2.projection == arms.t1.projection

    diff = assert_clean_intervention(
        snapshot_r0_arm(arms.t0),
        snapshot_r0_arm(arms.t1),
        spec=r0_transfer_spec(),
    )
    assert diff.all_differences == ("allow_cross_task", "projected_roots")


def test_r0_shift_t1_t2_receive_identical_contradictory_evidence_identity():
    family = generate_transfer_family(seed=303, regime="shift")
    arms = prepare_r0_arms(family)
    assert family.shift_index is not None

    observation = family.feedback_observation(family.shift_index)
    t1_record = _observe(arms.t1.store, observation)
    t2_record = _observe(arms.t2.store, observation)

    assert t1_record == t2_record
    assert arms.t1.store.canonical_snapshot() == arms.t2.store.canonical_snapshot()
    assert tuple(sorted(arms.t1.store.provenance)) == tuple(sorted(arms.t2.store.provenance))


def test_r0_hidden_extra_model_work_is_detected_and_ledgered():
    family = generate_transfer_family(seed=505, regime="shared")
    arms = prepare_r0_arms(family)

    clean_t0 = snapshot_r0_arm(arms.t0)
    clean_t1 = snapshot_r0_arm(arms.t1)
    assert assert_clean_intervention(
        clean_t0,
        clean_t1,
        spec=r0_transfer_spec(),
    ).clean

    envelope = ResourceVector(calls=1, observation_units=1)
    ledger = ResourceLedger(envelope)
    ledger.spend("model-call", ResourceVector(calls=1))
    ledger.spend("feedback-observation", ResourceVector(observation_units=1))
    with pytest.raises(ResourceLimitError):
        ledger.spend("hidden-extra-call", ResourceVector(calls=1))

    contaminated_t1 = snapshot_r0_arm(
        arms.t1,
        resource_total=ledger.total,
    )
    diff = compare_arms(clean_t0, contaminated_t1, spec=r0_transfer_spec())
    assert "resource_total" in diff.unexpected_differences
    with pytest.raises(InterventionError, match="invalid arm differences"):
        assert_clean_intervention(
            clean_t0,
            contaminated_t1,
            spec=r0_transfer_spec(),
        )


def test_r0_hidden_extra_observation_is_detected_by_matched_arm_diff():
    family = generate_transfer_family(seed=606, regime="shared")
    arms = prepare_r0_arms(family)

    clean_t0 = snapshot_r0_arm(arms.t0)
    _observe(arms.t1.store, family.feedback_observation(0))
    contaminated_t1 = snapshot_r0_arm(arms.t1)

    diff = compare_arms(clean_t0, contaminated_t1, spec=r0_transfer_spec())
    assert "canonical_digest" in diff.unexpected_differences
    assert "provenance_ids" in diff.unexpected_differences


def test_r0_model_response_and_verifier_result_remain_non_authoritative():
    family = generate_transfer_family(seed=707, regime="shared")
    arms = prepare_r0_arms(family)
    before = arms.t1.store.canonical_snapshot()
    before_provenance = tuple(sorted(arms.t1.store.provenance))

    response = json.dumps(list(family.expected_output(0)))
    result = family.verify_response(0, response)

    assert result.correct
    assert arms.t1.store.canonical_snapshot() == before
    assert tuple(sorted(arms.t1.store.provenance)) == before_provenance
    assert response.encode("utf-8") not in before
