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
PROOF_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "attestations"
    / "gemma-4-12b-it-qat-w4a16-vllm-reasoning-v1.json"
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
    drop_last: bool = False,
) -> VLLMRuntimeCapacityEvidence:
    counter = VLLMServingTokenizerCounter(
        base_url="http://127.0.0.1:8000/v1",
        target=target,
        reasoning_capability=capability,
        expected_max_model_len=1024,
        post_json=lambda *_: {"count": 1, "max_model_len": 1024},
    )
    plan = vllm_host.load_vllm_screening_plan(PLAN_PATH)
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
        observed_max_model_len=1024,
        scenario_set_revision=scenario_set.revision,
        counter_identity=counter.evidence_identity,
        footprints=tuple(footprints),
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
        ("A", OpenAICompatibleProvider, "single_pass"),
        ("B", OpenAICompatibleTwoPassProvider, "two_pass"),
        ("C", OpenAICompatibleTwoPassProvider, "two_pass"),
    ],
)
def test_prepare_screening_condition_uses_common_provider_and_binding_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    condition_id: str,
    provider_type: type[OpenAICompatibleProvider],
    mode: str,
) -> None:
    target = vllm_host.load_actual_model_repository_snapshot_target(TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_live_fetch,
    )
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id=condition_id,
    )
    plan = replace(
        vllm_host.load_vllm_screening_plan(PLAN_PATH),
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
        proof_path=PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=SNAPSHOT_ROOT,
        relaylm_commit="b" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_live_fetch,
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
    target = vllm_host.load_actual_model_repository_snapshot_target(TARGET_PATH)
    proof = vllm_host.load_vllm_reasoning_probe_proof(PROOF_PATH)
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        fetch_json=_live_fetch,
    )
    evidence = _write_capacity_evidence(
        tmp_path,
        target,
        capability,
        condition_id="C",
        drop_last=True,
    )
    plan = replace(
        vllm_host.load_vllm_screening_plan(PLAN_PATH),
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
            condition_id="C",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            fetch_json=_live_fetch,
            capacity_evidence_root=tmp_path,
        )


def test_prepare_condition_rejects_unknown_screening_condition_before_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan = vllm_host.load_vllm_screening_plan(PLAN_PATH)
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)

    with pytest.raises(vllm_host.ActualModelVLLMHostError, match="condition"):
        vllm_host.prepare_vllm_screening_condition(
            plan=plan,
            condition_id="D",
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=SNAPSHOT_ROOT,
            relaylm_commit="b" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
            fetch_json=_live_fetch,
        )
