from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

import relaylm.api.openai as openai_api
from relaylm.budget_enforcement import SerializedInputTokenCount, TokenCountMode
from relaylm.budget_runtime import TwoPassCognitiveBudgetRuntimeConfig
from relaylm.runtime_assembly import (
    RuntimeAssemblyError,
    TokenCounterCapability,
    assemble_runtime,
)
from relaylm.runtime_config import RuntimeConfigErrorCode
from relaylm.runtime_config_loader import resolve_runtime_config
from relaylm.server import create_app


class _TwoPassCounter:
    def count_conversation_input(self, _, *, pass_request=None):
        return SerializedInputTokenCount(
            total_input_tokens=32,
            required_input_framing_tokens=8,
            mode=TokenCountMode.EXACT,
        )

    def count_extraction_input(self, _, *, pass_request=None):
        return SerializedInputTokenCount(
            total_input_tokens=48,
            required_input_framing_tokens=8,
            mode=TokenCountMode.EXACT,
        )


def _capabilities():
    return {
        "test.two-pass": TokenCounterCapability(
            mode=TokenCountMode.EXACT,
            factory=lambda _: _TwoPassCounter(),
        )
    }


def _write_config(
    path: Path,
    *,
    backend: str = "lm_studio",
    pass1_limit: int | None = 256,
    pass2_limit: int | None = 128,
    reserve: int = 512,
) -> Path:
    pass1 = (
        "    pass1: {}\n"
        if pass1_limit is None
        else f"    pass1:\n      max_output_tokens: {pass1_limit}\n"
    )
    pass2 = (
        "    pass2: {}\n"
        if pass2_limit is None
        else f"    pass2:\n      max_output_tokens: {pass2_limit}\n"
    )
    path.write_text(
        f"""\
format_version: 1
profiles:
  - name: relm
    root: /characters/relm
provider:
  adapter: openai_compatible
  backend: {backend}
  base_url: http://127.0.0.1:1234/v1
  model: model-id
runtime:
  cognition:
    mode: two_pass
{pass1}{pass2}  cognitive_budget:
    total:
      model_context_window: 4096
      reserved_output_tokens: {reserve}
    policy:
      initial_plan:
        canonical_state: {{max_items: 8, floor_items: 2}}
        working_context: {{max_items: 4, floor_items: 1, max_chars: 2000, floor_chars: 500}}
        retrieved_memory: {{max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}}
        event_evidence: {{max_items: 4, floor_items: 0, max_chars: 1600, floor_chars: 0}}
      steps: []
    token_counter:
      capability: test.two-pass
      mode: exact
""",
        encoding="utf-8",
    )
    return path


def test_release_assembly_carries_one_coarse_budget_to_both_two_pass_totals(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml"),
        environ={},
    )
    assembly = assemble_runtime(
        resolved,
        token_counter_capabilities=_capabilities(),
    )

    budget = assembly.cognitive_budget
    assert isinstance(budget, TwoPassCognitiveBudgetRuntimeConfig)
    assert resolved.config.runtime.cognitive_budget is not None
    assert budget.pass1_total == resolved.config.runtime.cognitive_budget.total
    assert budget.pass2_total == resolved.config.runtime.cognitive_budget.total
    assert assembly.app_kwargs()["cognitive_budget"] is budget
    assert assembly.pass1_request is not None
    assert assembly.pass2_request is not None
    assert assembly.pass1_request.max_output_tokens == 256
    assert assembly.pass2_request.max_output_tokens == 128

    profile = assembly.profiles.resolve("relm")
    assert profile is not None
    assert "max_output_tokens" in profile.provider.decoding_capabilities.supported_controls


@pytest.mark.parametrize("missing", ["pass1", "pass2"])
def test_budgeted_two_pass_requires_explicit_hard_output_limit_for_each_pass(
    tmp_path: Path,
    missing: str,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(
            tmp_path / "runtime.yaml",
            pass1_limit=None if missing == "pass1" else 256,
            pass2_limit=None if missing == "pass2" else 128,
        ),
        environ={},
    )

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved, token_counter_capabilities=_capabilities())

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught.value.field == f"runtime.cognition.{missing}.max_output_tokens"


def test_budgeted_two_pass_rejects_hard_output_limit_larger_than_reserve(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(
            tmp_path / "runtime.yaml",
            pass1_limit=513,
            reserve=512,
        ),
        environ={},
    )

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved, token_counter_capabilities=_capabilities())

    assert caught.value.code is RuntimeConfigErrorCode.INVALID_COMBINATION
    assert caught.value.field == "runtime.cognition.pass1.max_output_tokens"


def test_budgeted_two_pass_fails_when_backend_cannot_attest_output_limit_carriage(
    tmp_path: Path,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml", backend="generic"),
        environ={},
    )

    with pytest.raises(RuntimeAssemblyError) as caught:
        assemble_runtime(resolved, token_counter_capabilities=_capabilities())

    assert caught.value.code is RuntimeConfigErrorCode.CAPABILITY_UNAVAILABLE
    assert caught.value.field == "runtime.cognition.pass1.max_output_tokens"


def test_buffered_and_streaming_api_receive_same_two_pass_budget(
    tmp_path: Path,
    monkeypatch,
) -> None:
    resolved = resolve_runtime_config(
        config_path=_write_config(tmp_path / "runtime.yaml"),
        environ={},
    )
    assembly = assemble_runtime(
        resolved,
        token_counter_capabilities=_capabilities(),
    )
    budget = assembly.cognitive_budget
    assert isinstance(budget, TwoPassCognitiveBudgetRuntimeConfig)

    buffered: dict[str, object] = {}
    streaming: dict[str, object] = {}

    async def fake_buffered(**kwargs):
        buffered.update(kwargs)
        return SimpleNamespace(response="ok")

    async def fake_streaming(**kwargs):
        streaming.update(kwargs)
        await kwargs["emit_response_delta"]("ok")
        return SimpleNamespace(response="ok")

    monkeypatch.setattr(openai_api, "run_user_turn_two_pass", fake_buffered)
    monkeypatch.setattr(openai_api, "run_user_turn_two_pass_streaming", fake_streaming)

    app = create_app(**assembly.app_kwargs())
    with TestClient(app) as client:
        response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relm",
                "messages": [{"role": "user", "content": "hello"}],
            },
        )
        stream_response = client.post(
            "/v1/chat/completions",
            json={
                "model": "relm",
                "messages": [{"role": "user", "content": "hello again"}],
                "stream": True,
            },
        )

    assert response.status_code == 200
    assert stream_response.status_code == 200
    assert buffered["cognitive_budget"] is budget
    assert streaming["cognitive_budget"] is budget
