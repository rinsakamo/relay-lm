from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.trace import append_trace_record, build_trace_record, read_trace_records


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "conversation.jsonl"
        empty_records = read_trace_records(trace_path)
        require(empty_records == [], empty_records)
        print("ok empty trace read")

        record = build_trace_record(
            trace_id="trace-001",
            created_at="2026-05-21T00:00:00+00:00",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="memory_light",
            compiler_used=True,
            messages=[{"role": "user", "content": "hello"}],
            response_text="hi",
            metadata={"source": "smoke"},
        )
        append_trace_record(trace_path, record)
        records = read_trace_records(trace_path)
        require(len(records) == 1, records)
        require(records[0].trace_id == "trace-001", records[0])
        require(records[0].character_id == "default", records[0])
        require(records[0].compiler_used is True, records[0])
        require(records[0].messages[0]["content"] == "hello", records[0])
        require(records[0].response_text == "hi", records[0])
        require(records[0].metadata["source"] == "smoke", records[0])
        print("ok append and read trace record")

        second = build_trace_record(
            trace_id="trace-002",
            created_at="2026-05-21T00:01:00+00:00",
            character_id="default",
            route_model="relaylm-default",
            mode_applied="pass_through",
            compiler_used=False,
            messages=[{"role": "user", "content": "next"}],
        )
        append_trace_record(trace_path, second)
        records = read_trace_records(trace_path)
        require([record.trace_id for record in records] == ["trace-001", "trace-002"], records)
        print("ok append multiple trace records")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
