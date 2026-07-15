from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.audit_projection import project_audit_metadata

UUID = "a1234567-89ab-4def-8123-abcdefabcdef"

# Values every URL/path-rejecting validator (`_bounded_token`, `_lower_token`,
# `_opaque_id`) must reject through `_looks_like_url_or_path()`, probed only
# through public projected fields, never the private validator functions.
URL_OR_PATH_REJECTED_VALUES = (
    "https://example.invalid/a",
    "//example.invalid/a",
    "www.example.invalid",
    "/absolute",
    "./relative",
    "../relative",
    "~/home",
    "C:\\windows",
    "a/b",
    "a\\b",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def compile_artifact(state: str) -> dict[str, object]:
    return {
        "schema_version": "relaylm.compile_decision_dry_run.v0",
        "decision_id": f"{UUID}:compile-decision-dry-run",
        "plan_id": f"{UUID}:compile-plan",
        "result_id": f"{UUID}:compile-result",
        "decision_state": state,
        "selected_route": "relaylm-default",
        "selected_mode": "memory_light",
        "backend": "local_backend",
        "character_id": "default",
        "compiled_message_count": 2,
        "fallback_reason": "memory_disabled",
        "blocking_reasons": [],
        "omitted_block_ids": [],
        "token_budget_status": "within_budget",
        "apply_compiled_messages": state == "COMPILE_APPLY",
        "diagnostics_only": state == "COMPILE_DRY_RUN",
        "content_free": True,
    }


def assert_finite_non_negative_numeric_boundary() -> None:
    valid_int = project_audit_metadata({"latency_ms": 5})
    require(valid_int.metadata.get("latency_ms") == 5, valid_int)
    require(valid_int.dropped_field_count == 0, valid_int)

    valid_float = project_audit_metadata({"latency_ms": 1.25})
    require(valid_float.metadata.get("latency_ms") == 1.25, valid_float)
    require(valid_float.dropped_field_count == 0, valid_float)

    rejected = [-1, -0.5, True, False, float("nan"), float("inf"), float("-inf")]
    for value in rejected:
        result = project_audit_metadata({"latency_ms": value})
        require("latency_ms" not in result.metadata, (value, result))
        require(result.dropped_field_count == 1, (value, result))
    print("ok latency_ms (_non_negative_number) accepts finite non-negative int/float and rejects negative/bool/NaN/+inf/-inf")


def assert_opaque_identifier_boundary() -> None:
    def probe(value: object) -> object:
        return project_audit_metadata({"memory_selection_summary": {"character_id": value}})

    valid = probe("default-character_1")
    require(
        valid.metadata["memory_selection_summary"].get("character_id") == "default-character_1",
        valid,
    )
    require(valid.dropped_field_count == 0, valid)

    rejected = ["", "x" * 257, *URL_OR_PATH_REJECTED_VALUES]
    for value in rejected:
        result = probe(value)
        require(
            "character_id" not in result.metadata.get("memory_selection_summary", {}),
            (value, result),
        )
        require(result.dropped_field_count == 1, (value, result))
    print(
        "ok memory_selection_summary.character_id (_opaque_id) accepts a valid bounded identifier "
        "and rejects empty/over-length/slash/backslash/URL/path-shaped values"
    )


def assert_sha256_boundary() -> None:
    valid_hash = "a" * 64
    result = project_audit_metadata({"stable_prefix_hash": valid_hash})
    require(result.metadata.get("stable_prefix_hash") == valid_hash, result)
    require(result.dropped_field_count == 0, result)

    malformed = [
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "sha256:" + "a" * 57,
        "https://example.invalid/" + "a" * 39,
        ("a" * 63) + "/",
    ]
    for value in malformed:
        result = project_audit_metadata({"stable_prefix_hash": value})
        require("stable_prefix_hash" not in result.metadata, (value, result))
        require(result.dropped_field_count == 1, (value, result))
    print(
        "ok stable_prefix_hash (_sha256) accepts exactly 64 hex characters and rejects "
        "short/long/non-hex/prefixed/URL-path-shaped values"
    )


def assert_content_type_boundary() -> None:
    valid_cases = [
        "application/json",
        "text/plain;charset=utf-8",
        "text/plain; charset=utf-8",
    ]
    for value in valid_cases:
        result = project_audit_metadata({"content_type": value})
        require(result.metadata.get("content_type") == value, (value, result))
        require(result.dropped_field_count == 0, (value, result))

    invalid_cases: list[object] = [
        "not-a-content-type",
        "application/json; boundary=1234",
        "text/plain; charset=utf 8",
        "https://example.invalid/type",
        ("a" * 65) + "/json",
        "text/" + ("b" * 65),
        123,
    ]
    for value in invalid_cases:
        result = project_audit_metadata({"content_type": value})
        require("content_type" not in result.metadata, (value, result))
        require(result.dropped_field_count == 1, (value, result))
    print(
        "ok content_type (_content_type) accepts exact media-type grammar including the supported "
        "optional charset form and rejects malformed/unsupported-parameter/whitespace-invalid/"
        "URL-path-shaped/overlong/non-string values"
    )


def assert_bounded_and_lower_token_path_rejection() -> None:
    valid_token = "memory_candidate_selection"
    result = project_audit_metadata({"memory_source": valid_token})
    require(result.metadata.get("memory_source") == valid_token, result)
    require(result.dropped_field_count == 0, result)

    for value in URL_OR_PATH_REJECTED_VALUES:
        result = project_audit_metadata({"memory_source": value})
        require("memory_source" not in result.metadata, (value, result))
        require(result.dropped_field_count == 1, (value, result))
    print("ok memory_source (_bounded_token) accepts a plain token and rejects every URL/path-shaped category")

    valid_lower = "memory_disabled"
    lower_result = project_audit_metadata(
        {"compile_decision_dry_run": {"fallback_reason": valid_lower}}
    )
    require(
        lower_result.metadata["compile_decision_dry_run"].get("fallback_reason") == valid_lower,
        lower_result,
    )
    require(lower_result.dropped_field_count == 0, lower_result)

    for value in URL_OR_PATH_REJECTED_VALUES:
        result = project_audit_metadata(
            {"compile_decision_dry_run": {"fallback_reason": value}}
        )
        require(
            "fallback_reason" not in result.metadata.get("compile_decision_dry_run", {}),
            (value, result),
        )
        require(result.dropped_field_count == 1, (value, result))
    print(
        "ok compile_decision_dry_run.fallback_reason (_lower_token) accepts a plain lower-case "
        "token and rejects every URL/path-shaped category"
    )


def assert_exact_nested_projection_drops_unknown_fields() -> None:
    result = project_audit_metadata(
        {
            "memory_selection_summary": {
                "total_candidates": 4,
                "eligible_count": 3,
                "unknown_nested_field": "must-not-project",
                "another_unknown_field": {"nested": "also-must-not-project"},
            }
        }
    )
    summary = result.metadata["memory_selection_summary"]
    require(summary.get("total_candidates") == 4, summary)
    require(summary.get("eligible_count") == 3, summary)
    require("unknown_nested_field" not in summary, summary)
    require("another_unknown_field" not in summary, summary)
    require(result.dropped_field_count == 2, result)
    print("ok unknown nested fields are dropped with an exact counter while known valid siblings are retained")


def main() -> int:
    for state in ("COMPILE_DRY_RUN", "COMPILE_APPLY"):
        projected = project_audit_metadata(
            {"compile_decision_dry_run": compile_artifact(state)}
        ).metadata["compile_decision_dry_run"]
        require(projected["decision_state"] == state, projected)
        require(projected["decision_id"] == f"{UUID}:compile-decision-dry-run", projected)
        require(projected["plan_id"] == f"{UUID}:compile-plan", projected)
        require(projected["result_id"] == f"{UUID}:compile-result", projected)
        require(projected["fallback_reason"] == "memory_disabled", projected)
    print("ok compile states, scoped UUID identifiers, and fallback reason")

    invalid_compile = compile_artifact("COMPILE_APPLY")
    invalid_compile["decision_id"] = "https://example.invalid/private"
    invalid_compile["plan_id"] = f"{UUID}:compile-result"
    invalid_compile["fallback_reason"] = "https://example.invalid/private"
    invalid = project_audit_metadata(
        {"compile_decision_dry_run": invalid_compile}
    ).metadata["compile_decision_dry_run"]
    require("decision_id" not in invalid, invalid)
    require("plan_id" not in invalid, invalid)
    require("fallback_reason" not in invalid, invalid)
    require(invalid["result_id"] == f"{UUID}:compile-result", invalid)
    print("ok compile identifiers and fallback reason reject URLs and wrong scopes")

    nodes = project_audit_metadata(
        {
            "pipeline_node_results": [
                {
                    "node_name": "relayint_reference_repair",
                    "status": "diagnostic_only",
                    "decision": "context_repair",
                    "diagnostics": {
                        "diagnostics_only": True,
                        "content_free": True,
                        "source_node_alias": "relayint_reference_repair",
                        "compatibility_source_node": "relayref",
                        "artifact_present": True,
                        "unresolved_reference_detected": True,
                        "apply_allowed": False,
                    },
                },
                {
                    "node_name": "relayint_reference_repair",
                    "status": "diagnostic_only",
                    "decision": "future_unregistered_mode",
                    "diagnostics": {
                        "diagnostics_only": True,
                        "content_free": True,
                        "source_node_alias": "relayint_reference_repair",
                        "compatibility_source_node": "relayref",
                        "artifact_present": True,
                        "unresolved_reference_detected": False,
                        "apply_allowed": False,
                    },
                },
            ]
        }
    ).metadata["pipeline_node_results"]
    require(nodes[0]["decision"] == "context_repair", nodes)
    require("decision" not in nodes[1], nodes)
    print("ok reference repair decisions use an exact enum")

    artifacts = project_audit_metadata(
        {
            "pipeline_node_results": [
                {
                    "node_name": "client_message_canonicalization",
                    "status": "diagnostic_only",
                    "decision": "current_request_evidence_identified",
                    "artifacts": [
                        {
                            "artifact_name": "client_message_canonicalization_dry_run",
                            "schema_version": "client_message_canonicalization_dry_run.v0",
                            "present": True,
                            "diagnostics_only": True,
                            "content_free": True,
                            "applied": False,
                            "runtime_private_source": True,
                            "read_only": True,
                        }
                    ],
                },
                {
                    "node_name": "client_instruction_identity",
                    "status": "diagnostic_only",
                    "decision": "instruction_identity_ready",
                    "artifacts": [
                        {
                            "artifact_name": "client_instruction_identity_runtime_summary",
                            "schema_version": "client_instruction_identity.v0",
                            "present": True,
                            "diagnostics_only": True,
                            "content_free": True,
                            "runtime_private_source": True,
                            "read_only": True,
                            "applied": False,
                        }
                    ],
                },
                {
                    "node_name": "relayctx_unpack",
                    "status": "diagnostic_only",
                    "decision": "plain_text_no_change",
                    "artifacts": [
                        {
                            "artifact_name": "relayctx_unpack_runtime_result",
                            "schema_version": "relayctx_unpack_runtime.v0",
                            "present": True,
                            "content_free": True,
                            "applied_to_response": False,
                            "candidate_present": False,
                            "persistence_allowed": False,
                            "diagnostics_only": True,
                        }
                    ],
                },
            ]
        }
    ).metadata["pipeline_node_results"]

    canonical = artifacts[0]["artifacts"][0]
    require("runtime_private_source" not in canonical, canonical)
    require("read_only" not in canonical, canonical)
    identity = artifacts[1]["artifacts"][0]
    require(identity["runtime_private_source"] is True, identity)
    require("read_only" not in identity, identity)
    unpack = artifacts[2]["artifacts"][0]
    require(unpack["candidate_present"] is False, unpack)
    require("diagnostics_only" not in unpack, unpack)
    print("ok artifact summaries enforce artifact-specific fields")

    apply_nodes = project_audit_metadata(
        {
            "pipeline_node_results": [
                {
                    "node_name": "client_history_exclusion_apply",
                    "status": "diagnostic_only",
                    "decision": "client_history_exclusion_apply_ready",
                    "diagnostics": {
                        "schema_version": "client_history_exclusion_apply.v0",
                        "enabled": True,
                        "status": "ready",
                        "dry_run_only": True,
                        "managed_route": True,
                        "compiler_used": True,
                        "relay_owned_prefix_message_count": 1,
                        "original_compiled_message_count": 4,
                        "forwarded_message_count": 2,
                        "excluded_client_message_count": 2,
                        "preserved_client_message_count": 1,
                        "instruction_resolution_mode": "none",
                        "payload_candidate_present": True,
                        "payload_mutation_applied": False,
                        "runtime_private_source": True,
                        "content_bearing_candidate_persisted": False,
                        "forwarded_payload": "private payload sentinel",
                    },
                    "artifacts": [
                        {
                            "artifact_name": "client_history_exclusion_apply_summary",
                            "schema_version": "client_history_exclusion_apply.v0",
                            "present": True,
                            "diagnostics_only": True,
                            "content_free": True,
                            "runtime_private_source": True,
                            "payload_candidate_present": True,
                            "payload_mutation_applied": False,
                            "content_bearing_candidate_persisted": False,
                            "forwarded_payload": "private payload sentinel",
                        }
                    ],
                },
                {
                    "node_name": "client_history_exclusion_apply",
                    "status": "diagnostic_only",
                    "decision": "future_apply_mode",
                    "diagnostics": {
                        "schema_version": "client_history_exclusion_apply.v0",
                        "enabled": True,
                        "status": "ready",
                        "dry_run_only": True,
                        "managed_route": True,
                        "compiler_used": True,
                        "relay_owned_prefix_message_count": 1,
                        "original_compiled_message_count": 2,
                        "forwarded_message_count": 2,
                        "excluded_client_message_count": 0,
                        "preserved_client_message_count": 1,
                        "instruction_resolution_mode": "none",
                        "payload_candidate_present": True,
                        "payload_mutation_applied": False,
                        "runtime_private_source": True,
                        "content_bearing_candidate_persisted": False,
                    },
                },
            ]
        }
    ).metadata["pipeline_node_results"]
    apply_node = apply_nodes[0]
    require(apply_node["decision"] == "client_history_exclusion_apply_ready", apply_node)
    require(apply_node["diagnostics"]["payload_candidate_present"] is True, apply_node)
    require("forwarded_payload" not in apply_node["diagnostics"], apply_node)
    apply_artifact = apply_node["artifacts"][0]
    require(apply_artifact["artifact_name"] == "client_history_exclusion_apply_summary", apply_artifact)
    require("forwarded_payload" not in apply_artifact, apply_artifact)
    require("decision" not in apply_nodes[1], apply_nodes[1])
    print("ok history apply node and artifact use exact content-free projections")

    assert_finite_non_negative_numeric_boundary()
    assert_opaque_identifier_boundary()
    assert_sha256_boundary()
    assert_content_type_boundary()
    assert_bounded_and_lower_token_path_rejection()
    assert_exact_nested_projection_drops_unknown_fields()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
