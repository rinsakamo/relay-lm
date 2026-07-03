---
relaylm_doc_type: implementation_plan
relaylm_authority: mvp_execution_plan_and_post_mvp_roadmap
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - MVP boundary changes
  - dependency sequencing changes
  - a wave opens or closes through a convergence PR
  - evaluation decision changes
  - post-MVP roadmap ordering changes
relaylm_not_authoritative_for:
  - current implemented runtime status
  - component responsibility and canonical target order
  - exact schema details
  - historical implementation evidence
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - file_first_character_workspace_design.md
  - character_template_creation_flow.md
  - current_target_migration_guide.md
  - relaymem_slp_current_target.md
  - analyzer_candidate_governance.md
  - acg1_analyzer_candidate_governance_contract.md
  - acg2_grounded_recall_detail_safety.md
  - acg3_retrieval_query_normalization.md
  - o1f_operational_validation.md
  - phase_i5b_pin_unpin_apply.md
  - phase_i7c_held_apply_discard_runtime.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - e1r3_provenance_preserving_primary_mem_formation_summary.md
  - e1r4_retrieval_response_grounding.md
  - e1r5_primary_mem_recall_candidate_bridge.md
  - e1r5_post_wave7_correction_convergence_audit.md
  - e1_evaluation_consolidation.md
  - wave7_cross_slice_convergence_audit.md
  - wave6_cross_slice_convergence_audit.md
  - wave5_cross_slice_convergence_audit.md
---
# RelayLM Project Execution Plan

Last reviewed: 2026-07-03 JST

## Purpose

This document is the single plan and roadmap authority for RelayLM execution. It owns dependency-first sequencing, MVP boundaries, MVP completion criteria, and post-MVP roadmap ordering.

It does not own current implementation status. Read [Project Status](../PROJECT_STATUS.md) first for the implemented boundary, incomplete work, and active caveats. Component responsibility remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact behavior remains in dedicated contracts and handoffs, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

## Authority split

```text
PROJECT_STATUS.md
  -> current implemented state, active gaps, next candidates

project_execution_plan.md
  -> MVP boundary, dependency sequence, roadmap, wave ordering

file_first_character_workspace_design.md
  -> target source tree, workspace UX, KV-cache tiers, and RelayREL boundary

character_template_creation_flow.md
  -> no-character startup, Quick/Advanced Create, template import, and showcase policy

slice contracts and handoffs
  -> exact bounded behavior for one feature or phase

docs/mvp/** and wave audits
  -> historical evidence and frozen convergence records
```

The former plan and roadmap files are compatibility stubs that point here:

```text
pipeline_implementation_plan.md
post_i3_evaluation_work_roadmap.md
relaymem_mvp_implementation_plan.md
```

## Product direction reset

The completed E1 / I-4 / I-5 / I-7 / O1 work proves that RelayLM can form, govern, recall, ground, and exclude scoped Primary MEM through durable local runtime boundaries. That foundation remains valuable, but it should not define the default product UX.

The target product MVP is now:

```text
A Markdown-first local-LLM character workspace where the user can edit
human-readable character source files, let RelaySLP maintain scene and memory
wiki pages, and have RelayLM compile those files into cache-friendly runtime
projections for character-consistent conversation.
```

The primary local user is a mid-range GPU local-LLM / OpenWebUI / LM Studio / AI companion / VTuber experimenter. MVP creation and template flows should prioritize low-friction character creation and finished showcase character experience over internal memory governance or RelayLM-development-specific default characters.

This means the default UI target shifts away from internal memory-governance controls and toward Character Workspace surfaces. Pin / Unpin, revision IDs, queue records, workers, and apply tokens remain available in Advanced diagnostics or explicit governance flows, but they are not the primary user mental model.

## MVP boundary

The MVP is the smallest file-first product boundary that lets a local operator evaluate whether RelayLM can sustain a character through editable Markdown sources, scene/emotion/relationship-aware context compilation, safe memory formation and recall, and bounded local operation.

MVP must provide:

- a character workspace source tree with `SOUL.md`, `STYLE.md`, `EMOTION.md`, `SCENE.md`, `RELATIONSHIP.md`, `MEMORY.md`, and `BOUNDARY.md`;
- optional `LORE.md` for characters with substantial world/backstory material;
- lower-case SLP-maintained `memory/**/*.md`, `scenes/**/*.md`, and `relationships/<target>.md` pages;
- `.relaylm/sources/`, `.relaylm/state/`, and `.relaylm/build/` generated/runtime domains;
- no-character startup routing to Character Creation / Import rather than default-character auto-restore;
- Quick Create and Advanced Create paths that produce the same file-first workspace format;
- bundled official primary-user-fit starter templates and at least one finished showcase character template;
- RelayLM onboarding knowledge in official starter/showcase templates so default characters can explain workspace basics without becoming development-review characters;
- KV-cache-friendly context tiering that keeps uppercase sources stable and pushes state/retrieval to dynamic suffixes;
- Character Workspace UI surfaces for Character, Scenes, Relationships, Memory Wiki, Runtime, and Advanced diagnostics;
- Primary MEM formation from trusted scene-qualified managed requests and from the E1-R1 route-owned trusted Home gate when explicitly enabled;
- speaker-provenance-safe Primary MEM formation summary so assistant acknowledgement/speculation and scene/trust qualification are not promoted to user facts;
- later-turn Primary MEM retrieval and RelayCTX injection through the M2-preferred path plus the bounded E1-R5 scoped Primary candidate bridge when M2 yields no eligible scoped Primary candidate;
- request-side retrieval-response grounding and unsupported-detail suppression for recalled Primary MEM evidence;
- ordinary retrieval exclusion for hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, and prior physical revisions;
- explicit user-visible archive/forget/correct/merge-style memory operations, backed by existing governance where applicable;
- proposal paths for high-risk source changes, including SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY and important `relationships/<target>.md` parameters;
- durable finalization evidence before protected visible release;
- one-record restart replay, retention/isolation cleanup, and crash validation;
- bounded local operation that can drain eligible replay and queue work through explicit caller-invoked rounds;
- caller-invoked O1E stale-recovery/cancellation/shutdown controls and O1F operational validation;
- dry-run-first character-store bootstrap for local evaluation.

MVP does not include:

- browser-owned trusted admission or frontend self-asserted persistence policy;
- always-on daemon/service supervision unless a later explicit MVP gate proves it is required;
- voice, TTS execution, avatar, Live2D, ASR, or peer communication transport;
- full Obsidian plugin behavior;
- one-file-per-memory user-facing storage;
- uncontrolled SLP auto-mutation of uppercase character sources;
- default active character auto-creation or auto-restore;
- unbounded third-party template execution;
- RelayLM-development-specific design partner as the default template shelf;
- physical secure erasure or purge semantics beyond explicit target contracts;
- experimental SOUL replacement or synthetic memory bootstrap.

## MVP completion criteria

MVP completion criteria retain the completed Phase I-2 observation boundary: read-only observation of latest runs, formed memory, held or blocked outcomes, lifecycle state, and used-memory evidence.

For the file-first Character Workspace reset, MVP completion additionally requires that the target Character Workspace surfaces and projections remain clearly separated from current implementation status until the dedicated implementation slices land.

## MVP execution lanes

```text
Completed runtime and governance foundation
  I-4E Forget API/UI                              complete
    -> I-4F Forget validation                     complete
    -> I-5A Pin / Unpin contract/preflight        complete
    -> I-5B Pin / Unpin apply/API/UI/ranking work complete
    -> I-7A/B Held Apply/Discard preflight        complete
    -> I-7C Held Apply/Discard runtime/API/UI/durable evidence complete

Analyzer Candidate Governance
  ACG-0 P0 RelayREL / RelaySCN / RelayEMO ordering boundary complete
    -> ACG-1 Analyzer Candidate Governance contract complete
    -> ACG-2 Grounded Recall Query Detail Analyzer complete
    -> ACG-3 RelayMEM Query Analyzer / Retrieval Hint Normalization complete
    -> ACG-4 RelayREF / RelayINT Reference Analyzer consolidation
    -> ACG-5 RelayEMO scene ownership cleanup
    -> ACG-6 SCN structured classifier and scene-wiki integration

Character Workspace reset
  CW-A1 file-first source tree and parser contracts
    -> CW-A2 workspace compiler projections and KV-cache tiers
    -> CW-A3 Character Workspace UI rebuild
    -> CW-A4 SLP-maintained MEM/SCENE/REL wiki candidates and proposals
    -> CW-A5 character creation, templates, and showcase import

Operations
  O1D2 bounded scheduler policy/fairness/pacing complete
    -> O1E stale recovery/cancellation/shutdown complete
    -> O1F operational validation               complete
    -> O2 supervised worker service, only if required
    -> O3 always-on local operation, only if required

Evaluation
  E1 evaluation consolidation                    complete
    -> E1-R1 trusted Home scene-admission path         complete
    -> E1-R2 idempotent character-store bootstrap command complete
    -> E1-R3 provenance-preserving Primary MEM formation summary complete
    -> E1-R4 retrieval-response grounding and unsupported-detail suppression complete
    -> E1-R5 Primary MEM recall candidate discovery bridge complete
```

## MVP dependency waves

### Foundation already available for MVP planning

The current MVP plan assumes the completed foundations listed in [Project Status](../PROJECT_STATUS.md): Phase 6 through C2/O0, UI-B0 real Home conversation, Phase I-2 observation, Phase I-3 Correct, I1-GA through I1-GE, I-4B through I-4F, O1A through O1F, UI-B1A, I-5A/I-5B, I-7A/B/I-7C, E1, E1-R1, E1-R2, E1-R3, E1-R4, E1-R5, P0-PIPE, ACG-1, ACG-2, and ACG-3.

### Wave 4 completed

```text
O1D2 bounded scheduler policy/fairness/pacing
I-4E loopback API and SOUL Lab Forget UI
UI-B1A read-only lifecycle visibility
I-5A Pin / Unpin contract/preflight
I-7A/B Held Apply / Discard contract/preflight
```

The frozen Wave 4 completion record is [Wave 4 Cross-Slice Convergence Audit](wave4_cross_slice_convergence_audit.md). The frozen Wave 4 start contracts remain recorded in [Wave 3 Cross-Slice Convergence Audit](wave3_cross_slice_convergence_audit.md).

### Wave 5 completed

```text
E1 evaluation consolidation
O1E stale recovery/cancellation/shutdown complete
I-4F crash/race/security/fresh-conversation validation
```

The Wave 5 convergence record is [Wave 5 Cross-Slice Convergence Audit](wave5_cross_slice_convergence_audit.md). Wave 5 closes the immediate post-Wave-4 validation/evaluation/operational-control gap without opening polling, service supervision, Pin/Unpin runtime apply, Held Apply/Discard runtime, direct Home-origin trusted formation, or O2/O3.

### O1F validation completed

```text
O1F operational validation
  -> corruption / concurrency / saturation / restart / leakage validation
  -> validation-only hardening over caller-invoked O1E/O1D2/O1D1
  -> no polling, sleep, service supervision, worker pool, or always-on operation
```

The O1F completion report is [O1F completion report](../mvp/wave6/o1f_completion_report.md). O1F completion allows O2/O3 to be considered later, but it does not itself prove that supervised or always-on operation is required for MVP.

### Post-O1F next candidates

This historical transition anchor records the candidate set that existed after O1F and before the later Wave 6, Wave 7, and E1-R5 implementation merges. It is kept so frozen convergence smokes can verify the transition while the current next-work list is the Character Workspace reset plus Post-E1-R5 / Post-Wave-7 debt registry.

```text
I-5B Pin / Unpin apply/API/UI/ranking work                 complete in Wave 6
I-7C Held Apply/Discard runtime/API/UI/durable evidence    complete in Wave 6
E1-R1 trusted Home scene-admission path                    complete in Wave 6
E1-R2 idempotent character-store bootstrap command         complete in Wave 6
E1-R3 provenance-preserving Primary MEM formation summary  complete in Wave 7
E1-R4 retrieval-response grounding and unsupported-detail suppression complete in Wave 7
E1-R5 Primary MEM recall candidate discovery bridge        complete post-Wave-7
O2/O3 only after explicit MVP need
```

### Wave 6 completed

```text
I-5B Pin / Unpin apply/API/UI/ranking work
I-7C Held Apply/Discard runtime/API/UI/durable evidence
E1-R1 trusted Home scene-admission path
E1-R2 idempotent character-store bootstrap command
```

The Wave 6 convergence record is [Wave 6 Cross-Slice Convergence Audit](wave6_cross_slice_convergence_audit.md). Wave 6 closes the primary remaining user-governance and local-evaluation ergonomics gaps without adding O2/O3, browser-owned trust, semantic summary-quality changes, RelaySOUL mutation, or media runtime execution.

### Wave 7 completed

```text
E1-R3 provenance-preserving Primary MEM formation summary
  -> user assertion evidence remains distinguishable
  -> assistant acknowledgement/speculation is not promoted to user fact
  -> scene/trust evidence remains qualification metadata
  -> public diagnostics remain content-free

E1-R4 retrieval-response grounding and unsupported-detail suppression
  -> backend-bound grounded recall context
  -> unsupported date/name/preference/quantity/relationship/cause suppression
  -> public diagnostics remain content-free
```

The Wave 7 convergence record is [Wave 7 Cross-Slice Convergence Audit](wave7_cross_slice_convergence_audit.md). Wave 7 closes the post-Wave-6 E1 evidence-quality lane without adding O2/O3, post-hoc visible response rewriting, browser-owned trust, semantic mutation authority, RelaySOUL mutation, or media runtime execution.

### Post-Wave-7 E1-R5 correction completed

```text
E1-R5 Primary MEM recall candidate discovery bridge
  -> M2 remains the preferred relevance owner
  -> bounded scoped Primary index/log/page fallback only when M2 yields no eligible scoped Primary candidate
  -> shared I-4D lifecycle eligibility still excludes hidden/prepared/recovery/corrupt/prior/cross-scope candidates
  -> public diagnostics remain content-free
```

The E1-R5 handoff is [E1-R5 Primary MEM Recall Candidate Bridge](e1r5_primary_mem_recall_candidate_bridge.md), the completion report is [E1-R5 completion report](../mvp/wave7/e1r5_completion_report.md), and the post-correction convergence record is [E1-R5 Post-Wave-7 Correction Convergence Audit](e1r5_post_wave7_correction_convergence_audit.md). E1-R5 corrects the E1 proof boundary; current docs must not claim that M2 alone always selects current eligible scoped Primary MEM.

### P0-PIPE ordering correction completed

```text
P0 RelayREL / RelaySCN / RelayEMO ordering
  -> RelayREL runs before RelaySCN
  -> RelaySCN no longer consumes RelayEMO artifact scene_state as fallback
  -> input-side RelayEMO runs after RelaySCN
  -> RelayINT, RelayMEM, and RelayCTX remain downstream
  -> public diagnostics remain content-free
```

The P0-PIPE handoff is [P0 RelayREL / RelaySCN / RelayEMO Ordering Fix](p0_relayrel_relayscn_relayemo_ordering_fix.md). This closes PM-D3 because the request path is rewired and validated, not merely because helper/projection code exists.

### ACG-1 Analyzer Candidate Governance completed

```text
ACG-1 Analyzer Candidate Governance contract
  -> shared candidate-vs-authoritative fields
  -> English-only schema keys / enum values / reason IDs
  -> fail-closed handling for invalid, low-confidence, or ambiguous analyzer output
  -> content-free public projection helpers
```

The ACG-1 handoff is [ACG-1 Analyzer Candidate Governance Contract](acg1_analyzer_candidate_governance_contract.md). ACG-1 establishes the shared contract/helper layer only; it does not implement the remaining ACG-4 through ACG-6 analyzer producers/classifiers.

### ACG-2 Grounded Recall Detail Safety completed

```text
ACG-2 Grounded Recall Query Detail Analyzer
  -> remembered-detail detection is a structured analyzer candidate artifact
  -> regex/heuristic checks remain fallback candidates, not distributed authority
  -> unsupported-detail suppression remains restrictive-only
  -> public diagnostics remain content-free
```

The ACG-2 handoff is [ACG-2 Grounded Recall Detail Safety](acg2_grounded_recall_detail_safety.md). ACG-2 closes the Grounded Recall detail-safety slice without adding post-hoc visible response rewriting, memory mutation, worker/scheduler behavior, or broad retrieval authority.

### ACG-3 Retrieval Query Normalization completed

```text
ACG-3 RelayMEM Query Analyzer / Retrieval Hint Normalization
  -> whitespace splitting is a fallback candidate, not the semantic owner
  -> bounded backend-private retrieval hints are produced behind an analyzer boundary
  -> E1-R5 fallback bridge consumes private hints without exposing public term hints
  -> public retrieval diagnostics remain content-free
```

The ACG-3 handoff is [ACG-3 Retrieval Query Normalization](acg3_retrieval_query_normalization.md). ACG-3 closes the retrieval-query normalization slice without adding broad retrieval, memory mutation, lifecycle bypass, worker/scheduler behavior, or raw-query public leakage.

### Post-E1-R5 / Post-Wave-7 next candidates

Compatibility anchor for E1 evaluation consolidation smokes. The P0 RelayREL / RelaySCN / RelayEMO ordering fix, ACG-1 governance contract, ACG-2 detail-safety boundary, and ACG-3 retrieval-query normalization boundary are complete.

Before the Character Workspace reset implementation begins, RelayLM should execute the remaining highest-priority Analyzer Candidate Governance sequence recorded in [Analyzer Candidate Governance and Multilingual Schema Policy](analyzer_candidate_governance.md). This prevents the next product layer from inheriting multilingual free-text keyword ownership across RelaySCN, RelayINT, RelayREF, RelayMEM, and RelayEMO.

```text
ACG-0 P0 RelayREL / RelaySCN / RelayEMO ordering boundary: complete
  -> RelayREL precedes RelaySCN
  -> RelaySCN lexical heuristics remain non-authoritative
  -> public diagnostics remain content-free

ACG-1 Analyzer Candidate Governance contract: complete
  -> shared candidate-vs-authoritative fields
  -> English-only schema keys / enum values / reason IDs
  -> fail-closed handling for invalid, low-confidence, or ambiguous analyzer output

ACG-2 Grounded Recall Query Detail Analyzer: complete
  -> date/name/preference/quantity/relationship/cause detection behind a structured artifact
  -> existing regex checks are fallback candidates, not distributed authority

ACG-3 RelayMEM Query Analyzer / Retrieval Hint Normalization: complete
  -> whitespace splitting is fallback candidate behavior, not semantic ownership
  -> language-tolerant bounded private hints feed read-only retrieval paths

ACG-4 RelayREF / RelayINT Reference Analyzer consolidation
  -> one reference/continuation/prior-memory request artifact
  -> locale markers become fallback candidate signals

ACG-5 RelayEMO scene ownership cleanup
  -> affect/expression ownership only
  -> any scene hint remains a non-authoritative candidate

ACG-6 SCN structured classifier and scene-wiki integration
  -> only after the authority contract and memory-safety analyzer boundaries land
```

### Character Workspace reset next candidates

```text
CW-A1 file-first source tree and parser contracts
  -> SOUL.md / STYLE.md / EMOTION.md / SCENE.md / RELATIONSHIP.md / MEMORY.md / BOUNDARY.md
  -> relationships/<target>.md / scenes/**/*.md / memory/**/*.md
  -> .relaylm/sources / .relaylm/state / .relaylm/build domains
  -> no one-file-per-memory assumption

CW-A2 workspace compiler projections and KV-cache tiers
  -> uppercase source stable prefix
  -> selected relationship/scene/memory semi-stable tier
  -> current state/retrieval/current input dynamic suffix
  -> content hash and fragment-id preservation

CW-A3 Character Workspace UI rebuild
  -> Character / Scenes / Relationships / Memory Wiki / Runtime / Advanced
  -> Pin / Unpin and queue details moved to Advanced/internal governance

CW-A4 RelaySLP workspace maintenance
  -> MEM inbox/page candidates
  -> SCENE inbox/page candidates
  -> REL update candidates
  -> high-risk uppercase changes as proposals only

CW-A5 character creation, templates, and showcase import
  -> no-character startup to creation/import flow
  -> Quick Create / Advanced Create
  -> primary-user-fit starter templates
  -> finished showcase character templates
  -> RelayLM onboarding knowledge in official templates
  -> content-only external import validation
```

### Post-E1-R5 / Post-Wave-7 decision debt registry

```text
Post-MVP decision debt registry:
  PM-D1 RelaySOUL gate design-freeze relation
  PM-D2 RelayINT -> RelayMEM relayref_artifact legacy compatibility scope
  PM-D3 RelayEMO/RelaySCN scene_state ownership: complete in PR #458
    -> Execute the existing RelaySCN-owned `scene_state` migration plan is now complete through PR #458; closed only after app.py was rewired and validation passed; it must not be reopened by future analyzer or Character Workspace work
  PM-D4 client history exclusion default-off deployment decision
  PM-D5 RelayMEM flat-store compatibility removal
  PM-D6 RelayINT native artifact / RelayREF wrapper removal
  PM-D7 runtime install hook fold-in
  PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in
  PM-D9 analyzer candidate governance and multilingual schema policy
    -> ACG-1 through ACG-3 are complete; execute ACG-4 before SCN structured classifier / scene-wiki work because reference/intent ownership remains a multilingual interpretation dependency

Implementation order for large compatibility removals:
  PM-D5 -> PM-D6 -> PM-D7
  PM-D8 should be evaluated with PM-D5 when Primary recall layout discovery or adapter/root handling is touched
  PM-D2 closure or absorption after PM-D6 if the RelayREF wrapper removal eliminates the remaining legacy artifact scope

O2 supervised worker service, only if required
  -> O3 always-on local operation, only if required

Static SOUL Lab bundle serving, only if required for local MVP packaging
```

O2/O3 should remain after the evidence-quality gates unless a concrete evaluation requirement proves that supervised or always-on operation is necessary before local MVP evaluation.
