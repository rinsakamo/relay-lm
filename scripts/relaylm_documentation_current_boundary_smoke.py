#!/usr/bin/env python3
"""Validate current docs while keeping PROJECT_STATUS a concise current-state authority."""
from __future__ import annotations

from relaylm_documentation_current_boundary_core import REQUIRED, main as core_main, read

# PROJECT_STATUS is intentionally checked for current authority, active migration state,
# caveats, and next work. Completed-slice prose and handoff link text belong in the
# reference map and must not be frozen here as exact historical anchors.
REQUIRED["docs/PROJECT_STATUS.md"] = (
    "relaylm_authority: current_project_state",
    "relaylm_status: current",
    "This page owns current implementation status and active caveats.",
    "## Current implementation position",
    "EV-1 Governed Evidence runtime foundation: complete",
    "OVL-1 CTX-OVL participant-private vertical slice: complete",
    "ASM-1 Shared Assessment runtime foundation: complete",
    "SM-1 Subjective MEM create decision/result vertical slice: complete",
    "ST-1 Markdown + operations commit protocol: next registered slice; not started",
    "## Contract-aligned implementation migration boundary",
    "## Current caveats",
    "## Immediate dependency-first work",
    "## Not yet implemented",
    "Project Status Reference Map",
)

_STATUS_HISTORY_ONLY_ANCHORS = (
    "Post-O1F next candidates:",
    "Character Workspace reset:",
    "Completed post-MVP debt:",
    "Post-E1-R5 / Post-Wave-7 next candidates:",
    "## O1B sealed replay-lane boundary",
    "## Offline tooling addenda",
)


def assert_project_status_is_current_scoped() -> None:
    body = read("docs/PROJECT_STATUS.md")
    stale_history = [anchor for anchor in _STATUS_HISTORY_ONLY_ANCHORS if anchor in body]
    assert not stale_history, (
        "docs/PROJECT_STATUS.md: history-only detail belongs in "
        f"docs/reference/project-status-reference-map.md: {stale_history!r}"
    )


def main() -> None:
    assert_project_status_is_current_scoped()
    core_main()


if __name__ == "__main__":
    main()
