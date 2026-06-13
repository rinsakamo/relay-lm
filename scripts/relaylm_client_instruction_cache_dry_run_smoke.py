from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_instruction_cache import (
    assert_client_instruction_cache_content_free,
    build_client_instruction_cache_dry_run,
    build_client_instruction_cache_node_result,
)
from relaylm.client_instruction_extraction import build_client_instruction_extraction_dry_run
from relaylm.client_instruction_fingerprint import build_client_instruction_fingerprint_dry_run


RAW_VALUES = (
    "system cache secret",
    "developer cache secret",
    "user cache secret",
    "tool cache secret",
    "https://example.invalid/cache-image.png",
    "call-cache-secret",
    "fingerprint-bytes-secret",
    "cache-key-secret",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _base_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {"model": "relaylm-default", "messages": messages, "stream": False}


def _fingerprint(payload: dict[str, Any], *, managed_route: bool = True) -> dict[str, Any]:
    extraction = build_client_instruction_extraction_dry_run(
        payload,
        enabled=True,
        managed_route=managed_route,
    )
    require(isinstance(extraction, dict), extraction)
    fingerprint = build_client_instruction_fingerprint_dry_run(extraction, enabled=True)
    require(isinstance(fingerprint, dict), fingerprint)
    return fingerprint


def _ready_fingerprint() -> dict[str, Any]:
    return _fingerprint(
        _base_payload(
            [
                {"role": "system", "content": "system cache secret"},
                {
                    "role": "developer",
                    "content": [{"type": "text", "text": "developer cache secret"}],
                },
                {"role": "user", "content": "user cache secret"},
            ]
        )
    )


def _assert_no_raw_content(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    for raw in RAW_VALUES:
        require(raw not in encoded, f"content leaked into cache artifact: {raw!r}")
    assert_client_instruction_cache_content_free(value)


def _assert_default_off() -> None:
    artifact = build_client_instruction_cache_dry_run(
        _ready_fingerprint(),
        enabled=False,
        lookup_requested=True,
        save_requested=True,
    )
    require(artifact is None, artifact)
    print("ok default-off returns None")


def _assert_requested_operations_ready() -> None:
    fingerprint = _ready_fingerprint()
    artifact = build_client_instruction_cache_dry_run(
        fingerprint,
        enabled=True,
        lookup_requested=True,
        save_requested=True,
    )
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("schema_version") == "client_instruction_cache_dry_run.v0", artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("dry_run_only") is True, artifact)
    require(artifact.get("operation_plan_mode") == "metadata_contract_only", artifact)
    require(artifact.get("cache_operation_plan_ready") is True, artifact)
    require(artifact.get("lookup_requested") is True, artifact)
    require(artifact.get("save_requested") is True, artifact)
    require(artifact.get("lookup_plan_ready") is True, artifact)
    require(artifact.get("save_plan_ready") is True, artifact)
    require(artifact.get("cache_lookup_attempted") is False, artifact)
    require(artifact.get("cache_save_attempted") is False, artifact)
    require(artifact.get("cache_key_computed") is False, artifact)
    require(artifact.get("cache_key_available") is False, artifact)
    require(artifact.get("fingerprint_hash_computed") is False, artifact)
    require(artifact.get("fingerprint_hash_available") is False, artifact)
    require(artifact.get("cache_hit_known") is False, artifact)
    require(artifact.get("cache_hit") is None, artifact)
    require(artifact.get("cache_result_available") is False, artifact)
    require(artifact.get("payload_mutation_applied") is False, artifact)
    require(artifact.get("history_exclusion_applied") is False, artifact)
    require(artifact.get("persistence_applied") is False, artifact)
    require(artifact.get("instruction_candidate_count") == 2, artifact)
    require(artifact.get("candidate_roles") == ["system", "developer"], artifact)
    require(artifact.get("candidate_indices") == [0, 1], artifact)
    require(artifact.get("content_shape_counts") == {"string": 1, "text_parts": 1}, artifact)
    require(
        artifact.get("fingerprint_scope_summary")
        == {
            "candidate_count": 2,
            "candidate_role_count": 2,
            "candidate_index_count": 2,
            "content_shape_kind_count": 2,
        },
        artifact,
    )
    require(artifact.get("source_blocked_reasons") == [], artifact)
    require(artifact.get("blocked_reasons") == [], artifact)
    _assert_no_raw_content(artifact)

    result = build_client_instruction_cache_node_result(artifact)
    require(result is not None, result)
    _assert_no_raw_content(result)
    logged = result.to_log_dict()
    require(logged.get("node_name") == "client_instruction_cache", logged)
    require(logged.get("status") == "diagnostic_only", logged)
    require(logged.get("decision") == "instruction_cache_operation_plan_ready", logged)
    require(logged.get("blocked_reasons") == [], logged)
    require(logged.get("diagnostics", {}).get("cache_operation_plan_ready") is True, logged)
    _assert_no_raw_content(logged)
    print("ok requested lookup/save plans are ready without attempts")


def _assert_unrequested_operations_still_ready() -> None:
    artifact = build_client_instruction_cache_dry_run(_ready_fingerprint(), enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("cache_operation_plan_ready") is True, artifact)
    require(artifact.get("lookup_requested") is False, artifact)
    require(artifact.get("save_requested") is False, artifact)
    require(artifact.get("lookup_plan_ready") is False, artifact)
    require(artifact.get("save_plan_ready") is False, artifact)
    require(artifact.get("cache_lookup_attempted") is False, artifact)
    require(artifact.get("cache_save_attempted") is False, artifact)
    _assert_no_raw_content(artifact)
    print("ok operation plan ready even when lookup/save are not requested")


def _assert_missing_source_blocks() -> None:
    artifact = build_client_instruction_cache_dry_run(None, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("cache_operation_plan_ready") is False, artifact)
    require("source_fingerprint_artifact_missing" in artifact.get("blocked_reasons", []), artifact)
    _assert_no_raw_content(artifact)
    print("ok missing source blocks")


def _assert_unsupported_source_schema_blocks() -> None:
    artifact = build_client_instruction_cache_dry_run(
        {
            "schema_version": "future.v99",
            "content_free": True,
            "fingerprint_plan_ready": True,
            "instruction_candidate_count": 1,
        },
        enabled=True,
    )
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("cache_operation_plan_ready") is False, artifact)
    require("source_fingerprint_schema_unsupported" in artifact.get("blocked_reasons", []), artifact)
    _assert_no_raw_content(artifact)
    print("ok unsupported source schema blocks")


def _assert_source_fingerprint_blocked_propagates() -> None:
    fingerprint = _fingerprint(
        _base_payload(
            [
                {
                    "role": "developer",
                    "content": [
                        {"type": "text", "text": "developer cache secret"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "https://example.invalid/cache-image.png"},
                        },
                    ],
                },
                {"role": "user", "content": "user cache secret"},
            ]
        )
    )
    artifact = build_client_instruction_cache_dry_run(fingerprint, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("cache_operation_plan_ready") is False, artifact)
    require("source_fingerprint_plan_not_ready" in artifact.get("blocked_reasons", []), artifact)
    require("source_fingerprint_blocked" in artifact.get("blocked_reasons", []), artifact)
    require(artifact.get("source_blocked_reasons") == fingerprint.get("blocked_reasons"), artifact)
    _assert_no_raw_content(artifact)
    print("ok source fingerprint block propagates")


def _assert_zero_candidate_blocks() -> None:
    fingerprint = _fingerprint(_base_payload([{"role": "user", "content": "user cache secret"}]))
    require(fingerprint.get("fingerprint_plan_ready") is True, fingerprint)
    artifact = build_client_instruction_cache_dry_run(fingerprint, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("cache_operation_plan_ready") is False, artifact)
    require("source_instruction_candidates_missing" in artifact.get("blocked_reasons", []), artifact)
    _assert_no_raw_content(artifact)
    print("ok zero instruction candidates block")


def _assert_unexpected_source_states_block() -> None:
    fingerprint = dict(_ready_fingerprint())
    fingerprint["cache_key_computed"] = True
    fingerprint["fingerprint_hash_available"] = True
    artifact = build_client_instruction_cache_dry_run(fingerprint, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require("unexpected_source_cache_key_state" in artifact.get("blocked_reasons", []), artifact)
    require("unexpected_source_fingerprint_hash_state" in artifact.get("blocked_reasons", []), artifact)
    _assert_no_raw_content(artifact)
    print("ok unexpected source cache/hash states block")


def _assert_rejects_content_bearing_keys() -> None:
    for value in (
        {"content": "system cache secret"},
        {"cache_key": "cache-key-secret"},
        {"fingerprint_hash": "fingerprint-bytes-secret"},
    ):
        try:
            assert_client_instruction_cache_content_free(value)
        except ValueError:
            continue
        raise AssertionError(f"expected content-bearing key rejection: {value!r}")
    print("ok content-bearing keys are rejected")


def main() -> None:
    _assert_default_off()
    _assert_requested_operations_ready()
    _assert_unrequested_operations_still_ready()
    _assert_missing_source_blocks()
    _assert_unsupported_source_schema_blocks()
    _assert_source_fingerprint_blocked_propagates()
    _assert_zero_candidate_blocks()
    _assert_unexpected_source_states_block()
    _assert_rejects_content_bearing_keys()
    print("client_instruction_cache_dry_run_smoke passed")


if __name__ == "__main__":
    main()
