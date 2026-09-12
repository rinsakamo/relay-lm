from __future__ import annotations

import json

from relaylm.v2_cognitive_ir_attack_observability_calibration import (
    ATTACK_OBS_CALLS_PER_CANDIDATE,
    ATTACK_OBS_MAX_INPUT_TOKEN_REQUESTS,
    ATTACK_OBS_MAX_SEMANTIC_CALLS,
    ATTACK_OBS_SEEDS,
    ATTACK_OBS_VISIBILITIES,
    D1_PREREGISTERED_SEEDS,
    attack_observability_call_plan,
    attack_probe_step_index,
    build_attack_target_only_messages,
    derive_attack_obs_seed,
    generate_attack_observability_family,
    run_attack_observability_calibration,
    validate_attack_observability_preregistration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
import tools.v2_cognitive_ir_attack_observability_calibration_llama_cpp_transaction as d2_tx
import tools.v2_cognitive_ir_attack_observability_calibration_llama_cpp_wsl as d2_wsl
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as legacy_tx
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy_wsl
from tools.v2_cognitive_ir_attack_observability_calibration_llama_cpp import (
    run_llama_cpp_attack_observability_calibration,
)


def test_attack_observability_identity_and_collision_fence() -> None:
    validate_attack_observability_preregistration()
    derived = {
        regime: tuple(derive_attack_obs_seed(regime, index) for index in range(6))
        for regime in ("null", "mismatch", "shift")
    }
    assert derived == dict(ATTACK_OBS_SEEDS)
    flat = {seed for seeds in ATTACK_OBS_SEEDS.values() for seed in seeds}
    assert len(flat) == 18
    assert flat.isdisjoint(D1_PREREGISTERED_SEEDS)
    assert ATTACK_OBS_VISIBILITIES == (1, 2, 3)
    assert ATTACK_OBS_CALLS_PER_CANDIDATE == 18
    assert ATTACK_OBS_MAX_SEMANTIC_CALLS == 54
    assert ATTACK_OBS_MAX_INPUT_TOKEN_REQUESTS == 108


def test_attack_families_keep_k3_and_regime_semantics() -> None:
    for regime in ("null", "mismatch", "shift"):
        for index in range(6):
            family = generate_attack_observability_family(regime, index)
            assert sum(value != 0 for value in family.source_rule.offsets) == 3
            assert all(
                sum(value != 0 for value in rule.offsets) == 3
                for rule in family.target_rules
            )
            if regime == "null":
                assert all(rule != family.source_rule for rule in family.target_rules)
            elif regime == "mismatch":
                target = family.target_rules[0]
                assert {
                    i for i, value in enumerate(target.offsets) if value != 0
                } == {
                    i for i, value in enumerate(family.source_rule.offsets) if value != 0
                }
                assert target != family.source_rule
            else:
                assert family.target_rules[:2] == (
                    family.source_rule,
                    family.source_rule,
                )
                assert family.target_rules[2] != family.source_rule
                assert family.target_rules[2:] == (
                    family.target_rules[2],
                    family.target_rules[2],
                )


def test_visibility_changes_only_visible_target_evidence() -> None:
    family = generate_attack_observability_family("shift", 0)
    queries = []
    for visibility in ATTACK_OBS_VISIBILITIES:
        messages = build_attack_target_only_messages(family, visibility)
        payload = json.loads(messages[1]["content"])
        assert len(payload["examples"]) == visibility
        assert "source" not in payload
        assert "P4" not in messages[1]["content"]
        assert "P6" not in messages[1]["content"]
        assert "memory" not in messages[1]["content"].lower()
        assert "structure" not in messages[1]["content"].lower()
        queries.append(tuple(payload["query"]))
    assert len(set(queries)) == 1
    assert attack_probe_step_index("shift") == 2


def test_call_plan_is_treatment_blind_and_exact() -> None:
    for visibility in ATTACK_OBS_VISIBILITIES:
        plan = attack_observability_call_plan(visibility)
        assert len(plan) == 18
        assert sum(":null:" in question for question in plan) == 6
        assert sum(":mismatch:" in question for question in plan) == 6
        assert sum(":shift:" in question for question in plan) == 6
        assert all(question.endswith(":target-only") for question in plan)
        assert not any(
            token in question
            for question in plan
            for token in ("P0_", "P1_", "P2_", "P3_", "P4_", "P5_", "P6_", "form-")
        )


class _FakeClient:
    def __init__(self, visibility: int, call_plan: tuple[str, ...]) -> None:
        self.visibility = visibility
        self.call_plan = call_plan
        self.index = 0

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        del messages, output_kind
        assert question_id == self.call_plan[self.index]
        self.index += 1
        _, regime, index_text, _, _ = question_id.split(":")
        family = generate_attack_observability_family(regime, int(index_text))
        expected = list(family.expected_output(attack_probe_step_index(regime)))
        threshold = {1: 4, 2: 5, 3: 6}[self.visibility]
        if int(index_text) < threshold:
            content = json.dumps(expected)
        else:
            wrong = list(expected)
            wrong[0] = (wrong[0] + 1) % family.modulus
            content = json.dumps(wrong)
        return ExperimentCompletion(
            content=content,
            input_tokens=11,
            output_tokens=7,
            response_id=f"fake-{self.visibility}-{self.index}",
        )

    def require_complete_plan(self) -> None:
        assert self.index == len(self.call_plan)


def test_calibration_uses_first_passing_visibility_and_no_extension() -> None:
    created: list[int] = []

    def factory(visibility: int, call_plan: tuple[str, ...]) -> _FakeClient:
        created.append(visibility)
        return _FakeClient(visibility, call_plan)

    result = run_attack_observability_calibration(factory)
    assert result.classification == "ATTACK_OBSERVABILITY_QUALIFIED"
    assert result.selected_visibility == 2
    assert created == [1, 2]
    assert result.semantic_calls == 36
    assert result.input_token_requests == 72
    assert [candidate.correct_by_regime for candidate in result.candidates] == [
        {"null": 4, "mismatch": 4, "shift": 4},
        {"null": 5, "mismatch": 5, "shift": 5},
    ]


def test_transaction_adapter_binds_d2_constants_then_restores(monkeypatch) -> None:
    observed: list[tuple[object, object, object, object, object]] = []

    def fake_main(argv):
        del argv
        observed.append(
            (
                legacy_tx.run_llama_cpp_shared_floor_calibration,
                legacy_tx.SHARED_FLOOR_CLAIM,
                legacy_tx.SHARED_FLOOR_CITABLE,
                legacy_tx.SHARED_FLOOR_MAX_SEMANTIC_CALLS,
                legacy_tx.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
            )
        )
        return 17

    original = (
        legacy_tx.run_llama_cpp_shared_floor_calibration,
        legacy_tx.SHARED_FLOOR_CLAIM,
        legacy_tx.SHARED_FLOOR_CITABLE,
        legacy_tx.SHARED_FLOOR_MAX_SEMANTIC_CALLS,
        legacy_tx.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    )
    monkeypatch.setattr(legacy_tx, "main", fake_main)
    assert d2_tx.main(["--repo-root", "."]) == 17
    assert observed == [
        (
            run_llama_cpp_attack_observability_calibration,
            "NON_CITABLE_ATTACK_OBSERVABILITY_CALIBRATION",
            False,
            54,
            108,
        )
    ]
    assert (
        legacy_tx.run_llama_cpp_shared_floor_calibration,
        legacy_tx.SHARED_FLOOR_CLAIM,
        legacy_tx.SHARED_FLOOR_CITABLE,
        legacy_tx.SHARED_FLOOR_MAX_SEMANTIC_CALLS,
        legacy_tx.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    ) == original


def test_wsl_adapter_targets_d2_transaction_and_restores(monkeypatch) -> None:
    observed: list[tuple[str, str]] = []

    def fake_main(argv):
        del argv
        observed.append((legacy_wsl.INNER_TRANSACTION_MODULE, legacy_wsl.WALL_TIME_SCHEMA))
        return 19

    monkeypatch.setattr(legacy_wsl, "main", fake_main)
    assert d2_wsl.main(["--repo-root", "."]) == 19
    assert observed == [
        (
            "tools.v2_cognitive_ir_attack_observability_calibration_llama_cpp_transaction",
            "relaylm2-cognitive-ir-r6d-attack-observability-wsl-wall-time-v1",
        )
    ]
    assert legacy_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    )
