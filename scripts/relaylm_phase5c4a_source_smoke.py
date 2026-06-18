#!/usr/bin/env python3
"""Phase 5-C4a explicit instruction-source provenance smoke."""
from __future__ import annotations

import json
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

        selected = "selected instruction sentinel"
        summary = "frontend summary must be excluded sentinel"
        request = payload(
            [("system", selected), ("system", summary)],
            selected_instruction_indices=[0],
        )
        context, _ = build_context(cfg, request)
        result = context.client_history_exclusion_apply_result
        assert result is not None and result.status == "applied"
        assert result.instruction_source_mode == "explicit"
        assert result.instruction_source_provenance_present is True
        assert result.instruction_candidate_count == 2
        assert result.selected_instruction_candidate_count == 1
        assert result.excluded_instruction_candidate_count == 1
        prefix = context.forwarded_payload["messages"][0]["content"]
        assert prefix.count(selected) == 1
        assert summary not in prefix
        assert "relaylm" not in context.forwarded_payload
        projection = json.dumps(context.node_results_to_log_dicts(), sort_keys=True)
        assert "selected_source_indices" not in projection
        assert "excluded_source_indices" not in projection
        assert selected not in projection
        assert summary not in projection
        consume_active_pipeline_context()

        missing = payload(
            [("developer", "missing provenance sentinel")],
            include_provenance=False,
        )
        missing_context, _ = build_context(cfg, missing)
        missing_result = missing_context.client_history_exclusion_apply_result
        assert missing_result is not None and missing_result.status == "blocked"
        assert "instruction_source_provenance_missing" in missing_result.blocked_reasons
        consume_active_pipeline_context()

        invalid_cases = (
            ([0, 0], "instruction_source_indices_invalid"),
            ([99], "instruction_source_indices_invalid"),
            ([2], "instruction_source_role_mismatch"),
        )
        for indices, expected_reason in invalid_cases:
            invalid = payload(
                [("system", "invalid provenance sentinel")],
                selected_instruction_indices=indices,
            )
            invalid_context, _ = build_context(cfg, invalid)
            invalid_result = invalid_context.client_history_exclusion_apply_result
            assert invalid_result is not None and invalid_result.status == "blocked"
            assert expected_reason in invalid_result.blocked_reasons
            consume_active_pipeline_context()

    print("relaylm_phase5c4a_source_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
