---
relaylm_doc_type: contract
relaylm_authority: relayrun_checkpoint_persistence_resume_and_recovery_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - RelayRUN checkpoint artifact schemas or gates change
  - writer, index, or resume-preflight behavior changes
  - stream or fallback recovery invariants change
  - recovery apply becomes implemented or changes authority
relaylm_not_authoritative_for:
  - repository-wide current implementation completion
  - semantic scene, intent, memory, relationship, or persona decisions
  - compile-plan or compile-decision artifact fields
  - scheduler service lifecycle
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/runtime/compile-and-checkpoint.md
  - ../architecture/runtime/request-response-pipeline.md
relaylm_related_contracts:
  - runtime_compile_artifact_contract.md
  - runtime_compile_current_target.md
relaylm_code_sources:
  - ../../relaylm/relayrun.py
relaylm_verified_by:
  - ../../scripts/relaylm_relayrun_runtime_checkpoint_dry_run_smoke.py
  - ../../scripts/relaylm_relayrun_checkpoint_writer_smoke.py
  - ../../scripts/relaylm_relayrun_resume_preflight_smoke.py
relaylm_lifecycle: current_state
relaylm_primary_consumers:
  - RelayRUN implementation
  - checkpoint and recovery validation
  - runtime failure-path reviewers
relaylm_authority_level: exact_contract
---
# RelayRUN Checkpoint and Recovery Contract

## Scope

This contract owns the exact current checkpoint artifact, persistence, index, resume-preflight, stream, fallback, and safety boundaries extracted from the former RelayRUN checkpoint design. It does not claim that general resume, retry, or recovery-transition apply is implemented.

The following normative sections are rebuilt without wording changes from `docs/architecture/relayrun_runtime_checkpoint_design.md` at blob `a0fc965aad8a0f4a8c6ae7248beba19e817d7292`.

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

## Safety invariants

- checkpoint writing remains explicit and default-off,
- no raw transcript or prompt store is created,
- path traversal, absolute paths, symlinks, and unsafe roots are blocked,
- existing checkpoint files are not silently overwritten,
- resume does not follow merely from successful persistence,
- user-visible text never bypasses the output pipeline,
- RelayRUN does not mutate semantic component state without the owning component's validated artifact,
- recovery after partial streaming never replays an already emitted chunk.

## Current / target interpretation

The v0 artifacts above are current implemented surfaces with distinct apply states. General retry, resume execution, waiting-user apply, and recovery-transition apply remain separate target capabilities unless Project Status, code, schema/version, and focused validation prove otherwise.
