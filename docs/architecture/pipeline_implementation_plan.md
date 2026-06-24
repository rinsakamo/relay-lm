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
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i3_auditable_primary_mem_correct.md
  - soul_lab_ui_b0_real_home_conversation.md
  - post_i3_evaluation_work_roadmap.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_mvp.md
  - soul_lab_runtime_mvp.md
---
# RelayLM Pipeline Implementation Plan

## Purpose

This document owns implementation status, phase sequencing, dependency boundaries, and active integration priority. Component ownership remains in [Pipeline Responsibility Design](pipeline_responsibility_design.md), exact schemas remain in dedicated contracts, and current/target interpretation remains in [Current / Target / Migration Guide](current_target_migration_guide.md).

RelayLM is integration-first. Helper-only or mock-only slices are justified only when they unblock an end-to-end milestone or close a demonstrated safety defect.

## Status legend

- **complete**: bounded contract and intended wiring exist with smoke coverage.
- **integration pending**: components exist but the ordinary product path is not connected.
- **planned**: design or need exists without a complete producer/consumer/apply/validation path.
- **deferred**: intentionally not a gate for the active milestone.

## Current position

```text
Phase 5-C managed-route correctness:
  v0 no-instruction managed apply: complete
  v1 explicit-provenance instruction-bearing managed apply: complete
  cache/typed-parse diagnostics: complete, default-off where specified
  trusted backend-response artifact producer and RelaySCN semantic apply: pending

Phase 5-D pre-stream hardening: complete through D2

Phase 5.5 Stream Unpack / TTS handoff preparation:
  RelayLM Core through B2/C4: complete
  adapter delivery and TTS/audio/avatar execution: pending outside Core

Phase 6 asynchronous RelaySLP orchestration:
  A0-A2: complete
  B0-B3: complete
  I1-B ordinary request-runtime enqueue/source capture: complete
  C1-0 through C1-5: complete
  C2 one-job claim/rehydrate/execute adapter: complete

RelayMEM Primary integration:
  M1/M2: complete
  M3a-M3h: complete
  I1 next-turn recall and scope isolation: complete
  Phase I-2 observation: complete
  Phase I-3 Correct: complete
  I1-G pre-enqueue durability: unresolved

SOUL Lab:
  UI-A0 through UI-A7: complete
  Phase I-2 real Observation: complete
  Phase I-3 auditable Correct: complete
  UI-B0 real Home conversation: complete
  broader memory governance and RelaySOUL mutation: planned

Operations:
  O0 local one-job runner: planned in a separate slice
  O1 queue scanner / retry scheduler: planned
  O2 supervised worker service: planned
  O3 always-on local operation: planned
```

## Compatibility status anchors

Phase 6-B1 dispatch preflight, B2 atomic durable enqueue, and B3 fenced queue lifecycle are complete.

I1-B ordinary managed non-stream/stream deferred enqueue is complete.

Phase 6-C1-0 through C1-5 are complete:

- exact current-claim protected source,
- exact M3a-M3h composition,
- one-active-claim execution,
- pure outcome classification,
- integrated crash/fault convergence,
- durable claim-independent protected capture and restart rehydration.

Phase 6-C2 one-job claim/rehydrate/execute adapter is complete. It accepts one exact queued canonical record, uses B3 claim, resolves source through C1-5, invokes C1-2, and preserves bounded retry/terminal behavior without adding queue scanning or a worker service.

Phase I-1 next-turn recall and scope isolation, Phase I-2 real SOUL Lab observation, Phase I-3 auditable Correct, and UI-B0 Real Home Conversation are complete. Remaining sequencing is recorded in [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md).

## Completed foundation

### Phase 5-C: managed-route correctness — complete for current bounded apply

Current runtime supports no-instruction managed apply and explicit-provenance instruction-bearing apply with conservative gates. Trusted backend-response instruction-control production, complete RelaySCN semantic apply, tool-chain reconstruction, and parser-versioned cache compatibility remain separate.

### Phase 5-D: pre-stream hardening — complete through D2

Pre-stream authority and content safety checks are wired before visible streaming.

### Phase 5.5: Stream Unpack and TTS handoff preparation — complete for Core

Core owns suppression, segmentation hints, adapter handoff metadata, and transport envelope preparation. Actual TTS, audio, avatar, Live2D, and adapter delivery remain Runtime work.

## Phase 6 asynchronous RelaySLP

### A0-A2: admission and finalized-turn handoff — complete

The ordinary response path may produce a bounded post-response handoff without executing memory formation inline.

### B0-B3: durable queue and fenced lifecycle — complete

Implemented:

- content-free durable queue record,
- deterministic dispatch identity,
- atomic create-if-absent enqueue,
- exact claim owner/token/generation/revision/expiry,
- lease renewal,
- retry release,
- stale recovery,
- terminal commit.

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

## Integration Milestone I1

### I1-A: worker prerequisites — complete

B3, C1-0/C1-1/C1-2/C1-3/C1-4/C1-5 and C2 exist with bounded contracts and validation.

### I1-B: ordinary producer wiring — complete

The ordinary managed response path may produce the durable source and queue record under existing explicit gates.

### I1-C: one exact queued job execution — complete

C2 proves claim, restart rehydration, worker execution, retry/terminal convergence, and terminal-only source cleanup for one exact queued job.

### I1-D: next-turn recall validation — complete

Phase I-1 proves:

- Turn 1 forms one durable Primary MEM through the existing worker path,
- Turn 2 discovers the correct store,
- M2 selects the memory for the correct character and namespace,
- RelayCTX injects bounded memory into the backend-bound request,
- cross-character and cross-namespace retrieval is rejected.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 provides loopback-only bounded projections for:

- latest completed managed run,
- validated recent Primary memories,
- durable held/blocked outcomes,
- memories actually included in backend-bound context,
- content-free RelaySLP/RelayRUN/RelayCTX status.

Observation evidence is read-only and does not replace Primary MEM, protected source, or worker authority.

### I1-F / Phase I-3: auditable Primary MEM Correct — complete

Phase I-3 provides:

- exact character/namespace/logical-memory/current-revision validation,
- bounded semantic diff,
- short-lived explicit confirmation token,
- immutable successor page through existing M3e,
- canonical M3f/M3g index/log convergence and recovery,
- durable correction receipt,
- later M2 retrieval of only the corrected current revision.

### UI-B0: Real Home Conversation — complete

UI-B0 connects SOUL Lab Home to the existing RelayLM Chat Completions route:

```text
exact active-character projection
  -> exactly one distinct projected route model
  -> same-origin POST /v1/chat/completions
  -> existing route and character resolution
  -> existing M2 retrieval
  -> existing RelayCTX injection
  -> existing backend forwarding
  -> bounded non-stream JSON or SSE rendering
```

Implemented safety and UX boundaries:

- no browser-owned character, namespace, SOUL, system prompt, backend ID, credential, path, or queue identity,
- no direct browser-to-LM-Studio connection,
- explicit Real Runtime versus Local Preview sessions,
- no runtime-error auto-fallback to mock,
- Stop preserves partial response text,
- Retry reuses the exact request snapshot without duplicating the user message,
- New Conversation resets only current browser-local history and draft,
- character/session/generation/route fencing rejects stale completion, chunk, error, and finalizer paths,
- conservative browser-only message, text, byte, event, and timeout bounds,
- existing M2/RelayCTX authority unchanged,
- memory-use proof remains Phase I-2 used-memory evidence.

See [UI-B0 handoff](soul_lab_ui_b0_real_home_conversation.md).

### I1-G: pre-enqueue background-finalizer durability — unresolved

A process may still exit after visible-response delivery but before protected-source and B2 queue publication completes. I1-G must begin with a dedicated failure-window and durability contract preserving:

- visible-response independence,
- source-before-queue ordering,
- dispatch idempotency,
- restart replay,
- duplicate suppression,
- content separation,
- bounded retention and cleanup.

I1-G is not queue scanning, worker scheduling, or C2 execution.

## Product evaluation sequence

UI-B0 completes the browser side of the first text-first experiment. Evaluation Gate E1 may now use the existing explicit C2 one-job method:

```text
Home real conversation
  -> explicit one-job C2 execution
  -> Primary MEM formation
  -> Phase I-2 observation
  -> Phase I-3 Correct
  -> Home New Conversation
  -> corrected-memory question
  -> Phase I-2 used-memory evidence
```

O0 will make one-job execution convenient and repeatable but remains a separate operations slice.

## Next independent work

### O0: local one-job runner — planned

A thin CLI may securely select one eligible queued record and invoke unchanged B3/C1-5/C2/C1-2 authority. It must not add a new queue schema or memory path.

### Phase I-4: Forget / Hide — planned

Define audited retrieval exclusion without physical deletion by default.

### Phase I-5: Pin / Unpin — planned

Add bounded ranking influence without authority inversion.

### Phase I-6: Merge / Supersession — planned

Converge duplicates while preserving complete lineage.

### Phase I-7: Held Apply / Discard — planned

Resolve exceptional held candidates through explicit review.

### I1-G implementation, O1, and O2 — planned

Close the pre-enqueue crash window, then add bounded queue selection/retry scheduling and supervised worker lifecycle using existing B3/C1-5/C2 authority.

### Phase I-8 and I-9 — planned

Secondary MEM consolidation precedes separately governed RelaySOUL proposal/intervention/rollback.

### O3 — planned

Package local startup/static UI/retention/upgrade and gather multi-day soak evidence.

## Parallel ownership

Low-overlap work may proceed in parallel:

```text
O0     Python one-job CLI and selection
I1-G   finalization durability contract and fault model
I-4    lifecycle-state and Forget/Hide contract
UI-B1  lifecycle visibility design after server projection contracts stabilize
```

UI-B0 owns `apps/soul-lab` Home transport and browser session state. O0 and I1-G must not modify that authority to make workers browser-driven.

## Validation boundary

Every phase that changes current behavior must include:

- contract and negative-path validation,
- scope and stale-identity checks,
- fault/crash/retry convergence where state is durable,
- security and content-leakage checks,
- documentation link and current-boundary checks,
- affected integration regression runners.

UI-B0 validation includes:

```bash
cd apps/soul-lab
npm install --no-audit --no-fund
npm run typecheck
npm run smoke:home-conversation
npm run build

cd ../..
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i1_two_turn_primary_recall_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i2_lab_observation_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_config_smoke.py
PYTHONPATH=. python scripts/relaylm_openwebui_lmstudio_proxy_smoke.py
```

## Documentation completion rule

When a phase lands, review together:

- `docs/PROJECT_STATUS.md`,
- this implementation plan,
- `docs/README.md`,
- `docs/architecture/README.md`,
- the dedicated handoff/contract,
- [Post-I3 roadmap](post_i3_evaluation_work_roadmap.md),
- `docs/config_schema.md` when configuration changes,
- the Current/Target Boundary Matrix when responsibility changes,
- status-checking smoke scripts,
- stale TODO or future-tense text in related documents.

UI-B0 changes no RelayLM configuration field, so `docs/config_schema.md` remains unchanged.