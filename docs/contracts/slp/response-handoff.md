---
relaylm_doc_type: contract
relaylm_authority: current_relayslp_response_finalization_handoff_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - RelaySLP response-handoff result, candidate, or projection schema changes
  - A1 private-result/projection compatibility requirements change
  - response-finalization or dry-run candidate gates change
  - response-handoff PipelineNodeResult mapping changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - durable queue persistence, dispatch identity, claim, retry, or terminal lifecycle
  - worker invocation or RelaySLP execution
  - memory formation or persistence apply
  - RelaySOUL mutation or visible-response delivery
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - job-admission.md
  - durable-queue.md
  - ../../architecture/memory/formation.md
relaylm_verified_by:
  - ../../../scripts/relaylm_relaymem_slp_response_handoff_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM/RelaySLP response-finalization and dispatch-preflight maintainers
  - durable queue, worker, memory-formation, and recovery maintainers
  - privacy, diagnostics, security, and documentation reviewers
relaylm_authority_level: exact_contract
---
# RelaySLP Response-Finalization Handoff Contract

## Authority summary

This contract owns the exact current Phase 6-A2 helper-only response-finalization handoff implemented by:

```text
relaylm/relaymem_slp_response_handoff.py
```

A2 consumes one exact A1 job-admission private result, revalidates its embedded content-free projection, and may produce one runtime-private metadata-only enqueue candidate after a finalized `turn_end` response.

The current boundary is deliberately narrower than durable dispatch:

```text
A1 exact admission result
  -> A2 exact compatibility validation
  -> response-finalization + A2 dry-run gate
  -> optional runtime-private enqueue candidate
  -> content-free node/projection diagnostics
```

A2 performs no queue I/O, no durable enqueue, no dispatch-idempotency allocation, no claim/lease, no worker invocation, no RelaySLP execution, no memory write, no RelaySOUL mutation, and no visible-response rewrite.

## Current schema identifiers

The exact current upstream A1 schemas are:

```text
relaymem.slp_job_admission_preflight.v0
relaymem.slp_job_admission_projection.v0
```

The exact current A2 schemas are:

```text
relaymem.slp_response_handoff.v0
relaymem.slp_enqueue_candidate.v0
relaymem.slp_response_handoff_projection.v0
```

A2 does not accept schema aliases or partial compatible shapes.

## Current A2 status vocabulary

`RelayMEMSLPResponseHandoffStatus` is exactly:

```text
disabled
invalid_input
blocked
held
skipped
dry_run_candidate
```

There is no current non-dry-run candidate status and no durable-enqueued status in A2.

## Current accepted A1 status vocabulary

A2 validates the full current A1 status vocabulary:

```text
skipped
blocked
held
admitted_dry_run
eligible_for_enqueue
```

Only these A1 statuses may proceed toward candidate creation:

```text
admitted_dry_run
eligible_for_enqueue
```

`blocked`, `held`, and `skipped` are propagated as bounded A2 outcomes after A2's own dry-run/finalization gates are satisfied.

## Current A2 gate inputs

`build_relaymem_slp_response_finalization_handoff(...)` accepts:

```text
admission_result
enabled = false
dry_run_only = true
response_finalized = false
```

The three A2 control values require exact boolean types.

Malformed control values normalize to false and return `invalid_input` with bounded reasons:

```text
enabled_invalid
dry_run_only_invalid
response_finalized_invalid
```

Control validation happens before source validation.

## Disabled boundary

After valid exact booleans, `enabled=false` returns:

```text
status = disabled
candidate = null
source_projection = null
blocked_reasons = ()
```

A2 does not inspect or validate the supplied A1 object on this disabled path.

Disabled therefore remains an outer feature gate rather than a claim that the source object was valid.

## Exact A1 private-result shape

When A2 is enabled, the source must be a mapping with **exactly** the current A1 private-result key set:

```text
schema_version
helper_only
diagnostics_only
read_only
enabled
dry_run_only
enqueue_enabled
admission_status
trigger_mode
processing_stage
source_event_kind
run_id
turn_index
session_id
namespace
source_count
source_reference_valid
source_lineage_fingerprint
visible_response_finalized
runtime_terminal_status
persistence_policy_status
retry_class
blocked_reasons
enqueue_eligible
queue_io_performed
enqueued
worker_invoked
invokes_slp
writes_memory
mutates_soul
changes_visible_response
dispatch_idempotency_key
memory_write_idempotency_key
projection
```

A non-mapping source returns:

```text
invalid_admission_result
```

Any missing or extra key returns:

```text
admission_result_shape_mismatch
```

The exact source schema must be:

```text
relaymem.slp_job_admission_preflight.v0
```

or A2 returns:

```text
admission_schema_mismatch
```

## A1 fixed helper flags

The source fields:

```text
helper_only
diagnostics_only
read_only
```

must each be exactly `true`.

A mismatch returns the corresponding bounded reason:

```text
admission_helper_only_invalid
admission_diagnostics_only_invalid
admission_read_only_invalid
```

## A1 exact boolean fields

A2 requires exact boolean types for:

```text
enabled
dry_run_only
enqueue_enabled
source_reference_valid
visible_response_finalized
enqueue_eligible
queue_io_performed
enqueued
worker_invoked
invokes_slp
writes_memory
mutates_soul
changes_visible_response
```

A non-boolean field fails the source-shape validation with:

```text
admission_<field>_invalid
```

Numeric `0`/`1` are not accepted as boolean substitutes.

## A1 token fields

The source token fields validated by A2 are:

```text
trigger_mode
processing_stage
source_event_kind
runtime_terminal_status
persistence_policy_status
retry_class
```

Each must be an exact string:

- already trimmed;
- non-empty;
- at most 128 characters;
- containing only ASCII alphanumeric characters or `-_.:/`.

A2 does not trim a source token into acceptance. Whitespace mismatch fails closed.

## A1 bounded numeric/correlation fields

`source_count` must be an exact integer in:

```text
0..32
```

or source validation returns:

```text
admission_source_count_invalid
```

`turn_index` may be null or an exact non-negative integer. Invalid values return:

```text
admission_turn_index_invalid
```

`run_id`, `session_id`, and `namespace` may be null on a structurally valid non-accepted A1 result; when present they must pass the same exact bounded token grammar.

## A1 lineage fingerprint shape

The A1 private `source_lineage_fingerprint` may be either:

```text
""
```

or an exact lowercase 64-character hexadecimal SHA-256 token.

Any other non-empty value returns:

```text
admission_source_lineage_fingerprint_invalid
```

Accepted-source validation later requires a real non-empty valid fingerprint.

## A1 reason-list validation

The private `blocked_reasons` field must be an exact list with at most 32 elements.

Each element must be an exact bounded token using the 128-character ASCII-safe token grammar.

Malformed shape/size/items fail with the appropriate bounded reason:

```text
blocked_reasons_invalid
blocked_reasons_limit_exceeded
blocked_reasons_item_invalid
```

A2 does not recursively parse arbitrary nested reason payloads.

## Prior-side-effect rejection

A2 refuses any source claiming that a lower execution boundary has already run.

The source must keep:

```text
queue_io_performed = false
enqueued = false
worker_invoked = false
invokes_slp = false
writes_memory = false
mutates_soul = false
changes_visible_response = false
```

Violations return fixed bounded reasons such as:

```text
source_queue_io_already_performed
source_already_enqueued
source_worker_invoked_invalid
source_invokes_slp_invalid
source_writes_memory_invalid
source_mutates_soul_invalid
source_changes_visible_response_invalid
```

A2 therefore does not accept a source object that has crossed into queue/worker/mutation effects and pretend it is still a pre-dispatch handoff.

## Idempotency-key rejection

The A1 source must contain exact string values for both:

```text
dispatch_idempotency_key
memory_write_idempotency_key
```

and both must equal the empty string.

Any type or content mismatch returns:

```text
dispatch_idempotency_key_not_allowed
memory_write_idempotency_key_not_allowed
```

A2 does not allocate either key.

Dispatch idempotency remains a later Phase 6 queue/orchestration authority; memory-write idempotency remains RelayMEM write/persistence authority.

## Exact A1 projection shape

The embedded A1 `projection` must be a mapping with exactly:

```text
schema_version
diagnostics_only
content_free
content_included
raw_text_included
enabled
dry_run_only
enqueue_enabled
admission_status
trigger_mode
processing_stage
source_event_kind
source_count
source_count_limit
correlation
source_reference_valid
visible_response_finalized
runtime_terminal_status
persistence_policy_status
retry_class
blocked_reasons
runtime_private_reference_included
lineage_fingerprint_included
dispatch_idempotency_key_included
memory_write_idempotency_key_included
```

Missing/extra keys return:

```text
source_projection_shape_mismatch
```

The exact schema must be:

```text
relaymem.slp_job_admission_projection.v0
```

or A2 returns:

```text
source_projection_schema_mismatch
```

## A1 projection fixed safety flags

The projection must have exact booleans with these exact values:

```text
diagnostics_only = true
content_free = true
content_included = false
raw_text_included = false
runtime_private_reference_included = false
lineage_fingerprint_included = false
dispatch_idempotency_key_included = false
memory_write_idempotency_key_included = false
```

Any mismatch fails source validation.

The projection therefore cannot be replaced by a content-bearing or identity-bearing lookalike.

## A1 projection variable booleans and enums

The projection fields:

```text
enabled
dry_run_only
enqueue_enabled
source_reference_valid
visible_response_finalized
```

must be exact booleans.

Its `admission_status` must be one of the exact current A1 statuses.

Its token fields use the same exact bounded token grammar as the A1 private result.

`source_count` must be an exact integer from 0 through 32.

`source_count_limit` must be the exact integer:

```text
32
```

## Exact projection correlation shape

The A1 projection `correlation` must be a mapping with exactly:

```text
run_id_present
turn_index_present
session_id_present
namespace_present
```

Every value must have exact boolean type.

Any shape/type mismatch fails source validation.

## Private/projection equality

A2 compares the embedded A1 projection against the private result for all shared fields:

```text
enabled
dry_run_only
enqueue_enabled
admission_status
trigger_mode
processing_stage
source_event_kind
source_count
source_reference_valid
visible_response_finalized
runtime_terminal_status
persistence_policy_status
retry_class
blocked_reasons
```

A mismatch returns:

```text
source_projection_mismatch:<field>
```

The expected correlation map is derived from whether the private values are null:

```text
run_id_present = run_id is not null
turn_index_present = turn_index is not null
session_id_present = session_id is not null
namespace_present = namespace is not null
```

Any mismatch returns:

```text
source_projection_correlation_mismatch
```

This prevents a caller from pairing one private source with a different public admission projection.

## A2 dry-run/finalization gates

After successful source-shape/projection validation, A2 applies its own gates **before** propagating A1 blocked/held/skipped status.

Current A2 supports only:

```text
dry_run_only = true
response_finalized = true
```

When `dry_run_only=false`, A2 appends:

```text
non_dry_run_not_supported
```

When `response_finalized=false`, A2 appends:

```text
response_not_finalized
```

Any A2 gate error returns:

```text
status = blocked
candidate = null
```

while preserving the validated source status and source projection.

## Propagation of non-candidate A1 statuses

When A2 gates pass and A1 status is:

```text
held
skipped
blocked
```

A2 returns the same status, creates no candidate, preserves the validated content-free source projection, and appends:

```text
source_admission_held
source_admission_skipped
source_admission_blocked
```

respectively after the bounded A1 source reasons.

The final A2 reason tuple is de-duplicated and bounded to 32 entries.

## Accepted-source semantic compatibility

For A1 status `admitted_dry_run` or `eligible_for_enqueue`, A2 applies the additional current response-handoff contract.

The source must satisfy all of:

```text
source.enabled = true
trigger_mode = turn_end
processing_stage in {primary_formation, primary_write_preflight}
source_event_kind = turn
run_id = valid required bounded token
session_id = null or valid bounded token
namespace = valid required bounded token
turn_index = exact non-negative int
1 <= source_count <= 32
source_reference_valid = true
source_lineage_fingerprint = valid lowercase SHA-256
visible_response_finalized = true
runtime_terminal_status in {completed, succeeded, idle}
persistence_policy_status in {allowed, free_to_update}
retry_class = not_dispatched
blocked_reasons = []
```

Failure returns A2 `blocked` with bounded compatibility reasons rather than constructing a candidate.

## Response-handoff trigger boundary

A1 may admit `explicit_memory_request`, but A2 is a **response-finalization** handoff and currently accepts only:

```text
trigger_mode = turn_end
```

A different trigger returns:

```text
trigger_not_supported_for_response_handoff
```

A2 does not reinterpret an explicit memory request as a turn-end handoff.

## Source gate consistency: admitted dry run

For source status:

```text
admitted_dry_run
```

A2 requires:

```text
source.dry_run_only = true
source.enqueue_eligible = false
```

Otherwise it adds:

```text
dry_run_source_gate_mismatch
```

The source `enqueue_enabled` value may be true or false; A1 can still be dry-run when its own `dry_run_only` gate is true.

## Source gate consistency: eligible for enqueue

For source status:

```text
eligible_for_enqueue
```

A2 requires:

```text
source.dry_run_only = false
source.enqueue_enabled = true
source.enqueue_eligible = true
```

Violations add:

```text
enqueue_source_dry_run_mismatch
enqueue_source_gate_mismatch
```

Even an A1 `eligible_for_enqueue` result is consumed by A2 only to produce a **dry-run A2 candidate** because A2's own `dry_run_only` must remain true.

## Enqueue candidate shape

`RelayMEMSLPEnqueueCandidate` carries runtime-private orchestration metadata:

```text
trigger_mode
processing_stage
source_event_kind
run_id
turn_index
session_id
namespace
source_count
source_lineage_fingerprint
source_admission_status
runtime_terminal_status
persistence_policy_status
```

`to_runtime_dict()` emits these fields plus the exact candidate schema and fixed execution metadata.

The exact schema is:

```text
relaymem.slp_enqueue_candidate.v0
```

The exact candidate kind is:

```text
relayslp_deferred_job
```

## Candidate fixed safety fields

Every current candidate runtime dictionary fixes:

```text
response_finalized = true
dry_run_only = true
enqueue_requested = false
queue_io_performed = false
enqueued = false
worker_invoked = false
invokes_slp = false
writes_memory = false
mutates_soul = false
changes_visible_response = false
dispatch_idempotency_key = ""
memory_write_idempotency_key = ""
content_free = true
runtime_private = true
```

A2 candidate creation is therefore metadata handoff, not queue/apply behavior.

## Source projection retained by A2

`RelayMEMSLPSourceProjection` retains only content-free source metadata:

```text
trigger_mode
processing_stage
source_event_kind
source_count
run_id_present
turn_index_present
session_id_present
namespace_present
```

Its log dictionary nests the four presence booleans under `correlation` and exposes none of the private identifier values.

This projection can be preserved for blocked/held/skipped diagnostics without producing an enqueue candidate.

## A2 result shape

`RelayMEMSLPResponseHandoffResult` carries:

```text
status
enabled
dry_run_only
response_finalized
source_admission_status
source_projection
candidate
blocked_reasons
```

Derived properties are:

```text
candidate_count = 1 if candidate exists else 0
candidate_created = candidate exists
```

The current helper creates at most one candidate per call.

## Runtime result dictionary

`to_runtime_dict()` emits:

```text
schema_version
helper_only
diagnostics_only
read_only
enabled
dry_run_only
response_finalized
status
source_admission_status
source_projection
candidate_count
candidate_created
candidate
queue_io_performed
enqueued
worker_invoked
invokes_slp
writes_memory
mutates_soul
changes_visible_response
blocked_reasons
```

The fixed effect flags are always false:

```text
queue_io_performed
enqueued
worker_invoked
invokes_slp
writes_memory
mutates_soul
changes_visible_response
```

## Content-free public projection

`to_log_dict()` uses schema:

```text
relaymem.slp_response_handoff_projection.v0
```

and emits:

```text
schema_version
diagnostics_only
content_free
content_included
raw_text_included
enabled
dry_run_only
response_finalized
status
source_admission_status
candidate_count
candidate_created
trigger_mode
processing_stage
source_event_kind
source_count
correlation
queue_io_performed
enqueued
worker_invoked
dispatch_idempotency_key_included
memory_write_idempotency_key_included
source_lineage_fingerprint_included
runtime_private_candidate_included
blocked_reasons
```

When no validated source projection exists, source token fields are null, source count is zero, and all correlation-presence booleans are false.

## Projection fixed safety fields

The public A2 projection fixes:

```text
diagnostics_only = true
content_free = true
content_included = false
raw_text_included = false
queue_io_performed = false
enqueued = false
worker_invoked = false
dispatch_idempotency_key_included = false
memory_write_idempotency_key_included = false
source_lineage_fingerprint_included = false
runtime_private_candidate_included = false
```

It therefore omits the candidate body, exact correlation identities, namespace value, lineage fingerprint, and both idempotency domains.

## A2 successful candidate outcome

When all current gates and accepted-source checks pass, A2 returns exactly:

```text
status = dry_run_candidate
enabled = true
dry_run_only = true
response_finalized = true
candidate_count = 1
candidate_created = true
blocked_reasons = ()
```

The candidate's `source_admission_status` remains whichever accepted A1 status was validated.

No queue operation follows automatically from this return.

## PipelineNodeResult mapping

`build_relaymem_slp_response_handoff_node_result(...)` uses node name:

```text
relaymem_slp_response_handoff
```

and `decision=result.status`.

Current node-status mapping is:

```text
invalid_input -> failed
blocked       -> blocked
disabled      -> skipped
held          -> skipped
skipped       -> skipped
dry_run_candidate -> diagnostic_only
```

The presence of a dry-run candidate therefore does not produce an `applied` node status.

## Node artifact projection

The node result includes one content-free artifact projection:

```text
artifact_name = relaymem_slp_enqueue_candidate
schema_version = relaymem.slp_enqueue_candidate.v0
present = result.candidate_created
content_free = true
runtime_private = true
candidate_omitted = true
queue_io_performed = false
enqueued = false
dispatch_idempotency_key_included = false
memory_write_idempotency_key_included = false
```

The runtime-private candidate body is intentionally not copied into generic diagnostics.

## Content boundary

A2 candidate/private state may contain bounded correlation and lineage references needed by a later in-process dispatch boundary.

Generic projection/node diagnostics do not expose:

- raw user/model text;
- finalized visible-response text;
- prompts or snippets;
- memory page content or patch values;
- filesystem paths;
- RelaySOUL content;
- run/session identifier values;
- namespace value;
- lineage fingerprint;
- runtime-private candidate body;
- dispatch or memory-write idempotency keys.

## B1/B2 ownership boundary

Phase 6-B1 is the first implemented downstream consumer that may derive Phase 6-owned deterministic dispatch/job identities from the exact A2 in-process candidate under its own contract.

Phase 6-B2 owns atomic durable enqueue.

A2 does not:

```text
allocate dispatch identity
serialize a durable queue record
open or write a queue root
claim/lease work
retry work
invoke a worker
write memory
```

A later consumer must revalidate its own exact contract rather than treating A2 `dry_run_candidate` as already enqueued work.

## Failure direction

A2 fails toward less downstream authority:

```text
invalid A2 booleans
  -> invalid_input

A2 disabled
  -> disabled without source inspection

malformed/inconsistent A1 private result or projection
  -> invalid_input

A2 non-dry-run or response not finalized
  -> blocked

validated source held/skipped/blocked
  -> corresponding A2 status, no candidate

accepted-status source fails current turn/finalization/lineage/policy/gate checks
  -> blocked

all gates pass
  -> dry_run_candidate
  -> still no queue I/O
```

A2 never broadens a malformed source into durable work.

## Stable invariants

- A2 is helper-only, diagnostics-only, and read-only.
- A2 accepts only the exact A1 private-result and projection shapes/schemas.
- A2 revalidates private/projection equality and correlation-presence consistency.
- Prior queue, worker, SLP, memory, SOUL, visible-response, or idempotency-key effects are rejected.
- A2 currently supports only dry-run handoff candidate creation.
- A2 candidate creation additionally requires a finalized response.
- A2 response handoff accepts only finalized `turn_end` sources.
- Accepted source stages are only `primary_formation` and `primary_write_preflight`.
- Accepted runtime terminal states are `completed`, `succeeded`, and `idle`.
- Accepted persistence policies are `allowed` and `free_to_update`.
- Accepted sources require 1..32 sources and a valid content-free lineage reference/fingerprint.
- A1 `admitted_dry_run` and `eligible_for_enqueue` have distinct source-gate consistency checks.
- A2 creates at most one runtime-private metadata-only candidate.
- Candidate and public diagnostics record no queue I/O and no enqueue.
- A2 creates neither dispatch nor memory-write idempotency key.
- `dry_run_candidate` maps to a diagnostic-only PipelineNodeResult, not applied.
- Public projection omits runtime-private candidate/correlation/fingerprint content.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- B1 dispatch/job identity derivation;
- B2 durable queue persistence;
- B3 claim/lease/retry/terminal lifecycle;
- worker execution;
- memory formation or persistence semantics;
- RelaySOUL mutation;
- non-dry-run A2 candidate publication;
- source retirement;
- repository-level sequencing.

## Related architecture and contracts

- [RelaySLP Job Admission Contract](job-admission.md)
- [RelaySLP Durable Queue Contract](durable-queue.md)
