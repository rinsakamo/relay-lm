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
        diagnostics = RequestDiagnostics(
            request_id="trace-success-001",
            route_model="relaylm-default",
            character_id="default",
            mode_applied="pass_through",
            compiler_used=False,
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
        print("ok trace backend response event")
        print("ok trace response text captured")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
