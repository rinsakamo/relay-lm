#!/usr/bin/env python3
"""Phase 5-C4a projection smoke."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from relaylm.client_history_exclusion_apply_v1_types import (
    build_client_history_exclusion_apply_v1_result,
)
from relaylm.managed_apply_projection import (
    build_instruction_bearing_apply_node_result,
)


def main() -> int:
    result = build_client_history_exclusion_apply_v1_result(
        status="applied",
        forwarded_payload={"messages": []},
        dry_run_only=False,
        managed_route=True,
        compiler_used=True,
        relay_owned_prefix_message_count=1,
        forwarded_message_count=2,
        instruction_resolution_mode="cache_miss_first_pass",
        instruction_source_mode="explicit",
        instruction_source_provenance_present=True,
        instruction_candidate_count=2,
        selected_instruction_candidate_count=1,
        excluded_instruction_candidate_count=1,
        instruction_evidence_block_present=True,
        legacy_incoming_system_prompt_replaced=True,
        payload_candidate_present=True,
        payload_mutation_applied=True,
    )
    row = build_instruction_bearing_apply_node_result(result).to_log_dict()
    assert row["status"] == "applied"
    assert row["blocked_reasons"] == []
    diag = row["diagnostics"]
    assert diag["schema_version"] == "client_history_exclusion_apply.v1"
    assert diag["instruction_source_mode"] == "explicit"
    assert diag["instruction_source_provenance_present"] is True
    assert diag["instruction_candidate_count"] == 2
    assert diag["selected_instruction_candidate_count"] == 1
    assert diag["excluded_instruction_candidate_count"] == 1
    assert diag["raw_instruction_message_forwarded"] is False
    assert diag["relaylm_control_forwarded"] is False
    assert diag["cache_entry_content_injected"] is False
    assert diag["cache_projection_applied"] is False
    assert diag["content_bearing_candidate_persisted"] is False
    assert "forwarded_payload" not in diag
    assert "selected_source_indices" not in diag
    assert "excluded_source_indices" not in diag
    assert "normalized_text" not in diag
    print("relaylm_phase5c4a_projection_smoke passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
