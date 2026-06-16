from __future__ import annotations

import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.audit_projection import (
    project_audit_metadata,
    registered_pipeline_node_projectors,
    registered_top_level_projectors,
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def assert_top_level_golden() -> None:
    result = project_audit_metadata(
        {
            "event": "backend_response",
            "status_code": 200,
            "content_type": "application/json; charset=utf-8",
            "memory_source": "memory_candidate_selection",
            "memory_selection_summary": {
                "total_candidates": 4,
                "eligible_count": 3,
                "selected_count": 1,
                "limit": 2,
                "character_id": "default",
                "selected_memory_ids": ["m1"],
                "excluded_disabled_ids": ["m4"],
                "excluded_character_ids": ["m3"],
                "state_counts": {
                    "active": 1,
                    "promoted": 1,
                    "demoted": 1,
                    "disabled": 1,
                    "private": 999,
                },
                "snippet_text": "must-not-project",
            },
            "relayrun_artifact": {
                "schema_version": "relayrun.runtime_checkpoint.v0",
                "content_free": True,
                "run_id": "run-1",
                "run_status": "diagnostics_only",
                "target_path_preview": "/tmp/private.md",
            },
            "unknown_artifact": {"status": "ready"},
        }
    )
    require(result.metadata["event"] == "backend_response", result)
    require(result.metadata["status_code"] == 200, result)
    require(
        result.metadata["memory_selection_summary"]["state_counts"]
        == {"active": 1, "promoted": 1, "demoted": 1, "disabled": 1},
        result,
    )
    require("snippet_text" not in result.metadata["memory_selection_summary"], result)
    require("target_path_preview" not in result.metadata["relayrun_artifact"], result)
    require("unknown_artifact" not in result.metadata, result)
    require(result.dropped_field_count == 3, result)
    require(result.unsupported_artifact_count == 1, result)
    print("ok top-level projectors have exact golden output")


def assert_node_isolation() -> None:
    result = project_audit_metadata(
        {
            "pipeline_node_results": [
                {
                    "node_name": "client_message_canonicalization",
                    "status": "diagnostic_only",
                    "decision": "current_request_evidence_identified",
                    "blocked_reasons": [],
                    "diagnostics": {
                        "schema_version": "client_message_canonicalization_dry_run.v0",
                        "enabled": True,
                        "diagnostics_only": True,
                        "content_free": True,
                        "managed_route": True,
                        "route_policy": "relay_managed",
                        "messages_present": True,
                        "message_count": 2,
                        "valid_message_count": 2,
                        "invalid_message_count": 0,
                        "system_message_count": 1,
                        "developer_message_count": 0,
                        "instruction_message_count": 1,
                        "instruction_text_message_count": 1,
                        "instruction_without_text_count": 0,
                        "current_user_turn_present": True,
                        "current_user_content_valid": True,
                        "current_user_content_kind": "text",
                        "current_user_text_part_count": 1,
                        "current_user_non_text_part_count": 0,
                        "current_user_invalid_part_count": 0,
                        "current_user_multimodal": False,
                        "messages_before_current_user_count": 1,
                        "messages_after_current_user_count": 0,
                        "prior_user_message_count": 0,
                        "prior_assistant_message_count": 0,
                        "tool_message_count": 0,
                        "assistant_tool_call_message_count": 0,
                        "post_user_tool_message_count": 0,
                        "active_tool_transaction_candidate": False,
                        "canonicalization_candidate_ready": True,
                        "runtime_schema_version": "relayctx_unpack_runtime.v0",
                    },
                    "artifacts": [
                        {
                            "artifact_name": "client_message_canonicalization_dry_run",
                            "schema_version": "client_message_canonicalization_dry_run.v0",
                            "present": True,
                            "diagnostics_only": True,
                            "content_free": True,
                            "applied": False,
                            "payload": "must-not-project",
                        }
                    ],
                    "future_node_field": True,
                },
                {
                    "node_name": "unknown_future_node",
                    "status": "diagnostic_only",
                    "diagnostics": {"content_free": True},
                },
            ]
        }
    )
    nodes = result.metadata["pipeline_node_results"]
    require(isinstance(nodes, list) and len(nodes) == 1, result)
    node = nodes[0]
    require("runtime_schema_version" not in node["diagnostics"], node)
    require("payload" not in node["artifacts"][0], node)
    require(result.dropped_field_count == 4, result)
    print("ok node projectors isolate diagnostics and reject unknown nodes")


def assert_numeric_contract() -> None:
    result = project_audit_metadata(
        {
            "memory_selection_summary": {
                "total_candidates": True,
                "eligible_count": 1.5,
                "selected_count": -1,
                "limit": "2",
                "selected_memory_ids": [],
                "excluded_disabled_ids": [],
                "excluded_character_ids": [],
                "state_counts": {
                    "active": 0,
                    "promoted": True,
                    "demoted": -1,
                    "disabled": 2,
                },
            },
            "latency_ms": 1.25,
        }
    )
    summary = result.metadata["memory_selection_summary"]
    require(summary["state_counts"] == {"active": 0, "disabled": 2}, result)
    require(result.metadata["latency_ms"] == 1.25, result)
    require(result.dropped_field_count == 6, result)
    print("ok count fields reject bool float negative and string values")


def assert_projection_counter_round_trip() -> None:
    result = project_audit_metadata(
        {
            "projection_dropped_field_count": 3,
            "projection_unsupported_artifact_count": 2,
        }
    )
    require(
        result.metadata
        == {
            "projection_dropped_field_count": 3,
            "projection_unsupported_artifact_count": 2,
        },
        result,
    )
    require(result.dropped_field_count == 0, result)
    require(result.unsupported_artifact_count == 0, result)

    invalid = project_audit_metadata(
        {
            "projection_dropped_field_count": True,
            "projection_unsupported_artifact_count": -1,
        }
    )
    require("projection_dropped_field_count" not in invalid.metadata, invalid)
    require("projection_unsupported_artifact_count" not in invalid.metadata, invalid)
    require(invalid.dropped_field_count == 2, invalid)
    print("ok projection counters survive reread and reject invalid values")


def assert_registry_hygiene() -> None:
    expected_top_level = {
        "bytes_avoided",
        "bytes_in",
        "bytes_out",
        "compile_decision_dry_run",
        "content_type",
        "error_class",
        "error_type",
        "event",
        "latency_ms",
        "memory_block_assembly",
        "memory_selection_summary",
        "memory_source",
        "pipeline_node_results",
        "projection_dropped_field_count",
        "projection_unsupported_artifact_count",
        "relayrun_artifact",
        "runtime_ctx_injection_result",
        "runtime_snippet_injection_result",
        "stable_prefix_block_ids",
        "stable_prefix_hash",
        "status_code",
        "token_memory_dry_run",
    }
    require(
        set(registered_top_level_projectors()) == expected_top_level,
        registered_top_level_projectors(),
    )
    expected_nodes = {
        "client_message_canonicalization",
        "client_instruction_extraction",
        "client_instruction_fingerprint",
        "client_instruction_identity",
        "client_instruction_cache",
        "client_instruction_cache_lookup",
        "client_history_exclusion_preflight",
        "client_history_exclusion_apply",
        "relayint_reference_repair",
        "relayint_quick_clarification",
        "relayctx_repack",
        "relayctx_unpack",
    }
    nodes = set(registered_pipeline_node_projectors())
    require(nodes == expected_nodes, nodes)
    for node in nodes:
        lowered = node.lower()
        require(
            "probe" not in lowered and "test" not in lowered and "fixture" not in lowered,
            node,
        )
    print("ok production registries are exact and contain no test probes")


def assert_pure_reentrant_projection() -> None:
    inputs = [
        {"event": "backend_response", "status_code": 200},
        {"event": "backend_error", "error_type": "RuntimeError"},
        {"unknown": {"status": "ready"}},
    ]
    expected = [project_audit_metadata(value).metadata for value in inputs]

    def run(index: int) -> tuple[int, dict[str, object]]:
        return index, project_audit_metadata(inputs[index]).metadata

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(run, [0, 1, 2] * 100))
    for index, metadata in results:
        require(metadata == expected[index], (index, metadata, expected[index]))
    print("ok audit projectors are pure and reentrant")


def main() -> int:
    assert_top_level_golden()
    assert_node_isolation()
    assert_numeric_contract()
    assert_projection_counter_round_trip()
    assert_registry_hygiene()
    assert_pure_reentrant_projection()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
