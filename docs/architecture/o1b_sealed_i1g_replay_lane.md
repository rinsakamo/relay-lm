---
relaylm_doc_type: handoff
relaylm_authority: o1b_sealed_i1g_replay_lane_discovery_and_delegation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaymem_slp_operations
relaylm_update_trigger:
  - I1-G record grammar or completion schema changes
  - I1-GD isolation filename or validator changes
  - I1-GC result vocabulary changes
  - O1C O1D1 O1D2 O1E or O1F scheduler integration lands
relaylm_not_authoritative_for:
  - I1-G replay or completion convergence
  - I1-GD retention isolation cleanup or orphan policy
  - C1-5 protected-source persistence
  - B2/B3/C2/worker/M3 execution
  - scheduler polling fairness backoff shutdown validation or service lifecycle
  - repository-wide current implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - o1a_two_lane_scheduler_contract.md
  - o1c_eligible_b2_queue_lane.md
  - o1d1_production_scheduler_round.md
  - o1d2_scheduler_policy.md
  - o1e_scheduler_operational_controls.md
  - o1f_operational_validation.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - o0_local_one_job_runner.md
  - phase6c1_durable_protected_source_persistence.md
  - phase6b2_relayslp_atomic_durable_enqueue.md
  - phase6c2_one_queued_primary_worker_integration.md
  - wave3_cross_slice_convergence_audit.md
---
# O1B: Bounded Sealed I1-G Replay-Lane Discovery

Last reviewed: 2026-06-27 JST

## Status and authority

**Production replay-lane adapter complete.** O1C queue-lane adapter, O1D1 one production round, O1D2 scheduling policy, O1E recovery/shutdown controls, and O1F operational validation are also complete at their bounded caller-invoked boundaries. O2 supervision and O3 always-on service operation remain planned/unimplemented.

O1B owns exactly one bounded replay-lane opportunity:

```text
configured durable-finalization root
  -> bounded non-recursive secure inventory
  -> exact component grammar and locator grouping
  -> read-only eligibility classification
  -> lexicographically first sealed-pending locator
  -> bounded canonical selected-locator reread
  -> existing I1-GC delegation at most once
  -> O1A LaneOutcome
  -> return without polling or sleeping
```

O1B does not reconstruct finalized turns, publish protected sources or queue records, decide durable completion, claim B3 work, invoke C2, execute a worker, or form Primary MEM. Those remain I1-GC, C1-5, B2/B3, C2, C1-2, and M3 authorities.

O1D1 may call O1B at most once in a single caller-invoked round, before O1C. O1D2 may wrap that round with bounded policy hints, O1E may wrap it with caller-invoked operational controls, and O1F may validate the operational boundary. None of those downstream slices changes O1B semantics or makes O1B a scheduler loop.

## Root and inventory bounds

The root comes only from `RelayLMConfig.relaymem_slp_durable_finalization_root`. The existing secure I1-G root opener enforces an absolute pre-existing directory, rejects symlink path components, and uses dirfd-relative operations.

One discovery inventory is non-recursive and bounded. Every directory entry counts against `discovery_max_entries`; the default is 256 and the accepted maximum is 4096. If the directory exceeds the cap, O1B discards the partial inventory, selects nothing, delegates nothing, and returns `unsafe_state`.

Known replay-lock and current publication temporary names are control objects only. They count toward the cap and never become candidates. Unknown objects, non-regular objects, symlinks, hardlinks, oversized controls, unsupported versions, and noncanonical grammar fail closed.

## Filename grammar and logical records

O1B recognizes only:

```text
durable-finalization-v0-<64 lowercase hex>.base.json
durable-finalization-v0-<64 lowercase hex>.segment-<6 decimal digits>.json
durable-finalization-v0-<64 lowercase hex>.seal.json
durable-finalization-completion-v0-<64 lowercase hex>.json
```

When the current I1-GD isolation authority is present, O1B obtains the exact isolation filename and validator from that module instead of copying its schema. Without that authority, an isolation-looking unknown object fails closed.

Recognized components are grouped by locator. Segment sequences must be unique, start at zero, be gap-free, and remain within the configured segment bound.

## Eligibility matrix

| State | Minimum observation | O1B action |
|---|---|---|
| `incomplete` | valid base/segments without a valid seal | retain; no candidate |
| `sealed_pending` | exact base/chain/seal; completion and isolation absent | eligible |
| `complete` | valid completion correlated to a valid seal | no candidate |
| `isolated` | current authoritative isolation marker present | no candidate |
| `corrupt` | malformed canonical data, chain/digest/correlation failure | fail closed |
| `unsupported` | unsupported schema or revision | fail closed |
| `unsafe` | path/type/link/race/root-integrity ambiguity | fail closed |

O1B does not independently prove downstream completion. A valid completion marker only excludes discovery; I1-GC remains the final replay/completion authority after its per-record fence and canonical reread.

## Canonical reread and delegation

After selection, O1B does not inventory the directory again. It verifies that the root directory identity is unchanged from the single bounded inventory, then rereads only the selected locator components captured by that inventory. The reread verifies exact filenames, device/inode identity, sizes, and content digests and reclassifies the locator as sealed pending. Component addition/removal, inode replacement, byte change, completion appearance, isolation appearance, or unsupported/unsafe state prevents delegation.

O1B passes only the selected locator and an exact process-local source registry to `replay_relaymem_slp_durable_finalization_record(...)`. It never pre-registers record content and never calls C1-5, B2, B3, C2, worker, or M3 directly. One O1B invocation performs at most one I1-GC call and never falls back to a second candidate.

A scheduler dry-run never authorizes an apply-configured I1-GC. Scheduler apply also never elevates disabled or dry-run I1-GC gates.

## Races and concurrency

- I1-GB publication racing discovery is detected by selected-locator reread or by I1-GC.
- Another direct I1-GC or O1B invocation may win the replay fence; the loser returns bounded `busy` or `already_complete`.
- I1-GD isolation/cleanup changes are respected; O1B does not bypass its marker or lock.
- Completion appearing after discovery becomes `candidate_changed` or I1-GC `already_complete`.
- No global root correctness lock, retry loop, sleep, or recursive round is added.

## Content-free projection

The public surface is strictly content-free. `LaneOutcome`, `repr`, the O1B node result, and scheduler projections expose only bounded statuses, booleans, counts, and approved reason IDs. Candidate snapshots and the raw I1-GC result are private and excluded from equality and representation.

The projection contains no user/assistant text, governed content, character/namespace, runtime IDs, locator, filename, path, digest, timestamp, registry content, raw exception, or nested C1-5/B2 result.

## Non-goals and next boundaries

```text
O0    local one-job queue runner                              complete
O1A   pure two-lane scheduler contract                        complete
O1B   sealed I1-G discovery + one I1-GC delegation            complete
O1C   eligible B2 discovery + one C2 delegation               complete
O1D1  accepted scheduler gates + one production round         complete
O1D2  ordering/fairness/retry-time/backoff/jitter/pacing      complete
O1E   stale recovery/cancellation/graceful shutdown           complete
O1F   operational validation                                  complete
O2    supervised service                                      planned/unimplemented
O3    always-on operation                                     planned/unimplemented
```

O1B adds no scheduler CLI, browser route, accepted scheduler configuration, polling interval, daemon, service unit, queue scan, queue execution, or automatic operation.

## Validation

The dedicated functional and security smokes cover gates, bounded inventory, safe no-work, deterministic selection, canonical reread changes, single delegation, dry-run/apply isolation, direct-I1-GC contention, exact completion convergence, filesystem type/link/JSON/size hardening, fault seams, non-goals, and content-leakage canaries. O1A, I1-GA/I1-GB/I1-GC, O0, documentation boundary, compileall, and link checks remain regression authorities.
