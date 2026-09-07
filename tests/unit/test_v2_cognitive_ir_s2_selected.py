from __future__ import annotations

import json

from relaylm.v2_cognitive_ir_actual_model import (
    build_s2_formation_messages,
    build_s2_target_messages,
)
from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import CALIBRATION_V2_SEEDS
from relaylm.v2_cognitive_ir_experiment import (
    assert_r0_admission,
    prepare_r0_representation_arms,
)
from relaylm.v2_cognitive_ir_s2_selected import (
    CALIBRATION_V2_ADMISSION_IDENTITY_FINGERPRINT,
    CALIBRATION_V2_ADMISSION_REPOSITORY_COMMIT,
    CALIBRATION_V2_ADMISSION_RUN_ID,
    S2_SELECTED_EXAMPLES_VISIBLE,
    S2_SELECTED_PHYSICAL_CALLS,
    S2_SELECTED_REGIME,
    S2_SELECTED_SEED,
    S2_SELECTED_STEP_INDEX,
    calibration_v2_admission_summaries,
    generate_selected_s2_family,
    replay_selected_regime,
    selected_s2_preregistration,
    wrap_count,
)


def test_completed_calibration_v2_replays_exact_selected_regime() -> None:
    summaries = calibration_v2_admission_summaries()
    observed = {
        item.regime: (
            item.application_correct,
            item.formation_correct,
            item.end_to_end_joint_correct,
            item.admitted,
        )
        for item in summaries
    }

    assert observed == {
        "V2_SINGLE_SWAP_ZERO_OFFSET": (6, 6, 5, False),
        "V2_IDENTITY_OFFSET_NO_WRAP": (6, 5, 4, True),
        "V2_IDENTITY_OFFSET_WRAP": (6, 2, 1, False),
        "V2_SINGLE_SWAP_OFFSET_NO_WRAP": (2, 0, 0, False),
    }
    assert replay_selected_regime() == S2_SELECTED_REGIME


def test_selected_s2_seed_is_fresh_relative_to_all_calibration_evidence() -> None:
    assert S2_SELECTED_SEED == 1399709667
    assert S2_SELECTED_SEED != 2211
    assert S2_SELECTED_SEED not in CALIBRATION_SEEDS
    assert S2_SELECTED_SEED not in CALIBRATION_V2_SEEDS


def test_selected_s2_family_is_identity_offset_no_wrap_and_globally_identifiable() -> None:
    family = generate_selected_s2_family()

    assert family.seed == S2_SELECTED_SEED
    assert family.regime == "shared"
    assert family.modulus == 10
    assert family.source_rule.permutation == (0, 1, 2, 3)
    assert family.source_rule.offsets == (3, 2, 1, 1)
    assert all(value > 0 for value in family.source_rule.offsets)
    assert len(family.source_examples) == 4
    assert len(family.target_steps) == 1
    assert len(family.target_steps[0].examples) == 3
    assert all(
        wrap_count(family.source_rule, item.input_values) == 0
        for item in family.source_examples
    )
    assert all(
        wrap_count(family.source_rule, item.input_values) == 0
        for item in family.target_steps[0].examples
    )
    assert wrap_count(family.source_rule, family.target_steps[0].query) == 0

    # The deterministic source packet itself is enough to identify one rule in the
    # full public affine-permutation class; S2 does not rely on a hidden identity prior.
    assert family.source_examples == (
        type(family.source_examples[0])((2, 1, 3, 4), (5, 3, 4, 5)),
        type(family.source_examples[0])((0, 6, 0, 2), (3, 8, 1, 3)),
        type(family.source_examples[0])((1, 7, 3, 8), (4, 9, 4, 9)),
        type(family.source_examples[0])((0, 4, 2, 2), (3, 6, 3, 3)),
    )


def test_selected_family_preserves_existing_p0_p6_r0_fairness_contract() -> None:
    family = generate_selected_s2_family()
    report = assert_r0_admission(prepare_r0_representation_arms(family))

    assert report.clean is True
    assert report.shared_source_identity is True
    assert report.shared_target_identity is True
    assert report.shared_provenance_identity is True
    assert report.typed_generic_semantic_equal is True


def test_selected_s2_public_formation_packet_does_not_reveal_hidden_rule() -> None:
    family = generate_selected_s2_family()
    messages = build_s2_formation_messages("P4_MEMORY_PLUS_STRUCTURE", family)
    packet = json.loads(messages[1]["content"])

    assert set(packet) == {"modulus", "examples"}
    assert "permutation" not in packet
    assert "offsets" not in packet
    assert packet["modulus"] == 10
    assert len(packet["examples"]) == 4


def test_selected_s2_target_freezes_zero_visible_target_examples() -> None:
    family = generate_selected_s2_family()
    representation = prepare_r0_representation_arms(family)["P0_RAW_HISTORY"]
    from relaylm.v2_cognitive_ir_actual_model import S2Representation

    projected = S2Representation(
        kind=representation.kind,
        serialized=representation.serialized,
        provenance_handles=representation.provenance_handles,
        reconstruction_handles=representation.reconstruction_handles,
        formation_completion=None,
        formation_calls=0,
        formation_input_tokens=0,
        formation_output_tokens=0,
    )
    prompt = build_s2_target_messages(
        projected,
        family,
        step_index=S2_SELECTED_STEP_INDEX,
        examples_visible=S2_SELECTED_EXAMPLES_VISIBLE,
    )

    assert prompt.task_packet["examples"] == []
    assert prompt.task_packet["query"] == [6, 5, 6, 8]
    assert family.expected_output(0) == (9, 7, 7, 9)


def test_selected_s2_preregistration_freezes_calibration_provenance_and_ten_calls() -> None:
    prereg = selected_s2_preregistration()

    assert prereg.calibration_repository_commit == CALIBRATION_V2_ADMISSION_REPOSITORY_COMMIT
    assert prereg.calibration_run_id == CALIBRATION_V2_ADMISSION_RUN_ID
    assert (
        prereg.calibration_identity_fingerprint
        == CALIBRATION_V2_ADMISSION_IDENTITY_FINGERPRINT
    )
    assert prereg.selected_regime == S2_SELECTED_REGIME
    assert prereg.family_seed == S2_SELECTED_SEED
    assert prereg.transfer_regime == "shared"
    assert prereg.step_index == 0
    assert prereg.examples_visible == 0
    assert prereg.planned_provider_calls == S2_SELECTED_PHYSICAL_CALLS == 10
