from __future__ import annotations

import httpx

from relaylm.v2_cognitive_ir_s3_r5 import S3_R5_MAX_OUTPUT_TOKENS
from relaylm.v2_transfer_actual_model import StructureProposalError
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_TIMEOUT_SECONDS
from tools.v2_cognitive_ir_s3_r4_llama_cpp import S3R4LlamaCppClient


class S3R5LlamaCppClient(S3R4LlamaCppClient):
    """R5 transport: retain the qualified R4 P2/runtime admission contract."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        call_plan: tuple[str, ...],
        timeout_seconds: float = S3_LLAMA_CPP_TIMEOUT_SECONDS,
        max_output_tokens: int = S3_R5_MAX_OUTPUT_TOKENS,
        temperature: int | float = 0.0,
        seed: int | None = None,
        api_key: str | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        if max_output_tokens != S3_R5_MAX_OUTPUT_TOKENS:
            raise StructureProposalError("S3-R5 output ceiling must be exactly 1024")
        if temperature != 0:
            raise StructureProposalError("S3-R5 temperature must be zero")
        if seed is not None:
            raise StructureProposalError("S3-R5 request seed must be null")
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
