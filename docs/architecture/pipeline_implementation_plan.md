---
relaylm_doc_type: implementation_plan
relaylm_authority: implementation_status_and_phase_sequencing
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - phase lands
  - sequencing changes
  - an integration milestone changes state
  - a target-only schema gains producer consumer apply skip block contract projection and smoke coverage
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - phase5_5_stream_unpack_bounded_slice.md
  - phase6_async_relayslp_bounded_slice.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_primary_worker_outcome_classifier.md
  - phase6c1_integrated_worker_fault_smoke_handoff.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - o0_local_one_job_runner.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - phase_i4b_primary_current_state_shared_fence.md
  - soul_lab_ui_b0_real_home_conversation.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - post_i3_evaluation_work_roadmap.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

Last reviewed: 2026-06-26 JST

## Purpose

This document owns implementation status, phase sequencing, dependency boundaries, and active integration priority. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact schemas remain in dedicated contracts, current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md), and the dependency-first post-I3 sequence remains in [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md).

RelayLM is integration-first. Helper-only or mock-only slices are justified only when they unblock an end-to-end milestone or close a demonstrated safety defect.

## Status legend

- **complete**: bounded contract and intended wiring exist with smoke coverage;
- **defined target**: exact contract exists, but production producer/consumer/apply/UI behavior is incomplete;
- **integration pending**: components exist but the ordinary product path is not connected;
- **planned**: design or need exists without a complete producer/consumer/apply/validation path;
- **current implementation work**: an active bounded slice is being implemented but is not complete;
- **deferred**: intentionally not a gate for the active milestone.

## Current position

```text
Phase 5-C managed-route correctness: complete through bounded v0/v1 apply and C5 plumbing
Phase 5-D pre-stream hardening: complete through D2
Phase 5.5 Stream Unpack / TTS handoff preparation: RelayLM Core complete

Phase 6 asynchronous RelaySLP orchestration:
  A0-A2: complete
  B0-B3: complete
  I1-B ordinary request-runtime enqueue/source capture: complete
  C1-0 through C1-5: complete
  C2 one-job claim/rehydrate/execute adapter: complete
  O0 local one-job runner: complete

RelayMEM Primary integration:
  M1/M2 and M3a-M3h: complete
  I1 next-turn recall and scope isolation: complete
  Phase I-2 observation: complete
  Phase I-3 Correct: complete
  Phase I-4A Forget / Hide contract: defined target
  Phase I-4B resolver/shared fence/read-only Forget boundary: complete
  Phase I-4C through I-4F hidden apply, M2, UI, and validation: unimplemented

SOUL Lab:
  UI-A0 through UI-A7: complete
  Phase I-2 real Observation: complete
  Phase I-3 auditable Correct: complete
  UI-B0 real Home conversation: complete
  UI-B1 lifecycle visibility: planned in read-only and later-operation slices

Operations:
  I1-GA contract / design decision / fault model: complete
  I1-GB durable-finalization publication / pre-release admission: complete
  I1-GC/GD/GE replay, cleanup, and full crash validation: unimplemented
  I1-G overall: in progress
  O0 local one-job runner: complete
  O1 durable-finalization replay and queue scheduler: planned
  O2 supervised worker service: planned
  O3 always-on local operation: planned
```

## Compatibility status anchors

Phase 6-B1 dispatch preflight, B2 atomic durable enqueue, and B3 fenced queue lifecycle are complete.

I1-B ordinary managed non-stream/stream deferred enqueue is complete.

Phase 6-C1-0 through C1-5 are complete:

- exact current-claim protected source;
- exact M3a-M3h composition;
- one-active-claim execution;
- pure outcome classification;
- integrated crash/fault convergence;
- durable claim-independent protected capture and restart rehydration.

Phase 6-C2 one-job claim/rehydrate/execute adapter is complete. It accepts one exact queued canonical record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves bounded retry/terminal behavior without adding queue scanning or a worker service.

O0 local one-job operation is complete. `relaylm-worker --once --config config.yaml` performs bounded non-recursive discovery, selects at most one eligible queued record, securely rereads it, resolves the exact config-owned character partition, and delegates unchanged authority to C2/B3/C1-5/C1-2.

Phase I-1 next-turn recall and scope isolation, Phase I-2 real SOUL Lab observation, Phase I-3 auditable Correct, UI-B0 Real Home Conversation, and the I-4B read-only resolver/shared-fence boundary are complete. I1-GA contract/design/fault-model work and I1-GB pre-release durable publication are complete. I1-GC through I1-GE remain planned; restart replay/completion convergence, cleanup, and full crash validation are unimplemented. Phase I-4A remains the exact Forget / Hide target contract, while I-4C through I-4F remain unimplemented.

## Completed foundation

### Phase 5-C: managed-route correctness — complete for current bounded apply

Current runtime supports no-instruction managed apply and explicit-provenance instruction-bearing apply with conservative gates. Trusted backend-response instruction-control production, complete RelaySCN semantic apply, tool-chain reconstruction, and parser-versioned cache compatibility remain separate.

### Phase 5-D: pre-stream hardening — complete through D2

Pre-stream authority and content safety checks are wired before visible streaming.

### Phase 5.5: Stream Unpack and TTS handoff preparation — complete for Core

Core owns suppression, segmentation hints, adapter handoff metadata, and transport envelope preparation. Actual TTS, audio, avatar, Live2D, and adapter delivery remain outside this milestone.

## Phase 6 asynchronous RelaySLP

### A0-A2: admission and finalized-turn handoff — complete

The ordinary response path may produce a bounded post-response handoff without executing memory formation inline.

### B0-B3: durable queue and fenced lifecycle — complete

Implemented: content-free durable queue record, deterministic dispatch identity, atomic create-if-absent enqueue, exact claim/lease fencing, retry release, stale recovery, and terminal commit.

### I1-B: ordinary request-runtime enqueue/source capture — complete

Ordinary managed non-stream and stream finalization can publish the protected source and enqueue the exact B3 job when explicitly enabled. The visible response path does not claim or execute the job inline.

### C1-0 through C1-5: Primary MEM worker — complete

```text
C1-0  exact protected source and one-shot scope
C1-1  M3a-M3h compose
C1-2  one already-claimed job execution
C1-3  pure outcome classifier
C1-4  fault, lease, race, corruption, and leakage validation
C1-5  durable protected source persistence and restart rehydration
```

### C2: one queued-job integration — complete

```text
exact queued record
  -> canonical B3 claim
  -> C1-5 durable source lookup
  -> fresh C1-0 source/scope
  -> C1-2 execution
  -> retry release or terminal commit
```

C2 does not select among multiple queue records and is not a daemon.

### O0: local one-job runner — complete

```text
relaylm-worker --once
  -> exact config and default-off gates
  -> bounded non-recursive queue discovery
  -> queued / retry-time eligibility
  -> deterministic one-candidate selection
  -> secure canonical reread and race validation
  -> exact character/store partition resolution
  -> one exact C2 request
  -> bounded content-free projection
  -> process exit
```

O0 never reconstructs protected content, performs claim CAS itself, changes retry policy, repairs corrupt records, starts polling, or becomes browser authority.

## Integration Milestone I1

### I1-A: worker prerequisites — complete

B3, C1-0/C1-1/C1-2/C1-3/C1-4/C1-5, and C2 exist with bounded contracts and validation.

### I1-B: ordinary producer wiring — complete

The ordinary managed response path may produce the durable source and queue record under explicit gates.

### I1-C: one exact queued job execution — complete

C2 proves claim, restart rehydration, worker execution, retry/terminal convergence, and terminal-only source cleanup for one exact queued job. O0 supplies the explicit local caller.

### I1-D: next-turn recall validation — complete

Phase I-1 proves Turn 1 formation, Turn 2 M2 discovery, canonical page/index/log validation, exact character/namespace isolation, bounded RelayCTX injection, and backend-bound use.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 provides loopback-only bounded projections for latest run, validated recent Primary memories, held/blocked outcomes, actual backend-bound used-memory evidence, and content-free RelaySLP/RelayRUN/RelayCTX status. Observation evidence is read-only and does not replace Primary MEM, protected source, queue, worker, or mutation authority.

### I1-F / Phase I-3: auditable Primary MEM Correct — complete

Phase I-3 provides exact scope/current-revision validation, bounded semantic diff, short-lived confirmation token, immutable successor page through M3e, M3f/M3g convergence and recovery, durable correction receipt, and later M2 retrieval of only the corrected current revision.

### I1-F2 / Phase I-4A: Primary MEM Forget / Hide contract — defined target

The contract fixes:

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

Candidate A is selected: revision `N active` advances to one immutable successor Primary page at revision `N+1 hidden`, followed by M3f/M3g convergence, retrieval-exclusion verification, and tombstone finalization. The page is lifecycle authority; the tombstone is not an independent sidecar flag.

Correct and Forget must share one per-memory lock namespace, pending-operation fence, operation identity lookup, and revision claim. I-4B now implements the canonical read-only resolver, shared `.lock`/fence, preflight, token validation, and bounded zero-item history. Hidden-successor apply, durable history artifacts/projection, M2 exclusion, loopback routes, and UI remain unimplemented.

### UI-B0: Real Home Conversation — complete

UI-B0 connects SOUL Lab Home to the existing RelayLM Chat Completions route using one server-projected route, same-origin non-stream/SSE transport, explicit Real Runtime versus Local Preview sessions, Stop/Retry/New Conversation, and stale-response fencing.

### I1-G: pre-enqueue durable-finalization — in progress

I1-GA is complete as the target contract, design decision, pure state/fault model, and validation boundary. I1-GB is complete for default-off bounded private base/stream-segment/seal publication, canonical reread validation, exact A1/A2/B1 preparation, non-stream pre-release admission, and stream pre-yield admission. The existing background finalizer remains the only C1-5-then-B2 writer.

```text
I1-GA  contract / fault model                                      complete
I1-GB  durable publication and bounded response-release admission complete
I1-GC  one-record restart replay, exact convergence, completion    unimplemented
I1-GD  retention, orphan reconciliation, and cleanup               unimplemented
I1-GE  full production crash-at-every-boundary integration smoke   unimplemented
```

I1-GB prevents RelayLM from intentionally releasing protected non-stream content, protected SSE units, or terminal stream completion before corresponding restart evidence is canonically durable. It does not discover or replay sealed records after restart, and therefore does not by itself complete Window A recovery.

I1-G is not queue scanning, worker scheduling, or C2 execution. O1 may later call the I1-GC one-record replay contract.

## Phase I-4B through I-4F: Forget / Hide implementation

```text
I-4B  canonical resolver, shared Correct/Forget fence,
       exact read-only preflight/history/token — complete

I-4C  immutable hidden successor, prepared artifact,
       tombstone, exact replay, and forward-only recovery

I-4D  index/log convergence, M2 exclusion,
       historical lifecycle projection

I-4E  loopback API and SOUL Lab Forget UI

I-4F  crash/race/security/fresh-conversation exclusion validation
```

The official I-4C contract remains one phase, but delivery should use:

```text
I-4C1  token/fence/revision ownership, prepared artifact,
       hidden successor and M3e publication

I-4C2  exact replay, prepared resume, forward recovery,
       tombstone finalization and response-loss convergence
```

I-4D is the user-visible semantic commit. Forget must not be described as product-complete before M2 and RelayCTX exclusion are proven.

Physical deletion, secure erase, purge, restore, and unhide remain separate future boundaries.

## O1: two-lane bounded scheduler — planned

O1 must schedule two distinct sources without merging their state machines:

```text
durable-finalization replay lane
  discover one sealed I1-G record
    -> secure reread
    -> one I1-GC call
    -> C1-5/B2 convergence only

queue execution lane
  discover one eligible B2 record
    -> reuse O0 primitives where compatible
    -> one C2 execution
```

Implementation slices:

```text
O1A  bounded work-source scheduling and idle contract
O1B  one eligible I1-G sealed-record discovery and I1-GC delegation
O1C  one eligible B2 discovery and O0/C2 delegation
O1D  ordering, fairness, retry-time, and bounded backoff
O1E  stale-claim orchestration and graceful shutdown
O1F  corruption, concurrency, saturation, restart, and leakage smoke
```

Recommended scheduler order:

```text
bounded sealed replay
  -> bounded queue execution
  -> idle/backoff
```

O1 must not execute a worker during I1-G replay or treat a durable-finalization record as a queue record.

## UI-B1 delivery split — planned

```text
UI-B1A  after I1-GC and I-4D
         conversation/run correlation
         durable-finalization-pending / queued / processing
         formed / held / blocked / failed
         active / hidden / recovery-required
         current revision and fresh-conversation verification

UI-B1B  after I-5 through I-7
         pin/unpin receipts
         merge/supersession lineage
         held apply/discard decisions
         evidence/runtime/mutation authority separation
```

UI-B1A is read-only and remains outside queue, worker, and mutation authority.

## Dependency-first execution waves

### Wave 0 — completed implementation foundation

```text
Thread A  I1-GB durable-finalization publication — complete
Thread B  I-4B resolver/shared fence/read-only Forget — complete
Thread C  O1A scheduling contract only — remains planned
```

I1-GB and I-4B are complete, and their response/I1-B/C1-5/B2/UI-B0 plus I-3 Correct/resolver/M2-equivalence regressions passed on the final I-4B head. Wave 1 is now the active implementation boundary.

### Wave 1 — current: one-record recovery and lifecycle commit ownership

```text
Thread A  I1-GC one-record replay
Thread B  I-4C1 hidden-successor commit ownership
Thread C  O1 lane contract refinement
Thread D  UI-B1A projection design
```

### Wave 2 — forward convergence, cleanup, and automatic bounded operation

```text
Thread A  I1-GD retention/orphan reconciliation/cleanup
Thread B  I-4C2 forward recovery/tombstone
          -> I-4D M2 exclusion/historical projection
Thread C  O1 implementation
Thread D  I-5A and I-7A/B contract work
```

### Wave 3 — production proof and product surfaces

```text
Thread A  I1-GE production crash integration
Thread B  I-4E UI/API -> I-4F validation
Thread C  O1 completion
Thread D  UI-B1A read-only visibility
```

## Governance order after Phase I-4

Phase identifiers stay unchanged, but production order should be:

```text
I-5 Pin / Unpin
  -> I-7 Held Apply / Discard
  -> I-6 Merge / Supersession
```

I-5 and I-7 stabilize single-memory token, receipt, revalidation, and UI patterns. I-6 introduces multi-memory claims and supersession lineage and therefore lands later. I-6 contract work may proceed earlier, but mutation-coordinator production changes should be serialized.

## Integration checkpoints

```text
G1  I1-G complete
    sealed pre-release evidence
      -> restart replay
      -> canonical C1-5/B2 convergence
      -> retention and crash proof

M4  Phase I-4 complete
    active current memory
      -> hidden successor
      -> M2/RelayCTX exclusion
      -> historical evidence preserved

O1  automatic bounded local processing complete
    replay lane + queue lane
    without changing I1-G/B3/C2/M3 authority

E2  governed Primary MEM product
    I-4 through I-7 + UI-B1 + repeatable real conversation
```

## Product evaluation sequence

The explicit E1 evaluation is complete across two proven lanes:

```text
explicit trusted scene-qualified managed request
  -> O0 one-job execution
  -> Primary MEM formation
  -> Phase I-2 observation
  -> Phase I-3 Correct

Home real conversation
  -> existing M2 / RelayCTX recall
  -> Home New Conversation
  -> corrected-memory question
  -> Phase I-2 used-memory evidence
```

Direct Home-origin formation remains unproven because UI-B0 does not send trusted scene-admission metadata.

The loop remains operator-driven until O1 lands.

Recommended next sequence:

```text
completed:
  I1-GB || I-4B

current:
  I1-GC || I-4C1 || O1A design

next:
  I1-GD || I-4C2 -> I-4D || O1 implementation

then:
  I1-GE || I-4E -> I-4F || UI-B1A

then:
  I-5 -> I-7 -> I-6 -> UI-B1B

long-term:
  I-8 -> I-9 -> UI-B2 -> O3 soak
```

I1-G and O1/O2 are mandatory before long-duration formation, multi-day consolidation, or long-term character evidence is treated as reliable.

## Parallel ownership

```text
I1-G    pre-enqueue durable evidence, one-record replay, completion, retention
O1      bounded discovery/scheduling across separate replay and queue lanes
O0/C2   one queued-record execution authority
I-4     lifecycle and Forget mutation semantics
M2      retrieval eligibility and ranking for eligible memory
UI-B1   read-only visibility until exact operation routes separately land
```

UI-B0 owns Home transport and browser session state. No operations phase may move worker or queue authority into the browser.

## Validation boundary

Every phase that changes current behavior must include:

- contract and negative-path validation;
- exact scope, stale, and conflict checks;
- fault/crash/retry convergence where state is durable;
- security and content-leakage checks;
- documentation link/current-boundary checks;
- affected integration regression runners.

Current common validation includes:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
git diff --check
```

O0 validation also includes:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_o0_local_one_job_runner_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_smoke.py
```

Phase I-4A remains the target contract. I-4B validation must prove only the read-only resolver/shared-fence/preflight-token-history boundary and must not imply hidden apply, M2 exclusion, loopback mutation routes, or UI completion.

## Documentation completion rule

When a phase lands, review together:

- `docs/PROJECT_STATUS.md`;
- this implementation plan;
- `docs/README.md`;
- `docs/architecture/README.md`;
- the dedicated handoff/contract;
- [Post-I3 roadmap](post_i3_evaluation_work_roadmap.md);
- `docs/config_schema.md` when configuration changes;
- the Current/Target Boundary Matrix when responsibility changes;
- status-checking smoke scripts;
- stale TODO or future-tense text in related documents.

I1-GB adds default-off durable-finalization publication gates, an explicit private root, and bounded capacity/timeout fields documented in `docs/config_schema.md` and `config.example.yaml`. The roadmap sequencing itself does not change M2 eligibility, queue semantics, or browser authority.
