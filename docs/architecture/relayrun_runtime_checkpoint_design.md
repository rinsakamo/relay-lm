---
relaylm_doc_type: subsystem_architecture
relaylm_authority: transitional_relayrun_checkpoint_current_implementation_note
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - current RelayRUN checkpoint wiring or implemented artifact posture changes
  - the legacy consumer migration and removal gate closes
relaylm_not_authoritative_for:
  - canonical compile/checkpoint architecture
  - exact checkpoint, writer, index, resume, stream, or fallback rules
  - repository-wide implementation completion
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - runtime/compile-and-checkpoint.md
relaylm_related_contracts:
  - ../contracts/relayrun-checkpoint-and-recovery.md
  - ../contracts/relayrun_recovery_response_generator_current_target.md
---
# Transitional RelayRUN Checkpoint Implementation Note

## Status

This path is a closed transitional current-implementation note retained for existing documentation consumers. Canonical subsystem architecture is [Runtime Compile and Checkpoint Architecture](runtime/compile-and-checkpoint.md). Exact checkpoint persistence, index, resume-preflight, stream, fallback, and safety rules are owned by the [RelayRUN Checkpoint and Recovery Contract](../contracts/relayrun-checkpoint-and-recovery.md).

This page no longer owns exact contract text and must not gain new consumers. Its removal gate is registered in `records/documentation/transitional-assets.json`.

## Current implemented surfaces

The current runtime contains distinct RelayRUN v0 surfaces rather than one undifferentiated checkpoint capability:

- request-local content-free runtime checkpoint summary;
- checkpoint persistence plan and writer preflight;
- explicit default-off file-backed checkpoint writer;
- diagnostics-only checkpoint index;
- resume preflight that validates readiness without applying resume;
- recovery-transition, waiting-user, and recovery-apply preflight artifacts.

These surfaces have different apply states. Persistence does not imply resume, and successful preflight does not authorize recovery apply.

## Current implementation posture

- checkpoint storage remains explicit, content-free, workspace-local, no-overwrite, and default-off;
- index and resume-preflight paths validate candidates but do not choose or resume a run;
- recovery metadata does not directly render user-visible text or mutate semantic component state;
- general node retry, runtime resume, waiting-user apply, and recovery-transition apply are not implied by the current v0 surfaces;
- partial streaming remains a hard monotonic boundary and emitted output is not replaced or replayed.

Exact fields, defaults, gates, and safety invariants live in the checkpoint/recovery contract.

## RelayRUN ownership

RelayRUN owns run/turn correlation, node execution state, content-free control artifacts, fallback and recovery routing, stream state, lineage, and idempotency metadata. It does not own scene, intent, memory, relationship, persona, prompt content, or final character wording.

## Removal gate

Delete this path after every current consumer links directly to `runtime/compile-and-checkpoint.md` and `../contracts/relayrun-checkpoint-and-recovery.md`, link and authority validation are green, and the retirement manifest records the old path. Historical wording remains recoverable through Git.
