from __future__ import annotations

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_p2_boundedness_qual_v2_llama_cpp import (
    P2BoundednessQualificationV2Client,
)
from tools.v2_cognitive_ir_s3_r3_llama_cpp import S3R3LlamaCppClient


QUESTION_ID = "shared:0:1429064482:form-p2"


def _client() -> P2BoundednessQualificationV2Client:
    return P2BoundednessQualificationV2Client(
        base_url="http://127.0.0.1:1234/v1",
        model="test-model",
        call_plan=(QUESTION_ID,),
    )


def _completion(content: str) -> ExperimentCompletion:
    return ExperimentCompletion(
        content=content,
        input_tokens=164,
        output_tokens=64,
        response_id="test-response",
    )


def test_above_target_but_inside_hard_envelope_is_admitted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    content = " ".join(["abcdefg"] * 90)
    assert 550 < len(content) < 800
    assert len(content.split()) == 90

    def fake_complete(
        self: S3R3LlamaCppClient,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        return _completion(content)

    monkeypatch.setattr(S3R3LlamaCppClient, "complete_named", fake_complete)
    try:
        result = client.complete_named(
            QUESTION_ID,
            ({"role": "system", "content": "x"},),
            output_kind="text",
        )
        assert result.content == content
        assert client.qualification_admissions == 1
        assert client.mechanical_records[0]["admitted"] is True
        identity = client.qualification_identity
        assert identity["target_max_words"] == 80
        assert identity["target_max_unicode_characters"] == 550
        assert identity["hard_max_words"] == 120
        assert identity["hard_max_unicode_characters"] == 800
        assert identity["max_output_tokens"] == 1024
    finally:
        client.close()


def test_over_hard_character_envelope_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()

    def fake_complete(
        self: S3R3LlamaCppClient,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        return _completion("x" * 801)

    monkeypatch.setattr(S3R3LlamaCppClient, "complete_named", fake_complete)
    try:
        with pytest.raises(StructureProposalError, match="visible_unicode_character_limit"):
            client.complete_named(
                QUESTION_ID,
                ({"role": "system", "content": "x"},),
                output_kind="text",
            )
    finally:
        client.close()


def test_over_hard_word_envelope_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()

    def fake_complete(
        self: S3R3LlamaCppClient,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        return _completion(" ".join(["x"] * 121))

    monkeypatch.setattr(S3R3LlamaCppClient, "complete_named", fake_complete)
    try:
        with pytest.raises(StructureProposalError, match="whitespace_delimited_word_limit"):
            client.complete_named(
                QUESTION_ID,
                ({"role": "system", "content": "x"},),
                output_kind="text",
            )
    finally:
        client.close()


def test_non_stop_finish_remains_terminal_without_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()

    def fake_non_stop(
        self: S3R3LlamaCppClient,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        self.last_failure_metadata = {
            "question_id": question_id,
            "finish_reason": "length",
            "prompt_tokens": 164,
            "completion_tokens": 1024,
            "reasoning_tokens": None,
            "reasoning_field_status": "absent",
            "content_chars": 700,
            "content_bytes": 700,
            "content_sha256": "0" * 64,
        }
        raise StructureProposalError("synthetic non-stop")

    monkeypatch.setattr(S3R3LlamaCppClient, "complete_named", fake_non_stop)
    try:
        with pytest.raises(StructureProposalError, match="synthetic non-stop"):
            client.complete_named(
                QUESTION_ID,
                ({"role": "system", "content": "x"},),
                output_kind="text",
            )
        assert client.qualification_admissions == 0
        assert len(client.mechanical_records) == 1
        assert client.mechanical_records[0]["failure"] == "non_stop_finish_reason"
    finally:
        client.close()
