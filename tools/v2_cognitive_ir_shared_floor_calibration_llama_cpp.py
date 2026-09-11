from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from relaylm.v2_cognitive_ir_shared_floor_calibration import (
    SharedFloorCalibrationResult,
    run_shared_floor_calibration,
)
from relaylm.v2_cognitive_ir_s3_r4 import S3_R4_MAX_OUTPUT_TOKENS
from tools.v2_cognitive_ir_s3_llama_cpp import (
    S3_LLAMA_CPP_ENDPOINT,
    S3_LLAMA_CPP_TIMEOUT_SECONDS,
)
from tools.v2_cognitive_ir_s3_r4_llama_cpp import S3R4LlamaCppClient


@dataclass(frozen=True, slots=True)
class SharedFloorLlamaCppRun:
    result: SharedFloorCalibrationResult
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int
    p2_hard_admissions: int
    p2_records: tuple[dict[str, object], ...]
    live_binding_checks: int


class SharedFloorLlamaCppClient(S3R4LlamaCppClient):
    """R4 transport plus an optional host-owned pre-call binding hook."""

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        call_plan: tuple[str, ...],
        before_call: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(
            base_url=base_url,
            model=model,
            call_plan=call_plan,
            timeout_seconds=S3_LLAMA_CPP_TIMEOUT_SECONDS,
            max_output_tokens=S3_R4_MAX_OUTPUT_TOKENS,
            temperature=0.0,
            seed=None,
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


def run_llama_cpp_shared_floor_calibration(
    *,
    base_url: str,
    model: str,
    before_call: Callable[[], None] | None = None,
) -> SharedFloorLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(
            f"shared-floor llama.cpp endpoint must be {S3_LLAMA_CPP_ENDPOINT}"
        )

    clients: list[SharedFloorLlamaCppClient] = []

    def factory(
        difficulty: str,
        call_plan: tuple[str, ...],
    ) -> SharedFloorLlamaCppClient:
        del difficulty
        client = SharedFloorLlamaCppClient(
            base_url=S3_LLAMA_CPP_ENDPOINT,
            model=model,
            call_plan=call_plan,
            before_call=before_call,
        )
        clients.append(client)
        return client

    try:
        result = run_shared_floor_calibration(factory)
        provider_attempts = sum(client.provider_attempts for client in clients)
        provider_completions = sum(client.provider_completions for client in clients)
        input_count_attempts = sum(client.input_count_attempts for client in clients)
        input_count_completions = sum(
            client.input_count_completions for client in clients
        )
        p2_records = tuple(
            dict(record)
            for client in clients
            for record in client.p2_mechanical_records
        )
        p2_hard_admissions = sum(
            bool(record.get("admitted")) for record in p2_records
        )
        live_binding_checks = sum(client.live_binding_checks for client in clients)

        if provider_attempts != result.semantic_calls:
            raise ValueError("shared-floor provider attempt total drifted")
        if provider_completions != result.semantic_calls:
            raise ValueError("shared-floor provider completion total drifted")
        if input_count_attempts != result.input_token_requests:
            raise ValueError("shared-floor input-token attempt total drifted")
        if input_count_completions != result.input_token_requests:
            raise ValueError("shared-floor input-token completion total drifted")
        if p2_hard_admissions != 6 * len(result.candidates):
            raise ValueError("shared-floor P2 hard-admission total drifted")
        if live_binding_checks not in (0, result.semantic_calls):
            raise ValueError(
                "shared-floor live binding hook did not cover every semantic call"
            )

        return SharedFloorLlamaCppRun(
            result=result,
            provider_attempts=provider_attempts,
            provider_completions=provider_completions,
            input_count_attempts=input_count_attempts,
            input_count_completions=input_count_completions,
            p2_hard_admissions=p2_hard_admissions,
            p2_records=p2_records,
            live_binding_checks=live_binding_checks,
        )
    finally:
        for client in clients:
            client.close()
