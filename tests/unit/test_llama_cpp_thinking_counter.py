from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from relaylm.actual_model_llama_cpp import (
    LlamaCppInputCounterError,
    LlamaCppRuntimeIdentity,
)
from relaylm.budget_enforcement import TokenCountMode
from tools.llama_cpp_thinking_counter import (
    LLAMA_CPP_GEMMA_THINKING_COUNTER_VERSION,
    LLAMA_CPP_GEMMA_THINKING_REQUEST_EXTENSION,
    LlamaCppGemmaThinkingChatInputCounter,
)


MODEL_ALIAS = "gemma-local"


def _identity() -> LlamaCppRuntimeIdentity:
    return LlamaCppRuntimeIdentity(
        upstream_revision="ab" * 20,
        build_info="llama.cpp build abababababababababababababababababababab",
        model_alias=MODEL_ALIAS,
        model_path="/home/rinsa/models/gguf/gemma-4-12B-it-Q4_K_M.gguf",
        model_ftype="Q4_K_M",
        artifact_sha256="cd" * 32,
        chat_template_sha256="ef" * 32,
        context_limit=4352,
        total_slots=4,
        context_shift_enabled=False,
    )


def _counter(
    observed: list[dict[str, Any]] | None = None,
) -> LlamaCppGemmaThinkingChatInputCounter:
    def post_json(
        _url: str,
        payload: Mapping[str, Any],
        _api_key: str | None,
    ) -> object:
        body = dict(payload)
        if observed is not None:
            observed.append(body)
        messages = body["messages"]
        assert isinstance(messages, list)
        has_content = any(
            isinstance(message, Mapping) and bool(message.get("content"))
            for message in messages
        )
        return {"input_tokens": 100 if has_content else 20}

    return LlamaCppGemmaThinkingChatInputCounter(
        base_url="http://127.0.0.1:1234/v1",
        runtime_identity=_identity(),
        post_json=post_json,
    )


def test_explicit_thinking_false_is_preserved_on_both_exact_count_requests() -> None:
    observed: list[dict[str, Any]] = []
    counter = _counter(observed)

    result = counter.count_input(
        {
            "model": MODEL_ALIAS,
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "hello"},
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "seed": 7,
            "max_tokens": 128,
            "response_format": {"type": "json_object"},
            "chat_template_kwargs": {"enable_thinking": False},
        }
    )

    assert result.total_input_tokens == 100
    assert result.required_input_framing_tokens == 20
    assert result.mode is TokenCountMode.EXACT
    assert len(observed) == 2
    assert all(
        body["chat_template_kwargs"] == {"enable_thinking": False}
        for body in observed
    )
    assert [message["content"] for message in observed[1]["messages"]] == ["", ""]


def test_evidence_identity_declares_thinking_request_extension() -> None:
    evidence = _counter().evidence_identity

    assert evidence.version == LLAMA_CPP_GEMMA_THINKING_COUNTER_VERSION
    assert evidence.mode is TokenCountMode.EXACT
    assert dict(evidence.parameters)["request_extension"] == (
        LLAMA_CPP_GEMMA_THINKING_REQUEST_EXTENSION
    )
    assert dict(evidence.parameters)["backend"] == "llama_cpp"
    assert dict(evidence.parameters)["context_limit"] == 4352


def test_unknown_chat_template_kwargs_member_fails_closed() -> None:
    with pytest.raises(LlamaCppInputCounterError, match="chat_template_kwargs fields"):
        _counter().count_input(
            {
                "model": MODEL_ALIAS,
                "messages": [{"role": "user", "content": "hello"}],
                "chat_template_kwargs": {
                    "enable_thinking": False,
                    "unknown": True,
                },
            }
        )


def test_non_bool_enable_thinking_fails_closed() -> None:
    with pytest.raises(LlamaCppInputCounterError, match="enable_thinking must be bool"):
        _counter().count_input(
            {
                "model": MODEL_ALIAS,
                "messages": [{"role": "user", "content": "hello"}],
                "chat_template_kwargs": {"enable_thinking": 0},
            }
        )


def test_missing_enable_thinking_member_fails_closed() -> None:
    with pytest.raises(LlamaCppInputCounterError, match="exactly enable_thinking"):
        _counter().count_input(
            {
                "model": MODEL_ALIAS,
                "messages": [{"role": "user", "content": "hello"}],
                "chat_template_kwargs": {},
            }
        )


def test_existing_unknown_top_level_field_rejection_remains_intact() -> None:
    with pytest.raises(LlamaCppInputCounterError, match="unsupported"):
        _counter().count_input(
            {
                "model": MODEL_ALIAS,
                "messages": [{"role": "user", "content": "hello"}],
                "chat_template_kwargs": {"enable_thinking": False},
                "tools": [],
            }
        )
