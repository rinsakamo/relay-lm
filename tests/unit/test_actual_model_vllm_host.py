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
from relaylm.cognition_execution import (
    CognitionReasoningMode,
    CognitionStructuredOutputMode,
)
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
GOOGLE_TARGET_PATH = REPO_ROOT / vllm_host.CANONICAL_VLLM_TARGET_PATH
GOOGLE_PROOF_PATH = REPO_ROOT / vllm_host.CANONICAL_VLLM_REASONING_PROOF_PATH
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-qat-w4a16-vllm-v1.json"
)
SCENARIO_PATH = REPO_ROOT / vllm_host.CANONICAL_SCENARIO_SET_PATH
SNAPSHOT_ROOT = Path("/tmp/relaylm-unsloth-w4a16-model")
GOOGLE_SNAPSHOT_ROOT = Path("/tmp/relaylm-google-gemma4-official-attest.CKxAGh")


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


def _google_capability():
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_google_live_fetch,
    )
    return target, capability


def _write_capacity_evidence(
    tmp_path: Path,
    target,
    capability,
    *,
    condition_id: str,
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
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    scenario_set = vllm_host.load_actual_model_scenario_set(SCENARIO_PATH)
    condition = plan.conditions[condition_id]
    requests = (
        ("pass1", condition.pass_requests.pass1),
        ("pass2", condition.pass_requests.pass2),
    )

    footprints: list[VLLMCapacityFootprintObservation] = []
    for scenario_id in plan.scenario_ids:
        definition = scenario_set.scenario(scenario_id)
        for turn_index in range(1, len(definition.scenario.turns) + 1):
            for pass_id, request in requests:
                assert request is not None
                footprints.append(
                    VLLMCapacityFootprintObservation(
                        condition_id=condition.condition_id,
                        topology="two_pass",
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
        relaylm_commit="b" * 40,
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


def _bind_current_capacity(
    tmp_path: Path,
    *,
    condition_id: str = REFERENCE_BASELINE_ROLE,
    drop_last: bool = False,
    model_runner: str = "v2",
):
    target, capability = _google_capability()
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id=condition_id,
        drop_last=drop_last,
        model_runner=model_runner,
    )
    plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id=evidence.evidence_id,
    )
    return plan, target, evidence


def _prepare(
    *,
    plan,
    condition_id: str,
    capacity_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    model_runner: str | None = "v2",
):
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        vllm_host,
        "verify_actual_model_repository_snapshot",
        lambda **_: _verification(target),
    )
    return vllm_host.prepare_vllm_screening_condition(
        plan=plan,
        condition_id=condition_id,
        proof_path=GOOGLE_PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=GOOGLE_SNAPSHOT_ROOT,
        relaylm_commit="b" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        model_runner=model_runner,
        fetch_json=_google_live_fetch,
        capacity_evidence_root=capacity_root,
    )


def test_historical_screening_plan_keeps_original_three_conditions() -> None:
    plan = vllm_host.load_vllm_screening_plan(PLAN_PATH)

    assert plan.screening_id == "cogp5-vllm-screening-v1"
    assert plan.target_id == "gemma-4-12b-it-qat-w4a16-vllm-v1"
    assert plan.effective_context_window == 1024
    assert plan.capacity_evidence_id is None
    assert tuple(plan.conditions) == ("A", "B", "C")
    assert plan.conditions["A"].cognition_execution.mode == "single_pass"
    assert plan.conditions["B"].pass_requests.pass2.reasoning_mode is CognitionReasoningMode.OFF
    assert plan.conditions["C"].pass_requests.pass2.reasoning_mode is CognitionReasoningMode.BOUNDED
    assert plan.conditions["C"].pass_requests.pass2.reasoning_budget == 16


def test_current_stage_r0_binding_uses_google_target_native_pass2_and_no_stale_capacity() -> None:
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)

    assert plan.target_id == target.target_id == proof.target_id
    assert proof.target_revision == target.revision
    assert plan.capacity_evidence_id is None
    reference = plan.conditions[REFERENCE_BASELINE_ROLE]
    assert reference.cognition_execution.mode == "two_pass"
    assert reference.pass_requests.pass1.reasoning_mode is CognitionReasoningMode.OFF
    assert reference.pass_requests.pass2.reasoning_mode is CognitionReasoningMode.OFF
    assert reference.pass_requests.pass1.structured_output_mode is None
    assert (
        reference.pass_requests.pass2.structured_output_mode
        is CognitionStructuredOutputMode.NATIVE
    )


def test_google_target_rejects_old_reasoning_proof_fail_closed() -> None:
    google_target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
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
    plan = vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH)
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("capacity gate must precede external preparation work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="capacity.*evidence"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root="/tmp/unused",
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            model_runner="v2",
        )

    assert touched is False


def test_current_stage_r0_fresh_capacity_is_bound_and_validated(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, evidence = _bind_current_capacity(tmp_path)

    prepared = _prepare(
        plan=plan,
        condition_id=REFERENCE_BASELINE_ROLE,
        capacity_root=tmp_path,
        monkeypatch=monkeypatch,
    )
    try:
        assert prepared.capacity_evidence == evidence
        assert prepared.capacity_evidence.model_runner == "v2"
        assert prepared.capacity_evidence.failed_capacity is None
        assert prepared.capacity_evidence.maximum_observed_input_tokens == 900
        assert prepared.capacity_evidence.observed_max_model_len == 1616
        assert (
            prepared.condition.pass_requests.pass2.structured_output_mode
            is CognitionStructuredOutputMode.NATIVE
        )
    finally:
        asyncio.run(prepared.provider.aclose())


def test_current_stage_r0_rejects_unknown_capacity_id_before_external_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = replace(
        vllm_host.load_vllm_screening_plan(CURRENT_PLAN_PATH),
        capacity_evidence_id="amcap-" + "f" * 64,
    )
    monkeypatch.setattr(
        vllm_host,
        "_verify_clean_exact_repo",
        lambda **_: pytest.fail("unknown capacity ID must fail before repository work"),
    )

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="capacity.*evidence"):
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
            capacity_evidence_root=tmp_path,
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
    plan, _, _ = _bind_current_capacity(tmp_path, model_runner=artifact_runner)
    monkeypatch.setattr(
        vllm_host,
        "_verify_clean_exact_repo",
        lambda **_: pytest.fail("runner mismatch must fail before repository work"),
    )

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="model_runner"):
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


def test_current_stage_r0_rejects_omitted_expected_runner(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, _ = _bind_current_capacity(tmp_path)
    monkeypatch.setattr(
        vllm_host,
        "_verify_clean_exact_repo",
        lambda **_: pytest.fail("runner identity must be checked before repository work"),
    )

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="model_runner"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id=REFERENCE_BASELINE_ROLE,
            proof_path=GOOGLE_PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=GOOGLE_SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            capacity_evidence_root=tmp_path,
        )


def test_current_stage_r0_rejects_artifact_identity_mismatch_before_external_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, _, evidence = _bind_current_capacity(tmp_path)
    artifact_path = tmp_path / f"{evidence.evidence_id}.json"
    raw = json.loads(artifact_path.read_text(encoding="utf-8"))
    raw["evidence_id"] = "amcap-" + "0" * 64
    artifact_path.write_text(
        json.dumps(raw, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    touched = False

    def forbidden(*args, **kwargs):
        nonlocal touched
        touched = True
        raise AssertionError("artifact identity failure must precede external work")

    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", forbidden)
    monkeypatch.setattr(vllm_host, "verify_actual_model_repository_snapshot", forbidden)
    monkeypatch.setattr(vllm_host, "acquire_vllm_reasoning_capability", forbidden)

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="evidence_id"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
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
    plan, _, evidence = _bind_current_capacity(tmp_path)
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
    plan = replace(plan, capacity_evidence_id=evidence.evidence_id)
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
    assert (
        capability.reasoning_off.status
        is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    )
    assert (
        capability.reasoning_bounded.status
        is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    )


def test_google_reasoning_probe_proof_binds_current_target() -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(GOOGLE_TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(GOOGLE_PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_google_live_fetch,
    )

    assert proof.source_issue == 1545
    assert proof.target_id == target.target_id
    assert proof.target_revision == target.revision
    assert capability.target_id == target.target_id
    assert capability.target_revision == target.revision
    assert capability.reasoning_off.status is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED
    assert capability.reasoning_bounded.status is VLLMReasoningCapabilityStatus.SEMANTICALLY_ATTESTED


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
    plan, _, evidence = _bind_current_capacity(tmp_path, condition_id=condition_id)

    prepared = _prepare(
        plan=plan,
        condition_id=condition_id,
        capacity_root=tmp_path,
        monkeypatch=monkeypatch,
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
        assert prepared.binding.manifest == prepared.manifest
        assert prepared.binding.reasoning_capability == prepared.reasoning_capability
        assert prepared.scenario_ids == plan.scenario_ids
    finally:
        asyncio.run(prepared.provider.aclose())


def test_prepare_rejects_incomplete_capacity_coverage_before_provider_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, target, _ = _bind_current_capacity(tmp_path, drop_last=True)
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
