---
relaylm_doc_type: subsystem_architecture
relaylm_authority: memory_mutation_lifecycle_and_authorization_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - Subjective MEM lifecycle states or governed transitions change
  - lifecycle operation authorization or payload fences change
  - shared publication, replay, selector-fencing, or recovery responsibilities change
  - Correct, Forget, Pin/Unpin, Restore, Consolidate, or Purge ownership changes
  - RT-1 Primary writer retirement changes compatibility mutation posture
relaylm_not_authoritative_for:
  - repository-wide current implementation completion or sequencing
  - exact lifecycle record, token, API, UI, or runtime schemas
  - exact canonical Markdown, operations-store, lock, or filesystem implementation
  - exact RT-1 cutover state, R5/R6 retirement approval, or irreversible purge procedure
  - formation-model policy, retrieval ranking, or relationship/source revision schemas
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source:
  - ../../adr/0003-subjective-mem-direction.md
  - ../../adr/0005-subjective-mem-storage-authority.md
relaylm_related_authority:
  - ../subjective-mem-lifecycle-publication-engine.md
  - ../lc1a_subjective_mem_correct.md
  - ../subjective-mem-forget-runtime.md
  - ../subjective-mem-pin-unpin-runtime.md
  - ../subjective-mem-restore-runtime.md
  - ../subjective-mem-consolidate-runtime.md
  - ../phase_i4_primary_mem_forget_hide_contract.md
  - ../subjective-mem-retrieval-projection-hard-cutover.md
  - storage-and-recovery.md
  - retrieval-and-grounding.md
  - formation.md
relaylm_related_contracts:
  - ../../contracts/shared-assessment-subjective-mem.md
  - ../../contracts/subjective-mem-storage-authority-and-commit-protocol.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - lifecycle operation implementers
  - memory management API and UI maintainers
  - retrieval, storage, recovery, and integrity reviewers
  - RT-1 cutover and Primary-retirement reviewers
relaylm_authority_level: subsystem
---
# Memory Mutation Governance

## Purpose

This page is the canonical subsystem architecture for governed durable-memory mutation and lifecycle change.

It owns the stable responsibility split between:

1. operation-specific semantic and authorization owners;
2. immutable successor and lifecycle-transition rules;
3. shared publication, selector fencing, replay, and forward-recovery mechanics;
4. retrieval exclusion while mutation is prepared or recovery is unresolved; and
5. explicit separation between reversible lifecycle governance, ordinary formation, and irreversible purge authority.

It does not own exact runtime schemas, API tokens, UI flows, filesystem mechanics, current milestone completion, or R5/R6 retirement decisions. Exact logical transition requirements remain contract-owned, exact operation behavior remains in the operation handoffs, and current repository status remains owned by [Project Status](../../PROJECT_STATUS.md).

## Semantic ownership stays with the operation

A mutation is not authorized merely because a shared publication engine, store, API endpoint, UI action, lock, or idempotency record exists.

Each operation owner remains responsible for:

- identifying the exact logical memory and current revision;
- validating character/workspace/scope authority;
- validating the allowed lifecycle transition;
- validating user-management, operator, or policy authority;
- constructing the exact immutable semantic successor;
- enforcing operation-specific payload fences;
- binding deterministic operation identity and idempotency;
- supplying any operation-specific durable final records or tombstone effects.

Shared infrastructure may execute an already-authorized immutable plan, but it does not choose a different operation, broaden scope, infer authority from persistence state, or reinterpret the semantic payload.

## Canonical lifecycle model

Subjective memory revisions are immutable. A governed mutation normally creates a consecutive successor rather than editing an existing committed revision in place.

The canonical lifecycle state set is:

```text
active
pinned
held
hidden
superseded
purged
```

Exactly one logical current-state selector may exist for each character and logical memory. The selector must name the latest accepted revision for that memory.

Ordinary Retrieval requires an unambiguous current revision whose lifecycle and mutation state are eligible. Prepared, recovery-required, corrupt, hidden, held, superseded, purged, prior, missing-current, duplicate-current, or otherwise unresolved revisions fail closed from ordinary serving.

Lifecycle visibility and currentness are semantic authority; cache rows, timestamps, UI state, filesystem order, or historical successful operations cannot select a different current revision.

## Governed operation classes

The stable lifecycle transitions are:

```text
Correct       active  -> active
Forget        active  -> hidden
Restore       hidden  -> active
Pin           active  -> pinned
Unpin         pinned  -> active
Consolidate   active Primary -> active Secondary
```

Purge is intentionally outside the ordinary reversible lifecycle family and requires separate irreversible authority.

Current detailed runtime support differs by operation and remains owned by Project Status and operation-specific handoffs. This page defines responsibility and semantic boundaries, not a claim that every target operation is implemented identically or through the same helper.

## Authorization classes

Correct, Forget, Restore, Pin, and Unpin require explicit user-management or operator authority under the Subjective memory contract.

Consolidate is different: memory policy may autonomously authorize bounded Primary-to-Secondary consolidation when its exact contract and current implementation gates permit it.

An operation cannot infer authorization from:

- an ordinary conversation request that was not routed through the owning durable-management authority;
- possession of a stale browser token or prior operation token;
- a valid canonical page or projection row;
- a current selector by itself;
- an idempotency result from another operation;
- a filesystem or advisory lock;
- a recovery classification;
- a historical Primary management implementation after its writer class has been fenced.

Authorization is operation-scoped and must be revalidated at the owning semantic boundary.

## Payload fences

A lifecycle operation cannot conceal an unrelated semantic rewrite.

Stable payload fences are:

- **Forget** changes lifecycle visibility to a hidden successor and associated governance/revision metadata; it does not silently rewrite grounded content or subjective meaning.
- **Restore** creates an active successor from the governed hidden lineage; it does not reinterpret the memory as new content.
- **Pin / Unpin** change lifecycle emphasis/visibility metadata through consecutive successors without rewriting memory meaning.
- **Consolidate** may change `formation_stage` from Primary to Secondary while preserving grounded content, subjective meaning, scope, character, memory kind, formation snapshot, and bounded strength semantics required by its exact contract.
- **Correct** may intentionally change grounded content, subjective meaning, or strength only through its explicit corrected successor while preserving the operation's identity/scope/lineage constraints.

Operation-specific documents remain authoritative for the exact field-level fences and additional records.

## Shared publication engine

The shared Subjective lifecycle publication engine owns operation-neutral execution mechanics for the operations that consume it.

The stable dependency direction is:

```text
operation owner
  -> exact authorization and semantic successor
  -> immutable publication plan

shared lifecycle publication engine
  -> reserve/fence current selector
  -> persist shared claim and prepared intent
  -> publish and verify exact canonical post-image
  -> invoke one deterministic operation finalizer
  -> finalize shared lifecycle receipt/result/current selector
  -> support exact finalized replay
  -> support caller-invoked forward recovery
```

The engine does not own the operation kind, semantic transition, user authorization, reason policy, candidate discovery, ordinary Retrieval, or a fallback operation registry.

Forget may retain specialized operation-specific finalization while anti-reformation tombstone behavior remains additional authority. That specialization does not create a second generic lifecycle publication architecture.

## Selector fencing during mutation

A prepared or unresolved mutation must not remain ordinary-Retrieval eligible simply because the previous canonical content is still present or a projection is stale.

The publication path therefore fences the logical current selector while the operation is prepared and restores normal eligibility only after exact finalization succeeds.

Stable rules are:

- prepared mutation state is retrieval-ineligible;
- unresolved recovery state is retrieval-ineligible;
- an unfinalized post-image is not normally served as the new current memory;
- stale projection rows cannot override selector/mutation state;
- replay or recovery must preserve one logical current selector;
- a failed mutation does not silently reactivate a revision whose lifecycle authority says otherwise.

Retrieval observes finalized lifecycle state; it does not complete, repair, or reinterpret a mutation.

## Publication and finalization

Mutation governance depends on the storage/finalization boundary in [Memory Storage and Recovery](storage-and-recovery.md).

Conceptually:

```text
exact authorized operation
  -> immutable successor + prepared intent
  -> exact canonical publication
  -> post-image verification
  -> matching durable finalization receipt/result
  -> final current selector and lifecycle state
```

Canonical memory remains semantic/lifecycle authority. Durable receipts finalize the operation without becoming a second editable memory body.

A post-image without its required receipt is recovery-pending. A receipt whose expected post-image cannot be verified is recovery-required/corrupt rather than success.

## Replay and idempotency

An exact repeated operation may return the already-finalized bounded result only when durable identity, target lineage, authority, successor, page image, and final bindings match the original operation exactly.

Replay does not:

- create another successor revision;
- rewrite the canonical page;
- advance the selector again;
- select a different lifecycle operation;
- weaken identity mismatch into success;
- convert a stale or foreign request into the original authority.

The same idempotency key with different memory, revision, operation, authority, scope, digest, or immutable successor is a conflict.

Idempotency prevents duplicate application; it does not grant semantic authorization.

## Forward recovery

Recovery continues only from exact durable states recognized by the owning publication protocol.

Stable recovery reasoning is:

```text
canonical image == expected pre-image
  -> exact prepared successor may be retried only under valid current authority

canonical image == expected post-image
  -> deterministic finalization may roll forward without semantic regeneration

canonical image == neither
  -> foreign/stale/corrupt state
  -> fail closed and require governed reconciliation
```

Recovery never asks an LLM to invent a replacement post-image, chooses a fallback operation, or guesses from timestamps.

Operation-specific durable state remains owned by the operation where required. A recovery classification is evidence about state, not permission to mutate.

## Forget and anti-reformation

Forget creates a canonical hidden successor rather than ordinary physical deletion.

Anti-reformation enforcement may use durable operational tombstone evidence so canonically hidden material is not automatically re-created by later formation. The tombstone is enforcement/operational authority, not a second lifecycle selector.

Stable rules are:

- canonical hidden state and tombstone enforcement must agree through the finalized Forget operation;
- a tombstone cannot silently hide an otherwise active canonical revision;
- tombstone absence cannot silently reactivate a hidden canonical revision;
- Restore clears or supersedes the applicable anti-reformation enforcement only through its own finalized operation;
- physical purge remains a separate irreversible authority.

Forget's exact current implementation and its temporary current-boundary/validation consumers remain separate from this permanent responsibility page. Their final retirement is not authorized here.

## Restore

Restore creates a new active successor from the governed hidden lineage.

It does not delete history, edit the hidden predecessor in place, or treat tombstone absence as enough to reactivate memory. Restore must bind the exact hidden current revision, operation authority, immutable successor, publication/finalization evidence, and any required tombstone release/supersession.

A stale pre-Forget token, old active revision, or unrelated lifecycle operation cannot restore the memory.

## Pin and Unpin

Pin and Unpin are lifecycle-governance operations, not general semantic edits and not reader-selection authority.

Pin may influence ordering only after all ordinary Retrieval eligibility rules pass. It cannot make hidden, held, prepared, recovery-required, corrupt, cross-scope, prior, or otherwise ineligible evidence retrievable.

Unpin removes the pinned lifecycle state through its own successor operation; it does not delete or reinterpret the memory.

## Consolidate

Consolidate moves eligible memory from Primary formation stage to Secondary formation stage while preserving the semantic dimensions that its contract forbids changing.

It is not a generic merge-anything operation and does not collapse Semantic/Episodic kind merely because formation stage changes.

Consolidation authority does not imply current ordinary reader authority. A consolidated result must still satisfy the selected family's lifecycle/currentness/retrieval rules before serving.

## Correct

Correct intentionally creates a new active successor that may alter the memory's grounded or subjective content within the exact operation contract.

Because Correct is semantically stronger than visibility-only operations, its authorization and successor validation cannot be inferred from a generic lifecycle transition alone.

The permanent architecture owns only the responsibility split: Correct's operation owner decides the exact correction; the shared publication/storage machinery publishes and finalizes the already-authorized immutable successor where the current implementation uses that shared path.

The legacy Correct handoff remains a detailed current/transition source and is not retired by this synthesis.

## Held and governed decision boundaries

`held` is a governed lifecycle state, not an ordinary active memory and not a queue retry state.

Held Apply/Discard decisions, where implemented, retain their exact runtime and governance owners. A UI-visible held candidate cannot be applied merely because it is displayed, selected, or old approval material exists.

The permanent mutation architecture requires explicit authority, exact current identity, and bounded operation execution for any durable state transition.

## Purge boundary

Purge is intentionally excluded from ordinary reversible mutation semantics.

A purge may destroy or irreversibly remove durable authority and therefore requires its own accepted authority, irreversible-operation safety model, recovery/backup implications, and explicit evidence-governance relationship.

No Correct, Forget, Restore, Pin/Unpin, Consolidate, lifecycle engine, or UI convenience path may silently implement purge by deletion.

## UI and API boundary

SOUL Lab or loopback management APIs may expose governed mutation operations, but interface presence is not authority by itself.

Stable rules are:

- browser state is not canonical lifecycle state;
- a stale UI response cannot overwrite a newer lifecycle decision;
- no implicit page load, refresh, observation, or selection triggers a durable mutation;
- public/audit responses remain content-free and omit unrestricted memory prose, paths, raw tokens, digests, or internal operation details;
- an API validates current operation authority rather than trusting client-supplied lifecycle meaning;
- UI/API implementation details remain outside this subsystem architecture.

## Relationship to Primary compatibility and RT-1

Historical Primary Correct/Forget/Pin/Unpin and worker mutation surfaces remain compatibility, regression, migration, or retirement evidence while their final RT-1 disposition is incomplete.

No historical Primary operation bypasses the exact RT-1 Primary writer decision. After `primary_writer_fenced`, an old token, lock, idempotency result, recovery state, current page, API route, or UI action cannot restore Primary mutation authority.

The permanent Subjective mutation architecture is not a compatibility workaround for old Primary semantics. Primary source documents retire or move to evidence only after R5/R6 dependency review and documentation replacement validation are complete.

## Relationship to Retrieval

Mutation and Retrieval have a one-way dependency through finalized current state:

```text
mutation owner + publication/storage
  -> finalized canonical successor
  -> exact current selector and lifecycle state
  -> projection refresh/rebuild as needed

ordinary Retrieval
  -> consumes only finalized eligible current evidence
```

Retrieval never authorizes a mutation because a candidate was selected or used. Usage, ranking, grounding, pin hints, or an empty/failed result do not become mutation authority.

Mutation does not select the ordinary reader family. RT-1 reader authority remains separate.

## Source and evidence disposition

This permanent page absorbs stable governance from the Subjective memory contract, storage contract, memory lifecycle design, shared publication engine, and operation-specific handoffs.

Detailed source pages remain valid for narrower current implementation, transition, validation, or historical roles while exact consumers still require them:

- `subjective-mem-lifecycle-publication-engine.md` — shared operation-neutral publication/replay/recovery mechanics;
- `lc1a_subjective_mem_correct.md` — current/transition Correct detail;
- `subjective-mem-forget-runtime.md` — current/transition Forget detail;
- `subjective-mem-pin-unpin-runtime.md` — Pin/Unpin implementation detail;
- `subjective-mem-restore-runtime.md` — Restore implementation detail;
- `subjective-mem-consolidate-runtime.md` — Consolidate implementation detail;
- `phase_i4_primary_mem_forget_hide_contract.md` and related evidence — Primary compatibility/history.

These are not competing permanent subsystem-architecture parents. Forget and Correct detailed source retirement remains blocked until their current-boundary/R5-owned consumers can be migrated atomically; this canonical synthesis does not bypass that stop condition.

## Stable invariants

- Durable mutation authority is operation-specific; shared mechanics do not invent semantic permission.
- Subjective memory revisions are immutable and lifecycle changes create governed successors.
- Exactly one logical current selector exists per character/memory.
- Prepared or recovery-required mutation state is ordinary-Retrieval ineligible.
- Lifecycle operations obey explicit transition and payload fences.
- Correct, Forget, Restore, Pin, and Unpin require explicit management/operator authority; Consolidate may be policy-authorized under its contract.
- Purge is a separate irreversible authority.
- Canonical publication and durable finalization evidence must converge before normal success.
- Exact replay is identity-bound and never re-applies a different operation.
- Recovery is deterministic and never semantically regenerates a different successor.
- Locks, idempotency, store state, UI state, and recovery classifications are not semantic authorization.
- Pin is an eligibility-subordinate ranking hint, not a disclosure or reader-authority bypass.
- Historical Primary lifecycle surfaces cannot bypass the RT-1 writer fence.
- Retrieval consumes finalized lifecycle state and never repairs or authorizes mutation.

## Non-goals

This architecture does not authorize:

- R5/R6 implementation or Primary deletion;
- exact lifecycle/API/UI token schemas;
- physical purge or irreversible deletion procedure;
- final filesystem/database/lock implementation;
- generic automatic correction, forget, restore, pin, or unpin from ordinary conversation;
- a universal operation registry or fallback mutation owner;
- storage repair outside the owning recovery protocol;
- reader selection, ranking algorithm, queue/scheduler policy, RelaySOUL mutation, or media-runtime behavior.
