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
        "RT-1D structural-seam architecture amendment      P1 Return recorded; runtime not started",
        "RT-1D-S1 reader seams                          complete in PR #789; behavior-preserving",
        "S1 mandatory P8 current-authority sync      PR #790; exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b",
        "RT-1D-S2 worker seams                    complete in PR #791; exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9",
        "S2 mandatory P8 current-authority sync      PR #792; exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba",
        "RT-1D-S3A Correct core seams       complete in PR #794; exact resulting main 2d05a41235e396ac82d536437ed8e5568f617253",
        "S3A mandatory P8 current-authority sync PR #795 result bc27c25d0b745fc2d9927e9e21179b14cd337141",
        "RT-1D-S3B Forget core seams complete in PR #796; exact resulting main b75df848bf3982e00f67969c016ba1f28dd93427",
        "**RT-1D-S1 Reader seams** completed in PR #789",
        "**RT-1D-S2 Worker seams** completed in PR #791",
        "b272edb78602032009d4882a6244883cce610b86",
        "3e20274f18306f7db2410fd5239051411b9c052b",
        "31b700a2db0af7819f761d51bd946ff6798eb4c9",
        "RT-1D-S3C Soul Lab mutation route seams completed in PR #798",
        "RT-1B remains default-off and unwired from ordinary Retrieval",
        "RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval",
        "**RT-1C Shadow adapter, grounding handoff, and usage ledger** selects exact current eligible Subjective revisions",
        "caller-attested prose with a matching caller digest cannot be admitted",
        "only then seals an admitted handoff that materializes fresh grounding dictionaries",
        "- RT-1C is default-off, explicit shadow-only, and unwired from ordinary request-path Retrieval.",
        "they still do not implement ordinary served Subjective MEM Retrieval, query matching or ranking, cache, request-path wiring, or authority cutover",
        "- Durable RT-1C usage persistence exists only for an explicitly non-shadow prepared handoff",
        "RT-1 is in progress with RT-1A, RT-1B, RT-1C, and all behavior-preserving RT-1D structural seams through S3C complete.",
        "The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`",
        "- RT-1D hard cutover and retirement;",
        "- ordinary served Subjective MEM Retrieval, query matching, ranking, cache, and request-path wiring;",
        "- Subjective MEM authority cutover and Primary MEM reader/writer retirement;",
        "**LC-1D Restore** consumes one exact current hidden canonical revision",
        "**LC-1E Consolidate** consumes one exact current active Primary canonical revision",
        "**RT-1A Contract and projection foundation** defines the storage-neutral retrieval request",
        "**RT-1B Projection builder and deterministic rebuild** derives one complete, deterministic, content-free projection generation",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority until a future RT-1D implementation is validated, merged, and its cutover receipt is finalized.",
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
        "RT-1D-S3C Soul Lab mutation route seams completed in PR #798",
        "RT-1D structural P1 Return / runtime not started",
        "RT-1D-S1 reader seams complete in PR #789",
        "S1 mandatory P8 current-authority sync in PR #790 -> exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b",
        "RT-1D-S2 worker seams complete in PR #791 -> exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9",
        "S2 mandatory P8 current-authority sync in PR #792 -> exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba",
        "S3A mandatory P8 PR #795 result `bc27c25d0b745fc2d9927e9e21179b14cd337141`",
        "LC-1C Pin/Unpin implements exact current `active -> pinned` and `pinned -> active` immutable successors",
        "[LC-1D Subjective MEM Restore Runtime](subjective-mem-restore-runtime.md) implements the exact current `hidden -> active` immutable successor",
        "[LC-1E Subjective MEM Consolidate Runtime](subjective-mem-consolidate-runtime.md) implements the exact current active Primary-to-Secondary immutable successor",
        "[RT-1 Subjective MEM Retrieval Projection and Hard Cutover](subjective-mem-retrieval-projection-hard-cutover.md) defines the accepted ordered RT-1A through RT-1D boundary",
        "LC-1 is complete through Consolidate.",
        "RT-1A contract and projection foundation is complete in PR #774; RT-1B projection builder and deterministic rebuild is complete in PR #779",
        "implementation program is complete through RT-1D-S2",
        "RT-1D-S1 reader seams completed in PR #789",
        "RT-1D-S2 worker seams completed in PR #791",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority.",
        "RT-1D-S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`",
        "RT-1C shadow adapter, grounding handoff, and usage ledger is implemented in PR #784 as three bounded owners",
        "RT-1 Retrieval projection and hard cutover in progress / RT-1A, RT-1B, and RT-1C complete",
        "RT-1B remains default-off and unwired from ordinary Retrieval",
        "RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval",
    ),
    "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md": (
        "relaylm_authority: rt1_subjective_mem_retrieval_projection_and_hard_cutover",
        "## Authorized implementation budget",
        "RT-1A contract and projection foundation is complete. RT-1B projection builder\nand deterministic rebuild is complete. RT-1C shadow adapter, grounding handoff,\nand usage ledger is implemented in PR #784 within the budget this section\nauthorizes, and remains default-off, explicit shadow-only, and unwired from\nordinary Retrieval.",
        "RT-1A, RT-1B,\nand RT-1C are implemented within it; RT-1D remains the unimplemented target.",
        "This architecture does not claim the RT-1 series or its hard cutover is\nimplemented.",
        "It claims no ordinary served Subjective MEM Retrieval,\nno authority cutover, and no completed RT-1 series",
        "RT-1D hard cutover, Primary retirement, and authority transfer are\narchitecture-authorized and are not started.",
        "Primary MEM remains the sole served ordinary memory and Retrieval authority.",
        "RT-1B remains disposable, default-off, and unwired from ordinary Retrieval.",
        "ST-1 revision-1 `create` still produces a legacy unbound current selector that\n  RT-1B rejects fail-closed",
        "## RT-1D architecture authorization and implementation budget",
        "### Authorization boundary and owners",
        "#### Dedicated RT-1D cutover domain owner",
        "#### EvidenceRecordStore is a reused generic dependency",
        "### Prerequisites and exact execution order",
        "### Required semantic invariants",
        "### Durable cutover state and forward recovery",
        "### Characterization and deployment gate",
        "### P1 authority-carriage return and amended API boundary",
        "#### Immutable runtime-private cutover binding",
        "`SubjectiveMemRetrievalCutoverBinding`",
        "the explicit `EvidenceRecordStore` root dependency and cutover evidence space",
        "the explicit Subjective projection location and canonical workspace/page",
        "exact build identity, configuration identity, and accepted",
        "deployment/readiness authority",
        "expected intent, reader-fence, writer-fence, and finalized-receipt identities",
        "#### Reader and writer decisions",
        "before the durable reader fence: `primary_only`",
        "after the reader fence and before the exact finalized receipt: `neither`",
        "after the exact finalized receipt: `subjective_only`",
        "The existing\npipeline checkpoint seam is reused before source consumption, M3e page write,\nand M3g reconciliation",
        "#### Explicit SLP and Correct/Forget carriage",
        "The immutable binding is carried explicitly through the one-queued-job runner\nrequest, worker request, worker execution, pipeline invocation",
        "a mutation token issued before `writer_fenced` cannot authorize an\napply or recovery write after `writer_fenced`",
        "#### Canonical Subjective source acquisition and configuration",
        "Configuration may add explicit locator/binding fields",
        "No configuration value, enable boolean, or load success\nauthorizes deployment or serving",
        "The rejected alternatives are a marker in the Primary root",
        "a process-local flag",
        "implicit root derivation",
        "Runtime implementation remains not started.",
        "### Future implementation path budget",
        "### Compatibility consumers and removal gates",
        "### Structural P1 Return and ordered prerequisite seams",
        "RT-1D-S1 reader seams",
        "RT-1D-S2 worker seams",
        "RT-1D-S3 mutation seams",
        "mandatory same-lane P8",
        "relaylm/managed_chat_pipeline_runtime.py",
        "relaylm/_relaymem_slp_primary_worker_pipeline.py",
        "_relaymem_primary_correction_preflight.py",
        "S1-S3 preserve Primary-only behavior",
        "### Required RT-1D negative matrix",
        "### RT-1D validation matrix",
        "### RT-1D explicit non-goals",
        "`relaylm/subjective_mem_retrieval_cutover.py` is the one dedicated RT-1D cutover domain owner",
        "One dedicated domain owner, `relaylm/subjective_mem_retrieval_cutover.py`, owns the whole semantic RT-1D authority transfer.",
        "`relaylm/evidence_store.py` is generic persistence infrastructure, not the RT-1D semantic authority.",
        "ordinary route / cutover orchestration\n  -> subjective_mem_retrieval_cutover domain owner\n       -> EvidenceRecordStore generic persistence",
        "The generic store must never import the cutover owner.",
        "The cutover owner reuses `EvidenceRecordStore` only for:",
        "Therefore RT-1D introduces no second lock, no second durable root, no second transaction journal, and no second generic recovery mechanism, and adds no RT-1D policy or state-machine logic to `relaylm/evidence_store.py`.",
        "Modifying `relaylm/evidence_store.py` is allowed only through a documented P1 return that proves, from exact evidence, a missing generic persistence capability that is not RT-1D-specific. This authorization does not pre-authorize such a change.",
        "`relaylm/evidence_store.py` is an imported and reused generic infrastructure\ndependency, not an expected modified production path and not the RT-1D semantic\nowner.",
        "primary_live\n  -> intent_recorded\n  -> reader_fenced\n  -> writer_fenced\n  -> subjective_prepared\n  -> receipt_finalized\n  -> validated\n  -> retired",
        "`subjective_prepared` constructs or validates the exact Subjective route inputs but releases no ordinary evidence and serves no ordinary request.",
        "Ordinary Subjective serving is authorized only by the exact finalized receipt.",
        "After `receipt_finalized`, only Subjective may serve.",
        "A crash in `subjective_prepared` resumes forward finalization with both ordinary authorities non-serving.",
        "(5) durable cutover-receipt finalization, which alone authorizes ordinary Subjective serving;",
        "tests/test_subjective_mem_retrieval_cutover.py",
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
        "RT-1C remains default-off, shadow-only, and unwired from\nthe ordinary request path, no ordinary request-path wiring is authorized, and\nRT-1D is architecture-authorized and not started.",
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


S3_AMENDMENT_ANCHORS = {
    "docs/PROJECT_STATUS.md": (
        "PR #793",
        "1100 lines for `relaylm/relaymem_primary_correction.py`",
        "771-line Correct apply module",
        "**RT-1D-S3A Correct core seams**",
        "**RT-1D-S3B Forget core seams**",
        "**RT-1D-S3C Soul Lab mutation route seams**",
        "`relaylm/_relaymem_primary_correction_publication.py`",
        "`relaylm/_relaymem_primary_forget_apply.py`",
        "`relaylm/soul_lab_memory_forget_runtime.py`",
        "This architecture-only amendment itself requires no separate P8",
        "RT-1D-S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority",
    ),
    "docs/architecture/project_execution_plan.md": (
        "PR #793",
        "### RT-1D-S3 ordered structural budgets",
        "**RT-1D-S3A Correct core seams**",
        "**RT-1D-S3B Forget core seams**",
        "**RT-1D-S3C Soul Lab mutation route seams**",
        "`tests/test_rt1d_s3a_correct_seams.py`",
        "`tests/test_rt1d_s3b_forget_seams.py`",
        "no optional focused test",
        "S3C PR #798 result `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`",
        "No generic mutation framework, second authority",
    ),
    "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md": (
        "PR #793",
        "#### RT-1D-S3 monolithic P1 Return and ordered slices",
        "##### RT-1D-S3A Correct core seams",
        "##### RT-1D-S3B Forget core seams",
        "##### RT-1D-S3C Soul Lab mutation route seams",
        "relaylm/_relaymem_primary_correction_publication.py",
        "relaylm/_relaymem_primary_forget_apply.py",
        "relaylm/soul_lab_memory_forget_runtime.py",
        "tests/test_rt1d_s3a_correct_seams.py",
        "tests/test_rt1d_s3b_forget_seams.py",
        "no optional focused test",
        "S2 P8 PR #792 result 7e4fb4383dc6c1229d488ac200132b66f6b65bba",
        "The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`.",
        "Only the exact resulting main after S3C P8 verification may bootstrap",
        "A fixed budget may not be silently expanded.",
    ),
}
for _path, _anchors in S3_AMENDMENT_ANCHORS.items():
    REQUIRED[_path] += _anchors

S3A_COMPLETION_ANCHORS = {
    "docs/PROJECT_STATUS.md": (
        "RT-1D-S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`",
        "**RT-1D-S3A Correct core seams** completed in PR #794",
        "exact resulting main `2d05a41235e396ac82d536437ed8e5568f617253`",
        "`relaylm/relaymem_primary_correction.py` (122 lines)",
        "`relaylm/_relaymem_primary_correction_preflight.py` (269)",
        "`relaylm/_relaymem_primary_correction_apply.py` (444)",
        "`relaylm/_relaymem_primary_correction_publication.py` (104)",
        "`relaylm/_relaymem_primary_correction_recovery.py` (60)",
        "`relaylm/_relaymem_primary_correction_history.py` (137)",
        "largest touched orchestration span of 73 lines",
        "introduced no production monkeypatch",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority",
    ),
    "docs/architecture/project_execution_plan.md": (
        "PR #793 merged the monolithic S3 P1 Return architecture amendment with exact result `5011eaaddd895b434f3d870dcf2206527725629c`",
        "RT-1D-S3A Correct core seams completed in PR #794 with exact resulting main `2d05a41235e396ac82d536437ed8e5568f617253`",
        "RT-1D-S3C completed in PR #798 with exact resulting main `56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`",
        "`relaylm/relaymem_primary_forget_recovery.py` and `relaylm/_relaymem_primary_forget_apply.py`",
        "only `tests/test_rt1d_s3b_forget_seams.py` is optional",
        "`relaylm/relaymem_primary_forget.py` and `relaylm/relaymem_primary_forget_public_apply.py` remain byte-identical",
        "Any additional S3B path requires a fresh P1 before writing.",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority.",
    ),
    "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md": (
        "exact result `5011eaaddd895b434f3d870dcf2206527725629c`",
        "S3A completed in PR #794 with exact resulting main",
        "`2d05a41235e396ac82d536437ed8e5568f617253`",
        "`relaylm/relaymem_primary_correction.py` (122 lines)",
        "`relaylm/_relaymem_primary_correction_preflight.py` (269)",
        "`relaylm/_relaymem_primary_correction_apply.py` (444)",
        "`relaylm/_relaymem_primary_correction_publication.py` (104)",
        "`relaylm/_relaymem_primary_correction_recovery.py` (60)",
        "`relaylm/_relaymem_primary_correction_history.py` (137)",
        "largest touched\norchestration span is 73 lines",
        "No production monkeypatch",
        "The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`.",
        "At that inspection, no runtime implementation had started",
        "Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets",
        "Primary MEM remains the sole served ordinary memory and Retrieval authority.",
    ),
}
for _path, _anchors in S3A_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors

S3B_COMPLETION_ANCHORS = {
    "docs/PROJECT_STATUS.md": (
        "**RT-1D-S3B Forget core seams** completed in PR #796",
        "`126e88dc18c8a61e439a41c8da7e6e0eaa2ccfc2`",
        "`b75df848bf3982e00f67969c016ba1f28dd93427`",
        "`bc27c25d0b745fc2d9927e9e21179b14cd337141`",
        "`relaylm/_relaymem_primary_forget_apply.py` (+400/-0)",
        "`relaylm/relaymem_primary_forget_recovery.py` (+127/-274)",
        "recovery facade is now 632 physical lines",
        "internal apply owner is 400 physical lines",
        "internal apply entry point 65",
        "public apply signature remains unchanged",
        "canonical public compatibility, recovery, finalization, result-class, schema, and export owner",
        "frozen per-call dependency bundle from current module globals",
        "No replacement public result dataclasses were introduced",
        "No production monkeypatch",
        "4fe026b1c87639c8cb248acce41ac4b2d875e1f05eb14d28fc79059dc0600f92",
        "8a0af188df9ee1c037547de60f92fc8cf39e9d09a34f361292ea82133694021e",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority",
        "The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`",
        "Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets",
        "Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets",
    ),
    "docs/architecture/project_execution_plan.md": (
        "RT-1D-S3B Forget core seams completed in PR #796 with exact resulting main `b75df848bf3982e00f67969c016ba1f28dd93427`",
        "The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`",
        "Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets",
        "No Lane C transaction overlaps",
    ),
    "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md": (
        "S3B implementation PR #796 result b75df848bf3982e00f67969c016ba1f28dd93427",
        "mandatory S3B P8 current-authority synchronization PR #797 result e221f17906682bdb077d8016e09843d176af5df4",
        "S3C implementation PR #798 result 56fa66fdba475a3d6e1a4bc4cbc3480ba238720e",
        "mandatory S3C P8 current-authority synchronization PR #799 result d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f",
        "independently verify S3C P8 PR #799 exact resulting main",
        "R1 PR #801 result 90a3c4f1cedf54e007cf5c0a6a9abc69a30d2acd -> mandatory R1 P8 PR #802 current -> R2 next, not started",
    ),
}
for _path, _anchors in S3B_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors

S3C_COMPLETION_ANCHORS = {
    path: (
        "**RT-1D-S3C Soul Lab mutation route seams** completed in PR #798",
        "`e221f17906682bdb077d8016e09843d176af5df4`",
        "`97e161beab5b037ab1b8505641b9c6091b7b4ca0`",
        "`56fa66fdba475a3d6e1a4bc4cbc3480ba238720e`",
        "`relaylm/soul_lab_memory_correction_routes.py` (+42/-99; 104 lines)",
        "`relaylm/soul_lab_memory_correction_runtime.py` (+136/-0; 136 lines)",
        "`relaylm/soul_lab_memory_forget_routes.py` (+43/-168; 106 lines)",
        "`relaylm/soul_lab_memory_forget_runtime.py` (+209/-0; 209 lines)",
        "total +430/-267, with no optional focused test",
        "maximum orchestration is 52 lines",
        "soul_lab_memory_correction_routes -> soul_lab_memory_correction_runtime",
        "soul_lab_memory_forget_routes -> soul_lab_memory_forget_runtime",
        "877457129d617ed0a90df879e1a41d9807503bb2612b68095812dfc87dea58e4",
        "44547117872e449294095f240d79f16b8bbd9c7f6c89737fa9c865e461c65dac",
        "The mandatory S3C P8 current-authority synchronization PR #799 merged as exact current main `d9caff1750e93f9d4ce2f0852e070bc96cb1bf2f`",
        "Fresh exact-current RT-1D P0/P1 inspection now authorizes the ordered runtime implementation budgets",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority",
        "Subjective ordinary retrieval remains disabled and unwired",
        "no cutover, authority switch, serving, fallback, writer fence, or retirement change occurred",
    )
    for path in (
        "docs/PROJECT_STATUS.md",
        "docs/architecture/project_execution_plan.md",
        "docs/architecture/subjective-mem-retrieval-projection-hard-cutover.md",
    )
}
for _path, _anchors in S3C_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors

CURRENT_DOCS = tuple(REQUIRED)

STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "RT-1D-R1 is next but non-executable until PR #800 merges",
    "fresh RT-1D runtime P0/P1 architecture authorization PR #800 current",
    "Fresh RT-1D runtime P0/P1 architecture authorization PR #800 current",
    "independently verify PR #800 exact resulting main after merge",
    "RT-1D-R1 next, not started",
    "RT-1D-R1 is not\nstarted and is non-executable until PR #800 merges",
    "No runtime implementation has started.",
    "PR #793 must merge before S3A",
    "PR #793 must merge and its exact resulting main must be independently verified before S3A",
    "S3A has not started",
    "S3A, S3B, S3C, and RT-1D runtime have not started.",
    "S3A implementation next",
    "S3B is executable before S3A P8 merges and resulting-main verification",
    "S3B is next but has not started",
    "S3B implementation pending",
    "S3C is executable before S3B P8 resulting-main verification",
    "S3C next, not started -> mandatory P8 -> independently verify exact resulting main",
    "fresh RT-1D runtime is current",
    "fresh RT-1D runtime has started",
    "Primary MEM is no longer the sole ordinary served memory and Retrieval authority",
    "RT-1D hard cutover, Primary retirement, and authority transfer remain\nunauthorized and not started.",
    "the durable cutover intent/fences/receipt belong to `relaylm/evidence_store.py`",
    "the Evidence store owns durable receipt/fence state",
    "relaylm/relayctx_repack.py\nrelaylm/evidence_store.py",
    "subjective_enabled -> receipt_finalized",
    "(4) Subjective ordinary-reader enablement;",
    "A crash after enablement but before receipt finalization keeps Primary fenced and Subjective non-serving until forward finalization proves the exact state.",
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
    "RT-1D hard cutover and retirement registered / not started",
    "RT-1B and RT-1C remain default-off, explicit shadow-only, and unwired from ordinary Retrieval",
    "It does not claim RT-1C is\nimplemented, started, or validated",
    "This document defines the accepted target architecture for RT-1 before runtime\nimplementation.",
    "The bounded path budget for the future RT-1C implementation is:",
    "the old four writer-entry files alone cover all writers",
    "current config already carries complete authority",
    "public page-writer fencing alone is sufficient",
    "process-local cutover authority is allowed",
    "a Primary-root cutover marker is allowed",
    "configuration or an enable flag selects served authority",
    "RT-1D-S1 reader seams is the next executable Lane C prerequisite",
    "RT-1D-S1 reader seams remains unimplemented",
    "The ordered Lane C sequence begins with RT-1D-S1 reader seams after PR #789.",
    "mandatory P8 and resulting-main verification pending",
    "RT-1D-S1 reader seams complete in PR #789 -> mandatory P8 pending -> verify resulting main",
    "The mandatory S1 P8 authority sync and resulting-main verification must complete",
    "RT-1D-S2 worker seams is the next executable Lane C prerequisite",
    "RT-1D-S2 worker seams next after exact PR #790 resulting-main verification",
    "implementation program is complete through RT-1D-S1",
    "RT-1D-S2 worker seams remains unimplemented",
    "The mandatory S2 P8 authority sync and resulting-main verification must complete",
    "the current S2 mandatory P8 current-authority sync PR",
    "The current S2 mandatory P8 current-authority sync PR",
    "Subjective serves before the finalized receipt",
    "Primary serves after the finalized receipt",
)


STALE += (
    "the current RT-1D-S3 P1 architecture amendment PR",
    "The current RT-1D-S3 P1 architecture amendment PR",
    "RT-1D-S3 mutation seams next -> mandatory P8 -> verify resulting main",
    "RT-1D-S3 mutation seams             next after exact S2 P8 resulting-main verification",
    "RT-1D-S3 has started",
    "RT-1D-S3 is complete",
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

RT1_STRUCTURAL_ANCHORS = (
    "These are review triggers, not permanent exemptions.",
    "Responsibility-driven extraction may move existing behavior only when one exact\n"
    "current responsibility, accepted caller, explicit input and output, and public\n"
    "facade are identified.",
    "splitting merely to lower line counts would\nnot transfer a coherent responsibility",
    "Moving one giant\nblock into another file over roughly 700 lines is not an accepted seam.",
    "RT-1D-S1 reader seams\n"
    "  -> mandatory same-lane P8 -> verify resulting main\n"
    "  -> RT-1D-S2 worker seams\n"
    "     -> mandatory same-lane P8 -> verify resulting main\n"
    "     -> RT-1D-S3 mutation seams\n"
    "        -> mandatory same-lane P8 -> verify resulting main\n"
    "        -> fresh RT-1D runtime implementation\n"
    "           -> mandatory same-lane P8 after merge",
    "relaylm/managed_chat_pipeline_runtime.py",
    "relaylm/relaymem_retrieval_dry_run.py",
    "_relaymem_retrieval_candidates.py",
    "_relaymem_retrieval_snippet.py",
    "relaylm/relaymem_primary_recall_selection.py",
    "relaylm/relaymem_primary_recall_store.py",
    "relaylm/_relaymem_slp_primary_worker_pipeline.py",
    "relaylm/_relaymem_slp_one_queued_job_runner_execute.py",
    "_relaymem_primary_correction_preflight.py",
    "_relaymem_primary_correction_apply.py",
    "_relaymem_primary_correction_history.py",
    "_relaymem_primary_forget_apply.py",
    "soul_lab_memory_correction_runtime.py",
    "soul_lab_memory_forget_runtime.py",
    "Every implementation merge requires its mandatory same-lane P8\n"
    "and exact resulting-main verification before the next slice.",
    "S1-S3 preserve Primary-only behavior and must not add the cutover\n"
    "binding, cutover records, configuration fields, reader/writer decisions,\n"
    "Primary fences, Subjective serving, fallback changes, authority selection,\n"
    "retirement, `EvidenceRecordStore` changes, or another persistence/recovery\n"
    "mechanism.",
    "its complete\nmain-relative path budget was fixed before writing",
    "every touched public API,\nimport, and schema remains exact",
    "durable filesystem bytes and fault,\ncrash, and recovery outcomes remain unchanged",
    "no import cycle, import-time side effect, duplicated semantics,\n"
    "generic framework, new authority, new configuration authority, or new\n"
    "persistence or recovery owner",
    "Every touched orchestration function is at or below the approximate 80-line\n"
    "review target.",
    "Any exception to that target requires an exact reviewed P1\n"
    "Return before any branch write, never a post-hoc exemption.",
    "Every new\nproduction module remains below the approximate 700-line review trigger.",
    "Every\ntouched pre-existing oversized facade is materially reduced and brought toward\n"
    "or below approximately 700 lines where the accepted responsibility-driven\n"
    "extraction can do so",
    "no destination module becomes another oversized dumping\nground.",
    "A slice unable to meet these gates returns to P1: it does not waive,\n"
    "line-golf, bypass, or reinterpret the thresholds.",
)

RT1_STRUCTURAL_STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "RT-1D runtime is the next implementation immediately after PR #788.",
    "S1-S3 and RT-1D runtime may be implemented in one combined PR.",
    "Existing oversized files are exempt from the structural thresholds.",
    "Wrapper-only extraction is sufficient for RT-1D authority carriage.",
    "Splitting code only to reduce line counts is authorized.",
    "A replacement module may exceed the approximate 700-line trigger.",
    "S1-S3 may add the RT-1D binding, configuration fields, or authority decisions.",
    "RT-1D-S1, RT-1D-S2, and RT-1D-S3 may run concurrently.",
    "The same-lane P8 authority sync may be skipped after a structural slice.",
    "Subjective ordinary serving is active during S1-S3.",
    "Primary RT-1D writer fencing is active during S1-S3.",
)

REQUIRED[RT1C] += RT1_STRUCTURAL_ANCHORS
STALE += RT1_STRUCTURAL_STALE

PROBES = (
    (STATUS, "RT-1C shadow adapter, grounding handoff, usage ledger complete in PR #784; default-off, shadow-only, unwired"),
    (STATUS, "- RT-1C is default-off, explicit shadow-only, and unwired from ordinary request-path Retrieval."),
    (STATUS, "- Durable RT-1C usage persistence exists only for an explicitly non-shadow prepared handoff"),
    (STATUS, "RT-1D structural-seam architecture amendment      P1 Return recorded; runtime not started"),
    (STATUS, "RT-1D-S1 reader seams                          complete in PR #789; behavior-preserving"),
    (STATUS, "S1 mandatory P8 current-authority sync      PR #790; exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b"),
    (STATUS, "RT-1D-S2 worker seams                    complete in PR #791; exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9"),
    (STATUS, "S2 mandatory P8 current-authority sync      PR #792; exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba"),
    (STATUS, "RT-1D-S3A Correct core seams       complete in PR #794; exact resulting main 2d05a41235e396ac82d536437ed8e5568f617253"),
    (STATUS, "Primary MEM remains the sole ordinary served memory and Retrieval authority until a future RT-1D implementation is validated, merged, and its cutover receipt is finalized."),
    (STATUS, "- ordinary served Subjective MEM Retrieval, query matching, ranking, cache, and request-path wiring;"),
    (PLAN, "RT-1D-S3C Soul Lab mutation route seams completed in PR #798"),
    (PLAN, "RT-1D structural P1 Return / runtime not started"),
    (PLAN, "S1 mandatory P8 current-authority sync in PR #790 -> exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b"),
    (PLAN, "RT-1D-S2 worker seams complete in PR #791 -> exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9"),
    (PLAN, "S2 mandatory P8 current-authority sync in PR #792 -> exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba"),
    (PLAN, "S3A mandatory P8 PR #795 result `bc27c25d0b745fc2d9927e9e21179b14cd337141`"),
    (STATUS, "RT-1B remains default-off and unwired from ordinary Retrieval"),
    (STATUS, "RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval"),
    (PLAN, "RT-1B remains default-off and unwired from ordinary Retrieval"),
    (PLAN, "RT-1C remains default-off, explicit shadow-only, and unwired from ordinary Retrieval"),
    (PLAN, "implementation program is complete through RT-1D-S2"),
    (RT1C, "#### Second P1 characterization budget-review disposition"),
    (RT1C, "`relaylm/subjective_mem_retrieval_characterization.py`\nis 309 lines."),
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
    (
        RT1C,
        "This is a bounded, reviewed exception for\nthis exact owner. It is not a general "
        "structural-budget relaxation",
    ),
    (
        RT1C,
        "Admission\nvalidation and comparison are one coherent temporary shadow-characterization"
        "\nresponsibility, not two separable production responsibilities",
    ),
    (RT1C, "Primary MEM remains the sole served ordinary memory and Retrieval authority."),
    (
        RT1C,
        "RT-1D hard cutover, Primary retirement, and authority transfer are\n"
        "architecture-authorized and are not started.",
    ),
    (RT1C, "no ordinary request-path wiring\nis authorized."),
    (RT1C, "#### Dedicated RT-1D cutover domain owner"),
    (RT1C, "#### EvidenceRecordStore is a reused generic dependency"),
    (
        RT1C,
        "One dedicated domain owner, `relaylm/subjective_mem_retrieval_cutover.py`, owns "
        "the whole semantic RT-1D authority transfer.",
    ),
    (
        RT1C,
        "`relaylm/subjective_mem_retrieval_cutover.py` is the one dedicated RT-1D cutover "
        "domain owner",
    ),
    (
        RT1C,
        "`relaylm/evidence_store.py` is generic persistence infrastructure, not the RT-1D "
        "semantic authority.",
    ),
    (
        RT1C,
        "ordinary route / cutover orchestration\n"
        "  -> subjective_mem_retrieval_cutover domain owner\n"
        "       -> EvidenceRecordStore generic persistence",
    ),
    (RT1C, "The generic store must never import the cutover owner."),
    (RT1C, "The cutover owner reuses `EvidenceRecordStore` only for:"),
    (
        RT1C,
        "Therefore RT-1D introduces no second lock, no second durable root, no second "
        "transaction journal, and no second generic recovery mechanism, and adds no RT-1D "
        "policy or state-machine logic to `relaylm/evidence_store.py`.",
    ),
    (
        RT1C,
        "Modifying `relaylm/evidence_store.py` is allowed only through a documented P1 "
        "return that proves, from exact evidence, a missing generic persistence capability "
        "that is not RT-1D-specific. This authorization does not pre-authorize such a change.",
    ),
    (
        RT1C,
        "primary_live\n  -> intent_recorded\n  -> reader_fenced\n  -> writer_fenced\n"
        "  -> subjective_prepared\n  -> receipt_finalized\n  -> validated\n  -> retired",
    ),
    (
        RT1C,
        "`subjective_prepared` constructs or validates the exact Subjective route inputs "
        "but releases no ordinary evidence and serves no ordinary request.",
    ),
    (RT1C, "Ordinary Subjective serving is authorized only by the exact finalized receipt."),
    (RT1C, "After `receipt_finalized`, only Subjective may serve."),
    (
        RT1C,
        "A crash in `subjective_prepared` resumes forward finalization with both ordinary "
        "authorities non-serving.",
    ),
    (
        RT1C,
        "(5) durable cutover-receipt finalization, which alone authorizes ordinary "
        "Subjective serving;",
    ),
    (RT1C, "tests/test_subjective_mem_retrieval_cutover.py"),
    (RT1C, "`SubjectiveMemRetrievalCutoverBinding`"),
    (RT1C, "the explicit `EvidenceRecordStore` root dependency and cutover evidence space"),
    (RT1C, "expected intent, reader-fence, writer-fence, and finalized-receipt identities"),
    (RT1C, "before the durable reader fence: `primary_only`"),
    (RT1C, "after the reader fence and before the exact finalized receipt: `neither`"),
    (RT1C, "after the exact finalized receipt: `subjective_only`"),
    (RT1C, "The existing\npipeline checkpoint seam is reused before source consumption, M3e page write,\nand M3g reconciliation"),
    (RT1C, "The immutable binding is carried explicitly through the one-queued-job runner\nrequest, worker request, worker execution, pipeline invocation"),
    (RT1C, "a mutation token issued before `writer_fenced` cannot authorize an\napply or recovery write after `writer_fenced`"),
    (RT1C, "Configuration may add explicit locator/binding fields"),
    (RT1C, "No configuration value, enable boolean, or load success\nauthorizes deployment or serving"),
    (RT1C, "Runtime implementation remains not started."),
) + tuple((RT1C, anchor) for anchor in RT1_STRUCTURAL_ANCHORS)

PROBES += tuple((path, anchor) for path, anchors in S3_AMENDMENT_ANCHORS.items() for anchor in anchors)
PROBES += tuple((path, anchor) for path, anchors in S3A_COMPLETION_ANCHORS.items() for anchor in anchors)
PROBES += tuple((path, anchor) for path, anchors in S3B_COMPLETION_ANCHORS.items() for anchor in anchors)
PROBES += tuple((path, anchor) for path, anchors in S3C_COMPLETION_ANCHORS.items() for anchor in anchors)

R2_LIVE_ROOT_ANCHORS = {
    STATUS: (
        "## RT-1D-R2 staged writer-fence and smoke-carriage budget amendment",
        "PR #803 completed with exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` and required no P8",
        "renewed R2 attempt also returned at P1 without mutation",
        "PR #804",
        "amendment PR head cannot bootstrap R2",
        "`relaylm/managed_chat_response.py`",
        "`bcf8d6f42b21c23ea96e081d69f3c039c5da4f5c`, 543 physical lines; final maximum 559 and net growth +16",
        "same decision to both finalization constructions",
        "`relaylm/relaymem_primary_pin_apply.py`",
        "`9dc4c8bd62623c0037821f19c8dab2d166dcbb01`, 617 physical lines; final maximum 697 and net growth +80",
        "prevent replay `_publish_state`, `_publish_receipt`, new-operation `_publish_state`",
        "exact twenty-three-path R2 production budget",
        "No twenty-fourth production path is authorized",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority",
        "changes no production, runtime, config, durable state, serving, fallback, or retirement behavior",
    ),
    PLAN: (
        "## Historical RT-1D-R2B P8 current-authority synchronization gate",
        "PR #803 exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` -> renewed R2 P1 Return without mutation",
        "PR #804",
        "RT-1D-R2B and mandatory P8 PR #812 are complete; RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started",
        "RT-1D-R2A implementation PR #809 exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430` -> completed mandatory R2A P8",
        "only the independently verified exact resulting main from the immediately preceding gate may bootstrap the next, never a PR head and never an audit branch",
        "managed_chat_runtime.py`-only carriage is insufficient",
        "route-only Pin fence is insufficient",
        "exact twenty-three-path ordered list",
        "no twenty-fourth production path",
        "maximum 559 (+16)",
        "maximum 697 (+80)",
        "requires no further P8 and changes no production/runtime behavior",
    ),
    RT1C: (
        "Production budget (exact twenty-three paths, authoritative order, split across the four ordered stages RT-1D-R2A, RT-1D-R2B, RT-1D-R2C, and RT-1D-R2D)",
        "relaylm/managed_chat_response.py",
        "relaylm/relaymem_primary_pin_apply.py",
        "### RT-1D-R2 staged writer-fence and smoke-carriage amendment gate",
        "PR #803 completed with exact result `eee986422b45c50e0d9ad0528e863457be4db9a1` and required no P8",
        "PR #804",
        "it required no P8",
        "same decision to both calls",
        "Managed-runtime-only carriage is insufficient",
        "Route-only fencing is insufficient",
        "blob `bcf8d6f42b21c23ea96e081d69f3c039c5da4f5c`, 543 physical lines; final maximum 559, net +16",
        "blob `9dc4c8bd62623c0037821f19c8dab2d166dcbb01`, 617 physical lines; final maximum 697, net +80",
        "dominates replay `_publish_state`, new-operation `_publish_receipt` and `_publish_state`",
        "No twenty-fourth production path is authorized",
        "Direct M3e/M3g code remains unchanged",
        "changes no runtime, config, durable state, serving, fallback, authority, or retirement behavior",
    ),
}
for _path, _anchors in R2_LIVE_ROOT_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2_LIVE_ROOT_ANCHORS.items() for anchor in anchors)

# The third R2 P1 Return proved one remaining production construction gap. The
# amendment authorizes exactly one further path, the shared queued-runner request
# builder, and fixes semantic-value equality across the durable queue boundary.
R2_QUEUE_ROOT_ANCHORS = {
    STATUS: (
        "PR #804 recorded those two roots and completed with exact result `00ba475c689631520538b7531022603447f11bd0`",
        "Draft PR #806",
        "closed, unmerged, and tree-neutral at head `733b38fd3e74dcc542dd1c8f2ec1353a2cab6a95`",
        "zero changed paths, a tree identical to main, and exactly one execution receipt",
        "PR #805 is an audit record only and must not be reopened, marked Ready, or merged",
        "no renewed R2 branch may bootstrap from the PR #805 head",
        "`relaylm/relaymem_slp_queue_candidate.py`",
        "sole production constructor of `RelayMEMSLPOneQueuedJobRunnerRequest`",
        "already delegate request construction to it and remain byte-identical",
        "`3fc6f0f5a03bb717bcd163c692bc87e54c216f81`, 462 physical lines; final maximum 510 and net growth +48",
        "never persisted in the B3 durable queue record",
        "Python object identity cannot and need not survive the durable queue boundary",
        "exact immutable semantic value equality",
        "binding-free result for exact `primary_only` posture",
        "not an implicit fallback and not a silently substituted dataclass default",
        "No permit-valued request-field default may conceal missing construction-root supply",
        "may validate the exact decision but may not re-derive or downgrade it",
    ),
    PLAN: (
        "staged writer-fence and smoke-carriage budget amendment PR #808 exact result `758c160e1ee71bb9ad67fe10234e5a38c03c6a3d`",
        "mandatory R2D P8 -> verify -> R3 may become next, not started by this amendment",
        "Every implementation and P8 is a separate fresh-branch single-writer transaction",
        "sole production constructor of `RelayMEMSLPOneQueuedJobRunnerRequest`",
        "both already delegate request construction to that shared builder",
        "would duplicate derivation responsibility across three owners for no added coverage",
        "blob `3fc6f0f5a03bb717bcd163c692bc87e54c216f81`, 462 lines, maximum 510 (+48)",
        "never persisted in the B3 durable queue record",
        "exact immutable semantic value equality",
        "binding-free `primary_stable` permitted result",
    ),
    RT1C: (
        "relaylm/relaymem_slp_queue_candidate.py",
        "Draft PR #808; it required no P8",
        "never its PR head and never the PR #805 or PR #807 heads",
        "twenty-third authorized path and the sole remaining production construction gap proved by the PR #805 P1 evidence",
        "blob `3fc6f0f5a03bb717bcd163c692bc87e54c216f81`, 462 physical lines; final maximum 510, net +48",
        "Semantic-value equality is the contract",
        "never persisted in the B3 durable queue record",
        "Python object identity cannot and need not survive the durable queue boundary",
        "binding-free result for exact `primary_only` posture",
        "may validate the exact decision but may not re-derive or downgrade it",
        "stop at P1 and raise a new architecture amendment rather than reinterpreting this budget",
    ),
}
for _path, _anchors in R2_QUEUE_ROOT_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2_QUEUE_ROOT_ANCHORS.items() for anchor in anchors)

# PR #807 proved the strict-carriage conflict. RT-1D-R2 is now four ordered,
# independently bounded stages, each authorizing only the exact existing
# non-production call sites it must mechanically update.
R2_STAGED_ANCHORS = {
    STATUS: (
        "## RT-1D-R2 staged writer-fence and smoke-carriage budget amendment",
        "PR #806 completed with exact result `cd8ce6e05b6476b08ecf25a5100fb0c3f0e77644` and required no P8",
        "closed, unmerged, and tree-neutral at head `00991760b3070597d6b763a0b3ffc2eb820435f2` with one bootstrap commit, zero changed paths and exactly one execution receipt",
        "PR #807 is an audit record only and must never be reopened, marked Ready, merged, deleted, reset, moved, or used as an implementation bootstrap",
        "a permit-preserving unbound or default class is rejected",
        "RT-1D-R2A is complete in PR #809 with exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`",
        "each gated behind independent verification of the preceding implementation result and its mandatory P8 current-authority synchronization",
        "No stage may bootstrap from a PR head or an audit branch",
        "### Strict semantics retained for every stage",
        "A missing decision fails closed and a malformed decision fails closed, both before any side effect",
        "no `primary_writer_unbound` or equivalent third class",
        "no permit-valued dataclass, request, or function default",
        "Every direct caller supplies an exact immutable bound decision",
        "may validate the immutable value but may not resolve configuration or reconstruct state",
        "No queue schema or persistence field carries the decision",
        "direct M3e/M3g implementations remain byte-identical",
        "### Ordered stage budgets",
        "RT-1D-R2A — decision owner and managed finalization carriage",
        "RT-1D-R2B — queue, runner, worker, and Primary pipeline carriage",
        "RT-1D-R2C — Correct and Forget carriage",
        "RT-1D-R2D — Pin and Unpin carriage",
        "exactly 4 frozen existing caller files",
        "exactly 29 frozen existing caller files",
        "exactly 23 frozen existing caller files",
        "exactly 6 non-production paths",
        "58 distinct existing files and 61 stage assignments",
        "no wildcard `scripts/` or `tests/` authority",
        "no new test, smoke, or support file may be created in any stage",
    ),
    PLAN: (
        "## Historical RT-1D-R2B P8 current-authority synchronization gate",
        "RT-1D-R2A implementation PR #809 exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430` -> completed mandatory R2A P8",
        "mandatory R2D P8 -> verify -> R3 may become next, not started by this amendment",
        "only the independently verified exact resulting main from the immediately preceding gate may bootstrap the next, never a PR head and never an audit branch",
        "RT-1D-R2B and mandatory P8 PR #812 are complete; RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started",
        "RT-1D-R2A (paths 1-4), RT-1D-R2B (paths 5-13), RT-1D-R2C (paths 14-20), and RT-1D-R2D (paths 21-23)",
        "4 for R2A, 29 for R2B, 23 for R2C, and 5 for R2D",
        "There is no wildcard `scripts/` or `tests/` authority and no new test, smoke, or support file in any stage",
    ),
    RT1C: (
        "### RT-1D-R2 staged implementation budgets",
        "RT-1D-R2A frozen non-production callers (exactly 4 files)",
        "RT-1D-R2B frozen non-production callers (exactly 29 files)",
        "RT-1D-R2C frozen non-production callers (exactly 23 files)",
        "RT-1D-R2D frozen non-production callers (exactly 5 files)",
        "58 distinct existing files and 61 stage assignments",
        "There is no wildcard `scripts/` or `tests/` authority, no stage authorizes all 58 files, and no new test, smoke, or support file may be created in any stage",
        "A missing decision fails closed and a malformed decision fails closed, both before any side effect",
        "no `primary_writer_unbound` or equivalent third class",
        "A shared support helper is allowed only inside an already-existing authorized support file",
        "Mandatory transaction ordering: PR #807 accepted P1 Return",
        "scripts/relaylm_phase6c1_primary_worker_test_support.py",
        "scripts/_relaylm_phase6c1_durable_source_support.py",
        "tests/test_relaymem_lifecycle_characterization.py",
        "tests/test_response_service.py",
    ),
}
for _path, _anchors in R2_STAGED_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2_STAGED_ANCHORS.items() for anchor in anchors)

# Call-site granularity is the final accepted stage-assignment unit. A repeated
# overlap path never grants whole-file authority.
R2_CALL_SITE_ANCHORS = {
    STATUS: (
        "Call-site granularity is the accepted and final stage-assignment unit; file granularity is rejected",
        "each individual site belongs to exactly one stage",
        "A repeated path never grants whole-file authority: there are exactly three overlap files",
        "every other-stage site and unrelated behavior in that file stays byte-identical for that stage",
        "Every stage P1 remeasures the then-current blob after the preceding implementation and its mandatory P8 result",
        "the stage returns to P1 rather than broadening file authority",
    ),
    PLAN: (
        "Each stage carries a path budget plus a call-site sub-budget",
        "Call-site granularity is accepted and final and file granularity is rejected",
        "the same site may never be assigned to two stages",
        "A listed overlap path is not whole-file authority",
        "the exact changed hunks, that all other-stage sites are unchanged, and the final blob",
        "re-fetches and remeasures against a fresh baseline taken after the preceding P8 result",
        "the stage returns to P1 and file authority is not broadened",
    ),
    RT1C: (
        "#### Overlap files and call-site ownership",
        "Call-site granularity is accepted as the final authoritative stage-assignment unit. File granularity is rejected.",
        "Each individual site belongs to exactly one stage, and the same site may never be assigned to two stages",
        "A repeated path in two stage budgets is not whole-file permission",
        "every other-stage site and unrelated behavior remains byte-identical in that stage, and no stage treats the path listing as whole-file authority",
        "Minimum stage-owned scaffolding means only the imports, an existing fixture or factory signature, or an existing support helper",
        "A later stage must not use the pre-R2 or amendment-time blob as its write baseline",
        "the exact owned site names with pre-edit line spans, the exact changed hunks, proof that all other-stage sites are unchanged, the final blob",
        "the stage returns to P1. File authority is never broadened.",
        "There are exactly three overlap files:",
        "only `RelayMEMSLPOneQueuedJobRunnerRequest` construction, `execute_one_queued_relaymem_slp_primary_job` calls, and minimum R2B scaffolding; must not modify Correct sites",
        "only `apply_primary_memory_correction` calls and minimum R2C scaffolding; must not modify runner sites",
        "only `apply_primary_memory_forget` calls and minimum R2C scaffolding; must not modify Pin/Unpin sites",
        "only `apply_primary_memory_pin` and `apply_primary_memory_unpin` calls and minimum R2D scaffolding; must not modify Forget sites",
        "plus minimum R2C scaffolding; must not modify Pin/Unpin sites",
        "only `apply_primary_memory_pin` and `apply_primary_memory_unpin` sites and minimum R2D scaffolding; must not modify Correct/Forget sites",
        "The historical pre-P1-expansion counts were 58 distinct files, 61 stage assignments, R2A 4, R2B 29, R2C 23, and R2D 5.",
    ),
}
for _path, _anchors in R2_CALL_SITE_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2_CALL_SITE_ANCHORS.items() for anchor in anchors)

# RT-1D-R2A is complete in PR #809 with exact result
# 0f0b88a0bd601d1cd14b830ca209a26107f62430, which is exact current main. This
# mandatory P8 records that result as current authority and makes RT-1D-R2B
# next and not started; it requires no further P8.
R2A_COMPLETION_ANCHORS = {
    STATUS: (
        "## RT-1D-R2A completion and mandatory P8 (current)",
        "RT-1D-R2A decision owner and managed finalization carriage is complete.",
        "it is closed and merged with exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`, which is exact current main",
        "PR #809 carries exactly three normal commits",
        "`62bb2a8ae4bff175ae8169210cbcf2e604b48835`",
        "`3a8f33a5b9c59108f5c2d4b3289481f587d1e090`",
        "`eafdc0629fd307ed7c136488280ddb449c5787f1`",
        "It changed exactly 9 paths, +829/-7, with exactly one execution receipt, no comments, no reviews, and no review threads.",
        "The full suite was 1041/1041 and every applicable exact-head workflow completed with no candidate-caused failure.",
        "blob `dd21090a80ec`, 549 lines",
        "blob `a6be671c66a1`, 585 lines",
        "blob `f226d495bbd0`, 479 lines",
        "A tenth R2A path is invalid.",
        "no Optional permit compatibility, and no unbound class",
        "binding-free `primary_stable` permit with no store, store root, binding digest, or durable access",
        "Unhashable corrupted values converge to `False` or a stable owner error and never to an uncontrolled `TypeError`",
        "the guard was not broadened into a generic exception swallower",
        "The decision is derived exactly once at the managed runtime root and carried exactly to both stream and non-stream finalization.",
        "The public finalization guard rejects before any replay, source, or queue side effect, and the permitted path delegates to the preserved byte-identical effect owner.",
        "No decision is persisted in any queue record.",
        "Mandatory R2B P8 PR #812 completed with exact result `ca4eae55ab2dd053978d1dc7a4dd4b55fee5e5a8`.",
        "It is documentation-only, requires no further P8",
        "RT-1D-R2B is complete in PR #811 with exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d`",
        "RT-1D-R2C is complete in PR #814; at that historical point, RT-1D-R2D and RT-1D-R3 had not started.",
        "R2B queue, runner, worker, and Primary pipeline carriage is complete.",
    ),
    PLAN: (
        "completed mandatory R2A P8 PR #810 exact result `5822b01fd4642c89c39a2518672191bf1a8da115`",
        "independently verify the R2A P8 exact resulting main -> RT-1D-R2B complete in PR #811 exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d`",
        "RT-1D-R2B and mandatory P8 PR #812 are complete; RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started.",
        "RT-1D-R2A completed in PR #809 with exactly three commits, final head `eafdc0629fd307ed7c136488280ddb449c5787f1`, exactly 9 changed paths and +829/-7, a full suite of 1041/1041, and exact-head CI with no candidate-caused failure.",
        "RT-1D-R2B bootstrapped from the independently verified R2A P8 result and completed in PR #811.",
        "RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started; at that historical point, R2D, R3, R4, and R5 had not started. R2B queue, runner, worker, and pipeline carriage is complete.",
    ),
    RT1C: (
        "## RT-1D-R2A completion evidence and mandatory P8 gate",
        "### Identity, result, and commits",
        "produced exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`, which is exact current main",
        "`chore: bootstrap RT-1D-R2A execution`, tree-neutral with zero changed paths",
        "`feat: implement RT-1D-R2A writer decision carriage`",
        "`fix: bound malformed RT-1D-R2A writer decisions`",
        "There was exactly one execution receipt, no comments, no reviews, and no review threads.",
        "The full suite was 1041/1041 and exact-head CI completed with no candidate-caused failure. RT-1D-R2A implementation is complete.",
        "PR #809 changed exactly 9 paths, +829/-7. A tenth R2A path is invalid.",
        "| `relaylm/subjective_mem_retrieval_cutover.py` | +146/-0 | `dd21090a80ec` | 549 |",
        "| `relaylm/relaymem_slp_runtime_finalization.py` | +57/-0 | `a6be671c66a1` | 585 |",
        "| `tests/test_response_service.py` | +146/-2 | `f226d495bbd0` | 479 |",
        "### Final spans and structural limits",
        "549 against maximum 550",
        "553 against maximum 559 with net +10 against +16",
        "### Immutable decision schema and state mapping",
        "a frozen dataclass with six required fields and no default on any field",
        "There is no `primary_writer_unbound` or equivalent third class, no Optional decision used as an implicit permit, no permit-valued dataclass, request, or function default, and no arbitrary Mapping representation.",
        "Every complete valid state strictly before `primary_writer_fenced`",
        "`primary_writer_fenced` and every later state map to rejected with the stable reason `cutover_primary_writer_fenced`.",
        "### Binding-free `primary_only` and rehearsal reconstruction",
        "with no `EvidenceRecordStore` access, no store root, no binding, no binding digest, and no durable read or write",
        "delegates to the existing exact reconstruction owner, which remains byte-identical",
        "### Malformed, tampered, and unhashable fail-closed correction",
        "Both fields are now validated with tuple membership, which compares by equality rather than hashing",
        "The guard was deliberately not broadened into a generic exception swallower",
        "### Single derivation, exact carriage, and finalization guard",
        "derived exactly once, at the managed runtime construction root",
        "carries the same value into both the stream and the non-stream finalization `BackgroundTask`",
        "rejects before any durable replay, source publication, protected-source write, or queue enqueue",
        "delegates straight into the preserved effect owner, whose body is byte-identical to the pre-R2A public function",
        "### Queue persistence and stage boundary",
        "No decision is persisted in any queue record, and R2A introduces no queue schema or persistence field for it.",
        "R2B queue, runner, worker, and Primary pipeline carriage is complete; R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, R2D was next and had not started; at that historical point, R2D, R3, R4, and R5 had not started.",
        "### Historical R2B P8 gate",
        "Mandatory RT-1D-R2B P8 PR #812 completed with exact result `ca4eae55ab2dd053978d1dc7a4dd4b55fee5e5a8`.",
        "It is documentation-only, requires no further P8",
        "RT-1D-R2B completed from the independently verified R2A P8 result; R2C may bootstrap only from this correction transaction's independently verified exact resulting main.",
        "the later-stage budgets are not expanded by this P8",
    ),
}
for _path, _anchors in R2A_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2A_COMPLETION_ANCHORS.items() for anchor in anchors)

R2C_COMPLETION_ANCHORS = {
    STATUS: ("## RT-1D-R2C completion and mandatory P8 (historical)", "RT-1D-R2C completed in implementation PR #814", "814157df4b82937244c51a34e8f1ebc71b2e03c4", "RT-1D-R2D was next and had not started"),
    PLAN: ("## RT-1D-R2C completion and mandatory P8 (historical)", "RT-1D-R2C completed in implementation PR #814", "814157df4b82937244c51a34e8f1ebc71b2e03c4", "RT-1D-R2D was next and had not started"),
    RT1C: ("## RT-1D-R2C completion and mandatory P8 (historical)", "RT-1D-R2C completed in implementation PR #814", "814157df4b82937244c51a34e8f1ebc71b2e03c4", "No decision enters a durable schema or byte representation", "RT-1D-R2D was next and had not started"),
}
for _path, _anchors in R2C_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2C_COMPLETION_ANCHORS.items() for anchor in anchors)

R2D_P8_ANCHORS = {
    path: (
        "## RT-1D-R2D completion and mandatory P8 (current)",
        "RT-1D-R2D completed in implementation PR #818",
        "992496748efc70d51a7ed356e23aea650220902c",
        "a2197e9f92a8067d733f8adba524bf54eb2708b6",
        "exactly 10 paths, +119/-43",
        "four production paths",
        "six non-production paths",
        "malformed exact-type validation for uninitialized and partial instances, missing fields, wrong primitive types, unhashable values, and hostile equality values; all return `False`",
        "The predicate retains its exact-type check and catches only `SubjectiveMemRetrievalCutoverError`",
        "The downstream generic `except Exception` wrapper was removed",
        "before request validation, store-root resolution, store access, locking, replay, publication, or any durable effect",
        "Focused semantic-owner/lifecycle validation passed 126 tests",
        "the external Python 3.12 suite passed 1063 tests",
        "No decision is serialized or persisted and no durable schema or bytes changed",
        "Primary MEM remains the sole ordinary served memory and Retrieval authority",
        "Subjective ordinary Retrieval remains disabled and unwired",
        "The current transaction is the mandatory RT-1D-R2D P8 authority synchronization",
        "This documentation-only P8 requires no recursive P8",
        "Only after this P8 is merged and its exact resulting main is independently verified may RT-1D-R3 become uniquely next",
        "RT-1D-R3 is not started, and RT-1D-R4 and RT-1D-R5 remain not started",
        "never PR #818 head or an unmerged P8 head",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R2D_P8_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2D_P8_ANCHORS.items() for anchor in anchors)

R2D_P8_STALE = (
    "RT-1D-R2D is next and has not started",
    "RT-1D-R2D is next and not started",
    "R2D, At that historical point, R3, R4, and R5 had not started",
    "## RT-1D-R2C completion and mandatory P8 (current)",
    "The mandatory R2C P8 authority sync is the current transaction",
    "PR #818 remains open",
    "Draft PR #818",
    "PR #818 is unmerged",
    "The mandatory R2B P8 current-authority synchronization is Draft PR #812",
    "Draft PR #803 is the current architecture-only amendment",
    "renewed R2 remains gated by PR #803 merge",
    "exactly 3 production paths",
    "malformed exact-type decisions may raise AttributeError",
    "malformed exact-type decisions may raise TypeError",
    "the downstream generic exception wrapper remains",
    "R3 has started",
    "this P8 requires another P8",
    "R3 may bootstrap from PR #818 head",
    "R3 may bootstrap from the unmerged P8 head",
)

R2A_COMPLETION_STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "PR #809 is the current Lane C transaction",
    "PR #809 remains open",
    "PR #809 is Ready for review",
    "PR #809 is unmerged",
    "Draft PR #809",
    "RT-1D-R2A is next and not started",
    "RT-1D-R2A is next and has not started",
    "RT-1D-R2A remains not started",
    "RT-1D-R2A next, not started",
    "RT-1D-R2A is pending",
    "R2 remains not started",
    "+801/-7",
    "PR #809 carries exactly two normal commits",
    "only two R2A commits",
    "malformed unhashable values may raise TypeError",
    "unhashable values may raise `TypeError`",
    "the guard swallows every exception",
    "a generic exception swallower is allowed",
    "RT-1D-R2B has started",
    "RT-1D-R2B is started",
    "RT-1D-R2B may bootstrap from the PR #809 head",
    "R2B bootstraps from the unmerged P8 head",
    "a renewed R2 branch may bootstrap from the PR #809 head",
    "this P8 requires another P8",
    "the R2A P8 requires a further P8",
    "RT-1D-R2C has started",
    "the RT-1D-R2A P8 gate is current and RT-1D-R2B remains not started",
    "its mandatory P8 current-authority synchronization is Draft PR #810",
    "RT-1D-R2D has started",
    "RT-1D-R3 has started",
)

R2_CALL_SITE_STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "stage assignment is file-granular",
    "file granularity is the accepted stage-assignment unit",
    "an overlap file grants whole-file authority",
    "a listed stage may freely modify every site in the file",
    "the same site may belong to multiple stages",
    "R2B may modify Correct sites in phase_i3_primary_mem_correct_smoke.py",
    "R2C may modify runner sites in phase_i3_primary_mem_correct_smoke.py",
    "R2C may modify Pin/Unpin sites in phase_i5b_pin_unpin_apply_smoke.py",
    "R2D may modify Forget sites in phase_i5b_pin_unpin_apply_smoke.py",
    "R2C may modify Pin/Unpin sites in test_relaymem_lifecycle_characterization.py",
    "R2D may modify Correct/Forget sites in test_relaymem_lifecycle_characterization.py",
    "a later stage may use the original PR #808 blob without remeasurement",
    "an isolation failure may broaden the stage",
    "all content in an ALSO file is authorized",
    "a fourth overlap file exists",
)

R2_STAGED_STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "PR #806 is the current Lane C transaction",
    "queued-runner root budget amendment Draft PR #806 is current",
    "PR #807 remains open",
    "PR #807 is the current Lane C transaction",
    "PR #807 is Ready for review",
    "PR #807 merged",
    "a renewed R2 branch may bootstrap from the PR #807 head",
    "RT-1D-R2 remains a single monolithic implementation transaction",
    "a `primary_writer_unbound` class is allowed",
    "an unbound decision class preserves current behavior",
    "a missing decision preserves current behavior",
    "a permit-valued default is allowed",
    "a compatibility permit default is allowed",
    "runner and worker leaves may re-derive the decision",
    "leaf re-derivation is allowed",
    "every `scripts/` file is authorized",
    "every `tests/` file is authorized",
    "all 50 files are authorized in every stage",
    "all 58 files are authorized in every stage",
    "the exact caller list is omitted",
    "a stage may start before the preceding P8 result",
    "R3 has started",
    "the staged budget amendment requires P8",
    "a new test, smoke, or support file may be created",
)

R2_QUEUE_ROOT_STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "exact twenty-two-path R2 production budget",
    "exact twenty-two-path ordered list",
    "Production budget (exact twenty-two paths, authoritative order)",
    "No twenty-third production path is authorized",
    "no twenty-third production path",
    "A twenty-fourth production path is authorized",
    "## RT-1D-R2 live-root budget amendment (current)",
    "## Current RT-1D-R2 live-root budget amendment gate",
    "### Current RT-1D-R2 live-root amendment gate",
    "the PR #804 live-root budget amendment gate remains current",
    "PR #805 remains open",
    "PR #805 is the current Lane C transaction",
    "PR #805 merged",
    "PR #805 is Ready for review",
    "`relaylm/local_worker_once.py` is an authorized R2 production path",
    "`relaylm/relaymem_slp_scheduler_queue_lane.py` is an authorized R2 production path",
    "the writer decision is stored in the durable queue record",
    "Python object identity survives the durable queue boundary",
    "a permit-valued request-field default is allowed",
    "the queued-runner may derive the decision",
    "the worker leaf may derive the decision",
    "a renewed R2 branch may bootstrap from the PR #805 head",
    "the queued-runner root amendment requires P8",
)

STATUS_TOP_SUMMARY_STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "Mandatory R1 P8 PR #802 is current",
    "non-executable until PR #802 merges",
    "only that verified P8 resulting main may bootstrap R2",
    "R2 may restart from PR #803 head",
    "PR #803 requires P8",
)

R2_STRUCTURE_STALE = (
    "RT-1D-R2C is next and has not started",
    "R2C is next and has not started",
    "No R2C Correct or Forget carriage exists yet",
    "unchanged exact twenty-path R2 production budget",
    "original exact twenty-path R2 production budget remains unchanged",
    "managed_chat_runtime-only carriage is sufficient",
    "route-only Pin fence is sufficient",
    "R2 may bootstrap from the amendment PR head",
    "live-root amendment requires P8",
    "bcf8d6f42b21c23ea96e081d69f3c039c5da4f5c`, 544",
    "9dc4c8bd62623c0037821f19c8dab2d166dcbb01`, 618",
    "final maximum 560",
    "final maximum 698",
    "the PR #803 amendment gate remains current",
)

STALE_PROBES = (
    (STATUS, "RT-1D-R1 is next but non-executable until PR #800 merges"),
    (STATUS, "fresh RT-1D runtime P0/P1 architecture authorization PR #800 current"),
    (PLAN, "independently verify PR #800 exact resulting main after merge"),
    (PLAN, "RT-1D-R1 next, not started"),
    (RT1C, "RT-1D-R1 is not\nstarted and is non-executable until PR #800 merges"),
    (RT1C, "No runtime implementation has started."),
    (STATUS, "PR #793 must merge before S3A"),
    (PLAN, "PR #793 must merge and its exact resulting main must be independently verified before S3A"),
    (STATUS, "S3A has not started"),
    (RT1C, "S3A, S3B, S3C, and RT-1D runtime have not started."),
    (PLAN, "S3A implementation next"),
    (STATUS, "S3B is executable before S3A P8 merges and resulting-main verification"),
    (STATUS, "S3B is next but has not started"),
    (PLAN, "S3B implementation pending"),
    (STATUS, "S3C is executable before S3B P8 resulting-main verification"),
    (RT1C, "S3C next, not started -> mandatory P8 -> independently verify exact resulting main"),
    (STATUS, "fresh RT-1D runtime is current"),
    (PLAN, "fresh RT-1D runtime has started"),
    (STATUS, "Primary MEM is no longer the sole ordinary served memory and Retrieval authority"),
    (STATUS, "the current RT-1D-S3 P1 architecture amendment PR"),
    (STATUS, "The current RT-1D-S3 P1 architecture amendment PR"),
    (STATUS, "RT-1C shadow adapter, grounding handoff, usage ledger next ordered slice; registered / not started"),
    (PLAN, "RT-1C shadow adapter, grounding handoff, and usage ledger next ordered slice / registered / not started"),
    (RT1C, "RT-1C remains authorized and not implemented on\n`main`"),
    (PLAN, "RT-1D hard cutover and retirement registered / not started"),
    (STATUS, "RT-1D-S1 reader seams is the next executable Lane C prerequisite"),
    (PLAN, "RT-1D-S1 reader seams remains unimplemented"),
    (PLAN, "The ordered Lane C sequence begins with RT-1D-S1 reader seams after PR #789."),
    (STATUS, "mandatory P8 and resulting-main verification pending"),
    (PLAN, "RT-1D-S1 reader seams complete in PR #789 -> mandatory P8 pending -> verify resulting main"),
    (STATUS, "The mandatory S1 P8 authority sync and resulting-main verification must complete"),
    (STATUS, "RT-1D-S2 worker seams is the next executable Lane C prerequisite"),
    (PLAN, "RT-1D-S2 worker seams next after exact PR #790 resulting-main verification"),
    (PLAN, "implementation program is complete through RT-1D-S1"),
    (PLAN, "RT-1D-S2 worker seams remains unimplemented"),
    (STATUS, "The mandatory S2 P8 authority sync and resulting-main verification must complete"),
    (STATUS, "the current S2 mandatory P8 current-authority sync PR"),
    (STATUS, "The current S2 mandatory P8 current-authority sync PR"),
    (PLAN, "the current S2 mandatory P8 current-authority sync PR"),
    (PLAN, "The current S2 mandatory P8 current-authority sync PR"),
    (STATUS, "RT-1B and RT-1C remain default-off, explicit shadow-only, and unwired from ordinary Retrieval"),
    (PLAN, "RT-1B and RT-1C remain default-off, explicit shadow-only, and unwired from ordinary Retrieval"),
    (
        RT1C,
        "the durable cutover intent/fences/receipt belong to `relaylm/evidence_store.py`",
    ),
    (RT1C, "the Evidence store owns durable receipt/fence state"),
    (RT1C, "relaylm/relayctx_repack.py\nrelaylm/evidence_store.py"),
    (RT1C, "subjective_enabled -> receipt_finalized"),
    (RT1C, "(4) Subjective ordinary-reader enablement;"),
    (
        RT1C,
        "A crash after enablement but before receipt finalization keeps Primary fenced and "
        "Subjective non-serving until forward finalization proves the exact state.",
    ),
    (RT1C, "the old four writer-entry files alone cover all writers"),
    (RT1C, "current config already carries complete authority"),
    (RT1C, "public page-writer fencing alone is sufficient"),
    (RT1C, "process-local cutover authority is allowed"),
    (RT1C, "a Primary-root cutover marker is allowed"),
    (RT1C, "configuration or an enable flag selects served authority"),
    (RT1C, "Subjective serves before the finalized receipt"),
    (RT1C, "Primary serves after the finalized receipt"),
) + tuple((RT1C, stale) for stale in RT1_STRUCTURAL_STALE)


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
        for damaged in (body.replace(anchor, ""), body.replace(anchor, "REMOVED")):
            try:
                require_body(path, REQUIRED[path], damaged)
            except AssertionError:
                continue
            raise AssertionError(f"{path}: anchor is not enforced: {anchor!r}")
        print(f"PASS: removal and alteration of {anchor.splitlines()[0]!r} fail closed")
    focused_mutations = (
        (STATUS, "exact twenty-three-path R2 production budget", "exact twenty-path R2 production budget", "old current budget"),
        (STATUS, "`relaylm/managed_chat_response.py`", "`relaylm/managed_chat_runtime.py`", "managed response root omission"),
        (STATUS, "`relaylm/relaymem_primary_pin_apply.py`", "`relaylm/soul_lab_memory_pin_routes.py`", "Pin apply root omission"),
        (PLAN, "route-only Pin fence is insufficient", "route-only Pin fence is sufficient", "route-only sufficiency"),
        (PLAN, "managed_chat_runtime.py`-only carriage is insufficient", "managed_chat_runtime-only carriage is sufficient", "runtime-only sufficiency"),
        (PLAN, "only the independently verified exact resulting main from the immediately preceding gate may bootstrap the next, never a PR head and never an audit branch", "the preceding PR head may bootstrap the next stage", "PR-head bootstrap"),
        (PLAN, "RT-1D-R2B and mandatory P8 PR #812 are complete; RT-1D-R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, RT-1D-R2D was next and had not started", "the PR #806 queued-runner root budget amendment gate remains current and R2 remains not started", "stale PR #806 current gate"),
        (RT1C, "it required no P8", "live-root amendment requires P8", "incorrect P8"),
        (RT1C, "Draft PR #808; it required no P8", "Draft PR #808; the staged budget amendment requires P8", "staged amendment P8"),
        (STATUS, "No twenty-fourth production path is authorized", "A twenty-fourth production path is authorized", "extra path"),
        (STATUS, "exact twenty-three-path R2 production budget", "exact twenty-two-path R2 production budget", "stale twenty-two-path budget"),
        (RT1C, "Production budget (exact twenty-three paths, authoritative order, split across the four ordered stages RT-1D-R2A, RT-1D-R2B, RT-1D-R2C, and RT-1D-R2D)", "Production budget (exact twenty-two paths, authoritative order)", "stale twenty-two-path order"),
        (STATUS, "`relaylm/relaymem_slp_queue_candidate.py`", "`relaylm/local_worker_once.py`", "queued-runner root omission"),
        (STATUS, "3fc6f0f5a03bb717bcd163c692bc87e54c216f81", "0fc6f0f5a03bb717bcd163c692bc87e54c216f81", "queue candidate blob"),
        (STATUS, "final maximum 510 and net growth +48", "final maximum 511 and net growth +49", "queue candidate limit"),
        (STATUS, "never persisted in the B3 durable queue record", "stored in the durable queue record", "durable decision persistence"),
        (STATUS, "Python object identity cannot and need not survive the durable queue boundary", "Python object identity survives the durable queue boundary", "identity across durable queue"),
        (STATUS, "No permit-valued request-field default may conceal missing construction-root supply", "a permit-valued request-field default is allowed", "permit-valued default"),
        (STATUS, "may validate the exact decision but may not re-derive or downgrade it", "the worker leaf may derive the decision", "leaf re-derivation"),
        (STATUS, "PR #805 is an audit record only and must not be reopened, marked Ready, or merged", "PR #805 is the current Lane C transaction", "PR #805 reuse"),
        (STATUS, "no renewed R2 branch may bootstrap from the PR #805 head", "a renewed R2 branch may bootstrap from the PR #805 head", "PR #805 head bootstrap"),
        (STATUS, "RT-1D-R2A is complete in PR #809 with exact result `0f0b88a0bd601d1cd14b830ca209a26107f62430`", "RT-1D-R2 remains a single monolithic implementation transaction", "monolithic R2 still current"),
        (STATUS, "a permit-preserving unbound or default class is rejected", "an unbound decision class preserves current behavior", "unbound compatibility class"),
        (STATUS, "A missing decision fails closed and a malformed decision fails closed, both before any side effect", "a missing decision preserves current behavior", "missing preserves behavior"),
        (STATUS, "no permit-valued dataclass, request, or function default", "a permit-valued default is allowed", "permit-valued default"),
        (STATUS, "may validate the immutable value but may not resolve configuration or reconstruct state", "leaf re-derivation is allowed", "leaf re-derivation"),
        (STATUS, "no wildcard `scripts/` or `tests/` authority", "every `scripts/` file is authorized", "wildcard script authority"),
        (STATUS, "no new test, smoke, or support file may be created in any stage", "a new test, smoke, or support file may be created", "new helper file"),
        (STATUS, "58 distinct existing files and 61 stage assignments", "all 58 files are authorized in every stage", "flat caller authority"),
        (STATUS, "exactly 29 frozen existing caller files", "exactly 30 frozen existing caller files", "R2B caller count"),
        (STATUS, "PR #807 is an audit record only and must never be reopened, marked Ready, merged, deleted, reset, moved, or used as an implementation bootstrap", "PR #807 is the current Lane C transaction", "PR #807 reuse"),
        (STATUS, "each gated behind independent verification of the preceding implementation result and its mandatory P8 current-authority synchronization", "a stage may start before the preceding P8 result", "stage ordering"),
        (PLAN, "mandatory R2D P8 -> verify -> R3 may become next, not started by this amendment", "R3 has started", "R3 started"),
        (RT1C, "RT-1D-R2B frozen non-production callers (exactly 29 files)", "RT-1D-R2B frozen non-production callers (exactly 30 files)", "RT2B inventory count"),
        (RT1C, "Mandatory transaction ordering: PR #807 accepted P1 Return", "the staged budget amendment requires P8", "amendment P8"),
        (STATUS, "Call-site granularity is the accepted and final stage-assignment unit; file granularity is rejected", "file granularity is the accepted stage-assignment unit", "file-granular assignment"),
        (STATUS, "A repeated path never grants whole-file authority: there are exactly three overlap files", "an overlap file grants whole-file authority", "whole-file authority"),
        (STATUS, "each individual site belongs to exactly one stage", "the same site may belong to multiple stages", "site in two stages"),
        (STATUS, "the stage returns to P1 rather than broadening file authority", "an isolation failure may broaden the stage", "isolation broadening"),
        (PLAN, "re-fetches and remeasures against a fresh baseline taken after the preceding P8 result", "a later stage may use the original PR #808 blob without remeasurement", "stale stage baseline"),
        (RT1C, "There are exactly three overlap files:", "a fourth overlap file exists", "fourth overlap file"),
        (RT1C, "minimum R2B scaffolding; must not modify Correct sites", "R2B may modify Correct sites in phase_i3_primary_mem_correct_smoke.py", "R2B Correct sites"),
        (RT1C, "minimum R2C scaffolding; must not modify runner sites", "R2C may modify runner sites in phase_i3_primary_mem_correct_smoke.py", "R2C runner sites"),
        (RT1C, "minimum R2D scaffolding; must not modify Forget sites", "R2D may modify Forget sites in phase_i5b_pin_unpin_apply_smoke.py", "R2D Forget sites"),
        (RT1C, "minimum R2D scaffolding; must not modify Correct/Forget sites", "R2D may modify Correct/Forget sites in test_relaymem_lifecycle_characterization.py", "R2D Correct/Forget sites"),
        (RT1C, "The historical pre-P1-expansion counts were 58 distinct files, 61 stage assignments, R2A 4, R2B 29, R2C 23, and R2D 5.", "all content in an ALSO file is authorized", "ALSO whole-file"),
        (STATUS, "final maximum 559 and net growth +16", "final maximum 560 and net growth +17", "managed limit"),
        (STATUS, "final maximum 697 and net growth +80", "final maximum 698 and net growth +81", "Pin apply limit"),
        (STATUS, "bcf8d6f42b21c23ea96e081d69f3c039c5da4f5c", "0cf8d6f42b21c23ea96e081d69f3c039c5da4f5c", "managed blob"),
        (STATUS, "9dc4c8bd62623c0037821f19c8dab2d166dcbb01", "0dc4c8bd62623c0037821f19c8dab2d166dcbb01", "Pin apply blob"),
        (STATUS, "0f0b88a0bd601d1cd14b830ca209a26107f62430", "1f0b88a0bd601d1cd14b830ca209a26107f62430", "R2A exact result"),
        (STATUS, "It changed exactly 9 paths, +829/-7", "It changed exactly 9 paths, +801/-7", "stale R2A stats"),
        (STATUS, "PR #809 carries exactly three normal commits", "PR #809 carries exactly two normal commits", "two R2A commits"),
        (STATUS, "The full suite was 1041/1041", "The full suite was 1039/1041", "R2A suite count"),
        (STATUS, "It is documentation-only, requires no further P8", "It is documentation-only, this P8 requires another P8", "further P8 required"),
        (STATUS, "RT-1D-R2B is complete in PR #811 with exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d`", "RT-1D-R2B has started", "R2B started"),
        (STATUS, "A tenth R2A path is invalid.", "A tenth R2A path is authorized.", "tenth R2A path"),
        (STATUS, "the guard was not broadened into a generic exception swallower", "a generic exception swallower is allowed", "generic swallower"),
        (STATUS, "blob `dd21090a80ec`, 549 lines", "blob `ed21090a80ec`, 549 lines", "cutover owner final blob"),
        (PLAN, "completed mandatory R2A P8 PR #810 exact result `5822b01fd4642c89c39a2518672191bf1a8da115`", "mandatory R2A P8 not started", "current P8 binding"),
        (PLAN, "independently verify the R2A P8 exact resulting main -> RT-1D-R2B complete in PR #811 exact result `a1fac7e4d3dee844990b680aa27130cee9051c3d`", "RT-1D-R2B has started", "plan R2B started"),
        (PLAN, "RT-1D-R2B bootstrapped from the independently verified R2A P8 result and completed in PR #811.", "R2B bootstraps from the unmerged P8 head", "R2B bootstrap source"),
        (RT1C, "PR #809 changed exactly 9 paths, +829/-7. A tenth R2A path is invalid.", "PR #809 changed exactly 9 paths, +801/-7. A tenth R2A path is invalid.", "architecture R2A stats"),
        (RT1C, "Both fields are now validated with tuple membership, which compares by equality rather than hashing", "malformed unhashable values may raise TypeError", "unhashable correction"),
        (RT1C, "R2B queue, runner, worker, and Primary pipeline carriage is complete; R2C is complete in PR #814 with exact result `814157df4b82937244c51a34e8f1ebc71b2e03c4`; at that historical point, R2D was next and had not started; at that historical point, R2D, R3, R4, and R5 had not started.", "RT-1D-R2B has started", "architecture R2B started"),
        (RT1C, "| `relaylm/relaymem_slp_runtime_finalization.py` | +57/-0 | `a6be671c66a1` | 585 |", "| `relaylm/relaymem_slp_runtime_finalization.py` | +57/-0 | `a6be671c66a1` | 586 |", "finalization final lines"),
    )
    for path, current, damaged, label in focused_mutations:
        body = read(path)
        assert current in body, f"{path}: focused anchor absent: {current!r}"
        try:
            require_body(path, REQUIRED[path], body.replace(current, damaged))
        except AssertionError:
            print(f"PASS: {path}: {label} fails closed")
        else:
            raise AssertionError(f"{path}: {label} is not rejected")
    for path, stale in STALE_PROBES:
        body = read(path)
        assert stale not in body, f"{path}: stale anchor is present: {stale!r}"
        try:
            forbid_body(path, STALE, body + "\n" + stale + "\n")
        except AssertionError:
            print(f"PASS: reintroducing {stale.splitlines()[0]!r} fails closed")
            continue
        raise AssertionError(f"{path}: stale anchor is not forbidden: {stale!r}")
    for stale in STATUS_TOP_SUMMARY_STALE:
        body = read(STATUS)
        assert stale not in body, f"{STATUS}: top-summary stale anchor is present: {stale!r}"
        try:
            forbid_body(STATUS, STATUS_TOP_SUMMARY_STALE, body + "\n" + stale + "\n")
        except AssertionError:
            print(f"PASS: {STATUS}: reintroducing top-summary stale form {stale!r} fails closed")
            continue
        raise AssertionError(f"{STATUS}: top-summary stale form is not forbidden: {stale!r}")
    for path in R2_LIVE_ROOT_ANCHORS:
        for stale in R2_STRUCTURE_STALE:
            body = read(path)
            assert stale not in body, f"{path}: R2 stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R2_STRUCTURE_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: R2 stale anchor is not forbidden: {stale!r}")
    for path in R2_QUEUE_ROOT_ANCHORS:
        for stale in R2_QUEUE_ROOT_STALE:
            body = read(path)
            assert stale not in body, f"{path}: queue-root stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R2_QUEUE_ROOT_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: queue-root stale anchor is not forbidden: {stale!r}")
    for path in R2_STAGED_ANCHORS:
        for stale in R2_STAGED_STALE:
            body = read(path)
            assert stale not in body, f"{path}: staged stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R2_STAGED_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: staged stale anchor is not forbidden: {stale!r}")
    for path in R2_CALL_SITE_ANCHORS:
        for stale in R2_CALL_SITE_STALE:
            body = read(path)
            assert stale not in body, f"{path}: call-site stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R2_CALL_SITE_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: call-site stale anchor is not forbidden: {stale!r}")
    for path in R2A_COMPLETION_ANCHORS:
        for stale in R2A_COMPLETION_STALE:
            body = read(path)
            assert stale not in body, f"{path}: R2A stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R2A_COMPLETION_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: R2A stale anchor is not forbidden: {stale!r}")
    for path in R2D_P8_ANCHORS:
        for stale in R2D_P8_STALE:
            body = read(path)
            assert stale not in body, f"{path}: R2D P8 stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R2D_P8_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: R2D P8 stale anchor is not forbidden: {stale!r}")
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
    forbid(STATUS, STATUS_TOP_SUMMARY_STALE)
    for path in R2_LIVE_ROOT_ANCHORS:
        forbid(path, R2_STRUCTURE_STALE)
    for path in R2_QUEUE_ROOT_ANCHORS:
        forbid(path, R2_QUEUE_ROOT_STALE)
    for path in R2_STAGED_ANCHORS:
        forbid(path, R2_STAGED_STALE)
    for path in R2_CALL_SITE_ANCHORS:
        forbid(path, R2_CALL_SITE_STALE)
    for path in R2A_COMPLETION_ANCHORS:
        forbid(path, R2A_COMPLETION_STALE)
    for path in R2D_P8_ANCHORS:
        forbid(path, R2D_P8_STALE)
    forbid("docs/PROJECT_STATUS.md", HISTORY_ONLY_STATUS_ANCHORS)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main(sys.argv[1:])
