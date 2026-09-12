from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from relaylm.v2_cognitive_ir_current_law_certificate_qualification import (
    CurrentLawCertificateQualificationResult,
    g1_call_plan,
    run_current_law_certificate_qualification,
)
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_ENDPOINT
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    SharedFloorLlamaCppClient,
)


@dataclass(frozen=True, slots=True)
class CurrentLawCertificateLlamaCppRun:
    result: CurrentLawCertificateQualificationResult
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int
    p2_hard_admissions: int
    p2_records: tuple[dict[str, object], ...]
    live_binding_checks: int


def run_llama_cpp_current_law_certificate_qualification(
    *,
    base_url: str,
    model: str,
    before_call: Callable[[], None] | None = None,
) -> CurrentLawCertificateLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(
            f"current-law certificate llama.cpp endpoint must be {S3_LLAMA_CPP_ENDPOINT}"
        )

    client = SharedFloorLlamaCppClient(
        base_url=S3_LLAMA_CPP_ENDPOINT,
        model=model,
        call_plan=g1_call_plan(),
        before_call=before_call,
    )
    try:
        result = run_current_law_certificate_qualification(client)
        if client.provider_attempts != result.semantic_calls:
            raise ValueError("G1 provider attempt total drifted")
        if client.provider_completions != result.semantic_calls:
            raise ValueError("G1 provider completion total drifted")
        if client.input_count_attempts != result.input_token_requests:
            raise ValueError("G1 input-token attempt total drifted")
        if client.input_count_completions != result.input_token_requests:
            raise ValueError("G1 input-token completion total drifted")
        if client.p2_mechanical_records:
            raise ValueError("G1 unexpectedly invoked P2 formation")
        if client.live_binding_checks not in (0, result.semantic_calls):
            raise ValueError("G1 live binding hook did not cover every semantic call")

        return CurrentLawCertificateLlamaCppRun(
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
