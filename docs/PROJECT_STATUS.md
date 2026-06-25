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
  - docs/architecture/phase6_async_relayslp_bounded_slice.md
  - docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - docs/architecture/phase6b3_relayslp_queue_state_helpers.md
  - docs/architecture/phase6c1_primary_mem_worker_contract.md
  - docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md
  - docs/architecture/phase6c1_durable_protected_source_persistence.md
  - docs/architecture/phase6c2_one_queued_primary_worker_integration.md
  - docs/architecture/o0_local_one_job_runner.md
  - docs/architecture/integration_i1_primary_mem_two_turn_recall.md
  - docs/architecture/phase_i2_real_soul_lab_observation.md
  - docs/architecture/phase_i3_auditable_primary_mem_correct.md
  - docs/architecture/phase_i4_primary_mem_forget_hide_contract.md
  - docs/architecture/soul_lab_ui_b0_real_home_conversation.md
  - docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md
---
# RelayLM Project Status

Last reviewed: 2026-06-25 JST

Status reviewed through:

- Phase 6 I1-B ordinary request-runtime enqueue and finalized-turn protected capture,
- Phase 6-C1-0 through C1-5 Primary MEM worker and durable-source boundaries,
- Phase 6-C2 one queued-job claim / rehydrate / execute integration adapter,
- O0 local one-job runner for one operator-invoked eligible queued job,
- Phase I-1 Primary MEM next-turn recall and character/namespace isolation,
- Phase I-2 real SOUL Lab latest-run and memory observation integration,
- Phase I-3 auditable Primary MEM Correct and later retrieval convergence,
- Phase I-4A Primary MEM Forget / Hide target contract definition only,
- SOUL Lab UI-B0 real Home non-stream and streaming conversation integration,
- I1-GA pre-enqueue durable-finalization contract and pure fault model,
- I1-GB durable-finalization publication and pre-release admission.

## Purpose and authority

This page is the concise current-state view. When documents disagree:

1. [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) owns component responsibilities and canonical target order.
2. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) owns detailed implementation status and sequencing.
3. Dedicated current contracts and handoffs own exact bounded behavior.
4. [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) owns compatibility interpretation.
5. `docs/mvp/` and archived documents are evidence only.

## Current implementation position

```text
Managed-route correctness: Phase 5-C complete through bounded v0/v1 apply and C5 runtime plumbing
Pre-stream hardening: Phase 5-D complete through D2
Stream safety / TTS handoff preparation: Phase 5.5 complete for RelayLM Core
Asynchronous RelaySLP orchestration: I1-B and B3 complete; C1-0 through C1-5 complete; C2 one-job adapter complete
Local worker operation: O0 one invocation -> at most one eligible queued job complete
RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall and scope isolation complete
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, and UI-B0 complete
Real Home conversation: same-origin RelayLM non-stream and SSE transport complete
I1 observe/correct/retrieve product loop: complete
Phase I-4A Forget / Hide contract: defined target; runtime apply, M2 exclusion, and UI unimplemented
I1-GA contract / design decision / fault model: complete
I1-GB durable-finalization publication / pre-release admission: complete
I1-GC restart replay / downstream convergence / completion marker: unimplemented
I1-G overall: in progress
```

## Core request/runtime foundation

Implemented:

- OpenAI-compatible `/v1/chat/completions` routing and backend forwarding,
- managed character resolution and SOUL / OUTPUT_POLICY application,
- selected RelayMEM M2 retrieval and bounded RelayCTX injection,
- non-stream and stream response handling,
- post-response RelaySLP enqueue handoff where explicitly enabled,
- conservative default-off apply gates.

Current limitations include incomplete active tool-chain reconstruction, parser-versioned cache compatibility, output-side RelayREF/RelaySCN completion, and `/v1/responses` support.

## Phase 6 RelaySLP orchestration and O0 operation

Implemented:

- A1/A2 deferred admission and finalized-turn handoff,
- B0-B3 durable enqueue and fenced lifecycle,
- I1-B ordinary runtime source publication and enqueue,
- C1-0 through C1-5 complete,
- C2 one-job claim/rehydrate/execute adapter: complete,
- O0 bounded non-recursive eligible-record selection, canonical reread, exact character partition resolution, and one C2 delegation per local CLI invocation.

C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication. C2 can claim one exact queued record, rehydrate a fresh protected source, invoke the one-claimed worker, and commit the canonical terminal result.

O0 adds `relaylm-worker --once --config config.yaml`. It is default-off, selects and delegates at most one currently eligible queued record, uses the existing B3/C1-5/C1-2/C2 authorities unchanged, emits one bounded content-free JSON projection, and exits. It does not reconstruct protected content, repair queue records, or add a second lifecycle policy.

Still separate:

- O1 automatic queue scanner and retry scheduler,
- O2 supervised worker service,
- O3 always-on local operation,
- I1-GC one-record restart replay and completion convergence, I1-GD cleanup, and I1-GE crash validation remain unimplemented.

I1-G tracks the process-exit window after visible-response delivery but before protected-source and B2 queue publication. I1-GA selected the target record and fault model. I1-GB now publishes bounded turn-scoped restart evidence before protected response release while preserving the existing background C1-5-then-B2 finalizer. O0 begins only after durable source and queue publication and therefore does not replace I1-G recovery.

## I1-GA / I1-GB durable-finalization boundary

I1-GA is complete as the contract and deterministic fault model. I1-GB is complete for private base/stream-segment/seal publication, canonical reread validation, exact A1/A2/B1 preparation, non-stream pre-release admission, and stream pre-yield admission. Successful JSON and concatenated SSE bytes remain unchanged.

Visible-release restart evidence publication is implemented in explicit apply mode. Restart-time one-record replay through canonical C1-5 and B2, exact duplicate convergence, and the durable completion marker remain I1-GC work. I1-GD retention/cleanup and I1-GE full production crash-at-every-boundary validation also remain unimplemented; I1-G overall is still in progress.

## RelayMEM Primary persistence and recall

Implemented:

- M3a-M3h Primary MEM formation, atomic page publication, index/log convergence, and recovery audit,
- exact one-claim worker execution,
- I1 next-turn Primary MEM recall: complete,
- character and namespace isolation: complete,
- bounded RelayCTX memory injection,
- Phase I-3 immutable successor correction with durable audit evidence.

Phase I-4A defines, but does not implement, the next lifecycle boundary:

```text
user-facing operation: Forget
canonical lifecycle state: hidden
runtime-private audit artifact: Forget tombstone
persistence model: immutable hidden successor Primary page with revision N+1
```

The hidden successor page is the lifecycle authority. The tombstone is audit/recovery evidence, not an independently updated sidecar flag. Correct and Forget must share one per-memory revision fence and one canonical current-state resolver. Prepared, recovery-required, corrupt, hidden, and prior physical revisions must be fail-closed for ordinary retrieval.

Still separate:

- production Forget preflight/apply/history,
- canonical lifecycle resolver and hidden-state M2 exclusion,
- SOUL Lab Forget UI,
- restore / unhide and physical deletion,
- Pin / Unpin,
- Merge / Supersession,
- Held Apply / Discard,
- Secondary MEM consolidation,
- RelaySOUL proposal/intervention/rollback.

## SOUL Lab UI

Implemented through UI-B0:

- TypeScript/React/Vite browser shell,
- Japanese-default and English preview language support,
- light/dark themes,
- server-projected active characters and content-free runtime settings,
- UI-A0 through UI-A7 product surfaces,
- I2 real SOUL Lab observation: complete,
- I3 auditable Primary MEM Correct: complete,
- real Home conversation over same-origin `/v1/chat/completions`,
- bounded non-stream response parsing,
- bounded UTF-8/SSE streaming parsing,
- one assistant entry per streamed response,
- Stop with partial-text preservation,
- retry without duplicate user messages,
- browser-local New Conversation,
- per-character and per-source-mode session separation,
- character/session/generation/route fencing against stale completions and chunks,
- explicit `REAL RUNTIME` / `LOCAL PREVIEW` separation,
- no automatic mock fallback after runtime failure.

UI-B0 uses only the exact `/lab/api/characters` server projection to select a conversation route. Zero routes are unavailable and multiple distinct routes are fail-closed as `ambiguous_route`. The browser does not own backend IDs, memory namespaces, SOUL, system prompts, credentials, filesystem paths, or queue identities.

The real request continues through existing RelayLM character resolution, M2 retrieval, RelayCTX injection, backend forwarding, and deferred RelaySLP boundaries. UI-B0 does not implement memory retrieval or prompt injection itself.

The dedicated frontend typecheck, strict Home conversation Node smoke, production build, documentation checks, OpenWebUI/LM Studio proxy smokes, and Phase I-1/I-2/I-3 regression runners pass. A real LM Studio workstation manual smoke remains an environment validation step and is documented in [UI-B0 Real Home Conversation](architecture/soul_lab_ui_b0_real_home_conversation.md).

Phase I-4A changes no browser behavior. The Forget UI remains unimplemented, and real mutation failure must never fall back to mock success.

## Evaluation boundary

UI-B0 plus O0 completes the explicit text-first local E1 path:

```text
real Home conversation
  -> O0 explicit one-job execution
  -> formed Primary MEM
  -> Phase I-2 observation
  -> Phase I-3 Correct
  -> Home New Conversation
  -> corrected-memory question
  -> Phase I-2 used-memory evidence
```

This is still operator-driven. O0 does not automate queue polling or retry scheduling, and UI-B0 does not own worker authority.

## Completion boundary (2026-06-25)

- I1-B producer: complete
- B3 lifecycle: complete
- C1-0 through C1-5 complete
- C2 one-job claim/rehydrate/execute adapter: complete
- O0 local one-job runner: complete
- O1 queue scanner / retry scheduler / polling: not implemented
- O2 supervised worker service: not implemented
- O3 always-on local operation: not implemented
- I1 next-turn Primary MEM recall: complete
- character and namespace isolation: complete
- I2 real SOUL Lab observation: complete
- I3 auditable Primary MEM Correct: complete
- I1 observe/correct/retrieve product loop: complete
- UI-B0 real Home conversation: complete
- I4A Forget / Hide contract: defined target
- I4 production Forget runtime, M2 exclusion, and UI: unimplemented
- I1-GA contract / design decision / fault model: complete
- I1-GB durable-finalization publication / pre-release admission: complete
- I1-GC restart replay / exact C1-5+B2 convergence / completion marker: unimplemented
- I1-GD retention / cleanup: unimplemented
- I1-GE full production crash-smoke: unimplemented
- I1-G overall: in progress

## Safe defaults and compatibility

```text
client_history_exclusion_apply_enabled = false
client_history_exclusion_apply_dry_run_only = true
memory.token_budget_truncation_enabled = false
client_instruction_typed_parse_enabled = false
client_instruction_cache_write_enabled = false
client_instruction_cache_write_dry_run_only = true
relayctx_stream_unpack_dry_run_enabled = false
relayctx_stream_unpack_dry_run_only = true
relayctx_tts_adapter_handoff_runtime_enabled = false
relayctx_tts_adapter_handoff_runtime_dry_run_only = true
relaymem_slp_runtime_enqueue_enabled = false
relaymem_slp_runtime_enqueue_dry_run_only = true
relaymem_slp_runtime_enqueue_apply_enabled = false
relaymem_slp_durable_finalization_enabled = false
relaymem_slp_durable_finalization_dry_run_only = true
relaymem_slp_durable_finalization_apply_enabled = false
relaymem_local_worker_enabled = false
relaymem_local_worker_dry_run_only = true
relaymem_local_worker_apply_enabled = false
```

UI-B0, I1-GA/I1-GB, Phase I-4A, and O0 do not weaken existing server defaults. I1-GB is default-off and changes response ordering only in explicit apply mode. Phase I-4A adds no accepted runtime route/schema, Primary writer change, M2 filtering, or browser mutation capability. O0 cannot be elevated to apply by CLI flags and performs no discovery while disabled.

## Not yet implemented

- O1 queue polling, retry scheduling, scanner fairness, or stale-claim orchestration,
- O2 supervised worker service,
- O3 always-on local operation,
- I1-GC one-record restart replay and completion marker, I1-GD retention/cleanup, and I1-GE full production crash integration,
- production Forget lifecycle apply, hidden-state M2 exclusion, Forget history API, or Forget UI,
- restore / unhide,
- hard delete, secure erase, or physical purge through Forget,
- I-5 through I-9 governance and RelaySOUL slices,
- durable transcript inspection,
- static RelayLM serving of the SOUL Lab bundle,
- TTS/audio/avatar/Live2D execution,
- ASR and peer communication transport.

## Usable local topology

```text
SOUL Lab Vite http://127.0.0.1:5173/lab/
  -> RelayLM http://127.0.0.1:8090/v1
  -> LM Studio http://127.0.0.1:1234/v1

local operator
  -> relaylm-worker --once --config config.yaml
  -> at most one eligible queued job through existing C2
```

The Vite `/v1` proxy remains loopback-targeted with `changeOrigin: false`. Real runtime and preview conversations remain separate browser-local sessions. O0 remains a separate operator authority and is not callable from the browser.
