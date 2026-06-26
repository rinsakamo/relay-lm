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
  - docs/architecture/e1_local_runtime_evaluation_2026_06_25.md
  - docs/architecture/current_target_migration_guide.md
  - docs/architecture/phase6_async_relayslp_bounded_slice.md
  - docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - docs/architecture/phase6b3_relayslp_queue_state_helpers.md
  - docs/architecture/phase6c1_primary_mem_worker_contract.md
  - docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md
  - docs/architecture/phase6c1_durable_protected_source_persistence.md
  - docs/architecture/phase6c2_one_queued_primary_worker_integration.md
  - docs/architecture/o0_local_one_job_runner.md
  - docs/architecture/o1a_two_lane_scheduler_contract.md
  - docs/architecture/integration_i1_primary_mem_two_turn_recall.md
  - docs/architecture/phase_i2_real_soul_lab_observation.md
  - docs/architecture/phase_i3_auditable_primary_mem_correct.md
  - docs/architecture/phase_i4_primary_mem_forget_hide_contract.md
  - docs/architecture/phase_i4b_primary_current_state_shared_fence.md
  - docs/architecture/phase_i4c1_primary_forget_hidden_successor.md
  - docs/architecture/soul_lab_ui_b0_real_home_conversation.md
  - docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md
---
# RelayLM Project Status

Last reviewed: 2026-06-26 JST

Status reviewed through:

- Phase 6 I1-B ordinary request-runtime enqueue and finalized-turn protected capture,
- Phase 6-C1-0 through C1-5 Primary MEM worker and durable-source boundaries,
- Phase 6-C2 one queued-job claim / rehydrate / execute integration adapter,
- O0 local one-job runner for one operator-invoked eligible queued job,
- O1A bounded replay-then-queue scheduler-round and idle-state contract,
- Phase I-1 Primary MEM next-turn recall and character/namespace isolation,
- Phase I-2 real SOUL Lab latest-run and memory observation integration,
- Phase I-3 auditable Primary MEM Correct and later retrieval convergence,
- Phase I-4A Primary MEM Forget / Hide target contract,
- Phase I-4B canonical current-state resolver, shared mutation fence, and read-only Forget boundary,
- Phase I-4C1 exact Forget preparation and hidden-successor commit,
- SOUL Lab UI-B0 real Home non-stream and streaming conversation integration,
- I1-GA pre-enqueue durable-finalization contract and pure fault model,
- I1-GB durable-finalization publication and pre-release admission,
- first local E1 workstation evaluation through explicit-scene durable formation, O0 terminal success, and later Home recall.

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
Scheduler contract: O1A replay-before-queue round / adapter / idle contract complete
Scheduler production: O1B through O1F discovery, delegation, fairness, recovery, shutdown, and validation unimplemented
RelayMEM Primary path: M1/M2 complete; M3a-M3h executable; next-turn recall and scope isolation complete
SOUL Lab UI: UI-A0 through UI-A7, Phase I-2, Phase I-3, and UI-B0 complete
Real Home conversation: same-origin RelayLM non-stream and SSE transport complete
Local E1 proof: explicit scene-qualified request -> O0 terminal success -> Primary MEM -> later Home recall complete
Direct Home-origin formation: not currently proven; trusted scene admission is missing
I1 observe/correct/retrieve product loop: complete
Phase I-4A Forget / Hide contract: defined target
Phase I-4B resolver / shared fence / read-only preflight-token-history: complete
Phase I-4C1 hidden-successor commit: complete
Phase I-4C2 through I-4F resume/replay/tombstone, M2 exclusion, UI, and validation: unimplemented
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

## Phase 6 RelaySLP orchestration, O0 operation, and O1A contract

Implemented:

- A1/A2 deferred admission and finalized-turn handoff,
- B0-B3 durable enqueue and fenced lifecycle,
- I1-B ordinary runtime source publication and enqueue,
- C1-0 through C1-5 complete,
- C2 one-job claim/rehydrate/execute adapter: complete,
- O0 bounded non-recursive eligible-record selection, canonical reread, exact character partition resolution, and one C2 delegation per local CLI invocation,
- O1A pure two-lane round/result/disposition contract and content-free projection.

C1-5 keeps queue records content-free and persists the claim-independent protected capture before queue publication. C2 can claim one exact queued record, rehydrate a fresh protected source, invoke the one-claimed worker, and commit the canonical terminal result.

O0 adds `relaylm-worker --once --config config.yaml`. It is default-off, selects and delegates at most one currently eligible queued record, uses the existing B3/C1-5/C1-2/C2 authorities unchanged, emits one bounded content-free JSON projection, and exits. It does not reconstruct protected content, repair queue records, or add a second lifecycle policy.

O1A defines one future bounded scheduler round only:

```text
validate scheduler gates
  -> replay-lane opportunity: at most one future I1-GC delegation
  -> queue-lane opportunity: at most one future C2 delegation
  -> aggregate content-free lane outcomes
  -> stop | run_next_round | idle
  -> return without sleeping
```

The lane order is fixed as replay then queue. If replay converges a B2 record, the queue lane may discover it in the same round only through its own independent queue-root discovery and canonical reread. Replay output is never passed directly to C2 and the scheduler never extracts a job/dispatch identity from it.

O1A adds no production scanner, record discovery, I1-GC or C2 invocation, polling loop, sleep, fairness, stale recovery, graceful shutdown, scheduler config field, CLI command, daemon, service, or worker pool. O1B through O1F remain unimplemented.

The first workstation evaluation observed the complete successful O0 projection for one explicit scene-qualified turn: canonical reread, character-scope resolution, B3 claim, C1-5 restart rehydration, source preparation, worker invocation, `terminal_succeeded`, and no reason IDs.

Still separate:

- O1B sealed I1-G record discovery and one I1-GC delegation,
- O1C eligible B2 discovery and one O0-compatible C2 delegation,
- O1D deterministic record ordering, lane fairness, retry-time handling, bounded backoff, and jitter,
- O1E stale-claim recovery orchestration, cancellation checkpoints, and graceful shutdown,
- O1F corruption/concurrency/saturation/restart/leakage operational validation,
- O2 supervised worker service,
- O3 always-on local operation,
- I1-GC one-record restart replay and completion convergence, I1-GD cleanup, and I1-GE crash validation.

I1-G tracks the process-exit window after visible-response delivery but before protected-source and B2 queue publication. I1-GA selected the target record and fault model. I1-GB now publishes bounded turn-scoped restart evidence before protected response release while preserving the existing background C1-5-then-B2 finalizer. O0 begins only after durable source and queue publication and therefore does not replace I1-G recovery. O1A does not implement that recovery; future O1B only discovers and calls the I1-GC authority.

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
- Phase I-3 immutable successor correction with durable audit evidence,
- Phase I-4B canonical read-only current-state resolution and shared Correct/Forget mutation fencing,
- Phase I-4C1 immutable Forget prepared artifact, deterministic hidden successor, M3e publication, and hidden/recovery-required resolution.

The workstation evaluation formed a character-scoped `relationship_moment` page, reconciled index/log state, and later recalled the core user fact through SOUL Lab Home. This validates the bounded production-authority path, not general memory quality.

The same experiment exposed two quality gaps:

- the current finalized-turn summary can concatenate user and assistant text into one `trusted_in_process_summary`, allowing assistant-authored decoration to enter evidence without speaker-safe provenance,
- the later backend answer can add unsupported details beyond the stored page.

Formation must preserve speaker-level provenance, and retrieval-side response generation must distinguish evidence from inference. Prompt-only grounding cannot repair evidence that was already stored without provenance.

Phase I-4A defines the lifecycle boundary, Phase I-4B implements its canonical read-only resolver and shared mutation fence, and Phase I-4C1 implements hidden-successor commit ownership:

```text
user-facing operation: Forget
canonical lifecycle state: hidden
runtime-private audit artifact: Forget tombstone
persistence model: immutable hidden successor Primary page with revision N+1
```

The hidden successor page is the lifecycle authority. The tombstone is audit/recovery evidence, not an independently updated sidecar flag. I-4B supplies the canonical current-state resolver, preserves the Phase I-3 per-memory `.lock` as the shared Correct/Forget mutation fence, and implements read-only Forget preflight, five-minute token validation, and bounded zero-item history. I-4C1 validates the exact token and reason again under that lock, publishes immutable `relaylm.mem.forget_prepared.v0`, deterministically builds `relaymem.primary_lifecycle_page.v0`, publishes it through M3c/M3d/M3e, canonically rereads it, and exposes `hidden / recovery_required / false`. Prepared and recovery-required evidence remains retrieval-ineligible.

Still separate:

- I-4C2 prepared resume, exact replay, forward-only recovery, response-loss convergence, and Forget tombstone finalization,
- I-4D hidden/prepared/recovery/corrupt M2 and RelayCTX exclusion plus historical lifecycle projection,
- I-4E loopback API and SOUL Lab Forget UI,
- I-4F crash/race/security/fresh-conversation validation,
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

UI-B0 uses only the exact `/lab/api/characters` server projection to select a conversation route. Zero routes are unavailable and multiple distinct routes are fail-closed as `ambiguous_route`. The browser does not own backend IDs, memory namespaces, SOUL, system prompts, credentials, filesystem paths, queue identities, finalization identities, or scheduler authority.

The real request continues through existing RelayLM character resolution, M2 retrieval, RelayCTX injection, backend forwarding, and deferred RelaySLP boundaries. UI-B0 does not implement memory retrieval or prompt injection itself.

UI-B0 sends only standard Chat Completions fields and does not send trusted scene-admission metadata. During the workstation evaluation, an ordinary Home memory statement was classified by the low-confidence heuristic fallback and failed persistence closed. Existing-memory retrieval still worked. Direct Home-origin Primary MEM formation therefore remains an integration gap; the browser must not simply self-assert arbitrary high-confidence policy to close it.

The dedicated frontend typecheck, strict Home conversation Node smoke, production build, documentation checks, OpenWebUI/LM Studio proxy smokes, and Phase I-1/I-2/I-3 regression runners pass. The real LM Studio workstation result is recorded in [E1 Local Runtime Evaluation](architecture/e1_local_runtime_evaluation_2026_06_25.md).

Phase I-4A/I-4B/I-4C1 change no browser behavior. The Forget UI remains unimplemented, and real mutation failure must never fall back to mock success.

## Evaluation boundary

UI-B0 plus O0 makes an explicit text-first local E1 evaluation possible, but the proven formation and recall lanes are currently separate:

```text
explicit trusted scene-qualified managed request
  -> durable protected source and queue publication
  -> O0 explicit one-job execution
  -> formed Primary MEM
  -> Phase I-2 observation

real Home conversation
  -> existing M2 / RelayCTX recall
  -> remembered-fact question
  -> Phase I-2 used-memory evidence
  -> Phase I-3 Correct when required
```

The shorthand `real Home conversation -> O0` is not currently a verified formation path because Home supplies no trusted scene qualification. This is still operator-driven. O0 does not automate queue polling or retry scheduling, O1A does not implement a production scheduler, and UI-B0 does not own worker authority.

The evaluation also requires an operator-initialized character-scoped store. The runtime resolves an opaque per-character root but does not create its Primary directories or `# Index` / `# Log` control files automatically.

## Completion boundary (2026-06-26)

- I1-B producer: complete
- B3 lifecycle: complete
- C1-0 through C1-5 complete
- C2 one-job claim/rehydrate/execute adapter: complete
- O0 local one-job runner: complete
- O1A two-lane scheduler / adapter / idle contract: complete
- O1B sealed-record discovery / I1-GC delegation: not implemented
- O1C B2 discovery / O0-compatible C2 delegation: not implemented
- O1D ordering / fairness / retry-time / backoff / jitter: not implemented
- O1E stale recovery / cancellation / graceful shutdown: not implemented
- O1F full operational validation: not implemented
- O2 supervised worker service: not implemented
- O3 always-on local operation: not implemented
- I1 next-turn Primary MEM recall: complete
- character and namespace isolation: complete
- I2 real SOUL Lab observation: complete
- I3 auditable Primary MEM Correct: complete
- I1 observe/correct/retrieve product loop: complete
- UI-B0 real Home conversation: complete
- local explicit-scene formation/O0/recall experiment: complete
- direct Home-origin Primary MEM formation: not implemented
- provenance-safe Primary MEM summary formation: not implemented
- evidence-grounded recall response suppression: not implemented
- I4A Forget / Hide contract: defined target
- I4B resolver / shared fence / read-only Forget boundary: complete
- I4C1 hidden-successor commit: complete
- I4C2 through I4F resume/replay/tombstone, M2 exclusion, UI, and validation: unimplemented
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

UI-B0, I1-GA/I1-GB, Phase I-4A/I-4B/I-4C1, O0, and O1A do not weaken existing server defaults. I1-GB is default-off and changes response ordering only in explicit apply mode. Phase I-4C1 adds no accepted loopback route, M3f/M3g convergence, tombstone, M2 filtering change, or browser mutation capability. O0 cannot be elevated to apply by CLI flags and performs no discovery while disabled. O1A adds no accepted configuration fields, CLI command, production scanner, or runtime invocation path.

## Not yet implemented

- trusted scene admission for direct ordinary Home-origin Primary MEM formation,
- an idempotent operator-facing character-store bootstrap command or packaged startup step,
- speaker-provenance-safe Primary MEM summary formation,
- strict evidence-grounded response generation without unsupported remembered details,
- O1B sealed-record discovery and I1-GC delegation,
- O1C B2 discovery and C2 delegation,
- O1D queue/replay ordering policy beyond fixed lane order, fairness, retry-time, backoff, jitter, and saturation pacing,
- O1E stale-claim recovery orchestration, cancellation, and graceful shutdown,
- O1F production corruption/concurrency/restart/leakage validation,
- any O1 production loop, polling, sleep, scheduler config/CLI, or automatic operation,
- O2 supervised worker service,
- O3 always-on local operation,
- I1-GC one-record restart replay and completion marker, I1-GD retention/cleanup, and I1-GE full production crash integration,
- I-4C2 prepared resume/recovery/replay and tombstone finalization, I-4D M3f/M3g plus M2 exclusion, I-4E Forget API/UI, or I-4F production validation,
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
  -> explicit scene-qualified managed request for current formation evaluation
  -> relaylm-worker --once --config config.yaml
  -> at most one eligible queued job through existing C2
```

The Vite `/v1` proxy remains loopback-targeted with `changeOrigin: false`. Real runtime and preview conversations remain separate browser-local sessions. O0 remains a separate operator authority and is not callable from the browser. O1A adds no callable runtime surface. Before first apply, the operator must initialize the resolved character-scoped Primary store structure.
