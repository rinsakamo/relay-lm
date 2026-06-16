#!/usr/bin/env python3
"""Smoke checks for the pure client-history exclusion apply contract."""

from __future__ import annotations

import copy
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_history_exclusion_apply import (
    build_client_history_exclusion_apply,
    build_client_history_exclusion_apply_diagnostics,
    build_client_history_exclusion_apply_node_result,
)
from relaylm.client_history_exclusion_preflight import (
    ClientHistoryExclusionPreflightResult,
    build_client_history_exclusion_preflight,
)
from relaylm.client_message_canonicalization import (
    build_client_message_canonicalization_dry_run,
)

SENTINELS = (
    "relay-owned system sentinel",
    "prior user sentinel",
    "prior assistant sentinel",
    "current user sentinel",
    "multimodal URL sentinel",
    "raw instruction sentinel",
    "projection secret sentinel",
)


def require(condition: bool, detail: Any) -> None:
    if not condition:
        raise AssertionError(detail)


def no_leak(value: Any) -> None:
    rendered = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    for sentinel in SENTINELS:
        require(sentinel not in rendered, (sentinel, rendered))


def payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": "relaylm-default",
        "messages": messages,
        "stream": False,
        "temperature": 0.25,
    }


def preflight_for(
    original_payload: dict[str, Any],
    *,
    lookup_status: str | None = None,
) -> ClientHistoryExclusionPreflightResult:
    artifact = build_client_message_canonicalization_dry_run(
        original_payload,
        enabled=True,
        managed_route=True,
    )

    lookup = None
    if lookup_status is not None:
        lookup = type("Lookup", (), {"status": lookup_status})()

    result = build_client_history_exclusion_preflight(
        original_payload,
        artifact,
        lookup,
        enabled=True,
        managed_route=True,
    )
    require(result is not None, original_payload)
    return result


def compiled_payload_for(original_payload: dict[str, Any]) -> dict[str, Any]:
    compiled = copy.deepcopy(original_payload)
    compiled["messages"] = [
        {"role": "system", "content": "relay-owned system sentinel"},
        *copy.deepcopy(original_payload["messages"]),
    ]
    return compiled


def test_all() -> None:
    original_payload = payload(
        [
            {"role": "user", "content": "prior user sentinel"},
            {"role": "assistant", "content": "prior assistant sentinel"},
            {"role": "user", "content": "current user sentinel"},
        ]
    )
    preflight = preflight_for(original_payload)
    compiled = compiled_payload_for(original_payload)

    # Default-off produces no contract result.
    require(
        build_client_history_exclusion_apply(
            compiled,
            preflight,
            enabled=False,
            dry_run_only=True,
            managed_route=True,
            compiler_used=True,
        )
        is None,
        "default-off",
    )
    require(build_client_history_exclusion_apply_node_result(None) is None, "node")
    print("ok default-off")

    # Pass-through is explicitly skipped and never receives a private candidate.
    skipped = build_client_history_exclusion_apply(
        compiled,
        preflight,
        enabled=True,
        dry_run_only=False,
        managed_route=False,
        compiler_used=False,
    )
    require(
        skipped
        and skipped.status == "skipped"
        and skipped.forwarded_payload is None
        and skipped.blocked_reasons == ("pass_through_route_exempt",),
        skipped,
    )
    skipped_node = build_client_history_exclusion_apply_node_result(skipped)
    require(
        skipped_node
        and skipped_node.status == "skipped"
        and skipped_node.decision == "pass_through_route_exempt",
        skipped_node,
    )
    no_leak(skipped_node.to_log_dict())
    print("ok pass-through skip")

    # Dry-run builds a detached private candidate but does not mark mutation applied.
    original_snapshot = copy.deepcopy(original_payload)
    compiled_snapshot = copy.deepcopy(compiled)
    ready = build_client_history_exclusion_apply(
        compiled,
        preflight,
        enabled=True,
        dry_run_only=True,
        managed_route=True,
        compiler_used=True,
    )
    require(
        ready
        and ready.status == "ready"
        and ready.payload_candidate_present
        and not ready.payload_mutation_applied
        and ready.relay_owned_prefix_message_count == 1
        and ready.original_compiled_message_count == 4
        and ready.forwarded_message_count == 2
        and ready.excluded_client_message_count == 2
        and ready.preserved_client_message_count == 1,
        ready,
    )
    candidate = ready.forwarded_payload
    require(
        candidate
        and candidate["messages"]
        == [compiled["messages"][0], original_payload["messages"][-1]]
        and candidate["temperature"] == 0.25,
        candidate,
    )
    require(
        original_payload == original_snapshot and compiled == compiled_snapshot,
        (original_payload, compiled),
    )
    candidate["messages"][0]["content"] = "mutated candidate"
    candidate["messages"][1]["content"] = "mutated user candidate"
    require(
        compiled["messages"][0]["content"] == "relay-owned system sentinel"
        and preflight.current_user_message["content"] == "current user sentinel",
        (compiled, preflight.current_user_message),
    )
    ready_diagnostics = build_client_history_exclusion_apply_diagnostics(ready)
    ready_node = build_client_history_exclusion_apply_node_result(ready)
    require(
        ready_diagnostics
        and ready_diagnostics["payload_candidate_present"] is True
        and ready_diagnostics["content_bearing_candidate_persisted"] is False
        and ready_node
        and ready_node.status == "diagnostic_only"
        and ready_node.decision == "client_history_exclusion_apply_ready",
        (ready_diagnostics, ready_node),
    )
    no_leak(ready_diagnostics)
    no_leak(ready_node.to_log_dict())
    print("ok dry-run detached candidate")

    # Apply mode returns the same bounded shape and marks mutation applicable.
    applied = build_client_history_exclusion_apply(
        compiled_snapshot,
        preflight,
        enabled=True,
        dry_run_only=False,
        managed_route=True,
        compiler_used=True,
    )
    require(
        applied
        and applied.status == "applied"
        and applied.payload_mutation_applied
        and applied.forwarded_payload
        and len(applied.forwarded_payload["messages"]) == 2,
        applied,
    )
    applied_node = build_client_history_exclusion_apply_node_result(applied)
    require(
        applied_node
        and applied_node.status == "applied"
        and applied_node.decision == "client_history_exclusion_applied",
        applied_node,
    )
    no_leak(applied_node.to_log_dict())
    print("ok apply result")

    # Multimodal current-turn content is deeply detached and preserved.
    multimodal_payload = payload(
        [
            {"role": "assistant", "content": "prior assistant sentinel"},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "current user sentinel"},
                    {
                        "type": "image_url",
                        "image_url": {"url": "multimodal URL sentinel"},
                    },
                ],
            },
        ]
    )
    multimodal_preflight = preflight_for(multimodal_payload)
    multimodal_compiled = compiled_payload_for(multimodal_payload)
    multimodal = build_client_history_exclusion_apply(
        multimodal_compiled,
        multimodal_preflight,
        enabled=True,
        dry_run_only=False,
        managed_route=True,
        compiler_used=True,
    )
    require(multimodal and multimodal.forwarded_payload, multimodal)
    multimodal_candidate = multimodal.forwarded_payload["messages"][-1]
    multimodal_candidate["content"][1]["image_url"]["url"] = "mutated"
    require(
        multimodal_payload["messages"][-1]["content"][1]["image_url"]["url"]
        == "multimodal URL sentinel"
        and multimodal_preflight.current_user_message["content"][1]["image_url"][
            "url"
        ]
        == "multimodal URL sentinel",
        multimodal,
    )
    no_leak(build_client_history_exclusion_apply_node_result(multimodal).to_log_dict())
    print("ok multimodal detach")

    # The first slice requires the compiled profile boundary.
    no_compiler = build_client_history_exclusion_apply(
        compiled_snapshot,
        preflight,
        enabled=True,
        dry_run_only=False,
        managed_route=True,
        compiler_used=False,
    )
    require(
        no_compiler
        and no_compiler.status == "blocked"
        and no_compiler.forwarded_payload is None
        and "compiled_profile_required" in no_compiler.blocked_reasons,
        no_compiler,
    )
    print("ok compiler required")

    # Cache-hit/miss instruction paths are deliberately deferred.
    instruction_payload = payload(
        [
            {"role": "system", "content": "raw instruction sentinel"},
            {"role": "user", "content": "current user sentinel"},
        ]
    )
    for lookup_status in ("hit", "miss"):
        instruction_preflight = preflight_for(
            instruction_payload,
            lookup_status=lookup_status,
        )
        instruction_compiled = compiled_payload_for(instruction_payload)
        blocked = build_client_history_exclusion_apply(
            instruction_compiled,
            instruction_preflight,
            enabled=True,
            dry_run_only=False,
            managed_route=True,
            compiler_used=True,
        )
        require(
            blocked
            and blocked.status == "blocked"
            and blocked.forwarded_payload is None
            and (
                "instruction_resolution_not_supported" in blocked.blocked_reasons
                or "preflight_not_ready" in blocked.blocked_reasons
            ),
            (lookup_status, blocked),
        )
        no_leak(build_client_history_exclusion_apply_node_result(blocked).to_log_dict())
    print("ok instruction paths deferred")

    # Exact compiled-layout and preflight contracts fail closed.
    malformed_cases = []
    malformed_cases.append(({**compiled_snapshot, "messages": "x"}, preflight, True))
    malformed_cases.append(({**compiled_snapshot, "messages": [1]}, preflight, True))
    malformed_cases.append(
        (
            {
                **compiled_snapshot,
                "messages": [
                    {"role": "assistant", "content": "not server prefix"},
                    *copy.deepcopy(original_snapshot["messages"]),
                ],
            },
            preflight,
            True,
        )
    )
    malformed_cases.append(
        (
            {
                **compiled_snapshot,
                "messages": copy.deepcopy(compiled_snapshot["messages"][:-1]),
            },
            preflight,
            True,
        )
    )
    malformed_cases.append((compiled_snapshot, None, True))
    malformed_cases.append(
        (
            compiled_snapshot,
            replace(preflight, status="blocked", history_exclusion_apply_ready=False),
            True,
        )
    )
    malformed_cases.append(
        (
            compiled_snapshot,
            replace(preflight, current_user_message={"role": "assistant", "content": "x"}),
            True,
        )
    )
    for malformed_payload, malformed_preflight, compiler_used in malformed_cases:
        blocked = build_client_history_exclusion_apply(
            malformed_payload,
            malformed_preflight,
            enabled=True,
            dry_run_only=False,
            managed_route=True,
            compiler_used=compiler_used,
        )
        require(
            blocked
            and blocked.status == "blocked"
            and blocked.forwarded_payload is None
            and blocked.blocked_reasons,
            blocked,
        )
        no_leak(build_client_history_exclusion_apply_node_result(blocked).to_log_dict())
    print("ok malformed contracts blocked")

    # Exact diagnostic projection drops fabricated strings and unsupported sources.
    fabricated = replace(
        applied,
        schema_version="projection secret sentinel",
        status="blocked",
        instruction_resolution_mode="projection secret sentinel",
        blocked_reasons=("projection secret sentinel",),
    )
    fabricated_diagnostics = build_client_history_exclusion_apply_diagnostics(
        fabricated
    )
    fabricated_node = build_client_history_exclusion_apply_node_result(fabricated)
    require(
        fabricated_diagnostics
        and fabricated_diagnostics["schema_version"]
        == "client_history_exclusion_apply.v0"
        and fabricated_diagnostics["instruction_resolution_mode"] == "blocked"
        and fabricated_diagnostics["blocked_reasons"] == []
        and fabricated_node
        and fabricated_node.status == "blocked",
        (fabricated_diagnostics, fabricated_node),
    )
    no_leak(fabricated_diagnostics)
    no_leak(fabricated_node.to_log_dict())

    invalid_preflight = build_client_history_exclusion_apply(
        compiled_snapshot,
        object(),  # type: ignore[arg-type]
        enabled=True,
        dry_run_only=False,
        managed_route=True,
        compiler_used=True,
    )
    require(
        invalid_preflight
        and invalid_preflight.status == "blocked"
        and invalid_preflight.blocked_reasons == ("preflight_type_invalid",),
        invalid_preflight,
    )
    print("ok exact diagnostics projection")


if __name__ == "__main__":
    test_all()
