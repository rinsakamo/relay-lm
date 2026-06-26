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
  - a target-only schema gains production wiring
relaylm_not_authoritative_for:
  - component responsibility and canonical target order
  - exact schema details
  - historical MVP authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_responsibility_design.md
  - current_target_migration_guide.md
  - post_i3_evaluation_work_roadmap.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - phase_i4c1_primary_forget_hidden_successor.md
  - o1a_two_lane_scheduler_contract.md
---
# RelayLM Pipeline Implementation Plan

Last reviewed: 2026-06-26 JST

## Purpose

This document owns implementation status, dependency sequencing, and active integration priority. Component responsibility remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact behavior remains in dedicated contracts, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

## Status legend

- **complete**: bounded production contract and intended wiring exist with smoke coverage;
- **contract complete**: pure contract/model/smoke exists but production discovery or delegation does not;
- **defined target**: exact target exists but production behavior is incomplete;
- **unimplemented**: required production producer/consumer/apply/UI/validation is absent;
- **deferred**: intentionally outside the active milestone.

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
  Phase I-4C1 hidden-successor commit: complete
  Phase I-4C2 through I-4F: unimplemented

SOUL Lab:
  UI-A0 through UI-A7: complete
  Phase I-2 real Observation: complete
  Phase I-3 auditable Correct: complete
  UI-B0 real Home conversation: complete
  UI-B1 lifecycle visibility: planned

Durability and operations:
  I1-GA contract / fault model: complete
  I1-GB durable publication / pre-release admission: complete
  I1-GC one-record replay / exact convergence / completion: complete
  I1-GD retention / cleanup: unimplemented
  I1-GE full production crash validation: unimplemented
  O1A two-lane round / adapter / idle contract: contract complete
  O1B through O1F production scheduling: unimplemented
  O2 supervised worker service: planned
  O3 always-on local operation: planned
```

## Compatibility status anchors

Phase 6-B1 dispatch preflight, B2 atomic durable enqueue, and B3 fenced queue lifecycle are complete.

Phase 6-C1-0 through C1-5 are complete:

- exact current-claim protected source;
- exact M3a-M3h composition;
- one-active-claim execution;
- pure outcome classification;
- integrated crash/fault convergence;
- durable claim-independent protected capture and restart rehydration.

Phase 6-C2 one-job claim/rehydrate/execute adapter is complete. It accepts one exact queued canonical record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves bounded retry/terminal behavior without adding queue scanning or a worker service.

O0 local one-job operation is complete. `relaylm-worker --once --config config.yaml` performs bounded non-recursive discovery, securely rereads one eligible record, resolves the exact character/store partition, and delegates unchanged authority to C2/B3/C1-5/C1-2.

## Completed foundation

### Phase 5-C: managed-route correctness — complete

Current runtime supports bounded managed apply with conservative gates. Full tool-chain reconstruction, parser-versioned cache compatibility, output-side RelayREF/RelaySCN completion, and `/v1/responses` remain separate.

### Phase 5-D: pre-stream hardening — complete through D2

Pre-stream authority and content-safety checks run before visible streaming.

### Phase 5.5: Stream Unpack and TTS handoff preparation — complete for Core

Core owns suppression, segmentation hints, adapter handoff metadata, and transport-envelope preparation. TTS, audio, avatar, Live2D, and adapter delivery remain outside this milestone.

## Phase 6 asynchronous RelaySLP

### A0-A2: admission and finalized-turn handoff — complete

The ordinary response path may produce a bounded post-response handoff without executing memory formation inline.

### B0-B3: complete

Implemented: content-free durable queue record, deterministic dispatch identity, atomic create-if-absent enqueue, exact claim/lease fencing, retry release, stale recovery, and terminal commit.

### I1-B: ordinary producer wiring — complete

Ordinary managed non-stream and stream finalization can publish the protected source and enqueue the exact B3 job under explicit gates.

### C1-0 through C1-5: Primary MEM worker — complete

```text
C1-0  exact protected source and one-shot scope
C1-1  M3a-M3h compose
C1-2  one already-claimed job execution
C1-3  pure outcome classifier
C1-4  integrated fault / race / corruption / leakage validation
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

### O0: local one-job runner — complete

O0 selects and delegates at most one eligible queued record. It does not poll, sleep, schedule, supervise, repair, or redefine queue lifecycle.

## Integration Milestone I1

### I1-A: worker prerequisites — complete

B3, C1-0 through C1-5, and C2 exist with bounded contracts and validation.

### I1-B: ordinary producer wiring — complete

The ordinary managed response path can produce durable protected source and queue records under explicit gates.

### I1-C: one exact queued job execution — complete

C2 proves claim, restart rehydration, worker execution, retry/terminal convergence, and terminal-only source cleanup for one exact queued job. O0 supplies the explicit local caller.

### I1-D: next-turn recall validation — complete

Phase I-1 proves Turn 1 formation, Turn 2 M2 discovery, canonical page/index/log validation, exact character/namespace isolation, bounded RelayCTX injection, and backend-bound use.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 provides loopback-only bounded projections for latest run, validated recent Primary memories, held/blocked outcomes, actual backend-bound used-memory evidence, and content-free RelaySLP/RelayRUN/RelayCTX status. Observation evidence is read-only and cannot authorize repair, mutation, retrieval, queue transition, or worker execution.

### I1-F / Phase I-3: auditable Primary MEM Correct — complete

Phase I-3 provides exact scope/current-revision validation, bounded semantic diff, short-lived confirmation token, immutable successor page, M3f/M3g convergence, durable correction receipt, recovery, exact replay, and later M2 retrieval of only the corrected current revision.

### I1-F2 / Phase I-4A: Primary MEM Forget / Hide contract — defined target

Canonical terms:

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

Phase I-4B completes exact read-only preflight/history/token and the shared Correct/Forget mutation fence. Phase I-4C1 completes exact token/reason revalidation, immutable prepared evidence, deterministic hidden successor publication through M3e, canonical reread, one-winner concurrency, and recovery-required projection.

Remaining:

```text
I-4C2  prepared resume, exact replay, forward recovery,
        tombstone finalization, response-loss convergence
I-4D   M3f/M3g convergence, M2/RelayCTX exclusion,
        historical lifecycle projection
I-4E   loopback API and SOUL Lab Forget UI
I-4F   crash/race/security/fresh-conversation validation
```

I-4D is the user-visible semantic commit. Forget is not product-complete before ordinary retrieval exclusion is proven.

### UI-B0: Real Home Conversation — complete

UI-B0 connects SOUL Lab Home to the existing RelayLM Chat Completions path using one server-projected route, same-origin non-stream/SSE transport, explicit Real Runtime versus Local Preview sessions, Stop/Retry/New Conversation, and stale-response fencing.

### I1-G: pre-enqueue durable-finalization — in progress overall

```text
I1-GA  contract / fault model                                      complete
I1-GB  durable publication and bounded response-release admission complete
I1-GC  one-record restart replay, exact convergence, completion    complete
I1-GD  retention, orphan reconciliation, and cleanup               unimplemented
I1-GE  full production crash-at-every-boundary validation          unimplemented
```

I1-GC is a caller-selected, one-record production convergence authority:

```text
sealed I1-G evidence
  -> exact finalized-turn source reconstruction
  -> existing A1 / A2 / B1 preparation
  -> exact sealed job / dispatch identity verification
  -> canonical C1-5 protected-source convergence
  -> canonical B2 queue convergence
  -> exact downstream reread and correlation verification
  -> immutable completion marker
  -> content-free replay result
```

The normal I1-GB finalizer uses the same per-record fence and completion authority. I1-GC does not discover records, scan directories, retry in a loop, clean up records, transition B3, execute C2/C1-2, write M3 state, or expose a UI.

## O1 automatic-operation track

### O1A: two-lane bounded scheduler contract — complete

O1A completion alone is not O1 completion.

```text
replay lane
  -> future O1B discovers at most one sealed record
  -> existing I1-GC handles at most one replay

queue lane
  -> future O1C discovers at most one eligible B2 record
  -> existing C2 handles at most one queued job
```

The fixed v0 order is replay then queue. One lane failure does not automatically suppress the unrelated lane. Replay output is never passed directly into C2. These fields are not added to `relaylm/config.py`; O1A target field names remain design-only.

### O1B through O1F: unimplemented

```text
O1B  one eligible sealed-record discovery and I1-GC delegation
O1C  one eligible B2 discovery and O0-compatible C2 delegation
O1D  deterministic ordering, fairness, retry-time, backoff, jitter
O1E  stale recovery, cancellation, graceful shutdown
O1F  full corruption/concurrency/saturation/restart/leakage validation
```

## Dependency-first execution waves

### Wave 0 — completed implementation foundation

```text
I1-GB durable-finalization publication
I-4B resolver/shared fence/read-only Forget
O1A scheduling and idle contract
```

### Wave 1 — completed commit and replay authorities

```text
I1-GC one-record replay and completion convergence
I-4C1 hidden-successor commit ownership
```

### Wave 2 — current parallel implementation candidates

```text
I1-GD retention/orphan reconciliation/cleanup
I-4C2 prepared resume/forward recovery/tombstone
O1B sealed-record discovery/delegation
O1C queue-record discovery/delegation
UI-B1A projection design
```

### Wave 3 — convergence, policy, and product surfaces

```text
I-4D M2/RelayCTX exclusion and historical lifecycle projection
O1D fairness/retry/backoff
O1E stale recovery/cancellation/shutdown
I-5A and I-7A/B contracts
```

### Wave 4 — production proof

```text
I1-GE crash-at-every-boundary integration smoke
I-4E API/UI -> I-4F validation
O1F operational validation
UI-B1A read-only lifecycle visibility
```

## Governance order after Phase I-4

```text
I-5 Pin / Unpin
  -> I-7 Held Apply / Discard
  -> I-6 Merge / Supersession
  -> I-8 Secondary MEM consolidation
  -> I-9 RelaySOUL proposal / intervention / rollback
```

## Product evaluation sequence

The explicit E1 path is complete across two separate proven lanes:

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

Direct Home-origin formation remains unproven because UI-B0 does not send trusted scene-admission metadata. The loop remains operator-driven until O1B through O1F land.

## Documentation completion rule

When a phase lands, update together:

- `docs/PROJECT_STATUS.md`;
- this implementation plan;
- `docs/README.md`;
- `docs/architecture/README.md`;
- the dedicated contract/handoff;
- `post_i3_evaluation_work_roadmap.md`;
- affected current/target documents;
- status-checking smoke scripts;
- stale TODO or future-tense text.

Current documents must state one status only. Do not preserve a stale status and append a later section saying that it supersedes earlier text.

<!-- O1B_CURRENT_BOUNDARY -->
### O1B sealed replay-lane discovery — complete

O1B owns one bounded secure inventory of the configured durable-finalization root, exact grouping and eligibility classification, lexicographic selection of one sealed-pending locator, canonical selected-locator reread, and at most one delegation to the existing I1-GC authority. It owns no replay algorithm, completion publication, queue lane, C2/worker execution, polling, fairness, backoff, shutdown, supervision, or always-on operation. O1C through O1F, O2, and O3 remain unimplemented.
