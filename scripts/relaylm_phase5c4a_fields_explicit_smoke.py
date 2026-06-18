#!/usr/bin/env python3
"""Phase 5-C4a explicit-provenance field preservation smoke."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_explicit_smoke_support import build_context, payload, write_config
from relaylm.pipeline_context import consume_active_pipeline_context


def main() -> int:
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        cfg = root / "apply.yaml"
        write_config(cfg, dry_run_only=False)
        multimodal = [
            {"type": "text", "text": "exact multimodal current sentinel"},
            {
                "type": "image_url",
                "image_url": {"url": "https://example.invalid/current.png"},
            },
        ]
        request = payload(
            [("developer", "field instruction sentinel")],
            current=multimodal,
        )
        context, _ = build_context(cfg, request)
        result = context.client_history_exclusion_apply_result
        assert result is not None and result.status == "applied"
        assert context.forwarded_payload["messages"][-1] == request["messages"][-1]
        assert len(context.forwarded_payload["messages"]) == 2
        assert "relaylm" not in context.forwarded_payload
        assert all(
            message.get("role") != "developer"
            for message in context.forwarded_payload["messages"]
        )
        for key in (
            "tools",
            "tool_choice",
            "response_format",
            "temperature",
            "top_p",
            "max_tokens",
            "stream",
            "provider_options",
        ):
            assert context.forwarded_payload[key] == request[key]
        consume_active_pipeline_context()

        pass_cfg = root / "pass.yaml"
        write_config(pass_cfg, dry_run_only=False, mode="pass_through")
        pass_context, _ = build_context(pass_cfg, request)
        pass_result = pass_context.client_history_exclusion_apply_result
        assert pass_result is not None and pass_result.status == "skipped"
        assert pass_context.forwarded_payload == request
        assert pass_context.last_mutating_step is None
        consume_active_pipeline_context()

    print("relaylm_phase5c4a_fields_explicit_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
