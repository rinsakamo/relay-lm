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
  - docs/architecture/pipeline_responsibility_design.md
  - docs/architecture/project_execution_plan.md
  - docs/architecture/current_target_migration_guide.md
  - docs/architecture/relaymem_slp_current_target.md
  - docs/architecture/o1f_operational_validation.md
  - docs/architecture/phase_i5b_pin_unpin_apply.md
  - docs/architecture/phase_i7c_held_apply_discard_runtime.md
  - docs/architecture/e1r1_trusted_home_scene_admission.md
  - docs/architecture/e1r2_character_store_bootstrap.md
  - docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md
  - docs/architecture/e1r4_retrieval_response_grounding.md
  - docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md
  - docs/architecture/e1r5_post_wave7_correction_convergence_audit.md
  - docs/architecture/e1_evaluation_consolidation.md
  - docs/architecture/wave7_cross_slice_convergence_audit.md
  - docs/architecture/wave6_cross_slice_convergence_audit.md
  - docs/architecture/wave5_cross_slice_convergence_audit.md
  - docs/architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md
  - docs/architecture/analyzer_candidate_governance.md
  - docs/architecture/acg1_analyzer_candidate_governance_contract.md
  - docs/architecture/acg2_grounded_recall_detail_safety.md
  - docs/architecture/acg3_retrieval_query_normalization.md
---
# RelayLM Project Status

Last reviewed: 2026-07-03 JST

## Purpose and authority

This page is the concise current-state view. When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibility and canonical target order.
2. This page owns current implementation status and active caveats.
3. [Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering.
4. Dedicated current contracts and handoffs own exact bounded behavior.
5. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) owns compatibility interpretation.
6. `docs/mvp/` and archived documents are historical evidence only.

This page owns current implementation status and active caveats. [Project Execution Plan](architecture/project_execution_plan.md) owns MVP boundary, dependency sequencing, and roadmap ordering.

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
O2 supervised worker service: planned/unimplemented
O3 always-on local operation: planned/unimplemented

RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall, scope isolation, and E1-R5 scoped candidate bridge complete
P0-PIPE RelayREL / RelaySCN / RelayEMO ordering: complete in PR #458 after actual app.py request-path rewiring and local validation; RelayREL now precedes RelaySCN, RelaySCN precedes input-side RelayEMO, RelayINT/RelayMEM/RelayCTX remain downstream
Analyzer Candidate Governance: ACG-1 contract/helpers complete; ACG-2 Grounded Recall Detail Safety complete; ACG-3 Retrieval Query Normalization complete; ACG-4 through ACG-6 remain planned/current next gates before Character Workspace implementation unless a later roadmap PR changes the dependency order
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, UI-B0, UI-B1A, I-4E Forget UI, I-5B Pin / Unpin UI, and I-7C Held Governance UI complete
UI-B1A read-only lifecycle visibility: complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete through M2-preferred recall plus E1-R5 bounded scoped candidate bridge
E1 evaluation consolidation: complete
E1-R1 trusted Home scene admission: complete
E1-R2 character-store bootstrap command: complete
E1-R3 provenance-preserving Primary MEM formation summary: complete
E1-R4 retrieval-response grounding and unsupported-detail suppression: complete
E1-R5 Primary MEM recall candidate discovery bridge: complete
Home can be a trusted formation source only through the E1-R1 route-owned gate; browser-owned trust remains rejected.

Phase I-4A Forget / Hide contract: defined target contract; completed by I-4B through I-4F implementation slices
Phase I-4B resolver / shared fence / read-only preflight-token-history: complete
Phase I-4C1 hidden-successor commit: complete
Phase I-4C2 prepared recovery / operation-scoped M3f-M3g / tombstone finalization: complete
Phase I-4D ordinary retrieval lifecycle exclusion: complete
Phase I-4E loopback Forget API and SOUL Lab UI: complete
Phase I-4F full Forget validation: complete
Phase I-4 overall: complete

I-5A Pin / Unpin contract and read-only preflight: complete
I-5B Pin / Unpin apply/API/UI/ranking behavior: complete

I-7A/B Held Apply / Discard contract and read-only preflight: complete
I-7C Held Apply/Discard runtime/API/UI/durable governance evidence: complete

I1-GA contract / fault model: complete
I1-GB durable-finalization publication / pre-release admission: complete
I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete
I1-GD retention / orphan reconciliation / isolation lifecycle / cleanup: complete
I1-GE full production crash validation: complete
I1-G overall: complete

Wave 3 implementation tracks complete
W3-INT merged
Wave 4 implementation tracks complete
W4-INT merged
Post-Wave-4 / Wave 5 implementation tracks complete
W5-INT merged
O1F validation slice merged after W5-INT
Wave 6 implementation tracks complete
W6-INT merged
Wave 7 implementation tracks complete
W7-INT merged
Post-Wave-7 E1-R5 correction merged and converged
P0-PIPE ordering slice is complete after PR #458 rewired app.py and validation passed for compile, ordering smoke, docs link check, and current-boundary smoke
ACG-1 Analyzer Candidate Governance contract/helper slice is complete; ACG-2 Grounded Recall Detail Safety is complete; ACG-3 Retrieval Query Normalization is complete; ACG-4 is the next dependency gate before Character Workspace reset implementation
```

Historical Post-O1F next candidates: I-5B Pin / Unpin apply, I-7C Held Apply / Discard runtime governance, E1-R1 trusted Home scene admission, and E1-R2 character-store bootstrap are now complete through Wave 6. E1-R3 and E1-R4 are complete through Wave 7. E1-R5 is complete as a post-Wave-7 correction to the E1 recall proof boundary.

Historical Post-E1-R3 next candidates:

```text
Post-E1-R3 next candidates:
  E1-R4 retrieval-response grounding and unsupported-detail suppression: complete
  E1-R5 Primary MEM recall candidate discovery bridge: complete
  O2/O3 only after explicit MVP need
  Static SOUL Lab bundle serving, if local packaging requires it
```

## Phase 6 RelaySLP orchestration and O0

Implemented:

- A1/A2 deferred admission and finalized-turn handoff;
- B0-B3 durable enqueue and fenced lifecycle;
- I1-B ordinary runtime source publication and enqueue;
- C1-0 through C1-5 complete;
- C2 one-job claim/rehydrate/execute adapter: complete;
- O0 one-shot bounded queue discovery and one C2 delegation;
- O1A pure two-lane round/result/disposition contract;
- O1B one bounded eligible sealed I1-G replay-lane discovery and one existing I1-GC delegation;
- O1C one bounded eligible B2/B3 queue-lane discovery and one existing C2 delegation;
- O1D1 accepted scheduler gates and one production `replay -> queue` round;
- O1D2 bounded policy wrapper;
- O1E bounded caller-invoked operational controls;
- O1F validation-only operational hardening.

B3 lifecycle: complete. C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication.

I1 next-turn Primary MEM recall: complete. Character and namespace isolation: complete. E1-R5 adds the current bounded candidate bridge when M2 yields no eligible scoped Primary candidate.

## O1 operations boundary

O1A through O1F are complete through a validation-only caller-invoked local scheduler boundary. O1D1 accepts the five exact scheduler gates and runs at most one `replay -> queue` round. O1D2 adds bounded policy hints without sleeping. O1E adds caller-invoked stale-recovery, cancellation, and shutdown projections without polling or supervision. O1F validates corruption, concurrency, saturation, restart reread, and leakage edges.

O2/O3 remain planned/unimplemented. O1F completion does not imply a daemon, worker pool, recurring schedule, service supervision, or always-on operation.

## RelayMEM Primary persistence and governance

Implemented governance boundaries now include:

- I-4B canonical current-state resolution and shared Correct/Forget mutation fence;
- I-4C1 immutable Forget prepared evidence and deterministic hidden-successor M3e commit;
- I-4C2 exact prepared resume, operation-scoped M3f/M3g convergence, tombstone finalization, and exact replay;
- I-4D ordinary M2/RelayCTX lifecycle and prior-revision exclusion plus read-only historical lifecycle projection;
- I-4E loopback-only Forget API and SOUL Lab UI;
- I-4F crash/race/security/fresh-conversation validation;
- I-5A Pin / Unpin contract and read-only preflight;
- I-5B durable Pin / Unpin apply, loopback API/UI, and deterministic ranking hint;
- I-7A/B Held Apply / Discard contract and read-only preflight;
- I-7C Held Apply / Discard runtime governance evidence, loopback API/UI, and explicit confirmation flow;
- E1-R5 bounded scoped Primary MEM recall candidate bridge when M2 yields no eligible scoped Primary candidate.

Forget product-complete means one real current active Primary MEM can be hidden through the loopback/SOUL Lab API/UI surface, with explicit token confirmation, bounded receipt/history/lifecycle visibility, restart-safe recovery, fresh-process reread, fresh ordinary conversation exclusion, stale-browser fencing, multi-scope isolation, and no private-content leakage.

I-5B Pin state is governance metadata and a ranking hint only. It does not admit hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions into retrieval and does not alter semantic memory content.

I-7C governs one already-held candidate through explicit Apply / Discard preflight and confirmation. It persists content-free decision evidence but does not start workers, schedulers, retry loops, C2, O1, or B3 lifecycle transitions from the UI.

## SOUL Lab and E1 evaluation

UI-B0 real Home conversation is complete. UI-B1A read-only lifecycle and operation visibility is complete. I-4E Forget API/UI, I-5B Pin / Unpin API/UI, and I-7C Held Governance API/UI are complete. The browser uses server-projected routes and the existing same-origin RelayLM Chat Completions path. It owns no backend, SOUL, namespace, storage-root, queue, worker, scheduler, or route authority.

E1 evaluation consolidation is complete as a docs/evidence boundary. E1-R1 adds a route-owned trusted Home scene-admission gate that defaults disabled and rejects browser-owned trust. E1-R2 adds a dry-run-first operator command for idempotent character-store bootstrap. E1-R3 adds speaker-provenance-safe Primary MEM formation summary construction so user assertions remain distinguishable, assistant acknowledgements/speculation are not promoted to user facts, and route-owned scene/trust evidence stays qualification metadata. E1-R4 adds request-side retrieval-response grounding and unsupported-detail suppression for eligible retrieved Primary MEM evidence. E1-R5 adds the bounded Primary MEM recall candidate discovery bridge for the discovered `selected_count: 0` scoped-recall gap while preserving M2 as the preferred relevance owner.

Wave 7 convergence is recorded in [Wave 7 Cross-Slice Convergence Audit](architecture/wave7_cross_slice_convergence_audit.md). E1-R5 is recorded in [E1-R5 Primary MEM Recall Candidate Bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md), [E1-R5 completion report](mvp/wave7/e1r5_completion_report.md), and [E1-R5 Post-Wave-7 Correction Convergence Audit](architecture/e1r5_post_wave7_correction_convergence_audit.md). The E1 proof boundary now includes E1-R5 and does not claim that M2 alone always selects current eligible scoped Primary MEM.

## RelayREL / RelaySCN / RelayEMO ordering boundary

P0-PIPE is complete in PR #458 after the actual FastAPI `app.py` request path was rewired and validation passed. The request path now establishes the content-free RelayREL relationship projection, builds RelaySCN scene policy without any RelayEMO artifact compatibility input, runs input-side RelayEMO afterward, and keeps RelayINT, RelayMEM retrieval, and RelayCTX repack/injection downstream of RelaySCN ownership.

This does not implement full RelayREL relationship Markdown parsing, Character Workspace source tree parsing, Character Workspace compiler projections, Quick Create / Advanced Create, or Character Workspace UI.

## Analyzer Candidate Governance boundary

ACG-1 Analyzer Candidate Governance is complete as the shared contract/helper slice. It provides `relaylm/analyzer_governance.py` and `scripts/relaylm_analyzer_governance_smoke.py`, with English-only fixed schema keys/enums/reason IDs, fail-closed validation, source-authority normalization, bounded runtime-open checks, and content-free public projection helpers.

ACG-2 Grounded Recall Detail Safety is complete. It moves remembered-detail detection behind a Query Detail Analyzer artifact consumed by Grounded Recall while preserving restrictive-only fallback behavior and public content-free diagnostics.

ACG-3 Retrieval Query Normalization is complete. It adds a RelayMEM retrieval query analyzer boundary, keeps backend-private bounded hints available to read-only candidate discovery and the E1-R5 bridge, and keeps public query diagnostics content-free.

ACG-4 through ACG-6 remain planned/unimplemented and are the immediate dependency gates before Character Workspace parser/compiler/UI implementation unless a later roadmap PR explicitly changes the dependency order.

The current order is:

```text
ACG-1 Analyzer Candidate Governance contract: complete
  -> ACG-2 Grounded Recall Query Detail Analyzer: complete
  -> ACG-3 RelayMEM Query Analyzer / Retrieval Hint Normalization: complete
  -> ACG-4 RelayREF / RelayINT Reference Analyzer consolidation
  -> ACG-5 RelayEMO scene ownership cleanup
  -> ACG-6 SCN structured classifier and scene-wiki integration
```

## Current caveats

E1-R4 is request-side only. It builds a backend-bound grounded recall context and instruction from eligible retrieved Primary MEM evidence; it does not add post-hoc visible response rewriting, polling, supervision, O2/O3, browser-owned trust, or new memory mutation authority.

E1-R5 is a bounded request-side fallback bridge. It does not replace M2 as the preferred relevance owner, does not run without query hints, does not scan unbounded filesystem trees, does not use the compatibility symlink, and does not add mutation, worker, scheduler, queue, browser trust, RelaySOUL, or media runtime authority.

Post-MVP decision debt is now tracked explicitly as PM-D1 RelaySOUL gate design-freeze relation, PM-D2 RelayINT -> RelayMEM relayref_artifact legacy compatibility scope, PM-D3 RelayEMO/RelaySCN scene_state ownership, PM-D4 client history exclusion default-off deployment decision, PM-D5 RelayMEM flat-store compatibility removal, PM-D6 RelayINT native artifact / RelayREF wrapper removal, PM-D7 runtime install hook fold-in, PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in, and PM-D9 analyzer candidate governance and multilingual schema policy. These items are intentionally unimplemented until dedicated roadmap PRs close or absorb them, except PM-D3 which is closed by PR #458 because the actual request path is rewired and validated. ACG-1 closes the initial PM-D9 contract/helper slice; ACG-2 and ACG-3 close the Grounded Recall detail-safety and Retrieval Query normalization slices; PM-D9 remains open until ACG-4 through ACG-6 are implemented or explicitly rescheduled by a later roadmap PR.

## Immediate dependency-first work

```text
Analyzer Candidate Governance slices
  -> ACG-1 contract/helper slice is complete after the completed P0-PIPE request-path ordering fix
  -> ACG-2 Grounded Recall Detail Safety is complete
  -> ACG-3 Retrieval Query Normalization is complete
  -> execute ACG-4 through ACG-6 before Character Workspace reset implementation unless a later roadmap PR changes this dependency order
  -> keep schema keys / enum values / reason IDs English-only while isolating multilingual free-text understanding inside analyzer candidate producers

Character Workspace parser/compiler/UI slices
  -> begin only after the remaining ACG gates land or a later roadmap PR explicitly changes this dependency order
  -> keep full RelayREL Markdown parsing out of PR #458

Character Workspace reset next candidates:
  CW-A1 file-first source tree and parser contracts
  CW-A2 workspace compiler projections and KV-cache tiers
  CW-A3 Character Workspace UI rebuild
  CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals
  CW-A5 character creation, templates, and showcase import

Post-E1-R5 / Post-Wave-7 next candidates:
  E1-R5 scoped Primary recall candidate bridge boundary remains complete; new work starts after P0-PIPE and ACG.
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D4 client history exclusion default-off deployment decision
  PM-D5 RelayMEM flat-store compatibility removal
  PM-D6 RelayINT native artifact / RelayREF wrapper removal
  PM-D7 runtime install hook fold-in
  PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in
  PM-D9 analyzer candidate governance and multilingual schema policy
  PM-D2 closure or absorption after PM-D6 if RelayREF wrapper removal closes the legacy artifact scope
  O2/O3 only after explicit MVP need
  Static SOUL Lab bundle serving, if local packaging requires it
```

The completed P0-PIPE implementation boundary is [P0 RelayREL / RelaySCN / RelayEMO Ordering Fix](architecture/p0_relayrel_relayscn_relayemo_ordering_fix.md). The ACG-1 contract is [ACG-1 Analyzer Candidate Governance Contract](architecture/acg1_analyzer_candidate_governance_contract.md). The ACG-2 handoff is [ACG-2 Grounded Recall Detail Safety](architecture/acg2_grounded_recall_detail_safety.md). The ACG-3 handoff is [ACG-3 Retrieval Query Normalization](architecture/acg3_retrieval_query_normalization.md). The Analyzer Candidate Governance roadmap is [Analyzer Candidate Governance and Multilingual Schema Policy](architecture/analyzer_candidate_governance.md). The Wave 7 convergence record is [Wave 7 Cross-Slice Convergence Audit](architecture/wave7_cross_slice_convergence_audit.md). The E1-R5 post-correction convergence record is [E1-R5 Post-Wave-7 Correction Convergence Audit](architecture/e1r5_post_wave7_correction_convergence_audit.md). The Wave 6 convergence record is [Wave 6 Cross-Slice Convergence Audit](architecture/wave6_cross_slice_convergence_audit.md). The E1-R3 implementation handoff is [E1-R3 Provenance-Preserving Primary MEM Formation Summary](architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md). The E1-R4 implementation handoff is [E1-R4 Retrieval-Response Grounding](architecture/e1r4_retrieval_response_grounding.md). The E1-R5 implementation handoff is [E1-R5 Primary MEM Recall Candidate Bridge](architecture/e1r5_primary_mem_recall_candidate_bridge.md). Detailed MVP sequencing and post-MVP roadmap ordering live in [Project Execution Plan](architecture/project_execution_plan.md).

## Safe defaults

Current mutation, worker, durable-finalization, retention, scheduler-related paths, and E1 evaluation paths remain default-off or explicitly caller/operator invoked. I1-GC does not add a scanner or automatic retry loop. I1-GD performs one bounded caller-invoked pass and does not poll or invoke replay. O1D1 accepts exact scheduler gates but runs only one caller-invoked round and returns without sleep. O1D2 returns bounded policy hints only. O1E returns bounded operational-control projections only. O1F validates operational edges but does not loop, poll, sleep, supervise, or run always-on. E1-R1 defaults disabled and does not accept browser-owned trust. E1-R2 is an explicit dry-run-first operator command. E1-R3 exposes only content-free provenance counts/statuses publicly and keeps raw user text, assistant text, protected source bodies, queue payloads, roots, paths, tokens, owners, and digests out of public projections. E1-R4 exposes only content-free grounded-recall counts/statuses publicly and keeps runtime-private evidence out of public projections. E1-R5 exposes only content-free bridge discovery counts/statuses publicly and keeps memory text, page paths, roots, namespaces, ids, digests, lineage, queue payloads, and protected source bodies out of public projections. P0-PIPE projections expose only content-free ordering/projection evidence and keep relationship bodies, scene bodies, memory bodies, raw messages, private state, and assistant output out of public projections. ACG-1 public analyzer projections expose fixed content-free fields only and keep raw user text, raw assistant text, free-form LLM rationale, source Markdown, memory text, scene Markdown, relationship Markdown, paths, and queue payload bodies out of public diagnostics. ACG-2 public Query Detail Analyzer projections and ACG-3 public Retrieval Query projections likewise expose only fixed content-free fields/counts/statuses while keeping raw query text, private hint strings, analyzer free-form rationale, memory text, protected source bodies, filesystem paths, and queue payloads out of public diagnostics.

## Not yet implemented

- Analyzer Candidate Governance analyzer producers/classifiers ACG-4 through ACG-6;
- Character Workspace source tree parser/compiler/UI;
- Quick Create / Advanced Create / template import UI;
- full RelayREL relationship Markdown parsing;
- O2 supervised worker service and O3 always-on local operation;
- restore/unhide or physical purge;
- Merge / Supersession runtime apply;
- Secondary MEM consolidation;
- RelaySOUL proposal/intervention/rollback slices;
- static SOUL Lab bundle serving;
- TTS/audio/avatar/Live2D execution;
- ASR and peer communication transport.

<!-- O1B_CURRENT_BOUNDARY -->
## O1B sealed replay-lane boundary

O1B is complete for one bounded, non-recursive inventory of the configured I1-G root, exact canonical grouping and eligibility classification, deterministic selection of one sealed-pending locator, canonical selected-record reread, and at most one existing I1-GC delegation. It does not implement the O1C queue algorithm, a scheduler round loop, polling, shutdown, supervision, or always-on operation.

## Wave 2 cross-slice convergence

W2-INT audits the merged I1-GD, I-4C2, O1B, and O1C production boundaries. It adds no scheduler loop or retrieval exclusion. The Wave 2 audit is frozen historical evidence.
