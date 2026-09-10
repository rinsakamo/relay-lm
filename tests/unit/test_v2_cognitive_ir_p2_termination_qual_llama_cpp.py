from __future__ import annotations

import pytest

from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_p2_termination_qual_llama_cpp import (
    P2TerminationQualificationClient,
)
from tools.v2_cognitive_ir_s3_r3_llama_cpp import S3R3LlamaCppClient


def _client() -> P2TerminationQualificationClient:
    return P2TerminationQualificationClient(
        base_url="http://127.0.0.1:1234/v1",
        model="test-model",
        call_plan=("shared:0:961584193:form-p2",),
    )


def _completion(content: str) -> ExperimentCompletion:
    return ExperimentCompletion(
        content=content,
        input_tokens=164,
        output_tokens=32,
        response_id="test-response",
    )


def test_valid_bounded_stop_content_is_admitted(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()

    def fake_complete(
        self: S3R3LlamaCppClient,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        return _completion("A concise faithful recap of the observed episodes.")

    monkeypatch.setattr(S3R3LlamaCppClient, "complete_named", fake_complete)
    try:
        completion = client.complete_named(
            "shared:0:961584193:form-p2",
            ({"role": "system", "content": "x"},),
            output_kind="text",
        )
        assert completion.content.startswith("A concise")
        assert client.qualification_admissions == 1
        assert client.mechanical_records[0]["admitted"] is True
        assert "content" not in client.mechanical_records[0]
        assert client.qualification_identity["max_output_tokens"] == 1024
        assert client.qualification_identity["reasoning_effort"] == "none"
    finally:
        client.close()


def test_stop_content_over_character_envelope_fails(monkeypatch: pytest.MonkeyPatch) -> None:
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
                "shared:0:961584193:form-p2",
                ({"role": "system", "content": "x"},),
                output_kind="text",
            )
        assert client.qualification_admissions == 0
        assert client.mechanical_records[0]["admitted"] is False
    finally:
        client.close()


def test_stop_content_over_word_envelope_fails(monkeypatch: pytest.MonkeyPatch) -> None:
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
                "shared:0:961584193:form-p2",
                ({"role": "system", "content": "x"},),
                output_kind="text",
            )
        assert client.qualification_admissions == 0
        assert client.mechanical_records[0]["admitted"] is False
    finally:
        client.close()


def test_synthetic_length_finish_stays_terminal_and_recorded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
            "content_chars": 2520,
            "content_bytes": 2520,
            "content_sha256": "0" * 64,
        }
        raise StructureProposalError("synthetic non-stop")

    monkeypatch.setattr(S3R3LlamaCppClient, "complete_named", fake_non_stop)
    try:
        with pytest.raises(StructureProposalError, match="synthetic non-stop"):
            client.complete_named(
                "shared:0:961584193:form-p2",
                ({"role": "system", "content": "x"},),
                output_kind="text",
            )
        assert client.qualification_admissions == 0
        assert client.mechanical_records == [
            {
                "question_id": "shared:0:961584193:form-p2",
                "finish_reason": "length",
                "prompt_tokens": 164,
                "completion_tokens": 1024,
                "reasoning_tokens": None,
                "reasoning_field_status": "absent",
                "content_chars": 2520,
                "content_bytes": 2520,
                "content_sha256": "0" * 64,
                "admitted": False,
                "failure": "non_stop_finish_reason",
            }
        ]
    finally:
        client.close()
