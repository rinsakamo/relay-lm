from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import relaylm.api.openai as openai_api
from relaylm.cognitive import CognitionExecutionMode
from relaylm.providers.openai_compatible import OpenAICompatibleProvider
from relaylm.providers.openai_compatible_two_pass import OpenAICompatibleTwoPassProvider
from relaylm.runtime_assembly import RuntimeAssemblyError, assemble_runtime
from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_config_loader import resolve_runtime_config
from relaylm.server import create_app
from relaylm.two_pass_turn import CognitionExecutionRuntime


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _base_config(runtime: str = "") -> str:
    return f"""\
format_version: 1
character:
  directory: /characters/relm
provider:
  adapter: openai_compatible
  base_url: http://127.0.0.1:1234/v1
  model: model-id
{runtime}"""


def test_release_config_defaults_to_two_pass_without_inventing_pass_controls() -> None:
    resolved = resolve_runtime_config(
        environ={
            "RELAYLM_CHARACTER_DIR": "/characters/relm",
            "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "RELAYLM_PROVIDER_MODEL": "model-id",
        }
    )

    cognition = resolved.config.runtime.cognition
    assert cognition.mode is CognitionExecutionMode.TWO_PASS
    assert cognition.pass1.reasoning_mode is None
    assert cognition.pass1.temperature is None
    assert cognition.pass2.reasoning_mode is None
    assert cognition.pass2.temperature is None


def test_release_config_can_select_explicit_single_pass(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "runtime.yaml",
        _base_config(
            """\
runtime:
  cognition:
    mode: single_pass
"""
        ),
    )

    resolved = resolve_runtime_config(config_path=path, environ={})

    assert resolved.config.runtime.cognition.mode is CognitionExecutionMode.SINGLE_PASS


def test_two_pass_assembly_constructs_two_pass_provider_and_execution_runtime() -> None:
    resolved = resolve_runtime_config(
        environ={
            "RELAYLM_CHARACTER_DIR": "/characters/relm",
            "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "RELAYLM_PROVIDER_MODEL": "model-id",
        }
    )

    assembly = assemble_runtime(resolved)

    assert assembly.cognition_mode is CognitionExecutionMode.TWO_PASS
    assert isinstance(assembly.provider, OpenAICompatibleTwoPassProvider)
    assert isinstance(assembly.cognition_execution_runtime, CognitionExecutionRuntime)
    assert assembly.pass1_request is resolved.config.runtime.cognition.pass1
    assert assembly.pass2_request is resolved.config.runtime.cognition.pass2
    assert assembly.app_kwargs()["cognition_mode"] is CognitionExecutionMode.TWO_PASS


def test_explicit_single_pass_assembly_preserves_legacy_provider(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "runtime.yaml",
        _base_config(
            """\
runtime:
  cognition:
    mode: single_pass
"""
        ),
    )
    resolved = resolve_runtime_config(config_path=path, environ={})

    assembly = assemble_runtime(resolved)

    assert assembly.cognition_mode is CognitionExecutionMode.SINGLE_PASS
    assert isinstance(assembly.provider, OpenAICompatibleProvider)
    assert not isinstance(assembly.provider, OpenAICompatibleTwoPassProvider)
    assert assembly.cognition_execution_runtime is None


@pytest.mark.parametrize("mode", ["auto", "shadow_two_pass"])
def test_unresolved_or_evidence_only_mode_fails_before_ordinary_serving(
    tmp_path: Path,
    mode: str,
) -> None:
    path = _write(
        tmp_path / "runtime.yaml",
        _base_config(
            f"""\
runtime:
  cognition:
    mode: {mode}
"""
        ),
    )
    resolved = resolve_runtime_config(config_path=path, environ={})

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught.value.field == "runtime.cognition.mode"


def test_existing_single_pass_cognitive_budget_is_not_guessed_into_two_pass(
    tmp_path: Path,
) -> None:
    path = _write(
        tmp_path / "runtime.yaml",
        _base_config(
            """\
runtime:
  cognitive_budget:
    total:
      model_context_window: 8192
      reserved_output_tokens: 1024
    policy:
      initial_plan:
        canonical_state: {max_items: 8, floor_items: 2}
        working_context: {max_items: 4, floor_items: 1, max_chars: 2000, floor_chars: 500}
        retrieved_memory: {max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}
        event_evidence: {max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}
      steps: []
    token_counter:
      capability: test.exact
      mode: exact
"""
        ),
    )
    resolved = resolve_runtime_config(config_path=path, environ={})

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught.value.field == "runtime.cognitive_budget"
    assert "two-pass" in str(caught.value).lower()


def test_buffered_openai_route_dispatches_to_two_pass_runtime(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_two_pass(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(response="ok")

    async def forbid_single_pass(**kwargs):  # pragma: no cover - must not run
        raise AssertionError(kwargs)

    monkeypatch.setattr(openai_api, "run_user_turn_two_pass", fake_two_pass)
    monkeypatch.setattr(openai_api, "run_user_turn", forbid_single_pass)
    runtime = CognitionExecutionRuntime()
    provider = SimpleNamespace(aclose=None)
    app = create_app(
        character=SimpleNamespace(),
        provider=provider,
        cognition_mode=CognitionExecutionMode.TWO_PASS,
        cognition_execution_runtime=runtime,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "client-label",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert response.json()["choices"][0]["message"]["content"] == "ok"
    assert captured["execution_runtime"] is runtime


def test_streaming_openai_route_dispatches_to_two_pass_runtime(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_two_pass_streaming(**kwargs):
        captured.update(kwargs)
        await kwargs["emit_response_delta"]("ok")
        return SimpleNamespace(response="ok")

    async def forbid_single_pass(**kwargs):  # pragma: no cover - must not run
        raise AssertionError(kwargs)

    monkeypatch.setattr(
        openai_api,
        "run_user_turn_two_pass_streaming",
        fake_two_pass_streaming,
    )
    monkeypatch.setattr(openai_api, "run_user_turn_streaming", forbid_single_pass)
    runtime = CognitionExecutionRuntime()
    provider = SimpleNamespace(aclose=None, stream_generate_conversation=lambda: None)
    app = create_app(
        character=SimpleNamespace(),
        provider=provider,
        cognition_mode=CognitionExecutionMode.TWO_PASS,
        cognition_execution_runtime=runtime,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "client-label",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )

    assert response.status_code == 200
    assert "data: [DONE]" in response.text
    assert captured["execution_runtime"] is runtime
