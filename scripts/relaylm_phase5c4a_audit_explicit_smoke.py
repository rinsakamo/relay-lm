#!/usr/bin/env python3
"""Phase 5-C4a explicit-provenance audit projection smoke."""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_explicit_smoke_support import build_context, payload, write_config
from relaylm.config import load_config
from relaylm.diagnostics import RequestDiagnostics
from relaylm.trace_runtime import trace_runtime_event


def main() -> int:
    raw = "audit private sentinel"
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        trace_path = root / "trace.jsonl"
        cfg_path = root / "cfg.yaml"
        write_config(
            cfg_path,
            dry_run_only=False,
            trace_path=str(trace_path),
        )
        context, _ = build_context(
            cfg_path,
            payload([("system", raw)]),
        )
        result = context.client_history_exclusion_apply_result
        assert result is not None and result.status == "applied"
        config = load_config(cfg_path)
        diagnostics = RequestDiagnostics(
            request_id="phase5c4a-audit",
            route_model="relaylm-default",
            character_id="default",
            mode_applied="memory_light",
            compiler_used=True,
            trace_enabled=True,
        )
        assert trace_runtime_event(
            config=config,
            diagnostics=diagnostics,
            message_count=2,
            response_present=False,
            metadata={"event": "backend_request"},
        )
        encoded = trace_path.read_text(encoding="utf-8")
        assert raw not in encoded
        assert "message_indices" not in encoded
        row = json.loads(encoded.strip().splitlines()[-1])
        apply_rows = [
            item
            for item in row["metadata"]["pipeline_node_results"]
            if item.get("node_name") == "client_history_exclusion_apply"
        ]
        assert len(apply_rows) == 1
        projected = apply_rows[0]["diagnostics"]
        assert projected["schema_version"] == "client_history_exclusion_apply.v1"
        assert projected["instruction_source_mode"] == "explicit"
        assert projected["instruction_source_provenance_present"] is True
        assert projected["relaylm_control_forwarded"] is False

    print("relaylm_phase5c4a_audit_explicit_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
