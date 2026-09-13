from __future__ import annotations

import asyncio
import importlib
import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from relaylm.actual_model_crystallization import (
    ActualModelCrystallizationReview,
    CrystallizationQualityObservation,
)
from relaylm.actual_model_llama_cpp import attest_llama_cpp_runtime
from relaylm.actual_model_llama_cpp_thinking import LlamaCppThinkingChatInputCounter
from relaylm.actual_model_targets import load_actual_model_target
from relaylm.crystallization import CrystallizationInput
from relaylm.identity import Identity
from relaylm.providers.llama_cpp_crystallization import (
    LlamaCppOpenAICompatibleCrystallizer,
)
from relaylm.providers.llama_cpp_reasoning import (
    LlamaCppReasoningCapabilityAttestation,
)
from relaylm.providers.openai_compatible import ProviderProtocolError
from relaylm.providers.openai_compatible_crystallization import (
    WIRE_SCHEMA,
)
from relaylm.providers.openai_compatible_decoding import (
    OpenAICompatibleDecodingCapabilities,
    OpenAICompatibleDecodingConfig,
)
from relaylm.state import CanonicalState


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = REPO_ROOT / "evaluation/actual_model/characters/crystallization-quality-v1"
TARGET_PATH = REPO_ROOT / (
    "evaluation/actual_model/targets/"
    "gemma-4-12b-it-q4-k-m-lmstudio-community-v1.json"
)
MODEL = "gemma-local"
MODEL_PATH = "/models/gemma.gguf"
RUNTIME_REVISION = "c841aeeb8bb2fe417038dadfa9b007cf1a9ef950"


def _runtime():
    return attest_llama_cpp_runtime(
        props={
            "build_info": f"llama-server build 10874 {RUNTIME_REVISION}",
            "model_alias": MODEL,
            "model_ftype": "Q4_K_M",
            "model_path": MODEL_PATH,
            "chat_template": "{{ messages }}",
            "total_slots": 1,
            "default_generation_settings": {"n_ctx": 8192},
        },
        slots=[{"id": 0, "n_ctx": 8192}],
        upstream_revision=RUNTIME_REVISION,
        expected_build_info=f"llama-server build 10874 {RUNTIME_REVISION}",
        expected_model_alias=MODEL,
        expected_model_path=MODEL_PATH,
        artifact_sha256="ab" * 32,
        context_shift_enabled=False,
    )


def _input() -> CrystallizationInput:
    from relaylm.events import Event
    from relaylm.state import StateRecord

    return CrystallizationInput(
        identity=Identity("# Aoi\nBe precise."),
        state=CanonicalState(
            states=(
                StateRecord(
                    state_id="state-name",
                    state_class="user.identity",
                    key="name",
                    value="Aoi",
                    sources=("evt-1",),
                ),
            )
        ),
        events=(
            Event.create(
                type="message",
                actor="user",
                payload={"content": "名前はAoiです。"},
                event_id="evt-1",
                timestamp="2026-09-13T00:00:00+00:00",
            ),
        ),
        prior_memory="# Memory\n",
    )


def _wire() -> dict[str, object]:
    return {
        "memory_units": [
            {
                "heading": "Name",
                "content": "The name is Aoi.",
                "temporal_scope": "current",
                "sources": [{"kind": "event", "reference_id": "evt-1"}],
            }
        ],
        "state_candidates": [],
    }


def _provider(
    *,
    transport: httpx.MockTransport,
    counter_payloads: list[dict[str, object]],
    observation_root: Path | None = None,
) -> LlamaCppOpenAICompatibleCrystallizer:
    def post_json(_: str, payload: dict[str, object], __: str | None) -> object:
        counter_payloads.append(dict(payload))
        return {"input_tokens": 12 if any(item["content"] for item in payload["messages"]) else 4}

    counter = LlamaCppThinkingChatInputCounter(
        base_url="http://127.0.0.1:1234/v1",
        runtime_identity=_runtime(),
        post_json=post_json,
    )
    return LlamaCppOpenAICompatibleCrystallizer(
        base_url="http://127.0.0.1:1234/v1",
        model=MODEL,
        decoding_config=OpenAICompatibleDecodingConfig(
            temperature=0,
            top_p=1,
        ),
        decoding_capabilities=OpenAICompatibleDecodingCapabilities(
            supported_controls=frozenset({"temperature", "top_p"})
        ),
        input_counter=counter,
        llama_cpp_reasoning_capability=LlamaCppReasoningCapabilityAttestation(
            request_model=MODEL,
            enable_thinking_supported=True,
        ),
        http_client=httpx.AsyncClient(transport=transport),
        observation_root=observation_root,
    )


def test_provider_preserves_schema_reasoning_and_same_body_for_counter_and_generation(
    tmp_path: Path,
) -> None:
    generation_bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        generation_bodies.append(body)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {"content": json.dumps(_wire())},
                    }
                ]
            },
        )

    counted: list[dict[str, object]] = []
    provider = _provider(
        transport=httpx.MockTransport(handler),
        counter_payloads=counted,
        observation_root=tmp_path / "observations",
    )
    output = asyncio.run(provider.generate(_input()))
    asyncio.run(provider._client.aclose())

    assert output.memory_units[0].heading == "Name"
    assert len(generation_bodies) == 1
    body = generation_bodies[0]
    assert body["reasoning_effort"] == "none"
    assert body["stream"] is False
    assert body["response_format"] == {
        "type": "json_schema",
        "json_schema": {
            "name": "relaylm_crystallization_output",
            "strict": True,
            "schema": WIRE_SCHEMA,
        },
    }
    assert len(counted) == 2
    assert counted[0]["reasoning_effort"] == body["reasoning_effort"]
    assert counted[0]["stream"] == body["stream"]
    assert counted[0]["response_format"] == body["response_format"]
    assert provider.generation_request_count == 1
    assert provider.input_counter_request_count == 2
    assert len(provider.input_count_artifacts) == 1
    assert len(provider.completion_artifacts) == 1


def test_provider_native_schema_failure_has_no_plain_text_fallback() -> None:
    requests: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        return httpx.Response(400, json={"error": {"message": "schema unsupported"}})

    counted: list[dict[str, object]] = []
    provider = _provider(
        transport=httpx.MockTransport(handler),
        counter_payloads=counted,
    )
    with pytest.raises(ProviderProtocolError):
        asyncio.run(provider.generate(_input()))
    asyncio.run(provider._client.aclose())
    assert requests == ["/v1/chat/completions"]
    assert provider.generation_request_count == 1


def test_provider_does_not_use_lm_studio_and_reasoning_attestation_is_fail_closed() -> None:
    module = importlib.import_module("relaylm.providers.llama_cpp_crystallization")
    assert "lm_studio" not in module.__dict__
    with pytest.raises(ValueError):
        LlamaCppOpenAICompatibleCrystallizer(
            base_url="http://127.0.0.1:1234/v1",
            model=MODEL,
            input_counter=LlamaCppThinkingChatInputCounter(
                base_url="http://127.0.0.1:1234/v1",
                runtime_identity=_runtime(),
                post_json=lambda *_: {"input_tokens": 1},
            ),
            llama_cpp_reasoning_capability=LlamaCppReasoningCapabilityAttestation(
                request_model="other-model",
                enable_thinking_supported=True,
            ),
        )


def test_host_delegates_existing_core_once_and_retains_raw_and_deterministic_evidence(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = importlib.import_module("relaylm.actual_model_crystallization_llama_cpp")
    target = load_actual_model_target(TARGET_PATH)
    model_file = tmp_path / "model.gguf"
    model_file.write_bytes(b"fake-model")
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    log_path = artifact_root / "server.log"
    log_path.write_text("owned server log", encoding="utf-8")
    launch = (
            "llama-server -m "
            f"{model_file} --host 127.0.0.1 --port 1234 -ngl 999 -c 8192 -np 1 "
            f"--no-context-shift -lv 4 --log-timestamps --log-file {log_path}"
    )
    monkeypatch.setattr(subject, "_verify_clean_exact_repo", lambda _: ("a" * 40, "b" * 40))
    monkeypatch.setattr(subject, "_frozen_core_fingerprint", lambda _: "sha256:" + "c" * 64)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: SimpleNamespace(
        target_id=target.target_id,
        target_revision=target.revision,
        artifact_size_bytes=target.artifact_size_bytes,
        artifact_sha256=target.artifact_sha256,
        to_mapping=lambda: {"artifact_sha256": target.artifact_sha256},
    ))
    monkeypatch.setattr(subject, "character_fixture_revision", lambda _: "sha256:" + "d" * 64)
    monkeypatch.setattr(subject, "_read_fixture_revision", lambda _: "sha256:" + "d" * 64)
    monkeypatch.setattr(subject, "attest_llama_cpp_runtime", lambda **_: _runtime())
    monkeypatch.setattr(
        subject,
        "_get_json",
        lambda _client, url, _label: (
            {"status": "ok"}
            if url.endswith("/health")
            else {"data": [{"id": MODEL}]}
            if url.endswith("/models")
            else {
                "build_info": "llama-server build 10874 c841aeeb8bb2fe417038dadfa9b007cf1a9ef950",
                "model_alias": MODEL,
                "model_path": MODEL_PATH,
                "model_ftype": "Q4_K_M",
                "chat_template": "{{ messages }}",
                "total_slots": 1,
                "default_generation_settings": {"n_ctx": 8192},
            }
            if url.endswith("/props")
            else [{"id": 0, "n_ctx": 8192}]
        ),
    )
    monkeypatch.setattr(subject, "prepare_character_fixture_workspace", lambda **_: SimpleNamespace(
        load_memory_markdown=lambda: "# Memory\n",
        load_config=lambda: SimpleNamespace(),
        load_identity=lambda: Identity("# Aoi"),
    ))
    calls: list[str] = []

    async def fake_run(**kwargs):
        calls.append("run_actual_model_crystallization")
        return SimpleNamespace(
            run_id="run-id",
            to_mapping=lambda: {},
            manifest=kwargs["manifest"],
            case=kwargs["case"],
            input=SimpleNamespace(),
            raw_model=SimpleNamespace(),
            deterministic=SimpleNamespace(),
        )

    monkeypatch.setattr(subject, "run_actual_model_crystallization", fake_run)
    monkeypatch.setattr(subject, "write_actual_model_crystallization_evidence", lambda **_: tmp_path / "evidence.json")
    monkeypatch.setattr(subject, "_schema_digest", lambda: "sha256:" + "e" * 64)
    prepared = subject.prepare_llama_cpp_crystallization_host_run(
        repo_root=REPO_ROOT,
        provider_base_url="http://127.0.0.1:1234/v1",
        request_model=MODEL,
        artifact_path=model_file,
        llama_upstream_revision=RUNTIME_REVISION,
        llama_version="llama-server build 10874",
        expected_build_number=10874,
        expected_context_window=8192,
        expected_slots=1,
        context_shift_disabled=True,
        gpu_identity="RTX fake",
        gpu_offload_args="-ngl 999",
        launch_args=launch,
        server_log_path=log_path,
        workspace_root=tmp_path / "workspace",
        artifact_root=artifact_root,
    )
    result = asyncio.run(subject.execute_llama_cpp_crystallization_host_run(prepared=prepared))
    assert calls == ["run_actual_model_crystallization"]
    assert result.run_id == "run-id"
    assert prepared.crystallizer.generation_request_count == 0


def test_host_rejects_runtime_target_context_slot_and_fixture_mismatches(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    subject = importlib.import_module("relaylm.actual_model_crystallization_llama_cpp")
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    log_path = artifact_root / "server.log"
    log_path.write_text("log", encoding="utf-8")
    model_file = tmp_path / "model.gguf"
    model_file.write_bytes(b"model")
    common = {
        "repo_root": REPO_ROOT,
        "provider_base_url": "http://127.0.0.1:1234/v1",
        "request_model": MODEL,
        "artifact_path": model_file,
        "llama_upstream_revision": RUNTIME_REVISION,
        "llama_version": "llama-server build 10874",
        "expected_build_number": 10874,
        "expected_context_window": 8192,
        "expected_slots": 1,
        "context_shift_disabled": True,
        "gpu_identity": "RTX fake",
        "gpu_offload_args": "-ngl 999",
        "launch_args": (
                f"llama-server -m {model_file} --host 127.0.0.1 --port 1234 "
                f"-ngl 999 -c 8192 -np 1 --no-context-shift -lv 4 "
                f"--log-timestamps --log-file {log_path}"
        ),
        "server_log_path": log_path,
        "workspace_root": tmp_path / "workspace",
        "artifact_root": artifact_root,
    }
    monkeypatch.setattr(subject, "_verify_clean_exact_repo", lambda _: ("a" * 40, "b" * 40))
    monkeypatch.setattr(subject, "_frozen_core_fingerprint", lambda _: "sha256:" + "c" * 64)
    monkeypatch.setattr(subject, "character_fixture_revision", lambda _: "sha256:" + "d" * 64)
    monkeypatch.setattr(subject, "_read_fixture_revision", lambda _: "sha256:" + "d" * 64)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: SimpleNamespace(
        target_id="wrong", target_revision="wrong", artifact_size_bytes=1,
        artifact_sha256="ab" * 32, to_mapping=lambda: {},
    ))
    with pytest.raises(subject.LlamaCppCrystallizationHostError, match="canonical current GGUF target"):
        subject.prepare_llama_cpp_crystallization_host_run(
            **common,
            target_path=tmp_path / "wrong-target.json",
        )

    common["target_path"] = subject.TARGET_PATH

    def invoke(**overrides: object) -> object:
        return subject.prepare_llama_cpp_crystallization_host_run(
            **{**common, **overrides}
        )

    def valid_get_json(_client: object, url: str, _label: str) -> object:
        if url.endswith("/health"):
            return {"status": "ok"}
        if url.endswith("/models"):
            return {"data": [{"id": MODEL}]}
        if url.endswith("/props"):
            return {
                "build_info": "llama-server build 10874",
                "model_alias": MODEL,
                "model_path": MODEL_PATH,
                "model_ftype": "Q4_K_M",
                "chat_template": "{{ messages }}",
                "total_slots": 1,
                "default_generation_settings": {"n_ctx": 8192},
            }
        return [{"id": 0, "n_ctx": 8192}]

    monkeypatch.setattr(subject, "_get_json", valid_get_json)
    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: SimpleNamespace(
        target_id=load_actual_model_target(TARGET_PATH).target_id,
        target_revision=load_actual_model_target(TARGET_PATH).revision,
        artifact_size_bytes=load_actual_model_target(TARGET_PATH).artifact_size_bytes,
        artifact_sha256=load_actual_model_target(TARGET_PATH).artifact_sha256,
        to_mapping=lambda: {},
    ))
    monkeypatch.setattr(subject, "attest_llama_cpp_runtime", lambda **_: _runtime())

    with pytest.raises(subject.LlamaCppCrystallizationHostError, match="context window"):
        invoke(expected_context_window=4096)
    with pytest.raises(subject.LlamaCppCrystallizationHostError, match="exactly one slot"):
        invoke(expected_slots=2)
    with pytest.raises(subject.LlamaCppCrystallizationHostError, match="context shift"):
        invoke(context_shift_disabled=False)

    def fail_artifact(**_: object) -> object:
        raise ValueError("artifact mismatch")

    monkeypatch.setattr(subject, "verify_actual_model_artifact", fail_artifact)
    with pytest.raises(subject.LlamaCppCrystallizationHostError, match="cannot verify current"):
        invoke()

    monkeypatch.setattr(subject, "verify_actual_model_artifact", lambda **_: SimpleNamespace(
        target_id=load_actual_model_target(TARGET_PATH).target_id,
        target_revision=load_actual_model_target(TARGET_PATH).revision,
        artifact_size_bytes=load_actual_model_target(TARGET_PATH).artifact_size_bytes,
        artifact_sha256=load_actual_model_target(TARGET_PATH).artifact_sha256,
        to_mapping=lambda: {},
    ))

    def fail_runtime(**_: object) -> object:
        raise ValueError("runtime mismatch")

    monkeypatch.setattr(subject, "attest_llama_cpp_runtime", fail_runtime)
    with pytest.raises(subject.LlamaCppCrystallizationHostError, match="runtime attestation"):
        invoke()

    monkeypatch.setattr(subject, "attest_llama_cpp_runtime", lambda **_: _runtime())
    monkeypatch.setattr(subject, "character_fixture_revision", lambda _: "sha256:" + "e" * 64)
    with pytest.raises(subject.LlamaCppCrystallizationHostError, match="fixture revision"):
        invoke()


def test_transaction_and_wrapper_have_zero_real_calls_and_wrapper_uses_fresh_roots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tx = importlib.import_module(
        "relaylm.actual_model_crystallization_llama_cpp_transaction"
    )
    wrapper = importlib.import_module("tools.v1_crystallization_llama_cpp_wsl")
    calls = {"server": 0, "host": 0}
    monkeypatch.setattr(tx, "_require_clean_repo", lambda _: None)
    monkeypatch.setattr(tx, "_git_identity", lambda _: ("a" * 40, "b" * 40))
    monkeypatch.setattr(tx, "_require_current_origin", lambda origin, port: tx.EXPECTED_ORIGIN)
    monkeypatch.setattr(tx, "_port_is_free", lambda *_: False)
    monkeypatch.setattr(tx, "_invoke_crystallization_host", lambda **_: calls.__setitem__("host", 1))
    rc = tx.main([
        "--repo-root", str(tmp_path / "repo"),
        "--workspace-root", str(tmp_path / "workspace"),
        "--artifact-root", str(tmp_path / "artifacts"),
    ])
    assert rc == 3
    assert calls == {"server": 0, "host": 0}
    summary = json.loads((tmp_path / "artifacts" / tx.TRANSACTION_SUMMARY_FILENAME).read_text())
    assert summary["server_launch_count"] == 0
    assert summary["provider_request_count"] == 0
    assert summary["crystallization_generation_count"] == 0

    operator_home = tmp_path / "operator-home"
    operator_home.mkdir()
    monkeypatch.setenv("HOME", str(operator_home))
    observed: list[dict[str, object]] = []

    def fake_run(command, *, cwd, env, check):
        observed.append({"command": command, "cwd": cwd, "env": env})
        assert command[1:3] == ["-m", wrapper.INNER_TRANSACTION]
        assert "llama-server" not in command
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(wrapper.subprocess, "run", fake_run)
    assert wrapper.main([]) == 0
    assert len(observed) == 1
    runtime_root = Path(observed[0]["env"]["HOME"]).parent
    assert runtime_root.is_relative_to(Path("/tmp"))
    shutil.rmtree(runtime_root)


def test_registry_target_is_distinct_and_core_fingerprint_stays_frozen() -> None:
    registry = json.loads(
        (REPO_ROOT / ".ai/physical/llama_cpp_targets.json").read_text()
    )
    assert registry["targets"]["v1:crystallization"]["module"] == (
        "tools.v1_crystallization_llama_cpp_wsl"
    )
    assert registry["targets"]["v1:crystallization"]["module"] != registry["targets"]["v1:stage-r"]["module"]
    expected = json.loads(
        (REPO_ROOT / "evaluation/actual_model/qualifications/core-semantic-v1.json").read_text()
    )["expected_fingerprint"]
    from tools.repository_authority import load_declarations, qualification_fingerprint

    assert qualification_fingerprint(
        REPO_ROOT,
        load_declarations(REPO_ROOT),
        roots=("crystallization", "runtime_configuration"),
    ) == expected == "sha256:18e7c1a1496ecc077adcb0b50acaedcd9ce84685c0519e7b4170fff6af7125cb"


def test_retained_evidence_run_id_can_feed_current_cry2_review_without_generation() -> None:
    observations = tuple(
        CrystallizationQualityObservation(axis=axis, outcome="not_rated")
        for axis in (
            "durable_information_selection",
            "state_taxonomy_key_normalization",
            "transient_durable_discipline",
            "correction_supersession_preservation",
            "temporal_provenance_fidelity",
            "memory_organization_readability",
            "semantic_stability",
        )
    )
    review = ActualModelCrystallizationReview(
        reviewer_identity="cry2-test",
        evidence_run_ids=("retained-run",),
        case_id="crystallization-consolidation-quality-v1",
        case_version="1",
        observations=observations,
    )
    assert review.evidence_run_ids == ("retained-run",)


def test_existing_lm_studio_and_stage_r_modules_remain_their_current_modules() -> None:
    lm = importlib.import_module("relaylm.actual_model_crystallization_host_runner")
    stage = importlib.import_module("relaylm.actual_model_stage_r_llama_cpp")
    assert lm.__name__ == "relaylm.actual_model_crystallization_host_runner"
    assert stage.__name__ == "relaylm.actual_model_stage_r_llama_cpp"
