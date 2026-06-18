#!/usr/bin/env python3
"""Phase 5-C4a runtime apply smoke."""
from __future__ import annotations

import copy
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from phase5c4a_explicit_smoke_support import build_context, payload, write_config
from relaylm.client_history_exclusion_apply_runtime import run_client_history_exclusion_apply_runtime
from relaylm.pipeline_context import consume_active_pipeline_context


def main() -> int:
    with tempfile.TemporaryDirectory(dir=ROOT) as td:
        root = Path(td)
        request = payload([("system", "runtime instruction sentinel")])

        dry_cfg = root / "dry.yaml"
        write_config(dry_cfg, dry_run_only=True)
        dry_context, compiled = build_context(dry_cfg, request)
        dry_result = dry_context.client_history_exclusion_apply_result
        assert dry_result is not None
        assert dry_result.schema_version == "client_history_exclusion_apply.v1"
        assert dry_result.status == "ready"
        assert dry_result.instruction_source_mode == "explicit"
        assert dry_result.instruction_source_provenance_present is True
        assert dry_result.selected_instruction_candidate_count == 1
        assert dry_result.excluded_instruction_candidate_count == 0
        assert dry_result.payload_mutation_applied is False
        assert dry_context.forwarded_payload == compiled
        assert dry_context.last_mutating_step is None
        assert dry_context.client_instruction_identity_result is not None
        assert len(dry_result.forwarded_payload["messages"]) == 2
        assert "relaylm" not in dry_result.forwarded_payload
        assert dry_result.forwarded_payload["messages"][-1] == request["messages"][-1]
        consume_active_pipeline_context()

        apply_cfg = root / "apply.yaml"
        write_config(apply_cfg, dry_run_only=False)
        context, _ = build_context(apply_cfg, request)
        result = context.client_history_exclusion_apply_result
        assert result is not None and result.status == "applied"
        assert context.last_mutating_step == "client_history_exclusion_apply"
        assert len(context.forwarded_payload["messages"]) == 2
        assert "relaylm" not in context.forwarded_payload
        assert context.forwarded_payload["messages"][-1] == request["messages"][-1]
        prefix = context.forwarded_payload["messages"][0]["content"]
        assert "prior user sentinel" not in prefix
        assert "prior assistant sentinel" not in prefix
        assert "incoming_system_prompt" not in prefix
        assert prefix.count("runtime instruction sentinel") == 1

        before = copy.deepcopy(context.forwarded_payload)
        node_count = len(context.node_results)
        repeated = run_client_history_exclusion_apply_runtime(
            pipeline_context=context,
            compiler_used=True,
        )
        assert repeated is result
        assert context.forwarded_payload == before
        assert len(context.node_results) == node_count
        consume_active_pipeline_context()

    print("relaylm_phase5c4a_runtime_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
