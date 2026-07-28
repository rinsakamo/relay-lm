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
        "LC-1 lifecycle migration                                    complete; LC-1A Correct, LC-1B Forget, LC-1C Pin/Unpin, LC-1D Restore, and LC-1E Consolidate implemented",
        "RT-1 Retrieval projection and hard cutover             in progress",
        "RT-1A contract and projection foundation           complete in PR #774",
        "RT-1B projection builder and rebuild               complete in PR #779",
        "RT-1C shadow adapter, grounding handoff, usage ledger next ordered slice; registered / not started",
        "RT-1 Retrieval migration: in progress; RT-1A contract and projection foundation complete in PR #774; RT-1B projection builder and deterministic rebuild complete in PR #779",
        "**LC-1D Restore** consumes one exact current hidden canonical revision",
        "**LC-1E Consolidate** consumes one exact current active Primary canonical revision",
        "**RT-1A Contract and projection foundation** defines the storage-neutral retrieval request",
        "**RT-1B Projection builder and deterministic rebuild** derives one complete, deterministic, content-free projection generation",
        "Primary MEM remains the current ordinary memory and Retrieval authority until RT-1 hard cutover is accepted.",
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
        "LC-1 lifecycle migration                        complete / LC-1A Correct, LC-1B Forget, LC-1C Pin/Unpin, LC-1D Restore, and LC-1E Consolidate implemented / default-off",
        "RT-1 Retrieval projection and hard cutover in progress / RT-1A and RT-1B complete",
        "RT-1B projection builder and rebuild complete in PR #779 / default-off / unwired",
        "RT-1C shadow adapter, grounding handoff, and usage ledger next ordered slice / registered / not started",
        "LC-1C Pin/Unpin implements exact current `active -> pinned` and `pinned -> active` immutable successors",
        "[LC-1D Subjective MEM Restore Runtime](subjective-mem-restore-runtime.md) implements the exact current `hidden -> active` immutable successor",
        "[LC-1E Subjective MEM Consolidate Runtime](subjective-mem-consolidate-runtime.md) implements the exact current active Primary-to-Secondary immutable successor",
        "[RT-1 Subjective MEM Retrieval Projection and Hard Cutover](subjective-mem-retrieval-projection-hard-cutover.md) defines the accepted ordered RT-1A through RT-1D boundary",
        "LC-1 is complete through Consolidate.",
        "RT-1A contract and projection foundation is complete in PR #774; RT-1B projection builder and deterministic rebuild is complete in PR #779",
        "RT-1 is in progress through RT-1B; RT-1C shadow adapter, grounding handoff, and usage ledger is the next ordered slice.",
        "implementation program is complete through RT-1B",
    ),
    "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md": (
        "relaylm_authority: rt1_subjective_mem_retrieval_projection_and_hard_cutover",
        "## Authorized implementation budget",
        "RT-1A contract and projection foundation is complete. RT-1B projection builder\nand deterministic rebuild is complete.",
        "RT-1C shadow adapter, grounding handoff, and usage ledger alone is the next\nauthorized implementation.",
        "RT-1D hard cutover, Primary retirement, and authority transfer remain\nunauthorized and not started.",
        "It does not claim RT-1C is\nimplemented, started, or validated",
        "Primary MEM remains the sole served ordinary memory and Retrieval authority.",
        "RT-1B remains disposable, default-off, and unwired from ordinary Retrieval.",
        "ST-1 revision-1 `create` still produces a legacy unbound current selector that\n  RT-1B rejects fail-closed",
        "### RT-1C bounded scope",
        "RT-1C runs the Subjective path in explicit shadow mode only, and RT-1D alone\n  may serve it",
        "never inject shadow evidence into the served RelayCTX or Main-LLM request",
        "keep E1-R4 as the grounding-policy owner and change no grounding behavior",
        "### RT-1C invariants",
        "durable usage finalization precedes private evidence admission",
        "failed usage finalization produces no handoff and no fallback",
        "### Expected implementation paths",
        "relaylm/subjective_mem_retrieval_selection.py",
        "relaylm/subjective_mem_retrieval_usage_ledger.py",
        "tests/test_subjective_mem_retrieval_selection.py",
        "tests/test_subjective_mem_retrieval_usage_ledger.py",
        "### Not authorized for modification",
        "### Required negative cases",
        "### Compatibility owner and removal gate",
        "The durable usage ledger is durable operations authority; it is not deleted\n  with the disposable projection",
        "### Structural-growth review triggers",
        "### RT-1C validation matrix",
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
    "LC-1 lifecycle migration                                    in progress; LC-1A Correct, LC-1B Forget, and LC-1C Pin/Unpin implemented",
    "LC-1D Restore                                          next ordered slice; not started",
    "LC-1 lifecycle migration                        in progress / LC-1A Correct, LC-1B Forget, and LC-1C Pin/Unpin implemented / default-off",
    "LC-1D Restore                               next ordered slice / target architecture accepted / implementation not started",
    "LC-1 remains incomplete, and Restore is the next ordered slice.",
    "LC-1D Restore is the next implementation slice; its target architecture is accepted, while runtime implementation remains not started.",
    "LC-1 lifecycle migration                                    in progress; LC-1A Correct, LC-1B Forget, LC-1C Pin/Unpin, and LC-1D Restore implemented",
    "LC-1 lifecycle migration                        in progress / LC-1A Correct, LC-1B Forget, LC-1C Pin/Unpin, and LC-1D Restore implemented / default-off",
    "LC-1E Consolidate                                      next ordered slice; not started",
    "LC-1E Consolidate                           next ordered slice / registered / not started",
    "LC-1 remains incomplete, and Consolidate is the next ordered slice.",
    "LC-1E Consolidate is the next implementation slice; RT-1 follows.",
    "Subjective MEM Consolidate and every lifecycle transition beyond LC-1D Restore;",
    "RT-1 Retrieval projection and hard cutover             next ordered slice; registered / not started",
    "RT-1 Retrieval projection and hard cutover next ordered slice / registered / not started",
    "LC-1 lifecycle migration is complete; RT-1 Retrieval projection and hard cutover is the next ordered slice.",
    "ordinary Subjective MEM Retrieval projection, ranking, cache, request-path wiring, and RT-1 hard cutover;",
    "RT-1B projection builder and rebuild               next ordered slice; registered / not started",
    "RT-1B projection builder and rebuild               registered / not started",
    "RT-1B projection builder and rebuild next ordered slice / registered / not started",
    "RT-1B projection builder and rebuild registered / not started",
    "RT-1 is in progress through RT-1A; RT-1B projection builder and rebuild is the next ordered slice.",
    "RT-1B projection builder and rebuild is the next ordered slice.",
    "RT-1B projection builder and rebuild, RT-1C shadow adapter / grounding handoff / usage ledger, and RT-1D hard cutover and retirement;",
    "RT-1 Retrieval migration: in progress; RT-1A contract and projection foundation complete in PR #774; no projection I/O or ordinary Retrieval wiring",
    "RT-1B projection builder and rebuild is the next ordered slice",
    "RT-1B remains not started",
    "The next authorized implementation is RT-1B only.",
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
