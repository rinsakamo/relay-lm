from __future__ import annotations

import json

from relaylm.v2_cognitive_ir_current_law_certificate_qualification import (
    G1_INPUT_TOKEN_REQUESTS,
    G1_SEEDS,
    G1_SEMANTIC_CALLS,
    G1_TARGET_EXAMPLE_INDEX,
    build_g1_messages,
    derive_current_law_certificate,
    derive_g1_seed,
    g1_call_plan,
    g1_probe_step_index,
    generate_g1_family,
    run_current_law_certificate_qualification,
    validate_g1_preregistration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion
import tools.v2_cognitive_ir_current_law_certificate_qualification_llama_cpp_transaction as g1_tx
import tools.v2_cognitive_ir_current_law_certificate_qualification_llama_cpp_wsl as g1_wsl
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction as legacy_tx
import tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl as legacy_wsl
from tools.v2_cognitive_ir_current_law_certificate_qualification_llama_cpp import (
    run_llama_cpp_current_law_certificate_qualification,
)


def test_g1_identity_and_call_ledger() -> None:
    validate_g1_preregistration()
    derived = {
        regime: tuple(derive_g1_seed(regime, index) for index in range(6))
        for regime in ("null", "mismatch", "shift")
    }
    assert derived == dict(G1_SEEDS)
    flat = {seed for seeds in G1_SEEDS.values() for seed in seeds}
    assert len(flat) == 18
    assert G1_SEMANTIC_CALLS == 18
    assert G1_INPUT_TOKEN_REQUESTS == 36
    assert G1_TARGET_EXAMPLE_INDEX == 0


def test_g1_certificate_reconstructs_current_rule_for_all_families() -> None:
    for regime in ("null", "mismatch", "shift"):
        for index in range(6):
            family = generate_g1_family(regime, index)
            certificate = derive_current_law_certificate(family)
            step_index = g1_probe_step_index(regime)
            assert certificate.target_step_index == step_index
            assert certificate.target_example_index == 0
            assert certificate.permutation == (0, 1, 2, 3)
            assert certificate.modulus == 10
            assert certificate.offsets == family.target_rules[step_index].offsets
            assert sum(value != 0 for value in family.source_rule.offsets) == 3
            assert all(
                sum(value != 0 for value in rule.offsets) == 3
                for rule in family.target_rules
            )


def test_g1_model_payload_is_certificate_only_and_source_blind() -> None:
    family = generate_g1_family("shift", 0)
    certificate = derive_current_law_certificate(family)
    messages = build_g1_messages(family)
    payload = json.loads(messages[1]["content"])

    assert set(payload) == {"instruction", "current_law_certificate", "query"}
    assert payload["current_law_certificate"] == {
        "modulus": certificate.modulus,
        "offsets": list(certificate.offsets),
        "permutation": list(certificate.permutation),
    }
    assert tuple(payload["query"]) == family.target_steps[2].query
    lower = messages[1]["content"].lower()
    for forbidden in (
        "source",
        "examples",
        "p0_",
        "p1_",
        "p2_",
        "p3_",
        "p4_",
        "p5_",
        "p6_",
        "memory",
        "structure",
    ):
        assert forbidden not in lower


def test_g1_call_plan_is_fixed_and_treatment_blind() -> None:
    plan = g1_call_plan()
    assert len(plan) == 18
    assert sum(":null:" in question for question in plan) == 6
    assert sum(":mismatch:" in question for question in plan) == 6
    assert sum(":shift:" in question for question in plan) == 6
    assert all(question.startswith("G1:") for question in plan)
    assert all(question.endswith(":certificate-only") for question in plan)


class _FakeClient:
    def __init__(self, *, mismatch_failures: int = 1) -> None:
        self.call_plan = g1_call_plan()
        self.index = 0
        self.mismatch_failures = mismatch_failures

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
        index = int(index_text)
        family = generate_g1_family(regime, index)
        expected = list(family.expected_output(g1_probe_step_index(regime)))
        should_fail = regime == "mismatch" and index >= 6 - self.mismatch_failures
        if should_fail:
            expected[0] = (expected[0] + 1) % family.modulus
        return ExperimentCompletion(
            content=json.dumps(expected),
            input_tokens=11,
            output_tokens=7,
            response_id=f"fake-{self.index}",
        )

    def require_complete_plan(self) -> None:
        assert self.index == len(self.call_plan)


def test_g1_qualification_requires_five_of_six_in_every_regime() -> None:
    qualified = run_current_law_certificate_qualification(
        _FakeClient(mismatch_failures=1)
    )
    assert qualified.classification == "CURRENT_LAW_CERTIFICATE_USABILITY_QUALIFIED"
    assert qualified.correct_by_regime == {"null": 6, "mismatch": 5, "shift": 6}
    assert qualified.semantic_calls == 18
    assert qualified.input_token_requests == 36

    failed = run_current_law_certificate_qualification(
        _FakeClient(mismatch_failures=2)
    )
    assert failed.classification == "CURRENT_LAW_CERTIFICATE_USABILITY_FAILED"
    assert failed.correct_by_regime == {"null": 6, "mismatch": 4, "shift": 6}


def test_g1_transaction_adapter_binds_constants_then_restores(monkeypatch) -> None:
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
    assert g1_tx.main(["--repo-root", "."]) == 17
    assert observed == [
        (
            run_llama_cpp_current_law_certificate_qualification,
            "NON_CITABLE_CURRENT_LAW_CERTIFICATE_USABILITY_QUALIFICATION",
            False,
            18,
            36,
        )
    ]
    assert (
        legacy_tx.run_llama_cpp_shared_floor_calibration,
        legacy_tx.SHARED_FLOOR_CLAIM,
        legacy_tx.SHARED_FLOOR_CITABLE,
        legacy_tx.SHARED_FLOOR_MAX_SEMANTIC_CALLS,
        legacy_tx.SHARED_FLOOR_MAX_INPUT_TOKEN_REQUESTS,
    ) == original


def test_g1_wsl_adapter_targets_transaction_and_restores(monkeypatch) -> None:
    observed: list[tuple[str, str]] = []

    def fake_main(argv):
        del argv
        observed.append((legacy_wsl.INNER_TRANSACTION_MODULE, legacy_wsl.WALL_TIME_SCHEMA))
        return 19

    monkeypatch.setattr(legacy_wsl, "main", fake_main)
    assert g1_wsl.main(["--repo-root", "."]) == 19
    assert observed == [
        (
            "tools.v2_cognitive_ir_current_law_certificate_qualification_llama_cpp_transaction",
            "relaylm2-cognitive-ir-r6d-current-law-certificate-usability-wsl-wall-time-v1",
        )
    ]
    assert legacy_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_transaction"
    )
