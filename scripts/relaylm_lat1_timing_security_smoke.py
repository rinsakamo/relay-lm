"""LAT-1 security smoke: timing fields and bench output stay content-free.

Verifies:
1. RelayRunNode timing fields (started_at/completed_at) and timing_summary
   never carry anything except ISO timestamp strings, non-negative ints, or
   null -- no request/response body text, no filesystem paths.
2. The retrieval bench's output JSON contains only the documented numeric
   fields -- no query text and no synthetic page body content.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from relaylm.relayrun import build_relayrun_node, build_relayrun_timing_summary

_ISO_TIMESTAMP_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(\+\d{2}:\d{2}|Z)$"
)

_ALLOWED_TIMING_SUMMARY_KEYS = {
    "schema_version",
    "pipeline_overhead_ms",
    "backend_forward_ms",
    "time_to_first_token_ms",
    "retrieval_ms",
    "nodes_timed_count",
    "nodes_untimed_count",
}

_ALLOWED_BENCH_RESULT_KEYS = {
    "store_size",
    "query_count",
    "repeat",
    "p50_ms",
    "p95_ms",
    "avg_selected_count",
}


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def check_node_timing_fields_are_content_free() -> None:
    secret = "SHOULD_NEVER_LEAK/etc/production/secrets.txt"
    now = "2026-07-07T00:00:00.000000+00:00"
    later = "2026-07-07T00:00:00.010000+00:00"

    node = build_relayrun_node(
        node_name="relaymem_retrieval",
        node_status="completed",
        started_at=now,
        completed_at=later,
        duration_ms=10,
    )
    require(_ISO_TIMESTAMP_RE.match(node["started_at"]) is not None, node)
    require(_ISO_TIMESTAMP_RE.match(node["completed_at"]) is not None, node)
    require(isinstance(node["duration_ms"], int) and not isinstance(node["duration_ms"], bool), node)
    require(secret not in json.dumps(node, ensure_ascii=False), node)

    # Missing either timestamp must force duration_ms to null, never a
    # backfilled/guessed number.
    partial_node = build_relayrun_node(
        node_name="relaymem_retrieval",
        node_status="completed",
        started_at=now,
        completed_at=None,
        duration_ms=10,
    )
    require(partial_node["duration_ms"] is None, partial_node)
    print("ok RelayRunNode timing fields are timestamp/int/null only, never backfilled")

    timing_summary = build_relayrun_timing_summary(
        [
            {"node_name": "relayrel", "node_status": "completed", "duration_ms": 5},
            {"node_name": "relaymem_retrieval", "node_status": "completed", "duration_ms": 7},
            {"node_name": "backend_forward", "node_status": "completed", "duration_ms": 90},
            {"node_name": "relayemo", "node_status": "skipped", "duration_ms": None},
        ]
    )
    require(set(timing_summary.keys()) == _ALLOWED_TIMING_SUMMARY_KEYS, timing_summary)
    for key, value in timing_summary.items():
        if key == "schema_version":
            require(isinstance(value, str) and secret not in value, timing_summary)
            continue
        require(
            value is None or (isinstance(value, int) and not isinstance(value, bool)),
            (key, value, timing_summary),
        )
    print("ok timing_summary keys are the fixed numeric/null/schema_version set")


def check_bench_output_is_content_free() -> None:
    from relaylm_lat1_retrieval_bench import _build_query_set, _run_one_size
    from relaylm_lat1_bench_store_generator import _generate_store
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        store_root = Path(td) / "size_12"
        _generate_store(store_root, size=12, seed=1)
        queries = _build_query_set()
        require(len(queries) == 20, queries)

        result = _run_one_size(store_root, size=12, queries=queries, repeat=1, max_candidates=3)
        require(set(result.keys()) == _ALLOWED_BENCH_RESULT_KEYS, result)

        encoded = json.dumps(result, ensure_ascii=False)
        for query in queries:
            require(query not in encoded, (query, result))
        # No page body text (synthetic vocabulary) or filesystem path leaks
        # into the numeric result record.
        require(str(store_root) not in encoded, (store_root, result))
        require("memory/mem" not in encoded, result)
        print("ok retrieval bench result JSON contains only the documented numeric fields")


def main() -> int:
    check_node_timing_fields_are_content_free()
    check_bench_output_is_content_free()
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
