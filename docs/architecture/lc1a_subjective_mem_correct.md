---
relaylm_doc_type: implementation
relaylm_authority: lc1a_subjective_mem_correct_runtime_boundary
relaylm_status: current
relaylm_volatility: high
relaylm_owner: memory
relaylm_update_trigger:
  - LC-1A Correct input, transition, persistence, or recovery changes
  - a later LC-1 operation changes the shared Subjective MEM mutation fence
  - RT-1 begins consuming lifecycle eligibility
relaylm_not_authoritative_for:
  - Forget, Pin/Unpin, Restore, Consolidate, or Purge runtime behavior
  - ordinary Subjective MEM Retrieval, ranking, cache, or request-path selection
  - Primary MEM migration, retirement, or precedence
  - API, UI, model-generated correction proposals, or background recovery
relaylm_related_authority:
  - ../contracts/shared-assessment-subjective-mem.md
  - ../contracts/subjective-mem-storage-authority-and-commit-protocol.md
  - ../contracts/subjective-mem-canonical-markdown-v1.md
  - st1_subjective_mem_commit_runtime.md
  - project_execution_plan.md
---
# LC-1A Subjective MEM Correct Runtime

Last reviewed: 2026-07-23 JST

## Implemented boundary

LC-1A is the first ordered slice of LC-1. It ports the characterization-backed Correct invariant onto canonical Subjective MEM after ST-1 publication.

The exact supported transition is:

| Operation | Source lifecycle | Source mutation | Target lifecycle | Semantic body | Revision | Final visible | Final logical eligible |
|---|---|---|---|---|---:|---:|---:|
| Correct | `active` | `none` | `active` | explicit governed correction | `N -> N+1` | `true` | `true` after page and receipt agree |

`pinned`, `held`, `hidden`, `superseded`, `purged`, `prepared`, `recovery_required`, and `corrupt` sources fail closed in LC-1A. Correct on pinned is not inferred from Primary MEM behavior because the accepted Subjective MEM v1 transition matrix authorizes only `active -> active`.

LC-1 remains incomplete. Forget, Pin/Unpin, Restore, and Consolidate must land in that order through later atomic slices. Purge remains prohibited.

## Explicit operation input

The caller supplies one exact, explicit correction proposal containing:

- Evidence space and current character/workspace authority;
- memory ID, current revision, lifecycle, mutation state, memory kind, and formation stage;
- exact scope-binding and formation-snapshot digests;
- canonical page ID, relative canonical page, current block ID, and page digest;
- exact Subjective MEM revision, page, block, renderer, partition, and platform revisions;
- singleton current-selector ID and digest;
- exact current ST-1 or lifecycle receipt ID and digest;
- one exact current Shared Assessment revision and selector;
- corrected grounded content equal to that Assessment's supported content;
- corrected subjective meaning and multidimensional strength;
- `user_management` or `operator` authorization and an opaque authorization ID;
- a fixed Correct reason category (`user_reported_inaccuracy` or `operator_grounded_correction`) and the exact `relaylm.subjective_mem_lifecycle_policy.v1` policy revision;
- fixed boundary attestations for evidence support, uncertainty, temporal qualification, scope, formation snapshot, product-knowledge exclusion, and no model generation;
- scoped idempotency key and monotonic operation time.

LC-1A does not call an LLM, embedding model, translator, classifier, API, UI, or request-path hook. The proposal is an upstream governed input, not a model decision made by this runtime.

## Immutable revision and current-selector model

Correct never edits a committed revision. It appends one immutable successor with:

```yaml
memory_id: unchanged
memory_revision: previous + 1
predecessor_revision_or_null: previous
character_id: unchanged
scope_binding: unchanged
memory_kind: unchanged
formation_stage: unchanged
formation_snapshot: unchanged
grounded_assessment_ref: exact current admitted Assessment
lifecycle_state: active
retrieval_visible: true
authorization_ref:
  authority_kind: lifecycle_transition
  authority_id: exact transition ID
```

The prior canonical revision remains byte-reconstructable and auditable. Exactly one operations selector continues to own logical currentness. During unresolved publication it is replaced atomically with:

```yaml
current_revision: previous
lifecycle_state: active
mutation_state: prepared | recovery_required
retrieval_eligible: false
```

After exact canonical post-image durability and matching operations finalization it becomes:

```yaml
current_revision: successor
lifecycle_state: active
mutation_state: none
retrieval_eligible: true
```

Logical eligibility does not wire ordinary Retrieval. RT-1 remains the sole owner of projection, ranking, cache, request-path selection, usage-event cutover, and reader retirement.

## Canonical Markdown representation

LC-1A extends the ST-1 page contract without introducing a second page format or one file per revision.

- ST-1 revision 1 retains the exact `relaylm.subjective_mem_markdown_block.v1` rendering and stable block identity.
- Lifecycle successors use `relaylm.subjective_mem_markdown_block.v2` in the same deterministic page.
- A successor block ID and anchor derive from memory ID plus immutable revision number; path, title, heading prose, order, and mtime remain non-identity.
- The parser permits retained revisions for one memory but rejects duplicate `(memory_id, memory_revision)` pairs, duplicate block IDs/anchors, broken consecutive predecessor chains, wrong character/partition/scope, and noncanonical bytes.
- Correct appends only to the exact existing page and fails closed at the existing 128-block or 512-KiB bounds. It never selects a heuristic alternate page.

The canonical page remains the human-readable semantic and lifecycle-visible authority. The operations store cannot supply or edit the corrected prose.

## Operations-store boundary

Before page replacement, one Evidence-space transaction creates content-free claim and intent records and replaces the singleton selector with the prepared state. The intent binds exact pre-image/post-image digests, revision and transition digests, page/block identities, immutable artifact identity, authorization/policy refs, renderer/platform revisions, and prepared time.

The intent and all final operations records exclude:

- canonical Markdown and corrected prose;
- Evidence or Assessment text;
- prompts or model rationale;
- raw idempotency keys;
- workspace or canonical relative paths;
- unrestricted exceptions.

The private content-addressed Markdown artifact is immutable transaction material under the existing ST-1 secure store. It is not a second editable memory body or current selector.

After exact page verification, one operations transaction inserts:

- immutable lifecycle transition;
- lifecycle commit receipt;
- durable scoped idempotency result;
- separate immutable intent-finalization record;
- final singleton current selector;
- rebuild-required projection state.

Prior revisions, decisions, receipts, and intents are never mutated.

## Concurrency and idempotency

Operation identity is scoped to Evidence space, current character authority, memory, operation kind, and hashed caller key. The exact input digest includes the current page/selector/receipt fences, Assessment, corrected post-image semantics, authorization, policy, and boundary attestations.

- exact retry returns the same transition, successor, receipt, selector, and canonical post-image;
- changed input under the same scoped key is an integrity conflict;
- a competing key loses once the shared selector is `prepared`;
- no second successor block, transition, receipt, idempotency result, or selector is created;
- durable replay is checked before stale preconditions are evaluated.

The selector transition is committed under the Evidence-space transaction lock and canonical publication uses the existing ST-1 page-domain lock. Correct therefore shares one mutation fence with later LC-1 operations rather than owning an operation-specific editable state.

## Secure publication and recovery

Apply reuses the ST-1 POSIX dir-fd writer: validated absolute workspace, component-by-component non-following traversal, allowlisted Character Workspace target, page lock, immediate pre-image digest check, private complete staging, file fsync, atomic replacement, installed inode/bytes/parser/lineage verification, directory fsync, and receipt finalization while the page lock remains held.

Recovery is caller-invoked only:

1. exact pre-image: read the original immutable artifact and retry that byte-exact post-image;
2. exact post-image: verify successor/predecessor lineage and roll forward the original receipt and selector;
3. neither: preserve intent, mark the selector `recovery_required`, refuse overwrite;
4. receipt/selector without exact page: never return success.

A durable successor page is never rolled back to the predecessor because receipt finalization failed. There is no scanner, worker, scheduler, polling loop, sleep, daemon, or background recovery process.

## Feature posture

```yaml
subjective_mem_lifecycle_enabled: false
subjective_mem_lifecycle_dry_run_only: true
subjective_mem_lifecycle_apply_enabled: false
subjective_mem_workspace_root: null
```

Only disabled, dry-run, and apply gate triples are accepted. Lifecycle apply additionally requires ST-1 apply, Evidence storage, an absolute Character Workspace root, and supported secure POSIX primitives. Dry-run validates the complete operation, current authorities, transition, page plan, deterministic render, lock plan, and recovery classification without writing.

SM-1 and ST-1 may be enabled while LC-1 remains disabled. Windows startup remains supported while secure lifecycle apply fails closed where the POSIX writer is unavailable.

## Non-goals and remaining ordered work

LC-1A does not implement or retire:

- Forget, anti-reformation tombstones, Pin/Unpin, Restore, or Consolidate;
- Purge, secure erasure, retention override, or backup/restore authority;
- ordinary Subjective MEM Retrieval or RT-1;
- Primary MEM readers, writers, lifecycle code, fixtures, APIs, UI, or operator paths;
- bulk migration, dual-read, dual-write, or precedence fallback;
- PM-D1 or PM-D9 closure;
- multi-host or non-POSIX publication.

The next LC-1 slice is Forget. LC-1 may be called complete only after Correct, Forget, Pin/Unpin, Restore, and Consolidate are all merged and exact-head validated.
