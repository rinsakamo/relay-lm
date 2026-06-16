# RelayRUN Runtime Checkpoint Design

## Status

This is the active RelayRUN checkpoint and recovery-orchestration contract.

It replaces an append-only historical document that mixed early dry-run plans with later default-off writer, index, resume-preflight, and recovery artifacts. The historical progression is retained in Git history and summarized in [RelayRUN Runtime Checkpoint Design History](archive/relayrun_runtime_checkpoint_design_history.md).

Implementation status and sequencing remain authoritative in [Project Status](../PROJECT_STATUS.md) and [Pipeline Implementation Plan](pipeline_implementation_plan.md).

## Purpose

RelayRUN is RelayLM's runtime orchestration layer. It owns run/turn correlation, node-state tracking, content-free checkpoint/control artifacts, fallback and recovery routing, waiting-user state, lineage, and idempotency metadata.

RelayRUN does not make semantic decisions for RelaySCN, RelayEMO, RelayINT, RelayMEM, RelayCTX, RelayREF, or RelaySOUL.

## Canonical component order

The canonical semantic order is:

```text
Client canonicalization
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval, when allowed
  -> RelayCTX Repack
  -> Main LLM
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> user / TTS / avatar output
```

RelayRUN orchestrates and records this flow. It must not reinterpret the current legacy diagnostic node aliases as canonical component ownership.

Current runtime diagnostics may still expose compatibility names such as `relayref`, `input_relayemo`, or `input_relayscn`. Those aliases describe implementation history only and must be migrated explicitly rather than used as the architecture source of truth.

## RelayRUN-owned state

RelayRUN owns:

- `run_id`, `turn_id`, request correlation, and lineage IDs,
- node execution status: pending, running, completed, failed, blocked, skipped, waiting-user,
- fallback and recovery-transition summaries,
- stream-boundary state,
- content-free checkpoint envelopes and checkpoint indexes,
- resume/readiness preflight,
- waiting-user action contracts,
- retry/resume/apply eligibility metadata,
- duplicate-emission and idempotency keys.

RelayRUN must not own:

- scene classification or persistence semantics,
- affect estimation or expression selection,
- intent/reference resolution,
- memory retrieval ranking or memory writes,
- prompt/context content selection,
- RelaySOUL revision decisions,
- final character wording,
- direct user-visible recovery text.

## Trace, checkpoint, and protected content

```text
Trace
  best-effort observation of what happened

Checkpoint
  content-free control state for safe stop/resume planning

Artifact lineage
  typed references showing which governed artifact enabled the next step
```

Default RelayRUN artifacts must not contain:

- raw user/client messages,
- backend forwarding payloads,
- prompt text,
- backend response text,
- memory snippets or full page bodies,
- persona-source bodies,
- API keys or secret-bearing URLs.

User-visible recovery or clarification text must pass through the normal RelayLM output pipeline.

## Current implemented artifact families

The current implementation contains several v0 artifact families with different apply states. They must not be collapsed into a single claim that checkpointing is either wholly implemented or wholly unimplemented.

### Runtime checkpoint summary

`relayrun.runtime_checkpoint.v0` is a request-local content-free runtime summary. It records run/turn identifiers, node statuses, stream state, blocked reasons, and fallback metadata.

It is not itself evidence that a checkpoint file was persisted or that resume is available.

### Checkpoint persistence plan and writer preflight

`relayrun.checkpoint_persistence_plan.v0` and `relayrun.checkpoint_writer_preflight.v0` are diagnostics/preflight artifacts.

They preview:

- target root and path class,
- path/content safety,
- explicit config requirements,
- atomic-write and idempotency requirements,
- blocked reasons.

Legacy reason IDs such as `checkpoint_persistence_not_implemented` or `checkpoint_writer_not_implemented` describe the original dry-run planning stage. They must not be interpreted as the current global writer status.

### File-backed checkpoint writer

A file-backed writer exists but is default-off.

```yaml
relayrun_checkpoint_write_enabled: false
relayrun_checkpoint_dry_run_only: true
relayrun_checkpoint_root: .relayrun/checkpoints
```

When either the enable flag is false or dry-run-only remains true, no directory or checkpoint file is created.

When all gates pass, the writer may persist only a content-free `relayrun.checkpoint_envelope.v0` using a safe workspace-local root, no-overwrite behavior, and atomic temp-file/rename semantics.

The writer provides persistence only. It does not implement node retry, runtime resume, recovery-transition apply, or user-visible recovery.

### Checkpoint index

`relayrun.checkpoint_index.v0` is a default-off, diagnostics-only listing and validation path.

It may summarize valid content-free checkpoint envelopes when explicitly enabled. It does not choose a checkpoint, resume a run, retry a node, or expose checkpoint bodies to the backend.

### Resume preflight

`relayrun.resume_preflight.v0` validates a candidate checkpoint path, schema, and content-free policy.

It remains readiness-only:

```text
resume_attempted=false
resume_applied=false
```

A readable checkpoint does not make resume automatically allowed.

### Recovery transition and waiting-user artifacts

`relayrun.recovery_transition.v0`, `relayrun.waiting_user_contract.v0`, and recovery-apply preflight artifacts are diagnostics/preflight objects.

They may describe:

- a proposed context-repair or confirmation transition,
- required user action classes,
- source node and reason IDs,
- gates required before future apply.

They do not directly render text, mutate the backend request, retry a backend call, or enter an applied waiting-user state unless a later explicit apply path satisfies all gates.

## Stream boundary

Streaming is a hard recovery boundary.

```text
before backend stream opens
  safe fallback, OpenAI-compatible error, or output-pipeline recovery may be selected

after stream opens but before first token
  recovery is limited by transport semantics

after first token is emitted
  RelayRUN must not replace or rewrite already emitted user-visible text
```

For realtime TTS/avatar profiles, per-chunk emission state and end-of-turn finalization must be tracked separately to prevent duplicate replay.

## Fallback boundary

Fallback is normal runtime behavior but remains route-, compatibility-, and authority-gated.

RelayRUN records:

- source node,
- from/to runtime mode,
- stable reason IDs,
- whether a user-visible response is required,
- whether the output pipeline is mandatory.

RelayRUN does not choose memory meaning, persona updates, or scene semantics.

## Current versus target boundary

### Current

- request-local RelayRUN diagnostics are wired,
- default-off content-free checkpoint persistence exists,
- checkpoint index and resume validation are diagnostics/readiness paths,
- recovery transition, waiting-user, and apply artifacts are predominantly dry-run/preflight,
- compatibility node names remain in some artifacts and scripts,
- resume/retry/recovery apply is not a general runtime capability.

### Target

- canonical typed node names aligned with the current pipeline,
- complete artifact lineage across SCN/EMO/INT/MEM/CTX/LLM/REF/output nodes,
- explicit safe resume-mode selection,
- idempotent retry/resume execution,
- applied waiting-user/recovery transitions through normal output generation,
- per-chunk and end-of-turn state for streaming recovery,
- schema migration and compatibility handling for persisted envelopes.

## Required migration scope

A future implementation migration should update together:

1. compatibility node aliases and canonical node naming,
2. app/PipelineContext node execution records,
3. checkpoint envelope and index schema migration,
4. resume-mode selection and confirmation gates,
5. retry/recovery-transition apply logic,
6. waiting-user state application,
7. streaming chunk/finalization idempotency,
8. trace/checkpoint typed projections,
9. smoke tests for writer, index, resume, recovery, and duplicate prevention.

## Safety invariants

- checkpoint writing remains explicit and default-off,
- no raw transcript or prompt store is created,
- path traversal, absolute paths, symlinks, and unsafe roots are blocked,
- existing checkpoint files are not silently overwritten,
- resume does not follow merely from successful persistence,
- user-visible text never bypasses the output pipeline,
- RelayRUN does not mutate semantic component state without the owning component's validated artifact,
- recovery after partial streaming never replays an already emitted chunk.

## Summary

```text
RelayRUN
  orchestrates nodes
  records content-free control state
  persists checkpoints only behind explicit gates
  validates future resume/recovery readiness
  never becomes the semantic decision or response-writing layer
```
