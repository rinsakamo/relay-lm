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


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "conversation.jsonl"
        require(read_trace_records(trace_path) == [], "missing trace should read empty")
        print("ok empty trace read")

        record = build_trace_record(
            trace_id="trace-001",
            created_at="2026-05-21T00:00:00+00:00",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="memory_light",
            compiler_used=True,
            messages=[{"role": "user", "content": "secret-user-content"}],
            response_text="secret-assistant-content",
            metadata={"event": "backend_response", "status_code": 200},
        )
        append_trace_record(trace_path, record)
        records = read_trace_records(trace_path)
        require(len(records) == 1, records)
        first = records[0]
        require(first.trace_id == "trace-001", first)
        require(first.request_id == "trace-001", first)
        require(first.character_id == "default", first)
        require(first.compiler_used is True, first)
        require(first.schema_version == AUDIT_TRACE_SCHEMA_VERSION, first)
        require(first.content_free is True, first)
        require(first.message_count == 1, first)
        require(first.response_present is True, first)
        require(first.messages == [], first)
        require(first.response_text is None, first)
        require(first.metadata["event"] == "backend_response", first)
        raw = trace_path.read_text(encoding="utf-8")
        require("secret-user-content" not in raw, raw)
        require("secret-assistant-content" not in raw, raw)
        payload = json.loads(raw.splitlines()[0])
        require("messages" not in payload, payload)
        require("response_text" not in payload, payload)
        print("ok append and read content-free audit trace record")

        second = build_trace_record(
            trace_id="trace-002",
            created_at="2026-05-21T00:01:00+00:00",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="pass_through",
            compiler_used=False,
            messages=[{"role": "user", "content": "next-secret"}],
        )
        append_trace_record(trace_path, second)
        records = read_trace_records(trace_path)
        require([item.trace_id for item in records] == ["trace-001", "trace-002"], records)
        require(records[1].message_count == 1, records[1])
        require(records[1].response_present is False, records[1])
        require("next-secret" not in trace_path.read_text(encoding="utf-8"), trace_path)
        print("ok append multiple content-free audit records")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
