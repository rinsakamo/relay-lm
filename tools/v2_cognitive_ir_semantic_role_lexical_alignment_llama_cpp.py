from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import httpx

from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
)
from relaylm.v2_cognitive_ir_semantic_role_lexical_alignment import (
    MAX_OUTPUT_TOKENS,
    TEMPERATURE,
    response_format,
)
from relaylm.v2_cognitive_ir_semantic_role_lexical_alignment_physical import (
    SemanticRoleLexicalAlignmentCampaignResult,
    physical_call_plan,
    run_semantic_role_lexical_alignment_campaign,
)
from tools.v2_cognitive_ir_s3_llama_cpp import (
    S3LlamaCppClient,
    S3_LLAMA_CPP_ENDPOINT,
    S3_LLAMA_CPP_TIMEOUT_SECONDS,
)
from tools.v2_cognitive_ir_strict_output_interface_qualification_llama_cpp import (
    StrictOutputInputCounterPreflight,
    preflight_strict_output_input_counter,
)


class SemanticRoleLexicalAlignmentLlamaCppClient(S3LlamaCppClient):
    """Native wire-only strict-json-schema llama.cpp transport for E4-LX1."""

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

    @staticmethod
    def _response_format(
        question_id: str,
        output_kind: str,
    ) -> dict[str, object] | None:
        if output_kind != "semantic_role_payload":
            raise ValueError(
                f"unsupported E4-LX1 output kind for {question_id}: {output_kind}"
            )
        return response_format()

    def complete_named(
        self,
        question_id: str,
        messages: tuple[dict[str, str], ...],
        *,
        output_kind: str,
    ):
        if self._before_call is not None:
            self._before_call()
            self.live_binding_checks += 1
        return super().complete_named(
            question_id,
            messages,
            output_kind=output_kind,
        )


@dataclass(frozen=True, slots=True)
class SemanticRoleLexicalAlignmentLlamaCppRun:
    result: SemanticRoleLexicalAlignmentCampaignResult
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int
    p2_hard_admissions: int
    p2_records: tuple[Mapping[str, object], ...]
    live_binding_checks: int


def run_llama_cpp_semantic_role_lexical_alignment(
    *,
    base_url: str,
    model: str,
    frozen_identity: FrozenConsumerIdentity,
    before_call: Callable[[], None] | None = None,
    family_factory=None,
) -> SemanticRoleLexicalAlignmentLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(f"E4-LX1 endpoint must be exactly {S3_LLAMA_CPP_ENDPOINT}")
    frozen_identity.validate()
    if frozen_identity.model != model:
        raise ValueError("frozen consumer model differs from E4-LX1 request model")

    client = SemanticRoleLexicalAlignmentLlamaCppClient(
        base_url=base_url,
        model=model,
        before_call=before_call,
    )
    try:
        result = run_semantic_role_lexical_alignment_campaign(
            client,
            frozen_identity=frozen_identity,
            family_factory=family_factory,
        )
        if client.provider_attempts != result.semantic_calls:
            raise ValueError("E4-LX1 provider attempt ledger drifted")
        if client.provider_completions != result.provider_completions:
            raise ValueError("E4-LX1 provider completion ledger drifted")
        if client.input_count_attempts != result.input_token_requests:
            raise ValueError("E4-LX1 input-count attempt ledger drifted")
        if client.input_count_completions != result.input_token_completions:
            raise ValueError("E4-LX1 input-count completion ledger drifted")
        if client.live_binding_checks != client.provider_attempts:
            raise ValueError("E4-LX1 live binding did not cover every semantic attempt")

        return SemanticRoleLexicalAlignmentLlamaCppRun(
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


__all__ = [
    "StrictOutputInputCounterPreflight",
    "preflight_strict_output_input_counter",
    "SemanticRoleLexicalAlignmentLlamaCppClient",
    "SemanticRoleLexicalAlignmentLlamaCppRun",
    "run_llama_cpp_semantic_role_lexical_alignment",
]
