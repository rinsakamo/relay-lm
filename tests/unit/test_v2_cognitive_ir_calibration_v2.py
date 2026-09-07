from __future__ import annotations

from itertools import permutations

import pytest

from relaylm.v2_cognitive_ir_calibration import CALIBRATION_SEEDS
from relaylm.v2_cognitive_ir_calibration_v2 import (
    CALIBRATION_V2_CLAIM_STATUS,
    CALIBRATION_V2_PROVIDER_CALLS,
    CALIBRATION_V2_PROBES,
    CALIBRATION_V2_REGIMES,
    CALIBRATION_V2_SEED_COUNT,
    CALIBRATION_V2_SEEDS,
    CalibrationV2Error,
    CalibrationV2RegimeSummary,
    build_calibration_v2_messages,
    calibration_v2_call_plan,
    generate_calibration_v2_case,
    select_calibration_v2_regime,
)
from relaylm.v2_transfer_experiment import VectorRule


def _candidate_rules(examples):
    first = examples[0]
    values = []
    for permutation in permutations(range(4)):
        offsets = tuple(
            (first.output_values[index] - first.input_values[permutation[index]]) % 10
            for index in range(4)
        )
        rule = VectorRule(tuple(permutation), offsets, 10)
        if all(rule.apply(item.input_values) == item.output_values for item in examples):
            values.append(rule)
    return tuple(values)


def _wrap_count(case, values):
    return sum(
        values[case.rule.permutation[index]] + case.rule.offsets[index] >= case.rule.modulus
        for index in range(4)
    )


def test_calibration_v2_seed_rule_is_fresh_and_bounded() -> None:
    assert len(CALIBRATION_V2_SEEDS) == CALIBRATION_V2_SEED_COUNT == 6
    assert len(set(CALIBRATION_V2_SEEDS)) == 6
    assert 2211 not in CALIBRATION_V2_SEEDS
    assert set(CALIBRATION_V2_SEEDS).isdisjoint(CALIBRATION_SEEDS)
    assert CALIBRATION_V2_CLAIM_STATUS == "NON_CITABLE_S2_CALIBRATION_V2"


def test_calibration_v2_call_plan_is_exactly_72_nonadaptive_cells() -> None:
    plan = calibration_v2_call_plan()
    assert CALIBRATION_V2_PROVIDER_CALLS == 72
    assert len(plan) == 72
    assert len(set(plan)) == 72
    assert len(CALIBRATION_V2_REGIMES) == 4
    assert len(CALIBRATION_V2_PROBES) == 3


@pytest.mark.parametrize("regime", CALIBRATION_V2_REGIMES)
@pytest.mark.parametrize("seed", CALIBRATION_V2_SEEDS)
def test_every_calibration_v2_case_is_globally_identifiable(seed: int, regime: str) -> None:
    case = generate_calibration_v2_case(seed=seed, regime=regime)
    assert _candidate_rules(case.examples) == (case.rule,)
    assert len(case.examples) == 4


@pytest.mark.parametrize("seed", CALIBRATION_V2_SEEDS)
def test_single_swap_regimes_have_exactly_two_moved_positions(seed: int) -> None:
    for regime in (
        "V2_SINGLE_SWAP_ZERO_OFFSET",
        "V2_SINGLE_SWAP_OFFSET_NO_WRAP",
    ):
        case = generate_calibration_v2_case(seed=seed, regime=regime)
        moved = sum(index != value for index, value in enumerate(case.rule.permutation))
        assert moved == 2


@pytest.mark.parametrize("seed", CALIBRATION_V2_SEEDS)
def test_zero_offset_regime_has_no_arithmetic_component(seed: int) -> None:
    case = generate_calibration_v2_case(
        seed=seed,
        regime="V2_SINGLE_SWAP_ZERO_OFFSET",
    )
    assert case.rule.offsets == (0, 0, 0, 0)


@pytest.mark.parametrize("seed", CALIBRATION_V2_SEEDS)
def test_no_wrap_regimes_have_no_wrap_in_examples_or_query(seed: int) -> None:
    for regime in (
        "V2_IDENTITY_OFFSET_NO_WRAP",
        "V2_SINGLE_SWAP_OFFSET_NO_WRAP",
    ):
        case = generate_calibration_v2_case(seed=seed, regime=regime)
        assert case.query_wrap_count == 0
        assert all(_wrap_count(case, item.input_values) == 0 for item in case.examples)
        assert all(offset in {1, 2, 3} for offset in case.rule.offsets)


@pytest.mark.parametrize("seed", CALIBRATION_V2_SEEDS)
def test_wrap_control_forces_query_wrap_without_permutation(seed: int) -> None:
    case = generate_calibration_v2_case(seed=seed, regime="V2_IDENTITY_OFFSET_WRAP")
    assert case.rule.permutation == (0, 1, 2, 3)
    assert case.query_wrap_count >= 2


def test_formation_prompts_do_not_expose_evaluator_rule_values() -> None:
    case = generate_calibration_v2_case(
        seed=CALIBRATION_V2_SEEDS[0],
        regime="V2_SINGLE_SWAP_OFFSET_NO_WRAP",
    )
    c1 = build_calibration_v2_messages(case, "C1_FORMATION_ONLY")
    c2 = build_calibration_v2_messages(case, "C2_END_TO_END")
    for messages in (c1, c2):
        user = messages[1]["content"]
        assert '"examples"' in user
        assert '"rule"' not in user
        assert '"permutation"' not in user
        assert '"offsets"' not in user
        assert "source-index-for-output" in messages[0]["content"]
        assert "Do not assume identity mapping" in messages[0]["content"]


def _summaries(*, admitted: str | None) -> tuple[CalibrationV2RegimeSummary, ...]:
    values = []
    for regime in CALIBRATION_V2_REGIMES:
        if regime == admitted:
            counts = (6, 3, 3)
        else:
            counts = (5, 3, 3)
        values.append(
            CalibrationV2RegimeSummary(
                regime=regime,
                sample_count=6,
                application_correct=counts[0],
                formation_correct=counts[1],
                end_to_end_joint_correct=counts[2],
            )
        )
    return tuple(values)


def test_selection_keeps_original_admission_thresholds() -> None:
    admitted = CalibrationV2RegimeSummary(
        regime="V2_SINGLE_SWAP_ZERO_OFFSET",
        sample_count=6,
        application_correct=6,
        formation_correct=3,
        end_to_end_joint_correct=2,
    )
    assert admitted.admitted
    assert not CalibrationV2RegimeSummary(
        regime="V2_SINGLE_SWAP_ZERO_OFFSET",
        sample_count=6,
        application_correct=5,
        formation_correct=3,
        end_to_end_joint_correct=2,
    ).admitted
    assert not CalibrationV2RegimeSummary(
        regime="V2_SINGLE_SWAP_ZERO_OFFSET",
        sample_count=6,
        application_correct=6,
        formation_correct=2,
        end_to_end_joint_correct=2,
    ).admitted
    assert not CalibrationV2RegimeSummary(
        regime="V2_SINGLE_SWAP_ZERO_OFFSET",
        sample_count=6,
        application_correct=6,
        formation_correct=3,
        end_to_end_joint_correct=5,
    ).admitted


def test_selection_uses_predeclared_compositional_priority() -> None:
    assert select_calibration_v2_regime(_summaries(admitted=None)) is None
    assert (
        select_calibration_v2_regime(_summaries(admitted="V2_SINGLE_SWAP_ZERO_OFFSET"))
        == "V2_SINGLE_SWAP_ZERO_OFFSET"
    )

    all_admitted = tuple(
        CalibrationV2RegimeSummary(
            regime=regime,
            sample_count=6,
            application_correct=6,
            formation_correct=3,
            end_to_end_joint_correct=3,
        )
        for regime in CALIBRATION_V2_REGIMES
    )
    assert select_calibration_v2_regime(all_admitted) == "V2_SINGLE_SWAP_OFFSET_NO_WRAP"


def test_selection_rejects_incomplete_summary_set() -> None:
    with pytest.raises(CalibrationV2Error):
        select_calibration_v2_regime(_summaries(admitted=None)[:-1])
