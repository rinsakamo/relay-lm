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


SECRET_VALUES = (
    "trace_secret_sentinel_7f5f4b22",
    "system developer user assistant secret sentence",
    "private snippet body",
    "/home/private/relaymem/page.md",
    "tool argument secret",
    "evidence body secret",
)


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _assert_content_free(raw: str) -> None:
    for secret in SECRET_VALUES:
        require(secret not in raw, raw)


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
            messages=[
                {"role": "system", "content": SECRET_VALUES[1]},
                {"role": "user", "content": SECRET_VALUES[0]},
            ],
            response_text=SECRET_VALUES[1],
            metadata={
                "event": "backend_response",
                "status_code": 200,
                "error_type": "BackendRequestError",
                "pipeline_node_results": [
                    {
                        "node_name": "relayctx_unpack",
                        "status": "diagnostic_only",
                        "decision": "current_request_evidence_identified",
                        "diagnostics": {
                            "candidate_present": True,
                            "candidate_count": 1,
                            "safe_counter_count": 2,
                            SECRET_VALUES[0]: 3,
                            f"{SECRET_VALUES[0]}_status": 4,
                            "http://internal.example/path": 5,
                            "source": "http://internal.example/path",
                            "candidate_text": SECRET_VALUES[0],
                            "snippet_text": SECRET_VALUES[2],
                            "root_path": SECRET_VALUES[3],
                            "tool_arguments": SECRET_VALUES[4],
                            "evidence": SECRET_VALUES[5],
                        },
                    }
                ],
                "relayrun_artifact": {
                    "schema_version": "relayrun.runtime_checkpoint.v0",
                    "content_free": True,
                    "run_id": "run-content-free-001",
                    # These keys would normally be permitted, but their values
                    # are tainted by raw user content and must still be dropped.
                    "run_status": SECRET_VALUES[0],
                    "run_state": f"prefix_{SECRET_VALUES[0]}_suffix",
                    "target_path_preview": SECRET_VALUES[3],
                    "response_text": SECRET_VALUES[1],
                },
                "relaymem_retrieval_artifact": {
                    "query_summary": {
                        "terms": ["evidence"],
                    },
                    "snippet_text": SECRET_VALUES[2],
                    "evidence_envelope": SECRET_VALUES[5],
                },
                "evidence_envelope": {"content": SECRET_VALUES[5]},
                "tool_arguments": SECRET_VALUES[4],
                "unknown_metadata": SECRET_VALUES[0],
            },
        )
        append_trace_record(trace_path, record)

        raw = trace_path.read_text(encoding="utf-8")
        _assert_content_free(raw)
        payload = json.loads(raw)
        require(payload["schema_version"] == AUDIT_TRACE_SCHEMA_VERSION, payload)
        require(payload["content_free"] is True, payload)
        require(payload["message_count"] == 2, payload)
        require(payload["response_present"] is True, payload)
        require("messages" not in payload, payload)
        require("response_text" not in payload, payload)
        require(payload["metadata"]["event"] == "backend_response", payload)
        require(payload["metadata"]["status_code"] == 200, payload)
        require(payload["metadata"]["error_type"] == "BackendRequestError", payload)
        require("relaymem_retrieval_artifact" not in payload["metadata"], payload)
        require("evidence_envelope" not in payload["metadata"], payload)
        require("tool_arguments" not in payload["metadata"], payload)
        require(
            payload["metadata"].get("sanitizer_dropped_field_count", 0) > 0,
            payload,
        )
        node = payload["metadata"]["pipeline_node_results"][0]
        diagnostics = node["diagnostics"]
        require(node["node_name"] == "relayctx_unpack", node)
        require(node["decision"] == "current_request_evidence_identified", node)
        require(diagnostics["candidate_present"] is True, node)
        require(diagnostics["candidate_count"] == 1, node)
        require(diagnostics["safe_counter_count"] == 2, node)
        require(SECRET_VALUES[0] not in diagnostics, node)
        require(f"{SECRET_VALUES[0]}_status" not in diagnostics, node)
        require("http://internal.example/path" not in diagnostics, node)
        require("source" not in diagnostics, node)
        require("candidate_text" not in diagnostics, node)
        require(
            "run_status" not in payload["metadata"]["relayrun_artifact"],
            payload,
        )
        require(
            "run_state" not in payload["metadata"]["relayrun_artifact"],
            payload,
        )
        print("ok audit trace persists only content-free allowlisted fields")
        print("ok tainted values are dropped even under structurally safe keys")
        print("ok tainted and URL-shaped nested audit map keys are dropped")
        print("ok URL-shaped nested audit strings are dropped")
        print("ok backend error types remain actionable and content-free")
        print("ok pass-through trace excludes messages response snippets paths tools and evidence")

        records = read_trace_records(trace_path)
        require(len(records) == 1, records)
        require(records[0].messages == [], records[0])
        require(records[0].response_text is None, records[0])
        require(records[0].message_count == 2, records[0])
        require(records[0].response_present is True, records[0])
        print("ok audit trace reader exposes redacted compatibility views")

        empty_response_path = Path(tmpdir) / "empty-response.jsonl"
        empty_response = build_trace_record(
            trace_id="trace-empty-response-001",
            request_id="request-empty-response-001",
            created_at="2026-06-14T00:00:01+00:00",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="memory_light",
            compiler_used=False,
            messages=[],
            response_text="",
            metadata={"event": "backend_response", "status_code": 200},
        )
        require(empty_response.response_present is True, empty_response)
        append_trace_record(empty_response_path, empty_response)
        empty_payload = json.loads(empty_response_path.read_text(encoding="utf-8"))
        require(empty_payload["response_present"] is True, empty_payload)
        require(read_trace_records(empty_response_path)[0].response_present is True, empty_payload)
        print("ok empty string response is preserved as present without content")

        legacy_path = Path(tmpdir) / "legacy.jsonl"
        legacy_path.write_text(
            json.dumps(
                {
                    "trace_id": "legacy-trace-001",
                    "created_at": "2026-05-21T00:00:00+00:00",
                    "character_id": "default",
                    "route_model": "relaylm-default",
                    "mode_applied": "memory_light",
                    "compiler_used": True,
                    "messages": [{"role": "user", "content": SECRET_VALUES[0]}],
                    "response_text": SECRET_VALUES[1],
                    "metadata": {
                        "event": "backend_response",
                        "status": SECRET_VALUES[0],
                        "snippet_text": SECRET_VALUES[2],
                    },
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        legacy = read_trace_records(legacy_path)[0]
        require(legacy.message_count == 1, legacy)
        require(legacy.response_present is True, legacy)
        require(legacy.messages == [], legacy)
        require(legacy.response_text is None, legacy)
        require("status" not in legacy.metadata, legacy.metadata)
        require("snippet_text" not in legacy.metadata, legacy.metadata)
        print("ok legacy content-bearing rows are read as redacted audit records")

        legacy_empty_path = Path(tmpdir) / "legacy-empty-response.jsonl"
        legacy_empty_path.write_text(
            json.dumps(
                {
                    "trace_id": "legacy-empty-response-001",
                    "created_at": "2026-05-21T00:00:01+00:00",
                    "response_text": "",
                    "metadata": {"event": "backend_response"},
                }
            )
            + "\n",
            encoding="utf-8",
        )
        legacy_empty = read_trace_records(legacy_empty_path)[0]
        require(legacy_empty.response_present is True, legacy_empty)
        require(legacy_empty.response_text is None, legacy_empty)
        print("ok legacy empty string response is preserved as present")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
