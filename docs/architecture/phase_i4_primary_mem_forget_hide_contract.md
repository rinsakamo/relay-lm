---
relaylm_doc_type: contract
relaylm_authority: phase_i4_primary_mem_forget_hide
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: relaymem_soul_lab_integration
relaylm_update_trigger:
  - Primary MEM lifecycle or current-state resolution changes
  - Forget preflight apply or history schema changes
  - correction and Forget mutation fencing changes
  - M2 retrieval eligibility or historical used-memory projection changes
relaylm_not_authoritative_for:
  - current Forget runtime availability
  - physical deletion secure erase or legal erasure
  - Pin Merge Held Secondary MEM or RelaySOUL mutation contracts
  - queue scheduling worker supervision or I1-G durability
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4b_primary_current_state_shared_fence.md
  - memory_lifecycle_design.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_current_target.md
  - pipeline_implementation_plan.md
  - post_i3_evaluation_work_roadmap.md
  - relaymem_m3e_atomic_primary_page_writer.md
  - relaymem_m3f_primary_index_log_reconciliation_preflight.md
  - relaymem_m3g_primary_index_log_reconciliation_apply.md
  - relaymem_m3h_primary_index_log_reconciliation_recovery_audit.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
---
# Phase I-4A: Auditable Primary MEM Forget / Hide Contract

Last reviewed: 2026-06-26 JST

## 1. Status

**Defined target contract; hidden-lifecycle apply remains unimplemented.**

This document fixes the lifecycle, identity, persistence, concurrency, API, audit, recovery, and retrieval-exclusion contract for Phase I-4. Phase I-4B now implements the canonical read-only current-state resolver, shared Correct/Forget mutation fence, read-only Forget preflight, five-minute token validation, and bounded zero-item history. It does not add hidden-successor apply, tombstone finalization, M2 lifecycle exclusion, loopback mutation routes, or SOUL Lab Forget UI.

Phase I-3 Correct remains the implemented mutation baseline. Phase I-4 must not introduce a weaker scope check, revision fence, token, idempotency, persistence, recovery, or mutation-access boundary.

## 2. Purpose

Phase I-4 lets a user explicitly stop one current active formed Primary MEM from participating in normal future retrieval while preserving durable audit and historical evidence:

```text
real current active Primary MEM
  -> read-only Forget preflight
  -> bounded destructive-effect preview
  -> explicit short-lived-token confirmation
  -> revision-fenced authoritative lifecycle transition
  -> page/index/log and retrieval-exclusion convergence
  -> immutable Forget tombstone
  -> later fresh ordinary managed turn
  -> existing M2 excludes the logical memory
  -> RelayCTX receives no representation of it
```

The contract guarantees that a forgotten memory is retrieval-ineligible, prior physical revisions cannot reappear as candidates, past used-memory evidence remains truthful, and character/namespace boundaries do not change.

## 3. Current foundation

The implementation already provides:

- one stable logical `memory_id` across Phase I-3 correction revisions;
- monotonically increasing current revision and immutable prior Primary pages;
- exact character, namespace, physical identity, and revision validation;
- read-only preflight separated from explicit token-gated apply;
- per-memory lock, pending-operation fence, and operation-level idempotency;
- M3e publication plus M3f/M3g index-before-log convergence;
- prepared/applied correction recovery;
- existing M2 selection of only the corrected current revision;
- immutable historical Phase I-2 used-memory evidence;
- loopback-config and actual-peer mutation restrictions;
- no browser-supplied filesystem paths and no mock-to-real mutation fallback.

Phase I-4B adds the canonical read-only Primary current-state resolver, preserves the Phase I-3 per-memory `.lock` path as the shared Correct/Forget mutation fence, and adds read-only Forget preflight, exact-binding five-minute token validation, and bounded zero-item history. Valid unresolved prepared evidence is classified `recovery_required` and remains retrieval-ineligible.

Remaining production work begins at I-4C1.

## 4. Scope

In scope:

- one current active formed Primary MEM;
- one explicit user-facing Forget operation;
- one immutable hidden successor revision;
- one runtime-private prepared artifact and one immutable Forget tombstone;
- one shared current-state resolver and per-memory mutation fence;
- exact preflight, apply, and bounded history schemas;
- crash-safe convergence and exact replay;
- normal M2 and RelayCTX exclusion;
- historical used-memory integrity;
- target SOUL Lab behavior and bounded error vocabulary.

Out of scope is listed under [Explicit non-claims](#22-explicit-non-claims).

## 5. Canonical terminology

| Term | Canonical meaning |
|---|---|
| **Forget** | Explicit user operation targeting one exact current active logical memory. |
| **`hidden`** | Durable current lifecycle state produced by successful Forget. Hidden memory is not retrieval-eligible. |
| **Forget tombstone** | Immutable runtime-private audit/recovery artifact proving the exact active-to-hidden transition and convergence. |
| **`active`** | Canonical lifecycle state eligible for ordinary retrieval when all other M2 gates pass. |
| **prepared** | Runtime-private operation state after exact intent is durable but before full convergence. |

“Hide” may remain in the phase nickname, but it is not a second operation. “Tombstoned” is not a lifecycle-state value. Forget does not imply physical deletion, secure erase, source deletion, or transcript deletion.

## 6. Lifecycle state machine

The canonical resolver returns orthogonal lifecycle and mutation dimensions:

```text
schema: relaylm.mem.primary_current_state.v0
lifecycle_state: active | hidden
mutation_state: none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

Normal transition:

```text
revision N active / none / eligible
  -> read-only preflight
  -> exact prepared operation; revision N quarantined
  -> revision N+1 hidden successor published through M3e
  -> index applied / log pending when interrupted
  -> index/log converged and exclusion verified
  -> Forget tombstone finalized
  -> hidden / none / ineligible
```

The hidden-successor publication is the lifecycle commit point. A valid prepared operation is fail-closed. A hidden lifecycle commit never rolls back to active because tombstone finalization or HTTP response delivery failed.

| Condition | Resolver result | Retrieval behavior | Required action |
|---|---|---|---|
| preflight only | `active / none` | eligible | no recovery |
| prepared artifact only | `active / prepared` | excluded | resume exact operation or bounded conflict |
| hidden successor published | `hidden / recovery_required` | excluded | resume M3f/M3g convergence |
| index applied, log pending | `hidden / recovery_required` | excluded | apply missing log step only |
| controls converged, tombstone missing | `hidden / recovery_required` | excluded | verify exclusion and finalize tombstone |
| tombstone finalized | `hidden / none` | excluded | return applied result |
| invalid or ambiguous chain | `unknown-or-hidden / corrupt` | excluded | fail closed |

Repeated Forget outcomes are distinct:

- exact replay returns the original applied result with `idempotent_replay=true`;
- a different operation targeting canonical hidden state returns `already_hidden`;
- changed revision, physical identity, lifecycle, reason, or binding returns `stale_revision` or `operation_conflict`.

## 7. Identity and revision model

Forget preserves the stable logical `memory_id` and advances the canonical revision exactly once:

```text
revision 1 active
  -> Correct
revision 2 active
  -> Forget
revision 3 hidden
```

The hidden successor is the canonical current physical page. Prior pages remain immutable audit evidence and are neither current nor retrieval-eligible. Forget does not create new semantic assertions; the bounded user reason remains runtime-private audit content.

No Correct and Forget operation may both consume the same current revision.

## 8. Authoritative persistence decision

### Decision: Candidate A

```text
immutable successor Primary page
  + lifecycle metadata `hidden`
  + monotonically increasing revision
  + existing M3e/M3f/M3g convergence
  + runtime-private prepared artifact and Forget tombstone
```

The hidden successor page is lifecycle authority. The tombstone is audit/recovery evidence, not an independent sidecar current-state flag.

Candidate A is required because it extends the immutable correction chain, keeps one revision fence, gives M2/Lab/future operations one resolver, preserves prior revisions, and prevents a missing tombstone or response from reactivating the old page.

A bare sidecar boolean such as `hidden=true` is forbidden as the sole or independently committed current-state mechanism.

## 9. Correct / Forget concurrency

One narrow Primary mutation coordinator owns the existing per-memory lock namespace, pending-operation fence, operation lookup, current-state resolution, and revision claim. It does not become a generic mutation framework.

| Starting condition | Operation A | Operation B | Required outcome |
|---|---|---|---|
| revision 1 active | Forget | none | revision 2 hidden |
| corrected revision N active | Forget | none | revision N+1 hidden |
| Correct preflight at N | Forget applies first | Correct apply | Forget wins; Correct `stale_revision` |
| Forget preflight at N | Correct applies first | Forget apply | Correct wins; Forget `stale_revision` |
| active N | concurrent different Forget operations | concurrent apply | one commit owner; loser stale/conflict |
| hidden N | exact prior replay | none | same result; no new revision |
| hidden N | new Forget | none | `already_hidden` |
| hidden N | Correct or future Pin | none | `target_not_active` |
| hidden source | future Merge or consolidation | none | ineligible; fail closed |

I-4B completed the resolver/shared-fence/read-only portion. I-4C owns durable commit and recovery behavior.

## 10. Target API and exact schemas

Target routes follow the Phase I-3 loopback style:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget/preflight?namespace=...
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget?namespace=...
GET  /lab/api/characters/{character_id}/memory/{memory_id}/forget-history?namespace=...
```

Schema names:

```text
relaylm.lab.memory_forget_preflight_request.v0
relaylm.lab.memory_forget_preflight.v0
relaylm.lab.memory_forget_apply_request.v0
relaylm.lab.memory_forget_apply.v0
relaylm.lab.memory_forget_history.v0
relaylm.mem.primary_current_state.v0
relaylm.mem.forget_prepared.v0
relaylm.mem.forget_tombstone.v0
```

All request and response models are exact-key, bounded, and strict. Unknown fields are rejected.

### Preflight request

```text
expected_revision: integer >= 1
expected_lifecycle_state: active
reason: trimmed bounded text, 1..512 characters
operation_id: trimmed opaque text, 1..128 characters
```

Preflight validates exact loopback access, character/namespace mapping, logical and physical identity, current revision/lifecycle, page/index/log convergence, current-state chain, pending mutation, operation binding, bounded reason, and mutation access policy. It writes no prepared artifact, successor, controls, tombstone, or observation receipt.

### Preflight response

```text
schema: relaylm.lab.memory_forget_preflight.v0
status: ready
read_only: true
memory_id: stable logical identity
memory_title: maximum 160 characters
bounded_summary: maximum 512 characters
current_revision: N
current_lifecycle_state: active
target_revision: N+1
target_lifecycle_state: hidden
effects:
  ordinary_retrieval_excluded: true
  relayctx_injection_excluded: true
  physical_deletion: false
  audit_evidence_retained: true
  historical_used_memory_unchanged: true
apply_token: opaque token
expires_at: UTC timestamp
```

### Apply request and response

```text
request schema: relaylm.lab.memory_forget_apply_request.v0
operation_id: exact preflight operation ID
apply_token: opaque, maximum 8192 characters
expected_revision: exact preflight revision
expected_lifecycle_state: active

response schema: relaylm.lab.memory_forget_apply.v0
status: applied | reconciled
memory_id: stable logical identity
prior_revision: N
result_revision: N+1
lifecycle_state: hidden
retrieval_eligible: false
tombstone_id: bounded opaque identifier
applied_at: UTC timestamp
idempotent_replay: boolean
```

### History response

```text
schema: relaylm.lab.memory_forget_history.v0
source: relaylm_runtime
read_only: true
memory_id: stable logical identity
current_revision: integer
current_lifecycle_state: active | hidden
forget_count: integer
items: maximum 50 bounded entries
```

History excludes filesystem paths, roots, digests, lineage, queue/lease identity, protected source, prompts, transcripts, credentials, and exception text.

I-4B implements only the exact read-only preflight/token models and bounded zero-item history boundary. Routes and durable applied items remain I-4E/I-4C work.

## 11. Apply-token binding

The integrity-protected token uses the Phase I-3 five-minute lifetime and binds:

- character ID and namespace;
- stable logical memory ID and current physical identity;
- current revision and lifecycle `active`;
- target revision and lifecycle `hidden`;
- bounded reason digest;
- operation ID;
- issue and expiry timestamps.

The browser never interprets claims. Tampering, expiry, wrong scope, wrong memory, wrong revision/lifecycle, changed reason, or non-canonical encoding is rejected. Reuse after success is accepted only as exact replay.

## 12. Idempotency

Forget operation idempotency is independent of Phase 6 dispatch, M3 memory-write identity, observation receipt identity, and HTTP retry behavior.

Rules:

1. exact replay returns the same result and tombstone identity;
2. replay creates no new revision, page, prepared artifact, or tombstone;
3. an operation ID with different binding returns `operation_conflict`;
4. stale revision is never converted to success;
5. one current revision has one commit owner across Correct and Forget;
6. response loss converges through exact replay;
7. recovery returns the same result later returned by replay.

## 13. Audit and recovery

Runtime-private artifacts live below the server-resolved character store and are never M1/M2 candidates or public filesystem references.

```text
relaylm.mem.forget_prepared.v0
  -> hidden successor publication
  -> index/log reconciliation
  -> retrieval exclusion verification
  -> relaylm.mem.forget_tombstone.v0 finalized
```

Artifacts contain only bounded deterministic continuation and audit data. They exclude raw protected source, prompt, transcript, credentials, unrestricted page content, generic trace, and exception strings.

Recovery is forward-only after hidden publication. Index-applied/log-pending resumes the missing log step. Controls-converged/tombstone-missing finalizes the same tombstone. Corrupt, ambiguous, symlinked, path-escaping, oversized, invalid-UTF-8, or schema-drifted artifacts fail closed.

## 14. M2 and RelayCTX exclusion

I-4D makes existing M2 consult canonical current-state eligibility before snippet construction:

- canonical hidden state is excluded;
- every prior active physical revision is excluded;
- prepared and recovery-required state is excluded;
- corrupt or ambiguous chains are excluded;
- hidden reason and audit metadata never reach RelayCTX;
- unrelated memories retain ranking and token-budget behavior;
- character and namespace isolation remains exact;
- M2 remains relevance owner for eligible active memories.

Fresh-conversation validation must omit forgotten content from frontend history and prove exclusion comes from M2/current-state eligibility rather than stale conversation context.

## 15. Historical used-memory integrity

Phase I-2 used-memory receipts remain immutable evidence of what a past backend-bound request received.

A future projection may show:

```text
injected_summary: historical representation actually injected
current_summary: null for hidden current memory
current_lifecycle_state: hidden
representation_changed: boolean
lifecycle_changed: true
```

Past runs and conversations are never rewritten as though the memory had not been used.

## 16. SOUL Lab target behavior

Forget is offered only for real-server mode, current formed Primary MEM, canonical active lifecycle, exact scope/revision, resolvable controls/page, and no pending mutation.

It is unavailable or refused for local preview, held, blocked, hidden, superseded, prepared-only, corrupt, stale, cross-character, or cross-namespace targets.

```text
select current active memory
  -> choose Forget
  -> enter bounded reason
  -> request read-only preflight
  -> review destructive-effect preview
  -> explicit confirmation
  -> apply exact token
  -> refresh current lifecycle and history
```

Required meaning:

- future ordinary retrieval is excluded;
- this is not physical file deletion;
- audit evidence remains;
- past conversations and historical used-memory evidence are not rewritten.

Real mutation failure remains an error and never falls back to mock success.

## 17. Security

The wrapper preserves or strengthens Phase I-3 controls:

- configured listen host and actual ASGI peer must be loopback;
- `Host`, `Origin`, and forwarding headers are not locality authority;
- mutation accepts exact bounded `application/json` only;
- strict schemas reject missing, unknown, or coerced fields;
- character, namespace, store root, paths, and lifecycle authority are server-resolved;
- apply requires exact unexpired token and current revision/lifecycle;
- no GET, form, query-only, wildcard-CORS, or browser-path mutation;
- response/history are bounded and rendered as text;
- public errors contain bounded codes only;
- raw source, prompts, transcripts, credentials, paths, roots, digests, lineage, queue/lease state, and exceptions never appear in public responses.

## 18. Error vocabulary

| Public code | HTTP | Meaning |
|---|---:|---|
| `invalid_request` | 422 | Exact schema, type, bounds, JSON, or semantic validation failed. |
| `access_refused` | 403 | Configured host, actual peer, or policy refused access. |
| `target_not_found` | 404 | No target exists in exact server-resolved scope. |
| `target_corrupt` | 409 | Page, controls, lifecycle chain, or audit artifacts cannot be safely resolved. |
| `target_not_active` | 409 | Target lifecycle is not active. |
| `already_hidden` | 409 | A different operation targets valid hidden state. |
| `stale_revision` | 409 | Current identity, revision, or lifecycle changed. |
| `operation_conflict` | 409 | Operation ID or pending mutation has different binding. |
| `token_invalid` | 403 | Token integrity, canonical encoding, or exact binding failed. |
| `token_expired` | 409 | Token lifetime elapsed. |
| `store_unavailable` | 503 | Authoritative scoped store cannot be safely read or written. |
| `reconciliation_required` | 503 | Forward recovery or convergence is required. |
| `response_lost` | 503 | Commit may have succeeded; exact replay is required. |

## 19. Fault matrix

| Fault seam | Durable/effective state | Retrieval | Recovery result |
|---|---|---|---|
| before prepared artifact | revision N active | eligible | repeat safely |
| after prepared artifact | N active plus prepared | excluded | resume exact operation or conflict |
| after hidden successor | N+1 hidden, controls may lag | excluded | converge forward |
| after index / before log | hidden, log pending | excluded | apply missing log only |
| controls converged / before tombstone | hidden, audit incomplete | excluded | finalize same tombstone |
| tombstone / before response | hidden, applied | excluded | exact replay returns same success |
| corrupt prepared artifact | corrupt/recovery-required | excluded | fail closed |
| corrupt hidden/control chain | corrupt | excluded | bounded recovery/manual path |
| corrupt tombstone after commit | hidden, audit recovery required | excluded | never reactivate |
| simultaneous Correct and Forget | one claimant wins | winner semantics | loser stale/conflict |

## 20. Implementation slices

### I-4B — complete read-only boundary

- canonical current-state resolver;
- shared `.lock`, pending-operation fence, and operation lookup;
- exact read-only preflight/token validation;
- bounded zero-item history;
- resolver-equivalence and fail-closed prepared evidence tests;
- no hidden mutation or M2 behavior change.

### I-4C1 — hidden-successor commit ownership

- exact token/fence/revision claim;
- prepared artifact;
- hidden-successor candidate and M3e publication;
- one-winner concurrency.

### I-4C2 — exact replay and forward recovery

- prepared-operation resume;
- forward-only recovery;
- exact replay;
- tombstone finalization;
- response-loss convergence.

### I-4D — convergence and exclusion

- M3f/M3g convergence;
- M2 and RelayCTX lifecycle exclusion;
- historical lifecycle projection without rewriting past injected content.

### I-4E — loopback wrapper and UI

- exact routes and bounded public errors;
- real-server-only confirmation, refresh, receipt, and history;
- mock-preview separation and stale cancellation.

### I-4F — production validation

- crash at every fault seam;
- token, scope, path, symlink, schema, bounds, and leakage tests;
- Correct/Forget and concurrent Forget races;
- fresh-conversation M2/RelayCTX exclusion;
- historical evidence and unrelated-ranking integrity.

## 21. Validation requirements

Phase I-4 is not complete until validation proves:

- original and corrected active memories transition to one hidden successor;
- Correct and Forget cannot both commit one revision;
- exact replay creates no additional revision or tombstone;
- stale, cross-scope, hidden, pending, and corrupt cases fail closed;
- every fault seam converges without re-exposure;
- M2 excludes hidden and every prior active physical page;
- RelayCTX receives no forgotten content or hidden audit metadata;
- unrelated ranking and character/namespace isolation are unchanged;
- historical used-memory receipts remain immutable and truthful;
- browser filesystem authority and mock fallback remain absent.

I-4B validation proves only the read-only resolver/shared-fence/preflight-token-history boundary. It must not imply hidden apply, M2 exclusion, routes, or UI completion.

## 22. Explicit non-claims

Phase I-4A and the completed I-4B boundary do **not** claim:

- production hidden-successor apply or tombstone finalization;
- production M2/RelayCTX hidden-state exclusion;
- loopback mutation routes or SOUL Lab Forget UI;
- hard delete, physical deletion, secure erase, purge, source deletion, protected-artifact deletion, or transcript deletion;
- GDPR, privacy-law, or other legal-erasure compliance;
- bulk Forget, restore, or unhide;
- Pin/Unpin, Merge/Supersession, Held Apply/Discard;
- Secondary MEM consolidation;
- RelaySOUL mutation, proposal apply, or rollback;
- queue scanner, retry scheduler, daemon, worker service, or always-on operation;
- I1-G pre-enqueue durability;
- static SOUL Lab serving;
- TTS, audio, Live2D, or avatar execution;
- a broad generic memory-mutation framework refactor.
