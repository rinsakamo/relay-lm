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


def require(condition: bool, message: object) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    with tempfile.TemporaryDirectory() as tmpdir:
        trace_path = Path(tmpdir) / "trace.jsonl"
        base = load_config(REPO_ROOT / "config.example.yaml")
        config_dict = base.model_dump()
        config_dict["trace"] = {"enabled": True, "path": str(trace_path)}
        config = RelayLMConfig.model_validate(config_dict)
        payload = {
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
            request_id="req-token-trace-payload",
            token_memory_dry_run=payload,
        )

        written = trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            messages=[{"role": "user", "content": "hello"}],
        )
        require(written, "trace record was not written")
        require(trace_path.exists(), "trace file was not created")

        lines = trace_path.read_text(encoding="utf-8").strip().splitlines()
        require(len(lines) == 1, lines)
        record = json.loads(lines[0])
        metadata = record.get("metadata")
        require(isinstance(metadata, dict), metadata)
        require(metadata.get("token_memory_dry_run") == payload, metadata)
        print("ok trace token memory dry run payload")

        log_payload = diagnostics.to_log_dict()
        require(log_payload["token_memory_dry_run"] == payload, log_payload)
        print("ok diagnostics token memory dry run log payload")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
