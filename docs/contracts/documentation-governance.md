---
relaylm_doc_type: contract
relaylm_authority: active_document_graph_retained_record_and_historical_retirement_governance
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - the allowed active-document types or locations change
  - the canonical granularity dimensions change
  - a retained-record class or schema changes
  - the retirement-manifest schema or recovery proof changes
  - generic documentation validation ownership changes
relaylm_not_authoritative_for:
  - current runtime, storage, API, UI, or feature behavior
  - current implementation completion
  - deletion of a source whose live content has not been dispositioned
  - lifecycle or Retrieval semantics before their owning implementation gates close
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_decision_source: ../adr/0006-repository-structure-and-maintenance-sequencing.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - ../planning/repository-structure-migration.md
  - ../planning/workstream-orchestration.md
relaylm_related_schemas:
  - schemas/documentation-governance-v1/current-machine-registry.schema.json
  - schemas/documentation-governance-v1/retained-record-envelope.schema.json
  - schemas/documentation-governance-v1/retained-record-registry.schema.json
  - schemas/documentation-governance-v1/retirement-manifest.schema.json
  - schemas/documentation-governance-v1/transitional-asset-registry.schema.json
relaylm_verified_by:
  - ../../scripts/relaylm_documentation_governance_validate.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - documentation maintainers
  - repository validators
  - AI coding agents
relaylm_authority_level: exact_contract
---
# Documentation Governance Contract

## Authority summary

This contract owns the exact repository boundary for active documentation, narrowly retained records, historical retirement, and the generic validation families that protect those surfaces.

It implements the D1 governance lock accepted by ADR 0006. It does not synthesize every domain document, perform a broad deletion wave, or claim completion of later D2-D6 work.

## Final active-document surface

Permanent active Markdown is allowed only in the following responsibility-oriented collections:

```text
docs/README.md
docs/PROJECT_STATUS.md
docs/DOCUMENTATION_MODEL.md
docs/adr/**/*.md
docs/architecture/**/*.md
docs/contracts/**/*.md
docs/planning/**/*.md
docs/reference/**/*.md
docs/operations/**/*.md
docs/guides/**/*.md
docs/release/**/*.md
docs/templates/**/*.md
```

The permanent active document-type allowlist is:

```text
documentation_model
documentation_index
status
adr
system_architecture
subsystem_architecture
concept_policy
contract
planning
reference
operations
guide
release
template
```

Completed implementation narratives, historical proposals, dated evaluations, convergence audits, frozen receipts, compatibility notes, and archived design copies are not permanent active documents. During D2-D6 they may remain only as explicitly transitional sources with a named removal gate.

## Canonical metadata and granularity

Every document activated into the canonical graph must carry the required core metadata from `docs/DOCUMENTATION_MODEL.md` plus:

```yaml
relaylm_lifecycle: <stable | current_state | accepted_target | release_gate | navigation | template>
relaylm_primary_consumers:
  - <consumer role>
relaylm_authority_level: <system | subsystem | concept | exact_contract | sequencing | lookup | operation | release | navigation | template>
```

Two bodies may share one permanent page only when they have the same:

```text
owner
update trigger
lifecycle
primary consumers
authority level
```

A difference in any dimension is a reason to split unless a reviewed exception proves that the sections cannot change independently. Length, one originating PR, a shared milestone, or a common filename prefix is not a reason to combine authorities.

A document must be split when it mixes any of these independent responsibilities:

- current implementation status and accepted target;
- architecture and exact contract;
- sequencing and durable architecture;
- procedure and subsystem ownership;
- evaluation method and dated result;
- release criteria and completed receipt;
- proposal argument and accepted decision;
- stable concept and milestone-specific completion narrative.

## Deterministic active graph

The active graph is generated from current-tree Markdown metadata:

1. enumerate Markdown in bytewise path order;
2. classify paths against the permanent location allowlist or the transitional registry;
3. parse front matter and reject malformed metadata;
4. include only canonical active documents as graph nodes;
5. require exact path/type agreement;
6. require one globally unique primary `relaylm_authority` per node;
7. resolve repository-local relationships to existing targets;
8. sort nodes and relationship lists deterministically;
9. serialize without wall-clock fields;
10. fail when committed generated navigation drifts from regenerated output.

Generated graph and collection indexes are navigation only. They cannot become status, architecture, contract, release, or record authority.

## Authority ownership

Status owns current implementation state. Architecture owns responsibility, interaction, lifecycle meaning, and failure boundaries. Contracts own exact schemas, fields, gates, states, transitions, artifacts, APIs, and must/must-not rules. Planning owns order. Reference owns lookup interpretation. Operations and guides own procedures. Release owns current release criteria.

An active page may summarize another authority only as explicitly non-authoritative context. It must not reproduce exact tables, defaults, gates, state machines, or current-state claims as a competing source of truth.

## Retained records

Retained records live under `records/`. The directory is not a free-form archive and must not contain active architecture, contracts, planning, guides, proposals, handoffs, progress narratives, or copied retired prose.

Every record must:

- match exactly one allowlisted class;
- be listed in `records/documentation/current-records.json`;
- use an allowlisted media type and validate through its registered schema and/or validator;
- identify its owner and continuing current function;
- name at least one current consumer;
- contain no unbounded runtime-private or user content;
- use deterministic serialization when generated;
- use canonical repository-relative POSIX paths with an allowlisted top-level prefix, no absolute paths, backslashes, empty segments, or `.` / `..` segments;
- avoid claiming documentation or runtime authority;
- be reachable from a current validator, operator procedure, or generated record index.

The only retained-record classes are:

```text
release_validation_receipt
stateful_migration_receipt
external_audit_record
recovery_checkpoint
retirement_manifest
current_machine_registry
```

There is no catch-all `evidence`, `historical`, `misc`, `handoff`, or `completion` class.

`records/documentation/retained-record-registry.json` owns the class identifiers, default schemas, owners, continuing functions, allowed media types, generation posture, and current consumers. `records/documentation/current-records.json` enumerates every retained record path with its class, media type, owner, continuing function, current consumers, schema when applicable, validator paths, and human authority paths. JSON and YAML are permitted only when the catalog and class registry allow the exact media type. An unregistered file is forbidden even when it parses. Widening a class or adding a record requires the catalog, schema or validator, authority, and negative coverage to change atomically.

## Retirement manifest

The canonical manifest is `records/documentation/retirement-manifest.json`, validated by `docs/contracts/schemas/documentation-governance-v1/retirement-manifest.schema.json`.

Each entry contains exactly:

```yaml
old_path: docs/...
last_live_commit: <40 lowercase hexadecimal commit SHA>
old_blob_sha: <40 lowercase hexadecimal Git blob SHA>
removed_by_pr: <positive integer>
replacement_paths:
  - docs/... | records/...
disposition: replaced | absorbed | superseded | retired_git_history_only | record_retained
retention_reason: <bounded provenance explanation>
```

Rules:

- entries are sorted by unique `old_path`;
- replacement paths are sorted and unique;
- only `retired_git_history_only` may have no replacement path;
- `record_retained` points only to current `records/` paths;
- retired prose is never copied into the manifest;
- the manifest is updated in the same PR that removes a path;
- every new entry attributes that active pull request, existing `removed_by_pr` values are immutable, and entries are never deleted;
- `last_live_commit` is an ancestor of the validating head;
- corrections preserve an auditable Git diff;
- the manifest is provenance and navigation only, never semantic authority.

## Git recoverability

For every retired path, validation proves:

1. the path exists at `last_live_commit`;
2. `git rev-parse <last_live_commit>:<old_path>` equals `old_blob_sha`;
3. the path is absent at the proposed head;
4. `removed_by_pr` identifies the actual removal PR before merge;
5. every replacement path exists at the proposed head;
6. live links, routers, scripts, workflows, registries, and validators are repaired or removed;
7. no redirect stub, duplicate archived Markdown, symlink, fallback, or second live authority was introduced.

Git history plus the generated manifest are the recovery surfaces. A general frozen or legacy source tree is prohibited.

## Normative extraction

A source cannot be retired while a live normative block lacks a reviewed disposition. Normative material includes exact fields, schemas, gates, states, transitions, artifacts, APIs, safety-significant commands, and must/must-not language.

Allowed dispositions are:

```text
exact_contract_rebuilt
already_owned_by_current_contract
superseded_by_accepted_contract_change
non_normative_after_review
retired_with_explicit_reason
```

Exact-copy migration records the source path, blob, line range, normalized digest, target path, target range, and target digest. A wording change is a separate contract change and must not be disguised as migration. Candidate extraction by keywords is not proof of complete normative coverage.

## Generic validation families

D1 establishes these generic families:

- `active_document_authority`: locations, types, metadata, granularity, status separation, and unique authority;
- `retained_record_allowlist`: class registry, current-record catalog, record schemas or validators, owners, consumers, media types, deterministic order, and unregistered/free-form archive rejection;
- `normative_extraction`: candidate coverage, reviewed disposition, and exact source/target digests;
- `git_recoverability`: commit/blob identity, path absence, replacement existence, PR attribution, and Git recovery;
- `links_and_routers`: Markdown and metadata links, routers, workflow/script literals, and stale old-path references;
- `metadata_and_authority_uniqueness`: front matter, lifecycle, consumers, owner, trigger, and one authority owner;
- `generated_index_drift`: reproducible active navigation, retained-record navigation, and manifest representation.

Validators fail closed on malformed input and emit bounded path-based diagnostics without reproducing protected or content-bearing runtime data.

## Transitional legacy machinery

Documentation Hard Cutover 1C-57 is the final source-by-source legacy slice. Later PRs must not add another numbered 1C slice, an ordinary per-source receipt, or a bespoke source guard as the default migration mechanism.

`records/documentation/transitional-assets.json` records the remaining legacy preparation tools, per-source guards, receipts, and ledger surfaces with:

```text
owner
protected boundary
current consumers
removal gate
replacement validation
growth policy
```

A transitional family may be removed only when:

1. every protected path has a generic manifest entry or explicit current disposition;
2. active replacement and normative extraction coverage is complete;
3. generic link, authority, record, and Git checks protect the same invariant;
4. no current workflow, operator, migration, rollback, or audit consumer remains;
5. the removal PR proves negative references and equivalent validation.

Until then the assets may remain, but closed families cannot grow. D6 owns their final retirement.

## Domain synthesis order and authority gates

Stable-domain synthesis proceeds:

```text
D2-A documentation governance and repository system
D2-B runtime pipeline and compile/checkpoint
D2-C Governed Evidence, CTX-OVL, and Shared Assessment
D2-D Character Workspace
D2-E Relationship, Scene, Emotion, and Analyzer governance
D2-F scheduler and local operation
D2-G voice, streaming, TTS, and latency
D2-H stable memory formation and storage boundaries unaffected by LC-1 or RT-1
```

Lifecycle and mutation canonicalization waits for LC-1 completion. Retrieval and Primary MEM canonicalization waits for RT-1. A documentation PR must not absorb authority that is still changing in Lane C.

## Atomic synthesis and retirement PR requirements

Every D2-D6 PR states and validates:

```text
canonical target documents
source-document set
source code, contract, status, and validation anchors
normative extraction result
retained-record decisions
retirement-manifest effect
Git-recoverability proof
links, routers, workflows, registries, and validators affected
legacy guards or receipts retired
current-versus-target separation
parallel-safety analysis
```

A source is not deleted while still-live architecture or normative content lacks an accepted replacement or explicit reviewed disposition.

## Rollback boundary

Before a retirement PR merges, rollback is branch abandonment or revert. After retirement, semantic rollback does not automatically recreate the old live path. Restoring authority requires a new reviewed canonical document or contract. Historical prose remains recoverable from Git and must not return as an unreviewed duplicate authority.
