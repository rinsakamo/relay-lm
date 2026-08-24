from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

import relaylm.actual_model_vllm_capacity_acquisition as acquisition
import relaylm.actual_model_vllm_host as vllm_host
from relaylm.actual_model_vllm_capacity import (
    VLLMRuntimeCapacityEvidenceError,
    load_vllm_runtime_capacity_evidence,
    validate_capacity_coverage,
)
from relaylm.cognitive import CognitiveInput
from relaylm.cognition_execution import (
    CognitionConversationOutput,
    CognitionExtractionInput,
    CognitionExtractionOutput,
)
from relaylm.events import Event
from relaylm.identity import Identity
from relaylm.state import STATE_CLASS_DEFINITIONS


REPO_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = REPO_ROOT / vllm_host.CANONICAL_VLLM_SCREENING_PLAN_PATH
PROOF_PATH = (
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
    / "gemma-4-12b-it-qat-w4a16-google-vllm-v1.json"
)
SNAPSHOT_ROOT = Path("/tmp/relaylm-google-gemma4-official-attest.CKxAGh")
LIVE_MAX_MODEL_LEN = 1536
CURRENT_REFERENCE_ROLE = "reference_baseline"


def _live_fetch(url: str, _: str | None) -> object:
    if url.endswith("/version"):
        return {"version": "0.26.1rc1.dev549+g70b84f0bc"}
    if url.endswith("/v1/models"):
        return {
            "object": "list",
            "data": [
                {
                    "id": "gemma-4-12B-it-qat-w4a16",
                    "object": "model",
                    "root": str(SNAPSHOT_ROOT),
                    "max_model_len": LIVE_MAX_MODEL_LEN,
                }
            ],
        }
    raise AssertionError(f"unexpected URL: {url}")


def _tokenize(_: str, payload, __: str | None) -> object:
    messages = payload["messages"]
    framing = all(message["content"] == "" for message in messages)
    return {
        "count": 80 if framing else 700,
        "max_model_len": LIVE_MAX_MODEL_LEN,
    }


def _verification(target):
    return vllm_host.ActualModelRepositorySnapshotVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        verified_file_count=len(target.files),
    )


def _input() -> CognitiveInput:
    return CognitiveInput(
        identity=Identity("# ReLM\nBe kind."),
        state_classes=STATE_CLASS_DEFINITIONS,
        state=(),
        context=(),
        input=Event.create(
            type="message",
            actor="user",
            payload={"content": "hello"},
            event_id="evt-now",
            timestamp="2026-08-21T00:00:00+00:00",
        ),
    )


class _SuccessfulTwoPassDelegate:
    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        assert cognitive_input is not None
        assert pass_request is not None
        return CognitionConversationOutput(response="visible")

    async def generate_extraction(self, extraction_input, *, pass_request=None):
        assert extraction_input is not None
        assert pass_request is not None
        return CognitionExtractionOutput()

    async def aclose(self) -> None:
        return None


class _FailingTwoPassDelegate:
    async def generate_conversation(self, cognitive_input, *, pass_request=None):
        assert cognitive_input is not None
        assert pass_request is not None
        raise RuntimeError("delegate failed after exact count")

    async def generate_extraction(self, extraction_input, *, pass_request=None):
        raise AssertionError("Pass 2 must not be reached after Pass 1 failure")

    async def aclose(self) -> None:
        return None


def _current_plan_without_capacity():
    plan = replace(
        vllm_host.load_vllm_screening_plan(PLAN_PATH),
        capacity_evidence_id=None,
    )
    assert plan.capacity_evidence_id is None
    return plan


def _prepare(
    monkeypatch: pytest.MonkeyPatch,
) -> acquisition.PreparedVLLMCapacityAcquisition:
    target = vllm_host.load_actual_model_repository_snapshot_target(TARGET_PATH)
    monkeypatch.setattr(acquisition, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        acquisition,
        "verify_actual_model_repository_snapshot",
        lambda **_: _verification(target),
    )
    return acquisition.prepare_vllm_capacity_acquisition(
        plan=_current_plan_without_capacity(),
        condition_id=CURRENT_REFERENCE_ROLE,
        proof_path=PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=SNAPSHOT_ROOT,
        relaylm_commit="c" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        model_runner="v2",
        fetch_json=_live_fetch,
        tokenize_post_json=_tokenize,
    )


def test_prepare_capacity_acquisition_uses_live_runtime_without_cited_capacity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = _prepare(monkeypatch)
    try:
        assert prepared.plan.capacity_evidence_id is None
        assert prepared.screening_condition_id == CURRENT_REFERENCE_ROLE
        assert prepared.model_runner == "v2"
        assert prepared.manifest.effective_context_window == LIVE_MAX_MODEL_LEN
        assert prepared.reasoning_capability.backend_attestation.max_model_len == (
            LIVE_MAX_MODEL_LEN
        )
        assert dict(prepared.serving_counter.evidence_identity.parameters)[
            "context_limit"
        ] == LIVE_MAX_MODEL_LEN
        assert prepared.single_pass_counter is None
        assert prepared.two_pass_counter is not None
    finally:
        asyncio.run(prepared.provider.aclose())


def test_prepare_capacity_acquisition_requires_explicit_runner() -> None:
    with pytest.raises(
        acquisition.VLLMCapacityAcquisitionError,
        match="model_runner",
    ):
        acquisition.prepare_vllm_capacity_acquisition(
            plan=_current_plan_without_capacity(),
            condition_id=CURRENT_REFERENCE_ROLE,
            proof_path=PROOF_PATH,
            repo_root=REPO_ROOT,
            snapshot_root=SNAPSHOT_ROOT,
            relaylm_commit="c" * 40,
            base_url="http://127.0.0.1:8000/v1",
            api_key=None,
        )


def test_partial_acquisition_persists_only_reached_footprint(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = replace(_prepare(monkeypatch), provider=_FailingTwoPassDelegate())

    async def fake_run_actual_model_fixture(*, provider, manifest, **kwargs):
        requests = manifest.cognition_pass_requests
        assert requests is not None
        pass1 = requests.pass1
        assert pass1 is not None
        await provider.generate_conversation(_input(), pass_request=pass1)
        raise AssertionError("unreachable")

    monkeypatch.setattr(
        acquisition,
        "run_actual_model_fixture",
        fake_run_actual_model_fixture,
    )

    with pytest.raises(acquisition.VLLMCapacityAcquisitionFailure) as caught:
        asyncio.run(
            acquisition.execute_vllm_capacity_acquisition(
                prepared=prepared,
                workspace_root=tmp_path / "workspace",
                artifact_root=tmp_path / "artifacts",
            )
        )

    failure = caught.value
    assert failure.artifact is not None
    assert failure.artifact.complete is False
    evidence = load_vllm_runtime_capacity_evidence(failure.artifact.artifact_path)
    assert evidence.model_runner == "v2"
    assert len(evidence.footprints) == 1
    assert evidence.footprints[0].condition_id == prepared.condition.condition_id
    assert evidence.footprints[0].topology == "two_pass"
    assert evidence.footprints[0].pass_id == "pass1"
    assert evidence.footprints[0].scenario_id == prepared.scenario_ids[0]
    assert evidence.footprints[0].turn_index == 1
    assert evidence.footprints[0].total_input_tokens == 700
    with pytest.raises(VLLMRuntimeCapacityEvidenceError, match="incomplete"):
        validate_capacity_coverage(
            evidence=evidence,
            scenario_set_revision=prepared.scenario_set.revision,
            required_coverage=vllm_host._required_capacity_coverage(
                condition=prepared.condition,
                scenario_set=prepared.scenario_set,
                scenario_ids=prepared.scenario_ids,
            ),
        )
    assert [path.name for path in (tmp_path / "artifacts").iterdir()] == [
        f"{evidence.evidence_id}.json"
    ]


def test_complete_acquisition_passes_exact_selected_condition_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prepared = replace(_prepare(monkeypatch), provider=_SuccessfulTwoPassDelegate())

    async def fake_run_actual_model_fixture(*, provider, manifest, scenario, **kwargs):
        requests = manifest.cognition_pass_requests
        assert requests is not None
        pass1 = requests.pass1
        pass2 = requests.pass2
        assert pass1 is not None
        assert pass2 is not None
        for _ in scenario.turns:
            cognitive_input = _input()
            conversation = await provider.generate_conversation(
                cognitive_input,
                pass_request=pass1,
            )
            await provider.generate_extraction(
                CognitionExtractionInput(
                    cognitive_input=cognitive_input,
                    assistant_response=conversation.response,
                ),
                pass_request=pass2,
            )
        return object()

    monkeypatch.setattr(
        acquisition,
        "run_actual_model_fixture",
        fake_run_actual_model_fixture,
    )

    artifact = asyncio.run(
        acquisition.execute_vllm_capacity_acquisition(
            prepared=prepared,
            workspace_root=tmp_path / "workspace",
            artifact_root=tmp_path / "artifacts",
        )
    )

    assert artifact.complete is True
    evidence = load_vllm_runtime_capacity_evidence(artifact.artifact_path)
    assert evidence.model_runner == "v2"
    expected_footprints = 2 * sum(
        len(prepared.scenario_set.scenario(scenario_id).scenario.turns)
        for scenario_id in prepared.scenario_ids
    )
    assert len(evidence.footprints) == expected_footprints
    assert {footprint.pass_id for footprint in evidence.footprints} == {
        "pass1",
        "pass2",
    }
    validate_capacity_coverage(
        evidence=evidence,
        scenario_set_revision=prepared.scenario_set.revision,
        required_coverage=vllm_host._required_capacity_coverage(
            condition=prepared.condition,
            scenario_set=prepared.scenario_set,
            scenario_ids=prepared.scenario_ids,
        ),
    )
    assert [path.name for path in (tmp_path / "artifacts").iterdir()] == [
        f"{evidence.evidence_id}.json"
    ]
