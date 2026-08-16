---
relaylm_doc_type: current_target_migration
relaylm_authority: relaymem_relayslp_current_target
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayMEM or RelaySLP producer consumer boundary changes
  - Phase 6 deferred orchestration slice lands
  - durable MEM persistence apply state changes
  - ordinary-runtime worker integration changes
  - I1-G or O1/O2/O3 boundary changes
  - E1 evaluation evidence boundary changes
  - RT-1 writer or reader cutover decisions change
  - RT-1D-R5 or R6 retirement disposition changes
  - accepted Subjective MEM target timing changes
relaylm_not_authoritative_for:
  - repository-wide phase sequencing or exact current transaction state
  - exact RelayMEM or RelaySLP schemas
  - exact RT-1 durable cutover state or R5/R6 retirement approval
  - RelaySOUL approval contracts
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0003-subjective-mem-direction.md
  - ../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - current_target_migration_guide.md
  - runtime/request-response-pipeline.md
  - runtime/scheduler.md
  - memory/formation.md
  - o1f_operational_validation.md
  - o2_supervised_scheduler_service.md
  - o3_always_on_local_scheduler.md
  - pm_d5_relaymem_flat_store_compatibility_removal.md
  - pm_d6_relayint_native_artifact_relayref_wrapper_removal.md
  - pm_d7_runtime_install_hook_fold_in.md
  - phase_i4d_primary_retrieval_exclusion.md
  - memory/pinned-memory.md
  - ../contracts/memory/held-governance.md
  - integration_i1_primary_mem_two_turn_recall.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - e1r3_provenance_preserving_primary_mem_formation_summary.md
  - ../contracts/grounded-recall.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - e1_evaluation_consolidation.md
  - ../evidence/waves/wave7_cross_slice_convergence_audit.md
  - ../evidence/waves/wave6_cross_slice_convergence_audit.md
  - ../PROJECT_STATUS.md
---
# RelayMEM / RelaySLP Current / Target Boundary

Last reviewed: 2026-08-08 JST

## Current implemented boundary

RelayMEM and RelaySLP retain the durable queue, worker, lifecycle, evaluation, and compatibility capabilities recorded below, but RT-1D-R4 now dominates the interpretation of ordinary memory serving. The ordinary Retrieval facade resolves exactly one reader authority before touching a memory family:

```text
primary_only
  -> retained Primary compatibility reader only

neither
  -> no ordinary durable-memory reader

subjective_only
  -> finalized Subjective reader only
  -> no Primary root resolution, discovery, recall, ranking, or fallback
```

Primary and Subjective are never ordinary co-authorities for one request. Configuration, store presence, historical Primary success, an empty or failed Subjective result, or a grounding status cannot select or restore reader authority. Primary-layer mutation is independently governed by the exact RT-1 writer decision and is permitted only strictly before the durable `primary_writer_fenced` state. A stale token, old worker, old lifecycle receipt, or caller-supplied decision cannot authorize a Primary write after that fence.

RT-1D-R4 and its mandatory P8 are complete. RT-1D-R5 immediate retirement remains unstarted in the current status authority. R5/R6 therefore own the final removal or retained read-only disposition of replaced Primary ordinary-reader/fallback surfaces and temporary cutover execution surfaces; this document does not pre-authorize those deletions.

The Phase 6 execution boundary remains implemented through B0-B3, C1-5, and C2, with O0 as the explicit local caller:

```text
B0 durable queue contract
B1 dispatch preflight
B2 atomic durable enqueue
B3 queue claim/lease/retry/terminal lifecycle
C1-0 exact current-claim protected source
C1-1 canonical M3a-M3h compose
C1-2 lease-fenced one-already-claimed worker
C1-3 pure outcome classification
C1-4 integrated fault/crash convergence
C1-5 durable claim-independent protected source and restart rehydration
C2 one-job claim/rehydrate/execute adapter
O0 one invocation -> at most one eligible queued job
```

Phase 6-B2 performs atomic durable enqueue through the existing content-free queue record authority. Phase 6-B3 performs default-off, dry-run-first fenced queue lifecycle transitions. C1-2 executes one already-claimed canonical B3 job. C1-5 persists protected content separately from the content-free queue. C2 accepts one caller-selected queued record and connects B3 claim, C1-5 preparation, and C1-2 execution. O0 adds bounded discovery and one C2 delegation without polling or retry scheduling. These capabilities remain implementation and operational evidence; they do not override the RT-1 writer fence or reader decision.

I2 real SOUL Lab observation is complete. It remains read-only evidence only and cannot authorize repair, mutation, retrieval, or a reader transition.

E1 evaluation consolidation remains current as an evidence/documentation boundary. E1-R1 route-owned trusted Home scene admission and E1-R2 dry-run-first character-store bootstrap remain current implemented bounded capabilities. E1-R3 remains implemented provenance-preserving formation-summary evidence in the Primary compatibility lineage. E1-R4 remains the live common one-authority request-side grounding policy. E1-R5 remains implemented only as bounded Primary-only compatibility fallback behavior while the exact reader decision is `primary_only`; it is not a Subjective failure fallback and cannot run under `subjective_only`.

PM-D5, PM-D6, PM-D7, and PM-D8 remain completed post-MVP compatibility/debt slices. PM-D5 removed legacy flat-store runtime discovery. PM-D6 made the input-side RelayINT artifact native instead of RelayREF-wrapper-shaped. PM-D7 added the explicit dry-run-first runtime install/preflight command. PM-D8 folded the bounded E1-R5 behavior into canonical Primary recall; RT-1 subsequently confines that folded behavior behind the exact `primary_only` reader branch, and R5/R6 own its final retirement disposition.

## Accepted target boundary after ADR 0004

The accepted target does not require Shared Assessment or Subjective MEM formation to complete inside the current conversation turn.

```text
ordinary managed no-tool response path
  -> one Main LLM response-generation call
  -> streaming user / TTS / avatar output
  -> response-complete assistant Evidence and RelayREF observation

out-of-band reference formation path
  -> governed Evidence references
  -> RelaySLP episode or bounded evidence-group Assessment Pass
  -> validated character-independent Shared Assessment
  -> RelaySLP Subjective Formation Pass with SOUL / MEMORY / BOUNDARY
  -> gated RelayMEM / workspace commit or hold
```

The retained Primary worker and queue implementation is implementation evidence and a migration/compatibility base. It does not, by itself, define the final Subjective MEM, Shared Assessment, episode grouping, storage-authority schema, current reader authority, or post-fence Primary mutation authority.

Target invariants:

- Protected Source Evidence remains durable independently of response and formation success.
- Finalized assistant-origin Evidence remains distinct from RelayREF response observation and never becomes user-origin fact through retention.
- RelayCTX owns current/session continuity and temporary correction or recall-suppression overlays, not durable pending MEM.
- RelayMEM Retrieval remains read-only in the interactive path.
- Exactly one ordinary durable-memory reader may be selected for one request; no dual serving or cross-authority fallback is permitted.
- RelaySLP preferably groups several related turns before formation when later qualification or correction is likely to improve coherence.
- The reference path validates a SOUL-independent Shared Assessment before SOUL-conditioned Subjective Formation.
- A fused SLP call is evaluation-gated optimization only and must fail closed to the split path when equivalence or SOUL-contamination boundaries are not met.
- Additional LLM adjudication is an optional deferred SLP exception and never blocks conversation.
- Current-conversation correction is best-effort CTX input control; it is not a guarantee about probabilistic Main LLM output.
- Natural-language conversational “forget” defaults to session-local suppression when durable management authority was not invoked.
- Durable lifecycle-management capabilities remain governed by their canonical owners and exact cutover writer decision; no historical token or UI path may bypass `primary_writer_fenced` for a Primary-layer mutation.
- RelayRUN separates control-plane mutation fences from compute/resource priority; semantic fallback remains owned by the applicable RelaySLP/RelayMEM policy under the selected authority.
- Explicit pass-through disables managed memory behavior by default unless a separate route contract opts in.

Current implementation status remains owned by Project Status. This accepted target is not a claim that every target schema, runtime migration, or retirement step is already implemented.

## I1-G durable-finalization boundary

I1-GA through I1-GE are complete. I1-G completion means sealed evidence, exact C1-5 source, exact B2 queue correlation, durable completion, retention/isolation lifecycle, and crash-at-every-boundary validation. It does not imply B3 terminal success, C2 execution, worker execution, current Primary writer permission, current Primary reader permission, semantic quality, retrieval use, automatic scheduling, polling, supervision, or always-on operation.

## O1/O2/O3 scheduler boundary

O1A defines a pure scheduler contract. O1B and O1C bounded production discovery and delegation are complete. O1D1 accepts the five exact scheduler gates, invokes O1B then O1C at most once each, aggregates through O1A, validates the content-free projection, and returns without sleeping.

O1D2 is current implemented as a bounded policy wrapper around the existing O1D1 one-round scheduler coordinator. O1D2 itself does not poll, sleep, run a second round, recover stale claims, handle cancellation, supervise services, or create a durable scheduler journal.

O1E is current implemented as a bounded caller-invoked operational-control layer. One explicit call may check cancellation, optionally orchestrate at most one B3 stale-recovery transition through existing B3 authority, invoke at most one O1D2/O1D1 scheduler round, and return a bounded content-free projection. O1E does not poll, sleep, loop, daemonize, supervise, create background workers, start timers, or rewrite queue records directly.

O1F is current implemented as validation-only hardening over the caller-invoked O1E/O1D2/O1D1 stack. It validates corruption, concurrency, saturation/boundedness, restart reread, cancellation/shutdown projection, and leakage boundaries. O1F does not poll, sleep, loop, supervise, create workers, or itself implement local always-on operation.

O2 is current implemented as an opt-in supervised local scheduler service above O1E. O3 is current implemented as an opt-in local CLI/process wrapper around O2. O2/O3 are not app-embedded, not browser authority, not default-on, and do not add memory mutation, queue, worker, stale-recovery, durable-finalization, or RT-1 reader/writer authority.

## Current Primary mutation and lifecycle-read boundary

The historical Primary lifecycle and management slices remain implemented capabilities and regression evidence, but their current ordinary-serving effect is subordinate to the exact RT-1 decisions.

For ordinary reads:

- `primary_only` may use the retained Primary compatibility reader and its exact lifecycle/currentness filtering;
- `neither` reads no ordinary durable-memory authority;
- `subjective_only` resolves no Primary root and performs no Primary lifecycle discovery, recall, ranking, or fallback.

For Primary-layer writes, the exact writer decision must still permit mutation. Once durable state reaches `primary_writer_fenced`, an old Correct/Forget, Pin/Unpin, Held Apply/Discard, worker, recovery, UI, API, or token path cannot restore Primary mutation authority. This fence does not erase historical records and does not by itself decide which explicitly read-only management/history consumers survive R5/R6.

I-4E remains implemented loopback Forget API/UI product work and I-4F remains implemented validation-only Forget product-completion evidence. I-4F proves crash/fault recovery, one-winner races, Correct/Forget stale races, strict token binding, loopback/security leakage boundaries, stale-browser response fencing, no implicit UI apply triggers, fresh process reread, fresh ordinary-conversation exclusion, and multi-scope isolation over its owning lifecycle authorities. Those completion facts do not bypass a later RT-1 writer fence.

UI-B1A remains implemented read-only visibility. I-5A remains implemented contract/read-only preflight. I-5B remains implemented Pin/Unpin apply/API/UI/ranking behavior. I-7A/B remains implemented contract/read-only preflight. I-7C remains implemented Held Apply/Discard runtime/API/UI/durable governance evidence. These implementation facts are capability/history statements rather than independent current reader/writer authorization.

I-5B Pin state remains governance metadata and a ranking hint. It never admits hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions and cannot select an ordinary reader. I-7C persists content-free decision evidence for already-held candidates and does not start workers, schedulers, retry loops, C2, O1, or B3 transitions from the UI.

## E1 evidence-quality boundary

E1-R3 remains implemented as speaker-provenance-safe Primary formation-summary construction in the retained Primary compatibility lineage. It keeps user assertion evidence separate from assistant acknowledgement/speculation and route-owned scene/trust qualification. Its implementation does not itself grant current Primary writer permission.

E1-R4 remains current as the common request-side retrieval-response grounding and unsupported-detail-suppression policy for **already selected ordinary memory evidence**. RelayCTX repack first observes the exact `ordinary_memory_authority`; only then does E1-R4 consume selected memories from that named family. `primary_only` may supply Primary compatibility evidence, `subjective_only` supplies only admitted/finalized Subjective evidence, and any other/malformed authority supplies none. E1-R4 never combines the two families, selects reader authority, or falls back from failed/empty Subjective retrieval to Primary. Its private backend context remains bounded and its public projection remains content-free.

E1-R5 remains implemented as a bounded scoped Primary recall fallback only inside an exact `primary_only` decision. M2 remains the preferred relevance owner in that compatibility branch. When no eligible scoped Primary candidate survives M2 narrowing, the folded E1-R5 behavior may derive bounded candidates from exact character-scoped Primary index/log/page controls, apply lifecycle eligibility, require query relevance, and rebuild the existing E1-R4 handoff shape. It cannot execute under `subjective_only`, cannot become a second ordinary reader, and cannot act as Subjective failure or empty-result fallback. R5/R6 own its final retirement disposition.

## Completed Primary MEM integration

This section is a completed implementation and regression inventory. It must not be read as an unconditional ordinary runtime path after RT-1D-R4.

```text
historical / compatibility formation path
  -> I1-B request-runtime A1/A2/B1                     complete
  -> C1-5 protected source then B2 queue               complete
  -> B3 queue claim/lease/retry lifecycle              complete
  -> O0 explicit local selection and one C2 call       complete
  -> C2/C1 worker path and verified Primary MEM        complete
  -> Primary-layer formation only while writer decision permits

later ordinary request
  -> exact RT-1 reader decision first
  -> primary_only: M2-preferred Primary compatibility retrieval
       -> bounded E1-R5 fallback only after eligible scoped M2 miss
       -> exact Primary lifecycle/currentness filtering
  -> neither: no ordinary durable-memory retrieval
  -> subjective_only: finalized Subjective retrieval only; no Primary read/fallback
  -> E1-R4 common one-authority grounded recall

completed supporting slices / historical evidence
  -> real Lab observation                              complete as I-2
  -> audited correction and corrected retrieval        complete as I-3
  -> canonical read-only lifecycle resolution          complete as I-4B
  -> hidden-successor lifecycle commit                 complete as I-4C1
  -> prepared recovery and tombstone finalization      complete as I-4C2
  -> ordinary retrieval exclusion and lifecycle overlay complete as I-4D
  -> loopback Forget API/UI over existing authorities  complete as I-4E
  -> full Forget product validation                    complete as I-4F
  -> read-only lifecycle visibility                    complete as UI-B1A
  -> Pin / Unpin read-only preflight                   complete as I-5A
  -> Pin / Unpin apply and ranking hint                complete as I-5B
  -> Held Apply / Discard read-only preflight          complete as I-7A/B
  -> Held Apply / Discard runtime governance           complete as I-7C
  -> E1 evidence consolidation                         complete as E1
  -> route-owned trusted Home admission                complete as E1-R1
  -> dry-run-first character-store bootstrap           complete as E1-R2
  -> provenance-preserving formation summary           complete as E1-R3
  -> one-authority grounded recall response             complete as E1-R4
  -> bounded scheduler operational controls            complete as O1E
  -> operational validation hardening                  complete as O1F
  -> opt-in supervised local scheduler service         complete as O2
  -> opt-in local CLI/process wrapper                  complete as O3
  -> target-only RelayMEM store discovery              complete as PM-D5
  -> native input-side RelayINT artifact               complete as PM-D6
  -> explicit runtime install/preflight command        complete as PM-D7
  -> canonical Primary fallback fold-in history        complete as PM-D8
```

The historical Phase I-1/I-4D/E1-R5/PM-D8 completion chain therefore proves what the Primary implementation did and what must remain regression-safe during retirement. It does not keep Primary ordinary serving authoritative after the exact reader decision selects `subjective_only`, and it does not keep Primary mutation authoritative after `primary_writer_fenced`.

## Completion interpretation

M3a-M3h, B0-B3, C1-0 through C1-5, C2, O0, I1-GA through I1-GE, O1A through O1F, O2, O3, I-1 recall, I-2 observation, I-3 Correct, I-4B, I-4C1, I-4C2, I-4D, I-4E, I-4F, UI-B1A, I-5A, I-5B, I-7A/B, I-7C, E1, E1-R1, E1-R2, E1-R3, E1-R4, E1-R5, PM-D5, PM-D6, PM-D7, and PM-D8 are implemented as recorded by their owning authorities. Later RT-1 cutover work changes the serving/mutation interpretation of some of those completed Primary slices; it does not erase their implementation history.

RT-1D-R4 one-authority activation and its mandatory P8 are complete. Current ordinary serving is therefore decided only by the exact RT-1 reader state: `primary_only`, `neither`, or `subjective_only`. There is no dual serving and no Primary fallback from `subjective_only`. Current Primary-layer mutation permission is separately bounded by the exact writer decision and ends at `primary_writer_fenced`.

RT-1D-R5 immediate retirement remains unstarted in Project Status. R5/R6 own retirement of replaced Primary ordinary-reader/fallback surfaces, temporary rehearsal/shadow execution surfaces, and final disposition of explicitly read-only historical/operational Primary consumers. This document records that dependency but does not authorize deletion ahead of the owning retirement transaction.

O1F remains validation-only caller-invoked operational hardening. O2 and O3 remain opt-in local operation layers that are explicit operator-invoked and default-off. E1-R1 remains route-owned and defaults disabled; it does not permit browser-owned trust. E1-R2 remains dry-run-first and does not create semantic memory content. E1-R3 remains speaker-provenance-safe formation-summary work. E1-R4 remains the common storage-neutral grounding policy after one-authority selection and does not perform post-hoc visible-response rewriting or create mutation authority. E1-R5 remains bounded Primary-only fallback compatibility and does not replace M2 as preferred relevance owner or add broad retrieval/mutation/scheduler authority. PM-D5 removes legacy flat-store runtime discovery. PM-D6 removes the input-side RelayREF-shaped RelayINT wrapper. PM-D7 adds explicit dry-run-first runtime install/preflight support only. PM-D8 records the historical E1-R5 fold-in but cannot bypass the RT-1 reader fence.
