from __future__ import annotations

from typing import Mapping

import httpx

from relaylm.v2_cognitive_ir_p2_boundedness_qual_v2 import (
    P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
    P2_BOUNDEDNESS_HARD_MAX_WORDS,
    P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS,
    P2_BOUNDEDNESS_QUAL_V2_LABEL,
    P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
    P2_BOUNDEDNESS_TARGET_MAX_WORDS,
    P2_BOUNDEDNESS_TARGET_MIN_WORDS,
)
from relaylm.v2_transfer_actual_model import StructureProposalError
from tools.v2_cognitive_ir_p2_termination_qual_llama_cpp import (
    P2TerminationQualificationClient,
)
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_TIMEOUT_SECONDS


class P2BoundednessQualificationV2Client(P2TerminationQualificationClient):
    """Fresh #2571 P2 qualification with unchanged hard admission and target margin metadata."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        call_plan: tuple[str, ...],
        timeout_seconds: float = S3_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens: int = P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS,
        temperature: int | float = 0.0,
        seed: int | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if max_output_tokens != P2_BOUNDEDNESS_MAX_OUTPUT_TOKENS:
            raise StructureProposalError("P2 boundedness qualification output ceiling must be exactly 1024")
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

    @property
    def qualification_identity(self) -> Mapping[str, object]:
        base = dict(super().qualification_identity)
        base.update(
            {
                "label": P2_BOUNDEDNESS_QUAL_V2_LABEL,
                "target_min_words": P2_BOUNDEDNESS_TARGET_MIN_WORDS,
                "target_max_words": P2_BOUNDEDNESS_TARGET_MAX_WORDS,
                "target_max_unicode_characters": P2_BOUNDEDNESS_TARGET_MAX_CHARACTERS,
                "hard_max_words": P2_BOUNDEDNESS_HARD_MAX_WORDS,
                "hard_max_unicode_characters": P2_BOUNDEDNESS_HARD_MAX_CHARACTERS,
            }
        )
        return base
