from __future__ import annotations

import hashlib
from typing import Mapping

import httpx

from relaylm.v2_cognitive_ir_p2_termination_qual import (
    P2_TERMINATION_QUAL_MAX_CHARACTERS,
    P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS,
    P2_TERMINATION_QUAL_MAX_WORDS,
)
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_TIMEOUT_SECONDS
from tools.v2_cognitive_ir_s3_r3_llama_cpp import S3R3LlamaCppClient


class P2TerminationQualificationClient(S3R3LlamaCppClient):
    """P2-only mechanical qualification transport with no efficacy surface."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        call_plan: tuple[str, ...],
        timeout_seconds: float = S3_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens: int = P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS,
        temperature: int | float = 0.0,
        seed: int | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if max_output_tokens != P2_TERMINATION_QUAL_MAX_OUTPUT_TOKENS:
            raise StructureProposalError("P2 qualification output ceiling must be exactly 1024")
        if temperature != 0:
            raise StructureProposalError("P2 qualification temperature must be zero")
        if seed is not None:
            raise StructureProposalError("P2 qualification request seed must be null")
        super().__init__(
            base_url=base_url,
            model=model,
            call_plan=call_plan,
            timeout_seconds=timeout_seconds,
            max_output_tokens=max_output_tokens,
            temperature=temperature,
            seed=seed,
            api_key=api_key,
            http_client=http_client,
        )
        self.mechanical_records: list[dict[str, object]] = []
        self.qualification_admissions = 0

    @staticmethod
    def _bounded_record(
        question_id: str,
        completion: ExperimentCompletion,
    ) -> tuple[dict[str, object], str | None]:
        visible = completion.content.strip()
        encoded = visible.encode("utf-8")
        characters = len(visible)
        words = len(visible.split())
        failure: str | None = None
        if not visible:
            failure = "empty_visible_content"
        elif characters > P2_TERMINATION_QUAL_MAX_CHARACTERS:
            failure = "visible_unicode_character_limit"
        elif words > P2_TERMINATION_QUAL_MAX_WORDS:
            failure = "whitespace_delimited_word_limit"
        return (
            {
                "question_id": question_id,
                "finish_reason": "stop",
                "input_tokens": completion.input_tokens,
                "output_tokens": completion.output_tokens,
                "visible_unicode_characters": characters,
                "whitespace_delimited_words": words,
                "content_bytes": len(encoded),
                "content_sha256": hashlib.sha256(encoded).hexdigest(),
                "reasoning_field_status": "absent_or_empty_verified",
                "admitted": failure is None,
                "failure": failure,
            },
            failure,
        )

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        if output_kind != "text":
            raise StructureProposalError("P2 qualification permits text formation only")
        try:
            completion = super().complete_named(
                question_id,
                messages,
                output_kind=output_kind,
            )
        except StructureProposalError:
            if self.last_failure_metadata is not None:
                record = dict(self.last_failure_metadata)
                record["admitted"] = False
                record["failure"] = "non_stop_finish_reason"
                self.mechanical_records.append(record)
            raise

        record, failure = self._bounded_record(question_id, completion)
        self.mechanical_records.append(record)
        if failure is not None:
            raise StructureProposalError(
                f"P2 termination qualification envelope failed: {failure}"
            )
        self.qualification_admissions += 1
        return completion

    def require_complete_qualification(self) -> None:
        self.require_complete_plan()
        if self.qualification_admissions != len(self.call_plan):
            raise StructureProposalError(
                "P2 termination qualification ended without admission for every call"
            )
        if len(self.mechanical_records) != len(self.call_plan):
            raise StructureProposalError("P2 qualification mechanical record count drifted")
        if not all(bool(record.get("admitted")) for record in self.mechanical_records):
            raise StructureProposalError("P2 qualification contains a failed mechanical record")

    @property
    def qualification_identity(self) -> Mapping[str, object]:
        return {
            "max_output_tokens": self.max_output_tokens,
            "max_visible_unicode_characters": P2_TERMINATION_QUAL_MAX_CHARACTERS,
            "max_whitespace_delimited_words": P2_TERMINATION_QUAL_MAX_WORDS,
            "planned_semantic_calls": len(self.call_plan),
            "reasoning_effort": "none",
            "temperature": self.temperature,
            "seed": self.seed,
        }
