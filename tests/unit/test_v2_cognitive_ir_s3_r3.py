from __future__ import annotations

import json

import httpx
import pytest

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_s3_r2 import S3_R2_SEEDS
from relaylm.v2_cognitive_ir_s3_r3 import (
    S3_R3_LABEL,
    S3_R3_MAX_OUTPUT_TOKENS,
    S3_R3_PREREGISTRATION_SCHEMA,
    S3_R3_PREREGISTRATION_SHA256,
    S3_R3_SEEDS,
    activate_s3_r3_preregistration,
    derive_s3_r3_seed,
    validate_s3_r3_preregistration,
)
from relaylm.v2_transfer_actual_model import StructureProposalError
import tools.v2_cognitive_ir_s3_llama_cpp as historical_transport
import tools.v2_cognitive_ir_s3_llama_cpp_wsl as wsl
from tools.v2_cognitive_ir_s3_r3_llama_cpp import S3R3LlamaCppClient


def test_s3_r3_identity_seeds_and_scientific_shape() -> None:
    validate_s3_r3_preregistration()
    assert S3_R3_PREREGISTRATION_SCHEMA == "relaylm2-cognitive-ir-s3-prereg-v3"
    assert S3_R3_PREREGISTRATION_SHA256 == (
        "a0b137f023c260eb9da479f5722708f6cf6f955198e4234203753831e9278ed1"
    )
    assert S3_R3_LABEL == "relaylm2-cognitive-ir-s3-semantic-invariance-v3"
    assert S3_R3_MAX_OUTPUT_TOKENS == 1024
    assert {
        regime: tuple(derive_s3_r3_seed(regime, index) for index in range(3))
        for regime in base.S3_REGIMES
    } == dict(S3_R3_SEEDS)
    fresh = {seed for values in S3_R3_SEEDS.values() for seed in values}
    r2 = {seed for values in S3_R2_SEEDS.values() for seed in values}
    assert len(fresh) == 12
    assert fresh.isdisjoint(r2)
    assert tuple(base.S3_REGIMES) == ("shared", "null", "mismatch", "shift")
    assert dict(base.S3_SHARD_CALLS) == {
        "shared": 123,
        "null": 123,
        "mismatch": 123,
        "shift": 129,
    }
    assert base.S3_TOTAL_SEMANTIC_CALLS == 498
    assert base.S3_TOTAL_INPUT_TOKEN_REQUESTS == 996
    assert (
        base.S3_SURFACE_EFFECT_MAX,
        base.S3_SEMANTIC_EFFECT_MIN,
        base.S3_EFFECT_MARGIN_MIN,
    ) == (0.15, 0.20, 0.15)


def test_s3_r3_activation_preserves_historical_transport_and_changes_only_identity() -> None:
    original = (
        base.S3_PREREGISTRATION_SCHEMA,
        base.S3_PREREGISTRATION_SHA256,
        base.S3_LABEL,
        base.S3_SEEDS,
    )
    historical_max = historical_transport.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS
    try:
        activate_s3_r3_preregistration()
        assert base.S3_PREREGISTRATION_SCHEMA == S3_R3_PREREGISTRATION_SCHEMA
        assert base.S3_PREREGISTRATION_SHA256 == S3_R3_PREREGISTRATION_SHA256
        assert base.S3_LABEL == S3_R3_LABEL
        assert dict(base.S3_SEEDS) == dict(S3_R3_SEEDS)
        assert len(base.s3_campaign_plan()) == 498
        assert historical_transport.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS == historical_max == 512
    finally:
        (
            base.S3_PREREGISTRATION_SCHEMA,
            base.S3_PREREGISTRATION_SHA256,
            base.S3_LABEL,
            base.S3_SEEDS,
        ) = original


def test_wsl_route_targets_r3_child() -> None:
    assert wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_s3_r3_llama_cpp_transaction"
    )


def test_s3_r3_transport_uses_1024_and_records_non_stop_metadata() -> None:
    seen: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.url.path, body))
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={"input_tokens": 17})
        return httpx.Response(
            200,
            json={
                "id": "s3-r3-length",
                "choices": [
                    {
                        "finish_reason": "length",
                        "message": {"content": "abcdef", "reasoning": ""},
                    }
                ],
                "usage": {
                    "prompt_tokens": 17,
                    "completion_tokens": 1024,
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = S3R3LlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="model.gguf",
        call_plan=("q1",),
        http_client=http_client,
    )
    try:
        with pytest.raises(StructureProposalError, match="failure_metadata="):
            client.complete_named(
                "q1",
                ({"role": "user", "content": "solve"},),
                output_kind="text",
            )
    finally:
        client.close()
        http_client.close()

    assert client.provider_attempts == 1
    assert client.provider_completions == 0
    assert client.input_count_attempts == client.input_count_completions == 2
    assert [path for path, _ in seen] == [
        "/v1/chat/completions/input_tokens",
        "/v1/chat/completions/input_tokens",
        "/v1/chat/completions",
    ]
    assert seen[-1][1]["max_tokens"] == 1024
    assert seen[-1][1]["reasoning_effort"] == "none"
    assert client.last_failure_metadata == {
        "question_id": "q1",
        "finish_reason": "length",
        "prompt_tokens": 17,
        "completion_tokens": 1024,
        "reasoning_tokens": 0,
        "reasoning_field_status": "empty",
        "content_chars": 6,
        "content_bytes": 6,
        "content_sha256": "bef57ec7f53a6d40beb640a780a639c83bc29ac8a9816f1fc6c5c6dcd93c4721",
    }
