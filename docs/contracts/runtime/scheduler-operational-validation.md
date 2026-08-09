---
relaylm_doc_type: contract
relaylm_authority: current_relaymem_slp_scheduler_operational_validation_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - SchedulerOperationalValidationResult exact fields or accepted statuses change
  - O1F validation result/projection schema identifiers or hard bounds change
  - queue-root, sealed durable-finalization, or source/queue correlation validation semantics change
  - public leakage or bounded-projection validation semantics change
  - O1F wrapper input validation or one-invocation behavior changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - O1A/O1D1 scheduler round, lane outcome, or replay-before-queue semantics
  - O1D2 fairness, retry-window, pacing, backoff, or jitter semantics
  - O1E cancellation, stale-recovery orchestration, or signal-adapter authority
  - B3 queue transition, claim, lease, retry, stale-recovery, or terminal semantics
  - I1-GC/I1-GD durable-finalization mutation, replay, retention, or cleanup semantics
  - C2 worker execution semantics
  - O2/O3 service supervision, polling, daemon, or always-on lifecycle
  - general RelayRUN resource scheduling
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o1f_operational_validation.md
  - ../../architecture/o1e_scheduler_operational_controls.md
  - ../../architecture/o2_supervised_scheduler_service.md
  - ../../architecture/o3_always_on_local_scheduler.md
relaylm_related_contracts:
  - scheduler-round.md
  - scheduler-policy.md
  - scheduler-operational-controls.md
  - ../relayrun-checkpoint-and-recovery.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o1f_operational_validation_smoke.py
  - ../../../scripts/relaylm_o1f_operational_validation_corruption_smoke.py
  - ../../../scripts/relaylm_o1f_operational_validation_concurrency_smoke.py
  - ../../../scripts/relaylm_o1f_operational_validation_saturation_smoke.py
  - ../../../scripts/relaylm_o1f_operational_validation_restart_smoke.py
  - ../../../scripts/relaylm_o1f_operational_validation_security_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM SLP scheduler validation and operations maintainers
  - queue, durable-finalization, recovery, security, and observability reviewers
  - O2/O3 service maintainers consuming the validated lower boundary
relaylm_authority_level: exact_contract
---
# Runtime Scheduler Operational Validation Contract

## Authority summary

This contract owns the exact current **O1F validation-only boundary** implemented by:

```text
relaylm/relaymem_slp_scheduler_operational_validation.py
```

O1F validates the already-owned O1E/O1D2/O1D1, B3, and sealed I1-G operational boundaries. It does not become a scheduler, queue owner, worker, recovery owner, durable-finalization writer, service, daemon, or mutation authority.

The current validation shape is bounded to explicit caller invocation:

```text
caller
  -> exact O1F input checks
  -> at most one existing O1E invocation when using the wrapper helper
  -> inspect only bounded public result/projection state
  -> optional read-only bounded queue-root inspection
  -> optional one sealed durable-finalization locator read
  -> optional source/queue correlation equality check
  -> leakage/boundedness validation
  -> content-free O1F projection
  -> return
```

There is no O1F polling loop, sleep, timer, background task, retry loop, daemon, service supervision, worker pool, or new queue lifecycle transition.

## Current implementation anchors

The exact implementation owner is:

```text
relaylm/relaymem_slp_scheduler_operational_validation.py
```

The lower operational-control boundary remains owned by:

```text
relaylm/relaymem_slp_scheduler_operations.py
```

The queue storage and transition authorities remain separately owned by their B3 modules. Durable-finalization reading remains owned by the existing sealed store implementation.

The current implementation handoff remains a transitional source:

```text
docs/architecture/o1f_operational_validation.md
```

This transaction does not retire or move that source.

## Current schema identifiers

The exact current O1F schemas are:

```text
VALIDATION_RESULT_SCHEMA     = relaylm.local_scheduler_operational_validation_result.v0
VALIDATION_PROJECTION_SCHEMA = relaylm.local_scheduler_operational_validation_projection.v0
```

The exact current hard bounds are:

```text
MAX_VALIDATION_REASON_IDS       = 16
MAX_VALIDATION_CATEGORIES       = 16
MAX_VALIDATION_SCAN_ENTRIES     = 4096
MAX_VALIDATION_PROJECTION_BYTES = 8192
```

Every bounded O1F reason/category token must match:

```regex
^[a-z][a-z0-9_]{0,63}$
```

## Validation status vocabulary

The exact constructor-accepted current validation statuses are:

```text
validated
invalid_input
unsafe
operation_unsafe
content_leakage_blocked
boundedness_failed
```

These are validation outcomes only. They do not replace O1E operational statuses, O1D2 policy statuses, scheduler-round statuses, B3 queue transition statuses, or durable-finalization reader statuses.

## Forbidden public token set

`validate_content_free_projection(...)` currently treats the following exact token fragments as forbidden in public/repr validation payloads:

```text
O1F_PRIVATE_CONTENT_CANARY
O1F_RAW_EXCEPTION_CANARY
O1F_PRIVATE_PATH_CANARY
slp-job-v0:
slp-dispatch-v0:
lease-v0-
protected_source
visible_response
backend_text
memory_body
raw_exception
private_delegate_result
```

Matching is case-insensitive after JSON serialization of the supplied values.

This token set is a validation canary/leakage fence. It is not a complete classification of every sensitive value in RelayLM and does not authorize emission of values merely because they are absent from this tuple.

## SchedulerOperationalValidationResult shape

`SchedulerOperationalValidationResult` is immutable and currently contains exactly these responsibility-level fields:

```text
status
categories
operation_status
stale_recovery_status
scheduler_policy_status
scheduler_round_invoked
scanned_entry_count
checked_candidate_count
unsafe
bounded_reason_ids
operation_result
schema_version
```

`schema_version` is fixed to:

```text
relaylm.local_scheduler_operational_validation_result.v0
```

`operation_result` is a private nested `SchedulerOperationalControlsResult` used only for local validation flow. It is excluded from repr and equality and is not projected directly.

## Result constructor exactness

Construction requires:

- `status` to be one of the six exact validation statuses;
- `scheduler_round_invoked` to be exact `bool`;
- `unsafe` to be exact `bool`;
- `scanned_entry_count` to be exact `int` in `0..4096`;
- `checked_candidate_count` to be exact `int` in `0..4096`;
- `operation_result` to be null or exact `SchedulerOperationalControlsResult`;
- `categories` to normalize through the bounded reason-token normalizer with maximum sixteen entries;
- `bounded_reason_ids` to normalize through the same token grammar with maximum sixteen entries.

Current constructor errors include:

```text
scheduler_operational_validation_status_invalid
scheduler_operational_validation_bool_invalid
scheduler_operational_validation_count_invalid
exact_scheduler_operational_result_required
```

Boolean values do not satisfy the exact-integer count requirement.

## Result repr boundary

The current repr includes only:

```text
status
operation_status
unsafe
private_values_omitted=True
```

It does not include the nested O1E result, queue records, locators, filesystem paths, claim/lease identity, memory content, backend text, protected source, or raw exceptions.

## Public projection

The exact current O1F projection contains:

```text
schema_version
status
operation_status
stale_recovery_status
scheduler_policy_status
scheduler_round_invoked
unsafe
scanned_entry_count
checked_candidate_count
categories
bounded_reason_ids
```

The projection schema is:

```text
relaylm.local_scheduler_operational_validation_projection.v0
```

The projection intentionally omits:

- nested `operation_result`;
- nested scheduler-policy or scheduler-round objects;
- queue records and record snapshots;
- job IDs and dispatch IDs;
- claim owners, claim generation, lease tokens, and exact lease timestamps;
- queue/sealed roots, paths, filenames, and file descriptors;
- durable-finalization record bodies;
- protected source or memory content;
- backend text or visible-response bodies;
- raw exceptions.

## Validation wrapper entry point

The current wrapper is:

```text
validate_scheduler_operational_boundary_once(
    *,
    config,
    registry=None,
    now=None,
    policy_state=None,
    cancellation=None,
    fault_injector=None,
)
```

It runs at most one already-owned O1E invocation and then validates only the returned public boundary.

O1F does not reinterpret O1E cancellation, stale recovery, scheduler invocation, or lower mutation semantics.

## Exact wrapper input checks

The current O1F wrapper requires:

```text
type(config) is RelayLMConfig
registry is null OR type(registry) is RelayMEMSLPPrimaryWorkerSourceRegistry
now is null OR exact timezone-aware datetime
policy_state is null OR type(policy_state) is SchedulerPolicyState
fault_injector is null OR callable
```

Current fail-closed reasons are:

```text
operational_validation_config_invalid
operational_validation_registry_invalid
operational_validation_now_invalid
operational_validation_policy_state_invalid
operational_validation_fault_injector_invalid
```

Invalid wrapper input returns:

```text
status = invalid_input
unsafe = true
```

The cancellation argument is deliberately passed through to O1E, which remains the cancellation-token/probe authority.

## O1E invocation failure handling

If the O1E call raises, O1F returns:

```text
status = unsafe
reason = operational_validation_invocation_failed
unsafe = true
```

If the returned object is not exact `SchedulerOperationalControlsResult`, O1F returns:

```text
status = unsafe
reason = operational_validation_operation_result_invalid
unsafe = true
```

O1F does not attempt a second invocation, retry, fallback scheduler, or alternative service path.

## Public leakage validation after O1E

For a valid exact O1E result, O1F obtains:

```text
operation.projection()
repr(operation)
```

and checks both through `validate_content_free_projection(...)`.

Any leakage reason returns:

```text
status = content_leakage_blocked
categories = [leakage]
unsafe = true
```

The private O1E result remains attached only as the private `operation_result` field and is not projected.

## Public boundedness validation after O1E

After leakage validation, O1F calls:

```text
validate_bounded_public_projection(operation.projection())
```

Any boundedness failure returns:

```text
status = boundedness_failed
categories = [boundedness]
unsafe = true
```

O1F therefore does not accept a semantically successful O1E operation whose public projection violates the O1F boundedness contract.

## Lower unsafe propagation

If the lower exact O1E result has:

```text
operation.unsafe == true
```

then O1F returns:

```text
status = operation_unsafe
categories = [operation]
unsafe = true
```

Reasons are the lower bounded O1E reasons when present, otherwise:

```text
scheduler_operation_unsafe
```

This is validation propagation, not a new definition of the lower unsafe state.

## Successful operational-boundary validation

When the lower result is exact, its public projection is content-free and bounded, and `operation.unsafe` is false, O1F returns:

```text
status = validated
categories = [operation]
reason = scheduler_operational_boundary_validated
unsafe = false
```

The lower `operation_status`, `stale_recovery_status`, `scheduler_policy_status`, and `scheduler_round_invoked` values are copied only as bounded public summary fields.

## Cancellation validation examples

Current O1F smoke evidence validates O1E cancellation outcomes including:

```text
cancelled_before_start
cancelled_before_stale_recovery
cancelled_before_scheduler_round
cancelled_after_scheduler_round
```

O1F accepts these as lower O1E public outcomes when their projections remain safe and bounded. O1F does not own the cancellation checkpoint sequence itself.

## Read-only queue-root inventory entry point

The current read-only helper is:

```text
validate_queue_root_inventory(
    *,
    queue_root,
    max_scan_entries=4096,
    now=None,
)
```

It validates a bounded B3 queue-root view through existing queue-storage helpers.

It does not claim, release, retry, stale-recover, terminalize, delete, rewrite, or otherwise mutate queue records.

## Queue inventory input validation

`max_scan_entries` must have exact `int` type and satisfy:

```text
1 <= max_scan_entries <= 4096
```

Otherwise O1F returns:

```text
status = invalid_input
reason = operational_validation_scan_limit_invalid
unsafe = true
```

`now`, when supplied, must be an exact timezone-aware `datetime` or O1F returns:

```text
status = invalid_input
reason = operational_validation_now_invalid
unsafe = true
```

## Queue-root opening and locking

O1F delegates root opening to:

```text
open_queue_root(queue_root)
```

If the root cannot be safely opened, O1F returns `unsafe` with the lower bounded root reasons and category `corruption`.

The inventory then acquires the existing queue lock with:

```text
exclusive = false
```

Any lock error returns:

```text
status = unsafe
categories = [concurrency]
unsafe = true
```

O1F releases the lock and closes the root descriptor on every owned exit path.

## Queue inventory scan bound

Every directory entry increments the local scanned count, including entries that do not match the queue-record filename pattern.

If scanning exceeds the configured bound, O1F returns:

```text
status = unsafe
reason = operational_validation_scan_limit_exceeded
categories = [saturation]
scanned_entry_count = 4096
unsafe = true
```

The helper does not continue scanning after the bound is exceeded.

## Queue filename eligibility

Only names matching the current queue-record filename shape are opened as queue records:

```regex
^<FILENAME_PREFIX>[0-9a-f]{64}\.json$
```

The prefix itself remains owned by the queue-record contract/implementation.

Nonmatching directory entries count toward the scan bound but are otherwise ignored by O1F inventory validation.

## Queue snapshot validation

Eligible queue files are read through:

```text
read_record_snapshot(root_fd, name)
```

Each successfully attempted queue record increments `checked_candidate_count`.

If no safe snapshot is returned or the lower read status is not `ok`, O1F stops at the first invalid record and returns `unsafe` with the lower bounded reason or:

```text
operational_validation_queue_record_invalid
```

O1F does not repair, quarantine, rewrite, delete, or recover the malformed record.

## Queue operational shape validation

For each safe queue record, O1F validates only the operational shape needed by O1F.

The state must belong to the existing queue `ALL_STATES` vocabulary or O1F returns:

```text
operational_validation_unsupported_queue_state
```

Both timestamps must parse:

```text
created_at
updated_at
```

otherwise:

```text
operational_validation_queue_timestamp_invalid
```

For `claimed` state, these timestamps must parse:

```text
lease_acquired_at
lease_expires_at
```

otherwise:

```text
operational_validation_claim_lease_invalid
```

A claimed record must also carry nonempty:

```text
claim_owner
lease_token
```

otherwise:

```text
operational_validation_claim_identity_missing
```

When `now` is supplied and state is claimed, lease expiry is revalidated as parseable. O1F does not itself classify or transition a stale lease in this inventory helper.

## Queue inventory result

If any operational-shape reason is found, O1F returns:

```text
status = unsafe
categories = [corruption]
unsafe = true
```

with scanned/checked counts clamped to the O1F hard bound.

A fully safe bounded scan returns:

```text
status = validated
reason = queue_inventory_validated
categories = [corruption, saturation]
unsafe = false
```

The inventory is observational only.

## Sealed durable-finalization locator validation

The current helper is:

```text
validate_durable_finalization_locator(
    *,
    sealed_root,
    locator_digest,
)
```

Both inputs must have exact `str` type. Otherwise:

```text
status = invalid_input
reason = durable_finalization_validation_input_invalid
unsafe = true
```

O1F constructs the existing sealed store reader and calls:

```text
RelayMEMSLPDurableFinalizationStore(sealed_root).read_evidence(locator_digest)
```

If construction/read raises:

```text
status = unsafe
reason = durable_finalization_validation_failed
categories = [corruption]
unsafe = true
```

O1F does not create, rewrite, seal, replay, cleanup, or mutate durable-finalization state.

## Sealed locator accepted outcomes

A lower read result is validated as a successful sealed record when all are true:

```text
status == loaded
sealed == true
replayable == true
```

O1F then returns:

```text
status = validated
reason = sealed_i1g_record_validated
categories = [restart]
unsafe = false
```

A lower read status of `missing` or `blocked` with `record_present == false` is also a valid restart observation. O1F returns `validated` with the lower blocked reasons, or the derived bounded reason:

```text
durable_finalization_<status>
```

Other combinations return:

```text
status = unsafe
categories = [corruption, restart]
unsafe = true
```

This validation does not redefine I1-G/I1-GC/I1-GD lifecycle semantics.

## Source/queue correlation validation

The current helper is:

```text
validate_source_queue_correlation(
    *,
    source_dispatch_idempotency_key,
    queue_dispatch_idempotency_key,
)
```

Both arguments must have exact `str` type. Otherwise:

```text
status = invalid_input
reason = source_queue_correlation_input_invalid
categories = [correlation]
unsafe = true
```

The helper validates exact equality only.

Mismatch returns:

```text
status = unsafe
reason = source_queue_correlation_mismatch
categories = [correlation]
unsafe = true
```

Equality returns:

```text
status = validated
reason = source_queue_correlation_validated
categories = [correlation]
unsafe = false
```

Neither raw dispatch value is emitted in the O1F projection.

## Content-free projection validator

The current generic helper is:

```text
validate_content_free_projection(*values)
```

It serializes the supplied tuple with:

```text
json.dumps(
    values,
    ensure_ascii=true,
    sort_keys=true,
    default=str,
)
```

Serialization failures due to `TypeError`, `ValueError`, or `RecursionError` return:

```text
projection_encoding_failed
```

After lowercasing, the first forbidden token match returns:

```text
projection_private_token_leaked
```

No match returns an empty reason tuple.

This helper reports bounded validation reasons; it does not redact or rewrite a payload into a safe one.

## Bounded public projection validator

The current helper is:

```text
validate_bounded_public_projection(projection)
```

Input must be a Mapping or the helper returns:

```text
projection_shape_invalid
```

The mapping is serialized with ASCII JSON, sorted keys, and `default=str`. Serialization failure returns:

```text
projection_encoding_failed
```

The encoded UTF-8 byte size must satisfy:

```text
size <= 8192
```

otherwise:

```text
projection_size_exceeded
```

## Bounded reason-list validation

The projection field:

```text
bounded_reason_ids
```

must be a list with at most sixteen entries.

Violation returns:

```text
projection_reason_bound_invalid
```

Every entry must be exact `str` matching the O1F reason regex. Any invalid entry returns:

```text
projection_reason_invalid
```

## Bounded category-list validation

The projection field:

```text
categories
```

may be absent or equal to `[]`.

When nonempty, it must be a list with at most sixteen entries. Violation returns:

```text
projection_category_bound_invalid
```

Every category must be exact `str` matching the same token regex. Invalid values return:

```text
projection_category_invalid
```

The helper does not prescribe semantic meaning for categories owned by other subsystems.

## O1F reason normalization

The internal O1F token normalizer preserves first-seen order, removes duplicates, and caps output at the supplied maximum.

Invalid values normalize to:

```text
operational_validation_reason_invalid
```

If normalization produces no output, it inserts:

```text
operational_validation_status
```

The same bounded token machinery is used for O1F categories and reason IDs.

## Validation categories evidenced by O1F

The current O1F implementation and focused smokes use bounded categories including:

```text
operation
leakage
boundedness
corruption
concurrency
saturation
restart
correlation
```

This list describes current O1F validation evidence; it is not a plugin registry or open namespace granting arbitrary category semantics.

## Corruption boundary

Current O1F focused evidence covers malformed/noncanonical queue data, unsupported state, claim/lease shape failures, unsafe filesystem objects, malformed sealed durable-finalization state, and source/queue correlation mismatch.

O1F's response is fail-closed validation. It does not add repair authority.

## Concurrency boundary

Current O1F evidence exercises concurrent lower O1E stale-recovery and B3 claim behavior while preserving lower authority ownership.

O1F's own queue inventory uses an existing shared queue lock and reports lock errors as unsafe concurrency observations.

O1F does not introduce a scheduler-global mutex, background supervisor lock, or new claim/lease mechanism.

## Saturation and boundedness boundary

Current O1F evidence validates:

- finite queue scan bounds;
- finite public projection size;
- finite reason and category lists;
- repeated no-work caller invocations that still return without internal polling or sleep.

No boundedness test converts O1F into a recurring scheduler.

## Restart-reread boundary

Current O1F evidence re-evaluates queue and sealed durable-finalization state from the existing disk authorities across restart-shaped scenarios.

A missing or blocked absent sealed locator may be a valid restart observation. Corrupt or contradictory state remains unsafe.

O1F does not cache a second authoritative queue or durable-finalization state.

## Leakage boundary

O1F projections and repr paths are validation surfaces only. They must remain content-free and bounded.

O1F does not expose:

```text
job_id
dispatch_idempotency_key
claim_owner
lease_token
filesystem root/path
exact timestamps
raw queue record
raw exception
protected_source
visible_response
backend_text
memory_body
nested delegate result
```

The exact lower record/result may exist transiently inside the validation implementation but does not become public O1F output.

## Authority preservation

O1F preserves these ownership boundaries:

```text
O1A
  pure scheduler result/disposition contract

O1B
  sealed I1-G replay-lane discovery/reread and I1-GC delegation

O1C
  eligible B2/B3 queue-lane discovery/reread and C2 delegation

O1D1
  one-round replay-before-queue coordinator

O1D2
  fairness/retry-window/backoff/jitter/pacing policy

O1E
  cancellation, stale-recovery orchestration, and one-invocation operational controls

B3
  queue claim/lease/retry/stale-recovery/terminal transition semantics

I1-GC / I1-GD
  durable-finalization replay/completion/retention/cleanup semantics

C2
  queued-job worker execution semantics
```

O1F validates those boundaries but does not inherit their mutation authority.

## No-loop and no-service invariant

The O1F module is validation-only.

It must not introduce:

- `sleep` or async sleep;
- polling or recurring scheduling;
- timers or scheduler threads;
- daemon/service lifecycle;
- service supervision;
- worker pools;
- automatic retry loops;
- always-on local operation.

O2/O3 remain separately owned higher layers.

## Fail-closed invariants

The stable exact O1F fail-closed rules are:

1. malformed direct O1F inputs do not invoke lower operational work;
2. lower invocation exceptions become bounded `unsafe` validation output;
3. wrong lower result type becomes bounded `unsafe` output;
4. public leakage blocks validation success;
5. public projection overflow or invalid reason/category shape blocks validation success;
6. queue root/open/lock/read corruption becomes bounded unsafe output;
7. scan-limit overflow stops the bounded scan;
8. queue inventory does not repair records;
9. durable-finalization reader exceptions or contradictory state become unsafe;
10. source/queue correlation mismatch is unsafe without exposing the compared IDs;
11. validation never grants lower mutation authority;
12. no validation path adds polling, sleep, retry loop, daemon, or service supervision.

## Current focused evidence

The exact contract is guarded by the current O1F smoke family:

```text
scripts/relaylm_o1f_operational_validation_smoke.py
scripts/relaylm_o1f_operational_validation_corruption_smoke.py
scripts/relaylm_o1f_operational_validation_concurrency_smoke.py
scripts/relaylm_o1f_operational_validation_saturation_smoke.py
scripts/relaylm_o1f_operational_validation_restart_smoke.py
scripts/relaylm_o1f_operational_validation_security_smoke.py
```

The base smoke confirms, among other things:

- disabled O1E can validate without invoking a scheduler round;
- dry-run O1E validates with exactly one bounded lower round invocation;
- all four currently tested cancellation positions remain safe public outcomes;
- queue inventory is observational and leaves the record present;
- stale recovery remains O1E/B3-owned while O1F validates its public result;
- equal source/queue dispatch correlation validates without exposing either identifier.

## Relationship to permanent architecture

`docs/architecture/runtime/scheduler.md` owns the stable target separation of runtime/resource scheduling responsibilities.

This exact contract owns only the current O1F validation implementation boundary. It does not promote the O1F phase name into permanent architecture responsibility and does not alter the broader target scheduler architecture.

## Source-retirement boundary

This contract does not retire:

```text
docs/architecture/o1f_operational_validation.md
```

Nor does it retire completion evidence, smokes, implementation modules, or any O1A-O1E source. Source retirement requires its own bounded transaction with exact provenance, consumer repair, and migration disposition.
