#!/usr/bin/env python3
"""Check normalized candidate IDs retain their M3b operation index."""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from relaylm_merged_review_residuals_smoke import _primary_candidate, require
from relaylm.relaymem_primary_page_candidate import (
    build_relaymem_governed_experience_summary,
    build_relaymem_primary_page_candidate_dry_run,
)
from relaylm.relaymem_primary_write_preflight import (
    build_relaymem_primary_source_lineage,
    build_relaymem_primary_write_preflight_dry_run,
)


def main() -> int:
    first = _primary_candidate()
    second = dict(first)
    second["candidate_id"] = f"{first['candidate_id']}-second"
    lineage = build_relaymem_primary_source_lineage(
        source_event_kind="turn",
        source_event_id="turn-normalized-index",
        namespace="normalized-index",
    )
    preflight = build_relaymem_primary_write_preflight_dry_run(
        candidates=[first, second],
        source_lineage_artifact=lineage,
        enabled=True,
    )
    experience = build_relaymem_governed_experience_summary(
        candidate_id=second["candidate_id"],
        source_event_kind=second["source_event_kind"],
        namespace="normalized-index",
        summary_text="Whitespace normalization must preserve operation correlation.",
    )
    experience["candidate_id"] = f"  {second['candidate_id']}  "
    result = build_relaymem_primary_page_candidate_dry_run(
        preflight_artifact=preflight,
        source_lineage_artifact=lineage,
        governed_experience_artifact=experience,
        enabled=True,
    )
    require(result["page_candidate_count"] == 1, result)
    require(result["projection"]["page_candidates"][0]["operation_index"] == 1, result)
    print("ok normalized M3c candidate ID preserves operation index")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
