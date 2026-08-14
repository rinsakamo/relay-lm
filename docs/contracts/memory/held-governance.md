---
relaylm_doc_type: contract
relaylm_authority: current_held_apply_discard_governance_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory_governance
relaylm_update_trigger:
  - held outcome candidate or source-evidence schema changes
  - Apply/Discard preflight governability rules change
  - preflight token or durable decision evidence changes
  - SOUL Lab Held governance request/public projection changes
  - related Primary compatibility reread behavior changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - Primary MEM lifecycle or R5/R6 retirement/cutover disposition
  - Primary MEM semantic mutation
  - B3 queue transitions, worker execution, scheduler invocation, or automatic retry
  - Subjective MEM Pin/Unpin, Correct, Forget, Restore, or other lifecycle operations
  - RelaySOUL mutation or source/body display
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase_i7ab_held_apply_discard_contract.md
  - ../../evidence/implementation/i7c_completion_report.md
  - ../../architecture/ui/soul-lab.md
  - ../../architecture/memory/mutation-governance.md
relaylm_verified_by:
  - ../../../scripts/relaylm_phase_i7c_held_governance_runtime_smoke.py
  - ../../../scripts/relaylm_phase_i7c_held_governance_concurrency_smoke.py
  - ../../../scripts/relaylm_phase_i7c_held_governance_security_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - held-outcome governance and SOUL Lab maintainers
  - RelayMEM lifecycle, queue, worker, and recovery maintainers
  - privacy, security, operator-governance, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Held Apply / Discard Governance Contract

## Authority summary

This contract owns the exact current human-governance boundary for one already-held outcome candidate.

The current implementation is split across:

```text
relaylm/relaymem_held_governance_contract.py
relaylm/relaymem_held_governance_preflight.py
relaylm/relaymem_held_governance.py
relaylm/soul_lab_held_governance.py
relaylm/lab_held_governance_api.py
```

The stable flow is:

```text
runtime-private held candidate evidence
  -> read-only Apply or Discard governability preflight
  -> short-lived runtime-private preflight token
  -> explicit human Apply/Discard confirmation
  -> governability recheck
  -> one content-free durable governance decision
  -> content-free receipt/history projection
```

This boundary records governance over an already-held outcome. It does not itself mutate Primary MEM content, rewrite B3 queue state, start a worker, invoke a scheduler, or trigger automatic retry/release.

## Current schema anchors

The exact current candidate/source/preflight schemas are:

```text
held candidate         = relaylm.mem.held_outcome_candidate.v0
source evidence ref    = relaylm.mem.held_source_evidence_ref.v0
Apply preflight        = relaylm.lab.held_apply_preflight.v0
Discard preflight      = relaylm.lab.held_discard_preflight.v0
```

The I-7C runtime evidence schemas are:

```text
candidate evidence     = relaylm.mem.held_governance_candidate_evidence.v0
preflight token        = relaylm.mem.held_governance_preflight_token.v0
durable decision       = relaylm.mem.held_governance_decision.v0
public preflight       = relaylm.lab.held_governance_preflight.v0
public receipt         = relaylm.lab.held_governance_receipt.v0
public history         = relaylm.lab.held_governance_history.v0
```

The SOUL Lab strict request schemas are:

```text
relaylm.lab.held_governance_preflight_request.v0
relaylm.lab.held_governance_decision_request.v0
```

## Governable candidate status

Only this candidate status is governable:

```text
held
```

Current already-final statuses are:

```text
applied
discarded
```

Current non-held distinction statuses are:

```text
blocked
failed
recovery_required
corrupt
terminal_succeeded
terminal_failed
```

A candidate in any status other than `held` does not become governable merely because a human selected Apply or Discard.

## Queue state is evidence only

The candidate may carry a related B3 queue state from the exact current vocabulary:

```text
queued
claimed
succeeded
failed
cancelled
dead_letter
```

Queue terminal states block held governability with bounded reasons.

I-7 never invokes B3 transition helpers and never rewrites queue files. Queue state remains evidence, not I-7 mutation authority.

## Current source authorities

The exact current allowed held source-authority values are:

```text
primary_worker_outcome
governance_flow
operator_import
```

A different source authority fails candidate validation.

Source authority must be accompanied by valid source-evidence metadata; the source-authority label alone is insufficient.

## Exact candidate key set

The current preflight helper requires the held candidate mapping to contain exactly:

```text
schema_version
runtime_private
content_included
candidate_id
operation_id
character_id
namespace
scope
status
queue_state
source_authority
source_evidence_digest
source_evidence_present
source_evidence_corrupt
source_evidence_ambiguous
source_content_included
related_primary_memory_id
related_primary_expected_revision
related_primary_physical_id
```

Missing or additional keys return:

```text
candidate_shape_mismatch
```

The candidate must have:

```text
schema_version = relaylm.mem.held_outcome_candidate.v0
runtime_private = true
content_included = false
source_content_included = false
```

Held governance therefore uses metadata/evidence references rather than carrying candidate body content through its public contract.

## Candidate token grammar

Current candidate token-like fields include:

```text
candidate_id
operation_id
character_id
namespace
scope
```

They use bounded ASCII-safe token validation with a current maximum of 128 characters.

The operation runtime additionally validates its direct request identifiers/reason/token inputs under its own bounded grammar before reading durable evidence.

## Source evidence digest

`source_evidence_digest` must be an exact lowercase 64-character hexadecimal SHA-256 digest.

The candidate also carries exact booleans:

```text
source_evidence_present
source_evidence_corrupt
source_evidence_ambiguous
```

Governability requires:

```text
source_evidence_present = true
source_evidence_corrupt = false
source_evidence_ambiguous = false
```

Failure closes to a bounded safe failure rather than exposing or reconstructing source content.

## Optional related Primary compatibility reference

The candidate may optionally include:

```text
related_primary_memory_id
related_primary_expected_revision
related_primary_physical_id
```

When `related_primary_memory_id` is null, the other two related-Primary fields must also be null.

When it is present:

- the memory ID must be a lowercase SHA-256 digest;
- expected revision must be an exact integer `>= 1`;
- physical ID may be null or a lowercase SHA-256 digest.

This is a compatibility safety check only. It does not make held governance the owner of Primary current-state semantics or R5/R6 authority.

## Related Primary reread

When a related Primary memory is present, preflight rereads it through the existing Primary current-state resolver.

The current fail-closed outcomes include:

```text
related_primary_store_root_required
related_primary_store_unavailable
related_primary_not_found
related_primary_hidden
related_primary_prepared
related_primary_recovery_required
related_primary_corrupt
related_primary_prior
related_primary_not_retrieval_eligible
related_primary_invalid
```

The current blocking Primary lifecycle set includes:

```text
hidden
```

The current blocking Primary mutation states include:

```text
prepared
recovery_required
corrupt
forget_prepared
```

Preflight also requires valid controls/page state, exact expected revision, optional exact physical ID, and retrieval eligibility.

A failed related-Primary check never triggers a Primary mutation or recovery attempt.

## R5/R6 non-authority

This contract records current compatibility behavior only.

It does not decide:

- whether Primary remains a writer;
- whether a Primary reader is retired;
- whether related Primary compatibility should eventually be removed;
- whether R5/R6 cutover has reached a particular production state;
- whether a historical Primary artifact should be reactivated.

Those decisions remain with their owning current-boundary/cutover authority outside Lane D.

## Preflight actions

The exact current governance actions are:

```text
apply
discard
```

Read-only entry points are:

```text
preflight_held_apply(...)
preflight_held_discard(...)
preflight_held_governance(...)
```

The action-specific preflight schema is selected from the Apply or Discard schema anchor.

Unknown action returns an invalid-input result rather than guessing an operation.

## Scope matching

Preflight receives expected:

```text
character_id
namespace
scope
```

The candidate must match each value exactly.

Mismatches close with bounded reasons such as:

```text
wrong_character
wrong_namespace
wrong_scope
```

The browser cannot use an Apply/Discard request to retarget a held candidate into another character/namespace/scope.

## Status and queue checks precede source adoption

A valid-shape candidate must still be a governable held outcome.

Current non-held/final states return bounded reasons including:

```text
already_applied
already_discarded
candidate_blocked_not_held
candidate_failed_not_held
candidate_recovery_required_not_held
candidate_corrupt_not_held
candidate_terminal_succeeded
candidate_terminal_failed
```

Terminal B3 evidence maps to queue-terminal reasons such as:

```text
queue_terminal_succeeded
queue_terminal_failed
queue_terminal_cancelled
queue_terminal_dead_letter
```

No human action bypasses these state distinctions.

## Preflight result

`HeldGovernancePreflightResult` carries bounded metadata including:

```text
schema_version
action
status
read_only
candidate_id
operation_id
character_id
namespace
scope
candidate_status
queue_state
related_memory_id
related_memory_checked
reason_code
blocked_reasons
```

Its public projection adds the fixed content-free/effect boundary.

Preflight never applies or discards anything; it is read-only governability evidence.

## Public effect contract

Current public effect flags for `apply` assert:

```text
held_item_adopted_contract = true
held_item_discarded_contract = false
queue_state_mutated = false
primary_mem_mutated = false
worker_started = false
scheduler_started = false
automatic_retry_or_release = false
runtime_private_content_exposed = false
```

For `discard`, only the adopted/discarded pair reverses:

```text
held_item_adopted_contract = false
held_item_discarded_contract = true
```

These flags describe the governance decision contract, not semantic Primary mutation or worker execution.

## Candidate evidence persistence

I-7C persists runtime-private candidate evidence under the character-scoped RelayMEM store in:

```text
.relaylm-held-governance-v0/
```

Current logical subdirectories are:

```text
candidates/
tokens/
decisions/
```

Before storing evidence, the runtime reruns held-governance preflight against the candidate's own character/namespace/scope and requires a held candidate.

The evidence envelope is runtime-private and explicitly `content_included=false`.

It stores the candidate metadata/digests needed for later exact revalidation, not held body text or queue/source payload bodies.

## Current preflight token TTL

The exact current token TTL is:

```text
300 seconds
```

A successful runtime preflight creates a runtime-private token envelope containing bounded identity/digest data including:

- candidate ID;
- action;
- operation ID;
- candidate digest;
- source-evidence digest;
- digest of the human reason;
- digest of the token;
- issue/expiry times.

The raw reason is not stored in the token envelope; a digest is stored instead.

The raw apply token is returned only to the bounded caller for the explicit decision step.

## Token binding

At Apply/Discard decision time, the runtime requires an existing preflight token for the exact candidate/operation slot.

It verifies at least:

```text
action
operation_id
token digest
candidate digest
expiry
```

Missing token returns the bounded preflight-required error.

Action/operation/token mismatch fails as invalid token.

An expired token cannot authorize a decision.

## Candidate-generation recheck

If the candidate evidence digest no longer matches the digest bound into the token, the runtime returns:

```text
status = stale_candidate
```

with no durable governance decision.

The public receipt reports that the candidate generation was not stable.

This prevents a token minted for one candidate generation from governing a later changed candidate.

## Governability is rerun at decision time

A matching unexpired token is not sufficient by itself.

Before writing a durable Apply/Discard decision, I-7C reruns the I-7A/B governability preflight against the current candidate and related compatibility evidence.

If governability is no longer `ready`, the decision is not persisted as applied/discarded.

The human token therefore authorizes one bounded decision attempt; it does not freeze all external state at token issuance.

## Durable decision evidence

On successful Apply or Discard, the runtime writes one runtime-private content-free decision envelope with schema:

```text
relaylm.mem.held_governance_decision.v0
```

It records bounded fields including:

- candidate ID;
- action;
- terminal governance status;
- operation ID;
- candidate digest;
- source-evidence digest;
- reason digest;
- decision time;
- fixed no-queue/no-Primary/no-worker/no-scheduler/no-auto-retry effect flags.

It does not store the raw reason or candidate/source content in the decision record.

## Current governance terminal statuses

A successful action writes:

```text
apply   -> applied
discard -> discarded
```

Repeated exact action/operation converges publicly as:

```text
apply   -> already_applied
discard -> already_discarded
```

A different action or operation against an existing stable decision returns:

```text
operation_conflict
```

A decision whose stored candidate digest no longer matches current candidate evidence returns:

```text
stale_candidate
```

## Write-once decision boundary

The durable decision is written once under the current candidate identity.

Concurrent exact decisions converge to the existing durable decision.

Conflicting operations do not overwrite the winner and do not create a second semantic mutation path.

Apply and Discard are therefore idempotent/conflict-aware governance decisions rather than toggle operations.

## Public receipt

The current receipt schema is:

```text
relaylm.lab.held_governance_receipt.v0
```

The projection includes bounded state such as:

```text
status
action
read_only
candidate_id_short
operation_id_short
reason_code
blocked_reason_ids
effects
already_applied
already_discarded
idempotent_replay
candidate_generation_stable
```

and fixed content/privacy/effect fields.

It never returns the runtime-private candidate, token envelope, decision envelope, candidate/source/reason/token digests, roots, claims, or semantic content.

## Public leakage boundary

Current preflight/receipt projections set:

```text
content_free = true
runtime_private_evidence_omitted = true
source_body_included = false
model_output_included = false
memory_content_included = false
queue_payload_included = false
primary_page_path_included = false
store_root_included = false
queue_root_included = false
claim_token_included = false
lease_owner_included = false
raw_exception_included = false
queue_state_mutated = false
primary_mem_mutated = false
worker_started = false
scheduler_started = false
automatic_retry_or_release = false
```

The public surface is deliberately not an evidence-inspection endpoint.

## History projection

`list_held_governance_history(...)` returns a read-only content-free history projection.

When a durable decision exists, each public item includes only bounded values such as:

```text
status
action
operation_id_short
decided_at
reason_code
content_free
runtime_private_evidence_omitted
```

The current history is evidence of governance decisions, not a replay queue or rollback log.

## SOUL Lab request models

`LabHeldGovernancePreflightRequest` contains exactly:

```text
schema = relaylm.lab.held_governance_preflight_request.v0
operation_id
reason
```

`LabHeldGovernanceDecisionRequest` contains exactly:

```text
schema = relaylm.lab.held_governance_decision_request.v0
operation_id
reason
apply_token
```

The shared strict request base forbids extra fields and uses strict validation.

Current request limits include:

```text
operation_id <= 128 characters
reason       <= 512 characters
apply_token  <= 8192 characters
```

The browser cannot supply store roots, queue roots, protected source bodies, queue payloads, claim tokens, lease owners, or worker/scheduler authority through these request models.

## Loopback API boundary

The SOUL Lab app installs character/namespace-scoped loopback routes for Apply preflight, Apply decision, Discard preflight, Discard decision, and history read:

```text
POST /lab/api/characters/{character_id}/held/{candidate_id}/apply/preflight
POST /lab/api/characters/{character_id}/held/{candidate_id}/apply
POST /lab/api/characters/{character_id}/held/{candidate_id}/discard/preflight
POST /lab/api/characters/{character_id}/held/{candidate_id}/discard
GET  /lab/api/characters/{character_id}/held/{candidate_id}/history
```

Server/runtime code resolves the owning store/scope authority rather than accepting arbitrary filesystem roots from the browser.

The API is an explicit human governance surface, not an implicit background mutation path.

## Related Primary is fail-closed evidence only

The public effects and durable decision records always keep:

```text
primary_mem_mutated = false
```

The related Primary reread only answers whether a held decision remains safe to govern under the current compatibility boundary.

A successful Apply decision does not call a Primary page writer, Pin/Unpin, Forget, Correct, index/log reconciler, or current-state mutation helper.

This distinction must remain true even while historical Primary compatibility exists.

## B3/worker/scheduler non-authority

Held Apply/Discard does not:

- claim or release a B3 record;
- retry a queue record;
- terminalize B3 work;
- start C1/C2 worker execution;
- invoke O1 scheduling;
- start polling, daemons, or service supervision.

If a future action needs those effects, it must cross the separately owned authority explicitly.

## No semantic body adoption in this contract

The current `apply` governance decision records that a held item is adopted **as a governance contract decision**.

The current effect flags still state:

```text
primary_mem_mutated = false
queue_state_mutated = false
```

This contract must not be cited as evidence that Apply wrote a memory page, activated a held semantic candidate, or changed a queue state.

Any later semantic materialization requires its own current owner and contract.

## Failure direction

The current boundary fails toward no governance decision when evidence cannot be trusted.

Examples:

```text
candidate shape/schema invalid
  -> invalid_input

wrong character/namespace/scope
  -> blocked

candidate not held or queue terminal
  -> blocked

source evidence missing/corrupt/ambiguous
  -> safe_failure

related Primary unavailable/hidden/prepared/recovery-required/corrupt/prior/ineligible
  -> safe_failure

preflight token missing/invalid/expired
  -> no durable decision

candidate changed after token mint
  -> stale_candidate

governability changed before decision
  -> bounded non-ready receipt

same exact durable decision
  -> already_applied / already_discarded

conflicting operation
  -> operation_conflict
```

No failure path broadens into queue, worker, Primary mutation, or content exposure.

## Stable invariants

- Only `held` candidates are governable.
- Apply and Discard are the only current actions.
- Candidate shape is exact and content-free at the governance contract boundary.
- Source evidence must be present, uncorrupt, unambiguous, and from a known source authority.
- Character, namespace, and scope must match exactly.
- B3 state is evidence only; I-7 never transitions it.
- Related Primary current-state reread is fail-closed compatibility evidence only and never mutates Primary.
- I-7 does not own or alter R5/R6 Primary cutover/retirement authority.
- Preflight is read-only.
- A short-lived token binds action, operation, candidate generation, and human reason digest.
- Governability is rerun at decision time.
- A stale candidate cannot consume an old token successfully.
- Durable decisions are content-free/write-once/idempotent/conflict-aware.
- Apply does not imply semantic memory mutation under the current effect contract.
- Discard does not rewrite queue state or memory content.
- Public projections omit runtime-private evidence, content, roots, claims, and raw exceptions.
- SOUL Lab browser requests cannot inject privileged filesystem/queue/worker authority.
- Held governance starts no worker, scheduler, retry loop, or daemon.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- Primary lifecycle/cutover/retirement semantics;
- semantic memory materialization after an Apply governance decision;
- B3 queue transition behavior;
- worker or scheduler execution;
- automatic retry/release;
- Pin/Unpin, Forget, Correct, Restore, Purge, Merge, or consolidation;
- source/body inspection UI;
- source retirement;
- repository-level sequencing.

## Related architecture

- [I-7A/B Held Apply / Discard Preflight](../../architecture/phase_i7ab_held_apply_discard_contract.md)
- [I-7C completion report](../../evidence/implementation/i7c_completion_report.md)
- [SOUL Lab UI](../../architecture/ui/soul-lab.md)
- [Memory Mutation Governance](../../architecture/memory/mutation-governance.md)
