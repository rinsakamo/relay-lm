# RelaySOUL Artifact Persistence Contract

## Status

This is the current content-free dry-run/preflight contract for artifact storage readiness.

Current helper:

```text
relaylm.relaysoul_persistence.build_relaysoul_storage_envelope_dry_run
```

The helper validates metadata and builds a storage envelope candidate. It does not create paths, write files/databases, append indexes, apply persona changes, or execute rollback.

## Terminology

- RelaySOUL artifact: persona-governance metadata used by dry-run/preflight/storage contracts.
- runtime compiled context: per-request RelayCTX backend payload; not a RelaySOUL artifact.
- memory record: RelayMEM datum/candidate; not a RelaySOUL artifact.
- trace log: runtime observability record; not a RelaySOUL artifact.
- `STABLE_MEMORY_SUMMARY.md`: current compatibility profile source, not target RelaySOUL ownership.
- content-free artifact: metadata, lineage, and status only.

## Current supported kinds

- `patch_dry_run`,
- `patch_compile_dry_run`,
- `rollback_summary`,
- `approval_summary`.

Consumers follow the exact implemented schema. A target design does not extend current kind support by itself.

## Current ID/lineage extraction

- patch dry run: candidate ID, no parent.
- patch compile dry run: patch candidate ID as artifact/parent.
- rollback summary: revision ID with parent revision ID.
- approval summary: revision ID when present, otherwise patch candidate ID; patch candidate ID as parent.

Missing required IDs fail closed or produce the implemented warning/blocking reason IDs.

## Status handling

A warning/blocked source artifact may be storage-ready for audit only when this persistence contract itself has no blocker. Storage readiness is not approval or execution permission.

## Content boundary

The artifact/envelope must not contain persona bodies, memory bodies/snippets, patch/prompt bodies, model request/response bodies, raw user messages, or arbitrary nested content-bearing artifacts.

A failed content-free assertion fails closed.

## Stage separation

- approval: readiness/decision metadata,
- preflight: verification before execution,
- gate: explicit allow/deny control,
- apply: real persona mutation; not implemented,
- rollback: real reversal; not implemented,
- persistence: real storage/index write; not implemented.

## Target migration

Actual persistence requires versioned schemas, storage configuration, atomic write/recovery policy, freshness and explicit approval, target-file ownership migration, idempotency, content-free validation, and storage smoke coverage.

## Safety constraints

- no actual persistence,
- no file/DB/index write,
- no patch/revision apply,
- no rollback execution,
- no model call,
- no persona/memory/feedback/prompt/response/patch body content.
