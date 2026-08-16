---
relaylm_doc_type: contract
relaylm_authority: current_relaymem_slp_scheduler_replay_lane_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - O1B replay-lane discovery bounds, component grammar, classification, selection, or reread semantics change
  - replay-lane gate compatibility or source-registry behavior changes
  - I1-GC delegate-status to LaneOutcome mapping changes
  - replay-lane PipelineNodeResult projection or privacy boundary changes
  - I1-G/I1-GD filename, validation, or isolation integration changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - O1A LaneOutcome/SchedulerGates common schema and round aggregation
  - I1-GC replay/completion convergence semantics
  - I1-GD isolation, retention, cleanup, or orphan policy
  - O1C queue-lane discovery/delegation
  - B2/B3 queue lifecycle or C2 worker execution
  - O1D1/O1D2/O1E/O1F/O2/O3 higher scheduling, policy, service, validation, or process semantics
  - Primary MEM formation, retrieval, or protected-source persistence
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/runtime/scheduler.md
  - ../../architecture/o1b_sealed_i1g_replay_lane.md
  - ../../architecture/o1a_two_lane_scheduler_contract.md
  - ../../architecture/o1d1_production_scheduler_round.md
  - ../slp/durable-finalization.md
relaylm_related_contracts:
  - scheduler-round.md
  - scheduler-policy.md
  - scheduler-operational-controls.md
  - scheduler-operational-validation.md
  - supervised-scheduler-service.md
  - local-scheduler-process.md
relaylm_verified_by:
  - ../../../scripts/relaylm_o1b_sealed_replay_lane_smoke.py
  - ../../../scripts/relaylm_wave2_cross_slice_convergence_smoke.py
  - ../../../scripts/relaylm_wave3_cross_slice_convergence_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayMEM SLP replay-lane and scheduler maintainers
  - durable-finalization replay and isolation maintainers
  - runtime, recovery, security, filesystem-hardening, and observability reviewers
relaylm_authority_level: exact_contract
---
# Scheduler Replay Lane Contract

## Authority summary

This contract owns the exact current **O1B bounded sealed I1-G replay-lane adapter** implemented by:

```text
relaylm/relaymem_slp_scheduler_replay_lane.py
```

One O1B invocation performs at most this sequence:

```text
server-owned durable-finalization root
  -> one bounded non-recursive inventory
  -> exact component grammar/grouping
  -> current I1-G/I1-GD validation
  -> deterministic first sealed-pending locator selection
  -> bounded canonical selected-locator reread
  -> at most one existing I1-GC replay delegation
  -> exact O1A replay LaneOutcome
  -> content-free replay PipelineNodeResult when requested
  -> return
```

O1B never polls, sleeps, recursively starts another round, tries a second candidate, claims queue work, invokes C2, forms Primary MEM, or directly mutates I1-G evidence.

## Current implementation anchors

The exact replay-lane owner is:

```text
relaylm/relaymem_slp_scheduler_replay_lane.py
```

It consumes existing authorities from:

```text
relaylm/relaymem_slp_scheduler_contract.py
relaylm/relaymem_slp_durable_finalization_record.py
relaylm/relaymem_slp_durable_finalization_replay.py
relaylm/relaymem_slp_durable_finalization_isolation.py
relaylm/relaymem_slp_durable_finalization_store.py
relaylm/relaymem_slp_primary_worker_source_registry.py
```

The implementation handoff remains:

```text
docs/architecture/o1b_sealed_i1g_replay_lane.md
```

This transaction does not retire that handoff.

## Common scheduler contract boundary

O1B returns `LaneOutcome` and accepts `SchedulerGates`, but it does not own their common schema. That remains the exact `scheduler-round.md` responsibility.

O1B specializes those common fields for:

```text
lane_kind = replay
```

and owns replay-specific discovery, reread, delegation, reason mapping, and node projection only.

## Public replay entry point

The current public replay-lane function is:

```text
run_relaymem_slp_scheduler_replay_lane_once(
    *,
    config,
    gates,
    registry=None,
    discovery_max_entries=None,
    fault_injector=None,
) -> LaneOutcome
```

The call is one bounded replay opportunity. It does not represent a scheduler service or recurring loop.

## Current replay node name

The exact PipelineNodeResult node name is:

```text
REPLAY_LANE_NODE_NAME = relaymem_slp_scheduler_replay_lane
```

## Discovery bounds

The exact current inventory bounds are:

```text
DEFAULT_DISCOVERY_MAX_ENTRIES = 256
MAX_DISCOVERY_MAX_ENTRIES     = 4096
```

When `discovery_max_entries` is null, O1B uses 256.

Otherwise the value must be exact `int` and satisfy:

```text
1 <= discovery_max_entries <= 4096
```

Invalid input returns a replay `LaneOutcome` with:

```text
status = unsafe_state
enabled = true
attempted = true
unsafe = true
no_immediate_work = true
reason = replay_inventory_limit_invalid
```

No inventory or delegation follows.

## Replay reason bound

O1B normalizes replay-specific reason IDs to at most:

```text
8
```

Each reason must match:

```regex
[a-z][a-z0-9_]{0,63}
```

Invalid values normalize to:

```text
replay_reason_invalid
```

Duplicates are removed while preserving first-seen order.

The common `LaneOutcome` contract remains authoritative for the final stored reason field.

## Exact config requirement

If:

```text
type(config) is not RelayLMConfig
```

O1B returns:

```text
status = dependency_unavailable
enabled = false
reason = exact_relaylm_config_required
```

No root access, registry creation, or delegate call occurs.

## Exact scheduler gates requirement

If:

```text
type(gates) is not SchedulerGates
```

O1B returns:

```text
status = dependency_unavailable
enabled = false
reason = exact_scheduler_gates_required
```

## Common scheduler-gate validation

O1B first consumes:

```text
gates.validation_reason_ids()
```

When any common gate reason exists, O1B returns `dependency_unavailable` without replay discovery.

The replay-specific reason is:

```text
scheduler_dependency_unavailable
```

only when the exact common reason tuple is:

```text
(required_dependency_unavailable,)
```

Otherwise O1B uses:

```text
scheduler_gate_invalid
```

`enabled` reflects whether both the scheduler and replay lane are enabled.

`retryable=true` only for the exact dependency-unavailable case above.

## Disabled scheduler behavior

When:

```text
gates.mode == disabled
```

O1B returns:

```text
status = no_eligible_work
enabled = false
no_immediate_work = true
reason = scheduler_disabled
```

## Disabled replay lane behavior

When the scheduler itself is usable but:

```text
gates.replay_lane_enabled == false
```

O1B returns:

```text
status = no_eligible_work
enabled = false
no_immediate_work = true
reason = replay_lane_disabled
```

## Required dependency availability

If:

```text
gates.required_dependency_available == false
```

O1B returns:

```text
status = dependency_unavailable
enabled = true
retryable = true
reason = scheduler_dependency_unavailable
```

## Fault injector exactness

`fault_injector` may be null or callable.

A non-null non-callable value returns:

```text
status = unsafe_state
enabled = true
attempted = true
unsafe = true
no_immediate_work = true
reason = replay_fault_injector_invalid
```

The fault injector is a focused validation seam only; it is not a production extension/plugin mechanism.

## Lower I1-GC mode derivation

O1B derives the lower durable-finalization mode from this exact current config triple:

```text
relaymem_slp_durable_finalization_enabled
relaymem_slp_durable_finalization_dry_run_only
relaymem_slp_durable_finalization_apply_enabled
```

The exact mapping is:

```text
(false, true,  false) -> disabled
(true,  true,  false) -> dry_run
(true,  false, true ) -> apply
anything else         -> invalid
```

This derives compatibility only. It does not redefine I1-GC gate authority.

## Invalid lower replay gate

If the lower I1-GC mode is invalid, O1B returns:

```text
status = dependency_unavailable
enabled = true
attempted = true
no_immediate_work = true
reason = replay_delegate_gate_invalid
```

No inventory/delegation proceeds.

## Scheduler dry-run cannot elevate I1-GC apply

When:

```text
gates.mode == dry_run
AND
I1-GC mode == apply
```

O1B returns:

```text
status = dependency_unavailable
enabled = true
attempted = true
no_immediate_work = true
reason = scheduler_dry_run_blocks_replay_apply
```

Thus an upper scheduler dry-run cannot execute an apply-configured lower replay path.

Conversely, scheduler apply does not elevate disabled or dry-run lower I1-GC gates.

## Durable-finalization root source

The replay inventory root comes only from:

```text
config.relaymem_slp_durable_finalization_root
```

O1B opens it through the existing secure durable-finalization store root helper.

It does not accept a per-call root override.

## One non-recursive inventory

O1B inventories the root exactly once before candidate selection.

Every directory entry increments the discovery count, including control objects and unknown objects.

When the count would exceed the configured limit, O1B returns an incomplete unsafe inventory with:

```text
reason = replay_inventory_limit_exceeded
entry_count = configured limit
```

The partial inventory is not used to select or delegate a candidate.

## Root identity

Before scanning, O1B records a directory identity tuple consisting of:

```text
device
inode
mtime_ns
ctime_ns
```

After inventory it rereads root metadata.

A changed root identity returns an incomplete unsafe inventory with:

```text
replay_root_changed_during_inventory
```

The selected-locator reread later requires the same root identity again.

## Root integrity requirements

The root must remain an actual directory and safely readable through the existing secure root opener.

Unsafe/unavailable cases normalize to bounded reasons such as:

```text
replay_root_unavailable
replay_root_integrity_unsafe
replay_inventory_failed
```

O1B does not fall back to another filesystem path.

## Recognized durable-finalization component grammar

O1B recognizes only these exact current non-isolation filename families:

```text
durable-finalization-v0-<64 lowercase hex>.base.json

durable-finalization-v0-<64 lowercase hex>.segment-<6 decimal digits>.json

durable-finalization-v0-<64 lowercase hex>.seal.json

durable-finalization-completion-v0-<64 lowercase hex>.json
```

The 64-hex locator grammar is:

```regex
[0-9a-f]{64}
```

Segment sequence syntax is six decimal digits.

## Isolation filename authority

Isolation filenames are not copied into O1B as a second grammar.

O1B delegates recognition to the current I1-GD helpers:

```text
parse_isolation_filename(...)
is_isolation_temp_filename(...)
```

and reads current isolation state through:

```text
read_relaymem_slp_durable_finalization_isolation_fd(...)
```

A valid loaded isolation marker classifies the logical record as `isolated`.

An isolation read that does not produce the exact expected loaded result is unsafe.

## Control objects

Known replay lock and current temporary publication/completion/isolation names are control objects only.

The replay-lock grammar is derived from the current I1-GC replay implementation lock prefix.

Current publication temp patterns include the exact current temporary families used by durable-finalization publication and completion.

Control objects:

- count toward discovery bounds;
- must be regular, non-symlink, single-link filesystem objects;
- must remain within their current bounded size;
- never become replay candidates.

## Unknown root entries

A root entry that matches neither a recognized durable component nor a current approved control-object shape contributes:

```text
replay_unknown_root_entry
```

and makes the inventory unsafe.

O1B does not ignore arbitrary unknown filesystem objects in the authoritative root.

## Filesystem object requirements

Every scanned entry must remain:

```text
regular file
not symlink
link count == 1
```

Any symlink, non-regular object, hardlink-shaped entry, stat failure, or equivalent ambiguity contributes:

```text
replay_root_integrity_unsafe
```

and fails the inventory closed.

## Logical grouping

Recognized components are grouped by locator digest.

Within one group, O1B permits at most one:

```text
base
seal
completion
isolation
```

Duplicate singleton components classify the group `unsafe`.

Segments must have unique sequence numbers.

The sorted segment sequence list must equal:

```text
0, 1, 2, ... N-1
```

A gap, duplicate, malformed sequence, or segment count beyond:

```text
config.relaymem_slp_durable_finalization_max_segment_count
```

classifies the group corrupt/unsafe as implemented.

## Group-state vocabulary

The exact internal O1B group-state vocabulary is:

```text
incomplete
sealed_pending
complete
isolated
corrupt
unsupported
unsafe
```

These states are private discovery/classification state. They are not a public replacement for I1-GC/I1-GD lifecycle statuses.

## Component byte bounds

Current maximum component bytes are delegated to existing authorities:

```text
segment
  -> config.relaymem_slp_durable_finalization_max_segment_bytes

completion
  -> current I1-GC maximum completion bytes

isolation
  -> current I1-GD ISOLATION_MAX_BYTES

base / seal
  -> config.relaymem_slp_durable_finalization_max_record_bytes
```

The aggregate base/segments/seal evidence byte count must also remain within the configured durable-finalization maximum record bytes.

## Component read hardening

Before opening a selected component, O1B validates captured metadata including:

```text
device
inode
size
mtime_ns
regular-file type
single-link count
maximum bytes
```

It opens by dirfd with no-follow behavior where available, validates the opened fd again, performs a bounded read, and validates pathname metadata again after reading.

Any identity/type/race ambiguity fails closed.

## Canonical JSON and existing validators

Non-isolation durable components are decoded through existing canonical JSON logic.

The exact record validators remain separately owned:

```text
validate_base_record
validate_segment_record
validate_segment_chain
validate_seal_record
validate_completion_marker
```

O1B uses their result/reason semantics for classification; it does not duplicate or redefine their schema.

Validator reasons containing schema/revision classification map a private group to `unsupported`; other invalid record shapes map to `corrupt`.

## Classification matrix

Current classification is:

```text
valid base + optional gap-free segments, no valid seal
  -> incomplete

valid base + chain + seal, no completion, no isolation
  -> sealed_pending

valid completion correlated to valid seal
  -> complete

current loaded isolation marker
  -> isolated

malformed canonical data / chain / digest / correlation
  -> corrupt

unsupported schema/revision
  -> unsupported

filesystem/path/type/race ambiguity
  -> unsafe
```

A completion without a valid seal or whose `seal_digest` does not equal the validated seal digest is corrupt/unsupported rather than complete.

## Unsafe group dominance

After classification, if any group is:

```text
corrupt
unsupported
unsafe
```

O1B fails the invocation closed before selection with replay LaneOutcome:

```text
status = unsafe_state
candidate_observed = true
unsafe = true
no_immediate_work = true
reason = replay_record_unsafe
```

The private candidate snapshot may be retained only inside private delegate details excluded from public representation/equality.

O1B does not select a healthy record while silently ignoring another authoritative-root corrupt record.

## Deterministic selection

Eligible groups are exactly those with:

```text
state = sealed_pending
```

O1B sorts them lexicographically by locator and selects exactly the first.

One call never selects a second candidate after a change, busy delegate, failed delegate, or not-replayable result.

## No-candidate reasons

If there is no eligible sealed-pending group, O1B returns:

```text
status = no_eligible_work
no_immediate_work = true
```

The current reason precedence is:

```text
replay_records_isolated
  if any classified group is isolated

replay_records_complete
  else if any group is complete

replay_records_incomplete
  else if any classified group exists

replay_no_eligible_record
  otherwise
```

`candidate_observed` is true when classified groups exist.

## Canonical selected-locator reread

After deterministic selection, O1B does not rescan the entire directory.

It rereads the selected locator using only the inventory-captured component set and validates:

- root identity unchanged;
- selected locator still present in captured grouping;
- current classification is still `sealed_pending`;
- component entry identity matches the captured identity;
- component content signatures match the captured digest signatures;
- root identity remains unchanged after reread.

This closes add/remove/replace/change races without introducing a second unbounded inventory.

## Reread outcomes

A reread exception returns:

```text
status = failed
retryable = true
reason = replay_reread_failed
```

An unsafe reread returns:

```text
status = unsafe_state
unsafe = true
no_immediate_work = true
reason = replay_reread_unsafe
```

A newly isolated selected locator returns:

```text
status = isolated
unsafe = true
no_immediate_work = true
reason = replay_candidate_isolated
```

Any other selected-locator change returns:

```text
status = candidate_changed
retryable = true
reason = replay_candidate_changed
```

All three selected-locator paths mark candidate observed/selected and canonical reread performed as appropriate.

## Process-local source registry

O1B may receive an exact:

```text
RelayMEMSLPPrimaryWorkerSourceRegistry
```

If `registry` is null, O1B creates one with current config:

```text
max_entries = config.relaymem_slp_source_registry_max_entries
ttl_seconds = config.relaymem_slp_source_registry_ttl_seconds
```

Registry construction `TypeError` or `ValueError` returns:

```text
status = dependency_unavailable
reason = source_registry_unavailable
```

A supplied non-null object whose exact type is not the registry class returns:

```text
status = dependency_unavailable
reason = exact_source_registry_required
```

O1B never pre-registers protected source content from the durable record.

## Single I1-GC delegation

After a successful canonical reread and registry resolution, O1B calls at most once:

```text
replay_relaymem_slp_durable_finalization_record(
    config,
    locator_digest = current.locator,
    registry = exact_registry,
)
```

The selected locator is passed privately to the existing I1-GC authority and is never included in O1B public diagnostics.

O1B never directly calls C1-5/B2/B3/C2/worker/M3 as a substitute for I1-GC.

## Delegation exception

If I1-GC raises, O1B returns:

```text
status = failed
delegation_attempted = true
retryable = true
no_immediate_work = true
reason = replay_delegate_failed
```

No second candidate or fallback delegate is attempted.

## Mutation-may-have-occurred detection

When a delegate result exists, O1B treats mutation as potentially having occurred when its projection reports any of:

```text
source_created
queue_created
completion_created
```

This boolean is used only for scheduler safety/result aggregation. O1B does not claim ownership of those lower mutations.

## I1-GC delegate status mapping

The exact current delegate-to-replay-lane mapping is:

```text
disabled
  -> dependency_unavailable
     reason replay_delegate_disabled
     no_immediate_work true
     retryable false

 dry_run_ready
  -> delegated
     reason replay_delegate_dry_run
     no_immediate_work true
     mutation_may_have_occurred false

completed | exact_duplicate
  -> completed
     reason replay_delegate_completed
     mutation_may_have_occurred true
     terminal_for_candidate true

already_complete
  -> already_complete
     reason replay_delegate_already_complete
     mutation_may_have_occurred false
     terminal_for_candidate true

replay_lock_busy
  -> busy
     reason replay_delegate_busy
     contention_observed true
     retryable true
     no_immediate_work true

record_missing | not_replayable
  -> not_replayable
     reason replay_delegate_not_replayable
     retryable true
     no_immediate_work true

corrupt | schema_unsupported | unsafe_path_or_type |
content_collision | invariant_violation
  -> unsafe_state
     reason replay_delegate_unsafe
     unsafe true
     retryable false
     no_immediate_work true
     mutation_may_have_occurred derived from lower projection
```

Remaining delegate results map to replay `failed`.

## Pending/failure fallback mapping

For these lower statuses:

```text
source_pending
queue_pending
completion_pending
ambiguous
```

O1B returns replay:

```text
status = failed
retryable = true
reason = replay_delegate_pending
```

A lower status exactly `failed` is also retryable but uses:

```text
replay_delegate_failed
```

Other unrecognized delegate statuses return `failed`, are not automatically retryable, and use `replay_delegate_failed`.

Mutation-may-have-occurred remains derived from the lower projection when available.

## Delegation fault after lower return

If the focused fault seam fires after I1-GC returns but before lane mapping, O1B returns `failed` while preserving:

```text
delegation_attempted = true
delegation_completed = true
mutation_may_have_occurred = lower-derived value
retryable = true
no_immediate_work = true
reason = replay_fault_injected
```

This prevents a post-effect observation fault from falsely claiming that no lower mutation may have happened.

## PipelineNodeResult adapter

The current node adapter is:

```text
build_relaymem_slp_scheduler_replay_lane_node_result(outcome)
```

It requires exact `LaneOutcome` with:

```text
lane_kind = replay
```

otherwise it raises:

```text
exact_replay_lane_outcome_required
```

## Node status mapping

The current node-status mapping is:

```text
replay lane status failed
  -> PipelineNodeResult status failed

replay lane status in
  dependency_unavailable
  busy
  not_replayable
  isolated
  unsafe_state
  -> PipelineNodeResult status blocked

all other replay lane statuses
  -> PipelineNodeResult status diagnostic_only
```

The node `decision` is the exact replay lane status.

`blocked_reasons` are the bounded replay LaneOutcome reason IDs.

## Content-free node diagnostics

The replay node diagnostics explicitly mark:

```text
diagnostics_only = true
content_free = true
content_included = false
identifier_values_included = false
path_values_included = false
digest_values_included = false
timestamp_values_included = false
exception_text_included = false
nested_delegate_result_included = false
```

The diagnostics contain only replay lane status/boolean fields and bounded reason IDs from the common LaneOutcome.

## Private replay node artifact

The current node artifact is marked:

```text
artifact_name = relaymem_slp_scheduler_replay_lane
content_free = true
private = true
```

It may report booleans for candidate/delegation/completion observation, but not the actual locator or lower delegate result.

`completion_observed_by_delegate` is true only when replay lane status is:

```text
completed
already_complete
```

## Public privacy boundary

O1B public outcomes, repr paths, node diagnostics, scheduler projections, and artifacts must not expose:

- user or assistant text;
- protected source or memory content;
- character or namespace values;
- job, dispatch, run, session, or turn IDs;
- selected locator;
- filename or filesystem path;
- device/inode identity;
- digest values;
- exact timestamps;
- registry content;
- raw exception text;
- nested I1-GC/C1-5/B2 results.

Candidate snapshots and delegate results are retained only in private non-repr/non-equality helper state.

## Concurrency boundary

O1B does not claim a global correctness lock around the root.

Current race closure relies on:

- root identity checks;
- selected-component identity/content reread;
- existing I1-GC replay fence;
- current I1-GD isolation/cleanup authority.

Another replay caller may win the I1-GC fence. Bounded `busy`, `already_complete`, `candidate_changed`, `isolated`, or lower fail-closed results are accepted convergence outcomes.

O1B does not retry internally.

## No queue-lane authority

O1B does not:

- scan the B2 queue root;
- inspect queue eligibility timestamps;
- claim B3 jobs;
- call C2 worker execution;
- release queue claims;
- terminalize queue records;
- expose queue-private candidate identity.

Those remain O1C/B3/C2 responsibilities.

## No direct durable-finalization mutation authority

O1B discovery and reread are read-only.

Any source publication, enqueue, completion marker creation, isolation, retention, cleanup, or replay convergence is delegated to separately owned I1-G authorities.

O1B selects an opportunity; it does not become the durable-finalization semantic owner.

## One-opportunity invariant

One invocation performs at most:

```text
one root inventory
one eligible selection
one selected-locator canonical reread
one I1-GC delegation
```

There is no:

- second candidate fallback;
- internal retry;
- sleep;
- poll;
- timer;
- recurring service loop;
- daemon/process wrapper;
- queue-lane invocation.

Higher O1D1/O2 orchestration may invoke O1B again only through their separately owned round/service semantics.

## Fail-closed invariants

The exact current O1B fail-closed rules include:

1. wrong config/gate types prevent discovery;
2. invalid scheduler gates prevent discovery;
3. invalid discovery bounds or fault seam prevent unsafe scanning;
4. incompatible scheduler/I1-GC mode combinations do not elevate lower apply;
5. unknown or unsafe root objects invalidate the bounded inventory;
6. inventory overflow discards the partial candidate set;
7. any corrupt/unsupported/unsafe logical group blocks selection from the root;
8. deterministic selection never skips to a second candidate after failure/change;
9. selected root/component identity and content are revalidated before delegation;
10. isolation appearing before delegation prevents replay;
11. registry construction/type failure prevents delegation;
12. delegate exceptions/failures produce bounded replay failure and no second attempt;
13. post-delegate fault preserves mutation-may-have-occurred conservatively;
14. public output never includes locator/path/digest/content/private delegate state;
15. O1B never reaches around I1-GC to perform lower replay/completion mutations itself.

## Current focused evidence

The exact replay-lane contract is guarded by:

```text
scripts/relaylm_o1b_sealed_replay_lane_smoke.py
scripts/relaylm_wave2_cross_slice_convergence_smoke.py
scripts/relaylm_wave3_cross_slice_convergence_smoke.py
```

The O1B focused evidence covers bounded inventory, deterministic selection, canonical reread races, single delegation, dry-run/apply isolation, direct I1-GC contention, exact completion convergence, filesystem type/link/JSON/size hardening, fault seams, non-goals, and content-leakage canaries.

## Relationship to scheduler-round contract

`docs/contracts/runtime/scheduler-round.md` owns the common `SchedulerGates`, `LaneOutcome`, scheduler-round result/projection, one-round aggregation, and O1D1 replay-before-queue call order.

This contract owns what happens **inside the replay lane** before that common outcome is returned.

The two authorities are complementary and non-overlapping.

## Relationship to O1C

O1C is the separate eligible B2/B3 queue-lane adapter.

O1B and O1C share common `LaneOutcome` mechanics but do not share discovery roots, candidate identity, delegation targets, lifecycle semantics, or private state.

O1C exact contract remains a separate transaction.

## Source-retirement boundary

This transaction does not retire:

```text
docs/architecture/o1b_sealed_i1g_replay_lane.md
```

Nor does it retire I1-G/O1A/O1C handoffs, implementation modules, smoke evidence, or completion reports. Any retirement requires separate exact provenance, consumer repair, and migration disposition.
