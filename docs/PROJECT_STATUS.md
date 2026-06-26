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
  - exact schema details
  - historical implementation evidence
relaylm_related_authority:
  - docs/DOCUMENTATION_MODEL.md
  - docs/architecture/pipeline_responsibility_design.md
  - docs/architecture/pipeline_implementation_plan.md
  - docs/architecture/post_i3_evaluation_work_roadmap.md
  - docs/architecture/current_target_migration_guide.md
  - docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md
  - docs/architecture/i1gd_durable_finalization_retention_cleanup.md
  - docs/architecture/phase_i4c1_primary_forget_hidden_successor.md
  - docs/architecture/o1a_two_lane_scheduler_contract.md
  - docs/architecture/o1c_eligible_b2_queue_lane.md
---
# RelayLM Project Status

Last reviewed: 2026-06-26 JST

## Purpose and authority

This page is the concise current-state view. When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibility and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns implementation status and sequencing.
3. Dedicated current contracts and handoffs own exact bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) owns compatibility interpretation.
5. `docs/mvp/` and archived documents are historical evidence only.

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
Scheduler remaining production: O1D through O1F unimplemented
RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall and scope isolation complete
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, and UI-B0 complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete
Direct Home-origin formation: not currently proven; trusted scene admission is missing
Phase I-4A Forget / Hide contract: defined target
Phase I-4B resolver / shared fence / read-only preflight-token-history: complete
Phase I-4C1 hidden-successor commit: complete
Phase I-4C2 through I-4F recovery, exclusion, UI, and validation: unimplemented
I1-GA contract / fault model: complete
I1-GB durable-finalization publication / pre-release admission: complete
I1-GC one-record restart replay / exact C1-5+B2 convergence / completion marker: complete
I1-GD retention / orphan reconciliation / isolation lifecycle / cleanup: complete
I1-GE full production crash validation: unimplemented
I1-G overall: in progress
```

## Core request/runtime foundation

Implemented:

- OpenAI-compatible `/v1/chat/completions` routing and backend forwarding;
- managed character resolution and SOUL / OUTPUT_POLICY application;
- selected RelayMEM M2 retrieval and bounded RelayCTX injection;
- non-stream and SSE response handling;
- post-response RelaySLP enqueue handoff where explicitly enabled;
- conservative default-off apply gates.

Current limitations include incomplete active tool-chain reconstruction, parser-versioned cache compatibility, output-side RelayREF/RelaySCN completion, and `/v1/responses` support.

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
- O1C one bounded eligible B2/B3 queue-lane discovery and one existing C2 delegation.

B3 lifecycle: complete.

C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication. C2 can claim one exact queued record, rehydrate a fresh protected source, invoke the one-claimed worker, and commit the canonical terminal result.

O0 adds `relaylm-worker --once --config config.yaml`. It is default-off, operator-invoked, and processes at most one currently eligible queued record. It does not poll, schedule, supervise, repair corrupt records, or create a second queue lifecycle.

## O1 operations boundary

O1A is complete as a pure contract only:

```text
validate scheduler gates
  -> replay lane: one bounded O1B discovery and at most one existing I1-GC delegation
  -> queue lane: at most one O1C discovery and one existing C2 delegation
  -> bounded content-free aggregation
  -> stop | run_next_round | idle
  -> return without sleeping
```

The lane order is replay then queue. Replay output, locator, job identity, and dispatch identity are never passed directly to C2. A queue record converged by replay may be selected in the same round only through independent queue-root discovery and canonical reread.

O1B is complete for one bounded sealed I1-G inventory, deterministic selection, canonical selected-record reread, and at most one existing I1-GC delegation. O1C is complete for one independent bounded queue-root inventory, due/future classification, deterministic selection, canonical reread, server-owned scope resolution, and at most one existing C2 delegation. Neither starts a scheduler round or loop.

Still separate:
- O1D ordering, fairness, retry-time, backoff, and jitter;
- O1E stale-claim recovery, cancellation, and graceful shutdown;
- O1F corruption, concurrency, saturation, restart, and leakage validation;
- O2 supervised worker service;
- O3 always-on local operation.

O1A adds no accepted configuration fields, CLI command, scanner, polling loop, sleep, daemon, or service.

## I1-GA through I1-GD durable-finalization boundary

Visible-release restart evidence publication is implemented by I1-GB in explicit apply mode. Restart-time one-record replay is implemented by I1-GC. Durable-finalization bounded retention and cleanup is implemented by I1-GD.

```text
ordinary finalized turn
  -> I1-GB durable base / stream segments / seal before protected visible release
  -> normal finalizer or caller-selected restart replay
  -> exact finalized-turn source reconstruction
  -> existing A1 / A2 / B1 preparation
  -> exact sealed job / dispatch identity verification
  -> canonical C1-5 protected-source convergence
  -> canonical B2 queue convergence
  -> exact downstream reread and correlation verification
  -> immutable content-free completion marker
  -> bounded I1-GD retention / isolation / cleanup pass
```

I1-GC and I1-GD use the same nonblocking cross-process per-record fence. I1-GD additionally holds the existing I1-GB store-root mutation lock while it rereads and cleans a record, so base/segment/seal publication cannot overlap maintenance. Duplicate, race, ambiguous-write, and restart paths converge only through canonical reread. Queue-without-source, identity mismatch, collision, corruption, unsupported schema, symlink, hardlink, and unsafe file type fail closed.

I1-G completion means exact sealed evidence, exact C1-5 source, exact B2 queue correlation, and a durable completion marker. It does not mean B3 terminal success, C2 execution, worker execution, or Primary MEM formation.

I1-GD publishes an immutable content-free isolation marker before deleting known record components, rereads it canonically, deletes the isolation marker last after its own retention horizon, never deletes the per-record lock file, and never mutates C1-5, B2, B3, C2, worker, or M3 state. Sealed records without completion remain replay candidates and are never deleted because of age or capacity pressure.

Remaining I1-G work:

- I1-GE full crash-at-every-boundary production validation.

## RelayMEM Primary persistence and governance

Implemented:

- M3a-M3h Primary MEM formation, page publication, index/log convergence, and recovery audit;
- exact one-claim worker execution;
- I1 next-turn Primary MEM recall: complete;
- character and namespace isolation: complete;
- bounded RelayCTX memory injection;
- I2 real SOUL Lab observation: complete;
- I3 auditable Primary MEM Correct: complete;
- I-4B canonical current-state resolution and shared Correct/Forget mutation fence;
- I-4C1 immutable Forget prepared evidence and deterministic hidden-successor M3e commit.

Phase I-4C1 establishes durable lifecycle commit ownership only. Forget is not product-complete until:

```text
I-4C2 prepared resume / exact replay / forward recovery / tombstone
  -> I-4D M3f/M3g convergence and M2/RelayCTX exclusion
  -> I-4E loopback API and SOUL Lab UI
  -> I-4F crash/race/security/fresh-conversation validation
```

The hidden successor page is lifecycle authority. Prepared, recovery-required, corrupt, hidden, and prior physical revisions must remain retrieval-ineligible once I-4D integrates lifecycle filtering. Physical deletion, secure erase, purge, restore, and unhide remain separate future contracts.

## SOUL Lab and E1 evaluation

UI-B0 real Home conversation: complete. The browser uses one server-projected route and the existing same-origin RelayLM Chat Completions path. It owns no backend, SOUL, namespace, filesystem, queue, worker, scheduler, or mutation authority.

The first local E1 result proves two separate lanes:

```text
formation lane
  explicit trusted scene-qualified managed request
    -> durable source and queue
    -> O0 one-job execution
    -> Primary MEM formation
    -> Phase I-2 observation

recall lane
  SOUL Lab Home real conversation
    -> existing M2 / RelayCTX recall
    -> remembered or corrected fact question
    -> Phase I-2 used-memory evidence
```

Direct Home-origin formation remains unproven because UI-B0 sends standard Chat Completions fields and does not self-assert trusted scene-admission metadata. The operator must also initialize the character-scoped Primary store structure before first apply.

The workstation evaluation exposed two quality gaps:

- finalized-turn summary formation needs speaker-provenance-safe evidence;
- recall responses need stronger separation between stored evidence and unsupported inference.

## Immediate dependency-first work

```text
I-4C2 prepared recovery / tombstone
|| O1B sealed-record discovery
|| O1C queue-record discovery
|| I1-GE crash validation preparation

then
  I-4D M2 exclusion
  O1D ordering / fairness / backoff
  O1E stale recovery / shutdown

then
  I1-GE crash validation completion
  I-4E / I-4F UI and validation
  O1F operational validation
  UI-B1A read-only lifecycle visibility
```

## Safe defaults

Current mutation, worker, durable-finalization, retention, and scheduler-related paths remain default-off or dry-run-first. I1-GC does not add a scanner or automatic retry loop. I1-GD performs one bounded caller-invoked pass and does not poll or invoke replay. O1A does not add current configuration fields. I-4C1 adds no accepted browser route and does not change ordinary M2 retrieval behavior.

## Not yet implemented

- trusted scene admission for direct Home-origin Primary MEM formation;
- idempotent operator-facing character-store bootstrap;
- speaker-provenance-safe Primary MEM summary formation;
- strict evidence-grounded recall response generation;
- I1-GE;
- O1B through O1F, O2, and O3;
- I-4C2 through I-4F;
- restore/unhide or physical purge;
- I-5 through I-9 governance and RelaySOUL slices;
- durable transcript inspection;
- static SOUL Lab bundle serving;
- TTS/audio/avatar/Live2D execution;
- ASR and peer communication transport.

<!-- O1B_CURRENT_BOUNDARY -->
## O1B sealed replay-lane boundary

O1B is complete for one bounded, non-recursive inventory of the configured I1-G root, exact canonical grouping and eligibility classification, deterministic selection of one sealed-pending locator, canonical selected-record reread, and at most one existing I1-GC delegation. It does not implement the O1C queue algorithm, a scheduler round loop, fairness, backoff, polling, shutdown, supervision, or always-on operation.
