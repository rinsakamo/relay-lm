from __future__ import annotations

import json

from relaylm.v2_cognitive_ir_shared_floor_calibration import (
    SHARED_FLOOR_DIFFICULTIES,
    SHARED_FLOOR_SEEDS,
    generate_shared_floor_family,
)
from relaylm.v2_cognitive_ir_shared_floor_calibration_v2 import (
    SHARED_FLOOR_V2_LABEL,
    SHARED_FLOOR_V2_SEEDS,
    derive_shared_floor_v2_seed,
    generate_shared_floor_v2_family,
    run_shared_floor_v2_calibration,
    shared_floor_v2_call_plan,
    shared_floor_v2_offsets,
    validate_shared_floor_v2_preregistration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as legacy_tx
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy_wsl
import tools.v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp_transaction as tx_v2
import tools.v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp_wsl as wsl_v2
from tools.v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp import (
    run_llama_cpp_shared_floor_calibration_v2,
)


def test_v2_identity_is_exact_disjoint_and_v1_stays_historical() -> None:
    validate_shared_floor_v2_preregistration()
    assert SHARED_FLOOR_V2_LABEL == (
        "relaylm2-cognitive-ir-shared-floor-calibration-v2"
    )
    assert tuple(derive_shared_floor_v2_seed(index) for index in range(6)) == (
        1142504739,
        1503134270,
        356394414,
        1625198782,
        1873901982,
        2032603824,
    )
    assert SHARED_FLOOR_V2_SEEDS == (
        1142504739,
        1503134270,
        356394414,
        1625198782,
        1873901982,
        2032603824,
    )
    assert set(SHARED_FLOOR_V2_SEEDS).isdisjoint(SHARED_FLOOR_SEEDS)
    assert SHARED_FLOOR_SEEDS == (
        824131651,
        727517075,
        1455229498,
        691488953,
        1485742517,
        411743139,
    )
    # Historical v1 generator remains unchanged by the v2 identity layer.
    assert generate_shared_floor_family("K4_CURRENT_CLASS", 0).source_rule.offsets == (
        1,
        2,
        2,
        3,
    )
    assert generate_shared_floor_family("K3_THREE_ACTIVE", 0).source_rule.offsets == (
        1,
        0,
        2,
        3,
    )


def test_v2_nested_ladder_changes_only_active_count() -> None:
    for index, seed in enumerate(SHARED_FLOOR_V2_SEEDS):
        families = {
            difficulty: generate_shared_floor_v2_family(difficulty, index)
            for difficulty in SHARED_FLOOR_DIFFICULTIES
        }
        offsets = {
            difficulty: shared_floor_v2_offsets(difficulty, seed)
            for difficulty in SHARED_FLOOR_DIFFICULTIES
        }
        assert [sum(value != 0 for value in offsets[difficulty]) for difficulty in SHARED_FLOOR_DIFFICULTIES] == [4, 3, 2, 1]

        previous_active = set(range(4))
        k4_values = offsets["K4_CURRENT_CLASS"]
        for difficulty in SHARED_FLOOR_DIFFICULTIES[1:]:
            active = {
                coordinate
                for coordinate, value in enumerate(offsets[difficulty])
                if value != 0
            }
            assert active < previous_active
            assert all(offsets[difficulty][coordinate] == k4_values[coordinate] for coordinate in active)
            previous_active = active

        source_inputs = {
            tuple(example.input_values for example in family.source_examples)
            for family in families.values()
        }
        queries = {
            tuple(step.query for step in family.target_steps)
            for family in families.values()
        }
        assert len(source_inputs) == 1
        assert len(queries) == 1


def test_v2_call_plan_is_exact_and_outcome_blind() -> None:
    for difficulty in SHARED_FLOOR_DIFFICULTIES:
        plan = shared_floor_v2_call_plan(difficulty)
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


class _FakeClient:
    def __init__(self, difficulty: str, call_plan: tuple[str, ...]) -> None:
        self.difficulty = difficulty
        self.call_plan = call_plan
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
        del messages, output_kind
        assert question_id == self.call_plan[self._index]
        self._index += 1
        self.provider_attempts += 1
        self.provider_completions += 1
        self.input_count_attempts += 2
        self.input_count_completions += 2

        parts = question_id.split(":")
        index = int(parts[1])
        family = generate_shared_floor_v2_family(self.difficulty, index)
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


def test_v2_calibration_keeps_frozen_early_stop_and_accounting() -> None:
    created: list[str] = []

    def factory(difficulty: str, call_plan: tuple[str, ...]) -> _FakeClient:
        created.append(difficulty)
        return _FakeClient(difficulty, call_plan)

    result = run_shared_floor_v2_calibration(factory)
    assert result.selected_difficulty == "K4_CURRENT_CLASS"
    assert result.classification == "SHARED_TARGET_RANGE_QUALIFIED"
    assert created == ["K4_CURRENT_CLASS"]
    assert result.semantic_calls == 54
    assert result.input_token_requests == 108
    candidate = result.candidates[0]
    assert candidate.application_correct == 6
    assert candidate.formation_correct == 6
    assert candidate.p2_hard_admitted == 6
    assert candidate.neutral_control_mean == 0.20
    assert candidate.neutral_non_degenerate_arm_count == 2


def test_v2_transaction_adapter_swaps_only_runner_then_restores(monkeypatch) -> None:
    observed: list[object] = []

    def fake_main(argv):
        observed.append(legacy_tx.run_llama_cpp_shared_floor_calibration)
        return 17

    monkeypatch.setattr(legacy_tx, "main", fake_main)
    result = tx_v2.main(["--repo-root", "."])
    assert result == 17
    assert observed == [run_llama_cpp_shared_floor_calibration_v2]
    assert legacy_tx.run_llama_cpp_shared_floor_calibration is tx_v2.legacy_runner
    assert hasattr(legacy_tx, "_wait_until_listener_released")
    assert legacy_tx.CLEANUP_RELEASE_TIMEOUT_SECONDS == 5.0


def test_v2_wsl_adapter_targets_dedicated_transaction_and_restores(monkeypatch) -> None:
    observed: list[tuple[str, str]] = []

    def fake_main(argv):
        observed.append((legacy_wsl.INNER_TRANSACTION_MODULE, legacy_wsl.WALL_TIME_SCHEMA))
        return 19

    monkeypatch.setattr(legacy_wsl, "main", fake_main)
    result = wsl_v2.main(["--repo-root", "."])
    assert result == 19
    assert observed == [
        (
            "tools.v2_cognitive_ir_shared_floor_calibration_v2_llama_cpp_transaction",
            "relaylm2-cognitive-ir-shared-floor-calibration-wsl-wall-time-v2",
        )
    ]
    assert legacy_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    )
    assert legacy_wsl.WALL_TIME_SCHEMA == (
        "relaylm2-cognitive-ir-shared-floor-calibration-wsl-wall-time-v1"
    )
