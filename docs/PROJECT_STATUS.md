---
relaylm_doc_type: status
relaylm_authority: current_project_state
relaylm_status: current
relaylm_volatility: high
relaylm_owner: project_status
relaylm_update_trigger:
  - boundary moves between design dry-run read-only and apply
  - default behavior changes
  - supported request shape changes
  - current schema producer or consumer changes
  - active integration milestone changes state
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - MVP boundary and roadmap sequencing
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/mvp/v0.1_release_readiness.md
  - docs/architecture/project_execution_plan.md
  - docs/architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md
  - docs/architecture/analyzer_candidate_governance.md
  - docs/architecture/acg1_analyzer_candidate_governance_contract.md
  - docs/architecture/acg2_grounded_recall_detail_safety.md
  - docs/architecture/acg3_retrieval_query_normalization.md
  - docs/architecture/acg4_reference_intent_analyzer.md
  - docs/architecture/acg5_relayemo_scene_cleanup.md
  - docs/architecture/acg6_scene_wiki_classifier.md
  - docs/architecture/cw_a1_file_first_source_tree_parser_contracts.md
  - docs/architecture/cw_a2_workspace_compiler_projections.md
  - docs/architecture/cw_a3_character_workspace_ui_rebuild.md
  - docs/architecture/cw_a4_slp_workspace_maintenance_candidates.md
  - docs/architecture/cw_a5_character_creation_templates_showcase_import.md
  - docs/architecture/o2_supervised_scheduler_service.md
  - docs/architecture/o3_always_on_local_scheduler.md
  - docs/architecture/pm_d5_relaymem_flat_store_compatibility_removal.md
  - docs/architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md
  - docs/architecture/pm_d7_runtime_install_hook_fold_in.md
  - docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md
  - docs/architecture/e1r4_retrieval_response_grounding.md
  - docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md
  - docs/architecture/e1r5_post_wave7_correction_convergence_audit.md
  - docs/architecture/wave7_cross_slice_convergence_audit.md
---
# RelayLM Project Status

Last reviewed: 2026-07-08 JST

## Purpose and authority

This page owns current implementation status and active caveats. [Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering.

## v0.1 release readiness

v0.1 readiness is recorded in [v0.1 Release Readiness](mvp/v0.1_release_readiness.md). All current MVP execution lanes listed below are complete. The durable-memory E2 value smoke after O2/O3 scheduler draining evidence has been completed locally and human-reviewed; content-bearing comparison artifacts remain local-only under `local/value_smoke/` and are not committed. The only remaining tracked items are post-v0.1 decision debt and broader not-yet-implemented capabilities listed below.

## Current implementation position

```text
Managed-route correctness: Phase 5-C complete through bounded v0/v1 apply and C5 runtime plumbing
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete; C2 one-job adapter complete
Local worker operation: O0 one invocation -> at most one eligible queued job complete
Scheduler contract: O1A replay-before-queue round / adapter / idle contract complete
Scheduler replay lane: O1B one bounded sealed-record discovery/reread/I1-GC adapter complete
Scheduler queue lane: O1C one bounded discovery/reread/scope/C2 adapter complete
O1D1 accepted gates/one-round coordinator: complete
O1D2 bounded scheduler policy/fairness/pacing: complete
O1E stale recovery/cancellation/shutdown: complete
O1F operational validation: complete
O1 overall: complete through validation-only caller-invoked local scheduler boundary
O2 supervised worker service: complete as opt-in supervised local scheduler service wrapping O1E; not app-embedded, not default-on, and no new memory mutation authority
O3 always-on local operation: complete as opt-in local CLI/process wrapper around O2; not browser authority, not app-embedded, and not default-on

RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall, scope isolation, E1-R5 scoped candidate fallback, and PM-D8 canonical Primary recall fold-in complete
P0-PIPE RelayREL / RelaySCN / RelayEMO ordering: complete in PR #458 after actual app.py request-path rewiring and local validation; RelayREL now precedes RelaySCN, RelaySCN precedes input-side RelayEMO, RelayINT/RelayMEM/RelayCTX remain downstream; PM-D3 scene_state ownership is closed by this shipped ordering boundary
CTX Repack phase ordering fix: complete; RelayCTX short-term runtime injection now runs before token_budget_truncation in app.py so token_budget_truncation is the actual final CTX Repack mutation gate
Analyzer Candidate Governance: ACG-1 contract/helpers complete; ACG-2 Grounded Recall Detail Safety complete; ACG-3 Retrieval Query Normalization complete; ACG-4 Reference/Intent Analyzer consolidation complete; ACG-5 RelayEMO scene ownership cleanup complete; ACG-6 SCN structured classifier and scene-wiki boundary complete
Character Workspace reset: CW-A1 file-first source tree/parser contracts complete; CW-A2 compiler projections and KV-cache tiers complete; CW-A3 Character Workspace UI rebuild complete as a presentation-only browser UI rebuild; CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals complete as dry-run-first content-free candidate/proposal planning; CW-A5 character creation, bundled templates, showcase import, and safe template validation complete
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, UI-B0, UI-B1A, I-4E Forget UI, I-5B Pin / Unpin UI, I-7C Held Governance UI, CW-A3 Character Workspace top-level surfaces, and CW-A5 creation surface complete
UI-B1A read-only lifecycle visibility: complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete through M2-preferred recall plus E1-R5 bounded scoped candidate fallback
Durable-memory E2 value smoke after O2/O3 scheduler draining evidence: complete as local human-reviewed v0.1 readiness evidence; content-bearing artifacts remain local-only
E1 evaluation consolidation: complete
E1-R1 trusted Home scene admission: complete
E1-R2 character-store bootstrap command: complete
E1-R3 provenance-preserving Primary MEM formation summary: complete
E1-R4 retrieval-response grounding and unsupported-detail suppression: complete
E1-R5 Primary MEM recall candidate fallback: complete
Home can be a trusted formation source only through the E1-R1 route-owned gate; browser-owned trust remains rejected.
I1-GA contract / fault model: complete
I1-GB durable-finalization publication / pre-release admission: complete
I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete
I1-GD retention / orphan reconciliation / isolation lifecycle / cleanup: complete
I1-GE full production crash validation: complete
I1-G overall: complete
Phase I-4D ordinary retrieval lifecycle exclusion: complete
Phase I-4E loopback Forget API and SOUL Lab UI: complete
Phase I-4F full Forget validation: complete
Phase I-4 overall: complete
I-5A Pin / Unpin contract and read-only preflight: complete
I-5B Pin / Unpin apply/API/UI/ranking behavior: complete
I-7A/B Held Apply / Discard contract and read-only preflight: complete
I-7C Held Apply/Discard runtime/API/UI/durable governance evidence: complete
Wave 3 implementation tracks complete
W3-INT merged
Wave 4 implementation tracks complete
W4-INT merged
Post-Wave-4 / Wave 5 implementation tracks complete
W5-INT merged
W6-INT merged
Wave 7 implementation tracks complete
W7-INT merged
Post-Wave-7 E1-R5 correction merged and converged; PM-D8 canonical Primary recall adapter fold-in complete in PR #491
P0-PIPE ordering slice is complete after PR #458 rewired app.py and validation passed for compile, ordering smoke, docs link check, and current-boundary smoke
ACG-1 through ACG-6 analyzer governance slices are complete through bounded candidate producers, cleanup gates, and content-free public diagnostics
PM-D3 RelayEMO/RelaySCN scene_state ownership: closed by P0-PIPE request-path ordering validation
PM-D5 RelayMEM flat-store compatibility removal: complete
PM-D6 RelayINT native artifact / RelayREF wrapper removal: complete
PM-D7 runtime install hook fold-in: complete
PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in: complete
```

## Phase 6 and E1 current boundary

B0-B3 durable enqueue and fenced lifecycle are complete. B3 lifecycle: complete. C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication. C2 one-job claim/rehydrate/execute adapter: complete. I1 next-turn Primary MEM recall: complete. Character and namespace isolation: complete.

## O2/O3 local scheduler operation boundary

O2 is complete as an opt-in supervised local scheduler service that wraps O1E operational controls, carries O1D2 policy state across repeated invocations, and follows bounded content-free pacing. O3 is complete as an opt-in local CLI/process wrapper around O2 with SIGINT/SIGTERM cancellation and JSON-only content-free output.

O2/O3 are not app-embedded, not browser authority, not default-on, and do not add memory mutation authority. Existing O1E/O1D2/O1D1 gates remain the only authority for stale recovery, scheduler rounds, worker execution, durable finalization, and pacing. Durable-memory E2 smoke remains intentionally separate from O2/O3 implementation authority and is recorded only as local, human-reviewed v0.1 readiness evidence.

## Analyzer Candidate Governance boundary

ACG-1 Analyzer Candidate Governance is complete as the shared contract/helper slice. ACG-2 Grounded Recall Detail Safety is complete. ACG-3 Retrieval Query Normalization is complete. ACG-4 Reference/Intent Analyzer consolidation is complete. ACG-5 RelayEMO scene ownership cleanup is complete. ACG-6 SCN structured classifier and scene-wiki boundary is complete.

ACG-6 keeps classifier and scene-wiki matches non-authoritative by default. It does not implement Character Workspace parser/compiler/UI, scene-wiki page mutation, live LLM classifier calls, RelayEMO scene ownership restoration, or permissive policy from classifier output alone.

## Character Workspace boundary

CW-A1 is complete as a read-only target contract slice. CW-A2 is complete as an explicit compiler projection slice for deterministic `.relaylm/build/**` artifacts and KV-cache tier summaries. CW-A3 is complete as a browser UI rebuild that reorganizes the existing `apps/soul-lab` shell into Home, Character, Scenes, Relationships, Memory Wiki, Runtime, and Advanced surfaces. CW-A4 is complete as dry-run-first RelaySLP-maintained MEM / SCENE / REL wiki candidate/proposal planning with a content-free public projection and explicit write-candidates mode for allowlisted inbox/proposal artifacts only. CW-A5 is complete as deterministic character creation, bundled official starter/showcase templates, local template validation, loopback creation APIs, CLI dry-run/write commands, and zero-character UI routing.

CW-A3 keeps Home on the existing RelayLM `/v1/chat/completions` authority path, keeps Real Runtime and Local Preview explicitly separated, and moves internal governance vocabulary toward Advanced without adding browser authority. CW-A4 keeps RelaySLP deferred and out-of-band. CW-A5 preserves the no-auto-default boundary: no-character startup enters Creation / Import flow, templates remain source candidates until explicit approval, workspace commit does not auto-activate the character, imported `.relaylm/**` runtime/build/state artifacts are rejected, and third-party/imported templates do not receive RelayLM onboarding memory automatically.

## Current caveats

E1-R4 is request-side only. It builds a backend-bound grounded recall context and instruction from eligible retrieved Primary MEM evidence; it does not add post-hoc visible response rewriting, polling, supervision, browser-owned trust, or new memory mutation authority.

E1-R5 is a bounded request-side fallback. PR #491 folds the former bridge behavior into canonical Primary recall. E1-R5 does not replace M2 as the preferred relevance owner, does not run without query hints, does not scan unbounded filesystem trees, does not use the compatibility symlink, and does not add mutation, worker, scheduler, queue, browser trust, RelaySOUL, or media runtime authority.

RelayCTX short-term runtime injection apply (`relayctx_short_term_runtime_injection_apply_enabled`) remains default-off and dry-run-only by default (`relayctx_short_term_runtime_injection_dry_run_only: true`), so the CTX Repack ordering fix closes a latent gap rather than an actively triggered production bug in the shipped default configuration; deployments that turn apply on must run with the fixed ordering.

Post-MVP decision debt is tracked explicitly as PM-D1 RelaySOUL gate design-freeze relation, PM-D2 RelayINT -> RelayMEM relayint_intent_artifact legacy compatibility scope, PM-D4 client history exclusion default-off deployment decision, and PM-D9 analyzer candidate governance and multilingual schema policy. PM-D3 is closed by P0-PIPE request-path ordering validation; PM-D5, PM-D6, PM-D7, and PM-D8 are complete; ACG-1 through ACG-6 close the current PM-D9 analyzer-governance sequence.

## Immediate dependency-first work

```text
Post-O1F next candidates:
  I-5B Pin / Unpin apply/API/UI/ranking work                 complete in Wave 6
  I-7C Held Apply/Discard runtime/API/UI/durable evidence    complete in Wave 6
  E1-R1 trusted Home scene-admission path                    complete in Wave 6
  E1-R2 idempotent character-store bootstrap command         complete in Wave 6
  E1-R3 provenance-preserving Primary MEM formation summary  complete in Wave 7
  E1-R4 retrieval-response grounding and unsupported-detail suppression complete in Wave 7
  E1-R5 Primary MEM recall candidate fallback               complete post-Wave-7
  O2/O3 supervised local scheduler operation                 complete for explicit MVP need
  durable-memory E2 value smoke after O2/O3 scheduler draining evidence complete as local human-reviewed v0.1 readiness evidence

Character Workspace reset:
  CW-A1 file-first source tree and parser contracts          complete
  CW-A2 workspace compiler projections and KV-cache tiers    complete
  CW-A3 Character Workspace UI rebuild                       complete
  CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals complete
  CW-A5 character creation, templates, and showcase import   complete

Completed post-MVP debt:
  PM-D3 RelayEMO/RelaySCN scene_state ownership              closed by P0-PIPE
  PM-D5 RelayMEM flat-store compatibility removal            complete
  PM-D6 RelayINT native artifact / RelayREF wrapper removal  complete
  PM-D7 runtime install hook fold-in                         complete
  PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in complete

Post-E1-R5 / Post-Wave-7 next candidates:
  E1-R5 scoped Primary recall candidate fallback boundary remains complete; new work starts after P0-PIPE and ACG.
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D4 client history exclusion default-off deployment decision
  PM-D9 analyzer candidate governance and multilingual schema policy follow-through
  PM-D2 closure or absorption after PM-D6 if RelayREF wrapper removal closes the legacy artifact scope
```

The completed P0-PIPE implementation boundary is [P0 RelayREL / RelaySCN / RelayEMO Ordering Fix](architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md), which also closes PM-D3 RelayEMO/RelaySCN same-turn `scene_state` ownership by shipped request-path wiring and validation. The ACG-1 contract is [ACG-1 Analyzer Candidate Governance Contract](architecture/acg1_analyzer_candidate_governance_contract.md). The ACG-2 handoff is [ACG-2 Grounded Recall Detail Safety](architecture/acg2_grounded_recall_detail_safety.md). The ACG-3 handoff is [ACG-3 Retrieval Query Normalization](architecture/acg3_retrieval_query_normalization.md). The ACG-4 handoff is [ACG-4 Reference Intent Analyzer](architecture/acg4_reference_intent_analyzer.md). The ACG-5 handoff is [ACG-5 RelayEMO Scene Cleanup](architecture/acg5_relayemo_scene_cleanup.md). The ACG-6 handoff is [ACG-6 Scene-Wiki Classifier Boundary](architecture/acg6_scene_wiki_classifier.md). The CW-A1 handoff is [CW-A1 File-first Source Tree and Parser Contracts](architecture/cw_a1_file_first_source_tree_parser_contracts.md). The CW-A2 handoff is [CW-A2 Workspace Compiler Projections and KV-cache Tiers](architecture/cw_a2_workspace_compiler_projections.md). The CW-A3 handoff is [CW-A3 Character Workspace UI Rebuild](architecture/cw_a3_character_workspace_ui_rebuild.md). The CW-A4 handoff is [CW-A4 SLP Workspace Maintenance Candidates](architecture/cw_a4_slp_workspace_maintenance_candidates.md). The CW-A5 handoff is [CW-A5 Character Creation, Templates, and Showcase Import](architecture/cw_a5_character_creation_templates_showcase_import.md). The O2 handoff is [O2 Supervised Scheduler Service](architecture/o2_supervised_scheduler_service.md). The O3 handoff is [O3 Always-On Local Scheduler](architecture/o3_always_on_local_scheduler.md). The PM-D5 handoff is [PM-D5 RelayMEM Flat-store Compatibility Removal](architecture/pm_d5_relaymem_flat_store_compatibility_removal.md). The PM-D6 handoff is [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal](architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md). The PM-D7 handoff is [PM-D7 Runtime Install Hook Fold-in](architecture/pm_d7_runtime_install_hook_fold_in.md). The Analyzer Candidate Governance roadmap is [Analyzer Candidate Governance and Multilingual Schema Policy](architecture/analyzer_candidate_governance.md). The Wave 7 convergence record is [Wave 7 Cross-Slice Convergence Audit](architecture/wave7_cross_slice_convergence_audit.md). The E1-R5 post-correction convergence record is [E1-R5 Post-Wave-7 Correction Convergence Audit](architecture/e1r5_post_wave7_correction_convergence_audit.md). The E1-R3 implementation handoff is [E1-R3 Provenance-Preserving Primary MEM Formation Summary](architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md). The E1-R4 implementation handoff is [E1-R4 Retrieval-Response Grounding](architecture/e1r4_retrieval_response_grounding.md). The E1-R5 implementation handoff is [E1-R5 Primary MEM Recall Candidate Bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md). The v0.1 release-readiness receipt is [v0.1 Release Readiness](mvp/v0.1_release_readiness.md). Detailed MVP sequencing and post-MVP roadmap ordering live in [Project Execution Plan](architecture/project_execution_plan.md).

## Not yet implemented

- full RelayREL relationship Markdown parsing;
- restore/unhide or physical purge;
- Merge / Supersession runtime apply;
- Secondary MEM consolidation;
- RelaySOUL proposal/intervention/rollback slices;
- static SOUL Lab bundle serving;
- media runtime execution;
- ASR and peer communication transport.

<!-- O1B_CURRENT_BOUNDARY -->
## O1B sealed replay-lane boundary

O1B is complete for one bounded, non-recursive inventory of the configured I1-G root, exact canonical grouping and eligibility classification, deterministic selection of one sealed-pending locator, canonical selected-record reread, and at most one existing I1-GC delegation. It does not implement the O1C queue algorithm, a scheduler round loop, polling, shutdown, supervision, or always-on operation.

## Offline tooling addenda

Offline extraction tooling (runtime non-contact) added: caller-invoked, bounded `scripts/relaylm_twin_extraction_*` preprocessing/batch-runner/merge CLIs that turn X archive and ChatGPT export material into a reviewable style/fact extraction artifact. See [Twin Extraction runbook](tools/twin_extraction_runbook.md). This tooling does not import `relaylm`, does not write to MEM/SOUL, and does not change O2/O3, CW-A4/CW-A5, or RelaySLP status.

Twin review import bridge exists as an offline, caller-invoked, runtime-non-contact import source generator: `scripts/relaylm_twin_review_import_bridge.py` turns an approved `twin_extraction_review.json` into `.relaylm/sources/imports/twin-extraction/` governed import sources for CW-A4 to plan against in dry-run. It does not import `relaylm`, does not write MEM/SOUL/REL/Primary MEM or any uppercase source directly, writes nothing by default, and never auto-promotes `private_only` material. This does not mean runtime memory mutation is implemented; CW-A4 candidate/proposal write and any MEM/SOUL bootstrap step remain separate, explicit, opt-in actions outside this bridge's scope.

Twin review import source -> CW-A4 candidate/proposal planning flow is documented and smoke-covered: see [Twin Review Import -> CW-A4 Workspace Candidate Flow](tools/twin_review_to_workspace_candidates.md) and `scripts/relaylm_twin_review_to_cw_a4_flow_smoke.py`. This connects the existing bridge output to existing CW-A4 dry-run and write-candidates planning; it does not add MEM/SOUL auto promotion, Primary MEM bootstrap from Twin Extraction, SOUL auto rewrite, or runtime dogfood ingestion.

LAT-1 latency measurement infrastructure added: real per-node RelayRUN timing (`started_at`/`completed_at`/`duration_ms`) and a content-free `timing_summary` rollup on the request-path checkpoint artifact, plus an offline, `runtime/bench/`-scoped M2 retrieval scaling bench (`scripts/relaylm_lat1_bench_store_generator.py`, `scripts/relaylm_lat1_retrieval_bench.py`). See [LAT-1 Latency Measurement](architecture/lat1_latency_measurement.md). This is measurement only: no request-path behavior, degradation-ladder, timeout, or search-algorithm change, and no response-time guarantee or optimization is implemented or claimed.

Single-owner mobile dogfood operation runbook added: [P0 Mobile Dogfood Entry](tools/mobile_dogfood_entry.md) documents a Cloudflare Tunnel + Cloudflare Access external-reachability procedure limiting external exposure to the chat-only UI, with `/v1`, LM Studio, SOUL Lab, Memory Inspector, and admin/debug surfaces kept unreachable from outside. This is an operations runbook only: it does not change RelayLM runtime behavior, does not add multi-user/family-tester/actor support, and does not add any Cloudflare API integration or automated configuration.

Mobile dogfood observation runbook and local-only record templates added: see [Mobile Dogfood Observation Runbook](evaluation/mobile_dogfood_observation_runbook.md). This is local-only evaluation guidance only: it does not change runtime behavior, does not complete mobile dogfood evidence, does not update release readiness, and does not improve latency.
