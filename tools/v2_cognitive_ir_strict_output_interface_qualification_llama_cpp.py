from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass

import httpx

from relaylm.v2_cognitive_ir_semantic_reconstruction_physical import (
    FrozenConsumerIdentity,
)
from relaylm.v2_cognitive_ir_strict_output_interface_qualification import (
    MAX_OUTPUT_TOKENS,
    TEMPERATURE,
    build_neutral_messages,
    response_format,
)
from relaylm.v2_cognitive_ir_strict_output_interface_qualification_physical import (
    StrictOutputInterfaceQualificationResult,
    physical_call_plan,
    run_strict_output_interface_qualification,
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
class StrictOutputInputCounterPreflight:
    total_input_tokens: int
    framing_input_tokens: int
    request_attempts: int
    request_completions: int


def _synthetic_preflight_messages() -> tuple[dict[str, str], ...]:
    return build_neutral_messages(
        {
            "operation": "affine_permutation",
            "permutation": [2, 0, 3, 1],
            "offsets": [1, 0, 2, 3],
            "modulus": 10,
            "provenance_handles": ["ifq1_synthetic_preflight"],
        }
    )


def preflight_strict_output_input_counter(
    *,
    base_url: str,
    model: str,
) -> StrictOutputInputCounterPreflight:
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
                "messages": list(_synthetic_preflight_messages()),
                "stream": False,
                "temperature": TEMPERATURE,
                "max_tokens": MAX_OUTPUT_TOKENS,
                "reasoning_effort": S3_LLAMA_CPP_REASONING_EFFORT,
                "response_format": response_format(),
            }
        )
        return StrictOutputInputCounterPreflight(
            total_input_tokens=counted.total_input_tokens,
            framing_input_tokens=counted.required_input_framing_tokens,
            request_attempts=counter.request_attempts,
            request_completions=counter.request_completions,
        )
    finally:
        client.close()


class StrictOutputInterfaceQualificationLlamaCppClient(S3LlamaCppClient):
    """One-interface native-json-schema llama.cpp transport for E4-IFQ1."""

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
        if output_kind != "strict_reference_payload":
            raise ValueError(
                f"unsupported IFQ1 output kind for {question_id}: {output_kind}"
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
class StrictOutputInterfaceLlamaCppRun:
    result: StrictOutputInterfaceQualificationResult
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int
    p2_hard_admissions: int
    p2_records: tuple[Mapping[str, object], ...]
    live_binding_checks: int


def run_llama_cpp_strict_output_interface_qualification(
    *,
    base_url: str,
    model: str,
    frozen_identity: FrozenConsumerIdentity,
    before_call: Callable[[], None] | None = None,
    payload_factory=None,
) -> StrictOutputInterfaceLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(
            f"IFQ1 endpoint must be exactly {S3_LLAMA_CPP_ENDPOINT}"
        )
    frozen_identity.validate()
    if frozen_identity.model != model:
        raise ValueError("frozen consumer model differs from IFQ1 request model")

    client = StrictOutputInterfaceQualificationLlamaCppClient(
        base_url=base_url,
        model=model,
        before_call=before_call,
    )
    try:
        result = run_strict_output_interface_qualification(
            client,
            frozen_identity=frozen_identity,
            payload_factory=payload_factory,
        )
        if client.provider_attempts != result.semantic_calls:
            raise ValueError("IFQ1 provider attempt ledger drifted")
        if client.input_count_attempts != result.input_token_requests:
            raise ValueError("IFQ1 input-count ledger drifted")
        if client.live_binding_checks != client.provider_attempts:
            raise ValueError("IFQ1 live binding did not cover every semantic attempt")
        if result.completed:
            if client.provider_completions != result.semantic_calls:
                raise ValueError("completed IFQ1 provider completion ledger drifted")
            if client.input_count_completions != result.input_token_requests:
                raise ValueError("completed IFQ1 input-count completion ledger drifted")

        return StrictOutputInterfaceLlamaCppRun(
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
