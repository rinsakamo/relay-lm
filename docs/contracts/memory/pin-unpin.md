---
relaylm_doc_type: contract
relaylm_authority: current_subjective_mem_pin_unpin_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM Pin/Unpin proposal or operation identity changes
  - active-to-pinned or pinned-to-active transition requirements change
  - shared lifecycle publication/replay/recovery integration changes
  - Pin/Unpin result/log projection or idempotency behavior changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - Primary MEM I-5 compatibility, migration, retirement, or R5/R6 disposition
  - ordinary Retrieval ranking, cache, or request-path selection
  - Correct, Forget, Restore, Consolidate, Purge, Merge, or Supersession
  - API/UI/model-generated Pin/Unpin policy or background recovery
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/memory/pinned-memory.md
  - ../../architecture/memory/mutation-governance.md
  - ../../architecture/subjective-mem-pin-unpin-runtime.md
  - ../../architecture/subjective-mem-lifecycle-publication-engine.md
  - ../../architecture/phase_i5_pin_unpin_contract.md
  - ../../architecture/phase_i5b_pin_unpin_apply.md
relaylm_related_contracts:
  - ../shared-assessment-subjective-mem.md
  - ../subjective-mem-storage-authority-and-commit-protocol.md
relaylm_verified_by:
  - ../../../scripts/relaylm_subjective_mem_pin_unpin_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Subjective MEM lifecycle and mutation maintainers
  - retrieval, recovery, integrity, and Character Workspace maintainers
  - privacy, diagnostics, migration, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Subjective MEM Pin / Unpin Contract

## Authority summary

This contract owns the exact current Subjective MEM Pin / Unpin operation boundary implemented by:

```text
relaylm/subjective_mem/pin.py
relaylm/subjective_mem_pin_runtime.py
```

The exact lifecycle transitions are:

```text
Pin:   active revision N -> pinned revision N+1
Unpin: pinned revision N -> active revision N+1
```

Pin / Unpin creates an immutable lifecycle successor. It does not rewrite semantic memory content, create a second pin-state database, make hidden memory retrievable, or call the historical Primary MEM Pin/Unpin path.

The long-lived semantic meaning of pinned memory remains described by `architecture/memory/pinned-memory.md`; this contract owns the exact current operation mechanics.

## Current operation family

The exact operation-family token is:

```text
pin_unpin
```

The only current operation kinds are:

```text
pin
unpin
```

`subjective_mem_pin_transition(...)` maps them exactly:

```text
pin   -> (active, pinned)
unpin -> (pinned, active)
```

Any other operation kind raises/fails with the bounded invalid-operation reason.

## Authorization classes

The exact current authorization classes are:

```text
user_management
operator_management
```

The exact reason categories are operation-specific:

```text
pin:
  user_requested_pin
  operator_requested_pin

unpin:
  user_requested_unpin
  operator_requested_unpin
```

The reason and authorization class must agree:

```text
user_requested_*     -> user_management
operator_requested_* -> operator_management
```

A mismatch fails validation.

## Fixed operation boundary

`SubjectiveMemPinBoundary` is immutable and the current accepted boundary equals its exact default value.

The fixed assertions are:

```text
subject_class = personal_subjective_memory
pin_unpin_authority_explicit = true
semantic_payload_preserved = true
scope_preserved = true
formation_snapshot_preserved = true
strength_preserved = true
memory_kind_and_stage_preserved = true
product_knowledge_excluded = true
model_generation_not_performed = true
content_rewrite_not_requested = true
purge_not_requested = true
restore_not_requested = true
primary_mem_projection_not_written = true
```

A caller cannot weaken one of these assertions and still produce a valid Pin/Unpin proposal.

## Proposal shape

`SubjectiveMemPinProposal` carries exactly:

```text
operation_kind
expected_memory_id
expected_current_revision
expected_lifecycle_state
expected_mutation_state
expected_page_id
expected_relative_path
expected_block_id
expected_page_digest
expected_current_selector_id
expected_current_selector_digest
expected_current_receipt_id
expected_current_receipt_digest
expected_memory_kind
expected_formation_stage
expected_scope_binding_digest
expected_formation_snapshot_digest
expected_revision_schema
expected_page_schema
expected_block_schema
expected_renderer_revision
expected_partition_revision
expected_platform_revision
authorization_class
authorization_id
reason_category
policy_revision
boundary
```

The proposal binds the exact current canonical revision, selector, receipt, page/block, scope, snapshot, schema/platform revisions, authorization, policy, and operation direction.

## Proposal digest

`proposal.input_digest` is the canonical digest of the complete proposal digest input.

The digest input includes:

- the fixed operation family;
- operation kind;
- exact memory identity/revision;
- expected lifecycle and mutation state;
- page/block/path/digest bindings;
- selector and receipt bindings;
- memory kind and formation stage;
- scope/snapshot digests;
- schema/renderer/partition/platform revisions;
- authorization/reason/policy;
- every fixed operation-boundary assertion.

Changing Pin to Unpin, changing the expected revision, or changing any bound authority changes the proposal digest.

## Proposal validation

`validate_subjective_mem_pin_proposal(...)` accepts only the exact `SubjectiveMemPinProposal` type.

Current validation includes:

- operation kind in `pin | unpin`;
- expected lifecycle matching the operation direction;
- expected mutation state exactly `none`;
- exact current revision as integer `>= 1`;
- bounded token fields;
- memory kind in `episodic | semantic`;
- formation stage in `primary | secondary`;
- authorization class/reason consistency;
- safe canonical relative path;
- exact page and authority digest shapes;
- exact default `SubjectiveMemPinBoundary`.

Validation reasons are de-duplicated while preserving first occurrence order.

## Token grammar

Current proposal/identity token validation requires strings matching:

```regex
[A-Za-z0-9][A-Za-z0-9_.:-]*
```

with the current helper default maximum length of 256 characters unless a more specific owning boundary applies.

Whitespace normalization is not used to turn an invalid token into a valid one.

## Digest grammar

Unprefixed digests are exact lowercase 64-character hexadecimal SHA-256 strings.

The expected page digest is the exact prefixed form:

```text
sha256:<64 lowercase hexadecimal characters>
```

Malformed digest values fail proposal validation.

## Relative-path grammar

The expected relative path must be:

- a non-empty string;
- at most 1024 characters;
- free of backslashes and NUL;
- non-absolute;
- already in its canonical `PurePosixPath.as_posix()` spelling;
- free of empty, `.` or `..` path components.

The runtime does not accept path normalization as permission to target a different file.

## Operation identity

`SubjectiveMemPinOperationIdentity` contains exactly:

```text
operation_slot_id
operation_id
operation_key_digest
input_digest
transition_id
intent_id
receipt_id
result_id
```

It is derived by `derive_subjective_mem_pin_operation_identity(...)` from:

```text
evidence_space_id
character_authority_digest
memory_id
operation_idempotency_key
proposal
operation_time
```

The input memory ID must equal the proposal's expected memory ID.

## Idempotency-key privacy

The raw operation idempotency key is never persisted as the operation identity.

The helper first derives:

```text
operation_key_digest = sha256(raw idempotency key)
```

The operation slot is then derived from:

```text
evidence_space_id
character_authority_digest
memory_id
operation family pin_unpin
operation_key_digest
```

This makes Pin and Unpin share one idempotency slot family for the same logical memory/key.

## Cross-direction conflict

Operation direction is part of the proposal/input digest but not a separate idempotency-slot family.

Consequently, reusing one raw key for the inverse direction reaches the same slot with a different input digest and is an integrity conflict rather than a toggle command.

The same principle applies to any changed proposal data under one idempotency key.

## Operation-time handling

Operation time must be a bounded timezone-aware ISO timestamp accepted by the current canonical timestamp helper.

It is normalized to UTC for identity derivation.

The runtime additionally rejects a committed time that is later than the supplied/current observation clock with:

```text
subjective_mem_pin_time_in_future
```

Invalid clocks fail closed.

## Public runtime entry points

The current public operation functions are:

```text
pin_subjective_mem(...)
unpin_subjective_mem(...)
```

Both delegate to the same internal operation body with the explicit operation kind.

There is no second Pin-only or Unpin-only publication/recovery core.

## Current runtime inputs

The shared runtime operation receives:

```text
store
evidence_space_id
character_config
character_authority
workspace_root
operation_idempotency_key
proposal
apply_enabled
committed_at
observed_at = optional
fault_injector = optional
```

`apply_enabled=false` is the dry-run boundary after the proposal/current-state preparation succeeds.

Fault injection is an internal validation seam, not a product/client authority.

## Current result statuses

The exact current `PinStatus` vocabulary is:

```text
disabled
dry_run_ready
committed
duplicate_finalized
recovery_pending
recovery_required
lock_busy
fail_closed
integrity_conflict
```

The operation does not expose Primary I-5A token statuses as current Subjective MEM authority.

## Result shape

`SubjectiveMemPinResult` contains:

```text
status
operation_kind
transition_id
receipt_id
memory_id
from_revision
to_revision
current_state
blocked_reasons
recovery_outcome
canonical_markdown_published
lifecycle_receipt_present
persisted
```

The nested `current_state` is internal runtime state and is not emitted wholesale by the content-free log projection.

## Result log projection

`to_log_dict()` emits bounded fields including:

```text
status
operation_kind
transition_id
receipt_id
memory_id
from_revision
to_revision
lifecycle_state
mutation_state
retrieval_eligible
canonical_markdown_published
lifecycle_receipt_present
ordinary_retrieval_wired
primary_mem_pin_projection_written
background_recovery_started
content_rewrite_performed
recovery_outcome
persisted
content_free
path_values_included
digest_values_included
raw_key_included
exception_text_included
```

Current fixed projection values include:

```text
ordinary_retrieval_wired = false
primary_mem_pin_projection_written = false
background_recovery_started = false
content_rewrite_performed = false
content_free = true
path_values_included = false
digest_values_included = false
raw_key_included = false
exception_text_included = false
```

Pin/Unpin logging therefore does not expose raw idempotency keys, filesystem paths, digests, semantic memory prose, or unrestricted exceptions.

## Exact predecessor requirement

The current predecessor must be the unique canonical revision identified by the expected singleton selector/receipt/page bindings.

It must satisfy:

```text
operation pin   -> lifecycle active
operation unpin -> lifecycle pinned
mutation_state = none
retrieval_eligible = true
exact expected revision/page/block/digests
exact character authority and workspace identity
no later revision for the same logical memory
```

A stale, ambiguous, hidden, held, superseded, purged, prepared, recovery-required, corrupt, or otherwise non-current target fails closed under the owning lifecycle/current-state validation.

## Successor requirement

The successor is exactly revision `N+1` with predecessor reference `N`.

It preserves the predecessor's semantic payload and owned semantic dimensions while changing the lifecycle state only as authorized by the operation.

Current successor construction preserves the existing memory content and sets:

```text
memory_revision = predecessor revision + 1
predecessor_revision_or_null = predecessor revision
lifecycle_state = pinned | active
retrieval_visible = true
authorization_kind = lifecycle_transition
decision_id = derived transition_id
```

Pin/Unpin cannot hide a content correction or other semantic rewrite inside this transition.

## Shared lifecycle publication

Pin/Unpin delegates publication, replay, and recovery mechanics to the operation-neutral Subjective MEM lifecycle engine.

The shared flow is:

```text
exact predecessor authority
  -> exact successor page plan
  -> lifecycle claim + prepared intent
  -> singleton selector mutation_state=prepared / retrieval_eligible=false
  -> immutable prepared post-image artifact
  -> canonical Markdown publication
  -> exact post-image verification
  -> lifecycle transition + receipt + result + intent finalization
  -> singleton selector final state mutation_state=none / retrieval eligible
  -> projection rebuild_required marker
```

The Pin/Unpin contract does not introduce a second selector, pin database, or operation-specific page publication engine.

## Prepared selector fence

Before the canonical page replacement, the shared lifecycle reservation changes the current selector into prepared mutation state.

During this period ordinary retrieval is not eligible for the logical memory.

This is the shared lifecycle mutation fence used to prevent a reader from treating an in-flight old/new revision pair as ordinary current truth.

## Dry-run boundary

When preparation succeeds and `apply_enabled=false`, the current runtime returns:

```text
status = dry_run_ready
recovery_outcome = new_intent_ready
```

without reserving/publishing the lifecycle mutation.

Dry-run still requires the exact proposal and current predecessor authority; it is not a relaxed validation path.

## Exact duplicate replay

Before new publication the runtime reads the existing lifecycle reservation/result by the deterministic operation slot/intent/result IDs.

If a finalized result exists with the exact same input digest, the runtime resolves the finalized replay and returns the existing durable operation rather than appending another successor.

An input-digest mismatch returns integrity conflict.

## Resume path

If a matching claim/intent already exists but finalization is incomplete, the runtime validates the intent, prepared selector, protected prepared post-image, predecessor authority, and lifecycle claim before resuming the same publication plan.

It does not generate a different successor or reinterpret the operation direction during recovery.

## Crash after intent before page

If an injected/real interruption occurs after reservation but before canonical page publication, the current bounded result becomes:

```text
recovery_pending
```

with the prepared selector retained as durable recovery evidence.

A later caller may resume the same operation through the shared lifecycle engine.

No background recovery worker is started by Pin/Unpin itself.

## Forward-only recovery

The current recovery model is forward-only:

```text
exact pre-image + exact prepared authority
  -> publish the already-authorized post-image

exact post-image + missing final records
  -> finalize the already-authorized lifecycle transition

foreign/neither exact image
  -> recovery_required / fail closed
  -> do not overwrite the foreign page
```

Recovery never changes Pin into Unpin, chooses a different revision, or derives a new authorization from partial state.

## Finalized state

A successful Pin finalization leaves the current selector naming the new `pinned` revision with normal mutation state and retrieval eligibility.

A successful Unpin finalization leaves the current selector naming the new `active` revision with normal mutation state and retrieval eligibility.

The predecessor remains immutable history.

## Retrieval boundary

Pinning does not directly wire or execute ordinary Retrieval.

The final pinned lifecycle state may later be consumed by the separately owned ordinary Retrieval/ranking authority only after its own currentness, scope, disclosure, mutation-state, and reader-decision gates pass.

Pin cannot make hidden, unsafe, stale, cross-scope, prepared, recovery-required, or otherwise ineligible memory retrievable.

## Primary compatibility boundary

Historical Primary I-5A/I-5B Pin/Unpin APIs, apply tokens, pin projections, ranking hints, and UI surfaces are compatibility/migration/characterization evidence only.

This current Subjective contract does not write the Primary pin projection and does not call the Primary Pin/Unpin runtime.

R5/R6 own the final retirement/migration disposition of historical Primary compatibility surfaces.

Lane D documentation does not reactivate, retire, or change those writer/reader authorities.

## Concurrency boundary

Pin/Unpin uses the same canonical Subjective lifecycle/current-state publication authority as other lifecycle mutations.

Multiple read-only proposals may exist, but the first successful lifecycle reservation/finalization wins current authority.

A later operation whose selector/receipt/revision/page bindings are stale fails closed or resolves only its own exact already-finalized idempotent replay.

No stale proposal is automatically retargeted to a newer revision.

## Content-free durable records

Lifecycle claim/intent/transition/receipt/result/finalization records remain content-free under the shared lifecycle engine.

They may carry bounded IDs, digests, lifecycle states, authorization class/ID, reason category, policy revision, timestamps and lineage bindings.

They do not contain grounded content, subjective meaning, prompt text, raw user reasons, raw idempotency keys, or filesystem path values.

## Failure direction

Pin/Unpin fails toward no lifecycle mutation when exact authority cannot be established.

Examples include:

```text
invalid proposal or operation direction
  -> fail closed

wrong lifecycle state / stale revision / changed selector or receipt
  -> fail closed or integrity conflict

unsupported/unsafe platform or path
  -> fail closed

lock contention
  -> lock_busy

same idempotency slot + different input
  -> integrity_conflict

prepared operation interrupted
  -> recovery_pending

foreign/non-exact recovery image
  -> recovery_required
```

No failure path consults a Primary fallback or creates a separate pin-state authority.

## Stable invariants

- The current operation family is `pin_unpin`.
- The only directions are Pin `active -> pinned` and Unpin `pinned -> active`.
- Pin/Unpin creates immutable revision `N+1`; it never mutates revision `N` in place.
- Semantic payload, scope, formation snapshot, strength, memory kind, and formation stage are preserved.
- The operation boundary explicitly excludes content rewrite, model generation, purge, restore, and Primary pin projection writes.
- Proposal identity binds the exact current selector/receipt/page/revision/scope/schema/policy authority.
- Raw idempotency keys are hashed and not persisted as operation identity.
- Pin and Unpin share one operation-slot family, so inverse-direction key reuse conflicts.
- Dry-run still validates exact current authority.
- Publication uses the shared lifecycle engine and one singleton current selector.
- Prepared publication makes retrieval ineligible until exact finalization or recovery.
- Exact finalized replay returns the same durable result without another revision.
- Recovery is caller-invoked and forward-only.
- Public diagnostics remain content-free and omit paths/digests/raw keys/exception text.
- Historical Primary I-5 state is not current Subjective authority and cannot bypass R5/R6.
- Ordinary Retrieval remains separately owned.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- ordinary Retrieval ranking weights or candidate budgets;
- Primary I-5 apply-token/history/projection schemas as current authority;
- R5/R6 Primary retirement/migration disposition;
- UI/API/model-generated Pin/Unpin policy;
- background recovery or scheduler behavior;
- Correct, Forget, Restore, Consolidate, Purge, Merge, or Supersession;
- a second canonical pin-state projection;
- source retirement;
- repository-level sequencing.

## Related architecture and contracts

- [Pinned Memory](../../architecture/memory/pinned-memory.md)
- [Memory Mutation Governance](../../architecture/memory/mutation-governance.md)
- [Subjective MEM Pin / Unpin Runtime](../../architecture/subjective-mem-pin-unpin-runtime.md)
- [Historical Primary I-5A Contract](../../architecture/phase_i5_pin_unpin_contract.md)
- [Shared Assessment / Subjective MEM](../shared-assessment-subjective-mem.md)
- [Subjective MEM Storage Authority and Commit Protocol](../subjective-mem-storage-authority-and-commit-protocol.md)
