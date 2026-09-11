from __future__ import annotations

import json

import pytest

from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_s3_r4 import S3_R4_PREREGISTRATION_SHA256
from relaylm.v2_cognitive_ir_shared_floor_calibration import (
    NO_SHARED_TARGET_RANGE_FOUND,
    SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE,
    SHARED_FLOOR_CALLS_PER_DIFFICULTY,
    SHARED_FLOOR_CITABLE,
    SHARED_FLOOR_DIFFICULTIES,
    SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY,
    SHARED_FLOOR_LABEL,
    SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    SHARED_FLOOR_MAX_SEMANTIC_CALLS,
    SHARED_FLOOR_NEUTRAL_ARMS,
    SHARED_FLOOR_SEEDS,
    SHARED_TARGET_RANGE_QUALIFIED,
    SharedFloorCalibrationError,
    SharedFloorSeedResult,
    build_explicit_application_messages,
    derive_shared_floor_seed,
    generate_shared_floor_family,
    run_shared_floor_calibration,
    shared_floor_call_plan,
    shared_floor_offsets,
    summarize_shared_floor_candidate,
    validate_shared_floor_preregistration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
from tools.v2_cognitive_ir_s3_r4_llama_cpp import S3R4LlamaCppClient
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    SharedFloorLlamaCppClient,
)
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as wsl


def test_shared_floor_exact_preregistration_and_accounting() -> None:
    validate_shared_floor_preregistration()
    assert SHARED_FLOOR_LABEL == (
        "relaylm2-cognitive-ir-shared-floor-calibration-v1"
    )
    assert tuple(derive_shared_floor_seed(index) for index in range(6)) == (
        824131651,
        727517075,
        1455229498,
        691488953,
        1485742517,
        411743139,
    )
    assert SHARED_FLOOR_SEEDS == (
        824131651,
        727517075,
        1455229498,
        691488953,
        1485742517,
        411743139,
    )
    assert SHARED_FLOOR_DIFFICULTIES == (
        "K4_CURRENT_CLASS",
        "K3_THREE_ACTIVE",
        "K2_TWO_ACTIVE",
        "K1_ONE_ACTIVE",
    )
    assert SHARED_FLOOR_CALLS_PER_DIFFICULTY == 54
    assert SHARED_FLOOR_INPUT_TOKEN_REQUESTS_PER_DIFFICULTY == 108
    assert SHARED_FLOOR_MAX_SEMANTIC_CALLS == 216
    assert SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS == 432
    assert SHARED_FLOOR_CITABLE is False
    assert SHARED_FLOOR_ARCHITECTURE_CONSEQUENCE == "NONE"
    assert S3_R4_PREREGISTRATION_SHA256 == (
        "deb10b356f1cfe4fd18275b790f1a5bcb5972b1b841e874c26a8827ffd20dae4"
    )


@pytest.mark.parametrize(
    ("difficulty", "active_count"),
    [
        ("K4_CURRENT_CLASS", 4),
        ("K3_THREE_ACTIVE", 3),
        ("K2_TWO_ACTIVE", 2),
        ("K1_ONE_ACTIVE", 1),
    ],
)
def test_shared_floor_ladder_changes_only_active_offset_count(
    difficulty: str,
    active_count: int,
) -> None:
    for index, seed in enumerate(SHARED_FLOOR_SEEDS):
        family = generate_shared_floor_family(difficulty, index)
        offsets = shared_floor_offsets(difficulty, seed)
        assert family.source_rule.permutation == (0, 1, 2, 3)
        assert family.source_rule.offsets == offsets
        assert sum(value != 0 for value in offsets) == active_count
        assert all(value in (0, 1, 2, 3) for value in offsets)
        assert all(
            value in (1, 2, 3)
            for value in offsets
            if value != 0
        )
        assert family.source_rule == family.target_rules[0]
        assert family.regime == "shared"

        first = family.source_examples[0]
        inferred = tuple(
            first.output_values[coordinate] - first.input_values[coordinate]
            for coordinate in range(4)
        )
        assert inferred == offsets
        assert all(
            vector[coordinate] + offsets[coordinate] < 10
            for vector in (
                [example.input_values for example in family.source_examples]
                + [step.query for step in family.target_steps]
            )
            for coordinate in range(4)
        )


def test_shared_floor_public_inputs_and_queries_do_not_change_with_difficulty() -> None:
    for index in range(6):
        families = [
            generate_shared_floor_family(difficulty, index)
            for difficulty in SHARED_FLOOR_DIFFICULTIES
        ]
        source_inputs = [
            tuple(example.input_values for example in family.source_examples)
            for family in families
        ]
        queries = [
            tuple(step.query for step in family.target_steps)
            for family in families
        ]
        assert len(set(source_inputs)) == 1
        assert len(set(queries)) == 1


def test_shared_floor_call_plan_is_exact_and_outcome_blind() -> None:
    for difficulty in SHARED_FLOOR_DIFFICULTIES:
        plan = shared_floor_call_plan(difficulty)
        assert len(plan) == 54
        assert sum(question.endswith(":a0-explicit") for question in plan) == 6
        assert sum(question.endswith(":form-p2") for question in plan) == 6
        assert sum(question.endswith(":form-p3") for question in plan) == 6
        assert sum(question.endswith(":form-p4") for question in plan) == 6
        assert sum(":canonical:" in question for question in plan) == 30
        assert not any(
            ":canonical:P4_MEMORY_PLUS_STRUCTURE" in question
            or ":canonical:P5_STRUCTURE_ONLY_RECONSTRUCTABLE" in question
            or ":surface:" in question
            or ":semantic:" in question
            or ":option:" in question
            or ":null:" in question
            or ":mismatch:" in question
            or ":shift:" in question
            for question in plan
        )


def test_explicit_rule_diagnostic_is_isolated_from_scientific_formation() -> None:
    family = generate_shared_floor_family("K4_CURRENT_CLASS", 0)
    diagnostic = build_explicit_application_messages(family)
    assert "explicit_rule" in diagnostic[1]["content"]
    for kind in (
        "P2_ORDINARY_SUMMARY",
        "P3_SEMANTIC_CACHE",
        "P4_MEMORY_PLUS_STRUCTURE",
    ):
        messages = build_s2_formation_messages(kind, family)
        assert all("explicit_rule" not in message["content"] for message in messages)


def _seed_result(
    index: int,
    *,
    difficulty: str = "K4_CURRENT_CLASS",
    application: bool = True,
    formation: bool = True,
    correct_arms: tuple[str, ...] = (),
) -> SharedFloorSeedResult:
    return SharedFloorSeedResult(
        difficulty=difficulty,
        seed=SHARED_FLOOR_SEEDS[index],
        application_correct=application,
        formation_correct=formation,
        neutral_correct={
            arm: arm in correct_arms for arm in SHARED_FLOOR_NEUTRAL_ARMS
        },
        p4_p6_semantic_equal=True,
        shared_formation_lineage=True,
    )


def test_shared_floor_admission_boundary_accepts_exact_twenty_percent() -> None:
    seeds = tuple(
        _seed_result(
            index,
            correct_arms=(
                ("P0_RAW_HISTORY",)
                if index < 3
                else ("P1_RETRIEVAL_ONLY",)
            ),
        )
        for index in range(6)
    )
    candidate = summarize_shared_floor_candidate("K4_CURRENT_CLASS", seeds)
    assert candidate.neutral_correct["P0_RAW_HISTORY"] == 3
    assert candidate.neutral_correct["P1_RETRIEVAL_ONLY"] == 3
    assert candidate.neutral_control_mean == pytest.approx(0.20)
    assert candidate.neutral_non_degenerate_arm_count == 2
    assert candidate.admitted is True


def test_shared_floor_requires_two_non_degenerate_neutral_arms() -> None:
    seeds = tuple(
        _seed_result(
            index,
            correct_arms=(
                ("P0_RAW_HISTORY", "P1_RETRIEVAL_ONLY")
                if index < 3
                else ("P0_RAW_HISTORY",)
            ),
        )
        for index in range(6)
    )
    candidate = summarize_shared_floor_candidate("K4_CURRENT_CLASS", seeds)
    assert candidate.neutral_control_mean == pytest.approx(0.30)
    assert candidate.neutral_correct["P0_RAW_HISTORY"] == 6
    assert candidate.neutral_correct["P1_RETRIEVAL_ONLY"] == 3
    assert candidate.neutral_non_degenerate_arm_count == 1
    assert candidate.admitted is False


@pytest.mark.parametrize(
    ("application", "formation", "p2_admitted"),
    [
        (False, True, 6),
        (True, False, 6),
        (True, True, 5),
    ],
)
def test_shared_floor_requires_all_mechanical_diagnostic_gates(
    application: bool,
    formation: bool,
    p2_admitted: int,
) -> None:
    seeds = tuple(
        _seed_result(
            index,
            application=application,
            formation=formation,
            correct_arms=(
                ("P0_RAW_HISTORY",)
                if index < 3
                else ("P1_RETRIEVAL_ONLY",)
            ),
        )
        for index in range(6)
    )
    candidate = summarize_shared_floor_candidate(
        "K4_CURRENT_CLASS",
        seeds,
        p2_hard_admitted=p2_admitted,
    )
    assert candidate.admitted is False


class _FakeClient:
    def __init__(
        self,
        difficulty: str,
        call_plan: tuple[str, ...],
        *,
        qualifying_difficulty: str | None,
    ) -> None:
        self.difficulty = difficulty
        self.call_plan = call_plan
        self.qualifying_difficulty = qualifying_difficulty
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
        assert question_id == self.call_plan[self._index]
        self._index += 1
        self.provider_attempts += 1
        self.provider_completions += 1
        self.input_count_attempts += 2
        self.input_count_completions += 2

        parts = question_id.split(":")
        index = int(parts[1])
        family = generate_shared_floor_family(self.difficulty, index)
        expected = list(family.expected_output(0))

        if question_id.endswith(":a0-explicit"):
            content = json.dumps(expected)
        elif question_id.endswith(":form-p2"):
            content = "A concise bounded recap of the observed source episodes."
        elif question_id.endswith(":form-p3"):
            content = "A compact neutral gist of the observed source episodes."
        elif question_id.endswith(":form-p4"):
            content = json.dumps(
                {
                    "permutation": list(family.source_rule.permutation),
                    "offsets": list(family.source_rule.offsets),
                    "modulus": family.modulus,
                }
            )
        elif ":canonical:" in question_id:
            arm = question_id.rsplit(":", 1)[-1]
            correct = False
            if self.difficulty == self.qualifying_difficulty:
                correct = (
                    (arm == "P0_RAW_HISTORY" and index < 3)
                    or (arm == "P1_RETRIEVAL_ONLY" and index >= 3)
                )
            if correct:
                content = json.dumps(expected)
            else:
                wrong = list(expected)
                wrong[0] = (wrong[0] + 1) % family.modulus
                content = json.dumps(wrong)
        else:
            raise AssertionError(f"unexpected fake call: {question_id}")

        return ExperimentCompletion(
            content=content,
            input_tokens=11,
            output_tokens=7,
            response_id=f"fake-{self._index}",
        )

    def require_complete_plan(self) -> None:
        assert self._index == len(self.call_plan)


def test_shared_floor_hardest_first_early_stop_never_observes_easier_candidates() -> None:
    created: list[str] = []

    def factory(
        difficulty: str,
        call_plan: tuple[str, ...],
    ) -> _FakeClient:
        created.append(difficulty)
        return _FakeClient(
            difficulty,
            call_plan,
            qualifying_difficulty="K4_CURRENT_CLASS",
        )

    result = run_shared_floor_calibration(factory)
    assert result.classification == SHARED_TARGET_RANGE_QUALIFIED
    assert result.selected_difficulty == "K4_CURRENT_CLASS"
    assert created == ["K4_CURRENT_CLASS"]
    assert result.semantic_calls == 54
    assert result.input_token_requests == 108


def test_shared_floor_no_range_exhausts_exact_frozen_maximum() -> None:
    created: list[str] = []

    def factory(
        difficulty: str,
        call_plan: tuple[str, ...],
    ) -> _FakeClient:
        created.append(difficulty)
        return _FakeClient(
            difficulty,
            call_plan,
            qualifying_difficulty=None,
        )

    result = run_shared_floor_calibration(factory)
    assert result.classification == NO_SHARED_TARGET_RANGE_FOUND
    assert result.selected_difficulty is None
    assert created == list(SHARED_FLOOR_DIFFICULTIES)
    assert result.semantic_calls == 216
    assert result.input_token_requests == 432


def test_shared_floor_rejects_k0_and_transport_inherits_r4_hard_gate() -> None:
    with pytest.raises(SharedFloorCalibrationError):
        shared_floor_offsets("K0", SHARED_FLOOR_SEEDS[0])
    assert issubclass(SharedFloorLlamaCppClient, S3R4LlamaCppClient)
    assert wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    )
