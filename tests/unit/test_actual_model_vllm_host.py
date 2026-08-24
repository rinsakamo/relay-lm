from __future__ import annotations

import asyncio
import json
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_host as vllm_host
from relaylm.actual_model_evaluation import ActualModelCognitionPassRequests
from relaylm.actual_model_vllm_capacity import (
    VLLMCapacityFootprintObservation,
    VLLMRuntimeCapacityEvidence,
    vllm_capacity_pass_request_id,
    write_vllm_runtime_capacity_evidence,
)
from relaylm.actual_model_vllm_counter import VLLMServingTokenizerCounter
from relaylm.budget_enforcement import TokenCountMode
from relaylm.cognition_execution import CognitionReasoningMode
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.providers.vllm_reasoning_capability import VLLMReasoningCapabilityStatus


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "screenings"
    / "cogp5-vllm-screening-v1.json"
)
CURRENT_PLAN_PATH = REPO_ROOT / vllm_host.CANONICAL_VLLM_SCREENING_PLAN_PATH
REFERENCE_BASELINE_ROLE = "reference_baseline"
PASS2_REASONING_ESCALATION_ROLE = "pass2_reasoning_escalation"
PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-vllm-reasoning-v1.json"
)
GOOGLE_TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-google-vllm-v1.json"
)
GOOGLE_PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-google-vllm-reasoning-v1.json"
)
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)
SCENARIO_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "scenario_sets"
    / "foundation-v2.json"
)
SNAPSHOT_ROOT = Path("/tmp/relaylm-unsloth-w4a16-model")
GOOGLE_SNAPSHOT_ROOT = Path("/tmp/relaylm-google-gemma4-official-attest.CKxAGh")
CANONICAL_B_CAPACITY_EVIDENCE_ID = (
    "amcap-2e39f7fd7bf8d32b2bc2be4263d5a3ce08f079319e76e59b104f236cce2464be"
)
LEGACY_B_CAPACITY_EVIDENCE_ID = (
    "amcap-7bcbbb3b1c0432c8cf3707670b99f373ab0fad05da93645aec023f43a6e5959b"
)
CANONICAL_B_CAPACITY_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "capacity"
    / f"{CANONICAL_B_CAPACITY_EVIDENCE_ID}.json"
)


def _live_fetch(url: str, _: str | None) -> object:
    if url.endswith("/version"):
        return {"version": "0.27.1"}
    if url.endswith("/v1/models"):
        return {
            "object": "list",
            "data": [
                {
                    "id": "gemma-4-12B-it-qat-w4a16",
                    "object": "model",
                    "root": str(SNAPSHOT_ROOT),
                    "max_model_len": 1024,
                }
            ],
        }
    raise AssertionError(f"unexpected URL: {url}")


def _google_live_fetch(url: str, _: str | None) -> object:
    if url.endswith("/version"):
        return {"version": "0.26.1rc1.dev549+g70b84f0bc"}
    if url.endswith("/v1/models"):
        return {
            "object": "list",
            "data": [
                {
                    "id": "gemma-4-12B-it-qat-w4a16",
                    "object": "model",
                    "root": str(GOOGLE_SNAPSHOT_ROOT),
                    "max_model_len": 1616,
                }
            ],
        }
    raise AssertionError(f"unexpected Google URL: {url}")


def _verification(target):
    return vllm_host.ActualModelRepositorySnapshotVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        verified_file_count=len(target.files),
    )


def _write_capacity_evidence(
    tmp_path: Path,
    target,
    capability,
    *,
    condition_id: str,
    plan_path: Path = PLAN_PATH,
    drop_last: bool = False,
    model_runner: str = "v2",
) -> VLLMRuntimeCapacityEvidence:
    max_model_len = capability.backend_attestation.max_model_len
    assert max_model_len is not None
    counter = VLLMServingTokenizerCounter(
        base_url="http://127.0.0.1:8000/v1",
        target=target,
        reasoning_capability=capability,
        expected_max_model_len=max_model_len,
        post_json=lambda *_: {"count": 1, "max_model_len": max_model_len},
    )
    plan = vllm_host.load_vllm_screening_plan(plan_path)
    scenario_set = vllm_host.load_actual_model_scenario_set(SCENARIO_PATH)
    condition = plan.conditions[condition_id]
    if condition.pass_requests.mode == "single_pass":
        requests = (("single_pass", condition.pass_requests.single_request),)
        topology = "single_pass"
    else:
        requests = (
            ("pass1", condition.pass_requests.pass1),
            ("pass2", condition.pass_requests.pass2),
        )
        topology = "two_pass"

    footprints = []
    for scenario_id in plan.scenario_ids:
        definition = scenario_set.scenario(scenario_id)
        for turn_index in range(1, len(definition.scenario.turns) + 1):
            for pass_id, request in requests:
                assert request is not None
                footprints.append(
                    VLLMCapacityFootprintObservation(
                        condition_id=condition.condition_id,
                        topology=topology,
                        pass_id=pass_id,
                        scenario_id=scenario_id,
                        turn_index=turn_index,
                        pass_request_id=vllm_capacity_pass_request_id(request),
                        total_input_tokens=900,
                        required_input_framing_tokens=100,
                        count_mode=TokenCountMode.EXACT,
                    )
                )
    if drop_last:
        footprints.pop()

    evidence = VLLMRuntimeCapacityEvidence(
        relaylm_commit="a" * 40,
        target_id=target.target_id,
        target_revision=target.revision,
        tokenizer_identity=target.tokenizer_identity,
        chat_template_identity=target.chat_template_identity,
        backend_version=capability.backend_version,
        request_model=capability.request_model,
        observed_max_model_len=max_model_len,
        scenario_set_revision=scenario_set.revision,
        counter_identity=counter.evidence_identity,
        footprints=tuple(footprints),
        model_runner=model_runner,
    )
    write_vllm_runtime_capacity_evidence(evidence=evidence, artifact_root=tmp_path)
    return evidence


def test_screening_plan_freezes_only_three_serial_product_conditions() -> None:
    plan = vllm_host.load_vllm_screening_plan(PLAN_PATH)

    assert plan.screening_id == "cogp5-vllm-screening-v1"
    assert plan.target_id == "gemma-4-12b-it-qat-w4a16-vllm-v1"
    assert plan.effective_context_window == 1024
    assert plan.scenario_ids == (
        "response-persona-correction-v1",
        "continuity-lifecycle-v1",
    )
    assert tuple(plan.conditions) == ("A", "B", "C")

    condition_a = plan.conditions["A"]
    assert condition_a.cognition_execution.mode == "single_pass"
    assert condition_a.pass_requests.mode == "single_pass"
    assert condition_a.pass_requests.single_request is not None
    assert condition_a.pass_requests.single_request.reasoning_mode is CognitionReasoningMode.OFF

    condition_b = plan.conditions["B"]
    assert condition_b.cognition_execution.mode == "two_pass"
    assert condition_b.pass_requests.pass1.reasoning_mode is CognitionReasoningMode.OFF
    assert condition_b.pass_requests.pass2.reasoning_mode is CognitionReasoningMode.OFF

    condition_c = plan.conditions["C"]
    assert condition_c.pass_requests.pass1.reasoning_mode is CognitionReasoningMode.OFF
    assert condition_c.pass_requests.pass2.reasoning_mode is CognitionReasoningMode.BOUNDED
    assert condition_c.pass_requests.pass2.reasoning_budget == 16

    serialized = json.dumps(plan.to_mapping(), sort_keys=True)
    for excluded in ("low", "medium", "high", "64"):
        assert excluded not in serialized


def test_current_stage_r0_canonical_binding_uses_google_target_and_proof() -> None:
    current_plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    google_target = vllm_host.load_actual_model_repository_snapshot_target(
        GOOGLE_TARGET_PATH
    )
    google_proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    old_target = vllm_host.load_actual_model_repository_snapshot_target(TARGET_PATH)
    old_proof = vllm_host.load_vllm_reasoning_probe_proof(PROOF_PATH)

    assert vllm_host.CANONICAL_VLLM_TARGET_PATH == Path(
        "evaluation/actual_model/targets/"
        "gemma-4-12b-it-qat-w4a16-google-vllm-v1.json"
    )
    assert vllm_host.CANONICAL_VLLM_REASONING_PROOF_PATH == Path(
        "evaluation/actual_model/attestations/"
        "gemma-4-12b-it-qat-w4a16-google-vllm-reasoning-v1.json"
    )
    assert current_plan.target_id == google_target.target_id
    assert google_proof.target_id == google_target.target_id
    assert google_proof.target_revision == google_target.revision
    assert current_plan.capacity_evidence_id == CANONICAL_B_CAPACITY_EVIDENCE_ID
    assert old_target.target_id == "gemma-4-12b-it-qat-w4a16-vllm-v1"
    assert old_proof.target_id == old_target.target_id
    assert TARGET_PATH.is_file()
    assert PROOF_PATH.is_file()

    reference = current_plan.conditions[REFERENCE_BASELINE_ROLE]
    assert reference.cognition_execution.mode == "two_pass"
    assert reference.pass_requests.pass1.reasoning_mode is CognitionReasoningMode.OFF
    assert reference.pass_requests.pass2.reasoning_mode is CognitionReasoningMode.OFF


def test_google_target_rejects_old_reasoning_proof_fail_closed() -> None:
    google_target = vllm_host.load_actual_model_repository_snapshot_target(
        GOOGLE_TARGET_PATH
    )
    old_proof = vllm_host.load_vllm_reasoning_probe_proof(PROOF_PATH)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="does not match the frozen target",
    ):
        vllm_host.acquire_vllm_reasoning_capability(
            proof=old_proof,
            target=google_target,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            fetch_json=_live_fetch,
        )


def test_current_stage_r0_without_capacity_fails_before_external_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=None,
    )
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("capacity gate must precede external preparation work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="capacity.*evidence",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=current_plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
        )

    assert touched is False


def test_current_stage_r0_complete_google_b_capacity_is_bound_and_validated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_google_live_fetch,
    )
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id=REFERENCE_BASELINE_ROLE,
        plan_path=CURRENT_PLAN_PATH,
        model_runner="v2",
    )
    current_plan = replace(current_plan, capacity_evidence_id=evidence.evidence_id)

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        vllm_host,
        "verify_actual_model_repository_snapshot",
        lambda **_: _verification(target),
    )

    prepared = vllm_host.prepare_vllm_screening_condition(
        plan=current_plan,
        condition_id=REFERENCE_BASELINE_ROLE,
        proof_path=GOOGLE_PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=GOOGLE_SNAPSHOT_ROOT,
        relaylm_commit="b" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        model_runner="v2",
        fetch_json=_google_live_fetch,
        capacity_evidence_root=tmp_path,
    )
    try:
        assert prepared.screening_condition_id == REFERENCE_BASELINE_ROLE
        assert prepared.capacity_evidence.evidence_id == evidence.evidence_id
        assert prepared.capacity_evidence.model_runner == "v2"
        assert prepared.capacity_evidence.failed_capacity is None
        assert prepared.capacity_evidence.maximum_observed_input_tokens == 900
        assert prepared.capacity_evidence.observed_max_model_len == 1616
        assert prepared.condition.cognition_execution.mode == "two_pass"
        assert prepared.condition.pass_requests.pass1.reasoning_mode is CognitionReasoningMode.OFF
        assert prepared.condition.pass_requests.pass2.reasoning_mode is CognitionReasoningMode.OFF
    finally:
        asyncio.run(prepared.provider.aclose())


def test_current_stage_r0_canonical_v3_v2_capacity_passes_preparation_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        vllm_host,
        "verify_actual_model_repository_snapshot",
        lambda **_: _verification(target),
    )

    prepared = vllm_host.prepare_vllm_screening_condition(
        plan=current_plan,
        condition_id=REFERENCE_BASELINE_ROLE,
        proof_path=GOOGLE_PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=GOOGLE_SNAPSHOT_ROOT,
        relaylm_commit="b" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        model_runner="v2",
        fetch_json=_google_live_fetch,
    )
    try:
        assert prepared.capacity_evidence.evidence_id == current_plan.capacity_evidence_id
        assert prepared.capacity_evidence.format_version == 3
        assert prepared.capacity_evidence.model_runner == "v2"
        assert prepared.condition.cognition_execution.mode == "two_pass"
        assert prepared.condition.pass_requests.pass1.reasoning_mode is CognitionReasoningMode.OFF
        assert prepared.condition.pass_requests.pass2.reasoning_mode is CognitionReasoningMode.OFF
    finally:
        asyncio.run(prepared.provider.aclose())


def test_current_stage_r0_canonical_v3_rejects_expected_v1_before_external_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)

    monkeypatch.setattr(
        vllm_host,
        "_verify_clean_exact_repo",
        lambda **_: pytest.fail("runner mismatch must fail before repository work"),
    )

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="model_runner",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=current_plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v1",
        )


def test_current_stage_r0_rejects_unknown_capacity_id_before_external_work(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id="amcap-" + "f" * 64,
    )

    monkeypatch.setattr(
        vllm_host,
        "_verify_clean_exact_repo",
        lambda **_: pytest.fail("unknown capacity ID must fail before repository work"),
    )

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="capacity.*evidence",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=current_plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
        )


def test_current_stage_r0_rejects_legacy_capacity_for_v2_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=LEGACY_B_CAPACITY_EVIDENCE_ID,
    )

    monkeypatch.setattr(
        vllm_host,
        "_verify_clean_exact_repo",
        lambda **_: pytest.fail("runner identity must be checked before repository work"),
    )

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="model_runner",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=current_plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
        )


def test_current_stage_r0_rejects_omitted_expected_runner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    current_plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)

    monkeypatch.setattr(
        vllm_host,
        "_verify_clean_exact_repo",
        lambda **_: pytest.fail("runner identity must be checked before repository work"),
    )

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="model_runner",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=current_plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
        )


@pytest.mark.parametrize(
    ("artifact_runner", "expected_runner"),
    [("v1", "v2"), ("v2", "v1")],
)
def test_current_stage_r0_rejects_capacity_runner_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    artifact_runner: str,
    expected_runner: str,
) -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_google_live_fetch,
    )
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id=REFERENCE_BASELINE_ROLE,
        plan_path=CURRENT_PLAN_PATH,
        model_runner=artifact_runner,
    )
    plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=evidence.evidence_id,
    )
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="model_runner",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner=expected_runner,
            fetch_json=_google_live_fetch,
            capacity_evidence_root=tmp_path,
        )


def test_current_stage_r0_rejects_artifact_identity_mismatch_before_external_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw = json.loads(CANONICAL_B_CAPACITY_PATH.read_text(encoding="utf-8"))
    raw["evidence_id"] = "amcap-" + "0" * 64
    artifact_path = tmp_path / f"{CANONICAL_B_CAPACITY_EVIDENCE_ID}.json"
    artifact_path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    current_plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=CANONICAL_B_CAPACITY_EVIDENCE_ID,
    )
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("artifact identity failure must precede external work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="evidence_id",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=current_plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
            capacity_evidence_root=tmp_path,
        )

    assert touched is False


@pytest.mark.parametrize("mismatch", ("target_id", "target_revision"))
def test_current_stage_r0_rejects_mismatched_capacity_target_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mismatch: str,
) -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_google_live_fetch,
    )
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id=REFERENCE_BASELINE_ROLE,
        plan_path=CURRENT_PLAN_PATH,
    )
    if mismatch == "target_id":
        old_target = vllm_host.load_actual_model_repository_snapshot_target(TARGET_PATH)
        parameters = dict(evidence.counter_identity.parameters)
        parameters["target_id"] = old_target.target_id
        evidence = replace(
            evidence,
            target_id=old_target.target_id,
            counter_identity=replace(
                evidence.counter_identity,
                parameters=tuple(sorted(parameters.items())),
            ),
        )
    else:
        evidence = replace(evidence, target_revision="sha256:" + "f" * 64)
    write_vllm_runtime_capacity_evidence(evidence=evidence, artifact_root=tmp_path)
    plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=evidence.evidence_id,
    )
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="canonical frozen target",
    ):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
            fetch_json=_google_live_fetch,
            capacity_evidence_root=tmp_path,
        )


def test_reasoning_probe_proof_reconstructs_capability_against_live_backend() -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(PROOF_PATH)

    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_live_fetch,
    )

    assert capability.backend_version == "0.27.1"
    assert capability.request_model == "gemma-4-12B-it-qat-w4a16"
    assert capability.backend_attestation.model_root == str(SNAPSHOT_ROOT)
    assert capability.backend_attestation.max_model_len == 1024
    assert capability.reasoning_parser == "gemma4"
    assert capability.template_thinking_control == "enable_thinking"
    assert capability.reasoning_off.status is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    assert capability.reasoning_bounded.status is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    assert dict(capability.reasoning_bounded.probe_wire) == {"thinking_token_budget": 16}


def test_google_reasoning_probe_proof_is_distinct_and_binds_the_google_target() -> None:
    old_proof = vllm_host.load_vllm_reasoning_probe_proof(PROOF_PATH)
    google_target = vllm_host.load_actual_model_repository_snapshot_target(
        GOOGLE_TARGET_PATH
    )
    google_proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)

    assert old_proof.proof_id == "gemma-4-12b-it-qat-w4a16-vllm-reasoning-v1"
    assert google_proof.proof_id == (
        "gemma-4-12b-it-qat-w4a16-google-vllm-reasoning-v1"
    )
    assert google_proof.proof_id != old_proof.proof_id
    assert google_proof.source_issue == 1545
    assert google_proof.source_comment_id == 5357427205
    assert google_proof.target_id == google_target.target_id
    assert google_proof.target_revision == google_target.revision
    assert google_proof.backend_version == "0.26.1rc1.dev549+g70b84f0bc"
    assert google_proof.request_model == "gemma-4-12B-it-qat-w4a16"
    assert google_proof.reasoning_parser == "gemma4"
    assert google_proof.template_thinking_control == "enable_thinking"
    assert dict(google_proof.off_probe.wire_controls.to_mapping()) == {
        "reasoning_effort": "none"
    }
    assert google_proof.off_probe.accepted is True
    assert google_proof.off_probe.effect_proven is True
    assert google_proof.off_probe.repeatable is True
    assert google_proof.off_probe.activation_applied is False
    assert google_proof.off_probe.template_kwargs == ()
    assert google_proof.off_probe.ambiguous is False
    assert dict(google_proof.bounded_probe.wire_controls.to_mapping()) == {
        "thinking_token_budget": 16
    }
    assert google_proof.bounded_probe.accepted is True
    assert google_proof.bounded_probe.effect_proven is True
    assert google_proof.bounded_probe.repeatable is True
    assert google_proof.bounded_probe.activation_applied is True
    assert google_proof.bounded_probe.template_kwargs == (("enable_thinking", True),)
    assert google_proof.bounded_probe.ambiguous is False

    def fetch_json(url: str, _: str | None) -> object:
        if url.endswith("/version"):
            return {"version": google_proof.backend_version}
        if url.endswith("/v1/models"):
            return {
                "object": "list",
                "data": [
                    {
                        "id": google_proof.request_model,
                        "object": "model",
                        "root": "/tmp/relaylm-google-gemma4-official-attest.CKxAGh",
                        "max_model_len": 1616,
                    }
                ],
            }
        raise AssertionError(f"unexpected Google attestation URL: {url}")

    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=google_proof,
        target=google_target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=fetch_json,
    )
    assert capability.backend_version == google_proof.backend_version
    assert capability.request_model == google_proof.request_model
    assert capability.target_id == google_target.target_id
    assert capability.target_revision == google_target.revision
    assert (
        capability.reasoning_off.status
        is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    )
    assert (
        capability.reasoning_bounded.status
        is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    )


def test_reasoning_probe_proof_fails_closed_on_live_version_drift() -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(PROOF_PATH)

    def drifted_fetch(url: str, api_key: str | None) -> object:
        value = _live_fetch(url, api_key)
        if url.endswith("/version"):
            return {"version": "0.28.0"}
        return value

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="version"):
        vllm_host.acquire_vllm_reasoning_capability(
            proof=proof,
            target=target,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            fetch_json=drifted_fetch,
        )


@pytest.mark.parametrize(
    ("condition_id", "provider_type", "mode"),
    [
        (REFERENCE_BASELINE_ROLE, OpenAICompatibleTwoPassProvider, "two_pass"),
        (PASS2_REASONING_ESCALATION_ROLE, OpenAICompatibleTwoPassProvider, "two_pass"),
    ],
)
def test_prepare_screening_condition_uses_common_provider_and_binding_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition_id: str,
    provider_type: type[OpenAICompatibleProvider],
    mode: str,
) -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_google_live_fetch,
    )
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id=condition_id,
        plan_path=CURRENT_PLAN_PATH,
    )
    plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=evidence.evidence_id,
    )
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        vllm_host,
        "verify_actual_model_repository_snapshot",
        lambda **_: _verification(target),
    )

    prepared = vllm_host.prepare_vllm_screening_condition(
        plan=plan,
        condition_id=condition_id,
        proof_path=GOOGLE_PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=GOOGLE_SNAPSHOT_ROOT,
        relaylm_commit="b" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        model_runner="v2",
        fetch_json=_google_live_fetch,
        capacity_evidence_root=tmp_path,
    )
    try:
        assert isinstance(prepared.provider, provider_type)
        assert prepared.condition.cognition_execution.mode == mode
        assert prepared.capacity_evidence == evidence
        assert isinstance(
            prepared.manifest.cognition_pass_requests,
            ActualModelCognitionPassRequests,
        )
        assert prepared.manifest.cognition_pass_requests == prepared.condition.pass_requests
        assert prepared.manifest.provider_identity == vllm_host.vllm_manifest_provider_identity(
            prepared.reasoning_capability
        )
        assert prepared.binding.manifest == prepared.manifest
        assert prepared.binding.reasoning_capability == prepared.reasoning_capability
        assert prepared.scenario_ids == plan.scenario_ids
    finally:
        asyncio.run(prepared.provider.aclose())


def test_prepare_rejects_incomplete_capacity_coverage_before_provider_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_google_live_fetch,
    )
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id=REFERENCE_BASELINE_ROLE,
        plan_path=CURRENT_PLAN_PATH,
        drop_last=True,
    )
    plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=evidence.evidence_id,
    )
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        vllm_host,
        "verify_actual_model_repository_snapshot",
        lambda **_: _verification(target),
    )

    def forbidden_provider(*args, **kwargs):
        raise AssertionError("incomplete capacity coverage reached provider construction")

    monkeypatch.setattr(vllm_host, "OpenAICompatibleTwoPassProvider", forbidden_provider)

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="coverage"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
            fetch_json=_google_live_fetch,
            capacity_evidence_root=tmp_path,
        )


def test_prepare_condition_rejects_unknown_screening_condition_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="condition"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="D",
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            fetch_json=_live_fetch,
        )
