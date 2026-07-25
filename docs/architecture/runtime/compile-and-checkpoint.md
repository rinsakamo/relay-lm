---
relaylm_doc_type: subsystem_architecture
relaylm_authority: runtime_compile_checkpoint_and_recovery_responsibility_flow
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - runtime compile ownership or request-local decision flow changes
  - checkpoint, resume, fallback, or recovery ownership changes
  - streaming recovery boundaries change
  - compile or checkpoint contract families change
relaylm_not_authoritative_for:
  - exact compile artifact schemas or decision-state fields
  - exact checkpoint envelope, writer, index, or resume-preflight fields
  - current repository implementation completion
  - scheduler service or worker lifecycle
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
relaylm_related_authority:
  - request-response-pipeline.md
  - ../pipeline-responsibilities.md
  - ../safe_soul_scene_ctx_compile_chain.md
  - scheduler.md
relaylm_related_contracts:
  - ../../contracts/runtime_compile_artifact_contract.md
  - ../../contracts/runtime_compile_current_target.md
  - ../../contracts/relayrun-checkpoint-and-recovery.md
  - ../managed_route_fallback_contract.md
relaylm_code_sources:
  - ../../../relaylm/compile_gate.py
  - ../../../relaylm/relayrun.py
relaylm_verified_by:
  - ../../../scripts/relaylm_relayrun_runtime_checkpoint_dry_run_smoke.py
  - ../../../scripts/relaylm_relayrun_checkpoint_writer_smoke.py
  - ../../../scripts/relaylm_relayrun_resume_preflight_smoke.py
relaylm_lifecycle: accepted_target
relaylm_primary_consumers:
  - runtime maintainers
  - checkpoint and recovery implementers
  - integration and failure-path reviewers
relaylm_authority_level: subsystem
---
# Runtime Compile and Checkpoint Architecture

## Purpose

This page defines the responsibility flow that connects request-local compilation, authority-safe forwarding, RelayRUN control state, checkpoint persistence, resume readiness, and recovery routing. It does not define exact artifact fields or claim that every target state is implemented.

Exact compile vocabulary remains in the [Runtime Compile Artifact Contract](../../contracts/runtime_compile_artifact_contract.md) and [Runtime Compile Current / Target Boundary](../../contracts/runtime_compile_current_target.md). Exact checkpoint and recovery rules are owned by the [RelayRUN Checkpoint and Recovery Contract](../../contracts/relayrun-checkpoint-and-recovery.md).

## System boundary

```text
validated request and route authority
  -> context/profile compilation
  -> compatibility and token-budget result
  -> Runtime Compile Gate
  -> selected authority-safe backend payload or fail-closed outcome
  -> RelayRUN request/stream accounting
  -> content-free checkpoint and recovery projections
```

Compilation and checkpointing are adjacent but distinct responsibilities:

- compilation selects one backend-bound payload for the current request;
- RelayRUN records and coordinates execution state without recreating semantic decisions;
- checkpoint persistence preserves bounded content-free control state;
- resume and recovery require separate validation and authority gates.

A persisted checkpoint is not proof that resume is allowed, and a compile failure is not authority to restore excluded client context.

## Ownership map

| Responsibility | Owner | Non-owner |
|---|---|---|
| selected context and token-budget degradation | RelayCTX or the current compiler | RelayRUN |
| route-authority-aware payload decision | Runtime Compile Gate | checkpoint writer |
| run, turn, node, stream, fallback, and recovery control state | RelayRUN | SCN, EMO, INT, MEM |
| content-free checkpoint persistence | RelayRUN checkpoint writer | prompt compiler |
| checkpoint discovery and validation | checkpoint index and resume preflight | automatic resume executor |
| semantic scene, intent, memory, relationship, or persona decisions | owning semantic component | RelayRUN and adapters |
| OpenAI-compatible forwarding and transport | adapter | compile/checkpoint policy |

## Compile flow

```text
route and mode resolution
  -> client-authority canonicalization
  -> approved source loading
  -> selected scene, intent, memory, and CTX inputs
  -> compile plan and runtime-private result
  -> compatibility and budget checks
  -> authority-aware compile decision
```

The Runtime Compile Gate consumes decisions already owned by route resolution, compatibility, SCN, INT, MEM, CTX, and budget policy. It does not repeat those semantic decisions.

For an explicit delegated `pass_through` route, client context authority may remain delegated. For a RelayLM-managed route, dry run, shadow, fallback, and failure remain RelayLM-owned. Managed failure selects an authority-safe reduced payload or fails closed; it never restores excluded prior history or raw client instructions.

## RelayRUN control-state flow

```text
request starts
  -> run and turn identity
  -> ordered node states and lineage references
  -> backend/stream state
  -> finalization or bounded failure transition
  -> optional content-free checkpoint projection
```

RelayRUN owns orchestration and content-free control state. It does not own prompt content, memory meaning, scene meaning, persona revision, or final wording.

Default trace and checkpoint surfaces carry opaque identifiers, status classes, reason identifiers, counts, booleans, and bounded compatibility metadata. Runtime-private request, prompt, memory, relationship, scene, and response bodies stay outside generic checkpoint and trace storage.

## Persistence, index, and resume separation

```text
checkpoint plan or writer preflight
  -> explicit default-off write gate
  -> atomic no-overwrite content-free envelope
  -> optional index validation
  -> resume preflight
  -> separately authorized future resume or recovery apply
```

These stages do not collapse into one capability:

- planning does not write;
- writing does not select a checkpoint;
- indexing does not resume;
- successful preflight does not authorize apply;
- recovery metadata does not directly render user-visible text.

## Streaming recovery boundary

Streaming creates a monotonic user-visible boundary.

```text
before stream opens
  -> normal safe fallback, compatible error, or output-pipeline recovery may be selected

after stream opens but before first visible token
  -> recovery is constrained by transport state

after first visible token
  -> emitted text is never replaced or replayed
  -> partial/failure finalization occurs once
```

Chunk state and end-of-turn finalization are tracked separately when voice, TTS, or avatar adapters are enabled.

## Current and target separation

### Current

- request-local compile apply and diagnostics surfaces exist;
- checkpoint summary, writer preflight, default-off file writer, index, and resume-preflight surfaces exist;
- checkpoint persistence remains content-free and explicitly gated;
- general retry, resume, and recovery-transition apply are not implied by those surfaces;
- some compatibility names and v0 artifact families remain current implementation facts.

### Target

- canonical typed compile and RelayRUN lineage across the request lifecycle;
- explicit route-authority and forwarded-payload-source typing;
- authority-safe managed fallback and complete fail-closed behavior;
- versioned checkpoint/index/resume compatibility;
- idempotent resume and recovery apply through explicit gates;
- per-chunk and response-finalization recovery state without replay.

Current implementation must be interpreted from code, schema/version, Project Status, and focused validation—not inferred from target terminology.

## Failure containment

Fail closed when:

- route authority is unknown;
- no authority-safe managed payload exists;
- a checkpoint path, root, schema, or content-free rule is invalid;
- persistence would overwrite an existing checkpoint;
- a resume candidate lacks readiness or authorization;
- recovery would bypass the normal output pipeline;
- already emitted text would be rewritten or replayed;
- RelayRUN would have to recreate a semantic component decision.

## Stable invariants

- compile decisions are request-local and authority-aware;
- managed failure never restores excluded client authority;
- RelayRUN remains semantic-neutral;
- checkpoint storage is content-free, explicit, bounded, and default-off;
- persistence, indexing, preflight, and apply remain separate gates;
- user-visible recovery uses the normal response path;
- partial streaming is never replayed;
- exact schemas and state rules live in contracts, not this architecture page.

## Non-goals

This architecture does not:

- enable checkpoint writing by default;
- claim that general resume or retry is implemented;
- define scheduler service lifecycle;
- change runtime code, storage, API, or user data;
- absorb Character Workspace, memory lifecycle, or voice/TTS authority;
- make RelayRUN a semantic decision maker or response writer.
