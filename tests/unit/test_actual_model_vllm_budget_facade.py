from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import relaylm.actual_model_host as host_runner
import relaylm.actual_model_vllm_budget as budget_bridge


CURRENT_SCREENING_ID = "stage-r0-vllm-reference-v2"
REFERENCE_BASELINE_ROLE = "reference_baseline"


def _write_budget(path: Path, *, include_counter: bool = False) -> None:
    payload: dict[str, object] = {
        "format_version": 1,
        "mode": "two_pass",
        "pass1": {
            "model_context_window": 1616,
            "reserved_output_tokens": 32,
        },
        "pass2": {
            "model_context_window": 1616,
            "reserved_output_tokens": 64,
        },
        "initial_plan": {
            "canonical_state": {"max_items": 0, "floor_items": 0},
            "working_context": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
            "retrieved_memory": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
            "event_evidence": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
        },
        "degradation_steps": [],
    }
    if include_counter:
        payload["token_counter"] = {"implementation": "caller-owned-is-forbidden"}
    path.write_text(json.dumps(payload), encoding="utf-8")


def _screening_args(tmp_path: Path, budget_path: Path) -> list[str]:
    return [
        "--backend",
        "vllm",
        "--condition",
        REFERENCE_BASELINE_ROLE,
        "--model-runner",
        "v2",
        "--repo-root",
        str(tmp_path),
        "--snapshot-root",
        "/tmp/relaylm-google-gemma4-official-attest.CKxAGh",
        "--provider-base-url",
        "http://127.0.0.1:8000/v1",
        "--workspace-root",
        "/tmp/relaylm-vllm-work",
        "--artifact-root",
        "/tmp/relaylm-vllm-evidence",
        "--cognitive-budget",
        str(budget_path),
    ]


def _bind_reference_role(monkeypatch, plan) -> None:
    monkeypatch.setattr(
        host_runner,
        "screening_condition_key_for_role",
        lambda plan_arg, role: (
            role
            if plan_arg is plan and role == REFERENCE_BASELINE_ROLE
            else (_ for _ in ()).throw(AssertionError("unexpected screening role"))
        ),
    )


def test_vllm_screening_facade_carries_strict_two_pass_budget_declaration(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    budget_path = tmp_path / "budget.json"
    _write_budget(budget_path)
    plan = SimpleNamespace(screening_id=CURRENT_SCREENING_ID)
    observed: dict[str, object] = {}
    prepared = SimpleNamespace(
        plan=plan,
        screening_condition_id=REFERENCE_BASELINE_ROLE,
        manifest=SimpleNamespace(relaylm_commit="a" * 40, replicate_id="0"),
        target=SimpleNamespace(target_id="gemma-4-12b-it-qat-w4a16-google-vllm-v1"),
    )

    def fake_prepare(**kwargs):
        observed.update(kwargs)
        return prepared

    async def fake_execute(**kwargs):
        return (
            SimpleNamespace(
                to_mapping=lambda: {
                    "scenario_id": "response-persona-correction-v1",
                    "execution_id": "amvx-1",
                    "run_id": "amr-1",
                    "artifact_path": "/tmp/amvx-1.vllm.json",
                    "boundary_verdict_id": "ambv-1",
                    "boundary_outcome": "pass",
                    "boundary_artifact_path": "/tmp/ambv-1.json",
                }
            ),
        )

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", lambda _: plan)
    _bind_reference_role(monkeypatch, plan)
    monkeypatch.setattr(host_runner, "_prepare_vllm_screening_condition", fake_prepare)
    monkeypatch.setattr(host_runner, "_execute_vllm_host_run", fake_execute)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    result = host_runner.main(_screening_args(tmp_path, budget_path))

    assert result == 0
    assert observed["condition_id"] == REFERENCE_BASELINE_ROLE
    declaration = observed["cognitive_budget"]
    assert type(declaration).__name__ == "VLLMTwoPassCognitiveBudgetDeclaration"
    assert declaration.pass1_total.model_context_window == 1616
    assert declaration.pass1_total.reserved_output_tokens == 32
    assert declaration.pass2_total.model_context_window == 1616
    assert declaration.pass2_total.reserved_output_tokens == 64
    assert declaration.policy.steps == ()
    assert not hasattr(declaration, "token_counter")
    assert f'"condition": "{REFERENCE_BASELINE_ROLE}"' in capsys.readouterr().out


def test_vllm_budget_declaration_rejects_caller_owned_counter_identity(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    budget_path = tmp_path / "budget.json"
    _write_budget(budget_path, include_counter=True)
    plan = SimpleNamespace(screening_id=CURRENT_SCREENING_ID)
    called = False

    def fake_prepare(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("prepare must not run for an invalid declaration")

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", lambda _: plan)
    _bind_reference_role(monkeypatch, plan)
    monkeypatch.setattr(host_runner, "_prepare_vllm_screening_condition", fake_prepare)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    result = host_runner.main(_screening_args(tmp_path, budget_path))

    assert result == 2
    assert called is False
    stderr = capsys.readouterr().err
    assert "cognitive budget declaration has unknown fields: token_counter" in stderr


def test_vllm_capacity_operation_rejects_screening_budget_declaration(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    budget_path = tmp_path / "budget.json"
    _write_budget(budget_path)
    plan = SimpleNamespace(screening_id=CURRENT_SCREENING_ID)
    called = False

    def fake_capacity_prepare(**kwargs):
        nonlocal called
        called = True
        raise AssertionError("capacity preparation must not consume screening budget policy")

    monkeypatch.setattr(host_runner, "load_vllm_screening_plan", lambda _: plan)
    _bind_reference_role(monkeypatch, plan)
    monkeypatch.setattr(host_runner, "_prepare_vllm_capacity_acquisition", fake_capacity_prepare)
    monkeypatch.setattr(host_runner, "_current_repo_head", lambda _: "a" * 40)

    args = _screening_args(tmp_path, budget_path)
    args[2:2] = ["--operation", "capacity"]
    result = host_runner.main(args)

    assert result == 2
    assert called is False
    assert "--cognitive-budget is valid only for screening" in capsys.readouterr().err


def test_budget_declaration_resolves_only_through_host_owned_live_counter(
    tmp_path: Path,
    monkeypatch,
) -> None:
    budget_path = tmp_path / "budget.json"
    _write_budget(budget_path)
    declaration = budget_bridge.load_vllm_two_pass_cognitive_budget_declaration(
        budget_path
    )

    plan = SimpleNamespace(
        decoding_config=object(),
        decoding_capabilities=object(),
    )
    capability = SimpleNamespace(
        request_model="gemma-4-12B-it-qat-w4a16",
        backend_attestation=SimpleNamespace(max_model_len=1616),
    )
    serving_counter = SimpleNamespace(
        count_input=lambda _: None,
        evidence_identity="live-counter-identity",
    )

    class FakeTwoPassCounter:
        def count_conversation_input(self, cognitive_input, *, pass_request=None):
            raise AssertionError("counter is not executed by this carriage test")

        def count_extraction_input(self, extraction_input, *, pass_request=None):
            raise AssertionError("counter is not executed by this carriage test")

    resolved_counter = FakeTwoPassCounter()
    observed: dict[str, object] = {}
    serialized_counter_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        budget_bridge,
        "load_actual_model_repository_snapshot_target",
        lambda _: object(),
    )
    monkeypatch.setattr(
        budget_bridge,
        "load_vllm_reasoning_probe_proof",
        lambda _: object(),
    )
    monkeypatch.setattr(
        budget_bridge,
        "acquire_vllm_reasoning_capability",
        lambda **_: capability,
    )
    monkeypatch.setattr(
        budget_bridge,
        "VLLMServingTokenizerCounter",
        lambda **_: serving_counter,
    )

    def fake_serialized_counter(**kwargs):
        serialized_counter_kwargs.update(kwargs)
        return resolved_counter

    monkeypatch.setattr(
        budget_bridge,
        "OpenAICompatibleTwoPassSerializedInputCounter",
        fake_serialized_counter,
    )

    marker = object()

    def fake_prepare(**kwargs):
        observed.update(kwargs)
        return marker

    monkeypatch.setattr(
        budget_bridge,
        "_prepare_vllm_screening_condition",
        fake_prepare,
    )

    result = budget_bridge.prepare_vllm_screening_condition_with_budget_declaration(
        plan=plan,
        condition_id=REFERENCE_BASELINE_ROLE,
        proof_path=tmp_path / "proof.json",
        repo_root=tmp_path,
        snapshot_root=tmp_path / "snapshot",
        relaylm_commit="a" * 40,
        base_url="http://127.0.0.1:8000/v1",
        api_key=None,
        model_runner="v2",
        cognitive_budget=declaration,
    )

    assert result is marker
    runtime = observed["cognitive_budget"]
    assert runtime.pass1_total == declaration.pass1_total
    assert runtime.pass2_total == declaration.pass2_total
    assert runtime.policy == declaration.policy
    assert runtime.token_counter is resolved_counter
    assert serialized_counter_kwargs["count_input"] is serving_counter.count_input
    assert serialized_counter_kwargs["evidence_identity"] == "live-counter-identity"
