---
relaylm_doc_type: implementation_handoff
relaylm_authority: i1ge_durable_finalization_crash_validation
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md
  - docs/architecture/i1gd_durable_finalization_retention_cleanup.md
  - docs/architecture/o1b_sealed_i1g_replay_lane.md
  - docs/mvp/wave3/i1ge_completion_report.md
relaylm_not_authoritative_for:
  - new durable-finalization schema
  - replay algorithm changes
  - scheduler or worker execution
  - Primary MEM formation
  - repository-wide current status after later waves
---
# I1-GE Durable-finalization crash validation handoff

## Status

I1-GE is complete as validation-only production evidence for the already implemented I1-GA through I1-GD durable-finalization authority chain. Source PR #411 merged as `e2caa1bdb53468ca282e8f374ba8ceebf839c976` with final head `6cb461cb614d14965f5a49c1c4b517755f44f4a6`.

The implementation adds crash-validation harnesses, permanent smokes, one CI workflow, and the Wave 3 completion report. It does not add production modules, accepted configuration, durable schemas, queue lifecycle, scheduler behavior, worker behavior, memory mutation, daemon behavior, or service supervision.

## Proven boundary

```text
I1-GB base / segment / seal publication
  -> protected visible release ordering
  -> normal finalizer or fresh-process restart replay
  -> I1-GC exact finalized-turn reconstruction
  -> canonical C1-5 protected-source convergence
  -> canonical B2 queue convergence
  -> exact downstream reread and correlation verification
  -> immutable content-free completion marker
  -> I1-GD retention / orphan isolation / marker-last cleanup proof
```

The permanent harness uses real child-process `os._exit` seams and fresh child interpreters for restart convergence. It distinguishes crash-immediate filesystem state from restart-converged state and requires canonical reread at every durable authority boundary.

## Crash seams

The source PR records the following bounded seam families:

```text
non-stream publication / visible release: 8 seams
stream publication / protected yield / terminal release: 9 seams
I1-GC reconstruction / C1-5 / B2 / completion: 12 seams
I1-GD retention / isolation / cleanup: 9 seams
```

Each seam uses a deterministic exit code. Sealed evidence converges to exactly one C1-5 source, one B2 queue record, and one completion marker. Incomplete evidence remains non-replayable. Repeated restart replay converges to already-complete without duplicate artifact growth.

## Concurrency and retention proof

I1-GE validates same-locator replay concurrency, normal finalizer versus restart replay, shared-fence busy mapping, O1B candidate replacement, completion appearance, and authoritative isolation appearance. It reuses the I1-GC/I1-GD nonblocking per-record fence and the I1-GB store-root mutation lock used by I1-GD cleanup.

Retention validation covers fresh reclassification, isolation marker publication/reread, component deletion boundaries, directory fsync, marker horizon, final marker deletion, sealed-pending non-destruction, forward recovery from marker-plus-components, and preservation of C1-5/B2 state. The per-record lock file remains present.

## Security and leakage boundary

Public crash-validation output is content-free. User content, model output, protected source text, private locator/job/dispatch/claim identities, paths, digests, timestamps, lease data, raw exceptions, and nested delegate results are not projected.

Filesystem security remains owned by the existing I1-G authorities and is covered through their regression suites: symlink, hardlink, unsafe type, path escape, duplicate JSON keys, malformed/noncanonical JSON/UTF-8, unknown fields, non-finite values, oversize objects, and inode/type replacement fail closed.

## Non-goals

I1-G completion after this proof means sealed durable-finalization evidence through exact C1-5/B2 correlation and durable completion plus retention/isolation lifecycle and crash-at-every-boundary validation. It does not mean B3 terminal success, C2 execution, worker execution, Primary MEM formation, semantic quality, retrieval use, automatic scheduling, polling, fairness, shutdown, supervision, or always-on operation.

## Permanent evidence

```text
scripts/_relaylm_i1ge_crash_child.py
scripts/_relaylm_i1ge_crash_validation.py
scripts/relaylm_i1ge_durable_finalization_nonstream_crash_smoke.py
scripts/relaylm_i1ge_durable_finalization_stream_crash_smoke.py
scripts/relaylm_i1ge_durable_finalization_replay_crash_smoke.py
scripts/relaylm_i1ge_durable_finalization_retention_crash_smoke.py
scripts/relaylm_i1ge_durable_finalization_concurrency_smoke.py
scripts/relaylm_i1ge_durable_finalization_security_smoke.py
.github/workflows/i1ge-durable-finalization-crash-validation.yml
docs/mvp/wave3/i1ge_completion_report.md
```

W3-INT records that the original implementation PR did not include this dedicated architecture handoff; this file is a documentation-governance correction based on the merged implementation report and PR inventory, not a production behavior change.
