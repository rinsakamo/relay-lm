from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace import AUDIT_TRACE_SCHEMA_VERSION, read_trace_records
from relaylm.trace_runtime import extract_response_text, trace_runtime_event


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    secret_user = "trace-success-user-secret"
    secret_response = "trace-success-assistant-secret"
    secret_snippet = "trace-success-snippet-secret"
    secret_path = "/home/private/relaymem/page.md"
    secret_evidence = "trace-success-evidence-secret"

    body = {
        "choices": [
            {"message": {"role": "assistant", "content": secret_response}}
        ]
    }
    response_text = extract_response_text(body)
    require(response_text == secret_response, response_text)
    print("ok extract response text")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        config = load_config(REPO_ROOT / "config.example.yaml").model_copy(deep=True)
        config.trace.enabled = True
        config.trace.path = str(trace_path)
        diagnostics = RequestDiagnostics(
            request_id="trace-success-001",
            route_model="relaylm-default",
            character_id="default",
            mode_applied="memory_light",
            compiler_used=True,
            memory_block_used=True,
            memory_source="memory_candidate_selection",
            memory_selection_summary={
                "selected_count": 1,
                "selected_memory_ids": ["default-memory-001"],
                "snippet_text": secret_snippet,
            },
            relaymem_retrieval_artifact={
                "schema_version": "relaymem.retrieval.v0",
                "snippet_text": secret_snippet,
                "root_path": secret_path,
                "evidence_envelope": {
                    "content": secret_evidence,
                    "page_path": secret_path,
                },
            },
            relayrun_artifact={
                "schema_version": "relayrun.runtime_checkpoint.v0",
                "diagnostics_only": True,
                "content_free": True,
                "run_id": "run-trace-001",
                "run_status": "diagnostics_only",
                "target_path_preview": secret_path,
                "blocked_reasons": [],
            },
            trace_enabled=True,
        )
        written = trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": secret_user}],
            response_text=response_text,
            metadata={
                "event": "backend_response",
                "status_code": 200,
                "unknown_metadata": secret_evidence,
            },
        )
        require(written is True, written)

        raw = trace_path.read_text(encoding="utf-8")
        for secret in (
            secret_user,
            secret_response,
            secret_snippet,
            secret_path,
            secret_evidence,
        ):
            require(secret not in raw, raw)

        payload = json.loads(raw)
        require(payload["schema_version"] == AUDIT_TRACE_SCHEMA_VERSION, payload)
        require(payload["content_free"] is True, payload)
        require(payload["message_count"] == 1, payload)
        require(payload["response_present"] is True, payload)
        require("messages" not in payload, payload)
        require("response_text" not in payload, payload)
        metadata = payload["metadata"]
        require(metadata["event"] == "backend_response", metadata)
        require(metadata["status_code"] == 200, metadata)
        require(metadata["memory_source"] == "memory_candidate_selection", metadata)
        require(metadata["memory_selection_summary"]["selected_count"] == 1, metadata)
        require(
            metadata["memory_selection_summary"]["selected_memory_ids"]
            == ["default-memory-001"],
            metadata,
        )
        require("snippet_text" not in metadata["memory_selection_summary"], metadata)
        require("relaymem_retrieval_artifact" not in metadata, metadata)
        require("evidence_envelope" not in metadata, metadata)
        require(metadata["relayrun_artifact"]["run_id"] == "run-trace-001", metadata)
        require("target_path_preview" not in metadata["relayrun_artifact"], metadata)
        require(metadata.get("sanitizer_dropped_field_count", 0) > 0, metadata)

        records = read_trace_records(trace_path)
        require(len(records) == 1, records)
        record = records[0]
        require(record.trace_id == "trace-success-001", record)
        require(record.message_count == 1, record)
        require(record.response_present is True, record)
        require(record.messages == [], record)
        require(record.response_text is None, record)
        print("ok trace backend response event persisted as content-free audit record")
        print("ok runtime trace redacts response memory evidence and local paths")

        stream_trace_path = Path(tmpdir) / "stream-trace.jsonl"
        config.trace.path = str(stream_trace_path)
        stream_diagnostics = RequestDiagnostics(
            request_id="trace-stream-001",
            route_model="relaylm-default",
            character_id="default",
            mode_applied="pass_through",
            compiler_used=False,
            trace_enabled=True,
        )
        stream_written = trace_runtime_event(
            config=config,
            diagnostics=stream_diagnostics,
            messages=[{"role": "user", "content": secret_user}],
            response_text=None,
            metadata={
                "event": "backend_stream_response",
                "status_code": 200,
                "content_type": "text/event-stream",
            },
        )
        require(stream_written is True, stream_written)

        charset_written = trace_runtime_event(
            config=config,
            diagnostics=stream_diagnostics,
            messages=[{"role": "user", "content": secret_user}],
            response_text=None,
            metadata={
                "event": "backend_stream_response",
                "status_code": 200,
                "content_type": "text/event-stream; charset=utf-8",
            },
        )
        require(charset_written is True, charset_written)

        unsafe_written = trace_runtime_event(
            config=config,
            diagnostics=stream_diagnostics,
            messages=[{"role": "user", "content": secret_user}],
            response_text=None,
            metadata={
                "event": "backend_stream_response",
                "status_code": 200,
                "content_type": "http://internal.example/path",
            },
        )
        require(unsafe_written is True, unsafe_written)

        stream_payloads = [
            json.loads(line)
            for line in stream_trace_path.read_text(encoding="utf-8").splitlines()
        ]
        require(len(stream_payloads) == 3, stream_payloads)
        stream_metadata = stream_payloads[0]["metadata"]
        require(stream_metadata["event"] == "backend_stream_response", stream_metadata)
        require(stream_metadata["status_code"] == 200, stream_metadata)
        require(stream_metadata["content_type"] == "text/event-stream", stream_metadata)
        charset_metadata = stream_payloads[1]["metadata"]
        require(
            charset_metadata["content_type"] == "text/event-stream; charset=utf-8",
            charset_metadata,
        )
        unsafe_metadata = stream_payloads[2]["metadata"]
        require("content_type" not in unsafe_metadata, unsafe_metadata)
        print("ok stream trace preserves validated content_type audit metadata")
        print("ok stream trace rejects URL-shaped content_type metadata")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
