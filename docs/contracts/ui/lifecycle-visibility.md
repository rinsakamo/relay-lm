---
relaylm_doc_type: contract
relaylm_authority: current_soul_lab_lifecycle_and_operation_visibility_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: soul_lab_ui
relaylm_update_trigger:
  - lifecycle visibility route or schema identifier changes
  - memory lifecycle, durable-finalization, queue/worker visibility fields or vocabularies change
  - lifecycle visibility scan or item bounds change
  - lifecycle visibility server aggregation or availability semantics change
  - browser exact-key validation, reason-ID bounds, fetch, or stale-result guard semantics change
  - lifecycle visibility gains mutation, scheduler, repair, or cleanup controls
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - Correct, Forget/Hide, Pin/Unpin, Held Apply/Discard, restore, purge, repair, recovery, or cleanup mutation semantics
  - Primary current-state mutation, retrieval exclusion, or historical used-memory receipt semantics
  - durable-finalization replay, completion, isolation, retention, or cleanup semantics
  - B2/B3 queue lifecycle, C2 worker execution, scheduler execution, or stale recovery
  - Phase I-2 last-run, used-memory, held-memory, or observation schemas outside this projection
  - SOUL Lab settings/characters management schemas or Home Chat Completions transport
  - browser-owned character, namespace, store, queue-root, protected-source-root, or backend authority
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/ui/soul-lab.md
  - ../../architecture/soul_lab_ui_b1a_lifecycle_visibility.md
  - ../../architecture/memory/mutation-governance.md
  - ../../architecture/memory/formation.md
  - ../../architecture/runtime/scheduler.md
relaylm_related_contracts:
  - soul-lab-management.md
  - home-conversation.md
  - ../memory/held-governance.md
  - ../memory/pin-unpin.md
  - ../runtime/scheduler-queue-lane.md
  - ../runtime/scheduler-replay-lane.md
relaylm_verified_by:
  - ../../../scripts/relaylm_ui_b1a_lifecycle_visibility_api_smoke.py
  - ../../../scripts/relaylm_ui_b1a_lifecycle_visibility_security_smoke.py
  - ../../../apps/soul-lab/scripts/lifecycleVisibilitySmoke.mjs
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - SOUL Lab Home and Lab Observation lifecycle-visibility maintainers
  - Primary current-state, durable-finalization, queue, worker, and scheduler maintainers
  - privacy, security, lifecycle, recovery, and UI reviewers
relaylm_authority_level: exact_contract
---
# SOUL Lab Lifecycle Visibility Contract

## Authority summary

This contract owns the exact current **read-only SOUL Lab lifecycle and operation visibility boundary** implemented by:

```text
relaylm/soul_lab_lifecycle_visibility_projection.py
relaylm/soul_lab_app.py
apps/soul-lab/src/features/lifecycle/lifecycleVisibilityApi.ts
```

The exact current schema is:

```text
relaylm.lab.lifecycle_visibility.v0
```

The exact current route is:

```text
GET /lab/api/characters/{character_id}/lab/lifecycle-visibility?namespace=...
```

The boundary is interpretive only:

```text
server-owned observation scope
  -> current Primary lifecycle read
  -> bounded durable-finalization visibility scan
  -> bounded queue/worker visibility scan
  -> content-free/read-only projection
  -> exact-key browser validation
  -> stale-character/generation guard
  -> display only
```

It does not add a command route, apply token, scheduler control, worker control, replay control, repair action, recovery action, restore action, purge action, or cleanup action.

## Permanent architecture relationship

`docs/architecture/ui/soul-lab.md` owns the stable browser/server authority boundary for SOUL Lab.

`docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md` is the implementation handoff that introduced this visibility slice.

This document owns the continuing exact API/projection/browser-consumption contract and does not retire either architecture source.

## Server route locality

The lifecycle route uses the same existing SOUL Lab management locality guard as other Lab API routes.

A successful read therefore requires both:

```text
configured RelayLM listen host is loopback
AND
actual ASGI peer is loopback
```

The route does not trust `Host`, `Origin`, or forwarded headers as transport-peer proof.

A refused remote read returns the existing management refusal:

```text
HTTP 403
lab_management_requires_loopback_access
```

The focused security smoke verifies that spoofed loopback-looking headers from a non-loopback ASGI peer remain refused.

## Core route isolation

Lifecycle visibility locality does not replace Core route policy.

The current security smoke verifies that a remote peer refused by lifecycle visibility can still receive the normal Core behavior from:

```text
GET /healthz
GET /v1/models
```

The lifecycle route therefore remains a Lab management/observation surface, not a global server-access gate.

## Read-only method boundary

The current lifecycle route is GET-only.

The focused server security smoke verifies that these methods on the same route are rejected:

```text
POST
PUT
PATCH
DELETE
```

with:

```text
HTTP 405
```

No mutation request model is installed at this path.

## Cache boundary

A successful lifecycle response includes:

```text
Cache-Control: no-store
```

The browser fetch also requests:

```text
cache: no-store
credentials: same-origin
```

The current visibility contract does not authorize durable browser caching of runtime lifecycle state.

## Server-owned character and namespace scope

The path provides a character ID and the query provides a namespace string, but the route resolves them through the existing SOUL Lab observation scope resolver:

```text
resolve_lab_observation_scope(
  config,
  character_id=character_id,
  namespace=namespace,
)
```

The browser does not submit a store path, queue root, durable-finalization root, protected-source root, scheduler setting, or backend identity.

## Namespace query bound

The exact current route declares:

```text
namespace: Query(min_length=1, max_length=128)
```

FastAPI therefore rejects values outside that query-shape boundary before lifecycle projection construction.

## Unknown character boundary

The shared observation-scope wrapper checks:

```text
scope.known
```

When false, the route returns:

```text
HTTP 404
lab_character_not_found
```

A known-but-currently-unavailable scope may still yield a bounded projection whose `availability` is `unavailable`; unknown character identity does not.

## Exact top-level schema

The exact top-level model is `LabLifecycleVisibilityProjection`.

Its current fields are:

```text
schema
source
read_only
availability
capability
character_id
namespace
memory_items
durable_finalization
queue_worker
fresh_conversation
mutation_controls_exposed
scheduler_controls_exposed
repair_controls_exposed
raw_content_included
raw_paths_included
raw_private_identifiers_included
bounded_reason_ids
```

The Pydantic model uses:

```text
extra = forbid
```

and the browser independently requires the exact key set.

## Exact top-level constants

The exact current fixed values are:

```text
schema = relaylm.lab.lifecycle_visibility.v0
source = relaylm_runtime
read_only = true
capability = read_only_lifecycle_and_operation_visibility
mutation_controls_exposed = false
scheduler_controls_exposed = false
repair_controls_exposed = false
raw_content_included = false
raw_paths_included = false
raw_private_identifiers_included = false
```

These flags are part of the exact contract, not optional UI hints.

## Availability vocabulary

The exact current shared `Availability` vocabulary is:

```text
available
empty
unavailable
not_connected
```

It is used by the top-level projection, durable-finalization visibility, and queue/worker visibility.

## Top-level availability aggregation

The exact current top-level availability calculation is:

```text
if scope.available is false
  -> unavailable

else if memory availability == available
     OR durable availability == available
     OR queue availability == available
  -> available

else if memory availability == empty
     OR durable availability == empty
     OR queue availability == empty
  -> empty

else if durable availability == not_connected
     AND queue availability == not_connected
  -> not_connected

else
  -> unavailable
```

This is an aggregate display availability only. It does not assert that every lower subsystem is healthy or connected.

## Top-level reason aggregation

The current builder combines bounded reason IDs from:

```text
observation scope
memory visibility
durable-finalization visibility
queue/worker visibility
```

through the existing SOUL Lab reason normalizer.

The top-level Pydantic field permits at most:

```text
32 reason IDs
```

The browser independently requires no more than 32 reason strings using its current bounded reason grammar.

## Memory item limit

The exact current server limit is:

```text
_MAX_MEMORY_ITEMS = 20
```

The browser independently rejects a top-level `memory_items` array longer than 20.

When the server discovers more logical memory IDs than the bound, it emits only the sorted first twenty and adds the bounded reason:

```text
lifecycle_visibility_memory_limit_reached
```

The projection does not silently imply that only twenty logical memories exist.

## Memory lifecycle vocabulary

The exact current public lifecycle vocabulary is:

```text
active
hidden
prepared
recovery_required
corrupt
unknown
```

This vocabulary is display-only. It does not define or execute mutation transitions.

## Physical-status vocabulary

The exact current `current_physical_status` vocabulary is:

```text
current
hidden
prepared
recovery_required
corrupt
unknown
```

For an `active` public lifecycle, physical status is exactly:

```text
current
```

For every other public lifecycle, physical status is the same token as the lifecycle value.

## LabLifecycleMemoryItem exact fields

Each current memory item contains exactly:

```text
memory_id
current_lifecycle_state
current_revision
current_physical_status
retrieval_eligible
historical_used_memory_remains_unchanged
bounded_reason_ids
```

The browser requires this exact key set.

## Memory ID shape

The current browser parser accepts `memory_id` only when it is exactly:

```regex
^[0-9a-f]{64}$
```

The server collects only logical IDs satisfying the same lowercase 64-hex shape before building normal items.

The memory ID is a bounded opaque lifecycle reference. The projection still explicitly excludes raw queue identifiers, raw durable-finalization locators, paths, claims, and other private identifiers.

## Current revision

`current_revision` is either:

```text
null
```

or a positive integer:

```text
>= 1
```

An unresolved current state uses null.

## Retrieval eligibility

`retrieval_eligible` is either:

```text
true
false
null
```

The server maps a successfully resolved current-state value to exact boolean.

An unresolved memory uses null.

The field reports current eligibility only. It does not initiate retrieval and does not expose retrieval content.

## Historical used-memory invariant

Every memory item contains exact:

```text
historical_used_memory_remains_unchanged = true
```

This communicates that current lifecycle exclusion does not rewrite historical used-memory observation evidence.

The lifecycle visibility layer does not edit historical receipts.

## Memory source inputs

For an available observation scope with a store root, the server reads the current Primary control state through the existing read helper and loads the current-state index for the exact namespace.

It derives candidate logical IDs from:

```text
current control index entries in the namespace
current control log entries in the namespace
current_by_logical keys in the current-state index
receipts_by_logical keys in the current-state index
```

Physical IDs from the control state are mapped through the current-state index's logical mapping when present.

Only lowercase 64-hex logical IDs are retained.

## Memory ordering

The server sorts the logical memory IDs before applying the twenty-item limit.

The output is therefore deterministic for an unchanged underlying current state.

## Memory control-state unavailable

When the scope is unavailable or no store root exists, memory visibility returns:

```text
items = []
availability = unavailable
```

with the scope's bounded reasons.

When the Primary control-state read fails, memory visibility returns an empty unavailable view with normalized lower reasons.

## Current-state index unavailable

If loading the current-state index raises, memory visibility returns:

```text
items = []
availability = unavailable
reason = primary_current_state_index_unavailable
```

The raw exception is not projected.

## Individual current-state resolution failure

For each selected logical memory ID, current state is resolved through the existing Primary current-state resolver.

If that resolver raises `PrimaryCurrentStateError`, the server does not expose the raw error and does not omit the logical memory silently.

It emits an unknown memory item:

```text
current_lifecycle_state = unknown
current_revision = null
current_physical_status = unknown
retrieval_eligible = null
historical_used_memory_remains_unchanged = true
bounded_reason_ids = [primary_current_state_unresolved]
```

and also adds the same bounded reason to aggregate memory reasons.

## Public lifecycle mapping

The current server mapping from lower current-state values is exactly ordered:

```text
mutation_state == corrupt
  -> corrupt

mutation_state == recovery_required
  -> recovery_required

mutation_state == prepared
  -> prepared

lifecycle_state == hidden
  -> hidden

lifecycle_state == active AND mutation_state == none
  -> active

otherwise
  -> unknown
```

This visibility mapping does not redefine the lower mutation-state machine.

## Memory availability result

After a successful current-state/control read:

```text
at least one emitted memory item -> available
no emitted memory item           -> empty
```

This availability says whether bounded lifecycle items were visible, not whether ordinary memory retrieval has or has not occurred.

## Durable-finalization exact fields

`LabDurableFinalizationVisibility` currently contains exactly:

```text
availability
status
pending_count
complete_count
isolated_count
content_free
locator_values_included
path_values_included
bounded_reason_ids
```

Exact fixed flags are:

```text
content_free = true
locator_values_included = false
path_values_included = false
```

## Durable-finalization status vocabulary

The exact current browser/server status vocabulary is:

```text
pending
complete
isolated
mixed
none
unknown
unavailable
not_connected
```

The current server aggregation emits the status values derived below; `unknown` remains an accepted schema value for forward-safe exact current model compatibility.

## Durable root not configured

If:

```text
config.relaymem_slp_durable_finalization_root
```

is not a nonempty string, the projection is:

```text
availability = not_connected
status = not_connected
pending_count = 0
complete_count = 0
isolated_count = 0
reason = durable_finalization_root_not_configured
```

No path value is emitted.

## Durable root unavailable

The configured durable root must currently be:

```text
absolute
not a symlink
an existing directory
```

Otherwise:

```text
availability = unavailable
status = unavailable
reason = durable_finalization_root_unavailable
```

with zero counters.

This is visibility checking only and is not the hardened replay-lane root authority.

## Durable scan failure

If directory enumeration raises `OSError`, the result is:

```text
availability = unavailable
status = unavailable
reason = durable_finalization_scan_failed
```

with no raw exception/path.

## Shared visibility scan bound

The exact current visibility scan bound is:

```text
_MAX_SCAN_ENTRIES = 4096
```

Both durable-finalization visibility and queue/worker visibility use this bound.

When the durable scan reaches the bound, it stops adding entries and records:

```text
durable_finalization_scan_limit_reached
```

The lifecycle visibility layer does not perform an unbounded directory scan.

## Durable component recognition

The current display scanner recognizes filename families beginning with:

```text
durable-finalization-v0-
durable-finalization-completion-v0-
```

followed by an exact lowercase 64-hex locator and one of the current recognized component suffix forms.

Only non-symlink regular files are considered after filename matching.

The raw locator is used only as an internal grouping key and is not projected.

## Durable component classes used for display

For each grouped locator, the visibility scanner records display component classes:

```text
isolation
completion
seal
other
```

`other` includes recognized base/ordinary segment components and does not itself create a pending/complete/isolated count.

This scanner does not parse or validate durable record contents and therefore does not replace O1B/I1-G replay/finalization correctness authority.

## Durable display classification precedence

For each internal locator group, the exact current display classification is:

```text
if isolation component present
  -> isolated_count += 1

else if completion component present
  -> complete_count += 1

else if seal component present
  -> pending_count += 1

else
  -> no state counter increment
```

This is a visibility approximation over recognized component presence, not a lifecycle transition or replayability proof.

## Durable availability

After the bounded scan:

```text
at least one recognized locator group -> available
no recognized locator group           -> empty
```

A group containing only `other` components therefore can make availability `available` while all three state counters remain zero.

## Dominant status rule

The current generic status reducer receives the ordered counter mapping.

It computes:

```text
no positive counters
  -> none

exactly one positive category
  -> that category name

two or more positive categories
  -> mixed
```

For durable-finalization the ordered categories are:

```text
pending
complete
isolated
```

## Queue/worker exact fields

`LabQueueWorkerVisibility` currently contains exactly:

```text
availability
status
queued_count
processing_count
formed_count
held_count
blocked_count
failed_count
content_free
queue_identifiers_included
claim_values_included
scheduler_controls_exposed
worker_controls_exposed
bounded_reason_ids
```

Exact fixed flags are:

```text
content_free = true
queue_identifiers_included = false
claim_values_included = false
scheduler_controls_exposed = false
worker_controls_exposed = false
```

## Queue/worker status vocabulary

The exact accepted current status vocabulary is:

```text
queued
processing
formed
held
blocked
failed
mixed
none
unknown
unavailable
not_connected
```

As with durable visibility, `unknown` is accepted by the model/browser even though the current normal counter reducer emits category/none/mixed values.

## Queue root not configured

If:

```text
config.relaymem_slp_queue_root
```

is not a nonempty string:

```text
availability = not_connected
status = not_connected
all counts = 0
reason = queue_root_not_configured
```

No queue root value is projected.

## Queue root unavailable

The current visibility root must be:

```text
absolute
not a symlink
an existing directory
```

otherwise:

```text
availability = unavailable
status = unavailable
all counts = 0
reason = queue_root_unavailable
```

This is a read-only display scan and does not replace the secure B3/O1C queue-root authority.

## Queue scan failure

If directory enumeration raises `OSError`:

```text
availability = unavailable
status = unavailable
reason = queue_scan_failed
```

No raw exception/path is projected.

## Queue visibility scan bound

Queue enumeration uses the same exact limit:

```text
4096 entries
```

When the bound is reached, scanning stops and records:

```text
queue_scan_limit_reached
```

Entries beyond the limit are not read for display.

## Queue filename eligibility

Only non-symlink regular files whose names match the exact current queue record filename family are read:

```text
<FILENAME_PREFIX><64 lowercase hex>.json
```

The queue-record module remains authoritative for the prefix and canonical record schema.

The filename itself is never projected.

## Queue record byte bound

Each eligible queue file is read as bytes.

If reading raises `OSError`, the scanner records:

```text
queue_record_read_failed
```

and continues to the next bounded entry.

If the byte string is empty or exceeds the existing queue-record `MAX_RECORD_BYTES`, the scanner records:

```text
queue_record_size_invalid
```

and continues.

## Queue record canonical validation

The lifecycle scanner passes eligible bytes through the existing canonical queue record decoder and mapping validator.

Decode failure appends the lower bounded decoder reason or:

```text
queue_record_invalid
```

Mapping validation reasons are added to the bounded reason list.

Invalid records do not contribute to display state counters.

The visibility scanner does not repair or mutate them.

## Queue state bucket mapping

For a validated queue record, current display bucketing is exactly:

```text
state == queued
  -> queued

state == claimed
  -> processing

state == succeeded
  -> formed

otherwise
  -> inspect lowercased "failure_class:terminal_reason_id"
```

For the remaining states/markers:

```text
marker contains "held"
  -> held

else marker contains "blocked" OR "policy"
  -> blocked

else
  -> failed
```

This is a display categorization only; it does not redefine the B3/C2 state machine.

## Queue availability

The total queue/worker display count is the sum of:

```text
queued
processing
formed
held
blocked
failed
```

Then:

```text
total > 0 -> availability = available
total == 0 -> availability = empty
```

A bounded scan containing only malformed/unrecognized records can therefore be `empty` while carrying bounded validation reasons.

## Queue dominant status order

The generic dominant reducer receives the queue counters in this current insertion order:

```text
queued
processing
formed
held
blocked
failed
```

One positive category yields that token; multiple positive categories yield `mixed`; none yields `none`.

## Fresh-conversation exact fields

`LabFreshConversationVisibility` contains exactly:

```text
browser_local_session_reset_visible
durable_memory_store_reset
durable_memory_store_retained
active_current_memories_remain_retrieval_eligible
hidden_or_current_ineligible_memories_remain_excluded
home_transcript_is_durable_source
durable_transcript_persistence
```

The exact current values are:

```text
browser_local_session_reset_visible = true
durable_memory_store_reset = false
durable_memory_store_retained = true
active_current_memories_remain_retrieval_eligible = true
hidden_or_current_ineligible_memories_remain_excluded = true
home_transcript_is_durable_source = false
durable_transcript_persistence = false
```

These are explanatory lifecycle semantics; the lifecycle route does not implement New Conversation itself.

## Fresh-conversation meaning

The exact display contract communicates:

```text
New Conversation
  -> browser-local Home session reset
  -> durable memory store retained
  -> active current memories may remain retrieval eligible
  -> hidden/current-ineligible memories remain excluded
  -> Home transcript is not a durable source
  -> Home transcript is not durably persisted by this UI path
```

This agrees with the separate Home browser transport contract and does not add persistence or deletion authority.

## Browser route construction

The current browser loader is:

```text
loadLifecycleVisibility(characterId, namespace, signal?)
```

It URL-encodes both user-interface-selected bounded labels and calls:

```text
/lab/api/characters/<encoded character>/lab/lifecycle-visibility?namespace=<encoded namespace>
```

using:

```text
method = GET
Accept = application/json
cache = no-store
credentials = same-origin
signal = supplied AbortSignal
```

It does not include a request body, Authorization header, root/path value, mutation command, scheduler control, or apply token.

## Browser HTTP failure mapping

A non-OK response becomes `LifecycleVisibilityError`.

The exact current error code is:

```text
HTTP 403
  -> lifecycle_visibility_access_refused

any other HTTP status N
  -> lifecycle_visibility_http_<N>
```

The browser does not treat a failed response body as a trusted lifecycle projection.

## Browser schema failure

After a successful response, the browser JSON-decodes the body and calls:

```text
parseLifecycleVisibility(payload, characterId, namespace)
```

If parsing returns null, the loader throws:

```text
LifecycleVisibilityError(
  invalid_lifecycle_visibility_schema
)
```

The error object stores only its bounded code as the Error message and name:

```text
LifecycleVisibilityError
```

## Browser exact-key top-level validation

The parser requires the top-level object to have **exactly** the current projection key set.

Extra and missing keys are both rejected.

It then requires exact schema/source/read-only/capability/control/privacy values, exact character and namespace equality to the request inputs, valid availability, an array of no more than twenty memory items, exact nested record objects, and bounded reason IDs.

This prevents newly added or malformed server fields from becoming implicitly trusted before a contract revision.

## Browser character/namespace fence

The parser requires:

```text
value.character_id == requested characterId
value.namespace == requested namespace
```

A server response for a different character or namespace is rejected even if the rest of the JSON has a valid schema.

This is an API-level stale/misrouting fence before React wrapper generation checks.

## Browser memory-item exact validation

Every memory item must have exactly the current seven keys and satisfy:

```text
memory_id = lowercase 64-hex
lifecycle value in exact vocabulary
current_revision = null OR integer >= 1
physical status in exact vocabulary
retrieval_eligible = null OR boolean
historical_used_memory_remains_unchanged = true
bounded reason IDs valid
```

One invalid memory item rejects the whole server projection.

The browser does not accept a partially valid memory list.

## Browser durable exact validation

The durable-finalization object must have exactly the current keys.

It requires:

```text
valid availability
valid durable status
pending_count nonnegative integer
complete_count nonnegative integer
isolated_count nonnegative integer
content_free = true
locator_values_included = false
path_values_included = false
bounded reason IDs valid
```

Any mismatch rejects the whole projection.

## Browser queue exact validation

The queue/worker object must have exactly the current keys and requires:

```text
valid availability
valid queue status
all six counts nonnegative integers
content_free = true
queue_identifiers_included = false
claim_values_included = false
scheduler_controls_exposed = false
worker_controls_exposed = false
bounded reason IDs valid
```

Any mismatch rejects the whole projection.

## Browser fresh-conversation exact validation

The fresh-conversation object must have exactly the seven current keys and every current fixed boolean value must match exactly.

Any semantic flip — for example `durable_memory_store_reset=true` or `home_transcript_is_durable_source=true` — rejects the server projection rather than silently changing UI meaning.

## Browser reason-ID grammar

The current browser helper accepts a reason list only when:

```text
Array.isArray(value)
length <= 32
```

and every item matches:

```regex
^[a-z0-9][a-z0-9_:-]{0,127}$
```

All reason entries must be strings.

This is a browser validation bound; lower components retain authority over the meaning of their own reason IDs.

## Browser integer validation

Current helper rules are:

```text
positive integer
  -> typeof number
     integer
     >= 1

nonnegative integer
  -> typeof number
     integer
     >= 0
```

NaN, fractional values, numeric strings, booleans, null outside explicitly nullable fields, and negative values are rejected.

## React stale-result guards

The current lifecycle wrappers on Home and Lab Observation guard asynchronous reads with both:

```text
generation.current
```

and:

```text
projection.character_id == activeCharacter.characterId
```

before committing fetched data to the active view.

Character switching therefore cannot allow an older request result to update a newer character view merely because both requests completed successfully.

The API-level character/namespace fence and wrapper generation fence are cumulative defenses.

## Read-only panel boundary

The current lifecycle panel is explicitly labeled:

```text
READ-ONLY LIFECYCLE VISIBILITY
```

The focused frontend smoke requires the panel source to contain no:

```text
<button
onClick
dangerouslySetInnerHTML
```

and no control-like command wording representing scheduler/worker/replay/repair/cleanup authority.

The panel is a display surface, not an operation launcher.

## Control text exclusions

The frontend smoke also rejects lifecycle-panel leakage/control text for current private/control tokens including:

```text
apply_token
lease_token
claim_owner
dispatch_idempotency_key
queue_root
protected_source_root
```

The server security smoke separately rejects content/path/claim/job/dispatch/traceback canaries in serialized projections.

## Durable-finalization content-free boundary

The lifecycle projection shows only:

```text
availability
bounded status
pending/complete/isolated counts
bounded reasons
fixed content/path exclusion flags
```

It does not expose:

- locator digests;
- filenames;
- root paths;
- component contents;
- exact completion or isolation record bodies;
- replay locks;
- private timestamps.

Because its scanner is display-oriented, O1B/I1-G authorities remain the sole owners of replay correctness and durable-finalization mutation.

## Queue/worker content-free boundary

The lifecycle projection shows only:

```text
availability
bounded status
six aggregate counts
bounded reasons
fixed content/identifier/control exclusion flags
```

It does not expose:

- queue filenames;
- job IDs;
- dispatch IDs;
- claim owner;
- lease token;
- retry timestamp;
- record body;
- queue root;
- protected-source locator/content;
- worker-private result.

B3/C2/O1C/O1E remain the mutation/execution authorities.

## Memory visibility content boundary

Memory lifecycle items intentionally expose the bounded opaque logical memory ID and current lifecycle/revision/eligibility metadata.

They do not expose:

- memory page body;
- title or summary content through this B1A item type;
- store path;
- tombstone body;
- mutation payload;
- apply/confirmation token;
- protected source;
- raw current-state index/receipt data.

Content-bearing memory observation remains on separately governed SOUL Lab observation projections.

## No mutation by projection builder

`build_lab_lifecycle_visibility_projection(...)` constructs read-only models.

It does not call:

- Correct apply;
- Forget/Hide apply;
- Pin/Unpin apply;
- Held Apply/Discard;
- restore/unhide;
- purge;
- B3 transition helpers;
- C2 worker execution;
- O1B replay delegation;
- scheduler service/process entry points;
- durable-finalization cleanup;
- current-state repair.

Lower reads may observe filesystem state but do not confer mutation authority on B1A.

## No scheduler controls

Both top-level and queue/worker projection flags state that scheduler controls are absent.

The UI does not run a scheduler, worker, queue claim, replay, or stale recovery operation from this panel.

A displayed `pending`, `queued`, `processing`, `blocked`, or `failed` state is not a clickable command or implicit authorization to remediate it.

## No repair controls

Top-level exact:

```text
repair_controls_exposed = false
```

means a display state such as:

```text
prepared
recovery_required
corrupt
isolated
failed
```

does not expose a repair/recovery/cleanup action through this contract.

The lower owning mutation/recovery contracts remain authoritative.

## Current focused server evidence

The API smoke:

```text
scripts/relaylm_ui_b1a_lifecycle_visibility_api_smoke.py
```

verifies current-state display, mixed durable counts, mixed queue/worker buckets, fresh-conversation semantics, exact control/privacy flags, and absence of private content/job/dispatch/claim/path/traceback canaries.

The security smoke:

```text
scripts/relaylm_ui_b1a_lifecycle_visibility_security_smoke.py
```

verifies loopback-only access, no-store, schema/read-only flags, private canary exclusion, 405 on mutation methods, spoofed remote refusal, and Core-route regression safety.

## Current focused browser evidence

The frontend smoke:

```text
apps/soul-lab/scripts/lifecycleVisibilitySmoke.mjs
```

statically verifies the current schema/route/fetch options, lifecycle/operation vocabularies, fixed non-authority flags, read-only panel labeling, Fresh Conversation durability wording, absence of command handlers/raw HTML, stale generation/character guards on Home and Observation, wrapper wiring, and absence of selected private/control tokens.

The TypeScript parser itself performs stricter runtime exact-key/type/value validation than the static smoke alone.

## Fail-closed invariants

The exact current B1A fail-closed rules include:

1. non-loopback management access receives no lifecycle projection;
2. unknown character scope receives no projection;
3. invalid namespace query shape is rejected before the builder;
4. lifecycle route exposes GET only;
5. a known unavailable scope reports bounded unavailable state rather than inventing a store;
6. current-state index failure returns bounded unavailable visibility with no raw exception;
7. individual current-state resolution failure becomes bounded `unknown` item state;
8. memory enumeration is deterministic and capped at twenty items;
9. durable and queue directory visibility scans are capped at 4096 entries;
10. durable locators/paths remain internal even though they are used for grouping;
11. malformed queue records contribute bounded reasons but no state count;
12. lifecycle projection does not execute repair, replay, worker, scheduler, or mutation actions;
13. browser responses with extra/missing/wrong keys are rejected;
14. browser character/namespace mismatch rejects the whole projection;
15. one malformed nested memory/durable/queue/fresh object rejects the whole projection;
16. fixed read-only/privacy/control booleans must match exactly;
17. stale React requests are fenced by generation and active character before display;
18. Fresh Conversation semantics cannot flip durable-memory meaning without schema-contract change;
19. read-only panel source contains no command button/click handler or raw-HTML rendering;
20. lower lifecycle/queue/durable statuses remain observations and never become B1A apply authority.

## Relationship to Home conversation

`docs/contracts/ui/home-conversation.md` owns Home's real/preview browser conversation transport and New Conversation session reset behavior.

This lifecycle contract only explains the durable-memory meaning of that reset and displays runtime lifecycle state.

Neither contract creates durable transcript persistence or memory deletion on New Conversation.

## Relationship to memory mutation governance

Current lifecycle states such as `hidden`, `prepared`, `recovery_required`, or `corrupt` are projections of lower current-state/mutation authorities.

This contract does not define the mutation commands/transitions that lead to those states and must not be used as authorization for Forget, Correct, Pin, Held, restore, repair, purge, or cleanup operations.

## Relationship to durable-finalization and scheduler contracts

O1B/I1-G authorities own exact durable-finalization replay/finalization/isolation semantics.

O1C/B3/C2 own queue candidate, queue transition, and worker execution semantics.

O1D2/O1E/O2/O3 own scheduler policy/operations/service/process behavior.

B1A observes bounded aggregate status only. Its counts and labels are not a replacement correctness proof for those lower authorities.

## Source-retirement boundary

This transaction does not retire:

```text
docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md
```

Nor does it retire the projection implementation, app route, frontend API/panel/wrappers, smokes, completion evidence, Phase I-2 observation sources, or memory/scheduler source documents. Source retirement requires a separate bounded transaction with exact provenance, consumer repair, and migration disposition.
