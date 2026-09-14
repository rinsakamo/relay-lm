from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import httpx

from relaylm.v2_cognitive_ir_role_accessible_generic import (
    MAX_OUTPUT_TOKENS,
    TEMPERATURE,
    build_formation_messages,
)
from relaylm.v2_cognitive_ir_role_accessible_generic_physical import (
    FrozenConsumerIdentity,
    RoleAccessibleGenericCampaignResult,
    generate_synthetic_shared_family,
    physical_call_plan,
    run_role_accessible_generic_campaign,
)
from tools.v2_cognitive_ir_s2_selected_llama_cpp import (
    LlamaCppThinkingOffInputCounter,
)
from tools.v2_cognitive_ir_s3_llama_cpp import (
    S3_LLAMA_CPP_ENDPOINT,
    S3_LLAMA_CPP_REASONING_EFFORT,
    S3_LLAMA_CPP_TIMEOUT_SECONDS,
)
from tools.v2_cognitive_ir_s3_r5_llama_cpp import S3R5LlamaCppClient


@dataclass(frozen=True, slots=True)
class RoleAccessibleGenericInputCounterPreflight:
    total_input_tokens: int
    framing_input_tokens: int
    request_attempts: int
    request_completions: int


def preflight_role_accessible_generic_input_counter(
    *, base_url: str, model: str
) -> RoleAccessibleGenericInputCounterPreflight:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(f"E5-RA1 endpoint must be exactly {S3_LLAMA_CPP_ENDPOINT}")
    family = generate_synthetic_shared_family(91_500_000_000_001)
    messages = build_formation_messages(family)
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
                "messages": list(messages),
                "stream": False,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "reasoning_effort": S3_LLAMA_CPP_REASONING_EFFORT,
                "response_format": S3R5LlamaCppClient._response_format(
                    "e5-ra1:synthetic-preflight",
                    "rule",
                ),
            }
        )
        return RoleAccessibleGenericInputCounterPreflight(
            total_input_tokens=counted.total_input_tokens,
            framing_input_tokens=counted.required_input_framing_tokens,
            request_attempts=counter.request_attempts,
            request_completions=counter.request_completions,
        )
    finally:
        client.close()


class RoleAccessibleGenericLlamaCppClient(S3R5LlamaCppClient):
    """Native S3-R5 rule/vector llama.cpp transport for E5-RA1."""

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
        if self._before_call is not None:
            self._before_call()
            self.live_binding_checks += 1
        return super().complete_named(
            question_id,
            messages,
            output_kind=output_kind,
        )


@dataclass(frozen=True, slots=True)
class RoleAccessibleGenericLlamaCppRun:
    result: RoleAccessibleGenericCampaignResult
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int
    p2_hard_admissions: int
    p2_records: tuple[Mapping[str, object], ...]
    live_binding_checks: int


def run_llama_cpp_role_accessible_generic(
    *,
    base_url: str,
    model: str,
    frozen_identity: FrozenConsumerIdentity,
    before_call: Callable[[], None] | None = None,
    family_factory=None,
) -> RoleAccessibleGenericLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(f"E5-RA1 endpoint must be exactly {S3_LLAMA_CPP_ENDPOINT}")
    frozen_identity.validate()
    if frozen_identity.model != model:
        raise ValueError("frozen consumer model differs from E5-RA1 request model")

    client = RoleAccessibleGenericLlamaCppClient(
        base_url=base_url,
        model=model,
        before_call=before_call,
    )
    try:
        result = run_role_accessible_generic_campaign(
            client,
            frozen_identity=frozen_identity,
            family_factory=family_factory,
        )
        if client.provider_attempts != result.semantic_calls:
            raise ValueError("E5-RA1 provider attempt ledger drifted")
        if client.provider_completions != result.provider_completions:
            raise ValueError("E5-RA1 provider completion ledger drifted")
        if client.input_count_attempts != result.input_token_requests:
            raise ValueError("E5-RA1 input-count attempt ledger drifted")
        if client.input_count_completions != result.input_token_completions:
            raise ValueError("E5-RA1 input-count completion ledger drifted")
        if client.live_binding_checks != client.provider_attempts:
            raise ValueError("E5-RA1 live binding did not cover every semantic attempt")
        return RoleAccessibleGenericLlamaCppRun(
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
    "RoleAccessibleGenericInputCounterPreflight",
    "RoleAccessibleGenericLlamaCppClient",
    "RoleAccessibleGenericLlamaCppRun",
    "preflight_role_accessible_generic_input_counter",
    "run_llama_cpp_role_accessible_generic",
]
