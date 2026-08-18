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
    HostTokenCounterCapability,
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
from relaylm.providers.openai_compatible_budget import (
    OpenAICompatibleSerializedInputCounter,
    SerializedInputCounterIdentity,
)
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode


REPO_ROOT = Path(__file__).resolve().parents[2]
PRIMARY_TARGET_ID = "gemma-4-12b-it-q4-k-m-v1"
LMSTUDIO_COMMUNITY_TARGET_ID = "gemma-4-12b-it-q4-k-m-lmstudio-community-v1"
PRIMARY_TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-v1.json"
)
LMSTUDIO_COMMUNITY_TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)
FIXTURE_ROOT = REPO_ROOT / "evaluation" / "actual_model" / "characters" / "foundation-v1"


def _condition_mapping(
    *,
    target_id: str = LMSTUDIO_COMMUNITY_TARGET_ID,
    scenario_ids: list[str] | None = None,
    continuity_runtime: dict[str, int] | None = None,
) -> dict[str, object]:
    return {
        "format_version": 2,
        "target_id": target_id,
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


def _verification(
    target_path: Path = LMSTUDIO_COMMUNITY_TARGET_PATH,
) -> ActualModelArtifactVerification:
    target = load_actual_model_target(target_path)
    return ActualModelArtifactVerification(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=target.artifact_size_bytes,
        artifact_sha256=target.artifact_sha256,
    )


def _total_condition_mapping(
    *,
    mode: str = "conservative_estimate",
    effective_context_window: int = 32768,
) -> dict[str, object]:
    mapping = _condition_mapping()
    mapping.pop("budgets")
    mapping["format_version"] = 3
    mapping["effective_context_window"] = effective_context_window
    mapping["cognitive_budget"] = {
        "model_context_window": 32768,
        "reserved_output_tokens": 512,
        "initial_plan": {
            "canonical_state": {"max_items": 0, "floor_items": 0},
            "working_context": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
            "retrieved_memory": {
                "max_items": 2,
                "floor_items": 0,
                "max_chars": 512,
                "floor_chars": 0,
            },
            "event_evidence": {
                "max_items": 0,
                "floor_items": 0,
                "max_chars": 0,
                "floor_chars": 0,
            },
        },
        "degradation_steps": [
            {
                "layer": "retrieved_memory",
                "tier": 3,
                "target": {
                    "max_items": 0,
                    "floor_items": 0,
                    "max_chars": 0,
                    "floor_chars": 0,
                },
            }
        ],
        "token_counter": {
            "format_version": 1,
            "capability": "lmstudio.gemma4.serialized-input.v1",
            "implementation": "operator-supplied-lm-studio-counter",
            "version": "counter-contract-v1",
            "mode": mode,
            "tokenizer_identity": (
                "gguf-embedded-tokenizer:sha256:"
                "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
            ),
            "parameters": {
                "request_shape": "openai-compatible-request-body-v1",
                "truthfulness_basis": "caller-verified-provider-model-counter",
            },
        },
    }
    return mapping


def _counter_capability(
    *,
    identity: SerializedInputCounterIdentity | None = None,
    exact_behavior_demonstrated: bool = False,
    conservative_bound_demonstrated: bool = True,
) -> dict[str, HostTokenCounterCapability]:
    def factory(condition, provider):
        counter_identity = identity or condition.cognitive_budget.token_counter_identity
        assert counter_identity is not None
        return OpenAICompatibleSerializedInputCounter(
            model=provider.model,
            count_input=lambda _: SerializedInputTokenCount(
                total_input_tokens=100,
                required_input_framing_tokens=10,
                mode=counter_identity.mode,
            ),
            decoding_config=provider.decoding_config,
            evidence_identity=counter_identity,
        )

    return {
        "lmstudio.gemma4.serialized-input.v1": HostTokenCounterCapability(
            factory=factory,
            exact_behavior_demonstrated=exact_behavior_demonstrated,
            conservative_bound_demonstrated=conservative_bound_demonstrated,
        )
    }


def test_host_condition_loader_is_strict_and_has_no_hidden_runtime_defaults(
    tmp_path: Path,
) -> None:
    path = _write_condition(tmp_path, _condition_mapping())

    condition = load_actual_model_host_condition(path)

    assert condition.target_id == LMSTUDIO_COMMUNITY_TARGET_ID
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


def test_total_host_condition_parses_complete_cognitive_budget_identity(
    tmp_path: Path,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _total_condition_mapping())
    )

    assert condition.format_version == 3
    assert condition.budgets.to_runtime() == host_runner.ExplicitBudgetConfiguration()
    assert condition.cognitive_budget is not None
    assert condition.cognitive_budget.total.model_context_window == 32768
    assert condition.cognitive_budget.total.reserved_output_tokens == 512
    assert condition.cognitive_budget.policy.steps[0].layer.value == "retrieved_memory"
    assert (
        condition.cognitive_budget.token_counter_identity.mode
        is TokenCountMode.CONSERVATIVE_ESTIMATE
    )


@pytest.mark.parametrize(
    "mutate",
    [
        lambda mapping: mapping["cognitive_budget"].pop("reserved_output_tokens"),
        lambda mapping: mapping["cognitive_budget"]["initial_plan"]["canonical_state"].update(
            {"hidden": 1}
        ),
        lambda mapping: mapping["cognitive_budget"]["degradation_steps"][0].update(
            {"tier": 2}
        ),
        lambda mapping: mapping["cognitive_budget"]["token_counter"].update(
            {"mode": "heuristic_guess"}
        ),
    ],
)
def test_total_host_condition_rejects_malformed_or_unsupported_shapes(
    tmp_path: Path,
    mutate,
) -> None:
    mapping = _total_condition_mapping()
    mutate(mapping)

    with pytest.raises(ActualModelHostRunnerError):
        load_actual_model_host_condition(_write_condition(tmp_path, mapping))


def test_total_host_condition_rejects_context_drift_before_preparation(
    tmp_path: Path,
) -> None:
    mapping = _total_condition_mapping(effective_context_window=8192)

    with pytest.raises(
        ActualModelHostRunnerError,
        match="model_context_window must match effective_context_window",
    ):
        load_actual_model_host_condition(_write_condition(tmp_path, mapping))


def test_total_host_preparation_binds_runtime_and_counter_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _total_condition_mapping())
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
        token_counter_capabilities=_counter_capability(),
    )
    try:
        assert prepared.cognitive_budget is not None
        assert prepared.manifest.cognitive_budget is not None
        assert prepared.manifest.budgets == host_runner.ExplicitBudgetConfiguration()
        assert (
            prepared.manifest.cognitive_budget.token_counter_identity
            == prepared.cognitive_budget.token_counter.evidence_identity
        )
        evidence_identity = prepared.manifest.to_mapping()["cognitive_budget"][
            "token_counter"
        ]
        assert evidence_identity["mode"] == "conservative_estimate"
        assert "base_url" not in json.dumps(prepared.manifest.to_mapping())
        assert "api_key" not in json.dumps(prepared.manifest.to_mapping())
    finally:
        asyncio.run(prepared.provider.aclose())


def test_total_host_preparation_fails_closed_without_counter_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _total_condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    with pytest.raises(ActualModelHostRunnerError, match="counter capability"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
        )


def test_total_host_preparation_rejects_counter_identity_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _total_condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )
    declared = condition.cognitive_budget.token_counter_identity
    assert declared is not None
    drifted = SerializedInputCounterIdentity(
        capability=declared.capability,
        implementation=declared.implementation,
        version="different-version",
        mode=declared.mode,
        tokenizer_identity=declared.tokenizer_identity,
        parameters=declared.parameters,
    )

    with pytest.raises(ActualModelHostRunnerError, match="identity"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
            token_counter_capabilities=_counter_capability(identity=drifted),
        )


def test_exact_counter_mode_requires_demonstrated_exact_behavior(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(
            tmp_path,
            _total_condition_mapping(mode="exact"),
        )
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    with pytest.raises(ActualModelHostRunnerError, match="demonstrated exact"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
            token_counter_capabilities=_counter_capability(),
        )


def test_conservative_counter_mode_requires_demonstrated_safe_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _total_condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    with pytest.raises(ActualModelHostRunnerError, match="safe bound"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
            token_counter_capabilities=_counter_capability(
                conservative_bound_demonstrated=False,
            ),
        )


def test_total_host_preparation_rejects_model_counter_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _total_condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    def factory(condition, provider):
        assert condition.cognitive_budget is not None
        return OpenAICompatibleSerializedInputCounter(
            model="different-model",
            count_input=lambda _: SerializedInputTokenCount(
                total_input_tokens=100,
                required_input_framing_tokens=10,
                mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
            ),
            decoding_config=provider.decoding_config,
            evidence_identity=condition.cognitive_budget.token_counter_identity,
        )

    capabilities = {
        "lmstudio.gemma4.serialized-input.v1": HostTokenCounterCapability(
            factory=factory,
            exact_behavior_demonstrated=False,
            conservative_bound_demonstrated=True,
        )
    }

    with pytest.raises(ActualModelHostRunnerError, match="model does not match"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
            token_counter_capabilities=capabilities,
        )


def test_total_host_preparation_rejects_decoding_counter_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(tmp_path, _total_condition_mapping())
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    def factory(condition, provider):
        assert condition.cognitive_budget is not None
        return OpenAICompatibleSerializedInputCounter(
            model=provider.model,
            count_input=lambda _: SerializedInputTokenCount(
                total_input_tokens=100,
                required_input_framing_tokens=10,
                mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
            ),
            decoding_config=host_runner.OpenAICompatibleDecodingConfig(
                temperature=0.7,
                top_p=provider.decoding_config.top_p,
                seed=provider.decoding_config.seed,
            ),
            evidence_identity=condition.cognitive_budget.token_counter_identity,
        )

    capabilities = {
        "lmstudio.gemma4.serialized-input.v1": HostTokenCounterCapability(
            factory=factory,
            exact_behavior_demonstrated=False,
            conservative_bound_demonstrated=True,
        )
    }

    with pytest.raises(ActualModelHostRunnerError, match="decoding configuration"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
            token_counter_capabilities=capabilities,
        )


def test_total_host_preparation_rejects_tokenizer_identity_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _total_condition_mapping()
    mapping["cognitive_budget"]["token_counter"]["tokenizer_identity"] = (  # type: ignore[index]
        "gguf-embedded-tokenizer:sha256:"
        "1" * 64
    )
    condition = load_actual_model_host_condition(_write_condition(tmp_path, mapping))
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(),
    )

    with pytest.raises(ActualModelHostRunnerError, match="tokenizer identity"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
            token_counter_capabilities=_counter_capability(),
        )


def test_v3_cli_passes_resolved_capability_map_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    condition_path = _write_condition(tmp_path, _total_condition_mapping())
    capability_map = {"lmstudio.gemma4.loaded-sdk.serialized-input.v1": object()}
    captured: dict[str, object] = {}

    def resolve_capabilities(**kwargs: object) -> object:
        captured["resolver_kwargs"] = kwargs
        return capability_map

    def fake_prepare(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace()

    async def fake_execute(**kwargs: object) -> tuple[object, ...]:
        captured["execute_kwargs"] = kwargs
        return ()

    monkeypatch.setattr(
        host_runner,
        "_resolve_canonical_host_token_counter_capabilities",
        resolve_capabilities,
    )
    monkeypatch.setattr(host_runner, "prepare_actual_model_host_run", fake_prepare)
    monkeypatch.setattr(host_runner, "execute_actual_model_host_run", fake_execute)

    assert (
        host_runner.main(
            [
                "--condition",
                str(condition_path),
                "--repo-root",
                str(REPO_ROOT),
                "--model-artifact",
                str(tmp_path / "model.gguf"),
                "--workspace-root",
                str(tmp_path / "workspaces"),
                "--artifact-root",
                str(tmp_path / "evidence"),
                "--counter-proof",
                str(tmp_path / "counter-proof.json"),
            ]
        )
        == 0
    )
    assert captured["token_counter_capabilities"] is capability_map
    assert capsys.readouterr().out


def test_v2_cli_does_not_resolve_lm_studio_counter_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition_path = _write_condition(tmp_path, _condition_mapping())
    captured: dict[str, object] = {}

    def unexpected_resolver(**kwargs: object) -> object:
        raise AssertionError("v2 must not resolve the LM Studio SDK counter")

    def fake_prepare(**kwargs: object) -> object:
        captured.update(kwargs)
        return SimpleNamespace()

    async def fake_execute(**kwargs: object) -> tuple[object, ...]:
        return ()

    monkeypatch.setattr(
        host_runner,
        "_resolve_canonical_host_token_counter_capabilities",
        unexpected_resolver,
    )
    monkeypatch.setattr(host_runner, "prepare_actual_model_host_run", fake_prepare)
    monkeypatch.setattr(host_runner, "execute_actual_model_host_run", fake_execute)

    assert (
        host_runner.main(
            [
                "--condition",
                str(condition_path),
                "--repo-root",
                str(REPO_ROOT),
                "--model-artifact",
                str(tmp_path / "model.gguf"),
                "--workspace-root",
                str(tmp_path / "workspaces"),
                "--artifact-root",
                str(tmp_path / "evidence"),
            ]
        )
        == 0
    )
    assert captured["token_counter_capabilities"] is None


def test_v3_cli_reports_missing_sdk_or_proof_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    condition_path = _write_condition(tmp_path, _total_condition_mapping())
    generated = False

    def unavailable(**kwargs: object) -> object:
        raise host_runner.ActualModelHostRunnerError(
            "LM Studio counter capability is unavailable: SDK or exact proof is missing"
        )

    async def should_not_execute(**kwargs: object) -> tuple[object, ...]:
        nonlocal generated
        generated = True
        return ()

    monkeypatch.setattr(
        host_runner,
        "_resolve_canonical_host_token_counter_capabilities",
        unavailable,
    )
    monkeypatch.setattr(host_runner, "execute_actual_model_host_run", should_not_execute)

    assert (
        host_runner.main(
            [
                "--condition",
                str(condition_path),
                "--repo-root",
                str(REPO_ROOT),
                "--model-artifact",
                str(tmp_path / "model.gguf"),
                "--workspace-root",
                str(tmp_path / "workspaces"),
                "--artifact-root",
                str(tmp_path / "evidence"),
            ]
        )
        == 2
    )
    assert generated is False
    assert "SDK or exact proof" in capsys.readouterr().err


def test_v3_cli_real_resolver_rejects_missing_counter_proof_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    condition_path = _write_condition(tmp_path, _total_condition_mapping())
    generated = False

    async def should_not_execute(**kwargs: object) -> tuple[object, ...]:
        nonlocal generated
        generated = True
        return ()

    monkeypatch.setattr(host_runner, "execute_actual_model_host_run", should_not_execute)

    assert (
        host_runner.main(
            [
                "--condition",
                str(condition_path),
                "--repo-root",
                str(REPO_ROOT),
                "--model-artifact",
                str(tmp_path / "model.gguf"),
                "--workspace-root",
                str(tmp_path / "workspaces"),
                "--artifact-root",
                str(tmp_path / "evidence"),
            ]
        )
        == 2
    )
    assert generated is False
    assert "exact LM Studio counter proof" in capsys.readouterr().err


def test_host_condition_loader_rejects_duplicate_json_keys_and_scenarios(
    tmp_path: Path,
) -> None:
    duplicate_key = tmp_path / "duplicate-key.json"
    duplicate_key.write_text(
        '{"format_version":2,"format_version":2}',
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


def test_prepare_derives_manifest_from_selected_target_fixture_and_provider(
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
        target = load_actual_model_target(LMSTUDIO_COMMUNITY_TARGET_PATH)
        identity = describe_openai_compatible_provider(prepared.provider)
        manifest = prepared.manifest

        assert prepared.target == target
        assert prepared.target.target_id == LMSTUDIO_COMMUNITY_TARGET_ID
        assert prepared.target.artifact_repository == "lmstudio-community/gemma-4-12B-it-GGUF"
        assert (
            prepared.target.artifact_repository_revision
            == "65fe312c53d8b4579f444382adf078bacb1972d0"
        )
        assert prepared.target.artifact_size_bytes == 7_381_384_864
        assert (
            prepared.target.artifact_sha256
            == "c088a44859de42a1966851b552ba628c0ff4419b87c4622539d69430f40024ed"
        )
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


def test_prepare_keeps_original_bartowski_target_selectable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(
            tmp_path,
            _condition_mapping(target_id=PRIMARY_TARGET_ID),
        )
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(
        host_runner,
        "verify_actual_model_artifact",
        lambda **_: _verification(PRIMARY_TARGET_PATH),
    )

    prepared = prepare_actual_model_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "not-read-because-verifier-is-patched.gguf",
    )
    try:
        assert prepared.target == load_actual_model_target(PRIMARY_TARGET_PATH)
    finally:
        asyncio.run(prepared.provider.aclose())


def test_prepare_rejects_target_outside_allowlist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    condition = load_actual_model_host_condition(
        _write_condition(
            tmp_path,
            _condition_mapping(target_id="not-a-canonical-target"),
        )
    )
    monkeypatch.setattr(host_runner, "_verify_clean_exact_repo", lambda **_: None)

    with pytest.raises(ActualModelHostRunnerError, match="not an allowed actual-model target"):
        prepare_actual_model_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "model.gguf",
        )


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
        cognitive_budget=object(),
    )
    captured: dict[str, object] = {}

    async def fake_run(**kwargs: object) -> object:
        captured.update(kwargs)
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
    assert captured["cognitive_budget"] is prepared.cognitive_budget
