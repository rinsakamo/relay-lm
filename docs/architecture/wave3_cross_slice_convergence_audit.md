---
relaylm_doc_type: implementation_handoff
relaylm_authority: wave3_cross_slice_convergence_record
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - exact lower-level schemas
  - future phase implementation
  - repository-wide current status after later waves
---
# Wave 3 Cross-Slice Convergence Audit

## Status and authority

W3-INT audited the merged Wave 3 implementation tracks, reconciled shared documentation, and was merged through PR #415. Wave 4 follow-up planning may use the frozen W3-INT authority map and inputs.

This audit is historical evidence for the Wave 3 convergence point. It records verified source PR inventory, cross-slice authority boundaries, documentation reconciliation, and frozen Wave 4 inputs. Dedicated handoffs and production modules remain authoritative for lower-level behavior.

## Wave 3 source PR inventory

| Slice | Source PR | Merged | Merge commit | Final head | Completion report | Dedicated handoff |
|---|---:|---|---|---|---|---|
| I1-GE full production crash validation | #411 | 2026-06-27 07:41:44 JST | `e2caa1bdb53468ca282e8f374ba8ceebf839c976` | `6cb461cb614d14965f5a49c1c4b517755f44f4a6` | `docs/mvp/wave3/i1ge_completion_report.md` | `docs/architecture/i1ge_durable_finalization_crash_validation.md` |
| I-4D lifecycle-aware retrieval exclusion | #414 | 2026-06-27 07:34:39 JST | `48e890f05f76196b73267559b079f4a05c441077` | `81c58516a4ba04c6e439ff17d633575bb193f843` | `docs/mvp/wave3/i4d_completion_report.md` | `docs/architecture/phase_i4d_primary_retrieval_exclusion.md` |
| O1D1 accepted scheduler gates and one round | #412 | 2026-06-27 02:02:51 JST | `9b6349236f1a01f3cdccbe9e3c2c874ae1137475` | `7aa051abe6a9e49a2f67c193b7e742f9406ec54f` | `docs/mvp/wave3/o1d1_completion_report.md` | `docs/architecture/o1d1_production_scheduler_round.md` |

The W3-INT start main SHA is `e2caa1bdb53468ca282e8f374ba8ceebf839c976`, which includes the documentation-governance PR #410 merge commit `4d31f45cfba967e23bd50f01f3c3d7ce9a8d0a33` and the three Wave 3 source PR merge commits.

## Completion report and handoff verification

All three completion reports declare `relaylm_doc_type: implementation_completion_report` and concrete source PR numbers. Their changed-file lists match the source PR file inventories checked during W3-INT:

- I1-GE #411 changed ten files: six public smokes, two private harness modules, one workflow, and one completion report. It intentionally changed no production module.
- I-4D #414 changed sixteen files: retrieval eligibility/runtime integration, Lab lifecycle projection/parser/API, seven permanent smokes, one workflow, one handoff, and one completion report.
- O1D1 #412 changed fourteen files: accepted config/schema/example, scheduler coordinator, O1D1 support/smokes, current-boundary smoke, workflow, handoff, and completion report.

Divergence found and corrected: I1-GE had a completion report but no dedicated architecture handoff in the merged source PR. W3-INT adds `docs/architecture/i1ge_durable_finalization_crash_validation.md` as a documentation-governance correction based on the merged PR body and report. No production behavior is changed.

## Production modules and workflows

| Slice | Production modules | Permanent evidence |
|---|---|---|
| I1-GE | none; validation-only against I1-GB/I1-GC/I1-GD/O1B authorities | `scripts/relaylm_i1ge_durable_finalization_*_smoke.py`, `scripts/_relaylm_i1ge_crash_*.py`, `.github/workflows/i1ge-durable-finalization-crash-validation.yml` |
| I-4D | `relaylm/relaymem_primary_recall.py`, `relaylm/relaymem_primary_retrieval_eligibility.py`, `relaylm/soul_lab_used_memory_lifecycle_projection.py`, `relaylm/soul_lab_app.py`, SOUL Lab used-memory lifecycle parser | `scripts/relaylm_phase_i4d_*_smoke.py`, `.github/workflows/phase-i4d-primary-retrieval-exclusion.yml` |
| O1D1 | `relaylm/config.py`, `relaylm/relaymem_slp_scheduler_round.py`, `docs/config_schema.md`, `config.example.yaml` | `scripts/relaylm_o1d1_*_smoke.py`, `.github/workflows/o1d1-production-scheduler-round.yml` |
| W3-INT | documentation and combined smoke only | `scripts/relaylm_wave3_cross_slice_convergence_smoke.py`, `scripts/relaylm_wave3_cross_slice_security_smoke.py`, `.github/workflows/wave3-cross-slice-convergence.yml` |

## Cross-slice authority map

| Boundary | Owner | W3 result | Must not absorb |
|---|---|---|---|
| Durable-finalization sealed evidence | I1-GB publication and I1-GC replay | I1-GE proves real crash/restart at every boundary | scheduler loop, worker execution, Primary mutation |
| Durable-finalization retention/isolation | I1-GD | I1-GE proves cleanup crash convergence and marker-last deletion | queue root, B3 claim, memory root |
| Replay lane | O1B -> I1-GC | O1D1 calls at most once and does not inspect private replay identity | O1C selection, queue claim, C2 execution |
| Queue lane | O1C -> C2 | O1D1 calls at most once after replay; same-round work uses independent queue rediscovery | replay-private locator/job/dispatch handoff |
| Scheduler aggregation | O1A | remains pure; O1D1 validates and invokes around it | lane discovery semantics, lower apply gates |
| Retrieval lifecycle filter | I-4D | filters after M2 selection and before snippet/RelayCTX/backend-bound construction | Forget mutation, recovery, queue execution |
| Historical lifecycle projection | I-4D | overlays current lifecycle as read-only v1 projection | rewriting durable v0 used-memory receipts |

## I1-GE vs O1D1

I1-GE crash seams and test harnesses own no scheduler authority. O1D1 does not read I1-GC private replay identity and uses only O1B -> I1-GC for the replay lane. After completion is present, duplicate replay converges to already-complete through I1-GC/O1B; O1D1 does not synthesize queue records or directly hand replay locators/jobs/dispatches to O1C. I1-GD-isolated records are not delegated by O1B/O1D1. Scheduler apply is an upper gate only and does not elevate durable-finalization replay/apply gates.

Combined scenario recorded by W3 smoke:

```text
child process exits after protected visible release
  -> fresh process
  -> O1D1 one round
  -> O1B independently discovers sealed record
  -> existing I1-GC converges C1-5/B2/completion
  -> O1C independently rescans queue root
  -> normal O1C selection/C2 authority
  -> O1A bounded result
  -> no direct replay-to-queue identity handoff
```

Even when the queue lane reaches C2/worker in a later scenario, I1-GE completion still means only crash proof for durable-finalization through C1-5/B2/completion and retention lifecycle; it does not imply worker terminal success or Primary MEM formation.

## I-4D vs O1D1

Scheduler, queue, and worker code do not absorb Primary lifecycle resolver authority. I-4D changes ordinary retrieval only; it does not mutate B2, B3, C2, worker state, scheduler config, or round result. Hidden filtering applies at request-time to ordinary M2/RelayCTX and does not retroactively remove queued work or memory formation candidates. Scheduler result/projection remains content-free and carries no memory lifecycle private data.

A memory formed through O1D1-visible queue execution is subject to normal future ordinary retrieval. If that memory later becomes hidden/prepared/recovery-required/corrupt/prior/cross-scope, I-4D excludes it before snippet construction.

## I1-GE vs I-4D

Durable-finalization crash proof does not create Primary lifecycle mutation. I-4D filtering does not alter I1-G, C1-5, B2, B3, C2, or worker evidence. Crash fixtures, reports, and public validation results remain content-free. Hidden memory content is not projected into I1-GE public results or W3 combined output. Their roots and locks remain independent.

## Lock / root / authority map

| Boundary | Owner | Hold scope | Must not absorb |
|---|---|---|---|
| I1-G record fence | I1-GC / I1-GD shared locator fence | one durable-finalization locator | scheduler loop / queue claim |
| I1-GB root mutation lock | I1-GB / I1-GD | durable-finalization root mutation | queue root / memory root |
| O1 queue discovery advisory lock | shared queue candidate authority | bounded inventory only | C2 delegation lifetime |
| B3 transition lock | B3 | one queue record transition | scheduler policy |
| Primary mutation lock | shared Correct/Forget authority | one logical memory | ordinary retrieval |
| I-4D retrieval resolver | read-only request scope | bounded current-state resolution | mutation/recovery |
| O1D1 coordinator | one caller invocation | no global correctness lock | lower lane authority |

No cross-root global lock is introduced by Wave 3 or W3-INT.

## Config map

O1D1 accepts exactly five production scheduler fields as `StrictBool` defaults:

```yaml
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
```

Invalid mode triples and enabled-with-both-lanes-disabled invoke no lane. Interval, poll, fairness, backoff, jitter, shutdown, daemon, supervision, and always-on fields remain absent.

## Race and failure interaction results

- I1-GE: sealed evidence, exact C1-5/B2 correlation, completion, duplicate convergence, ambiguous-write fail-closed, unsafe filesystem fail-closed, and marker-last retention are proven under process exit and restart.
- I-4D: active current revision remains eligible, while hidden, prepared, recovery-required, corrupt, ambiguous, unsafe, prior, cross-scope, and unresolved identities fail closed before snippets.
- O1D1: replay is invoked before queue at most once each, same-round replay-created B2 is visible only through independent O1C rediscovery, and round faults return bounded content-free results without sleeping or retrying.

## Security and leakage results

W3 combined security smoke rejects the following canaries from scheduler projection/repr, I1-GE public handoff text, I-4D public projection contract, W3 combined output, completion-report validation output, and documentation-boundary smoke output:

```text
user content
model output
memory summary/title
Forget reason
tombstone content
I1-G locator
queue root/path
job ID
dispatch ID
claim token
character private scope
raw exception
private timestamp
```

The audit may name abstract identity classes such as locator, job, dispatch, claim, root, and timestamp, but it must not include concrete private values.

## Documentation reconciliation

W3-INT updated the repository-wide current documents and indexes to state:

```text
I1-GA complete
I1-GB complete
I1-GC complete
I1-GD complete
I1-GE complete
I1-G overall complete

I-4B complete
I-4C1 complete
I-4C2 complete
I-4D complete
I-4E unimplemented
I-4F unimplemented
Phase I-4 overall in progress

O1A contract complete
O1B complete
O1C complete
O1D1 complete
O1D2 unimplemented
O1E unimplemented
O1F unimplemented
O1 overall in progress
O2 planned/unimplemented
O3 planned/unimplemented

Wave 3 implementation tracks complete
W3-INT merged
Wave 4 follow-up planning may use the frozen W3-INT authority map and inputs
```

Completion reports remain frozen historical evidence. `docs/mvp/README.md` links them centrally after W3-INT verifies their source PRs.

## Frozen Wave 4 inputs

### O1D2

Owns deterministic ordering beyond fixed lane order, fairness/starvation prevention, retry-time handling, bounded backoff/jitter, and saturation pacing. It does not own O1B/O1C discovery semantics, I1-GC replay semantics, C2/B3 worker semantics, supervision, or always-on service.

### O1E

Starts after O1D2 policy boundary is stable. Owns stale-claim operational recovery orchestration, cancellation checkpoints, and graceful shutdown. It does not own queue record schema, worker semantic outcome, or scheduler lane discovery.

### O1F

Owns corruption, concurrency, saturation, restart, leakage, and operational validation. It may build validation infrastructure in parallel, but must not claim O1 completion before O1D2 and O1E land.

### I-4E

Owns loopback-only mutation API and SOUL Lab Forget preflight/confirm/refusal/conflict/receipt UI. It must consume I-4B current-state/token authority, I-4C1/I-4C2 mutation/recovery authority, and I-4D read-only lifecycle result. It does not own retrieval filtering algorithm, restore, or purge.

### I-4F

Starts after I-4E product surface is stable. Owns fresh-conversation exclusion validation, crash/race/security validation, and product-level Forget completion proof.

### UI-B1A

Read-only only. It may show durable-finalization pending/complete/isolated, queued/processing/formed/held/blocked/failed, active/hidden/recovery-required, current revision, and fresh-conversation verification. It must not mutate queue/memory/SOUL, authorize repair, or become scheduler control.

### I-5A and I-7A/B

Contract/preflight work may begin after W3-INT merge. It must preserve the shared Primary mutation fence and must not add runtime Pin/Held apply behavior beyond each exact slice.

## Remaining non-goals

W3-INT implements no new durable-finalization schema, replay algorithm, queue lifecycle, worker behavior, Primary MEM mutation, Forget API/UI, restore/unhide/purge, scheduler polling loop, sleep, fairness/backoff/jitter policy, stale recovery, shutdown, daemon/service supervision, always-on operation, Pin/Unpin apply, Held Apply/Discard, Merge/Supersession, Secondary MEM consolidation, RelaySOUL mutation, TTS/audio/avatar/Live2D, ASR, or peer communication.
