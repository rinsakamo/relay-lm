# RelaySOUL Artifact Persistence Contract

## Status

This is the **current compatibility** content-free dry-run/preflight contract for RelaySOUL artifact storage readiness.

Current helper:

```text
relaylm.relaysoul_persistence.build_relaysoul_storage_envelope_dry_run
```

The helper validates metadata and builds a detached storage-envelope candidate. It does not create paths, write files or databases, append indexes, apply persona changes, or execute rollback.

This contract follows the implemented `mvp-soul-0` artifact family. Actual persistence remains target work.

## Terminology boundaries

- RelaySOUL artifact: versioned persona-source governance artifact used for dry-run, preflight, and storage contracts.
- runtime compiled context: per-request RelayCTX backend payload; not a RelaySOUL artifact.
- memory record: RelayMEM datum or candidate; not a RelaySOUL artifact.
- RAG document: retrieval corpus unit; not a RelaySOUL artifact.
- trace log: runtime observability record; not a RelaySOUL artifact.
- `STABLE_MEMORY_SUMMARY.md`: current compatibility profile-facing summary source; not the underlying memory DB and not target RelaySOUL ownership.
- content-free artifact: metadata, lineage, status, counts, and bounded reason IDs only.

RelaySOUL versions persona-source governance artifacts. It does not store runtime compiled prompts as canonical SOUL artifacts.

## Goal

Before any real persistence implementation, RelaySOUL validates artifact kind, lineage, status, and content-free posture in a consistent, auditable way.

Storage readiness is not approval, apply permission, rollback permission, or proof that durable storage occurred.

## Current supported artifact kinds

The implemented `ALLOWED_ARTIFACT_KINDS` allowlist is:

- `patch_dry_run`
- `patch_compile_dry_run`
- `rollback_summary`
- `approval_summary`
- `approval_package`
- `apply_plan`
- `rollback_plan`

Any other value blocks with `unsupported_artifact_kind`.

Consumers follow the exact implemented schema and kind allowlist. A target design does not extend current support by itself.

## Current status field per kind

Each kind reads its own status field, and a `blocked` or `warning` value adds `artifact_status_blocked` or `artifact_status_warning` as a warning reason:

```text
patch_dry_run           dry_run_status
patch_compile_dry_run   compile_dry_run_status
rollback_summary        rollback_status
approval_summary        approval_status
approval_package        approval_status
apply_plan              apply_plan_status
rollback_plan           rollback_plan_status
```

## Current artifact ID and parent ID extraction

### `patch_dry_run`

```text
artifact_id:
  artifact.candidate.candidate_id
parent_artifact_id:
  None
```

### `patch_compile_dry_run`

```text
artifact_id:
  artifact.patch_candidate_id
parent_artifact_id:
  artifact.patch_candidate_id
```

Missing or empty `patch_candidate_id` emits:

- blocking: `missing_artifact_id`
- warning: `missing_parent_artifact_id`

### `rollback_summary`

```text
artifact_id:
  artifact.revision.revision_id
parent_artifact_id:
  artifact.revision.parent_revision_id
```

Missing or empty `parent_revision_id` emits warning `missing_parent_artifact_id`.

### `approval_summary`

```text
artifact_id:
  artifact.revision_id when present
  otherwise artifact.patch_candidate_id
parent_artifact_id:
  artifact.patch_candidate_id
```

Missing or empty `patch_candidate_id` emits warning `missing_parent_artifact_id`.

### `approval_package`

```text
artifact_id:
  artifact.approval_package_id
parent_artifact_id:
  artifact.revision_id
```

Missing or empty `revision_id` emits warning `missing_parent_artifact_id`.

### `apply_plan`

```text
artifact_id:
  artifact.apply_plan_id
parent_artifact_id:
  artifact.approval_decision_id
```

Missing or empty `approval_decision_id` emits warning `missing_parent_artifact_id`.

### `rollback_plan`

```text
artifact_id:
  artifact.rollback_plan_id
parent_artifact_id:
  artifact.apply_plan_id
```

Missing or empty `apply_plan_id` emits warning `missing_parent_artifact_id`.

### Shared identity rules

`patch_dry_run` is the only kind with no parent; it emits no `missing_parent_artifact_id` warning.

A missing or empty `artifact_id` blocks with `missing_artifact_id` for every kind. A non-dict artifact blocks with `missing_artifact`, and an artifact whose `content_free` is not `true` blocks with `artifact_not_content_free`.

Missing required IDs otherwise fail closed or produce the exact implemented warning/blocking reason IDs. Consumers must not replace these field paths with inferred identifiers from target schemas.

## Current status handling

Blocked or warning source artifacts, including a non-OK `compile_dry_run_status`, may still be marked storage-ready for audit when the persistence contract itself has no blocking rule.

This means only that a content-free governance artifact may be retained for audit. It does not make the underlying candidate approved or executable.

## Content boundary

The artifact and storage-envelope candidate must not contain:

- persona-source bodies,
- memory bodies, snippets, or page content,
- patch or revision bodies,
- prompt text,
- model request or response bodies,
- raw user or client messages,
- feedback free text,
- arbitrary nested content-bearing artifacts,
- secret-bearing local paths or URLs.

A failed content-free assertion fails closed.

## Stage separation

- approval: readiness or decision metadata about whether a candidate may proceed.
- preflight: verification before any real execution.
- gate: explicit allow/deny control point.
- apply: real persona mutation; not implemented by this contract.
- rollback: real reversal; not implemented by this contract.
- persistence: real storage or index write; not implemented by this contract.

## Storage-envelope dry-run helper

`build_relaysoul_storage_envelope_dry_run(...)` wraps one supported content-free artifact into a detached envelope dictionary for validation before any real storage implementation.

The helper performs no:

- file write,
- database write,
- index append,
- directory or path creation,
- runtime prompt mutation,
- persona-source mutation,
- approval execution,
- rollback execution,
- model call.

The envelope is a candidate only. A returned ready state must not be interpreted as persisted storage.

## Target storage model

The target storage unit is one content-free governance artifact envelope per stored artifact, carrying schema version, artifact kind, artifact and parent identity, character identity, creation and source-commit metadata, persistence status, bounded reason lists, the content-free assertion, and a payload restricted to content-free artifact dictionaries.

Artifact identity and parent lineage are the reconstruction primitive: lineage must remain derivable from `artifact_id -> parent_artifact_id` links plus index records, and lineage may branch across retries and revisions.

Storage is namespaced per character. Artifact paths, artifact-index paths, and lineage-index paths are target-only identities: none is created, written, or appended by any current code, and their exact layout is deferred to the target persistence runtime contract rather than fixed here.

Index and lineage records must stay consistent with the artifact identity they describe. Warning-state and blocked artifacts remain indexable for audit; whether a blocked record is persisted at all is a target policy decision, not a current behavior.

Storage readiness is not source approval, apply permission, or rollback permission, and persisting a content-free governance artifact never converts it into portable character-source authority. Portable source ownership remains with [Character Identity and Source Authority](../architecture/character/identity-and-source-authority.md), and gate scope separation with [RelaySOUL Execution Gate Contract](relaysoul-execution-gates.md).

## Target architecture

Actual persistence requires a separately versioned runtime contract covering:

- storage configuration and namespace ownership,
- explicit approval and freshness verification,
- target file-first RelaySOUL source ownership,
- atomic write and recovery policy,
- idempotency and duplicate prevention,
- append/index behavior,
- rollback linkage,
- protected-content storage versus content-free audit projection,
- retention and deletion behavior,
- persistence and incident smoke coverage.

Retention, pruning, fsync strategy, and write-commit mechanics are open target decisions owned by that runtime contract. This contract fixes none of them.

## Required migration

A target persistence migration must update together:

1. supported artifact kinds and schema versions,
2. exact artifact/parent ID extraction,
3. five-file compatibility to file-first target source ownership,
4. approval and freshness consumers,
5. apply/rollback/storage gate consumers,
6. content-bearing protected storage types,
7. content-free projections,
8. idempotency and atomic-write handling,
9. examples and smoke fixtures.

## Safety constraints

Current behavior remains:

- dry-run/preflight only,
- no actual persistence,
- no file, DB, or index write,
- no path creation,
- no patch or revision apply,
- no rollback execution,
- no model call,
- no persona, memory, feedback, prompt, response, or patch body content in the envelope.
