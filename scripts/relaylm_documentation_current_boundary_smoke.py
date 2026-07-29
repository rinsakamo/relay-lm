#!/usr/bin/env python3
"""Validate the small set of documents that own RelayLM's current boundary."""
from __future__ import annotations

import sys
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
        "RT-1C shadow adapter, grounding handoff, usage ledger complete in PR #784; default-off, shadow-only, unwired",
        "RT-1D hard cutover and retirement                  next ordered target; unauthorized / not started",
        "RT-1C shadow adapter, grounding handoff, and usage ledger complete in PR #784",
        "RT-1B and RT-1C remain default-off, explicit shadow-only, and unwired from ordinary Retrieval",
        "**RT-1C Shadow adapter, grounding handoff, and usage ledger** selects exact current eligible Subjective revisions",
        "caller-attested prose with a matching caller digest cannot be admitted",
        "only then seals an admitted handoff that materializes fresh grounding dictionaries",
        "- RT-1C is default-off, explicit shadow-only, and unwired from ordinary request-path Retrieval.",
        "they still do not implement ordinary served Subjective MEM Retrieval, query matching or ranking, cache, request-path wiring, or authority cutover",
        "- Durable RT-1C usage persistence exists only for an explicitly non-shadow prepared handoff",
        "RT-1 is in progress with RT-1A, RT-1B, and RT-1C complete; RT-1D hard cutover and retirement remains unauthorized and not started.",
        "- RT-1D hard cutover and retirement;",
        "- ordinary served Subjective MEM Retrieval, query matching, ranking, cache, and request-path wiring;",
        "- Subjective MEM authority cutover and Primary MEM reader/writer retirement;",
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
        "RT-1B projection builder and rebuild complete in PR #779 / default-off / unwired",
        "RT-1C shadow adapter, grounding handoff, and usage ledger complete in PR #784 / default-off / shadow-only / unwired",
        "RT-1D hard cutover and retirement next ordered target / unauthorized / not started",
        "LC-1C Pin/Unpin implements exact current `active -> pinned` and `pinned -> active` immutable successors",
        "[LC-1D Subjective MEM Restore Runtime](subjective-mem-restore-runtime.md) implements the exact current `hidden -> active` immutable successor",
        "[LC-1E Subjective MEM Consolidate Runtime](subjective-mem-consolidate-runtime.md) implements the exact current active Primary-to-Secondary immutable successor",
        "[RT-1 Subjective MEM Retrieval Projection and Hard Cutover](subjective-mem-retrieval-projection-hard-cutover.md) defines the accepted ordered RT-1A through RT-1D boundary",
        "LC-1 is complete through Consolidate.",
        "RT-1A contract and projection foundation is complete in PR #774; RT-1B projection builder and deterministic rebuild is complete in PR #779",
        "RT-1 is in progress through RT-1C; RT-1D hard cutover and retirement is the next ordered target and remains unauthorized and not started.",
        "implementation program is complete through RT-1C",
        "RT-1C shadow adapter, grounding handoff, and usage ledger is implemented in PR #784 as three bounded owners",
        "RT-1 Retrieval projection and hard cutover in progress / RT-1A, RT-1B, and RT-1C complete",
    ),
    "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md": (
        "relaylm_authority: rt1_subjective_mem_retrieval_projection_and_hard_cutover",
        "## Authorized implementation budget",
        "RT-1A contract and projection foundation is complete. RT-1B projection builder\nand deterministic rebuild is complete. RT-1C shadow adapter, grounding handoff,\nand usage ledger is implemented in PR #784 within the budget this section\nauthorizes, and remains default-off, explicit shadow-only, and unwired from\nordinary Retrieval.",
        "RT-1A, RT-1B,\nand RT-1C are implemented within it; RT-1D remains the unimplemented target.",
        "This architecture does not claim the RT-1 series or its hard cutover is\nimplemented.",
        "It claims no ordinary served Subjective MEM Retrieval,\nno authority cutover, and no completed RT-1 series",
        "RT-1D hard cutover, Primary retirement, and authority transfer remain\nunauthorized and not started.",
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
        "### RT-1C P1 amendment",
        "At the time of that review RT-1C was authorized and\nnot yet implemented on `main`; the implementation landed later in PR #784 within\nthis amended budget.",
        "no ordinary request-path wiring\nis authorized.",
        "#### Accepted P1 characterization split",
        "the co-located selection and\ncharacterization owner crossed the roughly-700-line structural review trigger",
        "#### Canonical-page-bound private evidence",
        "consistency between prose and its own supplied digest is not canonical authority\nand must not authorize a private handoff. That design is rejected.",
        "`relaylm.subjective_mem_markdown.parse_subjective_mem_page_bytes` owner, and\n   introduces no second canonical parser",
        "the parsed page digest equals `row.canonical_page_digest`;",
        "that block's `block_digest` equals `row.block_digest`;",
        "that block's `revision_digest` equals `row.revision_digest`;",
        "No RT-1A projection-row\ndigest addition is required",
        "#### Revised three-owner structural budget",
        "relaylm/subjective_mem_retrieval_characterization.py   below roughly 320 lines",
        "The characterization owner's budget was amended from below roughly 300 lines to\nbelow roughly 320 lines by the second P1 budget-review disposition",
        "#### Second P1 characterization budget-review disposition",
        "Independent review examined the responsibility-preserving implementation of the\ncharacterization owner after genuine consolidation had already been applied.",
        "`relaylm/subjective_mem_retrieval_characterization.py`\nis 309 lines.",
        "Admission\nvalidation and comparison are one coherent temporary shadow-characterization\nresponsibility, not two separable production responsibilities",
        "- a fourth production owner is rejected, because it would split one\n  responsibility across two files and add dependency surface for no authority\n  gain;",
        "- deleting security or state checks, or line-golfing the code, to reach the\n  former roughly-300-line target is rejected",
        "The characterization structural budget is therefore amended from below roughly\n300 lines to below roughly 320 lines.",
        "This is a bounded, reviewed exception for\nthis exact owner. It is not a general structural-budget relaxation",
        "Exactly three production owners remain authorized:",
        "Strict validation and deterministic comparison remain in the same temporary\ncharacterization owner, which keeps its RT-1D removal/disable gate and its\none-way dependency direction unchanged.",
        "This disposition adjusted an implementation budget only, and RT-1C was not yet\nimplemented on `main` when it was recorded; the implementation landed later in\nPR #784 within this budget.",
        "RT-1C remains default-off, shadow-only, and unwired from\nthe ordinary request path, no ordinary request-path wiring is authorized, and\nRT-1D remains unauthorized and not started.",
        "#### Revised P1 return triggers",
        "- the characterization owner reaches 320 lines;",
        "- the characterization owner gains another responsibility, consumes private\n  content, or becomes a general validation framework;",
        "### Expected implementation paths",
        "relaylm/subjective_mem_retrieval_selection.py",
        "relaylm/subjective_mem_retrieval_characterization.py",
        "relaylm/subjective_mem_retrieval_usage_ledger.py",
        "tests/test_subjective_mem_retrieval_selection.py",
        "tests/test_subjective_mem_retrieval_characterization.py",
        "tests/test_subjective_mem_retrieval_usage_ledger.py",
        "### Not authorized for modification",
        "### Required negative cases",
        "Canonical binding:",
        "arbitrary prose plus a matching caller-supplied digest is refused, or made\n  impossible by the accepted API shape",
        "Characterization split:",
        "no reverse import into the selection owner or the durable ledger.",
        "Durable ledger:",
        "### Compatibility owner and removal gate",
        "The durable usage ledger is durable operations authority; it is not deleted\n  with the disposable projection",
        "`relaylm/subjective_mem_retrieval_characterization.py` is a temporary\n  shadow-only owner. It and its focused tests are removed or disabled by the\n  RT-1D one-authority transfer",
        "### Structural-growth review triggers",
        "more than the three new production responsibility files the accepted P1\n  amendment authorizes",
        "### RT-1C validation matrix",
        "exact canonical-page binding of every selected private item",
        "refusal of caller-attested prose and of a caller-supplied matching digest",
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
    "RT-1C shadow adapter, grounding handoff, usage ledger next ordered slice; registered / not started",
    "RT-1C shadow adapter, grounding handoff, and usage ledger next ordered slice / registered / not started",
    "RT-1C shadow adapter / grounding handoff / usage ledger and RT-1D hard cutover and retirement;",
    "RT-1C shadow adapter, grounding handoff, and usage ledger alone is the next\nauthorized implementation.",
    "RT-1C remains authorized and not implemented on\n`main`",
    "This disposition adjusts an implementation budget only. RT-1C remains authorized\nand not implemented on `main`",
    "RT-1 is in progress through RT-1B; RT-1C shadow adapter, grounding handoff, and usage ledger is the next ordered slice.",
    "implementation program is complete through RT-1B",
    "RT-1 Retrieval projection and hard cutover in progress / RT-1A and RT-1B complete",
    "RT-1D hard cutover and retirement                  registered / not started",
    "It does not claim RT-1C is\nimplemented, started, or validated",
    "This document defines the accepted target architecture for RT-1 before runtime\nimplementation.",
    "The bounded path budget for the future RT-1C implementation is:",
)

HISTORY_ONLY_STATUS_ANCHORS = (
    "Post-O1F next candidates:",
    "Character Workspace reset:",
    "Completed post-MVP debt:",
    "Post-E1-R5 / Post-Wave-7 next candidates:",
    "## O1B sealed replay-lane boundary",
    "## Offline tooling addenda",
)


RT1C = "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md"

STATUS = "docs/PROJECT_STATUS.md"
PLAN = "docs/architecture/project_execution_plan.md"

PROBES = (
    (STATUS, "RT-1C shadow adapter, grounding handoff, usage ledger complete in PR #784; default-off, shadow-only, unwired"),
    (STATUS, "- RT-1C is default-off, explicit shadow-only, and unwired from ordinary request-path Retrieval."),
    (STATUS, "- Durable RT-1C usage persistence exists only for an explicitly non-shadow prepared handoff"),
    (STATUS, "RT-1D hard cutover and retirement                  next ordered target; unauthorized / not started"),
    (STATUS, "Primary MEM remains the current ordinary memory and Retrieval authority until RT-1 hard cutover is accepted."),
    (STATUS, "- ordinary served Subjective MEM Retrieval, query matching, ranking, cache, and request-path wiring;"),
    (PLAN, "RT-1C shadow adapter, grounding handoff, and usage ledger complete in PR #784 / default-off / shadow-only / unwired"),
    (PLAN, "RT-1D hard cutover and retirement next ordered target / unauthorized / not started"),
    (PLAN, "implementation program is complete through RT-1C"),
    (RT1C, "#### Second P1 characterization budget-review disposition"),
    (RT1C, "relaylm/subjective_mem_retrieval_characterization.py   below roughly 320 lines"),
    (
        RT1C,
        "RT-1A contract and projection foundation is complete. RT-1B projection builder\n"
        "and deterministic rebuild is complete. RT-1C shadow adapter, grounding handoff,\n"
        "and usage ledger is implemented in PR #784 within the budget this section\n"
        "authorizes, and remains default-off, explicit shadow-only, and unwired from\n"
        "ordinary Retrieval.",
    ),
    (
        RT1C,
        "It claims no ordinary served Subjective MEM Retrieval,\n"
        "no authority cutover, and no completed RT-1 series",
    ),
    (RT1C, "Exactly three production owners remain authorized:"),
    (RT1C, "- the characterization owner reaches 320 lines;"),
    (
        RT1C,
        "- a fourth production owner is rejected, because it would split one\n"
        "  responsibility across two files and add dependency surface for no authority\n  gain;",
    ),
    (RT1C, "Primary MEM remains the sole served ordinary memory and Retrieval authority."),
    (
        RT1C,
        "RT-1D hard cutover, Primary retirement, and authority transfer remain\n"
        "unauthorized and not started.",
    ),
    (RT1C, "no ordinary request-path wiring\nis authorized."),
)

STALE_PROBES = (
    (STATUS, "RT-1C shadow adapter, grounding handoff, usage ledger next ordered slice; registered / not started"),
    (PLAN, "RT-1C shadow adapter, grounding handoff, and usage ledger next ordered slice / registered / not started"),
    (RT1C, "RT-1C remains authorized and not implemented on\n`main`"),
)


def read(path: str) -> str:
    location = ROOT / path
    assert location.exists(), f"missing file: {path}"
    return location.read_text(encoding="utf-8")


def require_body(path: str, anchors: tuple[str, ...], body: str) -> None:
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing current-boundary anchors: {missing!r}"


def require(path: str, anchors: tuple[str, ...]) -> None:
    require_body(path, anchors, read(path))


def self_test() -> None:
    """Prove each material boundary anchor fails closed when removed or altered.

    The probe damages an in-memory copy only; no repository content is written.
    """

    for path, anchor in PROBES:
        body = read(path)
        assert anchor in body, f"{path}: probe anchor absent: {anchor!r}"
        for damaged in (body.replace(anchor, "", 1), body.replace(anchor, "REMOVED", 1)):
            try:
                require_body(path, REQUIRED[path], damaged)
            except AssertionError:
                continue
            raise AssertionError(f"{path}: anchor is not enforced: {anchor!r}")
        print(f"PASS: removal and alteration of {anchor.splitlines()[0]!r} fail closed")
    for path, stale in STALE_PROBES:
        body = read(path)
        assert stale not in body, f"{path}: stale anchor is present: {stale!r}"
        try:
            forbid_body(path, STALE, body + "\n" + stale + "\n")
        except AssertionError:
            print(f"PASS: reintroducing {stale.splitlines()[0]!r} fails closed")
            continue
        raise AssertionError(f"{path}: stale anchor is not forbidden: {stale!r}")
    print("SELF-TEST PASS")


def forbid_body(path: str, anchors: tuple[str, ...], body: str) -> None:
    stale = [anchor for anchor in anchors if anchor in body]
    assert not stale, f"{path}: stale current-boundary anchors: {stale!r}"


def forbid(path: str, anchors: tuple[str, ...]) -> None:
    forbid_body(path, anchors, read(path))


def main(argv: list[str] | None = None) -> None:
    if argv and argv[0] == "--self-test":
        self_test()
        return
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in CURRENT_DOCS:
        forbid(path, STALE)
    forbid("docs/PROJECT_STATUS.md", HISTORY_ONLY_STATUS_ANCHORS)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main(sys.argv[1:])
