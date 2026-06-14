from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from relaylm.config import RelayLMConfig, load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace_runtime import trace_runtime_event


def require(condition: bool, detail: object) -> None:
    if not condition:
        raise AssertionError(detail)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        config_data = load_config(REPO_ROOT / "config.example.yaml").model_dump()
        config_data["trace"] = {"enabled": True, "path": str(trace_path)}
        config = RelayLMConfig.model_validate(config_data)
        summary = {
            "summary": {
                "selected_memory_ids": ["m1", "m2"],
                "excluded_disabled_ids": ["m3"],
            },
            "assembly": {
                "included_memory_ids": ["m1"],
                "dropped_memory_ids": ["m2"],
                "token_budget": 128,
                "estimated_tokens": 42,
            },
        }
        diagnostics = RequestDiagnostics(
            request_id="req-token-trace",
            token_memory_dry_run=summary,
        )
        written = trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            message_count=1,
            response_present=False,
        )
        require(written, "trace write failed")
        record = json.loads(trace_path.read_text(encoding="utf-8"))
        metadata = record["metadata"]
        require(metadata["token_memory_dry_run"] == summary, metadata)
        require(diagnostics.to_log_dict()["token_memory_dry_run"] == summary, diagnostics)
        print("ok token memory trace projection")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
