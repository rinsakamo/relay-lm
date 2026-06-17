from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.trace import (
    AUDIT_TRACE_SCHEMA_VERSION,
    append_trace_record,
    build_trace_record,
    read_trace_records,
)

SENTINELS = (
    "trace-private-user-value-7f5f4b22",
    "trace-private-response-value-5b06d2e1",
    "trace-private-artifact-value-45e9c81a",
    "/home/private/relaymem/page.md",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def assert_absent(raw: str) -> None:
    for value in SENTINELS:
        require(value not in raw, raw)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "audit.jsonl"
        record = build_trace_record(
            trace_id="trace-content-free-001",
            request_id="request-content-free-001",
            created_at="2026-06-14T00:00:00+00:00",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="pass_through",
            compiler_used=False,
            message_count=2,
            response_present=True,
            metadata={
                "event": "backend_response",
                "status_code": 200,
                "pipeline_node_results": [
                    {
                        "node_name": "relayint_reference_repair",
                        "status": "diagnostic_only",
                        "decision": "none",
                        "blocked_reasons": [],
                        "diagnostics": {
                            "diagnostics_only": True,
                            "content_free": True,
                            "source_node_alias": "relayint_reference_repair",
                            "compatibility_source_node": "relayref",
                            "artifact_present": True,
                            "unresolved_reference_detected": False,
                            "apply_allowed": False,
                            "private_value": SENTINELS[2],
                        },
                    },
                    {
                        "node_name": "future_unregistered_node",
                        "status": "diagnostic_only",
                        "diagnostics": {"private_value": SENTINELS[2]},
                    },
                ],
                "memory_selection_summary": {
                    "total_candidates": 2,
                    "eligible_count": 1,
                    "selected_count": 1,
                    "limit": 1,
                    "character_id": "default",
                    "selected_memory_ids": ["memory-001"],
                    "excluded_disabled_ids": ["memory-002"],
                    "excluded_character_ids": [],
                    "state_counts": {
                        "active": 1,
                        "promoted": 0,
                        "demoted": 0,
                        "disabled": 1,
                    },
                    "private_value": SENTINELS[2],
                },
                "relayrun_artifact": {
                    "schema_version": "relayrun.runtime_checkpoint.v0",
                    "content_free": True,
                    "run_id": "run-001",
                    "run_status": "diagnostics_only",
                    "target_path_preview": SENTINELS[3],
                },
                "unsupported_private_artifact": {
                    "value": SENTINELS[2],
                },
            },
        )
        append_trace_record(trace_path, record)

        raw = trace_path.read_text(encoding="utf-8")
        assert_absent(raw)
        payload = json.loads(raw)
        require(payload["schema_version"] == AUDIT_TRACE_SCHEMA_VERSION, payload)
        require(payload["content_free"] is True, payload)
        require(payload["message_count"] == 2, payload)
        require(payload["response_present"] is True, payload)
        require("messages" not in payload, payload)
        require("response_text" not in payload, payload)

        metadata = payload["metadata"]
        require(metadata["event"] == "backend_response", metadata)
        require(metadata["status_code"] == 200, metadata)
        require("unsupported_private_artifact" not in metadata, metadata)
        require(metadata.get("projection_unsupported_artifact_count") == 1, metadata)
        require(metadata.get("projection_dropped_field_count", 0) >= 4, metadata)

        results = metadata["pipeline_node_results"]
        require(len(results) == 1, results)
        require(results[0]["node_name"] == "relayint_reference_repair", results)
        require(
            results[0]["diagnostics"]["compatibility_source_node"] == "relayref",
            results,
        )
        require("private_value" not in results[0]["diagnostics"], results)
        require(
            "private_value" not in metadata["memory_selection_summary"], metadata
        )
        require(
            "target_path_preview" not in metadata["relayrun_artifact"], metadata
        )

        legacy_path = Path(tmpdir) / "legacy.jsonl"
        legacy_path.write_text(
            json.dumps(
                {
                    "trace_id": "legacy-001",
                    "created_at": "2026-06-14T00:00:01+00:00",
                    "character_id": "default",
                    "route_model": "relaylm-default",
                    "mode_applied": "pass_through",
                    "compiler_used": False,
                    "messages": [
                        {"role": "user", "content": SENTINELS[0]},
                        {"role": "assistant", "content": SENTINELS[1]},
                    ],
                    "response_text": "",
                    "metadata": {
                        "event": "backend_response",
                        "status_code": 200,
                        "unsupported_private_artifact": {"value": SENTINELS[2]},
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        legacy = read_trace_records(legacy_path)[0]
        require(legacy.message_count == 2, legacy)
        require(legacy.response_present is True, legacy)
        require(legacy.messages == [], legacy)
        require(legacy.response_text is None, legacy)
        assert_absent(json.dumps(legacy.to_json_dict(), ensure_ascii=False))

        print("ok typed audit trace persists only registered projections")
        print("ok legacy trace rows reduce to shape-only audit records")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
