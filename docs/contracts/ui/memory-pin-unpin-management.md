---
relaylm_doc_type: contract
relaylm_authority: current_soul_lab_primary_mem_pin_unpin_management_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - SOUL Lab Pin/Unpin route, request schema, response projection, or error mapping changes
  - Pin/Unpin management body, locality, scope, cache, confirmation, or stale-generation guards change
  - Pin/Unpin browser exact-key parsing or server redaction fields change
  - Pin/Unpin management begins to accept store/path/physical/route authority or perform automatic apply
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - Subjective MEM Pin/Unpin lifecycle transition, proposal, digest, publication, replay, or recovery semantics
  - Primary MEM I-5 compatibility, migration, retirement, or R5/R6 disposition
  - Pin ranking semantics outside the management response fields
  - Correct, Forget, Restore, Held Governance, Purge, Merge, or Supersession
  - ordinary Retrieval eligibility or candidate ranking beyond lower Pin authority
  - SOUL Lab observation, lifecycle visibility, Home conversation, or settings/characters schemas
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/ui/soul-lab.md
  - ../../architecture/phase_i5_pin_unpin_contract.md
  - ../../architecture/memory/pinned-memory.md
  - ../../architecture/memory/mutation-governance.md
relaylm_related_contracts:
  - ../memory/pin-unpin.md
  - lifecycle-visibility.md
  - soul-lab-management.md
relaylm_verified_by:
  - ../../../scripts/relaylm_phase_i5b_pin_unpin_api_projection_smoke.py
  - ../../../scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py
  - ../../../apps/soul-lab/scripts/pinUnpinUiSmoke.mjs
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - SOUL Lab Lab Observation and Pin/Unpin panel maintainers
  - Pin/Unpin runtime and compatibility maintainers
  - privacy, security, mutation-governance, and UI reviewers
relaylm_authority_level: exact_contract
---
# SOUL Lab Memory Pin / Unpin Management Contract

## Authority summary

This contract owns the exact current **SOUL Lab browser/server management boundary for Primary MEM Pin / Unpin**.

The current implementation anchors are:

```text
relaylm/soul_lab_memory_pin.py
relaylm/soul_lab_memory_pin_routes.py
relaylm/soul_lab_app.py
apps/soul-lab/src/features/lab/pinApi.ts
apps/soul-lab/src/features/lab/PrimaryMemoryPinPanel.tsx
apps/soul-lab/src/features/lab/ConnectedLabObservationPage.tsx
```

The lower operation itself remains owned by the Pin/Unpin memory authority. This management contract owns only:

```text
formed active Primary MEM row
  -> explicit browser preflight
  -> loopback-only strict request validation
  -> lower Pin/Unpin preflight authority
  -> exact bounded preflight projection
  -> explicit browser confirmation
  -> loopback-only strict apply request
  -> lower Pin/Unpin apply authority
  -> exact bounded receipt projection
  -> Lab Observation refresh
```

It does not define a new Pin state database, lifecycle transition engine, writer authority, ranking authority, or background mutation path.

## Relationship to core Pin / Unpin contract

`docs/contracts/memory/pin-unpin.md` owns the exact current Subjective MEM Pin/Unpin operation semantics.

That contract explicitly does not own API/UI policy.

This document owns the current SOUL Lab management surface without changing the lower operation semantics or deciding Primary compatibility disposition.

## Current route installation

The SOUL Lab wrapper installs the current route family through:

```text
install_primary_memory_pin_routes(...)
```

The route module is:

```text
relaylm/soul_lab_memory_pin_routes.py
```

The current routes are:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/pin/preflight
POST /lab/api/characters/{character_id}/memory/{memory_id}/pin
GET  /lab/api/characters/{character_id}/memory/{memory_id}/pin-history

POST /lab/api/characters/{character_id}/memory/{memory_id}/unpin/preflight
POST /lab/api/characters/{character_id}/memory/{memory_id}/unpin
GET  /lab/api/characters/{character_id}/memory/{memory_id}/unpin-history
```

The browser I-5B panel currently consumes the four preflight/apply routes. The two history routes are server read surfaces and are not currently part of `pinApi.ts` panel interaction.

## Loopback-only management gate

Every route in this family requires:

```text
configured SOUL Lab server host is loopback
AND
actual ASGI peer is loopback
```

using the shared current SOUL Lab loopback classifier.

Failure returns:

```text
HTTP 403
lab_management_requires_loopback_access
```

The browser cannot widen this rule with Host/Origin/forwarded headers or query data.

## Namespace query bound

Every route accepts the namespace through the current FastAPI query declaration:

```text
namespace: Query(min_length=1, max_length=128)
```

The browser URL-encodes the namespace before sending it.

## Server-owned scope resolution

The server resolves character/namespace scope through:

```text
resolve_lab_observation_scope(...)
```

and requires all of:

```text
scope.known
scope.available
scope.store_root is not None
```

Otherwise the exact route detail is:

```text
not_found_or_wrong_scope
```

with:

```text
HTTP 404
```

The browser never supplies a store root.

## Browser-supplied authority boundary

The current browser management requests may supply only bounded operation data:

```text
namespace
memory ID in the route
expected revision
reason
operation ID
apply token for apply only
```

They do not supply:

- memory store root;
- filesystem path;
- physical revision ID;
- current selector/receipt claims;
- character store partition path;
- route/backend authority;
- primary-writer decision;
- token claims;
- mutation lock identity.

The server resolves those authorities itself or delegates them to the lower operation owner.

## Strict request model base

All current Pin/Unpin mutation request models inherit:

```text
StrictLabRequestModel
```

whose Pydantic configuration is:

```text
extra = forbid
strict = true
```

Unexpected request keys and coercive type substitutions are rejected.

## Exact request-body transport

The current route helper requires the request header lowercased value to equal exactly:

```text
application/json
```

Otherwise:

```text
HTTP 415
invalid_request
```

A body must be nonempty and no larger than:

```text
16_384 bytes
```

Empty or oversized bodies return:

```text
HTTP 422
invalid_request
```

Malformed UTF-8, malformed JSON, or request-model validation failure also returns `422 invalid_request` without raw parse/validation text.

## Preflight request schemas

The exact current request schemas are:

```text
relaylm.lab.memory_pin_preflight_request.v0
relaylm.lab.memory_unpin_preflight_request.v0
```

Each preflight request contains exactly:

```text
schema
expected_revision
reason
operation_id
```

## Apply request schemas

The exact current apply request schemas are:

```text
relaylm.lab.memory_pin_apply_request.v0
relaylm.lab.memory_unpin_apply_request.v0
```

Each apply request contains exactly:

```text
schema
expected_revision
reason
operation_id
apply_token
```

## Expected revision bound

All four request models require exact integer:

```text
1 <= expected_revision <= 2_147_483_647
```

The browser passes the revision from the selected current formed memory row.

The management layer does not infer a newer revision when the browser is stale.

## Reason bound

`reason` is required and bounded to:

```text
1 .. 512 characters
```

The shared request-text validator additionally requires:

```text
value == value.strip()
```

and rejects control characters, U+2028, U+2029, and surrogate code points.

The current panel creates a browser-local default reason of the form:

```text
pin requested for <first 12 memory-id characters>
unpin requested for <first 12 memory-id characters>
```

The raw reason is not included in public apply receipts.

## Operation ID bound

`operation_id` is required and bounded to:

```text
1 .. 128 characters
```

It uses the same trimmed/control-safe text validation and additionally rejects newline, carriage return, and tab.

The current panel creates operation IDs in the form:

```text
i5b-pin-<Date.now()>
i5b-unpin-<Date.now()>
```

The operation ID is an idempotency/correlation input to the lower operation and is not projected by the browser receipt contract.

## Apply-token bound

`apply_token` exists only on apply requests.

It is required and bounded to:

```text
1 .. 8192 characters
```

with the same trimmed/control-safe validation plus newline/carriage-return/tab rejection.

The browser obtains it only from a successful exact preflight response.

It is never generated by the browser from lower claims.

## Preflight route calls

The current server preflight routes call exactly one lower operation-specific preflight with:

```text
store_root = server-resolved scope store root
character_id = path character
namespace = validated query namespace
memory_id = path memory ID
expected_revision = request field
reason = request field
operation_id = request field
```

The preflight path is read-only at the management contract level and returns a bounded tokenized plan or bounded already-state result.

## Apply route primary-writer decision

Before applying Pin or Unpin, the current server resolves:

```text
resolve_subjective_mem_retrieval_primary_writer_decision(config)
```

and supplies that server-owned decision to the lower apply function.

The browser cannot provide or override the writer decision.

This contract does not define the R5/R6 writer/cutover semantics behind that resolver.

## Apply route calls

The current apply routes call exactly one operation-specific lower apply with:

```text
server-resolved store root
path character ID
validated namespace
path memory ID
expected revision
reason
operation ID
preflight apply token
server-resolved primary-writer decision
```

No alternate store, fallback writer, or browser-selected apply authority is attempted.

## Lower error normalization

The server maps known `PrimaryPinError.code` values through this current status table:

```text
invalid_request              -> 422

target_not_found             -> 404
not_found_or_wrong_scope     -> 404

stale_revision               -> 409
target_not_active            -> 409
operation_conflict           -> 409
preflight_required           -> 409
token_expired                -> 409
target_corrupt               -> 409
recovery_required            -> 503
already_pinned               -> 409
already_unpinned             -> 409

token_invalid                -> 403
access_refused               -> 403

reconciliation_required      -> 503
store_unavailable            -> 503
```

An unrecognized lower code is normalized to:

```text
store_unavailable
HTTP 503
```

Raw lower exception text is not returned.

## Cache boundary

Successful preflight, apply, and history responses use:

```text
Cache-Control: no-store
```

The browser preflight/apply fetch also sets:

```text
credentials = same-origin
cache = no-store
```

This management operation state is not a durable browser cache authority.

## Exact preflight response schemas

The browser accepts exactly:

```text
relaylm.lab.memory_pin_preflight.v0
relaylm.lab.memory_unpin_preflight.v0
```

The server builds these responses through a bounded safe projection rather than returning arbitrary lower objects.

## Preflight exact top-level fields

The current exact preflight projection contains:

```text
schema
status
operation_kind
read_only
memory_id
current_revision
current_lifecycle_state
current_mutation_state
current_pin_state
target_pin_state
pin_state_contract_only
effects
apply_token
expires_at
```

The browser requires this exact key set.

## Preflight status vocabulary

For Pin, the browser accepts only:

```text
ready
already_pinned
```

For Unpin, it accepts only:

```text
ready
already_unpinned
```

No generic success/error status is accepted as a valid preflight object.

## Exact preflight invariants

Every accepted browser preflight requires:

```text
operation_kind == requested operation
read_only == true
memory_id == requested memory ID
current_revision == requested expected revision
current_lifecycle_state == active
current_mutation_state == none
current_pin_state in {pinned, unpinned}
target_pin_state == pinned for Pin
target_pin_state == unpinned for Unpin
pin_state_contract_only == false
```

A mismatch rejects the whole response as `schema_invalid`.

## Preflight effects

The exact common effect booleans are:

```text
audit_evidence_retained = true
ordinary_retrieval_deleted = false
ordinary_retrieval_excluded = false
physical_deletion = false
semantic_content_changed = false
```

Pin additionally requires exactly:

```text
future_priority_hint_contract = true
```

Unpin additionally requires exactly:

```text
future_priority_hint_removed_contract = true
```

The effect object requires the exact operation-specific key set.

Pin/Unpin therefore remains ranking/governance metadata and does not delete, hide, or rewrite the memory through this management boundary.

## Ready preflight token rule

When:

```text
status = ready
```

browser validation additionally requires:

```text
current_pin_state != target_pin_state
apply_token is a nonempty bounded opaque token
apply_token length <= 8192
apply_token matches [A-Za-z0-9_.-]+
expires_at is nonempty bounded safe text
expires_at length <= 128
```

The browser never applies from a ready response with a null or malformed token.

## Already-state preflight rule

For `already_pinned` / `already_unpinned`, browser validation requires:

```text
current_pin_state == target_pin_state
apply_token == null
expires_at == null
```

The UI therefore has no apply token to replay for an already-satisfied state.

## Exact apply response schemas

The browser accepts exactly:

```text
relaylm.lab.memory_pin_apply.v0
relaylm.lab.memory_unpin_apply.v0
```

The server obtains a lower result, converts it through `to_log_dict()`, and emits only the exact safe allowlisted fields below.

## Apply receipt exact fields

The current receipt contains exactly:

```text
schema
status
operation_kind
memory_id
current_revision
current_lifecycle_state
current_mutation_state
prior_pin_state
target_pin_state
retrieval_eligible
ordinary_retrieval_excluded
priority_hint_enabled
semantic_content_changed
physical_deletion
audit_evidence_retained
idempotent_replay
effect_applied
receipt_id
content_included
path_included
physical_id_included
reason_included
token_included
```

The browser requires this exact key set.

## Apply status vocabulary

For Pin, accepted status is:

```text
applied
already_pinned
```

For Unpin:

```text
applied
already_unpinned
```

## Apply receipt exact state invariants

Every accepted receipt requires:

```text
operation_kind == requested operation
memory_id == requested memory ID
current_revision == requested expected revision
current_lifecycle_state == active
current_mutation_state == none
prior_pin_state in {pinned, unpinned}
target_pin_state == operation target
retrieval_eligible == true
ordinary_retrieval_excluded == false
semantic_content_changed == false
physical_deletion == false
audit_evidence_retained == true
```

The management boundary therefore never represents Pin/Unpin as a lifecycle hide/delete operation.

## Priority-hint invariant

Browser validation requires:

```text
priority_hint_enabled == true
  exactly when target_pin_state == pinned
```

and false when target is unpinned.

The detailed candidate-ranking algorithm remains outside this UI contract.

## Effect-applied invariant

The current browser parser requires exact boolean:

```text
idempotent_replay
effect_applied
```

and requires:

```text
(status == applied) == effect_applied
```

An already-state receipt therefore cannot claim a newly applied effect.

## Receipt ID boundary

The browser accepts `receipt_id` only when it matches:

```regex
^[a-f0-9]{64}$
```

The receipt ID is the only bounded receipt identity in this response.

The response does not expose its filesystem path.

## Receipt privacy flags

Every accepted apply receipt requires exact false values:

```text
content_included = false
path_included = false
physical_id_included = false
reason_included = false
token_included = false
```

The browser rejects a response that flips any of these flags.

## Server projection failure closure

If the lower preflight/apply result does not contain the exact server-side fields needed to build the allowlisted response, the route fails closed with:

```text
HTTP 503
store_unavailable
```

It does not serialize an arbitrary lower object as a fallback.

## Browser request paths

The current browser constructs paths as:

```text
/lab/api/characters/<encoded-character>/memory/<encoded-memory>/<pin|unpin>/preflight?namespace=<encoded-namespace>

/lab/api/characters/<encoded-character>/memory/<encoded-memory>/<pin|unpin>?namespace=<encoded-namespace>
```

All path/query values are passed through `encodeURIComponent`.

## Browser transport

Every preflight/apply request currently uses:

```text
method = POST
Accept = application/json
Content-Type = application/json
credentials = same-origin
cache = no-store
body = JSON.stringify(exact request)
signal = optional AbortSignal
```

The browser does not add a backend Authorization header and does not contact a model backend directly.

## Browser request JSON

Preflight sends exactly:

```text
schema
expected_revision
reason
operation_id
```

Apply sends exactly:

```text
schema
expected_revision
reason
operation_id
apply_token
```

No store/path/physical/writer/route/token-claim field is added client-side.

## Browser error normalization

`MemoryPinError` exposes only a bounded code and uses that same code as its Error message.

The current browser recognizes bounded server detail codes including:

```text
invalid_request
target_not_found
not_found_or_wrong_scope
target_not_active
stale_revision
operation_conflict
preflight_required
token_expired
token_invalid
target_corrupt
recovery_required
store_unavailable
access_refused
response_lost
already_pinned
already_unpinned
```

A response JSON is accepted as a bounded server error only when it has exactly one key:

```text
detail
```

and the detail is in the allowlist.

## Browser fallback error mapping

When no exact bounded server error object can be read, the browser maps HTTP status as:

```text
403 -> access_refused
404 -> not_found_or_wrong_scope
409 -> operation_conflict
415 -> invalid_request
422 -> invalid_request
503 -> store_unavailable
other -> runtime_unavailable
```

Raw error bodies and raw exception text are not used as UI authority.

## Exact-key response validation

Both preflight and apply parsers require the exact current key set.

An extra field, missing field, wrong type, wrong operation, wrong memory ID, wrong revision, wrong state, wrong effect flag, malformed token, malformed receipt ID, or unexpected privacy flag rejects the whole response as:

```text
schema_invalid
```

The browser does not partially trust a mismatched response.

## Explicit confirmation boundary

The current panel does **not** apply Pin/Unpin immediately after row selection or preflight.

Apply is reachable only from:

```text
confirmApply()
```

and only when current panel state is:

```text
kind == preflight
AND
preflight.status == ready
AND
preflight.apply_token != null
```

The button text explicitly describes an explicit apply action.

Hover, selection, refresh, and initial render do not call apply.

## Panel operation state

The current local panel state is one of:

```text
idle
preflight
applied
error
```

Preflight state retains only the operation, bounded local reason, local operation ID, and exact parsed preflight response needed for confirmation.

The apply token exists only inside that current browser preflight state and the subsequent request body.

## Stale browser generation fence

The panel has a local generation counter.

Changing any of:

```text
characterId
namespace
memory.memory_id
memory.revision
```

resets panel state to `idle` and increments generation.

A preflight response is committed only when:

```text
request not aborted
AND
generation.current == request generation
```

Apply captures the current generation and applies its receipt/UI refresh only when the generation still matches.

A stale response for another character/namespace/memory/revision cannot update the new panel state.

## Selected-row boundary

The current Lab Observation page mounts `PrimaryMemoryPinPanel` from its `recent` formed Primary MEM collection after the user explicitly chooses `Pin / Unpin` on a row.

When the parent observation refreshes, selected memory is re-resolved by exact memory ID from the refreshed recent-memory list. If it no longer exists, the selected operation is cleared.

The UI does not present Pin/Unpin on held outcomes through this panel.

## Refresh after apply

After a current accepted apply receipt, the panel calls:

```text
onApplied()
```

The parent increments its refresh key and reloads the server observation bundle.

The UI therefore does not mutate its formed-memory source of truth locally and assume the server changed; it asks the server for a fresh observation.

## Preview/fallback non-authority

Lab Observation has an explicitly labeled local-preview fallback.

The page states that Correct, Forget, Pin, Held Governance, and other actions in preview are preview-only and not persisted.

The real `PrimaryMemoryPinPanel` is mounted only in the real runtime observation branch.

Mock fallback data cannot become an apply token or server mutation authority.

## History route boundary

The current server also exposes read-only:

```text
GET .../pin-history
GET .../unpin-history
```

under the same loopback and server-owned character/namespace scope gates and with `Cache-Control: no-store`.

The route delegates to the existing lower history readers.

This exact UI contract does not redefine lower receipt-history storage or record semantics, and the current `pinApi.ts`/panel does not consume these history routes.

## No semantic-content mutation

Both preflight effects and apply receipt privacy/effect flags require that Pin/Unpin through this management surface does not:

```text
rewrite semantic content
physically delete the memory
exclude ordinary retrieval solely by lifecycle
change active lifecycle to hidden
```

The operation changes the lower Pin priority-hint state under its owning contract.

## No hidden-memory admission

The browser requires current lifecycle state:

```text
active
```

and current mutation state:

```text
none
```

in both preflight and apply projections.

This management contract does not expose a Pin action that makes hidden/prepared/recovery-required/corrupt or otherwise current-ineligible memory retrievable.

## Concurrency and stale-revision boundary

The browser binds requests to one exact current revision.

The server/lower operation may return bounded stale/conflict statuses when another mutation wins.

The UI does not automatically increment the revision, reissue an apply token, or retry an apply against a newer revision.

A later explicit preflight is required after refreshed state.

## Token non-authority after refresh/change

Character, namespace, memory, or revision change resets the panel state and generation.

Therefore a preflight token retained by an older async closure cannot update/apply the current panel through the normal UI confirmation path after that state change.

Lower server token/revision revalidation remains the final authority even if a caller bypasses the normal UI.

## Privacy boundary

The current management responses exclude:

- memory content;
- raw reason text;
- apply token after apply;
- token digest/claims;
- store root/path;
- physical memory ID;
- selector/receipt paths;
- route/backend authority;
- mutation-lock identity;
- raw exception text.

Preflight necessarily returns the opaque apply token to the same-origin loopback browser because explicit confirmation requires it; the apply receipt explicitly requires `token_included=false`.

## Fail-closed invariants

The exact current management invariants include:

1. non-loopback peers receive no Pin/Unpin management authority;
2. unknown/unavailable/wrong character or namespace scope receives no store-root disclosure or mutation;
3. mutation request content type/body/JSON/model must be exact and bounded;
4. extra request fields and coercive types are rejected;
5. browser cannot submit store/path/physical/writer authority;
6. preflight binds the exact current revision and operation intent;
7. only `ready` exact preflight with a bounded opaque token can enable UI apply;
8. already-state preflight carries no apply token;
9. apply reuses the same revision/reason/operation ID plus the returned token;
10. server resolves the writer decision rather than accepting it from the browser;
11. lower errors are normalized to bounded details/status codes;
12. server projection failures become bounded 503 rather than arbitrary serialization;
13. browser exact-key/type/value parsing rejects response drift;
14. apply receipts must state content/path/physical/reason/token exclusion;
15. panel state is reset/fenced on character/namespace/memory/revision change;
16. selection/hover/refresh do not apply;
17. successful apply triggers a server observation refresh rather than local source-of-truth mutation;
18. preview fallback cannot produce real mutation authority;
19. management Pin/Unpin does not hide/delete/rewrite memory;
20. this API/UI boundary does not decide R5/R6 Primary compatibility disposition.

## Current focused evidence

The exact management contract is guarded by:

```text
scripts/relaylm_phase_i5b_pin_unpin_api_projection_smoke.py
scripts/relaylm_phase_i5b_pin_unpin_security_smoke.py
apps/soul-lab/scripts/pinUnpinUiSmoke.mjs
```

The lower apply/concurrency/ranking smokes remain evidence for the separately owned operation semantics and are not promoted into UI authority by this document.

## Source-retirement boundary

The transitional I-5B Pin / Unpin apply implementation handoff was retired in PR #1181 through its own bounded transaction, with exact provenance and recovery recorded in `records/documentation/retirement-manifest.json`. Its exact management semantics were already owned by this contract, so no management behavior changed.

This contract does not retire:

```text
docs/architecture/phase_i5_pin_unpin_contract.md
```

Nor does it retire the runtime/API/frontend implementation or smoke evidence. Further source retirement requires a separate bounded transaction with exact provenance, consumer repair, and migration disposition.
