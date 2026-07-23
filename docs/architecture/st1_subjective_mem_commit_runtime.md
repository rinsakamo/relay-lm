---
relaylm_doc_type: implementation_handoff
relaylm_authority: st1_subjective_mem_commit_runtime
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - ST-1 input, Markdown, intent, receipt, recovery, or idempotency behavior changes
  - SM-1 prepared-result or retry behavior changes
  - RT-1 or LC-1 begins consuming the finalized state
  - supported platform or workspace authority changes
relaylm_not_authoritative_for:
  - ordinary Subjective MEM Retrieval or projection implementation
  - lifecycle operations beyond create revision 1
  - Primary MEM migration, backup/restore, or user-data migration
  - multi-host publication or background recovery
relaylm_related_authority:
  - project_execution_plan.md
  - sm1_subjective_mem_create_runtime.md
  - file_first_character_workspace_design.md
  - ../contracts/subjective-mem-canonical-markdown-v1.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - ../contracts/shared-assessment-subjective-mem.md
  - ../adr/0005-subjective-mem-storage-authority.md
---
# ST-1 Subjective MEM Commit Runtime

Last reviewed: 2026-07-23 JST

## Purpose and supported slice

ST-1 consumes exactly one persisted SM-1 prepared `create` bundle and finalizes it as one deterministic canonical Subjective MEM Markdown post-image plus one matching durable operations receipt.

The accepted input is revision 1, primary formation, active lifecycle, `character_private` / `private` scope, known identity, and episodic or semantic kind. The SM-1 selector must be `mutation_state: prepared` and `retrieval_eligible: false`; its manifest must remain `prepared_noncanonical`, unpublished, receipt-free, and explicitly require ST-1.

The final logical state is:

```yaml
operation_kind: create
memory_revision: 1
lifecycle_state: active
mutation_state: none
retrieval_eligible: true
canonical_markdown_published: true
commit_receipt_present: true
projection_state: rebuild_required
ordinary_retrieval_wired: false
```

Logical eligibility is not ordinary Retrieval. No request-path reader, cache, ranking, projection, or hard cutover is added; RT-1 remains responsible for those later boundaries.

## SM-1 retrieval-visibility correction

The accepted Subjective MEM validator requires `retrieval_visible == true` for active or pinned revisions. SM-1 previously emitted an active prepared revision with `retrieval_visible: false`, which was not a valid final semantic post-image.

ST-1 corrects the producer boundary without creating revision 2 or changing subjective content:

```text
prepared immutable revision: active + retrieval_visible=true
pre-publication selector:    prepared + retrieval_eligible=false
finalized selector:          none + retrieval_eligible=true
```

Grounded content, subjective meaning, kind, strength, scope, formation snapshot, authorization, lifecycle, and lineage do not change after SM-1 preparation. Previously persisted incompatible experimental prepared shapes fail closed; no migration is authorized.

## Exact authority loading

The caller supplies the Evidence space, exact character authority, configured workspace root, original SM-1 scoped idempotency key, and operation time. ST-1 re-resolves the current character authority and requires exact equality.

Under the Evidence-space transaction lock, ST-1 loads and validates exactly one:

- immutable SM-1 operation record;
- ASM-1 formation authorization receipt;
- Subjective MEM decision;
- prepared revision and content-free manifest;
- logical current-state selector;
- referenced Shared Assessment revision.

All IDs, digests, timestamps, scope bindings, decision/result links, authority snapshots, and grounding fields must agree. Missing, corrupt, repointed, duplicated, cross-character, cross-workspace, unsupported, or target-schema-invalid records fail closed.

The existing `EvidenceRecordStore` is reused only as a transactional substrate. Governed Evidence record kinds remain Evidence authority; ST-1 record kinds are explicitly operations authority; canonical Markdown remains semantic/lifecycle authority. ST-1 stores neither a second editable body nor a second current selector in operations records.

## Canonical page plan

The physical contract is [Subjective MEM Canonical Markdown v1](../contracts/subjective-mem-canonical-markdown-v1.md).

- episodic revision 1 appends to `memory/episodes/subjective-mem-v1.md`;
- semantic revision 1 appends to `memory/topics/subjective-mem-v1.md`;
- each page is a bounded human editing unit, not one file per revision;
- page ID, block ID, and block anchor are deterministic and independent of display prose, path-derived identity, and block order;
- render/parse round-trip must reproduce the exact prepared revision;
- the page is limited to 128 blocks and 512 KiB;
- a full page fails closed with no heuristic alternate placement.

## Durable intent and immutable artifact

Before canonical replacement, ST-1 persists a content-free immutable intent binding:

- finalization and original SM-1 operation identities;
- Evidence-space, character, and workspace authority digests;
- memory, revision, decision, prepared manifest, and prepared revision identities/digests;
- stable page, relative target, block, and anchor identities;
- exact pre-image state/digest and post-image digest;
- immutable rendered artifact identity/digest;
- page schema, renderer, partition, and platform revisions;
- prepared time and fixed recovery state.

The intent, receipt, idempotency, manifest-finalization, intent-finalization, and projection-state records contain no Markdown, memory prose, Assessment text, Evidence body, messages, prompts, raw idempotency key, temp filename, or unrestricted exception text.

The private content-addressed rendered artifact is allowed only as immutable transaction material. It is byte-bound to the intent, not editable, and not canonical authority.

## Publication and finalization sequence

For the supported POSIX platform, apply performs:

```text
validate exact SM-1 bundle and workspace
  -> render and parse exact post-image
  -> create/verify immutable rendered artifact
  -> persist content-free publication intent
  -> acquire page-domain lock
  -> revalidate exact pre-image under lock
  -> private complete staging write + file fsync
  -> atomic rename
  -> verify exact bytes, digest, page schema, block, and revision lineage
  -> directory fsync
  -> while page lock remains held:
       one Evidence-space transaction inserts receipt/idempotency/finalization records,
       replaces the singleton selector with none/true,
       and records projection rebuild-required
```

The immutable SM-1 operation, decision, revision, formation receipt, and prepared manifest are not rewritten. Manifest consumption/finalization is represented by a separate immutable ST-1 finalization record. Only the mutable logical selector is replaced.

A page is never reported committed before the receipt transaction. A receipt is never inserted before exact installed-page verification and durability fencing.

## Caller-invoked recovery

Recovery occurs only when the caller invokes the ST-1 API. There is no scanner, worker, scheduler, daemon, polling loop, or background recovery.

For an unresolved exact intent:

1. **current page equals pre-image** — reuse the original immutable artifact and retry the exact replacement; no semantic re-rendering or new decision occurs;
2. **current page equals post-image** — verify exact page/block/revision lineage and roll forward the original receipt, idempotency result, manifest finalization, selector, and projection-pending state;
3. **current page equals neither** — preserve the intent, refuse overwrite, and return recovery-required for later governed reconciliation;
4. **receipt exists but page or artifact is missing/unverifiable** — return fail-closed and never expose ordinary Retrieval.

Faults before intent leave no authoritative intent. Faults after intent but before replacement retain deterministic retry material. Faults after replacement but before receipt return `recovery_pending`; the next exact call rolls forward rather than republishing or incrementing revision.

## Idempotency and SM-1 retry

ST-1 identity is scoped to the exact Evidence space, character/workspace authority, and original SM-1 operation. The same unresolved intent retries exactly; the same finalized operation returns the same receipt, page, block, digest, revision, and selector. Changed pre-image, target, renderer, artifact, decision, revision, authority, or SM-1 input is an integrity conflict or fail-closed result.

After finalization, the unchanged SM-1 call recognizes the final selector and validates the exact ST-1 receipt, immutable artifact, canonical page, and lineage outside the Evidence-store lock. It returns `duplicate_finalized` with the same decision, memory, revision, finalization ID, page ID, and block ID. Changed SM-1 input remains an idempotency conflict. No second page, block, revision, receipt, or selector is created.

## Feature posture

Configuration remains off by default:

```yaml
subjective_mem_commit_enabled: false
subjective_mem_commit_dry_run_only: true
subjective_mem_commit_apply_enabled: false
subjective_mem_workspace_root: null
```

Only the repository-standard disabled, dry-run, and apply gate triples are accepted. ST-1 dry-run validates the exact bundle, workspace, page plan, render/parse result, and recovery classification without writing artifact, intent, page, or receipt. Apply requires explicit SM-1 apply, an absolute Evidence root, an absolute workspace root, a validated character workspace, and supported POSIX secure primitives.

SM-1 may remain enabled while ST-1 is off. No ST-1 flag enables ordinary Retrieval, projection, lifecycle, migration, request-path integration, RelaySOUL, queue, worker, scheduler, polling, or background processing.

## Platform boundary and rollback

Apply currently supports one local POSIX host with `O_DIRECTORY`, `O_NOFOLLOW`, directory-relative open/stat/rename, non-following traversal, private staging, fsync, and page-domain locking. Unsupported platforms fail closed at apply; Windows configuration and startup remain unaffected.

Rollback rules are state-sensitive:

- before intent: keep gates off or revert code;
- intent exists but page is pre-image: preserve intent/artifact and use deterministic recovery only;
- page is post-image but receipt is absent: do not delete or semantically regenerate; verify and roll forward;
- receipt exists: do not revert only page or only receipt. A later governed lifecycle, correction, or migration operation is required.

Primary MEM remains unchanged and remains the runtime, characterization, rollback, and migration base.

## Explicit non-goals

ST-1 does not implement revision 2, reinforce/refine/reinterpret/supersede/contradict/consolidate, relations, Correct, Forget, Pin/Unpin, Restore, Purge, participant/relationship/scene scope, bulk publication, Primary MEM mutation or migration, ordinary Retrieval, projection authority, request-path wiring, LLM rendering, RelaySOUL, multilingual policy, product-knowledge formation, queue, worker, scheduler, polling, daemon, backup/restore, or multi-host publication.
