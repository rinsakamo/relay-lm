#!/usr/bin/env python3
"""Run E1 evidence convergence without freezing its history into PROJECT_STATUS."""
from relaylm_e1_evaluation_consolidation_smoke_core import REQUIRED, main

REQUIRED.pop("docs/PROJECT_STATUS.md", None)
REQUIRED["docs/reference/project-status-reference-map.md"] = (
    "## Completed foundation inventory",
    "E1-R1 through E1-R5",
    "## Phase 6 and E1 boundary notes",
    "E1-R4 remains request-side grounding",
    "E1-R5 remains a bounded query-hinted fallback",
)


if __name__ == "__main__":
    main()
