from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import relaylm.actual_model_host_runner as host_runner
from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_host_runner import (
    ActualModelHostRunnerError,
    load_actual_model_host_condition,
    prepare_actual_model_host_run,
)
from relaylm.actual_model_targets import (
    ActualModelArtifactVerification,
    load_actual_model_target,
)
from relaylm.providers.openai_compatible_identity import (
    describe_openai_compatible_provider,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-v1.json"
)
FIXTURE_ROOT = REPO_ROOT / "evaluation" / "actual_model" / "characters" / "foundation-v1"


def _condition_mapping(
    *,
    scenario_ids: list[str] | None = None,
    continuity_runtime: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "format_version": 1,
        "relaylm_commit": "9" * 40,
        "lm_studio": {
            "version": "0.3.30",
            "build": "example-build-123",
            "deployment_identity": "local-lm-studio-primary",
            "base_url": "http://127.0.0.1:1234/v1",
            "request_model": "google/gemma-4-12b",
            "api_key_env": None,
        },
        "effective_context_window": 32768,
        "decoding": {
            "temperature": 0.2,
            "top_p": 0.95,
            "seed": 7,
        },
        "supported_decoding_controls": ["temperature", "top_p", "seed"],
        "execution_path": "buffered",
        "continuity_runtime": continuity_runtime,
        "budgets": {
            "memory_max_chunks": 2,
            "memory_max_chars": 1024,
            "event_max_events": 4,
            "event_max_chars": 2048,
        },
        "condition_id": "explicit-baseline-example",
        "replicate_id": "0",
        "scenario_ids": scenario_ids or ["response-persona-correction-v1"],
    }


def _write_condition(tmp_path: Path, mapping: dict[str, object]) -> Path:
    path = tmp_path / "condition.json"
    path.write_text(json.dumps(mapping, ensure_ascii=False), encoding="utf-8")
    return path


def _verification() -> ActualModelArtifactVerification:
    target = load_actual_model_target(TARGET_PATH)
    return ActualModelArtifactVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=target.artifact_size_bytes,
        artifact_sha256=target.artifact_sha256,
    )


def test_host_condition_loader_is_strict_and_has_no_hidden_runtime_defaults(
    tmp_path: Path,
) -> None:
    path = _write_condition(tmp_path, _condition_mapping())

    condition = load_actual_model_host_condition(path)

    assert condition.relaylm_commit == "9" * 40
    assert condition.environment.version == "0.3.30"
    assert condition.environment.build == "example-build-123"
    assert condition.environment.request_model == "google/gemma-4-12b"
    assert condition.decoding_config.to_mapping() == {
        "temperature": 0.2,
        "top_p": 0.95,
        "seed": 7,
    }
    assert condition.budgets.to_runtime().memory_max_chunks == 2
    assert condition.continuity is None

    unknown = _condition_mapping()
    unknown["hidden_default"] = 4096
    with pytest.raises(ActualModelHostRunnerError, match="unknown fields"):
        load_actual_model_host_condition(_write_condition(tmp_path, unknown))


def test_host_condition_loader_rejects_duplicate_json_keys_and_scenarios(
    tmp_path: Path,
) -> None:
    duplicate_key = tmp_path / "duplicate-key.json"
    duplicate_key.write_text(
        '{"format_version":1,"format_version":1}',
        encoding="utf-8",
    )
    with pytest.raises(ActualModelHostRunnerError, match="duplicate JSON key"):
        load_actual_model_host_condition(duplicate_key)

    duplicate_scenario = _condition_mapping(
        scenario_ids=["response-persona-correction-v1", "response-persona-correction-v1"]
    )
    with pytest.raises(ActualModelHostRunnerError, match="scenario_ids.*duplicates"):
        load_actual_model_host_condition(
            _write_condition(tmp_path, duplicate_scenario)
        )


def test_prepare_derives_manifest_from_canonical_target_fixture_and_provider(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    prepared = prepare_actual_model_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
    )
    try:
        target = load_actual_model_target(TARGET_PATH)
        identity = describe_openai_compatible_provider(prepared.provider)
        manifest = prepared.manifest

        assert prepared.target == target
        assert prepared.scenario_set.scenario_set_version == "actual-model-foundation-v2"
        assert manifest.relaylm_commit == condition.relaylm_commit
        assert manifest.character_fixture_id == "actual-model-foundation-v1"
        assert manifest.character_fixture_revision == character_fixture_revision(FIXTURE_ROOT)
        assert manifest.provider_identity == condition.environment.manifest_provider_identity
        assert manifest.adapter_identity == identity.adapter_identity
        assert manifest.model_artifact == target.model_artifact_identity
        assert manifest.tokenizer_identity == target.tokenizer_identity
        assert manifest.effective_context_window == 32768
        assert dict(manifest.decoding_configuration) == {
            "temperature": 0.2,
            "top_p": 0.95,
            "seed": 7,
        }
        assert manifest.seed == 7
        assert manifest.provider_capabilities == identity.provider_capabilities
        assert manifest.cognitive_budget is None
        assert manifest.scenario_set_version == "actual-model-foundation-v2"
    finally:
        asyncio.run(prepared.provider.aclose())


def test_prepare_requires_continuity_identity_for_selected_continuity_scenario(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(
            tmp_path,
            _condition_mapping(
                scenario_ids=["continuity-lifecycle-v1"],
                continuity_runtime=None,
            ),
        )
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    with pytest.raises(ActualModelHostRunnerError, match="continuity_runtime"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "model.gguf",
        )


def test_prepare_rejects_scenario_outside_canonical_foundation_v2(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(
            tmp_path,
            _condition_mapping(scenario_ids=["not-a-canonical-scenario"]),
        )
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    with pytest.raises(ActualModelHostRunnerError, match="outside canonical foundation-v2"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "model.gguf",
        )


def test_exact_repo_preflight_rejects_head_drift_and_dirty_worktree(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def mismatched_head(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        output = "8" * 40 + "\n" if calls == 1 else ""
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(host_runner.subprocess, "run", mismatched_head)
    with pytest.raises(ActualModelHostRunnerError, match="HEAD does not match"):
        host_runner._verify_clean_exact_repo(
            root=tmp_path,
            expected_commit="9" * 40,
        )

    calls = 0

    def dirty_repo(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal calls
        calls += 1
        output = "9" * 40 + "\n" if calls == 1 else "?? condition.json\n"
        return subprocess.CompletedProcess(args=[], returncode=0, stdout=output, stderr="")

    monkeypatch.setattr(host_runner.subprocess, "run", dirty_repo)
    with pytest.raises(ActualModelHostRunnerError, match="must be clean"):
        host_runner._verify_clean_exact_repo(
            root=tmp_path,
            expected_commit="9" * 40,
        )


def test_execute_persists_boundary_sidecar_from_existing_execution_result(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Provider:
        closed = False

        async def aclose(self) -> None:
            self.closed = True

    provider = _Provider()
    execution = object()
    wrapped = SimpleNamespace(
        execution_id="amlsx-example",
        run_id="amr-example",
        execution=execution,
    )
    verdict = SimpleNamespace(
        verdict_id="amb-example",
        outcome="pass",
    )
    condition = SimpleNamespace(
        scenario_ids=("response-persona-correction-v1",),
        environment=object(),
        effective_context_window=32768,
        condition_id="baseline",
        replicate_id="0",
    )
    prepared = SimpleNamespace(
        condition=condition,
        target=object(),
        artifact_verification=object(),
        scenario_set=object(),
        fixture_root=tmp_path / "fixture",
        provider=provider,
        manifest=object(),
    )

    async def fake_run(**_: object) -> object:
        return wrapped

    def fake_evaluate(*, result: object) -> object:
        assert result is execution
        return verdict

    monkeypatch.setattr(
        host_runner,
        "run_lm_studio_actual_model_scenario_definition",
        fake_run,
    )
    monkeypatch.setattr(
        host_runner,
        "write_lm_studio_actual_model_execution_result",
        lambda **_: tmp_path / "amlsx-example.lm-studio.json",
    )
    monkeypatch.setattr(
        host_runner,
        "evaluate_actual_model_deterministic_boundary",
        fake_evaluate,
    )
    monkeypatch.setattr(
        host_runner,
        "write_actual_model_deterministic_boundary_verdict",
        lambda **_: tmp_path / "amb-example.boundary.json",
    )

    artifacts = asyncio.run(
        host_runner.execute_actual_model_host_run(
            prepared=prepared,  # type: ignore[arg-type]
            workspace_root=tmp_path / "workspaces",
            artifact_root=tmp_path / "evidence",
        )
    )

    assert provider.closed is True
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.scenario_id == "response-persona-correction-v1"
    assert artifact.execution_id == "amlsx-example"
    assert artifact.run_id == "amr-example"
    assert artifact.artifact_path.endswith("amlsx-example.lm-studio.json")
    assert artifact.boundary_verdict_id == "amb-example"
    assert artifact.boundary_outcome == "pass"
    assert artifact.boundary_artifact_path.endswith("amb-example.boundary.json")
