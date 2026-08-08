---
relaylm_doc_type: contract
relaylm_authority: current_relayslp_job_admission_preflight_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp
relaylm_update_trigger:
  - RelaySLP job-admission schema, triggers, stages, or statuses change
  - source-lineage validation or correlation requirements change
  - persistence-policy or enqueue-gate admission behavior changes
  - public admission projection changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - durable queue publication, claim, retry, or terminal lifecycle
  - worker invocation or RelaySLP execution
  - memory formation or persistence semantics
  - RelaySOUL mutation or visible-response delivery
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase6a1_relayslp_job_admission_contract.md
  - ../../architecture/phase6a2_relayslp_response_handoff_contract.md
  - ../../architecture/phase6_async_relayslp_bounded_slice.md
  - ../../architecture/memory/formation.md
relaylm_verified_by:
  - ../../../scripts/relaylm_relaymem_slp_job_admission_smoke.py
  - ../../../scripts/relaylm_relaymem_slp_job_admission_bounded_metadata_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM/RelaySLP response-finalization and queue-admission maintainers
  - durable queue, worker, memory-formation, and recovery maintainers
  - privacy, diagnostics, security, and documentation reviewers
relaylm_authority_level: exact_contract
---
# RelaySLP Job Admission Contract

## Authority summary

This contract owns the exact current helper-only deferred-job admission preflight implemented by:

```text
relaylm/relaymem_slp_job_admission.py
```

The helper validates bounded job metadata and one content-free Primary source-lineage artifact. It returns a runtime-private result and a content-free projection.

It does **not** enqueue a durable job, invoke a worker, invoke RelaySLP, write memory, mutate RelaySOUL, or change visible-response delivery.

The central invariant is:

```text
admission preflight success
  != durable queue publication
  != worker execution
  != memory write
```

`eligible_for_enqueue` means structural eligibility for a later owning boundary only.

## Current schema identifiers

The exact current private-result schema is:

```text
relaymem.slp_job_admission_preflight.v0
```

The exact current public/content-free projection schema is:

```text
relaymem.slp_job_admission_projection.v0
```

The accepted upstream source-lineage schema is:

```text
relaymem.primary_source_lineage.v0
```

## Current trigger vocabulary

The current known trigger vocabulary is:

```text
turn_end
explicit_memory_request
session_end
communication_end
scheduled_consolidation
recovery_followup
lab_memory_operation
```

Only these triggers are currently supported by A1 admission:

```text
turn_end
explicit_memory_request
```

A known-but-unsupported trigger is retained as the normalized trigger value but adds:

```text
trigger_mode_unsupported
```

and therefore blocks admission.

An invalid trigger normalizes to no private token / `unknown` in projections and adds:

```text
trigger_mode_invalid
```

## Current processing-stage vocabulary

The current known stage vocabulary is:

```text
primary_formation
primary_write_preflight
secondary_consolidation
memory_operation
lint
```

Only these stages are currently supported:

```text
primary_formation
primary_write_preflight
```

A known-but-unsupported stage adds:

```text
processing_stage_unsupported
```

An invalid stage adds:

```text
processing_stage_invalid
```

Both cases block admission.

## Current source-event kinds

The exact current source-event vocabulary is:

```text
turn
session
communication
manual_import
```

An invalid value adds:

```text
source_event_kind_invalid
```

## Current runtime-terminal statuses

The exact accepted runtime-terminal vocabulary is:

```text
completed
succeeded
idle
blocked
failed
waiting_user
recovery_pending
unresolved_recovery
```

The statuses that block admission are:

```text
blocked
failed
waiting_user
recovery_pending
unresolved_recovery
```

A blocking runtime status appends a bounded reason in the exact form:

```text
runtime_status_blocks_admission:<status>
```

Invalid runtime status adds:

```text
runtime_terminal_status_invalid
```

## Current persistence-policy statuses

The exact current persistence-policy vocabulary is:

```text
allowed
free_to_update
review_required
explicit_approval_required
blocked
never_auto_promote
```

`review_required` creates a hold reason:

```text
persistence_policy_requires_review
```

The hard-blocking policy set is:

```text
explicit_approval_required
blocked
never_auto_promote
```

Those states append:

```text
persistence_policy_blocks_admission:<status>
```

Invalid policy values append:

```text
persistence_policy_status_invalid
```

## Current admission statuses

The exact result status vocabulary is:

```text
skipped
blocked
held
admitted_dry_run
eligible_for_enqueue
```

Status precedence is exact:

```text
if blocking reasons exist:
    blocked
elif hold reasons exist:
    held
elif source_count == 0:
    skipped
elif dry_run_only or not enqueue_enabled:
    admitted_dry_run
else:
    eligible_for_enqueue
```

Blocking reasons therefore take precedence over policy holds and zero-source skipping.

## Entry point

The current public helper is:

```text
build_relaymem_slp_job_admission_preflight(...)
```

Current defaults are conceptually:

```text
enabled = false
dry_run_only = true
enqueue_enabled = false
trigger_mode = turn_end
processing_stage = primary_formation
run_id = null
turn_index = null
session_id = null
namespace = default
source_event_kind = turn
source_lineage_artifact = null
source_count = 1
visible_response_finalized = false
runtime_terminal_status = completed
persistence_policy_status = allowed
```

The defaults are intentionally not a successful admission request. In particular, disabled state, missing required correlation, missing lineage, and an unfinalized `turn_end` response close the default invocation toward `blocked`.

## Exact boolean handling

These inputs require exact `bool` type:

```text
enabled
dry_run_only
enqueue_enabled
visible_response_finalized
```

Numeric `0`/`1`, strings, and other values are not accepted as boolean substitutes.

Malformed values normalize to false and append respectively:

```text
enabled_invalid
dry_run_only_invalid
enqueue_enabled_invalid
visible_response_finalized_invalid
```

## Feature gate

When normalized `enabled` is false, admission appends:

```text
feature_disabled
```

The current helper does not use `skipped` merely because the feature is disabled; the reason participates in normal blocking-status derivation.

## Token grammar and bound

Required token fields such as `run_id` and `namespace` must be strings that, after trimming:

- are non-empty;
- are at most 128 characters;
- contain only ASCII alphanumeric characters or one of:

```text
- _ . : /
```

Invalid required tokens normalize to null and append their field-specific reason, for example:

```text
run_id_invalid
namespace_invalid
```

`session_id` is optional; `None` is valid, otherwise it uses the same token rule and may append:

```text
session_id_invalid
```

## Turn-index contract

`turn_index` may be `None` or an exact non-negative integer.

Boolean values are not valid integer substitutes.

Malformed values normalize to null and append:

```text
turn_index_invalid
```

For `trigger_mode=turn_end`, an absent normalized turn index additionally appends:

```text
turn_index_required_for_turn_end
```

## Source-count contract

`source_count` must be an exact non-negative integer.

Boolean and non-integer input, or a negative integer, normalize to zero and append:

```text
source_count_invalid
```

The exact current maximum source count is:

```text
32
```

A larger integer is clamped to 32 and appends:

```text
source_count_limit_exceeded
```

The projection includes this fixed limit as `source_count_limit`.

## Turn-end invariants

For normalized `trigger_mode=turn_end`, all of these must hold for admission to remain unblocked:

```text
turn_index is present
source_event_kind == turn
visible_response_finalized == true
```

Violations append:

```text
turn_index_required_for_turn_end
turn_end_source_event_kind_mismatch
visible_response_not_finalized
```

This ensures the `turn_end` admission helper does not treat an unfinished visible response as ready for deferred job publication.

## Explicit-memory-request source kinds

For normalized `trigger_mode=explicit_memory_request`, the current accepted source-event kinds are:

```text
turn
manual_import
```

Other otherwise-known source-event kinds append:

```text
explicit_request_source_event_kind_unsupported
```

## Enqueue apply gate

When:

```text
dry_run_only == false
enqueue_enabled == false
```

the helper appends:

```text
enqueue_gate_disabled
```

This blocks `eligible_for_enqueue`.

Even when both gates permit an `eligible_for_enqueue` result, A1 still performs no queue I/O and creates no durable record.

## Source-lineage requirement

The lineage parser is called with:

```text
required = source_count > 0
```

When `source_count > 0`, a missing/non-mapping lineage blocks with:

```text
source_lineage_missing
```

When `source_count == 0` and the lineage artifact is absent, the parser returns an invalid/no-fingerprint private lineage state **without a blocking reason**. This allows the outer status to reach `skipped` when no other reason blocks.

Supplying malformed lineage metadata can still block even when the source count is zero.

## Exact lineage top-level fields

The source-lineage mapping may contain only:

```text
schema_version
content_free
content_included
raw_text_included
source_event_kind
namespace
valid
lineage_fingerprint
lineage_shape
blocked_reasons
```

Any additional top-level field returns an invalid lineage with:

```text
source_lineage_unexpected_field
```

The helper does not recursively traverse arbitrary caller metadata.

## Lineage schema and boolean invariants

The source lineage must have:

```text
schema_version = relaymem.primary_source_lineage.v0
content_free = true
content_included = false
raw_text_included = false
valid = true
```

Each boolean must have exact `bool` type and the exact required value.

Failures return one of:

```text
source_lineage_schema_mismatch
source_lineage_not_content_free
source_lineage_content_included
source_lineage_raw_text_included
source_lineage_invalid
```

Numeric boolean substitutes are rejected.

## Exact lineage-shape fields

`lineage_shape` must be a mapping with exactly these keys:

```text
source_event_id_present
run_id_present
session_id_present
turn_index_present
```

Every value must have exact boolean type.

Malformed container or values return:

```text
source_lineage_shape_invalid
```

A non-exact key set returns:

```text
source_lineage_shape_unexpected_field
```

## Upstream lineage blocked reasons

The upstream lineage `blocked_reasons` field must be an exact empty list.

Any non-list or non-empty value returns:

```text
source_lineage_blocked_reasons_invalid
```

A1 therefore does not accept an upstream lineage artifact that already carries unresolved blocked reasons.

## Lineage fingerprint

`lineage_fingerprint` must be an exact lowercase 64-character hexadecimal SHA-256 string.

Uppercase hex, wrong length, non-string values, or non-hex content return:

```text
source_lineage_fingerprint_invalid
```

The valid fingerprint may remain in the runtime-private result but is excluded from the public projection.

## Lineage namespace and event-kind matching

The lineage namespace uses the same bounded token rule as the outer namespace.

The lineage source-event kind must be in the exact current source-event vocabulary.

Validation reasons include:

```text
source_lineage_namespace_invalid
source_lineage_event_kind_invalid
source_lineage_namespace_mismatch
source_lineage_event_kind_mismatch
```

A valid outer/inner value pair must match exactly.

## Lineage identity-shape rule

Any source-event kind is accepted as having identity when:

```text
source_event_id_present == true
```

Otherwise the current shape rule is:

```text
turn
  -> turn_index_present == true
     AND (run_id_present == true OR session_id_present == true)

session
  -> run_id_present == true OR session_id_present == true

communication / manual_import
  -> no alternate shape is accepted without source_event_id_present
```

Failure appends:

```text
source_lineage_missing
```

The helper validates only presence booleans from the upstream content-free shape; it does not recursively inspect source bodies.

## Reason bound and de-duplication

Blocking and hold reason lists are de-duplicated in first-occurrence order.

The exact current maximum retained reason count is:

```text
32
```

The final `blocked_reasons` projection is the de-duplicated concatenation of blocking reasons followed by hold reasons, truncated to that limit.

## Retry classes

The exact current retry classification is:

```text
held
  -> policy_hold

admitted_dry_run / eligible_for_enqueue
  -> not_dispatched

skipped
  -> not_applicable

blocked with runtime_status_blocks_admission:failed
blocked with runtime_status_blocks_admission:recovery_pending
blocked with runtime_status_blocks_admission:unresolved_recovery
  -> retry_requires_recovery

other blocked state
  -> non_retryable
```

The retry class is diagnostic; A1 does not itself schedule a retry.

## Runtime-private result shape

The current private result contains:

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

The fixed current safety/effect fields are:

```text
helper_only = true
diagnostics_only = true
read_only = true
queue_io_performed = false
enqueued = false
worker_invoked = false
invokes_slp = false
writes_memory = false
mutates_soul = false
changes_visible_response = false
dispatch_idempotency_key = ""
memory_write_idempotency_key = ""
```

`enqueue_eligible` is exactly:

```text
admission_status == eligible_for_enqueue
```

## Projection shape

The current content-free projection contains:

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

The exact fixed projection safety fields are:

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

## Correlation projection

The projection exposes only presence booleans:

```text
run_id_present
turn_index_present
session_id_present
namespace_present
```

It does not expose the runtime-private correlation values themselves.

## Content-free omissions

The public projection excludes:

- `run_id`, `session_id`, and exact turn index values;
- namespace value;
- lineage fingerprint;
- source-event IDs or other runtime-private references;
- dispatch idempotency key;
- memory-write idempotency key;
- raw text, messages, prompts, snippets, page content, or patches;
- candidate arrays;
- filesystem paths;
- RelaySOUL content.

The helper can communicate bounded admission state without becoming another content-bearing diagnostic surface.

## Idempotency ownership

A1 deliberately creates neither idempotency layer.

```text
dispatch idempotency
  -> later durable queue/orchestration authority

memory-write idempotency
  -> RelayMEM write-preflight/persistence authority
```

The private result keeps both key strings empty, and the public projection explicitly reports that neither key is included.

## Downstream A2 boundary

Phase 6-A2 may consume the exact A1 private result after response finalization and construct a runtime-private handoff/enqueue candidate under its own contract.

A1 itself does not claim A2 behavior.

In particular, A1 does not:

- create a response-finalization handoff record;
- publish to a durable queue;
- claim a queue record;
- start a worker;
- execute memory formation;
- persist a memory candidate.

## Failure direction

Malformed or unsupported input closes toward `blocked`, `held`, or `skipped`; it never widens into queue/execution authority.

Key examples:

```text
feature disabled
  -> blocked

turn_end before visible response finalization
  -> blocked

unsupported known trigger/stage
  -> blocked

invalid lineage / correlation / source identity
  -> blocked

review_required policy with no other blocking reason
  -> held

no sources with otherwise valid/gated request
  -> skipped

dry-run accepted request
  -> admitted_dry_run

apply gates accepted
  -> eligible_for_enqueue
  -> still no queue I/O
```

## Stable invariants

- A1 is helper-only, diagnostics-only, and read-only.
- The current private/projection schemas are fixed v0 identifiers.
- Only `turn_end` and `explicit_memory_request` are currently supported triggers.
- Only `primary_formation` and `primary_write_preflight` are currently supported stages.
- `turn_end` requires a turn source, turn index, and finalized visible response.
- Source count is bounded to 32.
- Tokens are bounded to 128 ASCII-safe characters.
- The upstream lineage mapping and lineage-shape key sets are fixed.
- Lineage booleans require exact boolean types.
- The lineage fingerprint is lowercase SHA-256 hex and never enters the public projection.
- A1 retains at most 32 de-duplicated reason IDs.
- `review_required` is a policy hold; explicit approval required/blocked/never-auto-promote are blocking policies.
- Non-dry-run admission requires the enqueue gate, but successful eligibility still performs no enqueue.
- `eligible_for_enqueue` is structural eligibility only.
- A1 creates no dispatch or memory-write idempotency key.
- Public projection is content-free and exposes correlation presence, not private values.
- A1 never invokes a worker/SLP, writes memory, mutates SOUL, or changes visible-response delivery.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- A2 response-finalization handoff details;
- durable queue record schema;
- claim/lease/retry/terminal lifecycle;
- worker execution;
- memory candidate or write-preflight semantics;
- RelaySOUL mutation;
- scheduler policy;
- repository-level sequencing;
- source retirement.

## Related architecture and transitional source

- [Phase 6-A1 transitional contract](../../architecture/phase6a1_relayslp_job_admission_contract.md)
- [Phase 6-A2 response handoff](../../architecture/phase6a2_relayslp_response_handoff_contract.md)
- [Phase 6 bounded asynchronous RelaySLP slice](../../architecture/phase6_async_relayslp_bounded_slice.md)
- [Memory Formation Architecture](../../architecture/memory/formation.md)
