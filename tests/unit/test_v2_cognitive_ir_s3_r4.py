from __future__ import annotations

import json

import httpx
import pytest

import relaylm.v2_cognitive_ir_s3 as base
from relaylm.v2_cognitive_ir_actual_model import build_s2_formation_messages
from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    P2_BOUNDEDNESS_HARD_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    P2_BOUNDEDNESS_TARGET_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MIN_WORDS,
    build_margin_p2_formation_messages,
)
from relaylm.v2_cognitive_ir_p2_termination_qual import (
    S3_R4_LABEL as PRECOMMITTED_R4_LABEL,
    S3_R4_PRECOMMITTED_SEEDS,
)
from relaylm.v2_cognitive_ir_s3_r3 import (
    S3_R3_LABEL,
    S3_R3_PREREGISTRATION_SHA256,
    S3_R3_SEEDS,
)
from relaylm.v2_cognitive_ir_s3_r4 import (
    S3_R4_LABEL,
    S3_R4_MAX_OUTPUT_TOKENS,
    S3_R4_P2_BUILDER,
    S3_R4_PREREGISTRATION_SCHEMA,
    S3_R4_PREREGISTRATION_SHA256,
    S3_R4_SEEDS,
    activate_s3_r4_preregistration,
    derive_s3_r4_seed,
    form_s2_representations_r4,
    validate_s3_r4_preregistration,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
import tools.v2_cognitive_ir_s3_llama_cpp_transaction as shared_transaction
import tools.v2_cognitive_ir_s3_llama_cpp_wsl as historical_wsl
import tools.v2_cognitive_ir_s3_r4_llama_cpp_wsl as r4_wsl
from tools.v2_cognitive_ir_s3_r4_llama_cpp import S3R4LlamaCppClient
import tools.v2_cognitive_ir_s3_r4_llama_cpp_transaction as r4_transaction


def _base_snapshot() -> tuple[object, ...]:
    return (
        base.S3_PREREGISTRATION_SCHEMA,
        base.S3_PREREGISTRATION_SHA256,
        base.S3_LABEL,
        base.S3_SEEDS,
        base.form_s2_representations,
    )


def _restore_base(snapshot: tuple[object, ...]) -> None:
    (
        base.S3_PREREGISTRATION_SCHEMA,
        base.S3_PREREGISTRATION_SHA256,
        base.S3_LABEL,
        base.S3_SEEDS,
        base.form_s2_representations,
    ) = snapshot


def test_s3_r4_exact_precommit_and_scientific_shape() -> None:
    validate_s3_r4_preregistration()
    assert S3_R4_PREREGISTRATION_SCHEMA == "relaylm2-cognitive-ir-s3-prereg-v4"
    assert S3_R4_PREREGISTRATION_SHA256 == (
        "deb10b356f1cfe4fd18275b790f1a5bcb5972b1b841e874c26a8827ffd20dae4"
    )
    assert S3_R4_LABEL == PRECOMMITTED_R4_LABEL
    assert dict(S3_R4_SEEDS) == dict(S3_R4_PRECOMMITTED_SEEDS)
    assert {
        regime: tuple(derive_s3_r4_seed(regime, index) for index in range(3))
        for regime in base.S3_REGIMES
    } == dict(S3_R4_SEEDS)
    fresh = {seed for values in S3_R4_SEEDS.values() for seed in values}
    r3 = {seed for values in S3_R3_SEEDS.values() for seed in values}
    assert len(fresh) == 12
    assert fresh.isdisjoint(r3)
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
    assert base.S3_SURFACE_VARIANTS == (
        "S1_ROLE_LABEL_NEUTRAL",
        "S2_KEY_RENAME_REORDER",
        "S3_LOSSLESS_LIST_PROSE_SERIALIZATION",
        "S4_PROMPT_PARAPHRASE_FORMAT",
    )
    assert base.S3_SEMANTIC_INTERVENTIONS == (
        "M1_RULE_OFFSET_FLIP",
        "M2_EXCEPTION_CHANGE",
        "M3_SCOPE_CHANGE",
        "M4_RELATION_REPLACE",
    )
    assert S3_R4_MAX_OUTPUT_TOKENS == 1024
    assert (
        P2_BOUNDEDNESS_TARGET_MIN_WORDS,
        P2_BOUNDEDNESS_TARGET_MAX_WORDS,
        P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    ) == (60, 80, 550)
    assert (
        P2_BOUNDEDNESS_HARD_MAX_WORDS,
        P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    ) == (120, 800)
    assert S3_R4_P2_BUILDER.endswith("build_margin_p2_formation_messages")


class _FormationStub:
    def __init__(self, modulus: int) -> None:
        self.messages: list[tuple[dict[str, str], ...]] = []
        self.completions = [
            ExperimentCompletion(
                content="A concise ordinary recap.",
                input_tokens=11,
                output_tokens=7,
                response_id="p2",
            ),
            ExperimentCompletion(
                content="A compact semantic gist.",
                input_tokens=12,
                output_tokens=6,
                response_id="p3",
            ),
            ExperimentCompletion(
                content=json.dumps(
                    {
                        "permutation": [0, 1, 2, 3],
                        "offsets": [1, 1, 1, 1],
                        "modulus": modulus,
                    }
                ),
                input_tokens=13,
                output_tokens=9,
                response_id="p4",
            ),
        ]

    def complete(
        self,
        messages: tuple[dict[str, str], ...],
    ) -> ExperimentCompletion:
        self.messages.append(messages)
        return self.completions[len(self.messages) - 1]


def test_s3_r4_changes_only_p2_formation_and_preserves_shared_lineage() -> None:
    snapshot = _base_snapshot()
    try:
        activate_s3_r4_preregistration()
        family = base.generate_s3_family("shared", 0)
        stub = _FormationStub(family.modulus)
        representations = form_s2_representations_r4(stub, family)

        assert stub.messages[0] == build_margin_p2_formation_messages(family)
        assert stub.messages[1] == build_s2_formation_messages("P3_SEMANTIC_CACHE", family)
        assert stub.messages[2] == build_s2_formation_messages(
            "P4_MEMORY_PLUS_STRUCTURE", family
        )
        assert stub.messages[0] != build_s2_formation_messages(
            "P2_ORDINARY_SUMMARY", family
        )
        assert (
            representations["P4_MEMORY_PLUS_STRUCTURE"].formation_completion
            is representations["P5_STRUCTURE_ONLY_RECONSTRUCTABLE"].formation_completion
            is representations["P6_GENERIC_EQUAL_INFORMATION"].formation_completion
        )
        assert base.semantic_digest(
            "P4_MEMORY_PLUS_STRUCTURE",
            json.loads(representations["P4_MEMORY_PLUS_STRUCTURE"].serialized),
        ) == base.semantic_digest(
            "P6_GENERIC_EQUAL_INFORMATION",
            json.loads(representations["P6_GENERIC_EQUAL_INFORMATION"].serialized),
        )
    finally:
        _restore_base(snapshot)


def test_s3_r4_target_margin_is_not_the_hard_gate() -> None:
    above_target = " ".join(["word"] * 90)
    failure, characters, words, _ = S3R4LlamaCppClient._p2_hard_failure(above_target)
    assert failure is None
    assert words == 90
    assert characters < 800

    too_many_words = " ".join(["w"] * 121)
    assert S3R4LlamaCppClient._p2_hard_failure(too_many_words)[0] == (
        "whitespace_delimited_word_limit"
    )
    assert S3R4LlamaCppClient._p2_hard_failure("x" * 801)[0] == (
        "visible_unicode_character_limit"
    )
    assert S3R4LlamaCppClient._p2_hard_failure("   ")[0] == "empty_visible_content"


def _mock_client(
    *,
    question_id: str,
    finish_reason: str = "stop",
    content: str = "ok",
) -> tuple[S3R4LlamaCppClient, httpx.Client, list[tuple[str, dict[str, object]]]]:
    seen: list[tuple[str, dict[str, object]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        seen.append((request.url.path, body))
        if request.url.path.endswith("/input_tokens"):
            return httpx.Response(200, json={"input_tokens": 17})
        return httpx.Response(
            200,
            json={
                "id": "s3-r4-test",
                "choices": [
                    {
                        "finish_reason": finish_reason,
                        "message": {"content": content, "reasoning": ""},
                    }
                ],
                "usage": {
                    "prompt_tokens": 17,
                    "completion_tokens": 10,
                    "completion_tokens_details": {"reasoning_tokens": 0},
                },
            },
        )

    http_client = httpx.Client(transport=httpx.MockTransport(handler))
    client = S3R4LlamaCppClient(
        base_url="http://127.0.0.1:1234/v1",
        model="model.gguf",
        call_plan=(question_id,),
        http_client=http_client,
    )
    return client, http_client, seen


def test_s3_r4_transport_admits_above_target_p2_and_keeps_frozen_runtime_controls() -> None:
    question_id = "shared:0:1813949056:form-p2"
    content = " ".join(["word"] * 90)
    client, http_client, seen = _mock_client(question_id=question_id, content=content)
    try:
        completion = client.complete_named(
            question_id,
            ({"role": "user", "content": "solve"},),
            output_kind="text",
        )
    finally:
        client.close()
        http_client.close()

    assert completion.content == content
    assert client.provider_attempts == client.provider_completions == 1
    assert client.input_count_attempts == client.input_count_completions == 2
    assert client.p2_mechanical_records[-1]["admitted"] is True
    body = seen[-1][1]
    assert body["max_tokens"] == 1024
    assert body["reasoning_effort"] == "none"
    assert body["temperature"] == 0.0
    assert "seed" not in body


def test_s3_r4_transport_fails_closed_on_p2_hard_envelope_without_retry() -> None:
    question_id = "shared:0:1813949056:form-p2"
    content = " ".join(["w"] * 121)
    client, http_client, seen = _mock_client(question_id=question_id, content=content)
    try:
        with pytest.raises(StructureProposalError, match="hard admission failed"):
            client.complete_named(
                question_id,
                ({"role": "user", "content": "solve"},),
                output_kind="text",
            )
    finally:
        client.close()
        http_client.close()

    assert client.provider_attempts == client.provider_completions == 1
    assert len([path for path, _ in seen if path.endswith("/chat/completions")]) == 1
    assert client.p2_mechanical_records[-1]["failure"] == (
        "whitespace_delimited_word_limit"
    )


def test_s3_r4_transport_non_stop_is_terminal_and_non_p2_is_not_bounded() -> None:
    p2_id = "shared:0:1813949056:form-p2"
    client, http_client, seen = _mock_client(
        question_id=p2_id,
        finish_reason="length",
        content="partial",
    )
    try:
        with pytest.raises(StructureProposalError, match="did not finish with stop"):
            client.complete_named(
                p2_id,
                ({"role": "user", "content": "solve"},),
                output_kind="text",
            )
    finally:
        client.close()
        http_client.close()
    assert client.provider_attempts == 1
    assert client.provider_completions == 0
    assert len([path for path, _ in seen if path.endswith("/chat/completions")]) == 1
    assert client.p2_mechanical_records[-1]["failure"] == "non_stop_finish_reason"

    p3_id = "shared:0:1813949056:form-p3"
    client2, http_client2, _ = _mock_client(question_id=p3_id, content="x" * 801)
    try:
        completion = client2.complete_named(
            p3_id,
            ({"role": "user", "content": "solve"},),
            output_kind="text",
        )
    finally:
        client2.close()
        http_client2.close()
    assert len(completion.content) == 801
    assert client2.p2_mechanical_records == []


def test_s3_r4_activation_and_transaction_leave_historical_r3_identity_intact() -> None:
    snapshot = _base_snapshot()
    transaction_snapshot = (
        shared_transaction.S3_PREREGISTRATION_SHA256,
        shared_transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS,
        shared_transaction.S3LlamaCppClient,
    )
    historical_route = historical_wsl.INNER_TRANSACTION_MODULE
    try:
        transaction, _ = r4_transaction._load_listener_safe_transaction()
        assert transaction is shared_transaction
        assert base.S3_LABEL == S3_R4_LABEL
        assert dict(base.S3_SEEDS) == dict(S3_R4_SEEDS)
        assert base.form_s2_representations is form_s2_representations_r4
        assert transaction.S3_PREREGISTRATION_SHA256 == S3_R4_PREREGISTRATION_SHA256
        assert transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS == 1024
        assert transaction.S3LlamaCppClient is S3R4LlamaCppClient
        assert tuple(transaction.S3_REGIMES) == ("shared", "null", "mismatch", "shift")
    finally:
        _restore_base(snapshot)
        (
            shared_transaction.S3_PREREGISTRATION_SHA256,
            shared_transaction.S3_LLAMA_CPP_MAX_OUTPUT_TOKENS,
            shared_transaction.S3LlamaCppClient,
        ) = transaction_snapshot

    assert S3_R3_LABEL == "relaylm2-cognitive-ir-s3-semantic-invariance-v3"
    assert S3_R3_PREREGISTRATION_SHA256 == (
        "a0b137f023c260eb9da479f5722708f6cf6f955198e4234203753831e9278ed1"
    )
    assert historical_wsl.INNER_TRANSACTION_MODULE == historical_route == (
        "tools.v2_cognitive_ir_s3_r3_llama_cpp_transaction"
    )
    assert r4_wsl.INNER_TRANSACTION_MODULE == (
        "tools.v2_cognitive_ir_s3_r4_llama_cpp_transaction"
    )


def test_s3_r4_runtime_rejects_arm_specific_sampling_drift() -> None:
    with pytest.raises(StructureProposalError, match="temperature must be zero"):
        S3R4LlamaCppClient(
            base_url="http://127.0.0.1:1234/v1",
            model="model.gguf",
            call_plan=("q",),
            temperature=0.1,
        )
    with pytest.raises(StructureProposalError, match="request seed must be null"):
        S3R4LlamaCppClient(
            base_url="http://127.0.0.1:1234/v1",
            model="model.gguf",
            call_plan=("q",),
            seed=1,
        )
    with pytest.raises(StructureProposalError, match="output ceiling must be exactly 1024"):
        S3R4LlamaCppClient(
            base_url="http://127.0.0.1:1234/v1",
            model="model.gguf",
            call_plan=("q",),
            max_output_tokens=2048,
        )
