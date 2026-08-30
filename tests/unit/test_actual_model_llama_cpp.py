from __future__ import annotations

import hashlib
from collections.abc import Mapping
from typing import Any

import pytest

from relaylm.actual_model_llama_cpp import (
    LLAMA_CPP_CHAT_COUNTER_CAPABILITY,
    LlamaCppChatInputCounter,
    LlamaCppInputCounterError,
    LlamaCppRuntimeAttestationError,
    attest_llama_cpp_runtime,
)
from relaylm.budget_enforcement import TokenCountMode


UPSTREAM_REVISION = "c841aeeb8bb2fe417038dadfa9b007cf1a9ef950"
BUILD_INFO = "b999-c841aeeb8bb2fe417038dadfa9b007cf1a9ef950"
MODEL_ALIAS = "gemma-local"
MODEL_PATH = "/models/gemma-local.Q4_K_M.gguf"
ARTIFACT_SHA256 = "ab" * 32
CHAT_TEMPLATE = "{{ bos_token }}{{ messages }}"


def _props(*, n_ctx: int = 4096) -> dict[str, object]:
    return {
        "build_info": BUILD_INFO,
        "model_alias": MODEL_ALIAS,
        "model_ftype": "Q4_K_M",
        "model_path": MODEL_PATH,
        "chat_template": CHAT_TEMPLATE,
        "total_slots": 1,
        "default_generation_settings": {
            "id": 0,
            "n_ctx": n_ctx,
            "speculative": False,
            "is_processing": False,
        },
    }


def _slots(*, n_ctx: int = 4096) -> list[dict[str, object]]:
    return [
        {
            "id": 0,
            "n_ctx": n_ctx,
            "speculative": False,
            "is_processing": False,
        }
    ]


def _identity():
    return attest_llama_cpp_runtime(
        props=_props(),
        slots=_slots(),
        upstream_revision=UPSTREAM_REVISION,
        expected_build_info=BUILD_INFO,
        expected_model_alias=MODEL_ALIAS,
        expected_model_path=MODEL_PATH,
        artifact_sha256=ARTIFACT_SHA256,
        context_shift_enabled=False,
    )


def test_llama_cpp_runtime_attestation_binds_exact_identity_and_context() -> None:
    identity = _identity()

    assert identity.upstream_revision == UPSTREAM_REVISION
    assert identity.build_info == BUILD_INFO
    assert identity.model_alias == MODEL_ALIAS
    assert identity.model_path == MODEL_PATH
    assert identity.model_ftype == "Q4_K_M"
    assert identity.artifact_sha256 == ARTIFACT_SHA256
    assert identity.context_limit == 4096
    assert identity.total_slots == 1
    assert identity.context_shift_enabled is False
    assert identity.chat_template_sha256 == hashlib.sha256(
        CHAT_TEMPLATE.encode("utf-8")
    ).hexdigest()


def test_llama_cpp_runtime_attestation_rejects_context_shift() -> None:
    with pytest.raises(LlamaCppRuntimeAttestationError, match="context shift"):
        attest_llama_cpp_runtime(
            props=_props(),
            slots=_slots(),
            upstream_revision=UPSTREAM_REVISION,
            expected_build_info=BUILD_INFO,
            expected_model_alias=MODEL_ALIAS,
            expected_model_path=MODEL_PATH,
            artifact_sha256=ARTIFACT_SHA256,
            context_shift_enabled=True,
        )


def test_llama_cpp_runtime_attestation_rejects_slot_context_mismatch() -> None:
    with pytest.raises(LlamaCppRuntimeAttestationError, match="slot context"):
        attest_llama_cpp_runtime(
            props=_props(n_ctx=4096),
            slots=_slots(n_ctx=2048),
            upstream_revision=UPSTREAM_REVISION,
            expected_build_info=BUILD_INFO,
            expected_model_alias=MODEL_ALIAS,
            expected_model_path=MODEL_PATH,
            artifact_sha256=ARTIFACT_SHA256,
            context_shift_enabled=False,
        )


def test_llama_cpp_chat_counter_counts_exact_body_and_empty_framing() -> None:
    observed: list[tuple[str, dict[str, Any], str | None]] = []

    def post_json(
        url: str,
        payload: Mapping[str, Any],
        api_key: str | None,
    ) -> object:
        body = dict(payload)
        observed.append((url, body, api_key))
        messages = body["messages"]
        assert isinstance(messages, list)
        has_content = any(
            isinstance(message, Mapping) and bool(message.get("content"))
            for message in messages
        )
        return {"input_tokens": 900 if has_content else 100}

    counter = LlamaCppChatInputCounter(
        base_url="http://127.0.0.1:8080/v1",
        runtime_identity=_identity(),
        api_key="secret",
        post_json=post_json,
    )
    counted = counter.count_input(
        {
            "model": MODEL_ALIAS,
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "hello"},
            ],
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 256,
            "response_format": {"type": "json_object"},
        }
    )

    assert counted.total_input_tokens == 900
    assert counted.required_input_framing_tokens == 100
    assert counted.mode is TokenCountMode.EXACT
    assert len(observed) == 2
    assert all(
        url == "http://127.0.0.1:8080/v1/chat/completions/input_tokens"
        for url, _, _ in observed
    )
    assert all(api_key == "secret" for _, _, api_key in observed)
    assert all(payload["max_tokens"] == 256 for _, payload, _ in observed)
    assert all("response_format" in payload for _, payload, _ in observed)
    framing_messages = observed[1][1]["messages"]
    assert isinstance(framing_messages, list)
    assert [message["role"] for message in framing_messages] == ["system", "user"]
    assert [message["content"] for message in framing_messages] == ["", ""]

    evidence = counter.evidence_identity
    assert evidence.capability == LLAMA_CPP_CHAT_COUNTER_CAPABILITY
    assert evidence.mode is TokenCountMode.EXACT
    assert dict(evidence.parameters)["backend"] == "llama_cpp"
    assert dict(evidence.parameters)["context_limit"] == 4096


def test_llama_cpp_chat_counter_rejects_unknown_model_input_fields() -> None:
    counter = LlamaCppChatInputCounter(
        base_url="http://127.0.0.1:8080/v1",
        runtime_identity=_identity(),
        post_json=lambda *_: {"input_tokens": 1},
    )

    with pytest.raises(LlamaCppInputCounterError, match="unsupported"):
        counter.count_input(
            {
                "model": MODEL_ALIAS,
                "messages": [{"role": "user", "content": "hello"}],
                "tools": [],
            }
        )


def test_llama_cpp_chat_counter_rejects_malformed_count_response() -> None:
    counter = LlamaCppChatInputCounter(
        base_url="http://127.0.0.1:8080/v1",
        runtime_identity=_identity(),
        post_json=lambda *_: {"input_tokens": "900"},
    )

    with pytest.raises(LlamaCppInputCounterError, match="input_tokens"):
        counter.count_input(
            {
                "model": MODEL_ALIAS,
                "messages": [{"role": "user", "content": "hello"}],
            }
        )
