from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.client_instruction_extraction import build_client_instruction_extraction_dry_run
from relaylm.client_instruction_fingerprint import (
    assert_client_instruction_fingerprint_content_free,
    build_client_instruction_fingerprint_dry_run,
    build_client_instruction_fingerprint_node_result,
)


RAW_VALUES = (
    "system fingerprint secret",
    "developer fingerprint secret",
    "user fingerprint secret",
    "assistant fingerprint secret",
    "tool fingerprint secret",
    "https://example.invalid/fingerprint-image.png",
    "call-fingerprint-secret",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _base_payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {"model": "relaylm-default", "messages": messages, "stream": False}


def _extract(payload: dict[str, Any], *, managed_route: bool = True) -> dict[str, Any]:
    artifact = build_client_instruction_extraction_dry_run(
        payload,
        enabled=True,
        managed_route=managed_route,
    )
    require(isinstance(artifact, dict), artifact)
    return artifact


def _assert_no_raw_content(value: Any) -> None:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    for raw in RAW_VALUES:
        require(raw not in encoded, f"content leaked into fingerprint artifact: {raw!r}")
    assert_client_instruction_fingerprint_content_free(value)


def _assert_default_off() -> None:
    extraction = _extract(
        _base_payload(
            [
                {"role": "system", "content": "system fingerprint secret"},
                {"role": "user", "content": "user fingerprint secret"},
            ]
        )
    )
    artifact = build_client_instruction_fingerprint_dry_run(extraction, enabled=False)
    require(artifact is None, artifact)
    print("ok default-off returns None")


def _assert_ready_plan() -> None:
    extraction = _extract(
        _base_payload(
            [
                {"role": "system", "content": "system fingerprint secret"},
                {
                    "role": "developer",
                    "content": [{"type": "text", "text": "developer fingerprint secret"}],
                },
                {"role": "user", "content": "user fingerprint secret"},
            ]
        )
    )
    artifact = build_client_instruction_fingerprint_dry_run(extraction, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("schema_version") == "client_instruction_fingerprint_dry_run.v0", artifact)
    require(artifact.get("content_free") is True, artifact)
    require(artifact.get("diagnostics_only") is True, artifact)
    require(artifact.get("source_schema_supported") is True, artifact)
    require(artifact.get("managed_route") is True, artifact)
    require(artifact.get("extraction_candidate_ready") is True, artifact)
    require(artifact.get("fingerprint_plan_ready") is True, artifact)
    require(artifact.get("fingerprint_plan_mode") == "metadata_contract_only", artifact)
    require(artifact.get("fingerprint_hash_computed") is False, artifact)
    require(artifact.get("cache_key_computed") is False, artifact)
    require(artifact.get("cache_lookup_attempted") is False, artifact)
    require(artifact.get("cache_save_attempted") is False, artifact)
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
    require(artifact.get("blocked_reasons") == [], artifact)
    _assert_no_raw_content(artifact)

    result = build_client_instruction_fingerprint_node_result(artifact)
    require(result is not None, result)
    _assert_no_raw_content(result)
    logged = result.to_log_dict()
    require(logged.get("node_name") == "client_instruction_fingerprint", logged)
    require(logged.get("status") == "diagnostic_only", logged)
    require(logged.get("decision") == "instruction_fingerprint_plan_ready", logged)
    require(logged.get("blocked_reasons") == [], logged)
    require(logged.get("diagnostics", {}).get("fingerprint_plan_ready") is True, logged)
    _assert_no_raw_content(logged)
    print("ok ready plan is content-free metadata-only")


def _assert_pass_through_skipped() -> None:
    extraction = _extract(
        _base_payload(
            [
                {"role": "system", "content": "system fingerprint secret"},
                {"role": "user", "content": "user fingerprint secret"},
            ]
        ),
        managed_route=False,
    )
    artifact = build_client_instruction_fingerprint_dry_run(extraction, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("managed_route") is False, artifact)
    require(artifact.get("fingerprint_plan_ready") is False, artifact)
    require("pass_through_route_exempt" in artifact.get("blocked_reasons", []), artifact)
    require("source_extraction_not_ready" in artifact.get("blocked_reasons", []), artifact)
    require("source_extraction_blocked" in artifact.get("blocked_reasons", []), artifact)
    result = build_client_instruction_fingerprint_node_result(artifact)
    require(result is not None, result)
    logged = result.to_log_dict()
    require(logged.get("status") == "skipped", logged)
    require(logged.get("decision") == "pass_through_route_exempt", logged)
    _assert_no_raw_content(logged)
    print("ok pass-through source is skipped")


def _assert_missing_or_unsupported_source_blocks() -> None:
    missing = build_client_instruction_fingerprint_dry_run(None, enabled=True)
    require(isinstance(missing, dict), missing)
    require(missing.get("fingerprint_plan_ready") is False, missing)
    require("source_extraction_artifact_missing" in missing.get("blocked_reasons", []), missing)
    _assert_no_raw_content(missing)

    unsupported = build_client_instruction_fingerprint_dry_run(
        {
            "schema_version": "future.v99",
            "content_free": True,
            "managed_route": True,
            "fingerprint_candidate_ready": True,
        },
        enabled=True,
    )
    require(isinstance(unsupported, dict), unsupported)
    require(unsupported.get("fingerprint_plan_ready") is False, unsupported)
    require("source_extraction_schema_unsupported" in unsupported.get("blocked_reasons", []), unsupported)
    _assert_no_raw_content(unsupported)
    print("ok missing/unsupported source blocks")


def _assert_source_blocks_propagate() -> None:
    extraction = _extract(
        _base_payload(
            [
                {
                    "role": "developer",
                    "content": [
                        {"type": "text", "text": "developer fingerprint secret"},
                        {
                            "type": "image_url",
                            "image_url": {"url": "https://example.invalid/fingerprint-image.png"},
                        },
                    ],
                },
                {"role": "user", "content": "user fingerprint secret"},
            ]
        )
    )
    artifact = build_client_instruction_fingerprint_dry_run(extraction, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("fingerprint_plan_ready") is False, artifact)
    require("source_extraction_not_ready" in artifact.get("blocked_reasons", []), artifact)
    require("source_extraction_blocked" in artifact.get("blocked_reasons", []), artifact)
    require(
        "source_multimodal_instruction_candidate_requires_preservation"
        in artifact.get("blocked_reasons", []),
        artifact,
    )
    require(artifact.get("has_multimodal_instruction_candidate") is True, artifact)
    require(artifact.get("source_blocked_reasons") == extraction.get("blocked_reasons"), artifact)
    _assert_no_raw_content(artifact)
    print("ok source blocks propagate without raw content")


def _assert_active_tool_transaction_blocks() -> None:
    extraction = _extract(
        _base_payload(
            [
                {"role": "system", "content": "system fingerprint secret"},
                {"role": "user", "content": "user fingerprint secret"},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [{"id": "call-fingerprint-secret", "type": "function"}],
                },
                {"role": "tool", "tool_call_id": "call-fingerprint-secret", "content": "tool fingerprint secret"},
            ]
        )
    )
    artifact = build_client_instruction_fingerprint_dry_run(extraction, enabled=True)
    require(isinstance(artifact, dict), artifact)
    require(artifact.get("fingerprint_plan_ready") is False, artifact)
    require("active_tool_transaction_requires_preservation" in artifact.get("blocked_reasons", []), artifact)
    require(artifact.get("active_tool_transaction_candidate") is True, artifact)
    _assert_no_raw_content(artifact)
    print("ok active tool transaction remains preservation-blocked")


def _assert_rejects_content_bearing_keys() -> None:
    try:
        assert_client_instruction_fingerprint_content_free({"content": "system fingerprint secret"})
    except ValueError:
        print("ok content-bearing key is rejected")
        return
    raise AssertionError("expected content-bearing key rejection")


def main() -> None:
    _assert_default_off()
    _assert_ready_plan()
    _assert_pass_through_skipped()
    _assert_missing_or_unsupported_source_blocks()
    _assert_source_blocks_propagate()
    _assert_active_tool_transaction_blocks()
    _assert_rejects_content_bearing_keys()
    print("client_instruction_fingerprint_dry_run_smoke passed")


if __name__ == "__main__":
    main()
