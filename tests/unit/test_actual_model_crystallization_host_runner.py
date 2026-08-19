from __future__ import annotations

import asyncio
import importlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from relaylm.actual_model_artifacts import character_fixture_revision
from relaylm.actual_model_targets import ActualModelArtifactVerification, load_actual_model_target
from relaylm.crystallization import CrystallizationInput, CrystallizationOutput


MODULE = "relaylm.actual_model_crystallization_host_runner"
REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET_ID = "gemma-4-12b-it-q4-k-m-lmstudio-community-v1"
TARGET_PATH = (
    REPO_ROOT
    / "evaluation"
    / "actual_model"
    / "targets"
    / "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)
FIXTURE_RELATIVE = Path("evaluation/actual_model/characters/foundation-v1")
FIXTURE_ROOT = REPO_ROOT / FIXTURE_RELATIVE
FIXTURE_REVISION = character_fixture_revision(FIXTURE_ROOT)


def _subject():
    spec = importlib.util.find_spec(MODULE)
    assert spec is not None, "CRY3 crystallization host runner is not implemented"
    return importlib.import_module(MODULE)


def _condition_mapping() -> dict[str, object]:
    return {
        "format_version": 2,
        "target_id": TARGET_ID,
        "relaylm_commit": "9" * 40,
        "lm_studio": {
            "version": "0.4.0",
            "build": "example-build-456",
            "deployment_identity": "local-lm-studio-primary",
            "base_url": "http://127.0.0.1:1234/v1",
            "request_model": "google/gemma-4-12b",
            "api_key_env": None,
        },
        "effective_context_window": 32768,
        "decoding": {
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 7,
        },
        "supported_decoding_controls": ["temperature", "top_p", "seed"],
        "reasoning": {"required_setting": "on"},
        "character_fixture": {
            "id": "actual-model-foundation-v1",
            "path": FIXTURE_RELATIVE.as_posix(),
            "revision": FIXTURE_REVISION,
        },
        "case": {
            "id": "crystallization-baseline",
            "version": "1",
        },
        "max_events": 100,
        "condition_id": "crystallization-baseline",
        "replicate_id": "0",
    }


def _write_condition(tmp_path: Path, mapping: dict[str, object]) -> Path:
    path = tmp_path / "crystallization-condition.json"
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


def _reasoning_identity(subject):
    return subject.ActualModelCrystallizationReasoningIdentity(
        required_setting="on",
        effective_setting="on",
        allowed_options=("off", "on"),
        live_default="on",
        control_source="lmstudio_model_default",
        control_mode="attested_default_without_per_request_override",
    )


def _native_models_response(
    *,
    reasoning: dict[str, object] | None = None,
    loaded_instances: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "models": [
            {
                "type": "llm",
                "key": "google/gemma-4-12b",
                "size_bytes": 7556574286,
                "quantization": {"name": "Q4_K_M"},
                "loaded_instances": loaded_instances
                if loaded_instances is not None
                else [{"id": "google/gemma-4-12b"}],
                "capabilities": {
                    "reasoning": reasoning
                    if reasoning is not None
                    else {"allowed_options": ["off", "on"], "default": "on"}
                },
            }
        ]
    }


def _proof_stub() -> SimpleNamespace:
    return SimpleNamespace(
        request_model="google/gemma-4-12b",
        model_key="google/gemma-4-12b",
        loaded_size_bytes=7556574286,
    )


class _ScriptedCrystallizer:
    def __init__(self, **kwargs) -> None:
        self.model = kwargs["model"]
        self.decoding_config = kwargs["decoding_config"]
        self.decoding_capabilities = kwargs["decoding_capabilities"]
        self.calls: list[CrystallizationInput] = []
        self.closed = False

    @property
    def effective_decoding_configuration(self):
        return self.decoding_config.to_mapping()

    async def generate(self, crystallization_input: CrystallizationInput) -> CrystallizationOutput:
        self.calls.append(crystallization_input)
        return CrystallizationOutput(
            memory_markdown="# Memory\n\nHost-run crystallization evidence.\n",
            state_candidates=(),
        )

    async def aclose(self) -> None:
        self.closed = True


def test_condition_loader_is_strict_and_crystallization_specific(tmp_path: Path) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )

    assert condition.target_id == TARGET_ID
    assert condition.environment.request_model == "google/gemma-4-12b"
    assert condition.decoding_config.to_mapping() == {
        "temperature": 0.0,
        "top_p": 1.0,
        "seed": 7,
    }
    assert condition.fixture_path == FIXTURE_RELATIVE
    assert condition.fixture_revision == FIXTURE_REVISION
    assert condition.case.case_id == "crystallization-baseline"
    assert condition.max_events == 100
    assert condition.reasoning_required_setting == "on"
    assert condition.to_mapping()["execution_kind"] == "off_turn_crystallization"

    serialized = json.dumps(condition.to_mapping(), ensure_ascii=False)
    for ordinary_only in (
        "scenario_ids",
        "continuity_runtime",
        "execution_path",
        "cognitive_budget",
        "budgets",
    ):
        assert ordinary_only not in serialized

    unknown = _condition_mapping()
    unknown["scenario_ids"] = ["response-persona-correction-v1"]
    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match="unknown fields"):
        subject.load_actual_model_crystallization_host_condition(
            _write_condition(tmp_path, unknown)
        )

    missing_reasoning = _condition_mapping()
    del missing_reasoning["reasoning"]
    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match="missing fields"):
        subject.load_actual_model_crystallization_host_condition(
            _write_condition(tmp_path, missing_reasoning)
        )


def test_condition_rejects_non_repo_relative_fixture_and_negative_budget(tmp_path: Path) -> None:
    subject = _subject()

    absolute = _condition_mapping()
    absolute["character_fixture"]["path"] = "/tmp/character"
    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match="relative"):
        subject.load_actual_model_crystallization_host_condition(
            _write_condition(tmp_path, absolute)
        )

    negative = _condition_mapping()
    negative["max_events"] = -1
    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match="max_events"):
        subject.load_actual_model_crystallization_host_condition(
            _write_condition(tmp_path, negative)
        )


def test_live_reasoning_capability_is_attested(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    target = load_actual_model_target(TARGET_PATH)
    monkeypatch.setattr(subject, "load_lm_studio_counter_proof", lambda _: _proof_stub())
    monkeypatch.setattr(
        subject,
        "_fetch_lm_studio_native_models",
        lambda **_: _native_models_response(),
    )

    identity = subject._attest_lm_studio_reasoning(
        condition=condition,
        target=target,
        proof_path=tmp_path / "proof.json",
        api_key=None,
    )

    assert identity.to_mapping() == {
        "format_version": 1,
        "required_setting": "on",
        "effective_setting": "on",
        "allowed_options": ["off", "on"],
        "live_default": "on",
        "control_source": "lmstudio_model_default",
        "control_mode": "attested_default_without_per_request_override",
    }


def test_live_native_models_uses_lm_studio_native_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    requests: list[tuple[str, str | None, float]] = []

    class _Response:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"models": []}'

    def _urlopen(request, *, timeout: float):
        requests.append((request.full_url, request.get_header("Authorization"), timeout))
        return _Response()

    monkeypatch.setattr(subject.urllib.request, "urlopen", _urlopen)

    assert subject._fetch_lm_studio_native_models(
        base_url="http://127.0.0.1:1234/v1",
        api_key="secret",
    ) == {"models": []}
    assert requests == [
        ("http://127.0.0.1:1234/api/v1/models", "Bearer secret", 10)
    ]


def test_live_reasoning_attestation_fails_without_capability(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    target = load_actual_model_target(TARGET_PATH)
    metadata = _native_models_response()
    model = metadata["models"][0]
    assert isinstance(model, dict)
    del model["capabilities"]
    monkeypatch.setattr(subject, "load_lm_studio_counter_proof", lambda _: _proof_stub())
    monkeypatch.setattr(subject, "_fetch_lm_studio_native_models", lambda **_: metadata)

    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match="reasoning capability"):
        subject._attest_lm_studio_reasoning(
            condition=condition,
            target=target,
            proof_path=tmp_path / "proof.json",
            api_key=None,
        )


def test_live_reasoning_attestation_fails_for_unallowed_setting(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    mapping = _condition_mapping()
    mapping["reasoning"] = {"required_setting": "high"}
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, mapping)
    )
    target = load_actual_model_target(TARGET_PATH)
    monkeypatch.setattr(subject, "load_lm_studio_counter_proof", lambda _: _proof_stub())
    monkeypatch.setattr(
        subject,
        "_fetch_lm_studio_native_models",
        lambda **_: _native_models_response(),
    )

    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match="not in LM Studio allowed_options"):
        subject._attest_lm_studio_reasoning(
            condition=condition,
            target=target,
            proof_path=tmp_path / "proof.json",
            api_key=None,
        )


def test_live_reasoning_attestation_fails_for_default_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    target = load_actual_model_target(TARGET_PATH)
    monkeypatch.setattr(subject, "load_lm_studio_counter_proof", lambda _: _proof_stub())
    monkeypatch.setattr(
        subject,
        "_fetch_lm_studio_native_models",
        lambda **_: _native_models_response(
            reasoning={"allowed_options": ["off", "on"], "default": "off"}
        ),
    )

    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match="default does not match"):
        subject._attest_lm_studio_reasoning(
            condition=condition,
            target=target,
            proof_path=tmp_path / "proof.json",
            api_key=None,
        )


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({"models": {}}, "must be a JSON array"),
        (_native_models_response(loaded_instances=[]), "loaded instance"),
        (
            {
                "models": [
                    *_native_models_response()["models"],
                    *_native_models_response()["models"],
                ]
            },
            "exactly one matching request model",
        ),
    ],
)
def test_live_reasoning_attestation_fails_for_ambiguous_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    metadata: dict[str, object],
    message: str,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    target = load_actual_model_target(TARGET_PATH)
    monkeypatch.setattr(subject, "load_lm_studio_counter_proof", lambda _: _proof_stub())
    monkeypatch.setattr(subject, "_fetch_lm_studio_native_models", lambda **_: metadata)

    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError, match=message):
        subject._attest_lm_studio_reasoning(
            condition=condition,
            target=target,
            proof_path=tmp_path / "proof.json",
            api_key=None,
        )


def test_reasoning_failure_precedes_crystallizer_construction(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    monkeypatch.setattr(subject, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: _verification())
    monkeypatch.setattr(
        subject,
        "_attest_lm_studio_serving_target",
        lambda **_: "lm-studio-serving-proof:sha256:" + "a" * 64,
    )
    monkeypatch.setattr(subject, "load_lm_studio_counter_proof", lambda _: _proof_stub())
    monkeypatch.setattr(
        subject,
        "_fetch_lm_studio_native_models",
        lambda **_: {"models": []},
    )

    class NeverConstructed:
        def __init__(self, **_: object) -> None:
            raise AssertionError("crystallizer construction must not follow failed attestation")

    monkeypatch.setattr(subject, "OpenAICompatibleCrystallizer", NeverConstructed)
    with pytest.raises(subject.ActualModelCrystallizationHostRunnerError):
        subject.prepare_actual_model_crystallization_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "verified-by-patched-verifier.gguf",
            serving_proof_path=tmp_path / "proof.json",
        )


def test_prepare_binds_verified_target_fixture_attestation_and_applied_decoding(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    monkeypatch.setattr(subject, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: _verification())
    monkeypatch.setattr(
        subject,
        "_attest_lm_studio_serving_target",
        lambda **_: "lm-studio-serving-proof:sha256:" + "a" * 64,
    )
    monkeypatch.setattr(subject, "_attest_lm_studio_reasoning", lambda **_: _reasoning_identity(subject))

    prepared = subject.prepare_actual_model_crystallization_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "verified-by-patched-verifier.gguf",
        serving_proof_path=tmp_path / "proof.json",
    )
    try:
        target = load_actual_model_target(TARGET_PATH)
        assert prepared.target.target_id == TARGET_ID
        assert prepared.artifact_verification == _verification()
        assert prepared.fixture_root == FIXTURE_ROOT.resolve()
        assert prepared.manifest.character_fixture_id == "actual-model-foundation-v1"
        assert prepared.manifest.character_fixture_revision == FIXTURE_REVISION
        assert prepared.manifest.model_artifact == target.model_artifact_identity
        assert prepared.manifest.tokenizer_identity == target.tokenizer_identity
        assert prepared.manifest.max_events == 100
        assert prepared.manifest.seed == 7
        assert prepared.manifest.reasoning_identity.required_setting == "on"
        assert prepared.manifest.decoding_configuration == (
            ("seed", 7),
            ("temperature", 0.0),
            ("top_p", 1.0),
        )
        assert prepared.manifest.adapter_identity == (
            "relaylm.providers.OpenAICompatibleCrystallizer:v1"
        )
        assert "lm-studio-serving-proof:sha256:" in prepared.manifest.provider_identity
        assert prepared.crystallizer.model == condition.request_model
    finally:
        asyncio.run(prepared.crystallizer.aclose())


def test_prepare_fails_closed_on_fixture_revision_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    mapping = _condition_mapping()
    mapping["character_fixture"]["revision"] = "sha256:" + "0" * 64
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, mapping)
    )
    monkeypatch.setattr(subject, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: _verification())
    monkeypatch.setattr(
        subject,
        "_attest_lm_studio_serving_target",
        lambda **_: "lm-studio-serving-proof:sha256:" + "a" * 64,
    )
    monkeypatch.setattr(subject, "_attest_lm_studio_reasoning", lambda **_: _reasoning_identity(subject))

    with pytest.raises(
        subject.ActualModelCrystallizationHostRunnerError,
        match="fixture revision",
    ):
        subject.prepare_actual_model_crystallization_host_run(
            condition=condition,
            repo_root=REPO_ROOT,
            model_artifact_path=tmp_path / "verified-by-patched-verifier.gguf",
            serving_proof_path=tmp_path / "proof.json",
        )


def test_execute_uses_fresh_workspace_one_pass_and_existing_cry2_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    monkeypatch.setattr(subject, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: _verification())
    monkeypatch.setattr(
        subject,
        "_attest_lm_studio_serving_target",
        lambda **_: "lm-studio-serving-proof:sha256:" + "b" * 64,
    )
    monkeypatch.setattr(subject, "_attest_lm_studio_reasoning", lambda **_: _reasoning_identity(subject))
    monkeypatch.setattr(subject, "OpenAICompatibleCrystallizer", _ScriptedCrystallizer)

    prepared = subject.prepare_actual_model_crystallization_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "verified-by-patched-verifier.gguf",
        serving_proof_path=tmp_path / "proof.json",
    )
    artifact = asyncio.run(
        subject.execute_actual_model_crystallization_host_run(
            prepared=prepared,
            workspace_root=tmp_path / "workspaces",
            artifact_root=tmp_path / "artifacts",
        )
    )

    assert len(prepared.crystallizer.calls) == 1
    assert prepared.crystallizer.closed is True
    assert artifact.case_id == "crystallization-baseline"
    assert artifact.run_id
    path = Path(artifact.artifact_path)
    assert path.is_file()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["run_id"] == artifact.run_id
    assert payload["raw_model"]["memory_markdown"].startswith("# Memory")
    assert payload["manifest"]["execution_kind"] == "off_turn_crystallization"

    workspace = (
        tmp_path
        / "workspaces"
        / condition.condition_id
        / condition.replicate_id
        / condition.case.case_id
    )
    assert (workspace / "memory" / "MEMORY.md").read_text(encoding="utf-8").startswith(
        "# Memory"
    )


def test_execute_rejects_reusing_existing_workspace_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = _subject()
    condition = subject.load_actual_model_crystallization_host_condition(
        _write_condition(tmp_path, _condition_mapping())
    )
    monkeypatch.setattr(subject, "_verify_clean_exact_repo", lambda **_: None)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: _verification())
    monkeypatch.setattr(
        subject,
        "_attest_lm_studio_serving_target",
        lambda **_: "lm-studio-serving-proof:sha256:" + "c" * 64,
    )
    monkeypatch.setattr(subject, "_attest_lm_studio_reasoning", lambda **_: _reasoning_identity(subject))
    monkeypatch.setattr(subject, "OpenAICompatibleCrystallizer", _ScriptedCrystallizer)
    prepared = subject.prepare_actual_model_crystallization_host_run(
        condition=condition,
        repo_root=REPO_ROOT,
        model_artifact_path=tmp_path / "verified-by-patched-verifier.gguf",
        serving_proof_path=tmp_path / "proof.json",
    )
    workspace = (
        tmp_path
        / "workspaces"
        / condition.condition_id
        / condition.replicate_id
        / condition.case.case_id
    )
    workspace.mkdir(parents=True)

    with pytest.raises(Exception, match="workspace must not already exist"):
        asyncio.run(
            subject.execute_actual_model_crystallization_host_run(
                prepared=prepared,
                workspace_root=tmp_path / "workspaces",
                artifact_root=tmp_path / "artifacts",
            )
        )
    assert prepared.crystallizer.calls == []
    assert prepared.crystallizer.closed is True


def test_module_exposes_host_cli_entrypoint() -> None:
    subject = _subject()
    assert callable(subject.main)
