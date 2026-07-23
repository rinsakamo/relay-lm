#!/usr/bin/env python3
"""Run Wave 5 convergence without freezing completed-wave prose in PROJECT_STATUS."""
from relaylm_wave5_cross_slice_convergence_smoke_core import REQUIRED, main

REQUIRED.pop("docs/PROJECT_STATUS.md", None)
REQUIRED["docs/reference/project-status-reference-map.md"] = (
    "## Completed foundation inventory",
    "RelaySLP durable enqueue, fenced lifecycle, one-job execution, local worker, O1 scheduler",
    "E1-R1 through E1-R5",
    "Wave 3 through Wave 7 integration tracks",
    "Primary MEM Correct, Forget/Hide, Pin/Unpin, Held Apply/Discard",
)


if __name__ == "__main__":
    main()
