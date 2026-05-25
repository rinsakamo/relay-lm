# RelaySOUL Persistence Storage Design

## Goal

RelaySOUL artifact persistence implementation should be preceded by a fixed storage-unit and audit design for content-free artifacts.

This design document defines a docs-only storage model so future implementation can:

- preserve artifact lineage across revision / approval / rollback / patch compile dry-run workflows
- keep persistence records auditable and indexable per character
- enforce content-free storage boundaries (no persona body, memory body, or patch body payload)

## Non-goals

This document does **not** implement runtime persistence behavior.

Out of scope in MVP-17A:

- actual persistence implementation
- file write
- DB write
- patch apply
- revision apply
- rollback execution
- model call

## Artifact kinds

Current RelaySOUL persistence dry-run supports the following artifact kinds:

- `patch_dry_run`
  - `artifact_id`: patch candidate id (`candidate.candidate_id`)
  - `parent_artifact_id`: `null` (lineage root for a candidate run)
- `patch_compile_dry_run`
  - `artifact_id`: patch candidate id (`patch_candidate_id`)
  - `parent_artifact_id`: patch candidate id (`patch_candidate_id`)
  - empty/missing id currently yields persistence blocking (`missing_artifact_id`) and missing parent warning (`missing_parent_artifact_id`)
- `rollback_summary`
  - `artifact_id`: revision id (`revision.revision_id`)
  - `parent_artifact_id`: parent revision id (`revision.parent_revision_id`)
- `approval_summary`
  - `artifact_id`: `revision_id` when present, otherwise `patch_candidate_id`
  - `parent_artifact_id`: `patch_candidate_id`
- `approval_package` (supported in current main)
  - `artifact_id`: `approval_package_id`
  - `parent_artifact_id`: `revision_id`

Design note: this document adopts current-main kind support so storage schema does not regress existing persistence dry-run lineage.

## Suggested storage layout

The following is a docs-only conceptual layout and is **not** created by this change:

- `.relaylm/relaysoul/artifacts/<character_id>/<artifact_kind>/<artifact_id>.json`
- `.relaylm/relaysoul/index/<character_id>/artifact_index.jsonl`
- `.relaylm/relaysoul/index/<character_id>/lineage_index.jsonl`

Intent:

- artifact envelope files are immutable records per artifact id
- `artifact_index.jsonl` is append-only audit metadata
- `lineage_index.jsonl` is append-only parent/child lineage edges for trace and reconstruction

## Artifact envelope

Future persistence should standardize one envelope shape per stored artifact (conceptual fields):

- `schema_version`
- `artifact_kind`
- `artifact_id`
- `parent_artifact_id`
- `character_id`
- `created_at`
- `source_commit_sha`
- `persistence_status`
- `warning_reasons`
- `blocking_reasons`
- `content_free`
- `payload`

Envelope constraints:

- `payload` must contain only the existing content-free artifact dictionaries produced by RelaySOUL dry-run contracts.
- persona source body, memory body, or patch body must not be serialized.

## Lineage and audit index

Lineage must be reconstructable from `artifact_id -> parent_artifact_id` links and index records.

Conceptual chain (can branch by retries/revisions):

- `patch_dry_run`
- `patch_compile_dry_run`
- `approval_package` or `approval_summary`
- `rollback_summary`

Audit requirements:

- warning artifacts and blocked artifacts should remain indexable for audit/debug workflows.
- if an artifact has persistence-contract blockers, actual storage implementation must explicitly decide whether to persist blocked records, and under which policy gate.

## Content-free policy

Storage targets are strictly content-free artifacts.

Required:

- `content_free` must be asserted true before persistence write path is allowed.
- raw persona text, memory text, prompt body, patch body, or model request/response body must never be included in artifact payloads.
- if content-free assertion fails, persistence path must fail closed.

## Retention and pruning

Initial design policy: retain-all.

Future policy hooks (per character and/or per artifact kind):

- keep latest N approvals
- keep all rollback summaries
- keep blocked artifacts only for a bounded debugging window
- archive/prune with lineage safety checks so parent/child traceability is not broken unintentionally

## Future implementation gates

Before enabling actual persistence, implementation should pass explicit gates:

- storage path config
- schema versioning
- atomic write strategy
- `tmp` + rename commit pattern
- fsync policy
- corruption handling / partial write recovery
- redaction + content-free assertions
- smoke coverage for "no body content"
- opt-in config flag (default off)

## Safety constraints

This MVP-17A document is docs-only and preserves runtime behavior.

- no actual persistence
- no file write
- no DB write
- no patch apply
- no revision apply
- no rollback execution
- no persona source mutation
- no model call
- no runtime behavior change
- no backend forwarding payload change
