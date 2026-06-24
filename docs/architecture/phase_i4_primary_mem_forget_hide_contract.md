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

Last reviewed: 2026-06-25 JST

## 1. Status

**Defined target contract; runtime unimplemented.**

This document fixes the exact lifecycle, identity, persistence, concurrency, API,
audit, recovery, and retrieval-exclusion contract for Phase I-4. It does not add
a production Forget apply path, SOUL Lab Forget UI, M2 lifecycle filtering, or a
Primary page writer change.

Phase I-3 Correct remains the implemented mutation baseline. Phase I-4 must not
introduce a weaker scope check, revision fence, token, idempotency, persistence,
recovery, or mutation-access boundary.

## 2. Purpose

Phase I-4 will let a user explicitly stop one current active formed Primary MEM
from participating in normal future retrieval while preserving durable audit and
historical evidence:

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

The contract guarantees that a forgotten memory is retrieval-ineligible, that
prior physical revisions cannot reappear as candidates, that past used-memory
evidence remains truthful, and that character and namespace boundaries do not
change.

## 3. Current foundation

The current implementation already provides:

- one stable logical `memory_id` across Phase I-3 correction revisions;
- monotonically increasing current revision;
- immutable prior Primary pages;
- exact character, namespace, physical identity, and revision validation;
- read-only preflight separated from explicit token-gated apply;
- per-memory lock, pending-operation fence, and operation-level idempotency;
- M3e publication plus M3f/M3g index-before-log convergence;
- prepared/applied correction recovery;
- existing M2 selection of only the corrected current revision;
- historical Phase I-2 used-memory evidence that is not rewritten;
- loopback-config and actual-peer mutation restrictions;
- no browser-supplied filesystem paths and no mock-to-real mutation fallback.

The current implementation still has a correction-specific current-revision
resolver. Phase I-4B must narrow-refactor that logic into one canonical Primary
current-state resolver shared by Correct, Forget, Lab reads, and M2. This
contract does not perform that refactor.

## 4. Scope

In scope for the target contract:

- one current active formed Primary MEM;
- one explicit user-facing Forget operation;
- one immutable hidden successor revision;
- one runtime-private prepared artifact and one immutable Forget tombstone;
- one shared current-state resolver and one shared per-memory mutation fence;
- exact preflight, apply, and bounded history schemas;
- crash-safe convergence and exact replay;
- normal M2 and RelayCTX exclusion;
- historical used-memory integrity;
- target SOUL Lab behavior and error vocabulary.

Out of scope is listed in [Explicit non-claims](#22-explicit-non-claims).

## 5. Terminology

The following terms are canonical and are not synonyms:

| Term | Canonical meaning |
|---|---|
| **Forget** | The user-facing explicit operation. It requests a lifecycle transition for one exact current active logical memory. |
| **`hidden`** | The canonical durable lifecycle state produced by a successful Forget. A hidden logical memory is current but not active and not retrieval-eligible. |
| **Forget tombstone** | The immutable runtime-private audit artifact proving the exact active-to-hidden transition and its convergence. A tombstone is not the lifecycle state and is not an M2 candidate. |
| **`active`** | The canonical lifecycle state eligible for ordinary retrieval when all other M2 gates pass. |
| **prepared** | A runtime-private operation state after the exact Forget intent is durably recorded but before the full transition is reconciled. It is not a lifecycle state exposed as current. |

“Hide” may remain in the phase nickname for discoverability, but it is not a
second operation name. “Tombstoned” is not a canonical lifecycle-state value.
Physical deletion, purge, secure erase, source deletion, and transcript deletion
are separate operations and are not implied by Forget.

## 6. Lifecycle state machine

### 6.1 Canonical state and operation state

The canonical resolver returns two orthogonal dimensions:

```text
lifecycle_state: active | hidden
mutation_state:  none | prepared | recovery_required | corrupt
retrieval_eligible: true | false
```

Only `lifecycle_state` is the durable memory lifecycle. `mutation_state` describes
whether an exact operation is pending, recoverable, or invalid. The resolver is
the only authority for “what is current, what is active, and what is retrieval
eligible.”

Target resolver schema:

```text
relaylm.mem.primary_current_state.v0
```

### 6.2 Normal transition

```text
revision N, lifecycle=active, mutation=none, retrieval_eligible=true
  -> read-only preflight
     no durable state change; revision N remains eligible
  -> Forget prepared
     revision N is quarantined; mutation=prepared; retrieval_eligible=false
  -> revision N+1 hidden successor published
     lifecycle=hidden; retrieval_eligible=false; this is the lifecycle commit point
  -> canonical index applied / log pending
     lifecycle=hidden; retrieval_eligible=false; recovery_required=true
  -> index/log converged and exclusion verified
     lifecycle=hidden; retrieval_eligible=false
  -> Forget tombstone finalized
     lifecycle=hidden; mutation=none; operation status=applied/reconciled
```

A valid prepared operation is fail-closed: while recovery is pending, neither the
prior active page nor a partially published successor may participate in normal
retrieval. This avoids re-exposure after process failure.

### 6.3 Apply and recovery states

| Condition | Resolver result | Retrieval behavior | Required action |
|---|---|---|---|
| preflight only | `active / none` | eligible | no recovery |
| prepared artifact only | `active / prepared` | excluded | resume exact operation or classify conflict |
| hidden successor published | `hidden / recovery_required` until controls converge | excluded | resume M3f/M3g convergence |
| index applied, log pending | `hidden / recovery_required` | excluded | apply missing log step only |
| controls converged, tombstone missing | `hidden / recovery_required` | excluded | verify exclusion and finalize tombstone |
| tombstone finalized | `hidden / none` | excluded | return applied result |
| invalid or ambiguous chain | `hidden-or-unknown / corrupt` | excluded | fail closed and require bounded recovery/manual handling |

A hidden lifecycle commit is never rolled back to active merely because audit
finalization or HTTP response delivery failed.

### 6.4 Repeated Forget

The outcomes are distinct:

- **exact replay**: the same operation ID and exact binding returns the original
  applied result with `idempotent_replay=true`; no revision or artifact is added;
- **already hidden**: a different operation targets a canonical hidden memory;
  return `already_hidden`, not success, and do not issue a new token;
- **stale or conflict**: an active revision changed, a token names an old physical
  page, or one operation ID has different binding data; return
  `stale_revision` or `operation_conflict`.

## 7. Identity and revision model

Forget preserves the stable logical `memory_id` and advances the canonical
revision exactly once:

```text
revision 1 active
  -> Correct
revision 2 active
  -> Forget
revision 3 hidden
```

The revision 3 hidden successor is the canonical current physical page for the
logical memory. Prior pages remain immutable audit evidence and are not current
or retrieval-eligible.

The hidden successor preserves the original scope, layer, kind, source lineage,
formed timestamp, and other non-semantic authority fields required by the
canonical Primary page contract. Forget does not rewrite title or summary as a
new semantic assertion. The bounded user reason belongs in runtime-private audit
artifacts and never becomes retrieval content.

The exact revision fence applies equally to original revision 1 memories and to
Correct-produced successor revisions. No Correct and Forget operation may both
successfully consume the same current revision.

## 8. Authoritative persistence decision

### Decision: Candidate A

Phase I-4 adopts:

```text
immutable successor Primary page
  + canonical lifecycle metadata (`hidden`)
  + monotonically increasing revision
  + existing M3e/M3f/M3g convergence
  + runtime-private prepared artifact and Forget tombstone
```

The hidden successor page is the lifecycle authority. The Forget tombstone is
audit and recovery evidence; it is not a sidecar flag that independently decides
whether the old page is active.

### Why Candidate A

- it extends the Phase I-3 immutable correction chain instead of creating a
  second current-state chain;
- Correct and Forget consume the same logical-memory revision fence;
- M2, Lab reads, future Pin/Merge, and Secondary consolidation consult one
  canonical resolver rather than guessing between page and sidecar state;
- a published hidden successor cannot become active again because a tombstone or
  response was lost;
- prior revisions remain auditable without being candidates;
- M3e/M3f/M3g remain publication and control-state authorities rather than being
  duplicated.

### Rejected: Candidate B as independent authority

An existing page plus a separately updated lifecycle/tombstone chain would make
page currentness and retrieval eligibility independently mutable. That creates a
split-authority interval in which one reader could see an active page while
another sees a tombstone. A tombstone chain may exist for audit, but it must not
be the independent lifecycle authority.

A bare sidecar boolean such as `hidden=true` is therefore forbidden as the sole
or independently committed current-state mechanism.

## 9. Correct / Forget concurrency matrix

Phase I-4 adopts one narrow **Primary mutation coordinator** shared by Correct and
Forget. It owns the existing per-memory lock namespace, one pending-operation
fence, operation identity lookup, current-state resolution, and revision claim.
It does not become a generic all-memory mutation framework in this slice.

| Starting condition | Operation A | Operation B | Required outcome |
|---|---|---|---|
| revision 1 active | Forget | none | revision 2 hidden |
| revision 2 active after Correct | Forget | none | revision 3 hidden |
| Correct preflight at N | Forget applies first at N | Correct apply | Forget wins; Correct returns `stale_revision` |
| Forget preflight at N | Correct applies first at N | Forget apply | Correct wins; Forget returns `stale_revision` |
| active N | concurrent Forget apply, different operations | concurrent Forget apply | one commit owner; loser is `stale_revision` or `operation_conflict` |
| hidden N | exact prior Forget replay | none | same success result; no new revision |
| hidden N | new Forget operation | none | `already_hidden` |
| hidden N | Correct | none | `target_not_active` |
| hidden N | future Pin | none | reject `target_not_active` unless a later contract explicitly defines otherwise |
| hidden input among future Merge sources | Merge | none | ineligible source; fail closed before multi-record claim |
| hidden N | Secondary consolidation | none | ineligible; no consolidation candidate |

The coordinator and common resolver are target implementation work for I-4B and
I-4C. Phase I-4A changes no production module.

## 10. API and exact schemas

The target SOUL Lab loopback routes follow the existing Phase I-3 routing style:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget/preflight?namespace=...
POST /lab/api/characters/{character_id}/memory/{memory_id}/forget?namespace=...
GET  /lab/api/characters/{character_id}/memory/{memory_id}/forget-history?namespace=...
```

### 10.1 Exact schema names

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

All JSON request and response models are exact-key, bounded, strict models.
Unknown fields are rejected.

### 10.2 Preflight request

```text
schema: relaylm.lab.memory_forget_preflight_request.v0
expected_revision: integer >= 1
expected_lifecycle_state: active
reason: trimmed bounded text, 1..512 characters
operation_id: trimmed opaque text, 1..128 characters
```

Preflight is read-only. It validates:

- exact schema and bounds;
- configured loopback access and actual loopback peer;
- exact character and namespace mapping;
- stable logical memory identity;
- current physical identity and expected revision;
- current lifecycle state `active`;
- canonical page/index/log convergence;
- complete correction/current-state chain;
- no conflicting pending mutation;
- operation ID availability or exact prior binding;
- bounded reason;
- mutation access policy.

It does not write a prepared artifact, successor page, index/log entry, tombstone,
or observation receipt and does not change retrieval eligibility.

### 10.3 Preflight response

```text
schema: relaylm.lab.memory_forget_preflight.v0
status: ready
read_only: true
memory_id: stable logical identity
memory_title: bounded current title, maximum 160 characters
bounded_summary: bounded current summary, maximum 512 characters
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

The preview must plainly state that future normal retrieval is excluded, physical
deletion does not occur, audit evidence remains, and past conversation evidence
is unchanged.

### 10.4 Apply request

```text
schema: relaylm.lab.memory_forget_apply_request.v0
operation_id: exact preflight operation ID
apply_token: opaque token, maximum 8192 characters
expected_revision: exact preflight revision
expected_lifecycle_state: active
```

### 10.5 Apply response

```text
schema: relaylm.lab.memory_forget_apply.v0
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

### 10.6 History response

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

Each item contains only an opaque tombstone ID, prior/result revisions,
`active -> hidden`, bounded reason, status, and timestamp. It excludes paths,
roots, page/control digests, lineage, queue/lease identity, protected source,
prompts, transcripts, credentials, and exception text.

## 11. Apply token binding

Forget requires an opaque short-lived token with a target lifetime equal to the
Phase I-3 five-minute boundary unless a later security review shortens it.

The token is integrity-protected and binds at least:

- character ID;
- namespace;
- stable logical memory ID;
- current physical identity;
- current revision;
- expected lifecycle state `active`;
- target revision;
- target lifecycle state `hidden`;
- bounded reason digest;
- operation ID;
- issue timestamp;
- expiry timestamp.

The browser never interprets token claims. Token reuse after successful apply is
accepted only as an exact replay of the same operation. Tampering, expiry,
wrong-memory, wrong-character, wrong-namespace, wrong-revision, wrong-lifecycle,
or changed-reason use is rejected.

## 12. Idempotency

Forget operation idempotency is independent of:

- Phase 6/B3 dispatch idempotency;
- M3 memory-write idempotency;
- observation receipt identity;
- HTTP retry behavior.

Rules:

1. an exact replay returns the same applied result and tombstone identity;
2. replay never creates another revision, hidden page, prepared artifact, or
   tombstone;
3. one operation ID with a different target, revision, lifecycle, reason digest,
   or token binding returns `operation_conflict`;
4. stale revision is never converted to success;
5. one current revision has one commit owner across Correct and Forget;
6. response loss after tombstone finalization converges through exact replay;
7. recovery completion produces the same result later returned by exact replay.

## 13. Audit and recovery

Runtime-private artifacts are scoped below the server-resolved character store
and are never M1/M2 candidates or public filesystem references.

```text
relaylm.mem.forget_prepared.v0
  -> hidden successor publication
  -> index/log reconciliation
  -> retrieval exclusion verified
  -> relaylm.mem.forget_tombstone.v0 finalized as applied/reconciled
```

The prepared artifact contains only the bounded exact data needed for
deterministic continuation, including the bound reason and successor candidate.
The tombstone is immutable and contains the transition identity and bounded audit
metadata. Neither artifact stores raw protected source, prompt, transcript,
credential, unrestricted page content, generic trace, or exception string.

Recovery rules:

- before hidden publication, a valid prepared operation quarantines the target
  from ordinary retrieval until it completes or is safely classified;
- after hidden publication, recovery may only converge forward; it does not
  reactivate the prior page;
- index-applied/log-pending resumes the missing log step rather than publishing a
  second successor;
- controls-converged/tombstone-missing verifies exclusion and finalizes the same
  operation;
- corrupt, ambiguous, symlinked, path-escaping, oversized, invalid-UTF-8, or
  schema-drifted lifecycle artifacts fail closed;
- successful recovery makes exact replay return the same success result.

## 14. M2 retrieval exclusion

The target behavior is implemented by the existing M2 path consulting the
canonical Primary current-state resolver. No correction-specific or
Forget-specific retriever is added.

For one logical memory:

- canonical `hidden` current state is excluded before snippet construction;
- every prior active physical revision is excluded;
- prepared or recovery-required state is excluded;
- corrupt or ambiguous lifecycle/current-state chains are excluded;
- hidden reason, prepared metadata, and tombstone metadata never reach RelayCTX;
- unrelated memories keep their existing candidate ranking and token-budget
  behavior;
- character and namespace isolation remains exact;
- M2 remains relevance owner for eligible active memories.

Fresh-conversation validation must omit the forgotten content from frontend chat
history and prove that exclusion comes from M2/current-state eligibility rather
than stale conversation context.

## 15. Historical used-memory integrity

Phase I-2 used-memory receipts remain immutable evidence of what a past
backend-bound request actually received.

After Forget, the target read projection can express:

```text
injected_summary: the historical representation actually injected
current_summary: null for a hidden current memory
current_lifecycle_state: hidden
representation_changed: unchanged unless a semantic correction also occurred
lifecycle_changed: true
```

A later schema may combine the two booleans into
`representation_or_lifecycle_changed`, but it must retain the distinction between
historical injected content and current lifecycle. The past run and conversation
must never be rewritten as though the memory had not been used.

## 16. SOUL Lab target behavior

Forget is shown only when every condition holds:

- real-server mode;
- a current formed Primary MEM;
- canonical lifecycle `active`;
- exact character and namespace scope;
- exact current revision;
- non-corrupt and fully resolvable target;
- no pending mutation.

Forget is unavailable or refused for local preview/mock, held, blocked, hidden,
superseded, prepared-only, corrupt, stale, cross-character, or cross-namespace
targets.

Target flow:

```text
select current active memory
  -> choose Forget
  -> enter bounded reason
  -> request read-only preflight
  -> review destructive-effect preview
  -> explicit confirmation
  -> apply exact token
  -> refresh current lifecycle and Forget history
```

Required UI meaning:

- “今後の通常会話では検索対象から外れます”;
- “ファイルの物理削除ではありません”;
- “監査履歴は保持されます”;
- “過去の会話履歴や、当時使用された記憶の記録は書き換えられません”.

A real mutation failure must remain an error state. It must not fall back to a
mock success or local preview mutation.

## 17. Security

The target wrapper preserves or strengthens Phase I-3 controls:

- the configured RelayLM listen host must be loopback;
- the actual ASGI peer must be loopback;
- `Host`, `Origin`, and forwarding headers are not locality authority;
- mutation accepts exact `application/json` only;
- request body size is fixed and bounded;
- strict schemas reject missing, unknown, or type-coerced fields;
- character, namespace, store root, paths, and lifecycle authority are resolved
  by the server;
- apply requires the exact unexpired token and current revision/lifecycle;
- no GET, form, query-only, wildcard-CORS, or browser-path mutation is allowed;
- response and history are bounded and rendered as text, not inserted HTML;
- public errors contain only the bounded error code;
- raw source, prompt, transcript, credentials, paths, roots, digests, lineage,
  queue/lease state, and exception strings are never public response fields.

## 18. Error vocabulary

| Public code | HTTP | Meaning |
|---|---:|---|
| `invalid_request` | 422 | Exact schema, type, bound, JSON, or semantic request validation failed. Exact media-type failure remains HTTP 415 with this bounded detail. |
| `access_refused` | 403 | Configured host, actual peer, or mutation policy refused access. |
| `target_not_found` | 404 | No target exists in the exact server-resolved scope. Wrong scope is intentionally collapsed into this code. |
| `target_corrupt` | 409 | Page, controls, lifecycle chain, or audit artifacts cannot be safely resolved. |
| `target_not_active` | 409 | The target lifecycle is not active for this operation. |
| `already_hidden` | 409 | A different operation targets a valid already-hidden memory. |
| `stale_revision` | 409 | Current physical identity, revision, or lifecycle changed after preflight. |
| `operation_conflict` | 409 | Operation ID or pending mutation is bound to different data. |
| `token_invalid` | 403 | Token integrity or exact binding failed. |
| `token_expired` | 409 | Token lifetime elapsed. |
| `store_unavailable` | 503 | The authoritative scoped store cannot be safely read or written. |
| `reconciliation_required` | 503 | Forward recovery or index/log/audit convergence is required. |
| `response_lost` | 503 | The operation may have committed but the response boundary failed; exact replay is required. |

`response_lost` is never a signal to create a new operation. Public detail is the
code only.

## 19. Fault matrix

| Fault seam | Durable/effective state | Retrieval behavior | Retry/recovery result |
|---|---|---|---|
| before prepared artifact | revision N active, no operation | eligible | repeat preflight/apply; no state to recover |
| after prepared artifact | N active plus exact prepared operation | excluded by quarantine | resume same operation or return bounded conflict |
| after hidden successor publication | N+1 hidden is lifecycle commit; controls may lag | excluded, including prior N | converge controls forward |
| after index apply / before log apply | N+1 hidden, index-applied/log-pending | excluded | apply missing log entry only |
| after index/log convergence / before tombstone | N+1 hidden, exclusion verified, audit incomplete | excluded | finalize same tombstone |
| after tombstone / before HTTP response | N+1 hidden, applied/reconciled | excluded | exact replay returns same success |
| corrupt prepared artifact | resolver corrupt/recovery-required | excluded | fail closed; no normal retrieval |
| corrupt hidden page or control chain | resolver corrupt | excluded | fail closed; bounded recovery/manual path |
| corrupt tombstone after lifecycle commit | hidden plus audit recovery required | excluded | do not reactivate; repair/finalize audit only |
| simultaneous Correct and Forget at N | one revision claimant wins | winner semantics only | loser receives stale/conflict; no fork |

## 20. Implementation work slices I-4B through I-4F

### I-4B — resolver, shared fence, and read-only contracts

- implement `relaylm.mem.primary_current_state.v0`;
- refactor Phase I-3 current-revision resolution into a narrow common resolver;
- share per-memory lock, pending-operation fence, and operation lookup between
  Correct and Forget;
- implement exact preflight and bounded history models/token issuance;
- add no mutation and no M2 behavior change beyond resolver equivalence tests.

### I-4C — atomic lifecycle apply and audit artifacts

- construct and publish the immutable hidden successor revision through M3e;
- implement prepared artifact, Forget tombstone, exact replay, and one-winner
  concurrency;
- preserve prior pages and forward-only recovery semantics.

### I-4D — convergence, M2 exclusion, and historical projection

- reuse M3f/M3g index-before-log convergence;
- make M2 and Lab current-memory reads consume the canonical resolver;
- exclude hidden, prior, prepared, recovery-required, and corrupt states;
- extend historical used-memory projection with current lifecycle without
  changing historical injected content.

### I-4E — loopback wrapper and SOUL Lab UI

- add exact loopback routes and bounded public error mapping;
- add real-server-only Forget flow, explicit confirmation, refresh, and history;
- preserve mock preview separation and stale response/token cancellation.

### I-4F — fault, security, and fresh-conversation validation

- crash at every fault-matrix seam;
- test token, scope, path, symlink, schema, bounds, and information leakage;
- test Correct/Forget and concurrent Forget races;
- prove fresh-conversation M2 and RelayCTX exclusion;
- prove historical used-memory integrity and no unrelated-ranking change.

## 21. Validation requirements

Phase I-4 implementation is not complete until automated validation proves:

- original and Correct-produced active memories can transition to one hidden
  successor revision;
- Correct and Forget cannot both commit the same current revision;
- exact replay creates no additional revision or tombstone;
- stale, cross-scope, already-hidden, pending, and corrupt cases fail closed;
- every fault seam converges without re-exposure;
- M2 excludes current hidden and all prior active physical pages;
- RelayCTX receives neither memory content nor hidden reason/tombstone metadata;
- unrelated memory ranking and character/namespace isolation remain unchanged;
- historical used-memory receipts remain immutable and truthful;
- browser mutation authority, filesystem paths, and mock fallback remain absent;
- documentation continues to state that I-4 runtime, UI, and retrieval exclusion
  are unimplemented until their respective slices land.

Phase I-4A itself is validated only as a documentation contract. Its smoke must
not import production runtime or imply that the target schemas/routes exist.

## 22. Explicit non-claims

Phase I-4A does **not** implement or claim:

- production Forget preflight or apply;
- production lifecycle/current-state resolver changes;
- production M2 exclusion or RelayCTX behavior change;
- SOUL Lab Forget UI;
- hard delete, physical deletion, secure erase, purge, source deletion, protected
  artifact deletion, or transcript deletion;
- GDPR, privacy-law, or other legal erasure compliance;
- bulk Forget;
- restore or unhide;
- Pin or Unpin;
- Merge or Supersession;
- Held Apply or Discard;
- Secondary MEM consolidation;
- RelaySOUL mutation, proposal apply, or rollback;
- queue scanner, retry scheduler, daemon, worker service, or always-on operation;
- I1-G pre-enqueue durability;
- static SOUL Lab serving;
- TTS, audio, Live2D, or avatar execution;
- a full generic memory-mutation framework refactor.
