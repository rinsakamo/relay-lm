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
  - soul_lab_ui_b0_real_home_conversation.md
  - i1g_pre_enqueue_durable_finalization_contract.md
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
- **defined target**: exact contract exists, but production producer/consumer/apply/UI behavior is not complete.
- **integration pending**: components exist but the ordinary product path is not connected.
- **planned**: design or need exists without a complete producer/consumer/apply/validation path.
- **deferred**: intentionally not a gate for the active milestone.

## Current position

```text
Phase 5-C managed-route correctness: complete through bounded v0/v1 apply and C5 plumbing
Phase 5-D pre-stream hardening: complete through D2
Phase 5.5 Stream Unpack / TTS handoff preparation: RelayLM Core complete; execution pending outside Core

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
  Phase I-4B through I-4F runtime, M2, UI, and validation: unimplemented

SOUL Lab:
  UI-A0 through UI-A7: complete
  Phase I-2 real Observation: complete
  Phase I-3 auditable Correct: complete
  UI-B0 real Home conversation: complete
  broader memory governance and RelaySOUL mutation: planned

Operations:
  I1-GA contract / design decision / fault model: complete
  I1-G production pre-enqueue durability: unresolved
  O0 local one-job runner: complete
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

O0 local one-job operation is complete. `relaylm-worker --once --config config.yaml` performs bounded non-recursive discovery, selects at most one eligible queued record, securely rereads it, resolves the exact config-owned character partition, and delegates unchanged authority to C2/B3/C1-5/C1-2. It does not implement polling, fairness, stale scanning, supervision, or always-on service behavior.

Phase I-1 next-turn recall and scope isolation, Phase I-2 real SOUL Lab observation, Phase I-3 auditable Correct, and UI-B0 Real Home Conversation are complete. I1-GA contract/design/fault-model work is complete. I1-GB through I1-GE remain planned, and production pre-enqueue durability remains unresolved. Phase I-4A defines the exact Forget / Hide target contract only. Remaining sequencing is recorded in [Post-I3 Evaluation and Work Roadmap](post_i3_evaluation_work_roadmap.md).

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
  -> exact config and default-off mode gates
  -> bounded non-recursive canonical queue discovery
  -> current queued / retry-time eligibility
  -> deterministic one-candidate selection
  -> secure canonical reread and identity/race validation
  -> exact model-route/character/namespace relation
  -> existing character partition resolver
  -> one exact C2 request
  -> bounded content-free projection and exit code
  -> process exit
```

O0 uses a fresh empty process-local registry so restart rehydration is proven through C1-5. It never reconstructs protected content, performs claim CAS, changes retry policy, applies M3a-M3h directly, repairs corrupt records, or starts a polling loop. Two concurrent O0 invocations remain fenced by initial queue-lock handling, canonical reread, and the existing B3 claim CAS, so at most one reaches C1-2 for the same record.

## Integration Milestone I1

### I1-A: worker prerequisites — complete

B3, C1-0/C1-1/C1-2/C1-3/C1-4/C1-5 and C2 exist with bounded contracts and validation.

### I1-B: ordinary producer wiring — complete

The ordinary managed response path may produce the durable source and queue record under existing explicit gates.

### I1-C: one exact queued job execution — complete

C2 proves claim, restart rehydration, worker execution, retry/terminal convergence, and terminal-only source cleanup for one exact queued job. O0 supplies the explicit local caller that selects at most one eligible record and delegates to C2.

### I1-D: next-turn recall validation — complete

Phase I-1 proves Turn 1 formation, Turn 2 M2 discovery, canonical page/index/log validation, exact character/namespace isolation, bounded RelayCTX injection, and backend-bound use.

### I1-E / Phase I-2: real SOUL Lab observation — complete

Phase I-2 provides loopback-only bounded projections for latest run, validated recent Primary memories, durable held/blocked outcomes, actual backend-bound used-memory evidence, and content-free RelaySLP/RelayRUN/RelayCTX status. Observation evidence is read-only and does not replace Primary MEM, protected source, or worker authority.

### I1-F / Phase I-3: auditable Primary MEM Correct — complete

Phase I-3 provides exact scope/current-revision validation, bounded semantic diff, short-lived confirmation token, immutable successor page through M3e, M3f/M3g convergence and recovery, durable correction receipt, and later M2 retrieval of only the corrected current revision.

### I1-F2 / Phase I-4A: Primary MEM Forget / Hide contract — defined target

The contract fixes:

```text
Forget            user-facing explicit operation
hidden            canonical current retrieval-ineligible lifecycle state
Forget tombstone  immutable runtime-private audit/recovery artifact
```

Candidate A is selected: revision `N active` advances to one immutable successor Primary page at revision `N+1 hidden`, followed by M3f/M3g convergence, retrieval-exclusion verification, and tombstone finalization. The page is lifecycle authority; the tombstone is not an independently updated sidecar flag.

Correct and Forget must share one per-memory lock namespace, pending-operation fence, operation identity, and revision claim. Prepared, recovery-required, corrupt, hidden, and prior physical revisions are excluded from ordinary retrieval through one canonical current-state resolver. Production routes, apply, M2 exclusion, historical lifecycle projection, and UI are unimplemented.

Exact authority: [Phase I-4A Primary MEM Forget / Hide Contract](phase_i4_primary_mem_forget_hide_contract.md).

### UI-B0: Real Home Conversation — complete

UI-B0 connects SOUL Lab Home to the existing RelayLM Chat Completions route using exactly one server-projected route, same-origin non-stream/SSE transport, explicit Real Runtime versus Local Preview sessions, Stop/Retry/New Conversation, and stale response fencing. It creates no routing, SOUL, MEM, namespace, credential, path, or worker authority.

### I1-G: pre-enqueue background-finalizer durability — unresolved

A process may still exit after visible-response delivery but before protected-source and B2 queue publication completes. C1-5 cannot rehydrate an artifact that was never published.

I1-GA is complete as a target contract, design decision, pure state/fault model, and validation boundary. It selects one turn-scoped sealed durable-finalization publication record, fixes source-before-queue replay, bounded retention classes, content-free projection, and the required 30-point fault matrix. I1-GA changes no production runtime behavior and does not close the failure window.

I1-GB through I1-GE remain planned:

```text
I1-GB  atomic/convergent durable-finalization publication and bounded response-release admission
I1-GC  one-record restart replay, fencing, duplicate suppression, and completion marker
I1-GD  retention, orphan reconciliation, and cleanup
I1-GE  production crash-at-every-boundary integration smoke
```

I1-G is not queue scanning, worker scheduling, or C2 execution. O1 may later call the I1-GC one-record replay contract.

## Product evaluation sequence

UI-B0 and O0 complete the explicit first text-first experiment path:

```text
Home real conversation
  -> O0 one-job execution
  -> Primary MEM formation
  -> Phase I-2 observation
  -> Phase I-3 Correct
  -> Home New Conversation
  -> corrected-memory question
  -> Phase I-2 used-memory evidence
```

The loop remains operator-driven. O0 does not poll or schedule retries automatically.

## Next independent work

### Phase I-4B through I-4F: Forget / Hide implementation — planned

```text
I-4B  canonical resolver, shared Correct/Forget fence, exact preflight/history/token
I-4C  immutable hidden successor, prepared artifact, tombstone, exact replay
I-4D  index/log convergence, M2 exclusion, historical lifecycle projection
I-4E  loopback API and SOUL Lab Forget UI
I-4F  crash/race/security/fresh-conversation exclusion validation
```

Physical deletion, secure erase, purge, restore, and unhide remain separate future boundaries.

### Phase I-5 through I-7 — planned

Pin/Unpin adds bounded ranking influence, Merge/Supersession converges duplicates while preserving lineage, and Held Apply/Discard resolves exceptional held candidates.

### I1-G implementation, O1, and O2 — planned

Implement I1-GB through I1-GE, then add bounded queue selection/retry scheduling and supervised worker lifecycle using existing O0/B3/C1-5/C2 authority.

### Phase I-8 and I-9 — planned

Secondary MEM consolidation precedes separately governed RelaySOUL proposal/intervention/rollback.

### O3 — planned

Package local startup/static UI/retention/upgrade and gather multi-day soak evidence.

## Parallel ownership

```text
I1-GB   durable-finalization publication
I-4B    canonical Primary current-state resolver, shared fence, and read-only contracts
O1      scanner / retry scheduler built on O0 and C2
UI-B1   lifecycle visibility design after server projection contracts stabilize
```

UI-B0 owns `apps/soul-lab` Home transport and browser session state. O0 is complete and remains outside browser authority. I1-G and O1 must not modify UI-B0 authority to make workers browser-driven.

## Validation boundary

Every phase that changes current behavior must include contract and negative-path validation, scope/stale checks, fault/crash/retry convergence where state is durable, security/content-leakage checks, documentation link/current-boundary checks, and affected integration regression runners.

O0 validation includes:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_o0_local_one_job_runner_ci_runner.py
PYTHONPATH=.:scripts python scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py
PYTHONPATH=. python scripts/relaylm_phase6b2_durable_enqueue_contract_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6b3_queue_state_smoke.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
```

Phase I-4A validation is documentation-only:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i4_forget_hide_contract_smoke.py
git diff --check
```

The I-4A smoke does not import production runtime or imply that target routes and schemas exist.

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

UI-B0, I1-GA, and Phase I-4A change no RelayLM configuration field. O0 adds explicit default-off local-worker gates documented in `docs/config_schema.md` and `config.example.yaml`.

### I1-F3 / Phase I-4B: canonical resolver and read-only Forget contracts — complete

I-4B centralizes current revision resolution, the Phase I-3 per-memory lock, pending-operation fencing, and operation lookup. It adds read-only Forget preflight, a five-minute integrity-protected token, and bounded zero-item history. I-4C hidden apply/tombstone/recovery, I-4D M2 exclusion, I-4E API/UI, and I-4F full validation remain planned.
