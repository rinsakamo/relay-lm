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
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_config(REPO_ROOT / "config.example.yaml").model_copy(deep=True)
        config.trace.enabled = True
        trace_path = Path(tmpdir) / "trace.jsonl"
        config.trace.path = str(trace_path)
        diagnostics = RequestDiagnostics(
            request_id="trace-success-001",
            route_model="relaylm-default",
            character_id="default",
            mode_applied="memory_light",
            compiler_used=True,
            memory_source="memory_candidate_selection",
            memory_selection_summary={
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
            },
            relayrun_artifact={
                "schema_version": "relayrun.runtime_checkpoint.v0",
                "content_free": True,
                "run_id": "run-trace-001",
                "run_status": "diagnostics_only",
            },
            trace_enabled=True,
        )
        require(
            trace_runtime_event(
                config=config,
                diagnostics=diagnostics,
                message_count=1,
                response_present=True,
                metadata={"event": "backend_response", "status_code": 200},
            ),
            "trace write failed",
        )
        payload = json.loads(trace_path.read_text(encoding="utf-8"))
        require(payload["schema_version"] == AUDIT_TRACE_SCHEMA_VERSION, payload)
        require(payload["message_count"] == 1, payload)
        require(payload["response_present"] is True, payload)
        metadata = payload["metadata"]
        require(metadata["event"] == "backend_response", metadata)
        require(metadata["status_code"] == 200, metadata)
        require(metadata["memory_source"] == "memory_candidate_selection", metadata)
        require(
            metadata["memory_selection_summary"]["selected_memory_ids"]
            == ["memory-001"],
            metadata,
        )
        require(metadata["relayrun_artifact"]["run_id"] == "run-trace-001", metadata)
        record = read_trace_records(trace_path)[0]
        require(record.messages == [], record)
        require(record.response_text is None, record)
        print("ok successful response writes a typed audit record")

        empty_path = Path(tmpdir) / "empty.jsonl"
        config.trace.path = str(empty_path)
        require(
            trace_runtime_event(
                config=config,
                diagnostics=diagnostics,
                message_count=1,
                response_present=True,
                metadata={"event": "backend_response", "status_code": 200},
            ),
            "empty response trace write failed",
        )
        require(
            json.loads(empty_path.read_text(encoding="utf-8"))["response_present"]
            is True,
            empty_path,
        )
        print("ok empty string response shape remains present")

        stream_path = Path(tmpdir) / "stream.jsonl"
        config.trace.path = str(stream_path)
        for content_type in (
            "text/event-stream",
            "text/event-stream; charset=utf-8",
            "invalid-media-type",
        ):
            require(
                trace_runtime_event(
                    config=config,
                    diagnostics=diagnostics,
                    message_count=1,
                    response_present=False,
                    metadata={
                        "event": "backend_stream_response",
                        "status_code": 200,
                        "content_type": content_type,
                    },
                ),
                content_type,
            )
        stream_rows = [
            json.loads(line)
            for line in stream_path.read_text(encoding="utf-8").splitlines()
        ]
        require(stream_rows[0]["metadata"]["content_type"] == "text/event-stream", stream_rows)
        require(
            stream_rows[1]["metadata"]["content_type"]
            == "text/event-stream; charset=utf-8",
            stream_rows,
        )
        require("content_type" not in stream_rows[2]["metadata"], stream_rows)
        print("ok stream response keeps only validated media types")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
