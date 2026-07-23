#!/usr/bin/env python3
"""Run Wave 4 convergence without freezing completed-wave prose in PROJECT_STATUS."""
from relaylm_wave4_cross_slice_convergence_smoke_core import CURRENT_REQUIRED, main

CURRENT_REQUIRED.pop("docs/PROJECT_STATUS.md", None)
CURRENT_REQUIRED["docs/reference/project-status-reference-map.md"] = (
    "## Completed foundation inventory",
    "O1 is complete through the validation-only caller-invoked local scheduler boundary.",
    "Primary MEM Correct, Forget/Hide, Pin/Unpin, Held Apply/Discard",
    "Wave 3 through Wave 7 integration tracks",
)


if __name__ == "__main__":
    main()
