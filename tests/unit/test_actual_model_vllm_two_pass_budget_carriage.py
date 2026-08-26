from __future__ import annotations

import asyncio
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

import relaylm.actual_model_fast_screening as fast_screening
import relaylm.actual_model_fast_screening_artifacts as fast_screening_artifacts
import relaylm.actual_model_vllm_host as vllm_host
from relaylm.actual_model_cognitive_budget import ExplicitCognitiveBudgetConfiguration
from relaylm.actual_model_fast_screening import REFERENCE_BASELINE_ROLE
from relaylm.actual_model_vllm_capacity import (
    VLLMCapacityFootprintObservation,
    VLLMRuntimeCapacityEvidence,
    vllm_capacity_pass_request_id,
    write_vllm_runtime_capacity_evidence,
)
from relaylm.actual_model_vllm_counter import VLLMServingTokenizerCounter
from relaylm.budget import (
    BudgetDegradationPolicy,
    BudgetPlan,
    CountCharacterEnvelope,
    CountEnvelope,
    TotalBudgetConfig,
)
from relaylm.budget_enforcement import TokenCountMode
from relaylm.budget_runtime import TwoPassCognitiveBudgetRuntimeConfig
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleTwoPassSerializedInputCounter,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_ROOT = Path("/tmp/relaylm-google-gemma4-official-attest.CKxAGh")
BASE_URL = "http://127.0.0.1:8000/v1"


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
                    "max_model_len": 1616,
                }
            ],
        }
    raise AssertionError(f"unexpected URL: {url}")


def _zero_plan() -> BudgetPlan:
    return BudgetPlan(
        canonical_state=CountEnvelope(0, 0),
        working_context=CountCharacterEnvelope(0, 0, 0, 0),
        retrieved_memory=CountCharacterEnvelope(0, 0, 0, 0),
        event_evidence=CountCharacterEnvelope(0, 0, 0, 0),
    )


def _write_current_capacity(
    *,
    root: Path,
    plan,
    target,
    capability,
    counter_identity,
) -> VLLMRuntimeCapacityEvidence:
    scenario_set = vllm_host.load_actual_model_scenario_set(
        REPO_ROOT / vllm_host.CANONICAL_SCENARIO_SET_PATH
    )
    condition = plan.conditions[REFERENCE_BASELINE_ROLE]
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
    evidence = VLLMRuntimeCapacityEvidence(
        relaylm_commit="b" * 40,
        target_id=target.target_id,
        target_revision=target.revision,
        tokenizer_identity=target.tokenizer_identity,
        chat_template_identity=target.chat_template_identity,
        backend_version=capability.backend_version,
        request_model=capability.request_model,
        observed_max_model_len=1616,
        scenario_set_revision=scenario_set.revision,
        counter_identity=counter_identity,
        footprints=tuple(footprints),
        model_runner="v2",
    )
    write_vllm_runtime_capacity_evidence(evidence=evidence, artifact_root=root)
    return evidence


def _prepared_inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    plan = vllm_host.load_vllm_screening_plan(
        REPO_ROOT / vllm_host.CANONICAL_VLLM_SCREENING_PLAN_PATH
    )
    target = vllm_host.load_actual_model_repository_snapshot_target(
        REPO_ROOT / vllm_host.CANONICAL_VLLM_TARGET_PATH
    )
    proof = vllm_host.load_vllm_reasoning_probe_proof(
        REPO_ROOT / vllm_host.CANONICAL_VLLM_REASONING_PROOF_PATH
    )
    capability = vllm_host.acquire_vllm_reasoning_capability(
        proof=proof,
        target=target,
        base_url=BASE_URL,
        api_key=None,
        fetch_json=_live_fetch,
    )
    serving_counter = VLLMServingTokenizerCounter(
        base_url=BASE_URL,
        target=target,
        reasoning_capability=capability,
        expected_max_model_len=1616,
        post_json=lambda *_: {"count": 1, "max_model_len": 1616},
    )
    evidence = _write_current_capacity(
        root=tmp_path,
        plan=plan,
        target=target,
        capability=capability,
        counter_identity=serving_counter.evidence_identity,
    )
    plan = replace(plan, capacity_evidence_id=evidence.evidence_id)
    counter = OpenAICompatibleTwoPassSerializedInputCounter(
        model=capability.request_model,
        count_input=serving_counter.count_input,
        decoding_config=plan.decoding_config,
        decoding_capabilities=plan.decoding_capabilities,
        vllm_reasoning_capability=capability,
        evidence_identity=serving_counter.evidence_identity,
    )
    runtime = TwoPassCognitiveBudgetRuntimeConfig(
        pass1_total=TotalBudgetConfig(
            model_context_window=1616,
            reserved_output_tokens=32,
        ),
        pass2_total=TotalBudgetConfig(
            model_context_window=1616,
            reserved_output_tokens=64,
        ),
        policy=BudgetDegradationPolicy(initial_plan=_zero_plan(), steps=()),
        token_counter=counter,
    )
    monkeypatch.setattr(vllm_host, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        vllm_host,
        "verify_actual_model_repository_snapshot",
        lambda **_: vllm_host.ActualModelRepositorySnapshotVerification(
            target_id=target.target_id,
            target_revision=target.revision,
            verified_file_count=len(target.files),
        ),
    )
    return plan, runtime


def _prepare(
    *,
    plan,
    runtime: TwoPassCognitiveBudgetRuntimeConfig,
    capacity_root: Path,
    condition_id: str = REFERENCE_BASELINE_ROLE,
):
    return vllm_host.prepare_vllm_screening_condition(
        plan=plan,
        condition_id=condition_id,
        proof_path=REPO_ROOT / vllm_host.CANONICAL_VLLM_REASONING_PROOF_PATH,
        repo_root=REPO_ROOT,
        snapshot_root=SNAPSHOT_ROOT,
        relaylm_commit="b" * 40,
        base_url=BASE_URL,
        api_key=None,
        model_runner="v2",
        fetch_json=_live_fetch,
        capacity_evidence_root=capacity_root,
        cognitive_budget=runtime,
    )


def test_prepare_vllm_two_pass_binds_explicit_runtime_to_manifest(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, runtime = _prepared_inputs(tmp_path, monkeypatch)

    prepared = _prepare(plan=plan, runtime=runtime, capacity_root=tmp_path)
    try:
        assert prepared.cognitive_budget is not None
        assert prepared.cognitive_budget is not runtime
        assert prepared.cognitive_budget.pass1_total == runtime.pass1_total
        assert prepared.cognitive_budget.pass2_total == runtime.pass2_total
        assert prepared.cognitive_budget.policy == runtime.policy
        assert (
            prepared.cognitive_budget.token_counter.evidence_identity
            == runtime.token_counter.evidence_identity
        )
        assert (
            prepared.cognitive_budget.token_counter.count_input
            != runtime.token_counter.count_input
        )
        assert prepared.manifest.cognitive_budget == (
            ExplicitCognitiveBudgetConfiguration.from_runtime(prepared.cognitive_budget)
        )
        assert prepared.binding.manifest.cognitive_budget == prepared.manifest.cognitive_budget
    finally:
        asyncio.run(prepared.provider.aclose())


def test_prepare_vllm_two_pass_rejects_counter_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, runtime = _prepared_inputs(tmp_path, monkeypatch)
    assert runtime.token_counter.evidence_identity is not None
    bad_identity = replace(
        runtime.token_counter.evidence_identity,
        tokenizer_identity="mismatched-tokenizer",
    )
    bad_counter = replace(runtime.token_counter, evidence_identity=bad_identity)
    bad_runtime = replace(runtime, token_counter=bad_counter)

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="counter identity does not match cited capacity semantics",
    ):
        _prepare(plan=plan, runtime=bad_runtime, capacity_root=tmp_path)


def test_prepare_vllm_two_pass_rejects_historical_single_pass_condition(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, runtime = _prepared_inputs(tmp_path, monkeypatch)
    historical = vllm_host.load_vllm_screening_plan(
        REPO_ROOT / vllm_host.CANONICAL_VLLM_HISTORICAL_SCREENING_PLAN_PATH
    )

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="requires a two_pass screening condition",
    ):
        _prepare(
            plan=historical,
            runtime=runtime,
            capacity_root=tmp_path,
            condition_id="A",
        )


def test_prepare_vllm_two_pass_rejects_context_window_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, runtime = _prepared_inputs(tmp_path, monkeypatch)
    bad_runtime = replace(
        runtime,
        pass2_total=TotalBudgetConfig(
            model_context_window=1615,
            reserved_output_tokens=runtime.pass2_total.reserved_output_tokens,
        ),
    )

    with pytest.raises(
        vllm_host.ActualModelVLLMHostError,
        match="context windows must match",
    ):
        _prepare(plan=plan, runtime=bad_runtime, capacity_root=tmp_path)


def test_execute_vllm_host_run_forwards_host_bound_two_pass_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    plan, runtime = _prepared_inputs(tmp_path, monkeypatch)
    prepared = _prepare(plan=plan, runtime=runtime, capacity_root=tmp_path)
    assert prepared.cognitive_budget is not None

    observed: list[TwoPassCognitiveBudgetRuntimeConfig | None] = []

    async def fake_run(**kwargs):
        observed.append(kwargs.get("cognitive_budget"))
        scenario_id = kwargs["scenario_id"]
        return SimpleNamespace(
            execution_id=f"outer-{scenario_id}",
            run_id=f"run-{scenario_id}",
            execution=SimpleNamespace(execution_id=f"inner-{scenario_id}"),
        )

    monkeypatch.setattr(
        vllm_host,
        "run_bound_vllm_actual_model_scenario_definition",
        fake_run,
    )
    monkeypatch.setattr(
        vllm_host,
        "write_vllm_actual_model_execution_result",
        lambda **_: tmp_path / "execution.json",
    )
    monkeypatch.setattr(
        vllm_host,
        "evaluate_actual_model_deterministic_boundary",
        lambda **_: SimpleNamespace(verdict_id="verdict", outcome="pass"),
    )
    monkeypatch.setattr(
        vllm_host,
        "write_actual_model_deterministic_boundary_verdict",
        lambda **_: tmp_path / "boundary.json",
    )
    monkeypatch.setattr(
        fast_screening,
        "instrument_screening_provider",
        lambda provider, **_: provider,
    )
    monkeypatch.setattr(
        fast_screening_artifacts,
        "bind_fast_screening_timing_artifact",
        lambda **_: SimpleNamespace(timing_id="timing"),
    )
    monkeypatch.setattr(
        fast_screening_artifacts,
        "write_fast_screening_timing_artifact",
        lambda **_: tmp_path / "timing.json",
    )

    asyncio.run(
        vllm_host.execute_vllm_host_run(
            prepared=prepared,
            snapshot_root=SNAPSHOT_ROOT,
            workspace_root=tmp_path / "workspace",
            artifact_root=tmp_path / "artifacts",
        )
    )

    assert observed == [prepared.cognitive_budget] * len(prepared.scenario_ids)
