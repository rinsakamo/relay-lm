#!/usr/bin/env python3
"""Phase 5-C4a fail-closed gate smoke."""
from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_smoke_support import build_context, payload, write_config
from relaylm.client_history_exclusion_apply_runtime import (
    client_history_exclusion_apply_blocks_backend,
    client_history_exclusion_apply_failure_reason,
)
from relaylm.pipeline_context import consume_active_pipeline_context


def main() -> int:
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        cfg = root / "apply.yaml"
        write_config(cfg, dry_run_only=False)

        for stream in (False, True):
            oversized = payload(
                [("system", "x" * 5000)],
                stream=stream,
            )
            context, _ = build_context(cfg, oversized)
            result = context.client_history_exclusion_apply_result
            assert result is not None and result.status == "blocked"
            assert "instruction_evidence_oversize" in result.blocked_reasons
            assert client_history_exclusion_apply_blocks_backend(
                context.route,
                result,
                forwarded_payload=context.forwarded_payload,
            )
            assert (
                client_history_exclusion_apply_failure_reason(result)
                == "client_history_exclusion_apply_blocked"
            )
            consume_active_pipeline_context()

        active = payload([("developer", "active tool sentinel")])
        active["messages"].append(
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_phase5c4a",
                        "type": "function",
                        "function": {"name": "lookup", "arguments": "{}"},
                    }
                ],
            }
        )
        tool_context, _ = build_context(cfg, active)
        tool_result = tool_context.client_history_exclusion_apply_result
        assert tool_result is not None and tool_result.status == "blocked"
        assert (
            "active_tool_transaction_requires_preservation"
            in tool_result.blocked_reasons
        )
        assert client_history_exclusion_apply_blocks_backend(
            tool_context.route,
            tool_result,
            forwarded_payload=tool_context.forwarded_payload,
        )
        consume_active_pipeline_context()

        normal = payload([("system", "exact apply sentinel")])
        normal_context, _ = build_context(cfg, normal)
        normal_result = normal_context.client_history_exclusion_apply_result
        assert normal_result is not None and normal_result.status == "applied"
        assert not client_history_exclusion_apply_blocks_backend(
            normal_context.route,
            normal_result,
            forwarded_payload=normal_context.forwarded_payload,
        )

        drifted = copy.deepcopy(normal_context.forwarded_payload)
        drifted["messages"].insert(
            -1,
            {"role": "system", "content": "downstream repack drift sentinel"},
        )
        assert client_history_exclusion_apply_blocks_backend(
            normal_context.route,
            normal_result,
            forwarded_payload=drifted,
        )
        consume_active_pipeline_context()

    print("relaylm_phase5c4a_gate_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
