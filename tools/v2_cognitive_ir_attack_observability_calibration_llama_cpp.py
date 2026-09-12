from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from relaylm.v2_cognitive_ir_attack_observability_calibration import (
    AttackObservabilityCalibrationResult,
    run_attack_observability_calibration,
)
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_ENDPOINT
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    SharedFloorLlamaCppClient,
)


@dataclass(frozen=True, slots=True)
class AttackObservabilityLlamaCppRun:
    result: AttackObservabilityCalibrationResult
    provider_attempts: int
    provider_completions: int
    input_count_attempts: int
    input_count_completions: int
    p2_hard_admissions: int
    p2_records: tuple[dict[str, object], ...]
    live_binding_checks: int


def run_llama_cpp_attack_observability_calibration(
    *,
    base_url: str,
    model: str,
    before_call: Callable[[], None] | None = None,
) -> AttackObservabilityLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(
            f"attack-observability llama.cpp endpoint must be {S3_LLAMA_CPP_ENDPOINT}"
        )

    clients: list[SharedFloorLlamaCppClient] = []

    def factory(
        visibility: int,
        call_plan: tuple[str, ...],
    ) -> SharedFloorLlamaCppClient:
        del visibility
        client = SharedFloorLlamaCppClient(
            base_url=S3_LLAMA_CPP_ENDPOINT,
            model=model,
            call_plan=call_plan,
            before_call=before_call,
        )
        clients.append(client)
        return client

    try:
        result = run_attack_observability_calibration(factory)
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
        live_binding_checks = sum(client.live_binding_checks for client in clients)

        if provider_attempts != result.semantic_calls:
            raise ValueError("attack-observability provider attempt total drifted")
        if provider_completions != result.semantic_calls:
            raise ValueError("attack-observability provider completion total drifted")
        if input_count_attempts != result.input_token_requests:
            raise ValueError("attack-observability input-token attempt total drifted")
        if input_count_completions != result.input_token_requests:
            raise ValueError("attack-observability input-token completion total drifted")
        if p2_records:
            raise ValueError("attack-observability unexpectedly invoked P2 formation")
        if live_binding_checks not in (0, result.semantic_calls):
            raise ValueError(
                "attack-observability live binding hook did not cover every semantic call"
            )

        return AttackObservabilityLlamaCppRun(
            result=result,
            provider_attempts=provider_attempts,
            provider_completions=provider_completions,
            input_count_attempts=input_count_attempts,
            input_count_completions=input_count_completions,
            p2_hard_admissions=0,
            p2_records=(),
            live_binding_checks=live_binding_checks,
        )
    finally:
        for client in clients:
            client.close()
