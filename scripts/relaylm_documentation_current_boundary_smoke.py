#!/usr/bin/env python3
"""Validate current documentation boundary anchors after E1-R5, ACG, CW-A5, O2/O3, PM-D5-D7, and Wave 8 docs updates."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CURRENT_DOCS = (
    "docs/PROJECT_STATUS.md",
    "docs/README.md",
    "docs/architecture/README.md",
    "docs/mvp/README.md",
    "docs/DOCUMENTATION_MODEL.md",
    "docs/architecture/current_target_migration_guide.md",
    "docs/architecture/project_execution_plan.md",
    "docs/architecture/relaymem_slp_current_target.md",
    "docs/architecture/e1_evaluation_consolidation.md",
    "docs/architecture/e1r1_trusted_home_scene_admission.md",
    "docs/architecture/e1r2_character_store_bootstrap.md",
    "docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md",
    "docs/architecture/e1r4_retrieval_response_grounding.md",
    "docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md",
    "docs/architecture/e1r5_post_wave7_correction_convergence_audit.md",
    "docs/architecture/acg1_analyzer_candidate_governance_contract.md",
    "docs/architecture/acg5_relayemo_scene_cleanup.md",
    "docs/architecture/cw_a5_character_creation_templates_showcase_import.md",
    "docs/architecture/o1e_scheduler_operational_controls.md",
    "docs/architecture/o2_supervised_scheduler_service.md",
    "docs/architecture/o3_always_on_local_scheduler.md",
    "docs/architecture/pm_d5_relaymem_flat_store_compatibility_removal.md",
    "docs/architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md",
    "docs/architecture/pm_d7_runtime_install_hook_fold_in.md",
    "docs/architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md",
    "docs/architecture/phase_i5_pin_unpin_contract.md",
    "docs/architecture/phase_i5b_pin_unpin_apply.md",
    "docs/architecture/phase_i7ab_held_apply_discard_contract.md",
    "docs/architecture/phase_i7c_held_apply_discard_runtime.md",
    "docs/architecture/soul_lab_ui_mvp.md",
    "docs/architecture/wave7_cross_slice_convergence_audit.md",
    "docs/architecture/wave6_cross_slice_convergence_audit.md",
)

REQUIRED = {
    "docs/PROJECT_STATUS.md": (
        "This page owns current implementation status and active caveats.",
        "O1F operational validation: complete",
        "O1 overall: complete through validation-only caller-invoked local scheduler boundary",
        "O2 supervised worker service: complete as opt-in supervised local scheduler service wrapping O1E; not app-embedded, not default-on, and no new memory mutation authority",
        "O3 always-on local operation: complete as opt-in local CLI/process wrapper around O2; not browser authority, not app-embedded, and not default-on",
        "## O2/O3 local scheduler operation boundary",
        "O2/O3 are not app-embedded, not browser authority, not default-on, and do not add memory mutation authority.",
        "O2/O3 supervised local scheduler operation                 complete for explicit MVP need",
        "durable-memory E2 value smoke after O2/O3 scheduler draining evidence",
        "O2 handoff is [O2 Supervised Scheduler Service]",
        "O3 handoff is [O3 Always-On Local Scheduler]",
        "PM-D5 handoff is [PM-D5 RelayMEM Flat-store Compatibility Removal]",
        "PM-D6 handoff is [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal]",
        "PM-D7 handoff is [PM-D7 Runtime Install Hook Fold-in]",
        "I-5B Pin / Unpin apply/API/UI/ranking behavior: complete",
        "I-7C Held Apply/Discard runtime/API/UI/durable governance evidence: complete",
        "E1-R1 trusted Home scene admission: complete",
        "E1-R2 character-store bootstrap command: complete",
        "E1-R3 provenance-preserving Primary MEM formation summary: complete",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression: complete",
        "E1-R5 Primary MEM recall candidate discovery bridge: complete",
        "Wave 7 implementation tracks complete",
        "W7-INT merged",
        "Post-E1-R5 / Post-Wave-7 next candidates:",
        "E1-R5 scoped Primary recall candidate bridge boundary",
        "Analyzer Candidate Governance: ACG-1 contract/helpers complete; ACG-2 Grounded Recall Detail Safety complete; ACG-3 Retrieval Query Normalization complete; ACG-4 Reference/Intent Analyzer consolidation complete; ACG-5 RelayEMO scene ownership cleanup complete; ACG-6 SCN structured classifier and scene-wiki boundary complete",
        "CW-A5 character creation, templates, and showcase import   complete",
        "CW-A5 handoff is [CW-A5 Character Creation, Templates, and Showcase Import]",
        "Post-MVP decision debt is now tracked explicitly as PM-D1",
        "PM-D1 RelaySOUL gate design-freeze relation",
        "PM-D2 RelayINT -> RelayMEM relayint_intent_artifact legacy compatibility scope",
        "PM-D3 RelayEMO/RelaySCN scene_state ownership",
        "PM-D4 client history exclusion default-off deployment decision",
        "PM-D5 RelayMEM flat-store compatibility removal",
        "PM-D6 RelayINT native artifact / RelayREF wrapper removal",
        "PM-D7 runtime install hook fold-in",
        "PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in",
        "E1-R5 Post-Wave-7 Correction Convergence Audit",
    ),
    "docs/README.md": (
        "[Current project status](PROJECT_STATUS.md) — the single current implementation status authority.",
        "CW-A5 Character Creation, Templates, and Showcase Import",
        "CW-A1 through CW-A5 Character Workspace reset slices are complete",
        "ACG-1 through ACG-6 analyzer governance slices are complete",
        "ACG-6 Scene-Wiki Classifier Boundary",
        "O2 Supervised Scheduler Service",
        "O3 Always-On Local Scheduler",
        "PM-D5 RelayMEM flat-store compatibility removal",
        "PM-D6 RelayINT native artifact / RelayREF wrapper removal",
        "PM-D7 runtime install hook fold-in",
        "Wave 8 implementation evidence",
        "MVP eval runner completion report",
        "Wave 7 Cross-Slice Convergence Audit",
        "E1-R3 completion report",
        "E1-R4 completion report",
        "E1-R5 completion report",
        "E1-R5 Primary MEM recall candidate discovery bridge",
        "E1-R5 Post-Wave-7 Correction Convergence Audit",
        "PM-D8 tracks the E1-R5 bridge canonical adapter fold-in decision",
    ),
    "docs/architecture/README.md": (
        "CW-A5 Character Creation, Templates, and Showcase Import",
        "current bounded deterministic local creation/template/import implementation slice",
        "CW-A5 creation/import surfaces remain explicit user-approved flows",
        "O2 Supervised Scheduler Service",
        "O3 Always-On Local Scheduler",
        "PM-D5 RelayMEM Flat-store Compatibility Removal",
        "PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal",
        "PM-D7 Runtime Install Hook Fold-in",
        "Wave 7 Cross-Slice Convergence Audit",
        "E1-R4 Retrieval-Response Grounding",
        "E1-R5 Primary MEM Recall Candidate Discovery Bridge",
        "E1-R5 Post-Wave-7 Correction Convergence Audit",
        "implemented E1-R1/E1-R2/E1-R3/E1-R4/E1-R5 evidence",
    ),
    "docs/mvp/README.md": (
        "Wave 8 merged completion reports",
        "MVP eval runner completion report",
        "source PR #451",
        "docs/mvp/wave8/mvp_eval_runner_completion_report.md",
        "Wave 7 merged completion reports",
        "source PR #436, merge `7bb2525cb000e893146408065f1aa5976f2b54ab`",
        "source PR #437, merge `e6e5b32cd489dda493ff0171a260dd561a91765c`",
        "source PR #439",
        "docs/mvp/wave7/e1r5_completion_report.md",
    ),
    "docs/DOCUMENTATION_MODEL.md": (
        "`architecture_handoff`",
        "`validation_receipt`",
        "`cross_slice_convergence_audit`",
        "`integration_convergence_audit`",
        "`evaluation_record`",
        "`evaluation_consolidation`",
    ),
    "docs/architecture/current_target_migration_guide.md": (
        "Current Wave 7 / P0-PIPE / ACG / CW compatibility interpretation",
        "O2 is current implemented as an opt-in supervised local scheduler service above O1E.",
        "O3 is current implemented as an opt-in local CLI/process wrapper around O2.",
        "E1-R3 is current implemented as provenance-preserving Primary MEM formation summary.",
        "E1-R4 is current implemented as request-side retrieval-response grounding and unsupported-detail suppression.",
        "E1-R5 is current implemented as bounded scoped Primary MEM recall candidate discovery bridge.",
        "ACG-2 is current implemented as Grounded Recall detail safety behind Query Detail Analyzer governance.",
        "ACG-6 is current implemented as the bounded SCN structured classifier and scene-wiki matching boundary.",
        "CW-A1 is current implemented as file-first source tree and parser contracts.",
        "CW-A2 is current implemented as workspace compiler projections and KV-cache tier summaries.",
        "CW-A3 is current implemented as the presentation-only Character Workspace UI rebuild.",
        "CW-A4 is current implemented as dry-run-first SLP-maintained MEM/SCENE/REL wiki candidate and proposal planning.",
        "CW-A5 is current implemented as deterministic character creation, bundled templates, showcase import, local validation, loopback APIs, CLI dry-run/write commands, zero-character UI routing, and local CW-A2 build generation after approved commit.",
        "PM-D5 is current implemented as RelayMEM flat-store compatibility removal from ordinary runtime discovery and public diagnostics.",
        "PM-D6 is current implemented as RelayINT native artifact ownership after RelayREF wrapper removal from the input-side entrypoint.",
        "PM-D7 is current implemented as explicit dry-run-first runtime install and setup preflight/apply command support.",
        "ACG-1 through ACG-6 are current as bounded analyzer-governance slices.",
        "CW-A1 through CW-A5 are current as bounded Character Workspace reset slices.",
        "Completed behavior must not be re-listed as migration work:",
        "O2 and O3 are opt-in local operation boundaries",
        "PM-D8 in [Project Execution Plan](project_execution_plan.md) tracks the later decision",
    ),
    "docs/architecture/project_execution_plan.md": (
        "Post-MVP decision debt registry",
        "PM-D1 RelaySOUL gate design-freeze relation",
        "PM-D2 RelayINT -> RelayMEM relayint_intent_artifact legacy compatibility scope",
        "PM-D3 RelayEMO/RelaySCN scene_state ownership",
        "PM-D4 client history exclusion default-off deployment decision",
        "PM-D5 RelayMEM flat-store compatibility removal",
        "PM-D6 RelayINT native artifact / RelayREF wrapper removal",
        "PM-D7 runtime install hook fold-in",
        "PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in",
        "CW-A5 character creation, templates, and showcase import complete",
        "O2 supervised worker service             complete as opt-in local scheduler service",
        "O3 always-on local operation             complete as opt-in local CLI/process wrapper",
        "Completed post-MVP debt:",
        "Implementation order for large compatibility removals",
        "PM-D5 -> PM-D6 -> PM-D7",
        "PM-D8 should be evaluated with PM-D5",
        "Execute the existing RelaySCN-owned `scene_state` migration plan",
    ),
    "docs/architecture/relaymem_slp_current_target.md": (
        "E1-R4 request-side evidence-grounded recall behavior is current implemented.",
        "E1-R5 scoped Primary recall candidate discovery bridge is current implemented.",
        "O2 is current implemented as an opt-in supervised local scheduler service above O1E.",
        "O3 is current implemented as an opt-in local CLI/process wrapper around O2.",
        "PM-D5, PM-D6, and PM-D7 are complete as post-MVP compatibility/debt fold-in slices.",
        "request-side grounded recall response             complete as E1-R4",
        "E1-R5 scoped Primary recall bridge                complete as E1-R5",
        "opt-in supervised local scheduler service         complete as O2",
        "opt-in local CLI/process wrapper                  complete as O3",
        "target-only RelayMEM store discovery              complete as PM-D5",
        "native input-side RelayINT artifact               complete as PM-D6",
        "explicit runtime install/preflight command        complete as PM-D7",
        "E1-R5 is current implemented as a bounded scoped Primary MEM recall candidate discovery bridge.",
    ),
    "docs/architecture/e1r4_retrieval_response_grounding.md": (
        "# E1-R4 Retrieval-Response Grounding",
        "relaymem.grounded_recall_context.v0",
        "e1r5_primary_mem_recall_candidate_bridge.md",
        "E1-R5 may provide the bounded scoped Primary MEM candidate",
        "directly_supported",
        "inferred_from_supported",
        "unsupported_detail_suppressed",
        "runtime_private_evidence_omitted=true",
    ),
    "docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md": (
        "relaylm_doc_type: implementation_handoff",
        "# E1-R5 Primary MEM Recall Candidate Discovery Bridge",
        "M2 remains the preferred relevance owner",
        "shared I-4D current-state eligibility index",
        "The runtime-bridge-to-canonical-adapter decision is tracked as PM-D8",
        "PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
        "E1-R5 completion report",
    ),
    "docs/architecture/e1r5_post_wave7_correction_convergence_audit.md": (
        "relaylm_doc_type: integration_convergence_audit",
        "# E1-R5 Post-Wave-7 Correction Convergence Audit",
        "M2 remains the preferred relevance owner.",
        "PM-D8: Fold E1-R5 bounded Primary MEM candidate bridge into canonical Primary recall adapter",
        "PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
        "PYTHONPATH=. python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py",
    ),
    "docs/architecture/e1_evaluation_consolidation.md": (
        "E1-R5 Primary MEM recall candidate discovery bridge is complete.",
        "Primary recall candidate bridge",
        "current eligible Primary MEM can be selected by the M2-preferred path or",
        "python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
    ),
    "docs/architecture/integration_i1_primary_mem_two_turn_recall.md": (
        "E1-R5 bounded scoped Primary candidate bridge",
        "preserves M2 as preferred owner",
        "I-4D shared lifecycle eligibility",
    ),
    "docs/architecture/acg1_analyzer_candidate_governance_contract.md": (
        "relaylm_doc_type: implementation_contract",
        "ACG-2 through ACG-6 are now implemented in dedicated handoffs",
    ),
    "docs/architecture/acg5_relayemo_scene_cleanup.md": (
        "relaylm_doc_type: implementation_handoff",
        "# ACG-5 RelayEMO Scene Ownership Cleanup",
    ),
    "docs/architecture/cw_a5_character_creation_templates_showcase_import.md": (
        "relaylm_doc_type: implementation_handoff",
        "relaylm_update_trigger:",
        "relaylm_not_authoritative_for:",
        "# CW-A5 Character Creation, Templates, and Showcase Import",
        "CW-A5 adds the bounded character creation path",
        "The SOUL Lab UI now routes the zero-character projection to the Create surface",
        "The CLI requires `--write` for persistence and does not auto-activate characters.",
        "PYTHONPATH=. python scripts/relaylm_cw_a5_character_creation_templates_smoke.py",
    ),
    "docs/architecture/o1e_scheduler_operational_controls.md": (
        "# O1E Scheduler Operational Controls",
        "Status: implemented in this slice.",
        "O1F is complete as validation-only operational hardening over this caller-invoked boundary.",
        "O2 and O3 are implemented in dedicated handoffs as opt-in layers above O1E",
    ),
    "docs/architecture/o2_supervised_scheduler_service.md": (
        "relaylm_doc_type: implementation_handoff",
        "relaylm_authority: o2_supervised_scheduler_service_boundary",
        "# O2 Supervised Scheduler Service",
        "O2 adds an opt-in supervised local service loop around the existing O1E operational controls boundary.",
        "O2 has no independent memory, queue, worker, stale-recovery, or finalization authority.",
        "O2 reads only public, content-free fields from O1E/O1D2 results.",
        "PYTHONPATH=. python scripts/relaylm_o2_supervised_scheduler_service_smoke.py",
        "Durable-memory E2 smoke should remain a separate slice.",
    ),
    "docs/architecture/o3_always_on_local_scheduler.md": (
        "relaylm_doc_type: implementation_handoff",
        "relaylm_authority: o3_always_on_local_scheduler_boundary",
        "# O3 Always-On Local Scheduler",
        "O3 adds an opt-in local process wrapper for O2.",
        "O3 delegates all scheduling work to O2, and O2 delegates each round to O1E.",
        "PYTHONPATH=. python scripts/relaylm_o3_always_on_local_scheduler.py --config config.yaml --max-rounds 1",
        "PYTHONPATH=. python scripts/relaylm_o3_always_on_local_scheduler_smoke.py",
        "The later durable-memory E2 scenario should consume this capability",
    ),
    "docs/architecture/pm_d5_relaymem_flat_store_compatibility_removal.md": (
        "relaylm_doc_type: implementation_handoff",
        "relaylm_authority: pm_d5_relaymem_flat_store_compatibility_removal_boundary",
        "# PM-D5 RelayMEM flat-store compatibility removal",
        "PM-D5 removes RelayMEM flat-store compatibility from ordinary runtime discovery and public diagnostics.",
        "flat_store_compatibility_removed: true",
        "Runtime page candidate discovery scans only target Primary/Secondary directories.",
        "PYTHONPATH=. python scripts/relaylm_pm_d5_flat_store_compat_removal_smoke.py",
    ),
    "docs/architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md": (
        "relaylm_doc_type: implementation_handoff",
        "relaylm_authority: pm_d6_relayint_native_artifact_boundary",
        "# PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal",
        "RelayINT now owns a request-local reference/intent artifact",
        "runtime-private schema: `relayint.intent.v1`",
        "PYTHONPATH=. python scripts/relaylm_pm_d6_relayint_native_artifact_smoke.py",
    ),
    "docs/architecture/pm_d7_runtime_install_hook_fold_in.md": (
        "relaylm_doc_type: implementation_handoff",
        "relaylm_authority: pm_d7_runtime_install_hook_fold_in",
        "# PM-D7 Runtime Install Hook Fold-in",
        "PM-D7 folds local runtime install and setup debt into a first-class explicit RelayLM command",
        "relaylm-runtime-install --config config.yaml --dry-run",
        "PYTHONPATH=. python scripts/relaylm_pm_d7_runtime_install_hook_fold_in_smoke.py",
    ),
    "docs/architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md": (
        "relaylm_doc_type: implementation_handoff",
        "# P0 RelayREL / RelaySCN / RelayEMO Ordering Fix",
    ),
    "docs/architecture/wave7_cross_slice_convergence_audit.md": (
        "# Wave 7 Cross-Slice Convergence Audit",
        "PR #436",
        "7bb2525cb000e893146408065f1aa5976f2b54ab",
        "PR #437",
        "e6e5b32cd489dda493ff0171a260dd561a91765c",
        "E1-R3 provenance-preserving Primary MEM formation summary: complete",
        "E1-R4 retrieval-response grounding and unsupported-detail suppression: complete",
        "W7-INT is merged.",
    ),
    "docs/mvp/wave7/e1r4_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "retrieval-response grounding and unsupported-detail suppression",
        "Request-side vs response-side decision",
        "Content leakage review",
        "Authority preservation",
    ),
    "docs/mvp/wave7/e1r5_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "Primary MEM Recall Candidate Discovery Bridge",
        "PR: #439",
        "PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py",
    ),
    "docs/mvp/wave8/mvp_eval_runner_completion_report.md": (
        "relaylm_doc_type: implementation_completion_report",
        "MVP Eval Runner Completion Report",
        "PR: #451",
        "PYTHONPATH=.:scripts python scripts/relaylm_mvp_eval_runner.py --mode static --json-out runtime/eval/mvp_eval_static_latest.json",
    ),
}

STALE = tuple(
    line.strip()
    for line in """
    W5-INT in progress until the convergence PR merges
    W5-INT is in progress until the convergence PR containing this audit is merged.
    O1F remains target/unimplemented.
    O2 supervised worker service: planned/unimplemented
    O3 always-on local operation: planned/unimplemented
    O2/O3 remain target/unimplemented.
    O2 supervision and O3 always-on operation remain unimplemented.
    O2 and O3 remain incomplete.
    O2 supervised worker service, only if required
    O3 always-on local operation, only if required
    O2 supervised worker service, if required
    O3 always-on operation, if required
    I-5 runtime apply/API/UI/ranking behavior: unimplemented
    I-7 runtime apply/discard/API/UI/durable governance evidence: unimplemented
    Direct Home-origin formation: not currently proven; trusted scene admission is missing
    Direct Home-origin trusted scene admission remains target work
    Pin/Unpin runtime API/UI/ranking behavior: pending
    Held Apply/Discard runtime API/UI/durable evidence: pending
    Character-store bootstrap remains operator-facing and brittle
    E1-R3 provenance-preserving Primary MEM formation summary current next candidate
    E1-R4 retrieval-response grounding and unsupported-detail suppression current next candidate
    E1-R4 evidence-grounded recall behavior remains quality work
    E1-R4 remains incomplete quality/evaluation work
    E1-R4 response grounding.
    remaining E1-R4 quality work
    E1-R5 remains unindexed
    E1-R5 remains incomplete
    Character Workspace source tree parser/compiler/UI
    ACG-1 is current as a shared contract/helper layer only. It does not mean that Grounded Recall detail detection, retrieval query normalization, RelayREF / RelayINT reference analyzer consolidation, RelayEMO scene-hint cleanup, or SCN scene-wiki classifier work is complete.
    ACG-2 through ACG-6 analyzer candidate producers/classifiers
    ACG-1 is complete as the analyzer governance contract/helper slice, and PM-D8 tracks
    relaylm_doc_type: architecture_contract
    relaylm_doc_type: implementation_report
    """.splitlines()
    if line.strip()
)


def read(path: str) -> str:
    location = ROOT / path
    assert location.exists(), f"missing file: {path}"
    return location.read_text(encoding="utf-8")


def require(path: str, anchors: tuple[str, ...]) -> None:
    body = read(path)
    missing = [anchor for anchor in anchors if anchor not in body]
    assert not missing, f"{path}: missing anchors: {missing!r}"


def forbid_current_stale(path: str) -> None:
    if "wave" in path and "cross_slice_convergence_audit" in path:
        return
    body = read(path)
    stale = [anchor for anchor in STALE if anchor in body]
    assert not stale, f"{path}: stale anchors: {stale!r}"


def main() -> None:
    for path, anchors in REQUIRED.items():
        require(path, anchors)
    for path in CURRENT_DOCS:
        forbid_current_stale(path)
    print("Documentation current boundary smoke passed")


if __name__ == "__main__":
    main()
