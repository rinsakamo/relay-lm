from __future__ import annotations

import hashlib

import httpx

from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    P2_BOUNDEDNESS_HARD_MAX_WORDS,
)
from relaylm.v2_cognitive_ir_s3_r4 import S3_R4_MAX_OUTPUT_TOKENS
from relaylm.v2_transfer_actual_model import ExperimentCompletion, StructureProposalError
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_TIMEOUT_SECONDS
from tools.v2_cognitive_ir_s3_r3_llama_cpp import S3R3LlamaCppClient


class S3R4LlamaCppClient(S3R3LlamaCppClient):
    """R4 transport: R3 controls plus the qualified P2 hard admission gate."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        call_plan: tuple[str, ...],
        timeout_seconds: float = S3_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens: int = S3_R4_MAX_OUTPUT_TOKENS,
        temperature: int | float = 0.0,
        seed: int | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if max_output_tokens != S3_R4_MAX_OUTPUT_TOKENS:
            raise StructureProposalError("S3-R4 output ceiling must be exactly 1024")
        if temperature != 0:
            raise StructureProposalError("S3-R4 temperature must be zero")
        if seed is not None:
            raise StructureProposalError("S3-R4 request seed must be null")
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
        self.p2_mechanical_records: list[dict[str, object]] = []

    @staticmethod
    def _p2_hard_failure(content: str) -> tuple[str | None, int, int, str]:
        visible = content.strip()
        characters = len(visible)
        words = len(visible.split())
        if not visible:
            failure = "empty_visible_content"
        elif characters > P2_BOUNDEDNESS_HARD_MAX_CHARACTERS:
            failure = "visible_unicode_character_limit"
        elif words > P2_BOUNDEDNESS_HARD_MAX_WORDS:
            failure = "whitespace_delimited_word_limit"
        else:
            failure = None
        digest = hashlib.sha256(visible.encode("utf-8")).hexdigest()
        return failure, characters, words, digest

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ) -> ExperimentCompletion:
        is_p2 = question_id.endswith(":form-p2")
        try:
            completion = super().complete_named(
                question_id,
                messages,
                output_kind=output_kind,
            )
        except StructureProposalError:
            if is_p2 and self.last_failure_metadata is not None:
                record = dict(self.last_failure_metadata)
                record.update(
                    {
                        "admitted": False,
                        "failure": "non_stop_finish_reason",
                    }
                )
                self.p2_mechanical_records.append(record)
            raise

        if not is_p2:
            return completion

        failure, characters, words, digest = self._p2_hard_failure(completion.content)
        self.p2_mechanical_records.append(
            {
                "question_id": question_id,
                "finish_reason": "stop",
                "visible_unicode_characters": characters,
                "whitespace_delimited_words": words,
                "content_sha256": digest,
                "reasoning_field_status": "absent_or_empty_verified",
                "admitted": failure is None,
                "failure": failure,
            }
        )
        if failure is not None:
            raise StructureProposalError(f"S3-R4 P2 hard admission failed: {failure}")
        return completion
