from __future__ import annotations

from collections.abc import Callable

from relaylm.v2_cognitive_ir_shared_floor_calibration_v2 import (
    run_shared_floor_v2_calibration,
)
from tools.v2_cognitive_ir_s3_llama_cpp import S3_LLAMA_CPP_ENDPOINT
from tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp import (
    SharedFloorLlamaCppClient,
    SharedFloorLlamaCppRun,
)


def run_llama_cpp_shared_floor_calibration_v2(
    *,
    base_url: str,
    model: str,
    before_call: Callable[[], None] | None = None,
) -> SharedFloorLlamaCppRun:
    if base_url.rstrip("/") != S3_LLAMA_CPP_ENDPOINT:
        raise ValueError(
            f"shared-floor-v2 llama.cpp endpoint must be {S3_LLAMA_CPP_ENDPOINT}"
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
        result = run_shared_floor_v2_calibration(factory)
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
            raise ValueError("shared-floor-v2 provider attempt total drifted")
        if provider_completions != result.semantic_calls:
            raise ValueError("shared-floor-v2 provider completion total drifted")
        if input_count_attempts != result.input_token_requests:
            raise ValueError("shared-floor-v2 input-token attempt total drifted")
        if input_count_completions != result.input_token_requests:
            raise ValueError("shared-floor-v2 input-token completion total drifted")
        if p2_hard_admissions != 6 * len(result.candidates):
            raise ValueError("shared-floor-v2 P2 hard-admission total drifted")
        if live_binding_checks not in (0, result.semantic_calls):
            raise ValueError(
                "shared-floor-v2 live binding hook did not cover every semantic call"
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
