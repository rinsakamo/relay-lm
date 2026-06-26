---
relaylm_doc_type: contract
relaylm_authority: o1a_two_lane_scheduler_round_adapter_and_idle_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - O1B replay-lane discovery or I1-GC delegation lands
  - O1C queue-lane discovery or O0 primitive extraction lands
  - O1D fairness retry-time or backoff policy lands
  - O1E stale-recovery cancellation or shutdown orchestration lands
  - O1F operational validation evidence lands
  - scheduler gate or projection schema changes
relaylm_not_authoritative_for:
  - I1-G durable-finalization record schema replay or completion semantics
  - C1-5 protected-source persistence or rehydration
  - B2 enqueue or B3 queue lifecycle
  - C2 one queued-record execution coordination
  - C1-2 worker execution or M3a-M3h memory formation
  - production scanning polling sleeping fairness backoff shutdown or service lifecycle
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - o0_local_one_job_runner.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6b3_relayslp_queue_state_helpers.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6c2_one_queued_primary_worker_integration.md
  - post_i3_evaluation_work_roadmap.md
  - pipeline_implementation_plan.md
  - relaymem_slp_current_target.md
---
# O1A: Bounded Two-Lane Work-Source Scheduling and Idle-State Contract

Last reviewed: 2026-06-26 JST

## 1. Status

**Contract and pure deterministic aggregation model complete; production scheduler unimplemented.**

O1A defines one bounded scheduler round across two distinct work sources:

1. one optional I1-G durable-finalization replay opportunity; then
2. one optional canonical B2/B3 queue execution opportunity.

O1A does not scan either root, select a production record, invoke I1-GC, invoke C2, poll, sleep, compute backoff, recover stale claims, supervise a process, or mutate a filesystem. The pure module `relaylm/relaymem_slp_scheduler_contract.py` validates already-bounded lane outcomes and derives only a scheduler result, a `stop | run_next_round | idle` disposition, and a content-free projection.

The following remain unimplemented:

```text
O1B  one eligible sealed I1-G record discovery and one I1-GC delegation — complete
O1C  one eligible B2 record discovery and one C2 delegation
O1D  deterministic within-lane ordering, fairness, retry-time and backoff policy
O1E  stale-claim recovery orchestration, cancellation, graceful shutdown
O1F  corruption, concurrency, saturation, restart, leakage, operational validation
```

O1A completion must not be described as automatic queue processing, a production scheduler loop, or always-on operation.

## 2. Purpose and target path

O0 provides one operator invocation that discovers and processes at most one eligible queue record. I1-GC is designed as one caller-selected sealed-record replay that converges C1-5 and B2 and writes the I1-G completion marker. Neither boundary owns automatic work-source scheduling.

```text
one bounded scheduler round
  -> replay lane opportunity
       -> future O1B bounded discovery
       -> existing I1-GC one-record replay
       -> C1-5 / B2 / I1-G completion convergence only
  -> queue lane opportunity
       -> future O1C bounded discovery
       -> O0-compatible canonical reread and scope resolution
       -> existing C2 one queued-record execution
  -> aggregate bounded content-free outcomes
  -> derive stop / run_next_round / idle
  -> return without sleeping
```

The scheduler coordinates opportunities. It does not absorb either underlying state machine.

## 3. Authority map

```text
O1 scheduler
  -> replay lane adapter
       -> O1B secure bounded discovery
       -> I1-GC one caller-selected record replay
  -> queue lane adapter
       -> O1C secure bounded discovery
       -> O0-compatible selection / canonical reread / scope resolution
       -> C2 one queued-record execution

I1-GC owns replay and durable completion convergence
C1-5 owns protected-source persistence and rehydration
B2 owns durable content-free queue publication
B3 owns claim / lease / retry / stale recovery / terminal lifecycle
C2 owns one queued-record claim / rehydrate / execute coordination
C1-2 owns one claimed worker execution
O1 owns only bounded scheduling between work sources
```

O1 owns only:

```text
server-owned scheduler enablement
fixed v0 lane order
one-opportunity-per-lane round budget
lane invocation eligibility
lane-local bounded outcome aggregation
stop / run_next_round / idle disposition
content-free scheduler projection
```

O1 does not own:

```text
I1-G schema, seal, replay, completion, isolation, retention, cleanup
C1-5 protected-source persistence, identity, rehydration, cleanup
B2 publication or duplicate/collision semantics
B3 claim, lease, retry release, stale recovery, terminal transition
C2 exact request and one-job execution coordination
C1-2 worker execution
M3a-M3h memory formation or lifecycle
queue or finalization repair
service process lifecycle
browser or SOUL Lab authority
```

No scheduler status replaces an I1-G, B3, C2, worker, or Primary MEM status.

## 4. Two independent lane state machines

O1 uses two explicit adapters. It does not introduce a generic plugin framework, generic job schema, shared durable state enum, or common storage format. Only the scheduler-level bounded result shape, one-round ordering, work-unit counters, disposition, and content-free projection are shared.

### 4.1 Replay lane

O1B eligibility:

```text
valid canonical I1-G record
state = sealed
completion absent
isolation absent
securely replayable now
```

Delegation:

```text
one caller-selected locator -> I1-GC
```

Permitted effects are owned by I1-GC and existing dependencies:

```text
C1-5 protected source absent -> canonical persistence
C1-5 exact duplicate -> convergence
B2 queue absent -> canonical enqueue
B2 exact duplicate -> convergence
exact downstream reread and correlation verification
I1-G completion marker commit and reread
```

Forbidden replay-lane effects:

```text
B3 claim
C2 invocation
worker execution
M3 mutation
retry-time modification
queue-record repair
```

### 4.2 Queue lane

Future O1C eligibility:

```text
valid canonical B2/B3 queue record
state = queued
retry_not_before absent or due
```

Delegation:

```text
O0-compatible bounded helper -> existing C2
```

Permitted effects are owned by B3/C1-5/C2/C1-2:

```text
B3 claim
C1-5 rehydration
C1-2 worker execution
retry release or terminal transition
terminal-only protected-source cleanup
```

Forbidden queue-lane effects:

```text
I1-G record mutation
I1-G completion publication
sealed-record reconstruction
use of replay-private output as queue authority
```

An I1-G record is never treated as a queue record.

## 5. Canonical one-round model

O1 v0 is single-threaded and sequential:

```text
validate scheduler-level gates
  -> replay-lane opportunity completes or returns
  -> queue-lane opportunity begins
  -> aggregate lane outcomes
  -> derive disposition
  -> return
```

The fixed order is `replay -> queue`. This lets Window-A evidence reach B2 before queue discovery while preserving separate replay and worker authorities. Both enabled lanes receive one opportunity per round. This is lane ordering, not record fairness.

Round bounds:

```text
I1-GC delegation per round       <= 1
C2 delegation per round          <= 1
total delegated work units       <= 2
```

A lane must not loop over multiple candidates. A round must not recurse, rescan in a loop, retry internally, sleep, or begin another round.

### 5.1 Same-round replay-to-queue rule

A replay opportunity may converge a new canonical B2 record. The later queue opportunity may independently discover that record in the same round.

```text
replay completes or returns
  -> queue lane opens queue root independently
  -> queue lane performs its own bounded discovery
  -> queue lane selects at most one canonical queue record
  -> queue lane performs canonical reread
  -> queue lane delegates to C2 at most once
```

Forbidden shortcuts:

```text
replay result -> direct C2 request
replay result -> direct queue candidate
scheduler extracts job or dispatch identity from replay result
scheduler treats I1-G private result as queue discovery authority
special priority for a queue record created by replay
```

The newly converged record may be selected, but O1 does not guarantee or privilege it.

## 6. Explicit lane adapter contracts

The target interfaces are `ReplayLaneAdapter` and `QueueLaneAdapter`, not a generic plugin system. Each invocation is bounded to:

```text
probe / discover at most one
  -> canonical reread
  -> delegate at most one
  -> return one bounded lane result
```

O1A defines the result contract. O1B now provides the production replay adapter; O1C remains unimplemented.

Schema:

```text
relaylm.local_scheduler_lane_result.v0
```

Internal fields:

```text
schema_version
lane_kind
status
enabled
attempted
candidate_observed
candidate_selected
canonical_reread_performed
delegation_attempted
delegation_completed
mutation_may_have_occurred
no_immediate_work
future_work_hint_present
contention_observed
retryable
unsafe
terminal_for_candidate
bounded_reason_ids
private_delegate_result
```

`private_delegate_result` is excluded from equality, `repr`, and public projection. The result exposes no locator, queue identity, path, source, claim, or exact timestamp.

Replay adapters must distinguish at least: no sealed candidate, selected candidate, changed candidate, lock busy, not replayable, already complete, delegated, completed, isolated/corrupt, and ambiguous/failed result.

Queue adapters must distinguish at least: no queued candidate, future retry only, busy, selected candidate, changed candidate, dry-run ready, C2 invoked, claim conflict, retry released, terminal, cleanup required, and unsafe queue state.

O1B may discover and classify but cannot implement replay convergence. O1C may discover and construct the existing exact C2 request but cannot implement B3 transitions or worker execution.

## 7. Bounded status vocabulary

Replay lane:

```text
dependency_unavailable
no_eligible_work
busy
candidate_changed
delegated
completed
already_complete
not_replayable
isolated
unsafe_state
failed
```

Queue lane:

```text
no_eligible_work
future_retry_only
busy
candidate_changed
dry_run_ready
delegated
executed
retry_released
terminal
cleanup_required
unsafe_state
failed
```

Scheduler:

```text
disabled
invalid_input
invalid_configuration
round_completed
partial_progress
idle
blocked
unsafe_state
unexpected_failure
```

The scheduler preserves lane meaning and aggregates only scheduler-relevant properties.

| Lane observation | Scheduler may derive | Scheduler must not claim |
|---|---|---|
| replay `completed` | bounded replay work completed | worker completed or MEM formed |
| queue `terminal` | queue delegation completed with terminal candidate result | semantic quality or MEM correctness |
| `retry_released` | bounded queue work completed and later work may remain | exact retry time or retry policy |
| `candidate_changed` | immediate next round may be useful | corruption or success |
| `busy` | later retry may be useful | no work exists |
| `no_eligible_work` | no immediate work observed in this attempt | root permanently empty |
| `isolated` / `unsafe_state` | lane-local unsafe outcome | other lane must roll back |

Unknown status values fail closed before projection.

## 8. Scheduler gates and target-only configuration

O1 is default-off. O1A records target names only and does not add them to `RelayLMConfig`, `docs/config_schema.md`, `config.example.yaml`, or CLI parsing.

```yaml
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
```

| Mode | enabled | dry_run_only | apply_enabled | Result |
|---|---:|---:|---:|---|
| disabled | false | true | false | no lane invocation; `stop` |
| dry-run | true | true | false | lower authorities remain dry-run only |
| apply | true | false | true | lower authorities may apply only when their own gates allow |

Every other combination is invalid and stops before lane invocation. An enabled scheduler with both lanes disabled is also invalid.

Scheduler gates never elevate I1-GC, O0, C2, B3, or durable-finalization gates. Replay apply requires future I1-GC explicit gates. Queue apply reuses current O0/C2 gates and server-owned roots. CLI and browser input cannot provide roots, locators, job IDs, dispatch IDs, or claims. Roots are never derived from a record. Interval, retry-time, fairness, backoff, and jitter remain O1D; concurrency and worker-count settings remain O2.

The pure `SchedulerGates` type uses exact booleans and rejects integer/string coercion.

## 9. Scheduler state model

These states describe orchestration only:

```text
disabled
invalid_configuration
ready
round_running
round_completed
idle
blocked
unsafe
stop_required
```

```text
ready
  -> round_running
       -> replay opportunity
       -> queue opportunity
  -> round_completed
       -> run_next_round
       -> idle
       -> stop_required
```

| State | O1 mutation | Typical disposition | Retryability |
|---|---|---|---|
| `disabled` | none | `stop` | no |
| `invalid_configuration` | none | `stop` | after correction |
| `ready` | none | external caller may begin one round | yes |
| `round_running` | only delegated lower-authority work | pending | lane-defined |
| `round_completed` | none after aggregation | `run_next_round` or `idle` | yes |
| `idle` | none | `idle` | later |
| `blocked` | none | scheduler-level dependency failure uses `stop` | cause-defined |
| `unsafe` | no scheduler repair | lane-local may aggregate; scheduler-level stops | fail closed |
| `stop_required` | none | `stop` | no until corrected |

Forbidden conflation:

```text
scheduler idle          != queue permanently empty
scheduler completed     != B3 terminal
replay completed        != worker completed
queue terminal          != Primary MEM formed
no eligible work        != healthy forever
lane busy               != no work
```

## 10. Pure disposition contract

### `stop`

Used for scheduler disabled, invalid gates, enabled scheduler with no lane, unsupported contract version, required capability unavailable, unsafe shared configuration, fatal scheduler state, or a future graceful-shutdown request. O1A does not implement shutdown signaling.

### `run_next_round`

Recommended when one or both delegations completed, a mutation may have occurred, a candidate changed during canonical reread, or bounded progress suggests more immediate work. O1A does not choose when the next round starts.

### `idle`

Normal later-retry result when both lanes report no immediate eligible work, only future retry work exists, a root is transiently busy, or a bounded lane-local retryable failure needs a later attempt. `idle` is not an error and does not imply permanent emptiness.

O1A never sleeps, registers timers, watches a filesystem, busy-loops, calculates delays, computes minimum retry timestamps, applies exponential backoff, or adds jitter.

A future queue adapter may retain a runtime-private typed earliest `retry_not_before` hint. The exact timestamp is not identity, is not projected, does not make a record eligible, and is not converted to a delay by O1A. Replay does not invent a retry timestamp. Public output exposes only `future_work_hint_present`, `idle_recommended`, and `immediate_next_round_recommended`.

## 11. Lane-local failure isolation

A bounded lane-local failure does not automatically suppress the unrelated lane or roll back completed work:

```text
replay busy                -> queue may run
replay no work             -> queue may run
replay isolated/corrupt    -> queue may run when shared configuration is safe
queue busy                 -> completed replay remains valid
queue unsafe record        -> queue performs no mutation; replay is not rolled back
queue claim conflict       -> replay remains valid
```

Round-fatal scheduler-level failures include invalid request schema, invalid gates, unsupported scheduler schema, unsafe shared root/config relation, missing required adapter capability, projection invariant failure, unknown lane status or type, and an adapter exception whose process integrity is unknown.

Isolatable failures include known nonblocking lock contention, candidate changes, canonical no-work/future-retry results, bounded I1-GC result failures, bounded C2/B3 claim conflicts or retry releases, and candidate-local corruption when root integrity remains established.

Raw exception text is never projected. Catch-all continuation is forbidden. An adapter may continue only after an exception classifier proves the failure is lane-local.

Cancellation before or between lanes is not implemented. O1E must preserve any completed replay result and prevent queue start when a shutdown checkpoint requires stop.

## 12. O0 reuse strategy

O1 does not launch `relaylm-worker` as a subprocess and does not parse CLI stdout as a production result. O1C must not reimplement B3 claim, change C2 request semantics, accept browser-owned identity/roots, or copy the CLI process-exit model into a scheduler loop.

Future safe reuse target:

```text
extract from O0 into a narrow production helper:
  one bounded queue discovery
  deterministic candidate selection
  canonical reread
  character/store scope resolution
  exact C2 request construction
```

O1A performs no refactor.

```text
O0:
  one operator invocation
  at most one queue job
  compact projection and process exit

O1C:
  one queue-lane opportunity inside one scheduler round
  same B3/C2 authority
  bounded lane result returned to scheduler
```

O0 CLI and smoke compatibility must remain intact after future O1C extraction.

## 13. I1-GC dependency strategy

O1B is the caller of I1-GC and is not part of I1-GC.

```text
I1-GC:
  accepts one caller-selected locator
  performs no scan or polling
  performs no worker execution
  owns exact replay, downstream convergence, and completion marker

O1B:
  performs bounded sealed-record discovery
  classifies secure eligibility
  deterministically selects one candidate under future O1D policy
  performs canonical reread
  delegates to I1-GC once
```

O1A/O1B never decide completion independently and never call C1-5 or B2 directly. At O1A completion I1-GC is still an independently developed dependency. This contract references only its target one-record interface and adds no production stub or fake success.

## 14. Internal result and public projection

Internal schema:

```text
relaylm.local_scheduler_round_result.v0
```

```text
schema_version
status
disposition
replay_lane          private nested LaneOutcome
queue_lane           private nested LaneOutcome
work_units_attempted
work_units_completed
idle_recommended
immediate_next_round_recommended
future_work_hint_present
retryable
unsafe
bounded_reason_ids
```

Nested lane outcomes are `repr=False`; nested delegate results are also `repr=False`.

Public/log schema:

```text
relaylm.local_scheduler_round_projection.v0
```

Allowed fields:

```text
schema_version
status
disposition
replay_lane_enabled
replay_lane_attempted
replay_lane_status
replay_candidate_selected
replay_delegated
replay_completed
queue_lane_enabled
queue_lane_attempted
queue_lane_status
queue_candidate_selected
queue_delegated
queue_completed
work_units_attempted
work_units_completed
idle_recommended
immediate_next_round_recommended
future_work_hint_present
retryable
unsafe
bounded_reason_ids
```

Reason IDs are unique lowercase ASCII identifiers, bounded to eight per lane and sixteen per round.

Forbidden projection data:

```text
user or assistant content
protected source or visible response
memory title summary or body
namespace or character value
run session turn job dispatch locator or lineage identity
queue or I1-G filename
store queue protected-source or finalization root
relative or absolute path
claim owner lease token generation or revision value
exact retry completion or record timestamp
digest or fingerprint
raw exception or config value
credential or backend secret
nested private lane result
nested I1-GC result
nested C2 result
```

## 15. Deterministic invariants

1. One round delegates to I1-GC at most once.
2. One round delegates to C2 at most once.
3. One lane contributes at most one delegated work unit.
4. Total delegated work units are at most two.
5. Replay opportunity precedes queue opportunity in v0.
6. Replay never executes a queue worker.
7. Queue never modifies an I1-G artifact.
8. Queue never accepts a job directly from replay output.
9. Queue discovery remains independent after replay completion.
10. B3 remains the only claim/lease/retry/terminal authority.
11. C2 remains the only one queued-record execution coordinator.
12. I1-GC remains the only replay/completion authority.
13. Scheduler never generates record, job, dispatch, claim, or memory identity.
14. Scheduler never changes retry time.
15. Scheduler never repairs an unsafe record.
16. Scheduler never converts failure into success.
17. No-work never starts a busy loop.
18. Exact delay policy does not exist before O1D.
19. O1A performs no filesystem mutation or production scan.
20. Public result is content-free.
21. Disabled/invalid scheduler invokes no lane.
22. Dry-run never elevates a lower authority to apply.
23. Unknown status, boolean coercion, and reason overflow fail closed.
24. Identical valid input yields an identical projection.

## 16. Fault and race matrix

### Scheduler-level

| Event | Required behavior |
|---|---|
| invalid gate combination | `invalid_configuration`, `stop`, no lane |
| both lanes disabled while enabled | `invalid_configuration`, `stop`, no lane |
| missing required capability | `blocked`, `stop`, no lane |
| safely lane-local adapter exception | bounded `failed`; unrelated lane may run |
| process-integrity-unknown exception | `unexpected_failure`; no further lane |
| projection invariant failure | fail closed; emit no leaking projection |
| cancelled before first lane | future O1E: `stop`, no lane |
| cancelled between lanes | future O1E: preserve replay, skip queue, `stop` |

### Replay lane

| Event | Owning authority | Outcome / continuation |
|---|---|---|
| no sealed record | O1B | `no_eligible_work`; queue may run |
| incomplete only | O1B/I1-G reader | `not_replayable` or no work; queue may run |
| completed only | O1B/I1-G reader | `already_complete` or no work; queue may run |
| replay lock busy | I1-GC | `busy`; queue may run |
| candidate replaced | O1B reread | `candidate_changed`; queue may run |
| becomes complete | I1-GC/reread | `already_complete`; queue may run |
| exact duplicate | I1-GC/C1-5/B2 | `completed`; queue may run |
| completion success | I1-GC | `completed`; queue may run |
| invariant violation | I1-GC | `unsafe_state`; queue only if shared integrity safe |
| isolated/corrupt | I1-G store/I1-GC | `isolated`; queue only if candidate-local |
| ambiguous replay | I1-GC | `failed` after reread; no invented success |

### Queue lane

| Event | Owning authority | Outcome |
|---|---|---|
| no queue record | O1C | `no_eligible_work` |
| future retry only | O1C | `future_retry_only`; private hint optional |
| advisory lock busy | O1C/O0 helper | `busy` |
| candidate replaced | O1C reread | `candidate_changed` |
| claimed elsewhere | B3/C2 | changed/conflict bounded result |
| C2 dry-run ready | C2 | `dry_run_ready` |
| claim conflict | B3/C2 | bounded retryable result |
| retry release | B3/C2 | `retry_released` |
| terminal success/failure | B3/C2 | `terminal` |
| cleanup incomplete | C1-5/C2 | `cleanup_required` |
| unsafe queue record | O1C/B3 reader | `unsafe_state`; no mutation |

### Cross-lane/concurrent actors

| Race | Required behavior |
|---|---|
| replay creates B2 before queue discovery | independent canonical queue discovery; no direct handoff |
| replay busy while queue work exists | queue still receives one opportunity |
| replay corrupt while queue work exists | queue may run only if corruption is candidate-local |
| queue busy while replay succeeds | replay remains committed; later-retry disposition |
| both no work | `idle` |
| both have work | replay then queue; at most two delegations |
| both fail independently | preserve both bounded results; no invented rollback/success |
| concurrent scheduler rounds | rely on I1-GC lock, queue lock, B3 CAS, C2 validation |
| O0 races O1 queue lane | existing queue lock/reread/B3 CAS decides |
| original finalizer races replay | I1-GC duplicate convergence/per-record lock decides |

O1 adds no global correctness lock.

## 17. Concurrency model

O1 v0 is single-threaded and sequential: the replay adapter returns before the queue adapter starts. Parallel lanes, scheduler threads, worker pools, per-character concurrency, distributed scheduling, leader election, and cross-host coordination are not implemented.

Multiple processes may begin rounds concurrently. Safety remains delegated to the I1-GC per-record lock, queue discovery advisory lock, B3 claim CAS, and C2 exact current-claim validation. A service-level single-instance policy belongs to O2.

## 18. Pure deterministic model and smoke

`relaylm/relaymem_slp_scheduler_contract.py` imports only standard-library dataclass/type/regex support. It has no filesystem, clock, sleep, network, queue, I1-GC, C2, config, or CLI integration. It validates gates, explicit lane order, work-unit bounds, status/flag consistency, reason bounds, and deterministic projection.

Dedicated smoke:

```text
PYTHONPATH=. python scripts/relaylm_o1a_two_lane_scheduler_contract_smoke.py
```

It validates the required twenty cases: fixed order, one delegation per lane, total two work units, all work/no-work combinations, idle/future/busy handling, lane failure isolation, disabled/invalid gates, independent queue input, private-result and leakage canaries, bounded reasons, unknown status rejection, strict booleans, and deterministic output.

The model does not prove production discovery. O1B/O1C/O1F must supply that proof. O0, C2, B2, B3, I1-G, compile, documentation-link, and current-boundary checks remain regressions.

## 19. O1B-O1F handoff

```text
O1A
  two-lane round, adapter result, gate, disposition, projection contract

O1B
  bounded I1-G sealed-record scan
  secure eligibility classification
  deterministic one-candidate selection
  canonical reread
  one I1-GC delegation

O1C
  bounded B2 queued-record scan
  safe O0 primitive extraction/reuse
  canonical reread and character/store resolution
  one C2 delegation

O1D
  within-lane deterministic ordering
  fairness and starvation policy
  retry-time handling
  bounded backoff and jitter
  saturation pacing

O1E
  stale-claim recovery orchestration
  cancellation checkpoints
  graceful shutdown

O1F
  corruption, concurrent rounds and external races
  saturation and repeated failure
  restart, leakage, operational regression
```

O1A does not preselect O1D delay values or O1E shutdown behavior.

## 20. Explicit non-goals

```text
production scheduler loop
while loop polling sleep backoff jitter filesystem watch
sealed-record directory scan or I1-G eligibility implementation
I1-GC production invocation or completion cleanup
queue directory scan or B2 candidate implementation
C2 invocation or B3 transition
stale-claim recovery
O0 refactor
config.py config-schema or config-example changes
CLI command daemon service worker pool health endpoint metrics
systemd Windows service Docker supervision
SOUL Lab control or browser scheduling
fairness priority quotas distributed coordination leader election
```

<!-- O1B_LANDED_HANDOFF -->
## O1B landed handoff

`relaylm/relaymem_slp_scheduler_replay_lane.py` now performs one bounded replay-lane opportunity and returns the existing `LaneOutcome`. A replay `busy` may be learned only after I1-GC returns from a completed delegation; a completed dry-run `delegated` result is an idle disposition and does not force another round. The pure O1A module still performs no filesystem scan or lane invocation.
