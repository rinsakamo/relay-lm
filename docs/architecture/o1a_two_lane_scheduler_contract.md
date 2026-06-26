---
relaylm_doc_type: contract
relaylm_authority: o1a_two_lane_scheduler_round_adapter_and_idle_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - O1B replay-lane discovery or I1-GC delegation lands
  - O1C queue-lane discovery or O0 primitive extraction lands
  - O1D1 scheduler-gate acceptance or production round coordination lands
  - O1D2 fairness retry-time backoff jitter or pacing policy lands
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
  - o1b_sealed_i1g_replay_lane.md
  - o1c_eligible_b2_queue_lane.md
  - o1d1_production_scheduler_round.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - wave3_cross_slice_convergence_audit.md
  - post_i3_evaluation_work_roadmap.md
  - pipeline_implementation_plan.md
  - relaymem_slp_current_target.md
---
# O1A: Bounded Two-Lane Work-Source Scheduling and Idle-State Contract

Last reviewed: 2026-06-27 JST

## 1. Status

**Contract and pure deterministic aggregation model complete.** O1B replay adapter, O1C queue adapter, and O1D1 one production round are complete. Recurring scheduler behavior, fairness/retry-time/backoff/jitter/pacing, stale recovery, graceful shutdown, supervision, and always-on operation remain unimplemented.

O1A defines one bounded scheduler round across two distinct work sources:

1. one optional I1-G durable-finalization replay opportunity; then
2. one optional canonical B2/B3 queue execution opportunity.

O1A does not scan either root, select a production record, invoke I1-GC, invoke C2, poll, sleep, compute backoff, recover stale claims, supervise a process, or mutate a filesystem. The pure module `relaylm/relaymem_slp_scheduler_contract.py` validates already-bounded lane outcomes and derives only a scheduler result, a `stop | run_next_round | idle` disposition, and a content-free projection.

O1D1 is now the production wiring for exactly one such round. It accepts the exact scheduler gates, invokes O1B then O1C at most once each, aggregates through O1A, validates content-free projection, and returns without sleep. O1A or O1D1 completion must not be described as recurring automatic queue processing, a production polling loop, supervision, or always-on operation.

The remaining phases are:

```text
O1D2  deterministic ordering policy, fairness/starvation prevention, retry-time,
      bounded backoff/jitter, and saturation pacing
O1E   stale-claim recovery orchestration, cancellation checkpoints, graceful shutdown
O1F   corruption, concurrency, saturation, restart, leakage, operational validation
O2/O3 supervised and always-on local operation
```

## 2. Purpose and path

O0 provides one operator invocation that discovers and processes at most one eligible queue record. I1-GC provides one caller-selected sealed-record replay that converges C1-5 and B2 and writes the I1-G completion marker. Neither boundary owns automatic work-source scheduling.

```text
one bounded scheduler round
  -> replay lane opportunity
       -> O1B bounded discovery
       -> existing I1-GC one-record replay
       -> C1-5 / B2 / I1-G completion convergence only
  -> queue lane opportunity
       -> O1C bounded discovery
       -> O0-compatible canonical reread and scope resolution
       -> existing C2 one queued-record execution
  -> aggregate bounded content-free outcomes through O1A
  -> derive stop / run_next_round / idle
  -> return without sleeping
```

The scheduler coordinates opportunities. It does not absorb either underlying state machine. O1D2 and O1E own the later policy and controls required to start, delay, cancel, or stop subsequent rounds.

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

O1 owns only server-owned scheduler enablement, fixed v0 lane order, one-opportunity-per-lane round budget, lane invocation eligibility, lane-local bounded outcome aggregation, `stop | run_next_round | idle` disposition, and content-free scheduler projection.

O1 does not own I1-G schema/seal/replay/completion/isolation/retention/cleanup, C1-5 protected-source persistence, B2 publication, B3 claim/lease/retry/stale/terminal lifecycle, C2 exact request coordination, C1-2 worker execution, M3a-M3h memory formation or lifecycle, queue/finalization repair, service process lifecycle, browser authority, or SOUL Lab authority. No scheduler status replaces an I1-G, B3, C2, worker, or Primary MEM status.

## 4. Two independent lane state machines

O1 uses two explicit adapters. It does not introduce a generic plugin framework, generic job schema, shared durable state enum, or common storage format. Only the scheduler-level bounded result shape, one-round ordering, work-unit counters, disposition, and content-free projection are shared.

Replay lane eligibility and delegation remain O1B/I1-GC authority:

```text
valid canonical I1-G record
state = sealed
completion absent
isolation absent
securely replayable now
  -> one caller-selected locator -> I1-GC
```

Forbidden replay-lane effects include B3 claim, C2 invocation, worker execution, M3 mutation, retry-time modification, and queue-record repair.

Queue lane eligibility and delegation remain O1C/C2 authority:

```text
valid canonical B2/B3 queue record
state = queued
retry_not_before absent or due
  -> O0-compatible bounded helper -> existing C2
```

Forbidden queue-lane effects include I1-G record mutation, I1-G completion publication, sealed-record reconstruction, and use of replay-private output as queue authority. An I1-G record is never treated as a queue record.

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

## 6. Same-round replay-to-queue rule

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

## 7. Scheduler gates and accepted configuration

O1 is default-off. O1D1 accepts exactly these names into the production configuration surface and wires them to one production round:

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

Scheduler gates never elevate I1-GC, O0, C2, B3, or durable-finalization gates. Replay apply requires the existing I1-GC/durable-finalization explicit gates. Queue apply reuses current O0/C2 gates and server-owned roots. CLI and browser input cannot provide roots, locators, job IDs, dispatch IDs, or claims. Roots are never derived from a record. Interval, retry-time, fairness, backoff, jitter, and saturation pacing remain O1D2; concurrency and worker-count settings remain O2.

The pure `SchedulerGates` type uses exact booleans and rejects integer/string coercion.

## 8. Internal result and public projection

Internal schema:

```text
relaylm.local_scheduler_round_result.v0
```

Public/log schema:

```text
relaylm.local_scheduler_round_projection.v0
```

`private_delegate_result` is excluded from equality, `repr`, and public projection. Nested lane outcomes are `repr=False`; nested delegate results are also `repr=False`.

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

## 9. Deterministic invariants

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
18. Exact delay and fairness policy does not exist before O1D2.
19. O1A performs no filesystem mutation or production scan.
20. Public result is content-free.
21. Disabled/invalid scheduler invokes no lane.
22. Dry-run never elevates a lower authority to apply.
23. Unknown status, boolean coercion, and reason overflow fail closed.
24. Identical valid input yields an identical projection.
25. O1D1 invokes each enabled lane at most once and always returns without sleep or recursion.

## 10. Pure disposition contract

`stop` is used for scheduler disabled, invalid gates, enabled scheduler with no lane, unsupported contract version, required capability unavailable, unsafe shared configuration, fatal scheduler state, or a future graceful-shutdown request. O1A does not implement shutdown signaling.

`run_next_round` is recommended when one or both delegations completed, a mutation may have occurred, a candidate changed during canonical reread, or bounded progress suggests more immediate work. O1A does not choose when the next round starts. O1D1 returns this recommendation to its caller but does not act on it.

`idle` is the normal later-retry result when both lanes report no immediate eligible work, only future retry work exists, a root is transiently busy, or a bounded lane-local retryable failure needs a later attempt. `idle` is not an error and does not imply permanent emptiness.

O1A and O1D1 never sleep, register timers, watch a filesystem, busy-loop, calculate delays, compute minimum retry timestamps, apply exponential backoff, or add jitter. A future queue adapter may retain a runtime-private typed earliest `retry_not_before` hint, but the exact timestamp is not projected or converted to delay before O1D2.

## 11. Fault and race matrix

Lane-local failures do not automatically suppress the unrelated lane or roll back completed work. A replay busy/no-work/candidate-local isolated result may still allow the queue lane. Queue busy or failure never rolls back completed replay work.

Round-fatal scheduler-level failures include invalid request schema, invalid gates, unsupported scheduler schema, unsafe shared root/config relation, missing required adapter capability, projection invariant failure, unknown lane status or type, and an adapter exception whose process integrity is unknown.

Cancellation before or between lanes is not implemented. O1E must preserve any completed replay result and prevent queue start when a shutdown checkpoint requires stop.

O1 adds no global correctness lock. Multiple processes may begin rounds concurrently; safety remains delegated to the I1-GC per-record lock, queue discovery advisory lock, B3 claim CAS, and C2 exact current-claim validation. A service-level single-instance policy belongs to O2.

## 12. Pure deterministic model and smoke

`relaylm/relaymem_slp_scheduler_contract.py` imports only standard-library dataclass/type/regex support. It has no filesystem, clock, sleep, network, queue, I1-GC, C2, config, or CLI integration. It validates gates, explicit lane order, work-unit bounds, status/flag consistency, reason bounds, and deterministic projection.

Dedicated smoke:

```text
PYTHONPATH=. python scripts/relaylm_o1a_two_lane_scheduler_contract_smoke.py
```

The model does not by itself prove production round coordination. O1D1 supplies that proof for one caller-invoked round; O1F must still supply operational validation. O0, O1B, O1C, C2, B2, B3, I1-G, compile, documentation-link, and current-boundary checks remain regressions.

## 13. O1B-O1F handoff

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

O1D1
  accept the five exact scheduler gates
  validate disabled / dry-run / apply combinations
  invoke O1B at most once, then O1C at most once
  aggregate through O1A
  return without sleep, recursion, or another round

O1D2
  deterministic ordering policy beyond the fixed lane order
  fairness and starvation prevention
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

O1A does not preselect O1D2 delay/fairness values or O1E shutdown behavior. O1D1 uses the O1A contract unchanged rather than introducing a second scheduler result model.

## 14. Explicit non-goals

```text
production polling loop or automatic repeated-round launcher
while loop polling sleep backoff jitter filesystem watch
sealed-record directory scan or I1-G eligibility implementation inside O1A
I1-GC replay semantics or completion cleanup
queue directory scan or B2 candidate implementation inside O1A
C2 execution semantics or B3 transition ownership
stale-claim recovery
O0 behavior changes
new accepted scheduler config beyond the five O1D1 fields
CLI daemon service worker pool health endpoint metrics
systemd Windows service Docker supervision
SOUL Lab control or browser scheduling
fairness priority quotas distributed coordination leader election before O1D2/O2
```
