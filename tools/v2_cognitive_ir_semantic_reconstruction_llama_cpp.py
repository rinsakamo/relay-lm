from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import httpx

from relaylm.v2_cognitive_ir_semantic_reconstruction import (
    MAX_OUTPUT_TOKENS,
    TEMPERATURE,
)
from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
    SemanticReconstructionCampaignResult,
    physical_call_plan,
    run_semantic_reconstruction_campaign,
)
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    LlamaCppThinkingOffInputCounter,
)
from tools.v2_cognitive_ir_s3_llama_cpp import (
    S3LlamaCppClient,
    S3_LLAMA_CPP_ENDPOINT,
    S3_LLAMA_CPP_REASONING_EFFORT,
    S3_LLAMA_CPP_TIMEOUT_SECONDS,
)


@dataclass(frozen=True, slots=True)
class SemanticReconstructionInputCounterPreflight:
    total_input_tokens: int
    framing_input_tokens: int
    request_attempts: int
    request_completions: int


def preflight_semantic_reconstruction_input_counter(
    *,
    base_url: str,
    model: str,
) -> SemanticReconstructionInputCounterPreflight:
    client = httpx.Client(timeout=30.0)
    try:
        counter = LlamaCppThinkingOffInputCounter(
            base_url=base_url,
            model=model,
            http_client=client,
        )
        counted = counter.count_input(
            {
                "model": model,
                "messages": [
                    {
                        "role": "system",
                        "content": "RelayLM semantic reconstruction counter preflight.",
                    },
                    {"role": "user", "content": "synthetic-preflight"},
                ],
                "stream": False,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "reasoning_effort": S3_LLAMA_CPP_REASONING_EFFORT,
            }
        )
        return SemanticReconstructionInputCounterPreflight(
            total_input_tokens=counted.total_input_tokens,
            framing_input_tokens=counted.required_input_framing_tokens,
            request_attempts=counter.request_attempts,
            request_completions=counter.request_completions,
        )
    finally:
        client.close()


class SemanticReconstructionLlamaCppClient(S3LlamaCppClient):
    """Plain-text llama.cpp transport for the #2709 accessibility discriminator."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        before_call: Callable[[], None] | None = None,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            model=model,
            call_plan=physical_call_plan(),
            timeout_seconds=S3_LLAMA_CPP_TIMEOUT_SECONDS,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            temperature=TEMPERATURE,
            seed=None,
            http_client=http_client,
        )
        self._before_call = before_call
        self.live_binding_checks = 0

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ):
        if output_kind != "text":
            raise ValueError(
                "semantic reconstruction must use ordinary text output without schema repair"
            )
        if self._before_call is not None:
            self._before_call()
            self.live_binding_checks += 1
        return super().complete_named(
            question_id,
            messages,
            output_kind="text",
        )


@dataclass(frozen=True, slots=True)
class SemanticReconstructionLlamaCppRun:
    result: SemanticReconstructionCampaignResult
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int
    p2_hard_admissions: int
    p2_records: tuple[dict[str, object], ...]
    live_binding_checks: int


def run_llama_cpp_semantic_reconstruction(
    *,
    base_url: str,
    model: str,
    frozen_identity: FrozenConsumerIdentity,
    before_call: Callable[[], None] | None = None,
    family_factory=None,
) -> SemanticReconstructionLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(
            f"semantic reconstruction endpoint must be {S3_LLAMA_CPP_ENDPOINT}"
        )
    frozen_identity.validate()
    if frozen_identity.model != model:
        raise ValueError("frozen consumer model differs from request model")

    client = SemanticReconstructionLlamaCppClient(
        base_url=base_url,
        model=model,
        before_call=before_call,
    )
    try:
        result = run_semantic_reconstruction_campaign(
            client,
            frozen_identity=frozen_identity,
            family_factory=family_factory,
        )
        if client.provider_attempts != result.semantic_calls:
            raise ValueError("semantic reconstruction provider attempt ledger drifted")
        if client.input_count_attempts != result.input_token_requests:
            raise ValueError("semantic reconstruction input-count ledger drifted")
        if client.live_binding_checks != client.provider_attempts:
            raise ValueError(
                "semantic reconstruction live binding did not cover every semantic attempt"
            )
        if result.completed:
            if client.provider_completions != result.semantic_calls:
                raise ValueError(
                    "completed semantic reconstruction provider completion ledger drifted"
                )
            if client.input_count_completions != result.input_token_requests:
                raise ValueError(
                    "completed semantic reconstruction input-count completion ledger drifted"
                )

        return SemanticReconstructionLlamaCppRun(
            result=result,
            provider_attempts=client.provider_attempts,
            provider_completions=client.provider_completions,
            input_count_attempts=client.input_count_attempts,
            input_count_completions=client.input_count_completions,
            p2_hard_admissions=0,
            p2_records=(),
            live_binding_checks=client.live_binding_checks,
        )
    finally:
        client.close()
