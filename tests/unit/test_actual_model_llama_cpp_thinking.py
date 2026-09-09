from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from relaylm.actual_model_llama_cpp import (
    LlamaCppInputCounterError,
    attest_llama_cpp_runtime,
)
from relaylm.actual_model_llama_cpp_thinking import (
    LLAMA_CPP_THINKING_CHAT_COUNTER_CAPABILITY,
    LLAMA_CPP_THINKING_CHAT_COUNTER_VERSION,
    LlamaCppThinkingChatInputCounter,
)


REVISION = "c841aeeb8bb2fe417038dadfa9b007cf1a9ef950"
MODEL = "gemma-local"
MODEL_PATH = "/models/gemma.gguf"


def _runtime():
    return attest_llama_cpp_runtime(
        props={
            "build_info": f"b999-{REVISION}",
            "model_alias": MODEL,
            "model_ftype": "Q4_K_M",
            "model_path": MODEL_PATH,
            "chat_template": "{{ messages }}",
            "total_slots": 1,
            "default_generation_settings": {"n_ctx": 4352},
        },
        slots=[{"id": 0, "n_ctx": 4352}],
        upstream_revision=REVISION,
        expected_build_info=f"b999-{REVISION}",
        expected_model_alias=MODEL,
        expected_model_path=MODEL_PATH,
        artifact_sha256="ab" * 32,
        context_shift_enabled=False,
    )


def test_thinking_counter_preserves_exact_reasoning_and_stream_controls() -> None:
    observed: list[dict[str, Any]] = []

    def post_json(_: str, payload: Mapping[str, Any], __: str | None) -> object:
        observed.append(dict(payload))
        return {
            "input_tokens": 12
            if any(m["content"] for m in payload["messages"])
            else 4
        }

    counter = LlamaCppThinkingChatInputCounter(
        base_url="http://127.0.0.1:1234/v1",
        runtime_identity=_runtime(),
        post_json=post_json,
    )
    result = counter.count_input(
        {
            "model": MODEL,
            "messages": [{"role": "user", "content": "hello"}],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 64,
            "stream": False,
            "reasoning_effort": "none",
        }
    )

    assert result.total_input_tokens == 12
    assert result.required_input_framing_tokens == 4
    assert len(observed) == 2
    assert all(item["reasoning_effort"] == "none" for item in observed)
    assert all("chat_template_kwargs" not in item for item in observed)
    assert all(item["stream"] is False for item in observed)
    assert counter.evidence_identity.capability == LLAMA_CPP_THINKING_CHAT_COUNTER_CAPABILITY
    assert counter.evidence_identity.version == LLAMA_CPP_THINKING_CHAT_COUNTER_VERSION
    parameters = dict(counter.evidence_identity.parameters)
    assert parameters["thinking_control"] == "reasoning_effort=none"
    assert parameters["stream_control"] == "stream=false"


def test_thinking_counter_rejects_unqualified_reasoning_or_stream_controls() -> None:
    counter = LlamaCppThinkingChatInputCounter(
        base_url="http://127.0.0.1:1234/v1",
        runtime_identity=_runtime(),
        post_json=lambda *_: {"input_tokens": 1},
    )

    for value in ("low", "medium", "high", ""):
        with pytest.raises(LlamaCppInputCounterError, match="reasoning_effort=none"):
            counter.count_input(
                {
                    "model": MODEL,
                    "messages": [{"role": "user", "content": "hello"}],
                    "reasoning_effort": value,
                }
            )

    with pytest.raises(LlamaCppInputCounterError, match="unsupported"):
        counter.count_input(
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": "hello"}],
                "chat_template_kwargs": {"enable_thinking": False},
            }
        )

    with pytest.raises(LlamaCppInputCounterError, match="stream=false"):
        counter.count_input(
            {
                "model": MODEL,
                "messages": [{"role": "user", "content": "hello"}],
                "stream": True,
                "reasoning_effort": "none",
            }
        )
