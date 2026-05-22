from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace import read_trace_records
from relaylm.trace_runtime import extract_response_text, trace_runtime_event


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    body = {
        "choices": [
            {"message": {"role": "assistant", "content": "hello from backend"}}
        ]
    }
    response_text = extract_response_text(body)
    require(response_text == "hello from backend", response_text)
    print("ok extract response text")

    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        config = load_config(REPO_ROOT / "config.example.yaml").model_copy(deep=True)
        config.trace.enabled = True
        config.trace.path = str(trace_path)
        selection_summary = {
            "selected_count": 3,
            "selected_memory_ids": [
                "default-relaylm-project",
                "default-like-tea",
                "shared-short-replies",
            ],
            "state_counts": {
                "active": 3,
                "promoted": 0,
                "demoted": 0,
                "disabled": 0,
            },
        }
        diagnostics = RequestDiagnostics(
            request_id="trace-success-001",
            route_model="relaylm-default",
            character_id="default",
            mode_applied="memory_light",
            compiler_used=True,
            memory_block_used=True,
            memory_source="memory_candidate_selection",
            memory_selection_summary=selection_summary,
            trace_enabled=True,
        )
        written = trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
            response_text=response_text,
            metadata={"event": "backend_response", "status_code": 200},
        )
        require(written is True, written)
        records = read_trace_records(trace_path)
        require(len(records) == 1, records)
        require(records[0].trace_id == "trace-success-001", records[0])
        require(records[0].response_text == "hello from backend", records[0])
        require(records[0].metadata["event"] == "backend_response", records[0].metadata)
        require(records[0].metadata["status_code"] == 200, records[0].metadata)
        require(records[0].metadata["memory_source"] == "memory_candidate_selection", records[0].metadata)
        require(records[0].metadata["memory_selection_summary"] == selection_summary, records[0].metadata)
        print("ok trace backend response event")
        print("ok trace response text captured")
        print("ok trace memory source captured")
        print("ok trace memory selection summary captured")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
