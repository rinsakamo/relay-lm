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
    "metadata_key_secret_9f31c4a2",
)
NESTED_REJECTED_SECRET = "nested_rejected_secret_45e9c81a"
UNKNOWN_TOP_LEVEL_SECRET = "unknown_top_level_secret_5b06d2e1"


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def _assert_content_free(raw: str) -> None:
    for secret in SECRET_VALUES:
        require(secret not in raw, raw)
    require(NESTED_REJECTED_SECRET not in raw, raw)
    require(UNKNOWN_TOP_LEVEL_SECRET not in raw, raw)


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
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "text",
                            "text": SECRET_VALUES[0],
                        }
                    ],
                },
                {"role": "user", "content": SECRET_VALUES[1]},
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_001",
                            "type": "function",
                            "function": {
                                "name": "lookup_memory",
                                "arguments": SECRET_VALUES[4],
                            },
                        }
                    ],
                },
            ],
            response_text=SECRET_VALUES[1],
            metadata={
                "event": "backend_response",
                "content_type": "text/event-stream",
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
                            "compatibility_source_node": "relayref",
                            "source": "relayref",
                            "schema_version": "relayctx.unpack.v0",
                            "inserted_message_role": "system",
                            "current_user_content_kind": "text",
                            "tool_call_reference_id": "call_001",
                            "tool_function_name": "lookup_memory",
                            "unapproved_number": 42,
                            "private_numeric_marker": 123456789,
                            "user_prompt_status": "ready",
                            "backend_response_text_status": "ready",
                            "custom_page_path_id": "notes/private.md",
                            "custom_root_path_id": "private/root",
                            "internal_tool_result_count": 1,
                            "retrieval_evidence_status": "ready",
                            "tainted_source": SECRET_VALUES[0],
                            "status": SECRET_VALUES[0],
                            "decision": SECRET_VALUES[0],
                            "node_name": SECRET_VALUES[0],
                            "reason": SECRET_VALUES[0],
                            "schema_version_secret": SECRET_VALUES[0],
                            SECRET_VALUES[6]: 6,
                            SECRET_VALUES[0]: 3,
                            f"{SECRET_VALUES[0]}_status": 4,
                            "http://internal.example/path": 5,
                            "source_url": "http://internal.example/path",
                            "candidate_text": SECRET_VALUES[0],
                            "snippet_text": SECRET_VALUES[2],
                            "root_path": SECRET_VALUES[3],
                            "tool_arguments": SECRET_VALUES[4],
                            "evidence": {
                                SECRET_VALUES[6]: 1,
                                "diagnostics": 1,
                                "decision": 1,
                                "compatibility_source_node": 1,
                            },
                        },
                    },
                    {
                        "node_name": "nested_rejected_taint_probe",
                        "status": NESTED_REJECTED_SECRET,
                        "reason": NESTED_REJECTED_SECRET,
                        "diagnostics": {
                            "private_summary": {
                                "source": "relayref",
                                "evidence": {
                                    NESTED_REJECTED_SECRET: 1,
                                },
                            },
                            "safe_counter_count": 1,
                        },
                    },
                    {
                        "node_name": "unknown_top_level_taint_probe",
                        "status": UNKNOWN_TOP_LEVEL_SECRET,
                        "reason": UNKNOWN_TOP_LEVEL_SECRET,
                    }
                ],
                "memory_selection_summary": {
                    "schema_version": SECRET_VALUES[0],
                    "safe_counter_count": 1,
                    "state_counts": {
                        "active": 1,
                        "promoted": 2,
                        "demoted": 3,
                        "disabled": 4,
                        "candidate": True,
                        "fractional": 1.5,
                        "negative": -1,
                        "private": 999,
                    },
                },
                "relayrun_artifact": {
                    "schema_version": "relayrun.runtime_checkpoint.v0",
                    "content_free": True,
                    "run_id": "run-content-free-001",
                    "safe_reference_id": "opaque-id-001",
                    "source": SECRET_VALUES[0],
                    "node_name": SECRET_VALUES[0],
                    "status": SECRET_VALUES[0],
                    "decision": SECRET_VALUES[0],
                    "reason": SECRET_VALUES[0],
                    "schema_version_secret": SECRET_VALUES[0],
                    "database_id": "postgres://db/path",
                    "cache_id": "redis://host/key",
                    "blob_id": "blob:secret-payload",
                    "browser_id": "chrome://settings",
                    "page_path_id": "notes/private.md",
                    "root_path_id": "private/root",
                    "content_id": "secret-content",
                    "url_id": "opaque-looking-url",
                    "user_prompt_status": "ready",
                    "backend_response_text_status": "ready",
                    "custom_page_path_id": "notes/private.md",
                    "custom_root_path_id": "private/root",
                    "internal_tool_result_count": 1,
                    "retrieval_evidence_status": "ready",
                    "evidence": {
                        SECRET_VALUES[6]: 1,
                    },
                    # These keys would normally be permitted, but their values
                    # are tainted by raw user content and must still be dropped.
                    "run_status": SECRET_VALUES[0],
                    "run_state": f"prefix_{SECRET_VALUES[0]}_suffix",
                    "target_path_preview": SECRET_VALUES[3],
                    "response_text": SECRET_VALUES[1],
                },
                "relaymem_retrieval_artifact": {
                    "source": "relayref",
                    "node_name": "relayint_reference_repair",
                    "status": "diagnostic_only",
                    "snippet_text": SECRET_VALUES[2],
                    "evidence": {
                        SECRET_VALUES[6]: 1,
                    },
                },
                "evidence_envelope": {"content": SECRET_VALUES[5]},
                "tool_arguments": SECRET_VALUES[4],
                "unknown_metadata": {
                    "status": UNKNOWN_TOP_LEVEL_SECRET,
                    "source": UNKNOWN_TOP_LEVEL_SECRET,
                    "diagnostics": 1,
                    "decision": 1,
                    "compatibility_source_node": 1,
                },
            },
        )
        append_trace_record(trace_path, record)

        raw = trace_path.read_text(encoding="utf-8")
        _assert_content_free(raw)
        payload = json.loads(raw)
        require(payload["schema_version"] == AUDIT_TRACE_SCHEMA_VERSION, payload)
        require(payload["content_free"] is True, payload)
        require(payload["message_count"] == 3, payload)
        require(payload["response_present"] is True, payload)
        require("messages" not in payload, payload)
        require("response_text" not in payload, payload)
        require(payload["metadata"]["event"] == "backend_response", payload)
        require(payload["metadata"]["content_type"] == "text/event-stream", payload)
        require(payload["metadata"]["status_code"] == 200, payload)
        require(payload["metadata"]["error_type"] == "BackendRequestError", payload)
        require(
            payload["metadata"]["memory_selection_summary"]["safe_counter_count"] == 1,
            payload,
        )
        require(
            payload["metadata"]["memory_selection_summary"]["state_counts"]
            == {
                "active": 1,
                "promoted": 2,
                "demoted": 3,
                "disabled": 4,
            },
            payload,
        )
        require(
            "schema_version" not in payload["metadata"]["memory_selection_summary"],
            payload,
        )
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
        require(diagnostics["compatibility_source_node"] == "relayref", node)
        require(diagnostics["source"] == "relayref", node)
        require(diagnostics["schema_version"] == "relayctx.unpack.v0", node)
        require(diagnostics["inserted_message_role"] == "system", diagnostics)
        require(diagnostics["current_user_content_kind"] == "text", diagnostics)
        require(diagnostics["tool_call_reference_id"] == "call_001", diagnostics)
        require(diagnostics["tool_function_name"] == "lookup_memory", diagnostics)
        require("unapproved_number" not in diagnostics, node)
        require("private_numeric_marker" not in diagnostics, node)
        require("user_prompt_status" not in diagnostics, node)
        require("backend_response_text_status" not in diagnostics, node)
        require("custom_page_path_id" not in diagnostics, node)
        require("custom_root_path_id" not in diagnostics, node)
        require("internal_tool_result_count" not in diagnostics, node)
        require("retrieval_evidence_status" not in diagnostics, node)
        require("tainted_source" not in diagnostics, node)
        require("status" not in diagnostics, node)
        require("decision" not in diagnostics, node)
        require("node_name" not in diagnostics, node)
        require("reason" not in diagnostics, node)
        require("schema_version_secret" not in diagnostics, node)
        require(SECRET_VALUES[6] not in diagnostics, node)
        require(SECRET_VALUES[0] not in diagnostics, node)
        require(f"{SECRET_VALUES[0]}_status" not in diagnostics, node)
        require("http://internal.example/path" not in diagnostics, node)
        require("source_url" not in diagnostics, node)
        require("candidate_text" not in diagnostics, node)
        probe = payload["metadata"]["pipeline_node_results"][1]
        require(probe["node_name"] == "nested_rejected_taint_probe", probe)
        require("status" not in probe, probe)
        require("reason" not in probe, probe)
        probe_diagnostics = probe["diagnostics"]
        require(probe_diagnostics["safe_counter_count"] == 1, probe_diagnostics)
        require("private_summary" not in probe_diagnostics, probe_diagnostics)
        unknown_probe = payload["metadata"]["pipeline_node_results"][2]
        require(
            unknown_probe["node_name"] == "unknown_top_level_taint_probe",
            unknown_probe,
        )
        require("status" not in unknown_probe, unknown_probe)
        require("reason" not in unknown_probe, unknown_probe)
        relayrun = payload["metadata"]["relayrun_artifact"]
        require(relayrun["safe_reference_id"] == "opaque-id-001", relayrun)
        require(relayrun["run_id"] == "run-content-free-001", relayrun)
        require("source" not in relayrun, relayrun)
        require("node_name" not in relayrun, relayrun)
        require("status" not in relayrun, relayrun)
        require("decision" not in relayrun, relayrun)
        require("reason" not in relayrun, relayrun)
        require("schema_version_secret" not in relayrun, relayrun)
        require("database_id" not in relayrun, relayrun)
        require("cache_id" not in relayrun, relayrun)
        require("blob_id" not in relayrun, relayrun)
        require("browser_id" not in relayrun, relayrun)
        require("page_path_id" not in relayrun, relayrun)
        require("root_path_id" not in relayrun, relayrun)
        require("content_id" not in relayrun, relayrun)
        require("url_id" not in relayrun, relayrun)
        require("user_prompt_status" not in relayrun, relayrun)
        require("backend_response_text_status" not in relayrun, relayrun)
        require("custom_page_path_id" not in relayrun, relayrun)
        require("custom_root_path_id" not in relayrun, relayrun)
        require("internal_tool_result_count" not in relayrun, relayrun)
        require("retrieval_evidence_status" not in relayrun, relayrun)
        require("evidence" not in relayrun, relayrun)
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
        print("ok forbidden metadata map keys taint matching allowed keys")
        print("ok safe audit structure keys are not over-tainted")
        print("ok arbitrary URI schemes are dropped from opaque ID fields")
        print("ok backend error types remain actionable and content-free")
        print("ok pass-through trace excludes messages response snippets paths tools and evidence")

        records = read_trace_records(trace_path)
        require(len(records) == 1, records)
        require(records[0].messages == [], records[0])
        require(records[0].response_text is None, records[0])
        require(records[0].message_count == 3, records[0])
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
