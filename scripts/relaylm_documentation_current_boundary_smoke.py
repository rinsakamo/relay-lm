#!/usr/bin/env python3
"""Validate the small set of documents that own RelayLM's current boundary."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = {
    "docs/PROJECT_STATUS.md": (
        "relaylm_authority: current_project_state",
        "relaylm_status: current",
        "This page owns current implementation status and active caveats.",
        "## Current implementation position",
        "EV-1 Governed Evidence runtime foundation: complete",
        "OVL-1 CTX-OVL participant-private vertical slice: complete",
        "ASM-1 Shared Assessment runtime foundation: complete",
        "SM-1 Subjective MEM create decision/result vertical slice: complete",
        "ST-1 Markdown + operations commit protocol: complete; default-off, create-only, POSIX apply",
        "## Contract-aligned implementation migration boundary",
        "## Current caveats",
        "## Immediate dependency-first work",
        "LC-1 lifecycle migration                                    in progress; LC-1A Correct, LC-1B Forget, and LC-1C Pin/Unpin implemented",
        "LC-1D Restore                                          next ordered slice; not started",
        "## Not yet implemented",
        "Project Status Reference Map",
    ),
    "docs/reference/project-status-reference-map.md": (
        "relaylm_authority: project_status_reference_map",
        "relaylm_not_authoritative_for:",
        "current implementation status",
        "Current state remains owned by [RelayLM Project Status]",
        "## Completed foundation inventory",
        "## Implementation handoff and evidence map",
        "## Runtime-non-authoritative addenda",
    ),
    "docs/architecture/project_execution_plan.md": (
        "Registered contract-aligned implementation debt:",
        "EV-1 Governed Evidence runtime foundation                            complete / default-off",
        "OVL-1 CTX-OVL participant-private vertical slice               complete / default-off / participant-private only",
        "ASM-1 Shared Assessment runtime foundation                     complete / default-off",
        "SM-1 Subjective MEM decision/result vertical slice        complete / default-off / prepared-only",
        "ST-1 Markdown + operations commit protocol           complete / default-off / create-only / POSIX apply",
        "LC-1 lifecycle migration                        in progress / LC-1A Correct, LC-1B Forget, and LC-1C Pin/Unpin implemented / default-off",
        "LC-1D Restore                               next ordered slice / target architecture accepted / implementation not started",
        "LC-1E Consolidate                           registered / not started",
        "LC-1C Pin/Unpin implements exact current `active -> pinned` and `pinned -> active` immutable successors",
        "LC-1 remains incomplete, and Restore is the next ordered slice.",
        "LC-1D Restore is the next implementation slice; its target architecture is accepted, while runtime implementation remains not started.",
    ),
    "docs/architecture/lc1a_subjective_mem_correct.md": (
        "relaylm_authority: lc1a_subjective_mem_correct_runtime_boundary",
        "# LC-1A Subjective MEM Correct Runtime",
        "Correct | `active` | `none` | `active`",
        "LC-1 remains incomplete.",
        "Purge remains prohibited.",
    ),
    "docs/architecture/subjective-mem-forget-runtime.md": (
        "relaylm_authority: subjective_mem_forget_runtime_architecture",
        "# LC-1B Subjective MEM Forget Runtime",
        "exact `active -> hidden`",
        "content-free anti-reformation tombstone effective",
        "The Forget module is a separate operation implementation, not a second semantic",
    ),
    "docs/README.md": (
        "[Current project status](PROJECT_STATUS.md) — the single current implementation status authority.",
    ),
    "docs/architecture/README.md": (
        "ASM-1 Shared Assessment Runtime Foundation",
        "SM-1 Subjective MEM Create Runtime",
        "ST-1 Subjective MEM Commit Runtime",
        "LC-1A Subjective MEM Correct Runtime",
        "LC-1B Subjective MEM Forget Runtime",
    ),
    "docs/DOCUMENTATION_MODEL.md": (
        "`architecture_handoff`",
        "`runbook`",
        "`validation_receipt`",
    ),
}

CURRENT_DOCS = tuple(REQUIRED)

STALE = (
    "OVL-1 CTX-OVL participant-private vertical slice               registered / not started",
    "ASM-1 Shared Assessment runtime foundation                     registered / not started",
    "SM-1 Subjective MEM decision/result vertical slice        registered / not started",
    "SM-1 Subjective MEM decision/result vertical slice         next registered slice",
    "ST-1 Markdown + operations commit protocol: next registered slice; not started",
    "ST-1 Markdown + operations commit protocol           next registered slice / not started",
    "LC-1 lifecycle migration                                    next registered slice; not started",
    "LC-1 lifecycle migration                        next registered slice / not started",
    "LC-1 lifecycle migration                                    in progress; LC-1A Correct implemented",
    "LC-1B Forget                                           next ordered slice; not started",
    "LC-1 lifecycle migration                        in progress / LC-1A Correct implemented / default-off",
    "LC-1B Forget                                next ordered slice / not started",
    "[LC-1A Subjective MEM Correct Runtime](lc1a_subjective_mem_correct.md) records the default-off exact `active -> active` immutable correction successor, shared mutation fence, and forward-only recovery boundary; later LC-1 operations remain unimplemented.",
    "LC-1 lifecycle migration                                    in progress; LC-1A Correct and LC-1B Forget implemented",
    "LC-1C Pin/Unpin                                        next ordered slice; not started",
    "LC-1 remains incomplete, and Pin/Unpin is the next ordered slice.",
    "LC-1 lifecycle migration                        in progress / LC-1A Correct and LC-1B Forget implemented / default-off",
    "LC-1C Pin/Unpin                             next ordered slice / not started",
    "LC-1D Restore -> LC-1E Consolidate          registered / not started",
    "LC-1C Pin/Unpin is next, followed by LC-1D Restore",
    "PM-D3 RelayEMO/RelaySCN scene_state ownership: open",
)

HISTORY_ONLY_STATUS_ANCHORS = (
    "Post-O1F next candidates:",
    "Character Workspace reset:",
    "Completed post-MVP debt:",
    "Post-E1-R5 / Post-Wave-7 next candidates:",
    "## O1B sealed replay-lane boundary",
    "## Offline tooling addenda",
)


def read(path: str) -> str:
    location = ROOT / path
    assert location.exists(), f"missing file: {path}"
    return location.read_text(encoding="utf-8")


def require(path: str, anchors: tuple[str, ...]) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing current-boundary anchors: {missing!r}"


def forbid(path: str, anchors: tuple[str, ...]) -> None:
    body = read(path)
    stale = [anchor for anchor in anchors if anchor in body]
    assert not stale, f"{path}: stale current-boundary anchors: {stale!r}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in CURRENT_DOCS:
        forbid(path, STALE)
    forbid("docs/PROJECT_STATUS.md", HISTORY_ONLY_STATUS_ANCHORS)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
