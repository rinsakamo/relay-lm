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
        "RT-1D structural-seam architecture amendment      P1 Return recorded; runtime implementation complete through R3",
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
        "RT-1D structural P1 Return / runtime implementation complete through R3",
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
        "RT-1A, RT-1B,\nRT-1C, and RT-1D through R3 rehearsal/readiness are implemented within it; the\nRT-1D hard cutover, authority transfer, ordinary Subjective serving, and Primary\nretirement remain the unimplemented target.",
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
        "RT-1D runtime implementation is complete through R3\nrehearsal/readiness; the hard cutover, authority transfer, and Primary\nretirement remain unimplemented.",
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
        "`relaylm/evidence/store.py` is generic persistence infrastructure, not the RT-1D semantic authority.",
        "ordinary route / cutover orchestration\n  -> subjective_mem_retrieval_cutover domain owner\n       -> EvidenceRecordStore generic persistence",
        "The generic store must never import the cutover owner.",
        "The cutover owner reuses `EvidenceRecordStore` only for:",
        "Therefore RT-1D introduces no second lock, no second durable root, no second transaction journal, and no second generic recovery mechanism, and adds no RT-1D policy or state-machine logic to `relaylm/evidence/store.py`.",
        "Modifying `relaylm/evidence/store.py` is allowed only through a documented P1 return that proves, from exact evidence, a missing generic persistence capability that is not RT-1D-specific. This authorization does not pre-authorize such a change.",
        "`relaylm/evidence/store.py` is an imported and reused generic infrastructure\ndependency, not an expected modified production path and not the RT-1D semantic\nowner.",
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
    "the durable cutover intent/fences/receipt belong to `relaylm/evidence/store.py`",
    "the Evidence store owns durable receipt/fence state",
    "relaylm/relayctx_repack.py\nrelaylm/evidence/store.py",
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
    (STATUS, "RT-1D structural-seam architecture amendment      P1 Return recorded; runtime implementation complete through R3"),
    (STATUS, "RT-1D-S1 reader seams                          complete in PR #789; behavior-preserving"),
    (STATUS, "S1 mandatory P8 current-authority sync      PR #790; exact resulting main 3e20274f18306f7db2410fd5239051411b9c052b"),
    (STATUS, "RT-1D-S2 worker seams                    complete in PR #791; exact resulting main 31b700a2db0af7819f761d51bd946ff6798eb4c9"),
    (STATUS, "S2 mandatory P8 current-authority sync      PR #792; exact resulting main 7e4fb4383dc6c1229d488ac200132b66f6b65bba"),
    (STATUS, "RT-1D-S3A Correct core seams       complete in PR #794; exact resulting main 2d05a41235e396ac82d536437ed8e5568f617253"),
    (STATUS, "Primary MEM remains the sole ordinary served memory and Retrieval authority until a future RT-1D implementation is validated, merged, and its cutover receipt is finalized."),
    (STATUS, "- ordinary served Subjective MEM Retrieval, query matching, ranking, cache, and request-path wiring;"),
    (PLAN, "RT-1D-S3C Soul Lab mutation route seams completed in PR #798"),
    (PLAN, "RT-1D structural P1 Return / runtime implementation complete through R3"),
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
        "`relaylm/evidence/store.py` is generic persistence infrastructure, not the RT-1D "
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
        "policy or state-machine logic to `relaylm/evidence/store.py`.",
    ),
    (
        RT1C,
        "Modifying `relaylm/evidence/store.py` is allowed only through a documented P1 "
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
    (RT1C, "RT-1D runtime implementation is complete through R3\nrehearsal/readiness; the hard cutover, authority transfer, and Primary\nretirement remain unimplemented."),
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
        "## RT-1D-R2D completion and mandatory P8 (historical)",
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
        "The mandatory RT-1D-R2D P8 authority synchronization completed in PR #819",
        "This documentation-only P8 requires no recursive P8",
        "The post-P8 validator correction PR #820 completed with exact result",
        "at that historical point RT-1D-R3 was uniquely next and had not started, and RT-1D-R4 and RT-1D-R5 had not started",
        "never PR #818 head, PR #819 head, or any unmerged branch head",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R2D_P8_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple((path, anchor) for path, anchors in R2D_P8_ANCHORS.items() for anchor in anchors)

R3_GENERATION_IDENTITY_AMENDMENT_ANCHORS = {
    path: (
        "## RT-1D-R3 projection-generation identity P1 amendment (historical)",
        "exact bootstrap `6a790486564b9d917ff8a3b20ef7e30417dd74f2`",
        "exact `smretrievalgen_<64-lowercase-hex>` identity",
        "RT-1D-R3 therefore remained unstarted",
        "`projection_source_digest`, `bootstrap_main_sha`, and `resulting_main_sha` remain raw 64-character lowercase SHA-256 values",
        "No prefix stripping, re-hashing, dual-read, fallback, or compatibility representation is authorized",
        "`relaylm/config.py` and `config.example.yaml`",
        "Projection builder/store, selection, usage ledger, Primary reader, managed route, and all R2 writer-carriage paths remain byte-identical",
        "This architecture-only amendment requires no P8",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R3_GENERATION_IDENTITY_AMENDMENT_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R3_GENERATION_IDENTITY_AMENDMENT_ANCHORS.items()
    for anchor in anchors
)

R3_COORDINATOR_AMENDMENT_ANCHORS = {
    path: (
        "## RT-1D-R3 rehearsal coordinator P1 amendment (historical)",
        "PR #823 was closed unmerged at exact frozen head `d411d443e71d771be4ac1f93e994d876e3f73b3a`",
        "`relaylm/subjective_mem_retrieval_rehearsal.py`",
        "`tests/test_subjective_mem_retrieval_rehearsal.py`",
        "below 500 normally formatted physical lines",
        "every function stays below 80 normally formatted physical lines",
        "Readiness is factory-only",
        "bundle is exactly absent before any write",
        "deletes only a bundle installed and trusted-read by that invocation",
        "verifies exact post-delete absence",
        "Projection builder/store, selection, usage ledger, Primary reader, managed route, and all R2 writer-carriage paths remain byte-identical",
        "This architecture-only amendment requires no P8",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R3_COORDINATOR_AMENDMENT_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R3_COORDINATOR_AMENDMENT_ANCHORS.items()
    for anchor in anchors
)

R3_COMPLETION_ANCHORS = {
    path: (
        "## RT-1D-R3 completion and mandatory P8 (completed)",
        "RT-1D-R3 rehearsal coordinator implementation completed in PR #825",
        "bootstrap `5f91be0efbaf2ba07777c973e260c40af343b7d6`",
        "final reviewed head `a21cfb0af9b0fbef3d466b145d81070b658e2540`",
        "exact squash result `1eeb4c03151a20b8504819f6c72564b981c84157`",
        "three pre-squash commits changed exactly seven implementation paths, +914/-15",
        "`relaylm/subjective_mem_retrieval_rehearsal.py` is 398 physical lines with a maximum function span of 40 lines",
        "passed 1086 tests with 0 failures and 1 warning in 671.84 seconds",
        "the normalized failure state is none, and `p6_stop` is false",
        "preserved the existing implementation receipt's logical writer",
        "one dedicated disposable rehearsal coordinator",
        "an immutable specification validated before every projection or store effect",
        "a factory-only readiness proof carrying complete binding, generation, source, manifest, ordered-row-population, characterization, readiness, and instance-owned closed-false authority fields",
        "an R3-exclusive fresh projection root in which every exact, stale, foreign, corrupt, unsafe, or unreadable pre-existing bundle fails closed without mutation",
        "deletion only of a bundle installed and trusted-read by the same invocation, exact post-delete absence, and same-source rebuild equality",
        "RT-1D-R3 introduces no ordinary Subjective serving, ordinary usage event, authority-state write, intent, fence, receipt, activation, fallback, transfer, or retirement behavior",
        "The mandatory RT-1D-R3 P8 current-authority synchronization completed in PR #826 from bootstrap `1eeb4c03151a20b8504819f6c72564b981c84157`, final reviewed head `3a9864839515d5787bd11c806fec655bffb9f0df`, and exact resulting main `c291e26f1c20e6479df427054142916dd7df57db`",
        "It was documentation-only and required no recursive P8",
        "the RT-1D-R4 implementation attempt then returned at P1 without repository mutation",
        "PR #823 remains closed, unmerged, and frozen at audit head `d411d443e71d771be4ac1f93e994d876e3f73b3a` as design evidence only, and its commits remain prohibited implementation history",
        "At that historical point RT-1D implementation was complete through R3 rehearsal/readiness",
        "RT-1D-R1 durable preparation and RT-1D-R2A through RT-1D-R2D Primary writer-fence carriage, together with their mandatory P8 gates, are completed historical work, not future steps",
        "RT-1D-R3 rehearsal/readiness implementation merged separately as PR #825, and its mandatory R3 P8 completed in PR #826 with exact resulting main `c291e26f1c20e6479df427054142916dd7df57db`",
        "At that historical point the final RT-1D hard cutover, authority transfer, ordinary Subjective serving, Primary retirement, and RT-1D-R4 and RT-1D-R5 were incomplete",
        "RT-1D-R4 implementation and RT-1D-R5 had not started, and RT-1D-R4 implementation could then bootstrap only from the independently verified exact resulting main of the completed RT-1D-R4 activation budget amendment PR #828, `9aea56d6d61d69c390bd0c2dc740739ab155d76e`",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R3_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R3_COMPLETION_ANCHORS.items()
    for anchor in anchors
)

R3_COMPLETION_STALE = (
    "RT-1D-R3 is uniquely next and remains unstarted",
    "RT-1D-R3 remains unstarted",
    "RT-1D-R3 is next and has not started",
    "RT-1D-R3 remains not started",
    "RT-1D-R3 runtime is not started",
    "RT-1D runtime remains not started",
    "the rehearsal coordinator is absent",
    "`relaylm/subjective_mem_retrieval_rehearsal.py` does not exist",
    "the rehearsal coordinator is authorized but not implemented",
    "RT-1D-R3 is authorized and not implemented",
    "## RT-1D-R3 projection-generation identity P1 amendment (current)",
    "## RT-1D-R3 rehearsal coordinator P1 amendment (current)",
    "## RT-1D-R2D completion and mandatory P8 (completed current boundary)",
    "## RT-1D-R3 completion and mandatory P8 (historical)",
    "R4 activation is authorized before the verified R3 P8 result",
    "Subjective ordinary Retrieval is enabled",
    "RT-1D-R5 has started",
    "the RT-1D-R3 P8 requires another P8",
    "this P8 requires a recursive P8",
    "PR #823 merged",
    "PR #823 commits may be reused",
    "PR #823 is reusable implementation history",
    "RT-1D-R3 completed in PR #823",
    "PR #825 remains open",
    "PR #825 is unmerged",
    "Draft PR #825",
    "RT-1D-R2C and RT-1D-R2D follow in order",
    "RT-1D structural-seam architecture amendment      P1 Return recorded; runtime not started",
    "RT-1D structural P1 Return / runtime not started",
    "RT-1D remains the unimplemented target",
    "Runtime implementation remains not started.",
    "RT-1D runtime implementation has not started",
    "RT-1D runtime is not started",
    "fresh RT-1D runtime transaction / only after S3C P8 exact resulting-main verification",
    "RT-1D-R1 is next and has not started",
    "RT-1D-R2 is next and has not started",
    "the mandatory R1 P8 gate is a future step",
    "the mandatory R2D P8 gate is a future step",
    "RT-1D implementation is not complete through R3",
    "R1, R2A-R2D, and R3 merged with completed mandatory P8 gates",
    "and RT-1D-R3 rehearsal/readiness are merged historical work whose mandatory P8 gates are completed",
    "## RT-1D-R3 completion and mandatory P8 (current)",
    "PR #826 remains open",
    "PR #826 is unmerged",
    "Draft PR #826",
    "its mandatory R3 P8 is this still-open PR #826",
    "the mandatory R3 P8 is the current incomplete gate",
    "RT-1D-R4 becomes uniquely next only after PR #826 merges",
    "This transaction is the mandatory RT-1D-R3 P8 current-authority synchronization",
)

R3_COMPLETION_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "final reviewed head `a21cfb0af9b0fbef3d466b145d81070b658e2540`",
            "final reviewed head `b21cfb0af9b0fbef3d466b145d81070b658e2540`",
            "R3 reviewed head",
        ),
        (
            "exact squash result `1eeb4c03151a20b8504819f6c72564b981c84157`",
            "exact squash result `2eeb4c03151a20b8504819f6c72564b981c84157`",
            "R3 exact result",
        ),
        (
            "three pre-squash commits changed exactly seven implementation paths, +914/-15",
            "three pre-squash commits changed exactly six implementation paths, +914/-15",
            "R3 path inventory",
        ),
        (
            "`relaylm/subjective_mem_retrieval_rehearsal.py` is 398 physical lines with a maximum function span of 40 lines",
            "`relaylm/subjective_mem_retrieval_rehearsal.py` is 498 physical lines with a maximum function span of 40 lines",
            "coordinator structure",
        ),
        (
            "passed 1086 tests with 0 failures and 1 warning in 671.84 seconds",
            "passed 1085 tests with 1 failure and 1 warning in 671.84 seconds",
            "R3 suite result",
        ),
        (
            "It was documentation-only and required no recursive P8",
            "It was documentation-only and required a recursive P8",
            "R3 P8 recursion",
        ),
        (
            "exact resulting main `c291e26f1c20e6479df427054142916dd7df57db`. It was documentation-only",
            "exact resulting main `d291e26f1c20e6479df427054142916dd7df57db`. It was documentation-only",
            "R3 P8 exact result",
        ),
        (
            "final reviewed head `3a9864839515d5787bd11c806fec655bffb9f0df`",
            "final reviewed head `4a9864839515d5787bd11c806fec655bffb9f0df`",
            "R3 P8 reviewed head",
        ),
        (
            "At that historical point RT-1D implementation was complete through R3 rehearsal/readiness",
            "RT-1D implementation is not complete through R3",
            "RT-1D runtime completion",
        ),
        (
            "together with their mandatory P8 gates, are completed historical work, not future steps",
            "the mandatory R2D P8 gate is a future step",
            "completed P8 gates as future steps",
        ),
        (
            "its mandatory R3 P8 completed in PR #826 with exact resulting main `c291e26f1c20e6479df427054142916dd7df57db`",
            "its mandatory R3 P8 is this still-open PR #826, which is the current incomplete gate",
            "R3 P8 still incomplete",
        ),
        (
            "At that historical point the final RT-1D hard cutover, authority transfer, ordinary Subjective serving, Primary retirement, and RT-1D-R4 and RT-1D-R5 were incomplete",
            "The final RT-1D hard cutover and Primary retirement are complete",
            "cutover completeness",
        ),
    )
)

R4_BUDGET_ANCHORS = {
    path: (
        "RT-1D-R4 one-authority activation returned at P1 without repository mutation from exact bootstrap main `c291e26f1c20e6479df427054142916dd7df57db`",
        "The authorized implementation branch `agent/rt1d-r4-one-authority-activation` remains identical to that exact main, 0 ahead / 0 behind",
        "That zero-diff implementation branch is frozen",
        "At that historical point RT-1D-R4 implementation and RT-1D-R5 had not started",
        "The requested mode is owned exactly by `SubjectiveMemRetrievalCutoverMode` and "
        "`RelayLMConfig` validation in `relaylm/config.py`, and by `RequestedMode` and "
        "`SubjectiveMemRetrievalCutoverRequest.__post_init__` in "
        "`relaylm/subjective_mem_retrieval_cutover.py`",
        "the cutover binding carries no requested-mode field",
        "Both owners admit only `primary_only` and `rehearsal`",
        "The extension is applied to both exact requested-mode owners together, so the configuration mode and the cutover request schema never disagree",
        "`relaylm/subjective_mem_retrieval_cutover.py` is 688 normally formatted physical lines before R4",
        "One new private R4 mechanics owner is authorized: `relaylm/_subjective_mem_retrieval_cutover_activation.py`",
        "The allowed dependency direction is exactly one-way",
        "The private activation owner must not import the cutover facade, the configuration owner, request-path owners, selection, the usage ledger, Primary owners, or RelayCTX",
        "the private activation owner is not a second semantic authority",
        "The public cutover owner alone owns the public binding, the requested-mode, result, and decision schemas, semantic validation, the exact reader and writer authority decisions, and validation of the private owner's returned content-free result",
        "The cutover facade remains strictly below 1000 normally formatted physical "
        "lines under the RT-1D-R4 cutover-facade structural exception recorded below",
        "The new private activation owner remains below roughly 600 normally formatted physical lines",
        "Every new or materially changed orchestration remains at or below roughly 80 normally formatted physical lines",
        "exactly these eleven paths: `relaylm/subjective_mem_retrieval_cutover.py`, "
        "`relaylm/_subjective_mem_retrieval_cutover_activation.py`, `relaylm/config.py`, "
        "`config.example.yaml`, `relaylm/managed_chat_pipeline_runtime.py`, "
        "`relaylm/managed_chat_runtime.py`, `relaylm/relaymem_retrieval.py`, "
        "`relaylm/relaymem_primary_recall.py`, `relaylm/relayctx_repack.py`, "
        "`relaylm/subjective_mem_retrieval_selection.py`, and "
        "`relaylm/subjective_mem_retrieval_usage_ledger.py`",
        "The original exact-eight RT-1D-R4 production budget is superseded and is no longer executable",
        "The RT-1D-R4 focused evidence budget is exactly the accepted existing evidence for "
        "those production paths: existing request-path tests; reader-seam and offload tests; "
        "pipeline-ordering tests; RelayCTX tests; Subjective selection and usage-ledger tests; "
        "existing configuration and cutover tests; "
        "`scripts/relaylm_p0_pipeline_ordering_smoke.py`; and "
        "`scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`",
        "There is no wildcard `tests/` or `scripts/` authority",
        "no new generic test, smoke, support, helper, framework, or control-plane file is authorized",
        "The requested cutover mode is extended exactly to `primary_only`, `rehearsal`, and `subjective_only`",
        "`subjective_only` requires the complete exact tuple and is only a requested deployment mode",
        "Configuration alone never enables Subjective serving.",
        "only an exact finalized transfer receipt bound to matching durable state may permit ordinary Subjective serving",
        "Primary and Subjective are never simultaneously ordinary authorities",
        "with no compatibility alias, permissive default, dual mode, precedence rule, or configuration-only authority",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R4_BUDGET_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R4_BUDGET_ANCHORS.items()
    for anchor in anchors
)

R4_BUDGET_STALE = (
    "## RT-1D-R4 P1 Return and activation budget amendment (historical)",
    "the original exact-eight RT-1D-R4 production budget remains executable",
    "the original exact-eight RT-1D-R4 production budget is still executable",
    "the exact-eight RT-1D-R4 production budget remains current",
    "the original exact-eight RT-1D-R4 production budget is authorized",
    "a new generic test, smoke, support, helper, framework, or control-plane file is authorized",
    "both the configuration and cutover-binding validators admit only `primary_only` and `rehearsal`",
    "the cutover binding validator admits only `primary_only` and `rehearsal`",
    "the cutover binding owns the requested mode",
    "the cutover binding carries a requested-mode field",
    "the requested mode is owned by the cutover binding",
    "the requested mode is validated by the cutover binding",
    "Only the existing configuration and cutover tests and smokes may be used",
    "the RT-1D-R4 focused evidence budget is only the existing configuration and cutover tests",
    "wildcard `tests/` authority applies to RT-1D-R4",
    "every `tests/` file is authorized for RT-1D-R4",
    "configuration alone enables Subjective serving",
    "`subjective_only` alone authorizes Subjective serving",
    "`subjective_only` authorizes ordinary Subjective serving by itself",
    "`subjective_only` skips rehearsal and readiness",
    "the private activation owner is a second semantic authority",
    "the private activation owner may import the cutover facade",
    "the private activation owner owns the public binding",
    "the cutover facade may import the private activation owner dynamically",
    "the frozen zero-diff implementation branch may bootstrap RT-1D-R4",
    "RT-1D-R4 implementation may bootstrap from the frozen zero-diff implementation branch",
    "this activation budget amendment requires P8",
    "the activation budget amendment requires a recursive P8",
    "Primary and Subjective may both serve",
    "## RT-1D-R4 P1 Return and activation budget amendment (current)",
    "This architecture-only amendment is the current Lane C transaction",
    "the RT-1D-R4 activation budget amendment is the current Lane C transaction",
    "the activation budget amendment is the current Lane C transaction",
    "activation budget amendment current",
    "activation budget amendment is current",
    "activation budget amendment remains current",
    "PR #828 remains open",
    "PR #828 is unmerged",
    "Draft PR #828",
    "the PR #828 amendment requires P8",
    "the completed activation budget amendment requires a recursive P8",
    "RT-1D-R4 implementation is uniquely next and has started",
    "RT-1D-R4 implementation is uniquely next and complete",
    "RT-1D-R4 implementation may bootstrap from PR #828 head",
    "RT-1D-R4 implementation may bootstrap from `be2218ac7c5ddd3a9f2a9672846101be482dd97b`",
    "RT-1D-R4 implementation may bootstrap from `agent/rt1d-r4-activation-budget-amendment`",
    "RT-1D-R4 implementation may bootstrap from `agent/rt1d-r4-one-authority-activation`",
    "RT-1D-R4 implementation may bootstrap from the amendment branch",
    "RT-1D-R4 implementation may bootstrap from a correction PR head",
    "RT-1D-R4 implementation may bootstrap from this correction PR head",
    "RT-1D-R5 is uniquely next",
    "RT-1D-R5 is next and has started",
    "Subjective MEM is the sole ordinary served memory and Retrieval authority",
)

# PR #828 merged with exact result `9aea56d…`. The amendment section is completed
# authority, RT-1D-R4 implementation is uniquely next and unstarted, and the
# bootstrap is pinned to the independently verified exact resulting main.
R4_RESULT_ANCHORS = {
    path: (
        "## RT-1D-R4 P1 Return and activation budget amendment (completed)",
        "This architecture-only amendment completed in PR #828 from bootstrap "
        "`c291e26f1c20e6479df427054142916dd7df57db`, final reviewed head "
        "`be2218ac7c5ddd3a9f2a9672846101be482dd97b`, and exact resulting main "
        "`9aea56d6d61d69c390bd0c2dc740739ab155d76e`",
        "Its two commits changed exactly the four amendment paths",
        "and it required no P8",
        "The revised RT-1D-R4 authority recorded in the rest of this section was the "
        "accepted RT-1D-R4 architecture authority until the RT-1D-R4 runtime-projection "
        "budget amendment recorded below superseded its exact production/config budget",
        "At that historical point RT-1D-R4 implementation was uniquely next and unstarted, and RT-1D-R5 was unstarted",
        "RT-1D-R4 implementation could then bootstrap only from the independently verified exact PR #828 "
        "resulting main `9aea56d6d61d69c390bd0c2dc740739ab155d76e`, or from a later independently "
        "verified exact current `main` that advances it only by documentation-only "
        "current-authority correction, never from PR #828 head "
        "`be2218ac7c5ddd3a9f2a9672846101be482dd97b`, never from the frozen "
        "`agent/rt1d-r4-one-authority-activation` branch, never from the "
        "`agent/rt1d-r4-activation-budget-amendment` branch, and never from a correction PR head",
        "it never received the amendment and must not be used as a bootstrap now that the amendment has merged",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R4_RESULT_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R4_RESULT_ANCHORS.items()
    for anchor in anchors
)

R4_RESULT_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "and exact resulting main `9aea56d6d61d69c390bd0c2dc740739ab155d76e`",
            "and exact resulting main `8aea56d6d61d69c390bd0c2dc740739ab155d76e`",
            "R4 amendment exact result",
        ),
        (
            "final reviewed head `be2218ac7c5ddd3a9f2a9672846101be482dd97b`",
            "final reviewed head `ce2218ac7c5ddd3a9f2a9672846101be482dd97b`",
            "R4 amendment reviewed head",
        ),
        (
            "Its two commits changed exactly the four amendment paths",
            "Its two commits changed exactly the five amendment paths",
            "R4 amendment path inventory",
        ),
        (
            "and it required no P8",
            "and it required a further P8",
            "R4 amendment result P8 status",
        ),
        (
            "At that historical point RT-1D-R4 implementation was uniquely next and unstarted, and RT-1D-R5 was unstarted",
            "RT-1D-R4 implementation is uniquely next and has started",
            "R4 next-slice state",
        ),
        (
            "could then bootstrap only from the independently verified exact PR #828 resulting main "
            "`9aea56d6d61d69c390bd0c2dc740739ab155d76e`",
            "may bootstrap only from PR #828 head "
            "`be2218ac7c5ddd3a9f2a9672846101be482dd97b`",
            "R4 bootstrap source",
        ),
        (
            "never from the frozen `agent/rt1d-r4-one-authority-activation` branch, never from the "
            "`agent/rt1d-r4-activation-budget-amendment` branch, and never from a correction PR head",
            "or from any convenient branch head",
            "R4 prohibited bootstrap heads",
        ),
    )
)

R4_BUDGET_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "returned at P1 without repository mutation from exact bootstrap main `c291e26f1c20e6479df427054142916dd7df57db`",
            "returned at P1 without repository mutation from exact bootstrap main `d291e26f1c20e6479df427054142916dd7df57db`",
            "R4 amendment bootstrap",
        ),
        (
            "`relaylm/subjective_mem_retrieval_cutover.py` is 688 normally formatted physical lines before R4",
            "`relaylm/subjective_mem_retrieval_cutover.py` is 588 normally formatted physical lines before R4",
            "pre-R4 cutover owner size",
        ),
        (
            "exactly these eleven paths: `relaylm/subjective_mem_retrieval_cutover.py`, "
            "`relaylm/_subjective_mem_retrieval_cutover_activation.py`, `relaylm/config.py`,",
            "exactly these eleven paths: `relaylm/subjective_mem_retrieval_cutover.py`, "
            "`relaylm/config.py`,",
            "private activation owner omitted from budget",
        ),
        (
            "The original exact-eight RT-1D-R4 production budget is superseded and is no longer executable",
            "The original exact-eight RT-1D-R4 production budget remains executable",
            "superseded exact-eight budget",
        ),
        (
            "That zero-diff implementation branch is frozen",
            "That zero-diff implementation branch may be reused as a bootstrap",
            "frozen implementation branch",
        ),
        (
            "The cutover facade remains strictly below 1000 normally formatted physical "
            "lines under the RT-1D-R4 cutover-facade structural exception recorded below",
            "The cutover facade remains below roughly 700 normally formatted physical lines",
            "cutover facade limit",
        ),
        (
            "The new private activation owner remains below roughly 600 normally formatted physical lines",
            "The new private activation owner remains below roughly 1200 normally formatted physical lines",
            "private activation owner limit",
        ),
        (
            "The requested cutover mode is extended exactly to `primary_only`, `rehearsal`, and `subjective_only`",
            "The requested cutover mode is extended exactly to `primary_only` and `rehearsal`",
            "requested mode set",
        ),
        (
            "The requested mode is owned exactly by `SubjectiveMemRetrievalCutoverMode` and "
            "`RelayLMConfig` validation in `relaylm/config.py`, and by `RequestedMode` and "
            "`SubjectiveMemRetrievalCutoverRequest.__post_init__` in "
            "`relaylm/subjective_mem_retrieval_cutover.py`",
            "The requested mode is owned exactly by the cutover binding validator",
            "requested-mode ownership",
        ),
        (
            "the cutover binding carries no requested-mode field",
            "the cutover binding carries the requested-mode field",
            "binding requested-mode field",
        ),
        (
            "existing configuration and cutover tests; "
            "`scripts/relaylm_p0_pipeline_ordering_smoke.py`; and "
            "`scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`",
            "existing configuration and cutover tests; and "
            "`scripts/relaylm_subjective_mem_retrieval_cutover_smoke.py`",
            "pipeline-ordering smoke omitted from focused budget",
        ),
        (
            "existing request-path tests; reader-seam and offload tests; "
            "pipeline-ordering tests; RelayCTX tests; Subjective selection and usage-ledger tests;",
            "existing configuration and cutover tests only;",
            "narrowed focused evidence budget",
        ),
        (
            "Configuration alone never enables Subjective serving.",
            "Configuration alone enables Subjective serving.",
            "configuration serving authority",
        ),
        (
            "the private activation owner is not a second semantic authority",
            "the private activation owner is a second semantic authority",
            "private owner semantic authority",
        ),
    )
)

# RT-1D-R4 returned at P1 a second time: ordinary Subjective serving has no
# production exact-source acquisition owner and no distinct ordinary live-projection
# root. The exact-eleven budget is superseded by an exact-twelve budget carrying one
# new private runtime-projection owner and one new configuration field.
R4_RUNTIME_PROJECTION_ANCHORS = {
    path: (
        "## RT-1D-R4 runtime-projection budget amendment",
        "RT-1D-R4 one-authority activation returned at P1 a second time, without "
        "repository mutation, from exact bootstrap main "
        "`dc33626fe66ec79ee1d1a5cfc8a5aed23342032c`",
        "Both zero-diff RT-1D-R4 implementation branches, "
        "`agent/rt1d-r4-one-authority-activation` and "
        "`agent/rt1d-r4-one-authority-activation-implementation`, are frozen and must "
        "never be reused as a bootstrap",
        "no production exact-source acquisition owner exists",
        "production code does not construct that source, and existing construction is "
        "test and rehearsal evidence only",
        "no ordinary live-projection deployment authority exists",
        "Current configuration carries the durable cutover store root and binding tuple "
        "but no distinct ordinary projection root",
        "the projection store accepts a bundle only through a trusted read against both "
        "an exact fixed source and an explicit projection root",
        "the RT-1D-R3 root is rehearsal-exclusive and disposable",
        "Reusing the durable cutover store as the disposable ordinary projection root "
        "would conflate two authorities and violate the accepted store separation",
        "Ordinary Subjective serving cannot be safely implemented by laundering source "
        "acquisition into selection, the cutover facade, the activation mechanics owner, "
        "Primary owners, or RelayCTX",
        "Exactly one additional private production owner is authorized: "
        "`relaylm/_subjective_mem_retrieval_runtime_projection.py`",
        "acquire one exact current `SubjectiveMemRetrievalProjectionSource` by "
        "orchestrating the existing canonical workspace, Evidence-store, selector, "
        "receipt, and authorization owners without reimplementing their semantics",
        "install or exact-verify one disposable live projection bundle in a dedicated "
        "projection root through the existing projection store",
        "trusted-read that bundle against the same exact source",
        "fail closed on missing, foreign, stale, mixed, corrupt, unsafe, unreadable, "
        "incomplete, or source-disagreeing state",
        "it must not become a second current selector, receipt validator, authorization "
        "evaluator, projection builder, projection store, selection owner, usage ledger, "
        "or cutover authority",
        "the ordinary route and cutover facade depend on "
        "`relaylm/_subjective_mem_retrieval_runtime_projection.py`, which depends on the "
        "existing canonical source authorities, "
        "`relaylm/subjective_mem_retrieval_projection.py`, and "
        "`relaylm/subjective_mem_retrieval_projection_store.py`",
        "No reverse import is allowed.",
        "The existing projection builder and store and the canonical and lifecycle "
        "owners remain byte-identical.",
        "Exactly one configuration field is authorized: "
        "`subjective_mem_retrieval_projection_root`",
        "It must be an absolute, normalized, non-symlinked directory and must be "
        "distinct from `subjective_mem_retrieval_cutover_store_root`, "
        "`evidence_data_root`, `subjective_mem_workspace_root`, and the RT-1D-R3 "
        "rehearsal root",
        "`subjective_only` requires the complete existing cutover tuple and this "
        "projection root, and configuration still grants no serving authority",
        "twelve paths total",
        "`relaylm/_subjective_mem_retrieval_runtime_projection.py`, `relaylm/config.py`,",
        "The prior exact-eleven RT-1D-R4 production/config budget is superseded and is "
        "no longer executable",
        "No thirteenth RT-1D-R4 production or configuration path, schema owner, "
        "registry, workflow, helper, generic smoke, control plane, fallback, or "
        "compatibility layer is authorized",
        "Before transfer intent, source and projection preparation may fail with Primary "
        "still serving",
        "After transfer intent, every source, generation, manifest, row-population, "
        "readiness, and binding disagreement fails closed with neither authority "
        "serving, and recovery remains forward-only",
        "The final transfer receipt authorizes only the exact generation and source "
        "state finalized atomically at activation",
        "Source drift after activation never silently rebinds, never falls back, and "
        "never restores Primary",
        "the new private runtime-projection owner remains below roughly 600 normally "
        "formatted physical lines",
        "physical-line compression, wrapper splitting, dynamic import, hidden generated "
        "source, and responsibility laundering are prohibited",
        "This RT-1D-R4 runtime-projection budget amendment is documentation and "
        "current-boundary only",
        "and it requires no P8. At that historical point RT-1D-R4 implementation was "
        "uniquely next and unstarted, RT-1D-R5 was unstarted",
        "RT-1D-R4 implementation could then bootstrap only from the independently verified "
        "exact resulting `main` of this runtime-projection budget amendment, never from "
        "either frozen RT-1D-R4 implementation branch, never from "
        "`agent/rt1d-r4-runtime-projection-budget-amendment`, and never from this "
        "amendment's PR head",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R4_RUNTIME_PROJECTION_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R4_RUNTIME_PROJECTION_ANCHORS.items()
    for anchor in anchors
)

R4_RUNTIME_PROJECTION_STALE = (
    "the prior exact-eleven RT-1D-R4 production/config budget remains executable",
    "the prior exact-eleven RT-1D-R4 production/config budget is still executable",
    "the exact-eleven RT-1D-R4 production/config budget remains current",
    "the exact-eleven RT-1D-R4 production/config budget is authorized",
    "No twelfth RT-1D-R4 production path is authorized.",
    "A thirteenth RT-1D-R4 production path is authorized.",
    "RT-1D-R4 requires no runtime-projection owner",
    "no runtime-projection owner is required",
    "no ordinary exact-source acquisition owner is required",
    "the ordinary route may acquire the Subjective source without the runtime-projection owner",
    "source acquisition may be added to the selection owner",
    "source acquisition may be added to the cutover facade",
    "source acquisition may be added to the activation mechanics owner",
    "source acquisition may be added to a Primary owner",
    "the runtime-projection owner is a second semantic authority",
    "the runtime-projection owner may import the cutover facade",
    "the runtime-projection owner reimplements the canonical selector, receipt, or authorization semantics",
    "RT-1D-R4 implementation may bootstrap from `agent/rt1d-r4-one-authority-activation-implementation`",
    "RT-1D-R4 implementation may bootstrap from `agent/rt1d-r4-runtime-projection-budget-amendment`",
    "either frozen RT-1D-R4 implementation branch may bootstrap RT-1D-R4",
    "a frozen RT-1D-R4 implementation branch may be reused as a bootstrap",
    "the durable cutover store root is the ordinary projection root",
    "`subjective_mem_retrieval_cutover_store_root` may be reused as the ordinary projection root",
    "the RT-1D-R3 rehearsal root is the ordinary projection root",
    "the rehearsal projection root may be reused for ordinary serving",
    "`subjective_mem_retrieval_projection_root` alone authorizes Subjective serving",
    "the projection root grants Subjective serving authority",
    "configuration and the projection root together authorize Subjective serving",
    "the projection store accepts a bundle without an exact fixed source",
    "a source-less trusted projection read is allowed",
    "a stale trusted projection read is allowed",
    "a stale projection generation may be trusted",
    "source drift after activation silently rebinds the generation",
    "source drift after activation restores Primary",
    "Primary fallback is allowed after transfer intent",
    "Primary falls back after transfer intent",
    "the RT-1D-R4 runtime-projection budget amendment requires P8",
    "RT-1D-R5 has started",
    "RT-1D-R5 implementation has started",
)

R4_RUNTIME_PROJECTION_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "Exactly one additional private production owner is authorized: "
            "`relaylm/_subjective_mem_retrieval_runtime_projection.py`",
            "No additional private production owner is authorized",
            "runtime-projection owner authorization",
        ),
        (
            "twelve paths total",
            "eleven paths total",
            "R4 exact-twelve budget",
        ),
        (
            "The prior exact-eleven RT-1D-R4 production/config budget is superseded and "
            "is no longer executable",
            "The prior exact-eleven RT-1D-R4 production/config budget remains executable",
            "superseded exact-eleven budget",
        ),
        (
            "Exactly one configuration field is authorized: "
            "`subjective_mem_retrieval_projection_root`",
            "No new configuration field is authorized",
            "projection-root configuration field",
        ),
        (
            "distinct from `subjective_mem_retrieval_cutover_store_root`, "
            "`evidence_data_root`, `subjective_mem_workspace_root`, and the RT-1D-R3 "
            "rehearsal root",
            "the durable cutover store root is the ordinary projection root",
            "projection-root separation",
        ),
        (
            "No reverse import is allowed.",
            "A reverse import is allowed.",
            "runtime-projection dependency direction",
        ),
        (
            "Source drift after activation never silently rebinds, never falls back, and "
            "never restores Primary",
            "source drift after activation silently rebinds the generation",
            "post-activation source drift",
        ),
        (
            "After transfer intent, every source, generation, manifest, row-population, "
            "readiness, and binding disagreement fails closed with neither authority "
            "serving, and recovery remains forward-only",
            "Primary falls back after transfer intent",
            "post-intent fail-closed",
        ),
        (
            "the new private runtime-projection owner remains below roughly 600 normally "
            "formatted physical lines",
            "the new private runtime-projection owner remains below roughly 1800 "
            "normally formatted physical lines",
            "runtime-projection owner limit",
        ),
        (
            "Both zero-diff RT-1D-R4 implementation branches, "
            "`agent/rt1d-r4-one-authority-activation` and "
            "`agent/rt1d-r4-one-authority-activation-implementation`, are frozen and "
            "must never be reused as a bootstrap",
            "either frozen RT-1D-R4 implementation branch may bootstrap RT-1D-R4",
            "frozen R4 implementation branches",
        ),
        (
            "no production exact-source acquisition owner exists",
            "a production exact-source acquisition owner exists",
            "exact-source acquisition blocker",
        ),
        (
            "no ordinary live-projection deployment authority exists",
            "an ordinary live-projection deployment authority exists",
            "ordinary projection-root blocker",
        ),
        (
            "`subjective_only` requires the complete existing cutover tuple and this "
            "projection root, and configuration still grants no serving authority",
            "the projection root grants Subjective serving authority",
            "configuration-only serving",
        ),
        (
            "RT-1D-R4 implementation could then bootstrap only from the independently verified "
            "exact resulting `main` of this runtime-projection budget amendment",
            "RT-1D-R4 implementation may bootstrap from "
            "`agent/rt1d-r4-runtime-projection-budget-amendment`",
            "R4 runtime-projection bootstrap source",
        ),
    )
)

# RT-1D-R4 returned at P1 a third time. The complete facade surface measures 966
# normally formatted physical lines after the maximum authorized extraction, so the
# roughly-700 facade gate is replaced by one measured, RT-1D-R4-only strict
# below-1000 exception. The exact-twelve budget and every other gate are unchanged.
R4_FACADE_ANCHORS = {
    path: (
        "## RT-1D-R4 cutover-facade structural budget amendment",
        "RT-1D-R4 one-authority activation returned at P1 a third time, without "
        "repository mutation, from exact bootstrap main "
        "`afe18c86de7bbf7d5605ccc74f1fcdd32b68de65`",
        "The authorized implementation branch "
        "`agent/rt1d-r4-exact-twelve-activation-implementation` remains identical to "
        "that exact main, 0 ahead / 0 behind",
        "That branch is frozen and must never be reused as a bootstrap or as "
        "implementation history",
        "The current cutover facade `relaylm/subjective_mem_retrieval_cutover.py` is "
        "688 normally formatted physical lines",
        "the durable state list, the durable record schema and field tuple, chain "
        "reconstruction, chain validation, exact record and predecessor binding, and "
        "the content-free identity predicates, 136 physical lines",
        "the facade stands at 566 lines",
        "projects to 966 normally formatted physical lines: 278 lines above the "
        "current file and 266 lines above the earlier roughly-700 gate",
        "Further extraction sufficient to force the facade below roughly 700 lines "
        "would move the public cutover contracts, the exact reader and writer "
        "authority decisions, binding and readiness validation, or validation of the "
        "private owner's returned content-free result into another semantic owner",
        "The accepted decision is one explicit, measured, RT-1D-R4-only structural "
        "exception rather than a thirteenth production path or a second semantic "
        "evaluator",
        "The exact-twelve RT-1D-R4 production/config budget recorded above is "
        "unchanged, and no thirteenth RT-1D-R4 production or configuration path, "
        "schema owner, registry, workflow, helper, generic smoke, control plane, "
        "fallback, or compatibility layer is authorized",
        "The RT-1D-R4 focused evidence budget is unchanged, there is no wildcard "
        "`tests/` or `scripts/` authority",
        "The final normally formatted RT-1D-R4 cutover facade must remain strictly "
        "below 1000 physical lines, against the measured 966-line projection",
        "This bounded RT-1D-R4-only exception supersedes the earlier roughly-700 "
        "cutover-facade gate for RT-1D-R4 alone. It is not a repository-wide precedent "
        "and it is not permission for physical-line compression.",
        "`relaylm/_subjective_mem_retrieval_cutover_activation.py` and "
        "`relaylm/_subjective_mem_retrieval_runtime_projection.py` each remain below "
        "roughly 600 normally formatted physical lines, and every new or materially "
        "changed orchestration remains at or below roughly 80 normally formatted "
        "physical lines",
        "Physical-line compression, wrapper splitting, hidden generated source, "
        "dynamic import, duplicate semantic validation, second authority evaluation, "
        "and responsibility laundering remain prohibited",
        "If the final facade reaches 1000 physical lines, either private owner exceeds "
        "its gate, or any orchestration exceeds its gate, the implementation returns "
        "to P1 without broadening authority",
        "Every accepted RT-1D-R4 semantic rule is unchanged",
        "This RT-1D-R4 cutover-facade structural budget amendment is documentation and "
        "current-boundary only",
        "RT-1D-R4 implementation could then restart only from a fresh branch created from the "
        "independently verified exact resulting `main` of this cutover-facade "
        "structural budget amendment",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R4_FACADE_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R4_FACADE_ANCHORS.items()
    for anchor in anchors
)

R4_FACADE_STALE = (
    "The cutover facade remains below roughly 700 normally formatted physical lines",
    "the roughly-700 cutover-facade gate remains executable",
    "the roughly-700 cutover-facade gate is still executable",
    "the RT-1D-R4 cutover facade must remain below roughly 700 physical lines",
    "the cutover facade gate remains roughly 700 lines",
    "a thirteenth RT-1D-R4 production path is authorized",
    "A thirteenth RT-1D-R4 production or configuration path is authorized.",
    "a second semantic cutover evaluator is authorized",
    "a second public semantic cutover owner is authorized",
    "the cutover facade may reach 1000 physical lines",
    "the cutover facade may exceed 1000 physical lines",
    "the RT-1D-R4 cutover facade limit is 1200 physical lines",
    "the below-1000 facade exception is a repository-wide precedent",
    "the below-1000 facade exception permits physical-line compression",
    "the private activation owner may exceed roughly 600 normally formatted physical lines",
    "the private runtime-projection owner may exceed roughly 600 normally formatted physical lines",
    "an orchestration may exceed roughly 80 normally formatted physical lines",
    "RT-1D-R4 implementation may bootstrap from `agent/rt1d-r4-exact-twelve-activation-implementation`",
    "the exact-twelve activation implementation branch may be reused as a bootstrap",
    "the RT-1D-R4 cutover-facade structural budget amendment requires P8",
    "RT-1D-R5 retirement has started",
)

R4_FACADE_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "The final normally formatted RT-1D-R4 cutover facade must remain strictly "
            "below 1000 physical lines, against the measured 966-line projection",
            "the cutover facade may exceed 1000 physical lines",
            "R4 facade strict limit",
        ),
        (
            "The current cutover facade `relaylm/subjective_mem_retrieval_cutover.py` is "
            "688 normally formatted physical lines",
            "The current cutover facade `relaylm/subjective_mem_retrieval_cutover.py` is "
            "588 normally formatted physical lines",
            "measured facade baseline",
        ),
        (
            "the facade stands at 566 lines",
            "the facade stands at 466 lines",
            "measured post-extraction facade",
        ),
        (
            "projects to 966 normally formatted physical lines: 278 lines above the "
            "current file and 266 lines above the earlier roughly-700 gate",
            "projects to 690 normally formatted physical lines",
            "measured facade projection",
        ),
        (
            "rather than a thirteenth production path or a second semantic evaluator",
            "a second semantic cutover evaluator is authorized",
            "thirteenth path or second evaluator",
        ),
        (
            "This bounded RT-1D-R4-only exception supersedes the earlier roughly-700 "
            "cutover-facade gate for RT-1D-R4 alone. It is not a repository-wide precedent "
            "and it is not permission for physical-line compression.",
            "the below-1000 facade exception is a repository-wide precedent",
            "R4-only exception scope",
        ),
        (
            "each remain below roughly 600 normally formatted physical lines, and every "
            "new or materially changed orchestration remains at or below roughly 80 "
            "normally formatted physical lines",
            "the private activation owner may exceed roughly 600 normally formatted physical lines",
            "private owner and orchestration gates",
        ),
        (
            "That branch is frozen and must never be reused as a bootstrap or as "
            "implementation history",
            "the exact-twelve activation implementation branch may be reused as a bootstrap",
            "frozen exact-twelve branch",
        ),
        (
            "RT-1D-R4 implementation could then restart only from a fresh branch created from the "
            "independently verified exact resulting `main` of this cutover-facade "
            "structural budget amendment",
            "RT-1D-R4 implementation may bootstrap from "
            "`agent/rt1d-r4-exact-twelve-activation-implementation`",
            "R4 restart bootstrap source",
        ),
    )
)

R4_READINESS_REPLAY_ANCHORS = {
    path: (
        "## RT-1D-R4 readiness/replay authority amendment",
        "Draft PR #832 reached final head "
        "`737406d2f32b5d270177367f3b760af2eb4863a6` with exactly the authorized "
        "twelve production/config and existing focused-evidence paths, +2965/-257, "
        "three normal commits, exactly one execution receipt, and clean exact-head CI",
        "PR #832 is closed unmerged and frozen",
        "no commit, cherry-pick, merge, rebase, or branch history from it may seed "
        "later implementation",
        "no readiness-carriage seam exists inside the exact-twelve RT-1D-R4 budget",
        "the RT-1D-R3 readiness proof is factory-only, its identity binds a "
        "characterization digest derived from live per-request Primary served metrics "
        "and from the rehearsal's own request identity",
        "`rehearsal` and `subjective_only` are mutually exclusive configurations",
        "response-lost usage replay is bounded by the wall clock",
        "### RT-1D-R4 architecture decision A",
        "The accepted design is a durable handoff through the existing cutover "
        "authority chain, not transport or reconstruction of the factory-only "
        "readiness object",
        "An exact `rehearsal` deployment may run the existing RT-1D-R3 rehearsal "
        "coordinator in the ordinary managed pipeline after the Primary served metrics "
        "for that request exist and while Primary remains the sole served authority",
        "the facade may create-or-verify exactly the durable cutover prefix ending at "
        "`rehearsal_ready`",
        "That write must be idempotent, must bind the complete existing cutover "
        "binding including `readiness_id`",
        "must never advance to `transfer_intent`, either Primary fence, exact "
        "Subjective generation binding, Subjective-reader enablement, or the finalized "
        "transfer receipt while the requested mode is `rehearsal`",
        "The readiness proof object itself remains factory-only and non-serializable; "
        "it is not added to configuration, request payload, API, control plane, or a "
        "new durable record kind.",
        "A later `subjective_only` deployment may activate only from an exact durable "
        "`rehearsal_ready` or later supported state",
        "It must not mint readiness, accept configuration alone as readiness, or "
        "receive a live readiness proof through the ordinary request path.",
        "Exactly one configuration field is added: "
        "`subjective_mem_retrieval_rehearsal_projection_root`.",
        "It is required only for `rehearsal`; it is prohibited for `primary_only` and "
        "`subjective_only`",
        "distinct from `subjective_mem_retrieval_projection_root`, the cutover store "
        "root, the Evidence root, the Subjective workspace root, and every other "
        "operational root",
        "The existing RT-1D-R3 rehearsal owner "
        "`relaylm/subjective_mem_retrieval_rehearsal.py` and the characterization owner "
        "`relaylm/subjective_mem_retrieval_characterization.py` remain byte-identical.",
        "No new proof schema, registry, helper, control plane, store, journal, or "
        "authority owner is authorized.",
        "### RT-1D-R4 architecture decision B",
        "The stable usage slot remains authoritative and the first finalized event owns "
        "the occurrence time.",
        "First finalization derives one event with the real canonical occurrence time "
        "and commits the exact event and result pair atomically.",
        "Replay resolves the stable result record first, obtains the original "
        "`usage_event_id` from that result, reads the original event, validates both "
        "stored bodies exactly, and requires the stored pair to be internally exact.",
        "projection generation, request input digest, request correlation digest, "
        "selection digest, row digest, memory identity, memory revision, event kind, "
        "idempotency-key digest, and policy revision",
        "The newly supplied wall-clock occurrence is the sole field not compared "
        "against the original event",
        "returns `duplicate_finalized` without a second durable pair",
        "fails closed, and is never repaired or overwritten",
        "Coverage must include an explicit different-second replay proving exactly one "
        "durable pair, plus negative true-disagreement cases. A timing-dependent "
        "same-second replay test is insufficient.",
        "The exact-twelve RT-1D-R4 production/config path budget is unchanged",
        "No thirteenth RT-1D-R4 production or configuration path is authorized by this "
        "amendment.",
        "The RT-1D-R4 structural gates are unchanged",
        "The RT-1D-R4 focused evidence budget is unchanged",
        "This RT-1D-R4 readiness/replay authority amendment is documentation and "
        "current-boundary only",
        "RT-1D-R4 implementation then restarted exactly as this amendment required, from a "
        "fresh branch created from the independently verified exact resulting `main` of "
        "this readiness/replay "
        "authority amendment",
        "Mandatory RT-1D-R4 P8 remains required after the replacement implementation "
        "merges and before RT-1D-R5 may start.",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R4_READINESS_REPLAY_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R4_READINESS_REPLAY_ANCHORS.items()
    for anchor in anchors
)

R4_READINESS_REPLAY_STALE = (
    "the RT-1D-R3 readiness proof may be carried through configuration",
    "configuration alone is accepted as RT-1D-R4 readiness",
    "the readiness proof may be serialized into a durable record kind",
    "a new durable readiness record kind is authorized",
    "the readiness proof may be supplied through the ordinary request path",
    "a `subjective_only` deployment may mint readiness",
    "a `subjective_only` deployment may run the RT-1D-R3 rehearsal coordinator",
    "the RT-1D-R4 rehearsal projection root may equal the ordinary projection root",
    "`subjective_mem_retrieval_rehearsal_projection_root` is required for `subjective_only`",
    "`subjective_mem_retrieval_rehearsal_projection_root` is permitted for `primary_only`",
    "the `rehearsal` mode may advance to `transfer_intent`",
    "the `rehearsal` mode may finalize the transfer receipt",
    "no durable RT-1D-R3-to-R4 readiness handoff is authorized",
    "the RT-1D-R3 rehearsal owner may change",
    "response-lost replay may create a second durable pair",
    "the replay compares the wall-clock occurrence against the original event",
    "a same-second replay test is sufficient",
    "a divergent usage slot may be repaired",
    "a divergent usage slot may be overwritten",
    "the RT-1D-R4 readiness/replay authority amendment requires P8",
    "RT-1D-R4 implementation may bootstrap from "
    "`agent/rt1d-r4-strict-below-1000-activation-implementation`",
    "PR #832 may be reused as implementation history",
    "PR #832 merged",
    "PR #832 remains open",
    "a thirteenth RT-1D-R4 production or configuration path is authorized by this amendment",
)

R4_READINESS_REPLAY_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "PR #832 is closed unmerged and frozen",
            "PR #832 merged",
            "PR #832 frozen unmerged",
        ),
        (
            "Draft PR #832 reached final head "
            "`737406d2f32b5d270177367f3b760af2eb4863a6`",
            "Draft PR #832 reached final head "
            "`f48a28763b344be581f6e04a86703b0b5b2251c1`",
            "PR #832 exact frozen head",
        ),
        (
            "the facade may create-or-verify exactly the durable cutover prefix ending at "
            "`rehearsal_ready`",
            "the `rehearsal` mode may advance to `transfer_intent`",
            "rehearsal durable prefix bound",
        ),
        (
            "It must not mint readiness, accept configuration alone as readiness, or "
            "receive a live readiness proof through the ordinary request path.",
            "configuration alone is accepted as RT-1D-R4 readiness",
            "subjective_only readiness source",
        ),
        (
            "The readiness proof object itself remains factory-only and non-serializable; "
            "it is not added to configuration, request payload, API, control plane, or a "
            "new durable record kind.",
            "the readiness proof may be serialized into a durable record kind",
            "readiness proof transport",
        ),
        (
            "It is required only for `rehearsal`; it is prohibited for `primary_only` and "
            "`subjective_only`",
            "`subjective_mem_retrieval_rehearsal_projection_root` is required for "
            "`subjective_only`",
            "rehearsal projection root mode",
        ),
        (
            "distinct from `subjective_mem_retrieval_projection_root`, the cutover store "
            "root, the Evidence root, the Subjective workspace root, and every other "
            "operational root",
            "the RT-1D-R4 rehearsal projection root may equal the ordinary projection root",
            "rehearsal projection root distinctness",
        ),
        (
            "The newly supplied wall-clock occurrence is the sole field not compared "
            "against the original event",
            "the replay compares the wall-clock occurrence against the original event",
            "cross-time replay comparison",
        ),
        (
            "returns `duplicate_finalized` without a second durable pair",
            "response-lost replay may create a second durable pair",
            "replay durable pair count",
        ),
        (
            "fails closed, and is never repaired or overwritten",
            "a divergent usage slot may be repaired",
            "divergent slot handling",
        ),
        (
            "Coverage must include an explicit different-second replay proving exactly one "
            "durable pair, plus negative true-disagreement cases. A timing-dependent "
            "same-second replay test is insufficient.",
            "a same-second replay test is sufficient",
            "cross-time replay coverage",
        ),
        (
            "No thirteenth RT-1D-R4 production or configuration path is authorized by this "
            "amendment.",
            "a thirteenth RT-1D-R4 production or configuration path is authorized by this "
            "amendment",
            "readiness/replay thirteenth path",
        ),
        (
            "This RT-1D-R4 readiness/replay authority amendment is documentation and "
            "current-boundary only",
            "the RT-1D-R4 readiness/replay authority amendment requires P8",
            "readiness/replay amendment P8 status",
        ),
        (
            "RT-1D-R4 implementation then restarted exactly as this amendment required, from a "
            "fresh branch created from the independently verified exact resulting `main` of "
            "this readiness/replay "
            "authority amendment",
            "RT-1D-R4 implementation may bootstrap from "
            "`agent/rt1d-r4-strict-below-1000-activation-implementation`",
            "readiness/replay restart bootstrap source",
        ),
    )
)

# RT-1D-R4 one-authority activation is implemented and merged in PR #834 with exact
# resulting main `53839b6…`. The current incomplete gate is this mandatory R4 P8
# current-authority synchronization, which itself requires no recursive P8, and
# RT-1D-R5 stays unstarted until this P8 result is independently verified.
R4_COMPLETION_ANCHORS = {
    path: (
        "## RT-1D-R4 completion and mandatory P8 (completed)",
        "RT-1D-R4 one-authority activation implementation completed in PR #834 from exact "
        "bootstrap main `5273b3ba214e9ba7730fcc4b7683dfc96eeafdb7`, final reviewed head "
        "`d15daeec270ba453940bc10dad924a5df93dfeef`, and exact resulting main "
        "`53839b6c349e47a436a885419d699b52142adc86`",
        "Its thirteen normal forward commits on one lineage changed exactly 22 paths, "
        "+2147/-258",
        "no commit, patch, tree, or branch history from frozen PR #832 or PR #833 was reused",
        "It carried exactly one execution receipt, was accepted at cumulative P5/P6, and its "
        "normalized failure state is none with `p6_stop` false.",
        "RT-1D-R4 one-authority activation is therefore implemented and merged, and it is no "
        "longer an unstarted or uniquely next slice.",
        "eleven paths changed and `relaylm/subjective_mem_retrieval_selection.py` remained "
        "byte-identical by design",
        "admission is proven at the usage-ledger owner boundary rather than asserted at "
        "selection",
        "The budget therefore stands at exactly 12 of 12 and no thirteenth RT-1D-R4 production "
        "or configuration path was taken.",
        "The bounded P5 smoke-carriage correction changed exactly seven existing Primary "
        "direct-recall smoke scripts.",
        "12 existing call sites across 7 files were corrected to construct the exact immutable "
        "decision through the canonical owner instead of weakening the production fence to make "
        "a missing decision imply `primary_only`",
        "That correction changed no production or configuration path.",
        "No new test, smoke, helper, support, framework, registry, or control-plane file was "
        "created",
        "`relaylm/subjective_mem_retrieval_cutover.py` is 998 physical lines against the "
        "strictly-below-1000 RT-1D-R4-only exception",
        "`relaylm/_subjective_mem_retrieval_runtime_projection.py` is 481 and "
        "`relaylm/_subjective_mem_retrieval_cutover_activation.py` is 314 against the "
        "roughly-600 private-owner gate",
        "`run_managed_chat_pipeline` at 79, `run_relaymem_retrieval_stage` at 74, and "
        "`handle_managed_chat_completion` at 64 are each at or below roughly 80",
        "The full Python 3.12 suite passed 1089 tests with 0 failures and 1 warning at the "
        "final exact head, and no RT-1D-R5 retirement behavior was introduced.",
        "Ordinary serving is now exactly one-authority.",
        "A deployment whose durable chain has not reached an exact finalized transfer receipt "
        "continues to serve Primary MEM alone.",
        "Only an exact finalized activation, bound to matching durable state, may serve "
        "Subjective alone.",
        "`neither` is the bounded fenced transition state between the Primary reader fence and "
        "that finalized receipt",
        "There is no dual serving, no precedence, no empty-result fallback, no stale-projection "
        "fallback, and no Primary fallback in either direction",
        "so Primary MEM is not universally the sole ordinary served memory and Retrieval "
        "authority once an exact finalized activation exists",
        "The mandatory RT-1D-R4 P8 current-authority synchronization completed in merged "
        "PR #835 from bootstrap `53839b6c349e47a436a885419d699b52142adc86`, reviewed head "
        "`1299084bb5256c6638925b518291c22ecd3a4178`, and exact resulting main "
        "`c623898fa8c2ba0a7c7151a912a940295829dda5`.",
        "Its cumulative scope was exactly the four authority paths, +360/-61, in two normal "
        "branch commits carrying exactly one execution receipt, its cumulative P5/P6 was "
        "accepted clean, and the Ready-event Agent execution safety run was green before the "
        "expected-head-protected merge.",
        "and it required no recursive P8",
        "PR #835 is merged and completed, not open, current, or incomplete, and RT-1D-R4 "
        "implementation and its mandatory P8 are both complete.",
        "This transaction is the bounded RT-1D-R4 P8 result/current-authority correction that "
        "records that merged PR #835 result.",
        "The merged P8 text necessarily still carried open-transaction present tense, so this "
        "correction replaces it with the exact completed result.",
        "It is documentation and current-boundary only, changes only the same four authority "
        "paths, introduces no runtime, serving, or retirement behavior, and requires no P8.",
        "RT-1D-R5 immediate retirement was unstarted during that correction and introduced "
        "no retirement behavior.",
        "That correction merged as exact resulting `main` "
        "`71a334f8eab873775f378ee246daa0ca75b2ba71`, its result was independently verified, "
        "and RT-1D-R5 then became uniquely next.",
        "never from PR #834 head `d15daeec270ba453940bc10dad924a5df93dfeef`, never from "
        "PR #835 head `1299084bb5256c6638925b518291c22ecd3a4178`, never from PR #836 head "
        "`cf964cf9b530c85656f25958f261e47038247413`, and never from any frozen RT-1D-R4 "
        "implementation or amendment branch",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R4_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R4_COMPLETION_ANCHORS.items()
    for anchor in anchors
)

R4_COMPLETION_STALE = (
    "RT-1D-R4 implementation is unstarted",
    "RT-1D-R4 implementation remains unstarted",
    "RT-1D-R4 one-authority activation is unstarted",
    "RT-1D-R4 one-authority activation remains unstarted",
    "RT-1D-R4 remains unstarted",
    "RT-1D-R4 implementation is uniquely next",
    "RT-1D-R4 is uniquely next",
    "RT-1D-R4 implementation has not started",
    "Draft PR #834",
    "PR #834 remains open",
    "PR #834 is unmerged",
    "PR #834 remains Draft",
    "PR #834 is closed unmerged",
    "PR #834 returned at P1 without merging",
    "the exact RT-1D-R4 reviewed implementation head is unknown",
    "the exact RT-1D-R4 implementation result is unknown",
    "a thirteenth RT-1D-R4 production or configuration path was taken",
    "the exact-twelve RT-1D-R4 production/config budget was exceeded",
    "the P5 smoke-carriage correction changed a production path",
    "a missing Primary reader decision implies `primary_only`",
    "Primary MEM is universally the sole ordinary served memory and Retrieval authority",
    "Primary MEM remains the sole ordinary served memory and Retrieval authority after a "
    "finalized activation",
    "dual serving is permitted",
    "Primary and Subjective may both serve ordinary requests",
    "Primary fallback is permitted after a finalized activation",
    "an empty Subjective result falls back to Primary",
    "`neither` permits Primary fallback",
    "the mandatory RT-1D-R4 P8 requires another P8",
    "this RT-1D-R4 P8 requires a recursive P8",
    "the mandatory RT-1D-R4 P8 is complete",
    "the mandatory RT-1D-R4 P8 is not required",
    "RT-1D-R5 immediate retirement has started",
    "RT-1D-R5 retirement is complete",
    "RT-1D-R5 is uniquely next before the mandatory RT-1D-R4 P8 result is verified",
    "RT-1D-R5 may bootstrap from PR #834 head",
    "RT-1D-R5 may bootstrap from `d15daeec270ba453940bc10dad924a5df93dfeef`",
    "RT-1D-R5 may bootstrap from this P8 PR head",
    "still-open PR #835",
    "PR #835 remains open",
    "PR #835 is unmerged",
    "PR #835 is the current incomplete RT-1D-R4 gate",
    "the current incomplete RT-1D-R4 gate",
    "Draft PR #835",
    "the mandatory RT-1D-R4 P8 awaits merge",
    "the mandatory RT-1D-R4 P8 awaits resulting-main verification",
    "the exact RT-1D-R4 P8 resulting main is unknown",
    "the exact RT-1D-R4 P8 reviewed head is unknown",
    "the mandatory RT-1D-R4 P8 is incomplete",
    "RT-1D-R4 implementation and its mandatory P8 are incomplete",
    "the RT-1D-R4 P8 result/current-authority correction requires P8",
    "RT-1D-R5 may bootstrap from PR #835 head",
    "RT-1D-R5 may bootstrap from `1299084bb5256c6638925b518291c22ecd3a4178`",
    "RT-1D-R5 may bootstrap from a frozen RT-1D-R4 branch",
    "RT-1D-R5 has already started",
    "RT-1D-R5 retirement has completed",
)

R4_COMPLETION_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "exact resulting main `53839b6c349e47a436a885419d699b52142adc86`",
            "exact resulting main `63839b6c349e47a436a885419d699b52142adc86`",
            "R4 exact resulting main",
        ),
        (
            "final reviewed head `d15daeec270ba453940bc10dad924a5df93dfeef`",
            "final reviewed head `e15daeec270ba453940bc10dad924a5df93dfeef`",
            "R4 reviewed implementation head",
        ),
        (
            "Its thirteen normal forward commits on one lineage changed exactly 22 paths, "
            "+2147/-258",
            "Its twelve normal forward commits on one lineage changed exactly 21 paths, "
            "+2147/-258",
            "R4 implementation cumulative scope",
        ),
        (
            "RT-1D-R4 one-authority activation is therefore implemented and merged, and it is "
            "no longer an unstarted or uniquely next slice.",
            "RT-1D-R4 implementation is unstarted",
            "R4 merged implementation state",
        ),
        (
            "eleven paths changed and `relaylm/subjective_mem_retrieval_selection.py` remained "
            "byte-identical by design",
            "twelve paths changed and `relaylm/subjective_mem_retrieval_selection.py` was "
            "modified",
            "R4 selection byte identity",
        ),
        (
            "The budget therefore stands at exactly 12 of 12 and no thirteenth RT-1D-R4 "
            "production or configuration path was taken.",
            "a thirteenth RT-1D-R4 production or configuration path was taken",
            "R4 final path budget",
        ),
        (
            "That correction changed no production or configuration path.",
            "the P5 smoke-carriage correction changed a production path",
            "P5 correction boundary",
        ),
        (
            "instead of weakening the production fence to make a missing decision imply "
            "`primary_only`",
            "because a missing Primary reader decision implies `primary_only`",
            "P5 correction fence direction",
        ),
        (
            "`relaylm/subjective_mem_retrieval_cutover.py` is 998 physical lines against the "
            "strictly-below-1000 RT-1D-R4-only exception",
            "`relaylm/subjective_mem_retrieval_cutover.py` is 1002 physical lines against the "
            "strictly-below-1000 RT-1D-R4-only exception",
            "R4 facade final measurement",
        ),
        (
            "The full Python 3.12 suite passed 1089 tests with 0 failures and 1 warning at the "
            "final exact head",
            "The full Python 3.12 suite passed 1088 tests with 1 failure and 1 warning at the "
            "final exact head",
            "R4 suite result",
        ),
        (
            "A deployment whose durable chain has not reached an exact finalized transfer "
            "receipt continues to serve Primary MEM alone.",
            "Primary MEM is universally the sole ordinary served memory and Retrieval authority",
            "pre-receipt ordinary authority",
        ),
        (
            "so Primary MEM is not universally the sole ordinary served memory and Retrieval "
            "authority once an exact finalized activation exists",
            "so Primary MEM remains the sole ordinary served memory and Retrieval authority "
            "after a finalized activation",
            "post-activation ordinary authority",
        ),
        (
            "There is no dual serving, no precedence, no empty-result fallback, no "
            "stale-projection fallback, and no Primary fallback in either direction",
            "dual serving is permitted",
            "dual serving and fallback",
        ),
        (
            "`neither` is the bounded fenced transition state between the Primary reader fence "
            "and that finalized receipt",
            "`neither` permits Primary fallback",
            "fenced transition state",
        ),
        (
            "and it required no recursive P8",
            "this RT-1D-R4 P8 requires a recursive P8",
            "R4 P8 recursion",
        ),
        (
            "exact resulting main "
            "`c623898fa8c2ba0a7c7151a912a940295829dda5`",
            "exact resulting main "
            "`d623898fa8c2ba0a7c7151a912a940295829dda5`",
            "R4 P8 exact resulting main",
        ),
        (
            "reviewed head "
            "`1299084bb5256c6638925b518291c22ecd3a4178`",
            "reviewed head "
            "`2299084bb5256c6638925b518291c22ecd3a4178`",
            "R4 P8 reviewed head",
        ),
        (
            "Its cumulative scope was exactly the four authority paths, +360/-61, in two "
            "normal branch commits carrying exactly one execution receipt",
            "Its cumulative scope was exactly the five authority paths, +360/-61, in three "
            "normal branch commits carrying exactly one execution receipt",
            "R4 P8 cumulative scope",
        ),
        (
            "the Ready-event Agent execution safety run was green before the "
            "expected-head-protected merge",
            "the mandatory RT-1D-R4 P8 awaits merge",
            "R4 P8 Ready-event evidence",
        ),
        (
            "PR #835 is merged and completed, not open, current, or incomplete, and RT-1D-R4 "
            "implementation and its mandatory P8 are both complete.",
            "still-open PR #835",
            "R4 P8 gate state",
        ),
        (
            "RT-1D-R5 immediate retirement was unstarted during that correction and "
            "introduced no retirement behavior.",
            "RT-1D-R5 immediate retirement has started",
            "R5 start state",
        ),
        (
            "This transaction is the bounded RT-1D-R4 P8 result/current-authority correction "
            "that records that merged PR #835 result.",
            "PR #835 is the current incomplete RT-1D-R4 gate",
            "R4 P8 transaction identity",
        ),
        (
            "It is documentation and current-boundary only, changes only the same four "
            "authority paths, introduces no runtime, serving, or retirement behavior, and "
            "requires no P8.",
            "the RT-1D-R4 P8 result/current-authority correction requires P8",
            "R4 P8 correction recursion",
        ),
        (
            "never from PR #834 head `d15daeec270ba453940bc10dad924a5df93dfeef`, never from "
            "PR #835 head `1299084bb5256c6638925b518291c22ecd3a4178`, never from PR #836 head "
            "`cf964cf9b530c85656f25958f261e47038247413`, and never from any frozen RT-1D-R4 "
            "implementation or amendment branch",
            "RT-1D-R5 may bootstrap from PR #835 head",
            "R5 bootstrap source",
        ),
        (
            "That correction merged as exact resulting `main` "
            "`71a334f8eab873775f378ee246daa0ca75b2ba71`, its result was independently "
            "verified, and RT-1D-R5 then became uniquely next.",
            "RT-1D-R5 has already started",
            "R5 next-slice gate",
        ),
    )
)

R5_BUDGET_AMENDMENT_ANCHORS = {
    path: (
        "The first RT-1D-R5 immediate retirement attempt returned at P1 with zero repository "
        "mutation from exact bootstrap main `71a334f8eab873775f378ee246daa0ca75b2ba71`",
        "The authorized implementation branch `agent/rt1d-r5-immediate-retirement-proof` was "
        "never pushed, carries no commit, receipt, PR, workflow run, or temporary artifact, "
        "and is frozen as P1-return evidence only",
        "architecture/budget defect, not an implementation finding",
        "adding exactly `relaylm/subjective_mem_retrieval_rehearsal.py`",
        "added exactly `tests/test_subjective_mem_retrieval_rehearsal.py` to the bounded "
        "RT-1D-R5 focused-evidence budget",
        "It is not a wildcard `tests/` or `scripts/` budget",
        "pre-authorizes no eighth production path",
        "any continuing ordinary consumer outside the exact-seven budget still returns "
        "RT-1D-R5 to P1",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R5_BUDGET_AMENDMENT_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R5_BUDGET_AMENDMENT_ANCHORS.items()
    for anchor in anchors
)

REQUIRED[RT1C] += (
    "Production deletion/modification budget (exact seven paths):",
    "relaylm/subjective_mem_retrieval_rehearsal.py",
    "`relaylm/subjective_mem_retrieval_rehearsal.py` is the seventh RT-1D-R5\nproduction path.",
    "cannot produce a closed production import graph",
    "R5 retires the temporary rehearsal and shadow characterization execution surface\ntogether",
    "R5 must not invalidate or rewrite accepted durable R3/R4 records",
    "No live\nrehearsal or shadow characterization may remain as an ordinary or operator path\n"
    "after `retirement_complete`.",
    "never ordinary\nreader, writer, ranking, fallback, or mutation authority",
    "no eighth production path\nis pre-authorized",
)

R5_BUDGET_AMENDMENT_STALE = (
    "the RT-1D-R5 production deletion/modification budget is exactly six paths",
    "exact six-path RT-1D-R5 production budget",
    "RT-1D-R5 production deletion/modification budget (exact six paths)",
    "`relaylm/subjective_mem_retrieval_rehearsal.py` is outside the RT-1D-R5 budget",
    "RT-1D-R5 retires characterization while leaving rehearsal untouched",
    "a live characterization dependency may remain after `retirement_complete`",
    "rehearsal survives as an ordinary path after `retirement_complete`",
    "shadow characterization survives as an operator path after `retirement_complete`",
    "characterization semantics may move into another owner",
    "the RT-1D-R5 focused-evidence budget is a wildcard `tests/` budget",
    "the RT-1D-R5 focused-evidence budget is a wildcard `scripts/` budget",
    "an eighth RT-1D-R5 production path is authorized",
    "a dynamic import may satisfy the RT-1D-R5 import graph",
    "RT-1D-R5 may delete tests to satisfy the retirement gates",
    "RT-1D-R5 may weaken package-import coverage",
    "the frozen `agent/rt1d-r5-immediate-retirement-proof` branch may be reused",
    "the frozen `agent/rt1d-r5-immediate-retirement-proof` branch may be pushed",
    "the RT-1D-R5 rehearsal-retirement budget amendment requires P8",
    "RT-1D-R5 implementation has started",
    "RT-1D-R5 may invalidate accepted durable R3/R4 records",
    "the P1 return was an implementation finding",
)

R5_BUDGET_AMENDMENT_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "adding exactly `relaylm/subjective_mem_retrieval_rehearsal.py`",
            "adding exactly `relaylm/subjective_mem_retrieval_projection.py`",
            "R5 seventh production path identity",
        ),
        (
            "added exactly `tests/test_subjective_mem_retrieval_rehearsal.py` to the bounded "
            "RT-1D-R5 focused-evidence budget",
            "added every file under `tests/` to the bounded RT-1D-R5 focused-evidence budget",
            "R5 focused-evidence budget scope",
        ),
        (
            "pre-authorizes no eighth production path",
            "an eighth RT-1D-R5 production path is authorized",
            "R5 eighth-path pre-authorization",
        ),
        (
            "architecture/budget defect, not an implementation finding",
            "the P1 return was an implementation finding",
            "R5 blocker classification",
        ),
        (
            "The authorized implementation branch `agent/rt1d-r5-immediate-retirement-proof` "
            "was never pushed, carries no commit, receipt, PR, workflow run, or temporary "
            "artifact, and is frozen as P1-return evidence only",
            "the frozen `agent/rt1d-r5-immediate-retirement-proof` branch may be reused",
            "R5 frozen P1-return branch",
        ),
    )
)

R5_AMENDMENT_RESULT_ANCHORS = {
    path: (
        "The RT-1D-R5 rehearsal-retirement budget amendment completed in merged PR #837 from "
        "bootstrap `71a334f8eab873775f378ee246daa0ca75b2ba71`, reviewed head "
        "`efd936329f214464f3e872d2fe0e314a2e90210a`, and exact resulting main "
        "`9468c870036226d4900fbc4c5ae94bf8c3758af8`.",
        "Its cumulative scope was exactly the four authority paths, +195/-24, in one normal "
        "forward branch commit carrying exactly one execution receipt, its cumulative P5/P6 "
        "was accepted clean, and the Ready-event Agent execution safety run 861 was green "
        "before the expected-head-protected merge.",
        "PR #837 is merged and completed, not open, current, Draft, unmerged, or incomplete.",
        "This transaction is the bounded RT-1D-R5 budget-amendment result/current-authority "
        "correction that records that merged PR #837 result.",
        "RT-1D-R5 immediate retirement was unstarted during that correction and introduced no "
        "retirement behavior.",
        "restarted only from a fresh branch created from that verified correction result, "
        "never from PR #837 head `efd936329f214464f3e872d2fe0e314a2e90210a`, never from the "
        "frozen `agent/rt1d-r5-immediate-retirement-proof` branch, and never from that "
        "correction's PR head.",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R5_AMENDMENT_RESULT_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R5_AMENDMENT_RESULT_ANCHORS.items()
    for anchor in anchors
)

REQUIRED[RT1C] += (
    "## RT-1D-R5 rehearsal-retirement budget amendment (completed)",
)

R5_AMENDMENT_RESULT_STALE = (
    "## RT-1D-R5 rehearsal-retirement budget amendment (current)",
    "PR #837 remains open",
    "PR #837 is unmerged",
    "PR #837 remains Draft",
    "PR #837 is the current incomplete RT-1D-R5 gate",
    "PR #837 is closed unmerged",
    "the RT-1D-R5 budget amendment awaits merge",
    "the RT-1D-R5 budget amendment result is unknown",
    "the exact RT-1D-R5 budget amendment reviewed head is unknown",
    "RT-1D-R5 implementation remains unstarted during this amendment",
    "the RT-1D-R5 budget-amendment result/current-authority correction requires P8",
    "RT-1D-R5 may bootstrap from PR #837 head",
    "RT-1D-R5 restarted before this correction result was verified",
)

R5_AMENDMENT_RESULT_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "exact resulting main `9468c870036226d4900fbc4c5ae94bf8c3758af8`",
            "exact resulting main `8468c870036226d4900fbc4c5ae94bf8c3758af8`",
            "R5 amendment exact resulting main",
        ),
        (
            "reviewed head `efd936329f214464f3e872d2fe0e314a2e90210a`",
            "reviewed head `ffd936329f214464f3e872d2fe0e314a2e90210a`",
            "R5 amendment reviewed head",
        ),
        (
            "exactly the four authority paths, +195/-24, in one normal forward branch commit",
            "exactly the five authority paths, +195/-24, in two normal forward branch commits",
            "R5 amendment cumulative scope",
        ),
        (
            "the Ready-event Agent execution safety run 861 was green before the "
            "expected-head-protected merge",
            "the RT-1D-R5 budget amendment awaits merge",
            "R5 amendment Ready-event evidence",
        ),
        (
            "PR #837 is merged and completed, not open, current, Draft, unmerged, or "
            "incomplete.",
            "PR #837 is the current incomplete RT-1D-R5 gate",
            "R5 amendment gate state",
        ),
        (
            "RT-1D-R5 immediate retirement was unstarted during that correction and "
            "introduced no retirement behavior.",
            "RT-1D-R5 restarted before this correction result was verified",
            "R5 start state during correction",
        ),
    )
)

# RT-1D-R5 immediate retirement implementation merged as exact resulting main
# `684b49f9bef5b34ccf9518891de85bdef3139c43`. The ordinary Primary reader and its
# selection/ranking/fallback path are retired, so the R4-era "serves Primary MEM
# alone" and "R5 unstarted" current claims are now stale. The mandatory R5 P8
# merged as PR #929 with exact resulting main
# `ec3a0789a19c05b21c9b123e012c6aac1941e54a`, so the earlier self-referential
# "this P8 is the current incomplete convergence gate while its PR is open" claim
# is itself now stale and the completed #929 identity/result is required instead.
# These anchors describe only durable merged results; they never depend on the
# branch, PR, head, or future result of the correction that records them.
R5_COMPLETION_ANCHORS = {
    path: (
        "RT-1D-R5 immediate retirement implementation completed in merged PR #907 from exact "
        "bootstrap main `731711f0a207bf547a07e56d84d60156542cff98`, final reviewed head "
        "`5911711f0f57c53a7388442b136577b4de76c938`, and exact resulting main "
        "`684b49f9bef5b34ccf9518891de85bdef3139c43`.",
        "six changed production paths inside the exact-seven RT-1D-R5 production budget, plus "
        "30 bounded focused-evidence paths",
        "`relaylm/relaymem_primary_recall_store.py` and every writer-carriage module remain "
        "byte-identical.",
        "PR #907 is merged and completed, not open, current, Draft, unmerged, or incomplete.",
        "The ordinary Primary reader is retired from current `main` rather than fenced.",
        "`run_relaymem_retrieval_stage` has exactly one fenced exit, and an ordinary decision "
        "still naming `primary_only` fails closed to `neither`.",
        "They are read-only survivors and are not ordinary reader, writer, ranking, fallback, "
        "or mutation authority, and they do not restore ordinary Primary serving.",
        "Before an exact finalized activation the accepted fail-closed cutover rules apply, so "
        "no ordinary request resolves a Primary store root, discovers or ranks a Primary "
        "candidate, or executes a Primary fallback.",
        "so Primary MEM is no longer universally the sole ordinary served memory and Retrieval "
        "authority",
        "The durable chain advances through `post_transfer_validated` and then "
        "`retirement_complete` only over the accepted exact finalized-receipt path",
        "The mandatory RT-1D-R5 P8 current-authority synchronization completed in merged PR "
        "#929 from bootstrap `684b49f9bef5b34ccf9518891de85bdef3139c43`, final reviewed head "
        "`f56302fc668491287d469d13a644b7a27d6d33a0`, and exact resulting main "
        "`ec3a0789a19c05b21c9b123e012c6aac1941e54a`.",
        "Its cumulative scope was exactly the four current-authority paths, its cumulative "
        "P5/P6 was accepted clean, and the Ready-event Agent execution safety run 1134 was "
        "green before the expected-head-protected squash merge.",
        "PR #929 is merged and completed, not open, current, Draft, unmerged, or incomplete.",
        "The R5 implementation and its mandatory P8 are therefore both complete.",
        "This result/current-authority correction only replaces the P8's self-referential "
        "open-transaction wording with the exact completed result",
        "it is documentation and current-boundary only, introduces no runtime, serving, or "
        "retirement behavior, and requires no P8.",
    )
    for path in (STATUS, PLAN, RT1C)
}
for _path, _anchors in R5_COMPLETION_ANCHORS.items():
    REQUIRED[_path] += _anchors
PROBES += tuple(
    (path, anchor)
    for path, anchors in R5_COMPLETION_ANCHORS.items()
    for anchor in anchors
)

REQUIRED[RT1C] += ("## RT-1D-R5 completion and mandatory P8 (completed)",)

R5_COMPLETION_STALE = (
    "RT-1D-R5 remains unstarted",
    "RT-1D-R5 immediate retirement remains unstarted and no retirement change has occurred",
    "RT-1D-R5 immediate retirement is unstarted",
    "RT-1D-R5 has not started",
    "the final RT-1D hard cutover remains unimplemented",
    "the final RT-1D Primary retirement remains incomplete",
    "Primary retirement remains unimplemented",
    "the Subjective MEM Retrieval hard cutover remains incomplete",
    "every deployment whose durable chain has not reached an exact finalized transfer receipt "
    "serves Primary MEM alone",
    "Primary MEM is universally the sole ordinary served memory and Retrieval authority",
    "RelayMEM Primary path: current production memory/retrieval authority",
    "PR #907 remains open",
    "PR #907 is unmerged",
    "PR #907 remains Draft",
    "PR #907 is closed unmerged",
    "the RT-1D-R5 implementation result is unknown",
    "the mandatory RT-1D-R5 P8 requires a recursive P8",
    "RT-1D-R4 is the current serving authority boundary",
    # The mandatory R5 P8 is merged as PR #929, so every open/self-referential
    # form of that P8, every wrong or unknown identity for it, and every
    # recursive-P8 claim about it or about this bounded result correction are
    # now stale. None of these forms name this correction's own branch, PR,
    # head, or future result.
    "## RT-1D-R5 completion and mandatory P8 (current)",
    "PR #929 remains open",
    "PR #929 is unmerged",
    "PR #929 remains Draft",
    "PR #929 is incomplete",
    "PR #929 is closed unmerged",
    "PR #929 is the current incomplete RT-1D-R5 gate",
    "this mandatory RT-1D-R5 P8 current-authority synchronization is the current incomplete "
    "convergence gate while its PR is open",
    "the mandatory RT-1D-R5 P8 is the current incomplete convergence gate",
    "This P8 must not be claimed complete before its own expected-head-protected merge and "
    "independent exact-result verification.",
    "the mandatory RT-1D-R5 P8 result is unknown",
    "the exact RT-1D-R5 P8 reviewed head is unknown",
    "the mandatory RT-1D-R5 P8 exact resulting main is "
    "`684b49f9bef5b34ccf9518891de85bdef3139c43`",
    "the mandatory RT-1D-R5 P8 bootstrap is `f56302fc668491287d469d13a644b7a27d6d33a0`",
    "the RT-1D-R5 P8 result/current-authority correction is the current incomplete convergence "
    "gate",
    "the RT-1D-R5 P8 result/current-authority correction requires P8",
    "the RT-1D-R5 P8 result/current-authority correction requires a recursive P8",
)

R5_COMPLETION_MUTATIONS = tuple(
    (path, current, damaged, label)
    for path in (STATUS, PLAN, RT1C)
    for current, damaged, label in (
        (
            "exact resulting main `684b49f9bef5b34ccf9518891de85bdef3139c43`",
            "exact resulting main `784b49f9bef5b34ccf9518891de85bdef3139c43`",
            "R5 implementation exact resulting main",
        ),
        (
            "final reviewed head `5911711f0f57c53a7388442b136577b4de76c938`",
            "final reviewed head `6911711f0f57c53a7388442b136577b4de76c938`",
            "R5 implementation reviewed head",
        ),
        (
            "bootstrap main `731711f0a207bf547a07e56d84d60156542cff98`",
            "bootstrap main `831711f0a207bf547a07e56d84d60156542cff98`",
            "R5 implementation bootstrap",
        ),
        (
            "six changed production paths inside the exact-seven RT-1D-R5 production budget",
            "eight changed production paths inside the exact-nine RT-1D-R5 production budget",
            "R5 production budget",
        ),
        (
            "PR #907 is merged and completed, not open, current, Draft, unmerged, or "
            "incomplete.",
            "PR #907 remains open",
            "R5 implementation gate state",
        ),
        (
            "The ordinary Primary reader is retired from current `main` rather than fenced.",
            "Primary MEM is universally the sole ordinary served memory and Retrieval "
            "authority",
            "retired reader claim",
        ),
        (
            "merged PR #929 from bootstrap `684b49f9bef5b34ccf9518891de85bdef3139c43`",
            "merged PR #929 from bootstrap `784b49f9bef5b34ccf9518891de85bdef3139c43`",
            "R5 P8 bootstrap",
        ),
        (
            "final reviewed head `f56302fc668491287d469d13a644b7a27d6d33a0`",
            "final reviewed head `e56302fc668491287d469d13a644b7a27d6d33a0`",
            "R5 P8 reviewed head",
        ),
        (
            "and exact resulting main `ec3a0789a19c05b21c9b123e012c6aac1941e54a`",
            "and exact resulting main `fc3a0789a19c05b21c9b123e012c6aac1941e54a`",
            "R5 P8 exact resulting main",
        ),
        (
            "the Ready-event Agent execution safety run 1134 was green before the "
            "expected-head-protected squash merge",
            "the mandatory RT-1D-R5 P8 result is unknown",
            "R5 P8 Ready-event evidence",
        ),
        (
            "PR #929 is merged and completed, not open, current, Draft, unmerged, or "
            "incomplete.",
            "PR #929 remains open",
            "R5 P8 gate state",
        ),
        (
            "The R5 implementation and its mandatory P8 are therefore both complete.",
            "the mandatory RT-1D-R5 P8 is the current incomplete convergence gate",
            "R5 P8 completion claim",
        ),
        (
            "This result/current-authority correction only replaces the P8's self-referential "
            "open-transaction wording with the exact completed result",
            "the RT-1D-R5 P8 result/current-authority correction requires a recursive P8",
            "R5 P8 correction recursion claim",
        ),
    )
)


R2D_P8_STALE = (
    "RT-1D-R2D is next and has not started",
    "RT-1D-R2D is next and not started",
    "R2D, R3, R4, and R5 remain not started",
    "## RT-1D-R2C completion and mandatory P8 (current)",
    "## RT-1D-R2D completion and mandatory P8 (current)",
    "The current transaction is the mandatory RT-1D-R2D P8 authority synchronization",
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
        "the durable cutover intent/fences/receipt belong to `relaylm/evidence/store.py`",
    ),
    (RT1C, "the Evidence store owns durable receipt/fence state"),
    (RT1C, "relaylm/relayctx_repack.py\nrelaylm/evidence/store.py"),
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
    ) + (
        R3_COMPLETION_MUTATIONS
        + R4_BUDGET_MUTATIONS
        + R4_RESULT_MUTATIONS
        + R4_RUNTIME_PROJECTION_MUTATIONS
        + R4_FACADE_MUTATIONS
        + R4_READINESS_REPLAY_MUTATIONS
        + R4_COMPLETION_MUTATIONS
        + R5_BUDGET_AMENDMENT_MUTATIONS
        + R5_AMENDMENT_RESULT_MUTATIONS
        + R5_COMPLETION_MUTATIONS
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
    for path in R3_COMPLETION_ANCHORS:
        for stale in R3_COMPLETION_STALE:
            body = read(path)
            assert stale not in body, f"{path}: R3 completion stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R3_COMPLETION_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: R3 completion stale anchor is not forbidden: {stale!r}")
    for path in R4_BUDGET_ANCHORS:
        for stale in R4_BUDGET_STALE:
            body = read(path)
            assert stale not in body, f"{path}: R4 budget stale anchor is present: {stale!r}"
            try:
                forbid_body(path, R4_BUDGET_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(f"{path}: R4 budget stale anchor is not forbidden: {stale!r}")
    for path in R4_RUNTIME_PROJECTION_ANCHORS:
        for stale in R4_RUNTIME_PROJECTION_STALE:
            body = read(path)
            assert stale not in body, (
                f"{path}: R4 runtime-projection stale anchor is present: {stale!r}"
            )
            try:
                forbid_body(path, R4_RUNTIME_PROJECTION_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(
                f"{path}: R4 runtime-projection stale anchor is not forbidden: {stale!r}"
            )
    for path in R4_FACADE_ANCHORS:
        for stale in R4_FACADE_STALE:
            body = read(path)
            assert stale not in body, (
                f"{path}: R4 facade stale anchor is present: {stale!r}"
            )
            try:
                forbid_body(path, R4_FACADE_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(
                f"{path}: R4 facade stale anchor is not forbidden: {stale!r}"
            )
    for path in R4_READINESS_REPLAY_ANCHORS:
        for stale in R4_READINESS_REPLAY_STALE:
            body = read(path)
            assert stale not in body, (
                f"{path}: R4 readiness/replay stale anchor is present: {stale!r}"
            )
            try:
                forbid_body(
                    path, R4_READINESS_REPLAY_STALE, body + "\n" + stale + "\n"
                )
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(
                f"{path}: R4 readiness/replay stale anchor is not forbidden: {stale!r}"
            )
    for path in R4_COMPLETION_ANCHORS:
        for stale in R4_COMPLETION_STALE:
            body = read(path)
            assert stale not in body, (
                f"{path}: R4 completion stale anchor is present: {stale!r}"
            )
            try:
                forbid_body(path, R4_COMPLETION_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(
                f"{path}: R4 completion stale anchor is not forbidden: {stale!r}"
            )
    for path in R5_BUDGET_AMENDMENT_ANCHORS:
        for stale in R5_BUDGET_AMENDMENT_STALE:
            body = read(path)
            assert stale not in body, (
                f"{path}: R5 budget amendment stale anchor is present: {stale!r}"
            )
            try:
                forbid_body(path, R5_BUDGET_AMENDMENT_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(
                f"{path}: R5 budget amendment stale anchor is not forbidden: {stale!r}"
            )
    for path in R5_AMENDMENT_RESULT_ANCHORS:
        for stale in R5_AMENDMENT_RESULT_STALE:
            body = read(path)
            assert stale not in body, (
                f"{path}: R5 amendment result stale anchor is present: {stale!r}"
            )
            try:
                forbid_body(path, R5_AMENDMENT_RESULT_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(
                f"{path}: R5 amendment result stale anchor is not forbidden: {stale!r}"
            )
    for path in R5_COMPLETION_ANCHORS:
        for stale in R5_COMPLETION_STALE:
            body = read(path)
            assert stale not in body, (
                f"{path}: R5 completion stale anchor is present: {stale!r}"
            )
            try:
                forbid_body(path, R5_COMPLETION_STALE, body + "\n" + stale + "\n")
            except AssertionError:
                print(f"PASS: {path}: reintroducing {stale!r} fails closed")
                continue
            raise AssertionError(
                f"{path}: R5 completion stale anchor is not forbidden: {stale!r}"
            )
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
    for path in R3_COMPLETION_ANCHORS:
        forbid(path, R3_COMPLETION_STALE)
    for path in R4_BUDGET_ANCHORS:
        forbid(path, R4_BUDGET_STALE)
    for path in R4_RUNTIME_PROJECTION_ANCHORS:
        forbid(path, R4_RUNTIME_PROJECTION_STALE)
    for path in R4_FACADE_ANCHORS:
        forbid(path, R4_FACADE_STALE)
    for path in R4_READINESS_REPLAY_ANCHORS:
        forbid(path, R4_READINESS_REPLAY_STALE)
    for path in R4_COMPLETION_ANCHORS:
        forbid(path, R4_COMPLETION_STALE)
    for path in R5_BUDGET_AMENDMENT_ANCHORS:
        forbid(path, R5_BUDGET_AMENDMENT_STALE)
    for path in R5_AMENDMENT_RESULT_ANCHORS:
        forbid(path, R5_AMENDMENT_RESULT_STALE)
    for path in R5_COMPLETION_ANCHORS:
        forbid(path, R5_COMPLETION_STALE)
    forbid("docs/PROJECT_STATUS.md", HISTORY_ONLY_STATUS_ANCHORS)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main(sys.argv[1:])
