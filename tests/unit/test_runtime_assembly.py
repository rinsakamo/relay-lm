from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import relaylm.api.openai as openai_api
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.cognitive import CognitiveInput
from relaylm.cognitive_profile import CognitiveProfileRegistry, CognitiveProfileRuntime
from relaylm.continuity import ContinuityContext
from relaylm.runtime_assembly import (
    RuntimeAssemblyError,
    TokenCounterCapability,
    assemble_runtime,
)
from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_config_loader import resolve_runtime_config
from relaylm.server import create_app
from relaylm.storage.cognitive_package import CognitivePackageDirectory
from relaylm.turn import ContinuityRuntime, EventRetrievalBudget, MemoryRetrievalBudget


class _ExactCounter:
    def count_serialized_input(
        self,
        cognitive_input: CognitiveInput,
    ) -> SerializedInputTokenCount:
        del cognitive_input
        return SerializedInputTokenCount(
            total_input_tokens=100,
            required_input_framing_tokens=10,
            mode=TokenCountMode.EXACT,
        )


class _StreamingProviderStub:
    async def generate(self, cognitive_input: CognitiveInput):  # pragma: no cover
        raise AssertionError(cognitive_input)

    async def stream_generate(
        self,
        cognitive_input: CognitiveInput,
        emit_response_delta,
    ):  # pragma: no cover
        raise AssertionError((cognitive_input, emit_response_delta))


def _write(path: Path, body: str) -> Path:
    path.write_text(body, encoding="utf-8")
    return path


def _base_config(runtime: str = "") -> str:
    return f"""\
format_version: 1
profiles:
  - name: relm
    root: /characters/relm
provider:
  adapter: openai_compatible
  base_url: http://127.0.0.1:1234/v1
  model: model-id
{runtime}"""


def _cognitive_budget_yaml(*, include_memory: bool = False) -> str:
    memory = """
  memory_retrieval:
    max_chunks: 2
    max_chars: 800
""" if include_memory else ""
    return f"""\
runtime:
  cognition:
    mode: single_pass{memory}
  cognitive_budget:
    total:
      model_context_window: 8192
      reserved_output_tokens: 1024
    policy:
      initial_plan:
        canonical_state:
          max_items: 8
          floor_items: 2
        working_context:
          max_items: 4
          floor_items: 1
          max_chars: 2000
          floor_chars: 500
        retrieved_memory:
          max_items: 4
          floor_items: 0
          max_chars: 1600
          floor_chars: 0
        event_evidence:
          max_items: 4
          floor_items: 0
          max_chars: 1600
          floor_chars: 0
      steps:
        - layer: retrieved_memory
          target:
            max_items: 2
            floor_items: 0
            max_chars: 800
            floor_chars: 0
    token_counter:
      capability: test.exact
      mode: exact
"""


def _registry(
    provider: object,
    *,
    continuity: ContinuityRuntime | None = None,
) -> CognitiveProfileRegistry:
    return CognitiveProfileRegistry(
        (
            CognitiveProfileRuntime(
                name="relm",
                package=CognitivePackageDirectory("/characters/relm"),
                provider=provider,
                physical_model="model-id",
                continuity_runtime=continuity,
            ),
        )
    )


def test_assemble_basic_resolved_config_constructs_profile_and_provider() -> None:
    resolved = resolve_runtime_config(
        environ={
            "RELAYLM_PROFILE_NAME": "relm",
            "RELAYLM_PROFILE_ROOT": "/characters/relm",
            "RELAYLM_PROVIDER_BASE_URL": "http://127.0.0.1:1234/v1",
            "RELAYLM_PROVIDER_MODEL": "model-id",
            "RELAYLM_PROVIDER_API_KEY": "process-secret",
        }
    )

    assembly = assemble_runtime(resolved)
    profile = assembly.profiles.resolve("relm")

    assert profile is not None
    assert profile.package.root == Path("/characters/relm")
    assert profile.provider.base_url == "http://127.0.0.1:1234/v1"
    assert profile.provider.model == "model-id"
    assert profile.provider.api_key == "process-secret"
    assert profile.physical_model == "model-id"
    assert assembly.memory_budget is None
    assert assembly.event_budget is None
    assert profile.continuity_runtime is None
    assert assembly.cognitive_budget is None
    assert "process-secret" not in repr(assembly)


def test_assemble_explicit_retrieval_and_continuity_use_existing_owner_types(
    tmp_path: Path,
) -> None:
    config_path = _write(
        tmp_path / "runtime.yaml",
        _base_config(
            """\
runtime:
  memory_retrieval:
    max_chunks: 3
    max_chars: 900
  event_retrieval:
    max_events: 4
    max_chars: 1200
  continuity:
    max_items: 5
    lifetime_revisions: 6
"""
        ),
    )
    resolved = resolve_runtime_config(config_path=config_path, environ={})

    assembly = assemble_runtime(resolved)
    profile = assembly.profiles.resolve("relm")

    assert profile is not None
    assert assembly.memory_budget == MemoryRetrievalBudget(max_chunks=3, max_chars=900)
    assert assembly.event_budget == EventRetrievalBudget(max_events=4, max_chars=1200)
    assert isinstance(profile.continuity_runtime, ContinuityRuntime)
    assert profile.continuity_runtime.context.max_items == 5
    assert profile.continuity_runtime.context.revision == 0
    assert profile.continuity_runtime.context.items == ()
    assert profile.continuity_runtime.lifetime_revisions == 6


def test_assemble_cognitive_budget_resolves_declared_counter_capability(
    tmp_path: Path,
) -> None:
    config_path = _write(
        tmp_path / "runtime.yaml",
        _base_config(_cognitive_budget_yaml()),
    )
    resolved = resolve_runtime_config(config_path=config_path, environ={})
    counter = _ExactCounter()

    assembly = assemble_runtime(
        resolved,
        token_counter_capabilities={
            "test.exact": TokenCounterCapability(
                mode=TokenCountMode.EXACT,
                factory=lambda provider: counter,
            )
        },
    )

    assert assembly.cognitive_budget is not None
    assert assembly.cognitive_budget.total.model_context_window == 8192
    assert assembly.cognitive_budget.total.reserved_output_tokens == 1024
    assert assembly.cognitive_budget.token_counter is counter
    assert assembly.memory_budget is None
    assert assembly.event_budget is None


def test_missing_token_counter_capability_fails_before_runtime_use(tmp_path: Path) -> None:
    config_path = _write(
        tmp_path / "runtime.yaml",
        _base_config(_cognitive_budget_yaml()),
    )
    resolved = resolve_runtime_config(config_path=config_path, environ={})

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved)

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "runtime.cognitive_budget.token_counter.capability"


def test_token_counter_mode_mismatch_fails_closed(tmp_path: Path) -> None:
    config_path = _write(
        tmp_path / "runtime.yaml",
        _base_config(_cognitive_budget_yaml()),
    )
    resolved = resolve_runtime_config(config_path=config_path, environ={})

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(
            resolved,
            token_counter_capabilities={
                "test.exact": TokenCounterCapability(
                    mode=TokenCountMode.CONSERVATIVE_ESTIMATE,
                    factory=lambda provider: _ExactCounter(),
                )
            },
        )

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "runtime.cognitive_budget.token_counter.mode"


def test_overlapping_direct_retrieval_and_cognitive_budget_fails_at_assembly(
    tmp_path: Path,
) -> None:
    config_path = _write(
        tmp_path / "runtime.yaml",
        _base_config(_cognitive_budget_yaml(include_memory=True)),
    )
    resolved = resolve_runtime_config(config_path=config_path, environ={})

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(
            resolved,
            token_counter_capabilities={
                "test.exact": TokenCounterCapability(
                    mode=TokenCountMode.EXACT,
                    factory=lambda provider: _ExactCounter(),
                )
            },
        )

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught.value.field == "runtime.cognitive_budget"
    assert "retrieval" in str(caught.value).lower()


def test_counter_factory_failure_is_reported_as_capability_unavailable(
    tmp_path: Path,
) -> None:
    config_path = _write(
        tmp_path / "runtime.yaml",
        _base_config(_cognitive_budget_yaml()),
    )
    resolved = resolve_runtime_config(config_path=config_path, environ={})

    def fail_factory(provider):
        del provider
        raise RuntimeError("tokenizer internals must not escape")

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(
            resolved,
            token_counter_capabilities={
                "test.exact": TokenCounterCapability(
                    mode=TokenCountMode.EXACT,
                    factory=fail_factory,
                )
            },
        )

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "runtime.cognitive_budget.token_counter.capability"
    assert "tokenizer internals" not in str(caught.value)


def test_buffered_openai_route_carries_all_assembled_turn_controls(monkeypatch) -> None:
    memory = MemoryRetrievalBudget(max_chunks=2, max_chars=800)
    event = EventRetrievalBudget(max_events=3, max_chars=900)
    continuity = ContinuityRuntime(
        context=ContinuityContext(max_items=4),
        lifetime_revisions=5,
    )
    captured: dict[str, object] = {}

    async def fake_run_user_turn(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(response="ok")

    monkeypatch.setattr(openai_api, "run_user_turn", fake_run_user_turn)
    provider = _StreamingProviderStub()
    app = create_app(
        profiles=_registry(provider, continuity=continuity),
        memory_budget=memory,
        event_budget=event,
        cognitive_budget=None,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relm",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )

    assert response.status_code == 200
    assert captured["memory_budget"] is memory
    assert captured["event_budget"] is event
    assert captured["continuity_runtime"] is continuity
    assert captured["cognitive_budget"] is None


def test_streaming_openai_route_carries_same_turn_controls(monkeypatch) -> None:
    memory = MemoryRetrievalBudget(max_chunks=2, max_chars=800)
    event = EventRetrievalBudget(max_events=3, max_chars=900)
    captured: dict[str, object] = {}

    async def fake_run_user_turn_streaming(**kwargs):
        captured.update(kwargs)
        await kwargs["emit_response_delta"]("ok")
        return SimpleNamespace(response="ok")

    monkeypatch.setattr(openai_api, "run_user_turn_streaming", fake_run_user_turn_streaming)
    provider = _StreamingProviderStub()
    app = create_app(
        profiles=_registry(provider),
        memory_budget=memory,
        event_budget=event,
        cognitive_budget=None,
    )

    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relm",
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
            },
        )

    assert response.status_code == 200
    assert "data: [DONE]" in response.text
    assert captured["memory_budget"] is memory
    assert captured["event_budget"] is event
    assert captured["continuity_runtime"] is None
    assert captured["cognitive_budget"] is None
