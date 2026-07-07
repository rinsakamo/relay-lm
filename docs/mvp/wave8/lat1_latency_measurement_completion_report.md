---
relaylm_doc_type: implementation_completion_report
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# LAT-1 Latency Measurement Completion Report

## Scope

This report records the LAT-1 latency-measurement slice: real per-node RelayRUN
timing on the live request path plus an offline M2 retrieval scaling bench.
The slice is measurement only -- no request-path behavior, degradation-ladder,
timeout, node-skip, or search-algorithm change. The base branch is `main` at
the time this slice started (the P1 CTX Repack ordering fix, PR #476, is
already merged into `main` and this slice builds on top of it).

## Implemented production boundary

Implemented:

- `relaylm/relayrun.py`: `RelayRunNode.duration_ms` field (defensively nulled
  by `to_log_dict()` whenever either `started_at` or `completed_at` is
  missing, so a node can never show a backfilled/guessed duration);
  `started_at`/`completed_at`/`duration_ms` params on `build_relayrun_node()`;
  new `build_relayrun_timing_summary()` (pure aggregation over already-built
  `node_statuses`, no timing or I/O of its own); `timing_summary` param on
  `build_runtime_checkpoint_dry_run_artifact()`.
- `relaylm/relayrun_lazy_recovery.py`: `timing_summary` passthrough in
  `_build_minimal_runtime_checkpoint_artifact()`, the lightweight artifact
  path used on the ordinary (non-recovery-detail) request path.
- `relaylm/app.py`: `_start_timing()`/`_finalize_timing()` helpers
  (wall-clock ISO timestamps for display, `time.monotonic()` delta for
  `duration_ms`, matching the existing pattern in
  `relaylm/soul_lab_observation.py`); real timing brackets around each of
  the ten live `RUNTIME_CHECKPOINT_NODE_SEQUENCE` nodes' already-existing
  work in `chat_completions()`; `node_timings` threaded through
  `_ManagedRuntimeArtifactContext` and `_build_relayrun_runtime_artifact()`
  into each `_relayrun_*_node()` helper.
- `relaylm/audit_projection.py`: `_RELAYRUN_TIMING_SUMMARY`, a bounded
  numeric/null validator, added to the `_RELAYRUN` projection whitelist so
  `timing_summary` reaches the persisted, content-free audit trace. Per-node
  `node_statuses` (with their own timestamps/`duration_ms`) are not added to
  this whitelist by this slice -- they remain visible only in-process, matching
  this projector's pre-existing scope.
- `scripts/relaylm_lat1_bench_store_generator.py`: generates fully synthetic,
  Primary MEM-shaped stores (front matter + body pages, `index.md`/`log.md`)
  under the gitignored `runtime/bench/` directory only; fail-closed against
  an existing non-empty target directory or an `--out-root` outside
  `runtime/bench/`.
- `scripts/relaylm_lat1_retrieval_bench.py`: calls the real M2 retrieval path
  (`build_relaymem_retrieval_dry_run_artifact`) against generated stores with
  a fixed, seeded 20-query set, computes p50/p95 latency and average
  selected-candidate count, and writes a content-free JSON result file under
  `runtime/bench/results/`. No backend/LLM/network call.
- `docs/evaluation/lat1_retrieval_scaling_report.md`: report template with
  all result cells blank, pending a real local bench run.
- `docs/architecture/lat1_latency_measurement.md`: the slice handoff --
  `timing_summary` schema, exact per-node measured-span definitions, the
  documented `time_to_first_token_ms`/streaming `backend_forward_ms`
  limitation, and the bench reproduction runbook.

## Preserved authorities and non-goals

Preserved authorities:

- Search/ranking/candidate-limit (K) design, degradation-ladder design,
  Secondary MEM integration, SSE/stream behavior, O2/O3 scheduler behavior,
  and TTS/avatar timing are all untouched and remain separate design work.
- The P1 CTX Repack phase ordering and RelayRUN node-sequence fix (PR #476)
  is a prerequisite this slice builds on, not something it re-touches.
- The `_RELAYRUN` audit-projection whitelist's existing scope (only a fixed
  set of top-level scalar fields, no `node_statuses` detail) is preserved;
  this slice only adds one new bounded key (`timing_summary`) to that
  existing whitelist.

Non-goals (explicit, per the slice's own scope):

- no search algorithm, ranking, or candidate-limit (K) change;
- no embedding/ANN/vector DB introduction;
- no degradation ladder, timeout, or node-skip behavior change;
- no Secondary MEM integration;
- no SSE/stream chunk behavior change or per-chunk timing metadata;
- no O2/O3, scheduler, or always-on daemon change;
- no TTS/avatar timing.

## Changed files

- `relaylm/relayrun.py`
- `relaylm/relayrun_lazy_recovery.py`
- `relaylm/app.py`
- `relaylm/audit_projection.py`
- `scripts/relaylm_lat1_bench_store_generator.py`
- `scripts/relaylm_lat1_retrieval_bench.py`
- `scripts/relaylm_lat1_timing_smoke.py`
- `scripts/relaylm_lat1_timing_security_smoke.py`
- `scripts/relaylm_lat1_bench_smoke.py`
- `docs/evaluation/lat1_retrieval_scaling_report.md`
- `docs/architecture/lat1_latency_measurement.md`
- `docs/mvp/wave8/lat1_latency_measurement_completion_report.md`
- `docs/README.md`
- `docs/contracts/README.md`
- `docs/PROJECT_STATUS.md`
- `.gitignore`

## Validation evidence

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_lat1_timing_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_lat1_timing_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_lat1_bench_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave8/lat1_latency_measurement_completion_report.md
```

All of the above pass locally. Regression coverage: every existing
`scripts/relaylm_relayrun_*.py` smoke and `scripts/relaylm_ctx_repack_final_gate_smoke.py`
were re-run before and after this change (`git stash` A/B comparison); the
set of locally-failing smokes (an unrelated environment/dependency-version
gap in this container, reproduced identically on the pre-change tree) is
byte-identical before and after except for random `run_id` values, and one
real regression found during development (`_ManagedRuntimeArtifactContext`
gained a new required field, breaking
`scripts/relaylm_app_orchestration_extract_smoke.py`) was fixed by giving
`node_timings` a `field(default_factory=dict)` default. A full local run of
all 441 scripts under `scripts/` was diffed the same way (excluding the two
new bench CLIs) with the same identical-failure-set result. `discover_relaymem_page_candidates`
was exercised directly against a generated synthetic store to confirm real
M2 retrieval finds candidates in it exactly as it would in a production-shaped
store.

## Known limitations

- `timing_summary.time_to_first_token_ms` is always `null`: the checkpoint
  artifact is fully built and attached to response headers before a
  streaming response begins sending bytes, so first-token timing cannot be
  observed without either delaying the response (a behavior change) or
  wrapping the stream generator and reporting a second, later trace event
  (out of scope for this measurement-only slice).
- For a streaming request, `timing_summary.backend_forward_ms` measures time
  until the backend's response stream opens (headers received), not full
  stream drain, for the same reason.
- `relaylm/relayrun.py`'s `DEFAULT_RELAYRUN_NODE_SEQUENCE` and
  `RelayRunDiagnosticsArtifact` are pre-existing dead code (nothing outside
  `relayrun.py` calls them); this slice times the live
  `RUNTIME_CHECKPOINT_NODE_SEQUENCE` set actually used by `app.py` instead.
  This mismatch predates this slice and is documented, not fixed, here.
- `discover_relaymem_page_candidates`'s internal scan is capped at a fixed
  constant (`_MAX_PRIORITY_DISCOVERY_CANDIDATES = 128`) regardless of store
  size; the retrieval bench may show latency plateauing above that cap
  rather than scaling linearly with N. This is documented as an
  interpretation note, not treated as a bug.
- The retrieval scaling report (`docs/evaluation/lat1_retrieval_scaling_report.md`)
  ships with blank result cells; no real N=100..5000 bench run has been
  recorded yet. This is a template awaiting a maintainer-run local bench.
- Per-node `duration_ms`/`started_at`/`completed_at` are not surfaced through
  the content-free audit-projection whitelist; only the `timing_summary`
  rollup is. Inspecting individual node timing requires a direct call to
  `relaylm.app._build_relayrun_runtime_artifact` (as the new timing smoke
  does), not the persisted trace.

## Shared documentation update inputs

- `docs/PROJECT_STATUS.md` receives one addendum paragraph (after the
  existing Twin Extraction offline-tooling addendum) stating the LAT-1
  addition is measurement only, with no response-time guarantee or
  optimization implemented or claimed.
- `docs/README.md` gains one new bullet under the existing "Offline tooling
  and runbooks" section (added directly by this implementation PR, matching
  the precedent set by the Twin Extraction tooling links already there); no
  existing anchors were removed or reworded. This PR does not add itself to
  the Wave 8 implementation-evidence index; that indexing is left to a future
  convergence pass, consistent with the parallel-implementation documentation
  rule.
- `docs/contracts/README.md` gains one new bullet under "Runtime and compiler
  contracts" for the new `relayrun.timing_summary.v0` schema.
- No RelayMEM/RelaySOUL runtime authority, O2/O3, CW-A4/CW-A5, or RelaySLP
  status changes; this slice does not touch search algorithm, ranking,
  candidate-limit (K), or degradation-ladder design.

## Source pull request

Pending: this slice has not yet been opened as a pull request. This section
must be filled in with a concrete PR number and URL before this report is
treated as final evidence.
