from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.trace import read_trace_records


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace-path", required=True)
    parser.add_argument("--expected-count", type=int, default=1)
    parser.add_argument("--expected-event", default="backend_error")
    args = parser.parse_args()

    records = read_trace_records(args.trace_path)
    require(len(records) == args.expected_count, records)
    record = records[-1]
    require(record.trace_id, record)
    require(record.content_free is True, record)
    require(record.metadata.get("event") == args.expected_event, record.metadata)
    require(record.message_count > 0, record)
    require(record.messages == [], record)
    require(record.response_text is None, record)
    print("ok trace file count")
    print("ok trace backend error event")
    print("ok trace message count captured without message content")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
