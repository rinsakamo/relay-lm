---
relaylm_doc_type: implementation_handoff
relaylm_authority: lat1_latency_measurement_boundary_scope
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - the live RelayRUN node set (relaylm.relayrun.RUNTIME_CHECKPOINT_NODE_SEQUENCE) changes
  - the timing_summary schema changes
  - the retrieval bench CLIs' flags, query set, or output schema change
  - stream time-to-first-token measurement becomes possible without behavior change
relaylm_not_authoritative_for:
  - search algorithm, ranking, or candidate-limit (K) design decisions
  - degradation ladder, timeout, or node-skip design
  - repository-wide current implementation status
relaylm_current_status_source: ../PROJECT_STATUS.md
---

# LAT-1 Latency Measurement

## Summary

LAT-1 adds a real-time-measurement foundation for RelayRUN's per-node
timing and an offline M2 retrieval scaling bench. It is measurement only:
no request-path behavior, skip/degrade logic, timeout, or search
algorithm changed. This is the evidence base for later design decisions
(candidate-limit K, ANN adoption, Secondary MEM integration priority),
not those decisions themselves.

## Implemented files

```text
relaylm/relayrun.py               RelayRunNode.duration_ms; build_relayrun_node()
                                   timing params; build_relayrun_timing_summary();
                                   timing_summary param on
                                   build_runtime_checkpoint_dry_run_artifact()
relaylm/relayrun_lazy_recovery.py timing_summary passthrough in
                                   _build_minimal_runtime_checkpoint_artifact()
relaylm/app.py                    _start_timing()/_finalize_timing() helpers;
                                   real per-node timing brackets in
                                   chat_completions(); node_timings threaded
                                   through _ManagedRuntimeArtifactContext and
                                   _build_relayrun_runtime_artifact()
relaylm/audit_projection.py       _RELAYRUN_TIMING_SUMMARY validator; timing_summary
                                   added to the _RELAYRUN projection whitelist
scripts/relaylm_lat1_bench_store_generator.py   synthetic Primary MEM store generator
scripts/relaylm_lat1_retrieval_bench.py         M2 retrieval scaling bench runner
scripts/relaylm_lat1_timing_smoke.py            node timing + timing_summary smoke
scripts/relaylm_lat1_timing_security_smoke.py   content-free timing/bench-output smoke
scripts/relaylm_lat1_bench_smoke.py             minimal generate->bench->schema smoke
docs/evaluation/lat1_retrieval_scaling_report.md  bench report template (results blank)
```

## Live node set this slice times

`relaylm/relayrun.py` defines two node-name sequences. Only one is live:

- `RUNTIME_CHECKPOINT_NODE_SEQUENCE` (`request_received`, `relayrel`, `relayscn`,
  `relayemo`, `relayint`, `relaymem_retrieval`, `relaymem_runtime_ctx`,
  `relayctx_short_term_injection`, `token_budget_truncation`,
  `backend_forward`) is what `relaylm/app.py`'s `chat_completions()` actually
  builds into `node_statuses` on every request. LAT-1 times exactly these ten
  nodes.
- `DEFAULT_RELAYRUN_NODE_SEQUENCE` and `RelayRunDiagnosticsArtifact` (also in
  `relaylm/relayrun.py`) are pre-existing dead code: nothing in `relaylm/`
  outside `relayrun.py` itself imports or calls them. LAT-1 does not wire
  timing into this unused sequence; a future slice would need to either wire
  it up for real or remove it.

## Measured span per node (what is timed, and what is not)

Each node's `started_at`/`completed_at` bracket the real work app.py already
does for that node, not the after-the-fact `_relayrun_*_node()` status
classifier (which only inspects an already-built artifact and cannot time
its own construction):

| node_name | measured span in `app.py` |
|---|---|
| `request_received` | request-id creation through request validation/routing |
| `relayrel` | `build_relayrel_relationship_projection()` call |
| `relayscn` | `build_relayscn_scene_policy_artifact()` call |
| `relayemo` | the RelayEMO block (session-state load/run/save), only when `config.relayemo_enabled`; **untimed (null) when disabled**, matching the existing skip behavior |
| `relayint` | `build_relayint_reference_intent_artifact()` call |
| `relaymem_retrieval` | `build_relaymem_store_diagnostics()` + `build_relaymem_retrieval_dry_run_artifact()` + optional `apply_relaymem_primary_recall_scope()` -- this is the scaling-monitoring primary metric (`timing_summary.retrieval_ms`) |
| `relaymem_runtime_ctx` | `apply_relaymem_runtime_injection_phase()` call |
| `relayctx_short_term_injection` | `apply_relayctx_short_term_runtime_injection_phase()` call |
| `token_budget_truncation` | `apply_token_budget_truncation_phase()` call |
| `backend_forward` | non-stream: the `forward_chat_completion_json()` call. Stream: the `open_chat_completion_stream()` call only -- see limitation below |

`started_at`/`completed_at` are wall-clock ISO 8601 strings
(`datetime.now(timezone.utc).isoformat()`); `duration_ms` is derived from a
`time.monotonic()` delta so it stays correct across a wall-clock adjustment
mid-request. If either timestamp is missing, `duration_ms` is `null` --
`RelayRunNode.to_log_dict()` enforces this defensively regardless of what a
caller passes, so a node can never show a backfilled or guessed duration.

No node's internal behavior, I/O, or control flow changed to add this
timing; the brackets wrap already-existing calls.

## `timing_summary` schema (`relayrun.timing_summary.v0`)

Attached as a new top-level key on the live `relayrun.runtime_checkpoint.v0`
artifact (`node_statuses`' sibling), built by
`relaylm.relayrun.build_relayrun_timing_summary()` from the already-computed
per-node `duration_ms` values -- it performs no timing or I/O of its own.

```text
schema_version            "relayrun.timing_summary.v0"
pipeline_overhead_ms       int, sum of duration_ms over every node with
                           node_status == "completed" except backend_forward
backend_forward_ms         int | null, backend_forward node's own duration_ms
time_to_first_token_ms     always null in this slice -- see limitation below
retrieval_ms               int | null, relaymem_retrieval node's own duration_ms
nodes_timed_count          int, nodes with a non-null duration_ms
nodes_untimed_count        int, nodes with a null duration_ms
```

All fields are numeric, null, or the fixed `schema_version` string --
content-free by construction. `_RELAYRUN_TIMING_SUMMARY` in
`relaylm/audit_projection.py` enforces this shape on the persisted audit
trace; unknown keys or non-numeric values are silently dropped, never
raised or logged as content. Note that per-node `node_statuses` (with their
own `started_at`/`completed_at`/`duration_ms`) are **not** added to the
`_RELAYRUN` projection whitelist by this slice -- they remain visible only
in-process during request handling, matching this projector's pre-existing
scope. Use `docs/evaluation/lat1_retrieval_scaling_report.md`'s reproduction
steps or a direct call to `relaylm.app._build_relayrun_runtime_artifact` to
inspect node-level timing.

## Known limitation: `time_to_first_token_ms` is always null

The RelayRUN checkpoint artifact (including `timing_summary`) is fully built
and attached to response headers *before* a streaming response begins
sending bytes to the client. Because of this, LAT-1 cannot observe "first
token sent" or "stream fully drained" without either delaying the response
(a behavior change) or wrapping the stream generator and reporting the
result in a second, later trace event (out of scope for this
measurement-only slice; see `docs/architecture/phase55b1_stream_suppression_gate_handoff.md`
for the existing ASGI-level "response fully sent" pattern this might reuse).
Consequently:

- `time_to_first_token_ms` is `null` for every request, stream or not.
- For a streaming request, `backend_forward_ms` measures time until the
  backend's response stream opens (headers received), not full stream
  drain. For a non-streaming request, `backend_forward_ms` is the real,
  complete backend response time.

## Offline retrieval scaling bench

`scripts/relaylm_lat1_bench_store_generator.py` builds fully synthetic
Primary MEM-shaped stores (front matter + body pages under
`memory/mem/{primary,secondary}/<kind>/`, plus `index.md`/`log.md`) under
the gitignored `runtime/bench/` directory only. It is a **test fixture
generator**, not a substitute for Primary MEM page issuance authority
(M3e): generated pages never go through page publication, promotion, or
reconciliation, and it refuses (fail-closed) to write into an existing
non-empty directory or outside `runtime/bench/`.

`scripts/relaylm_lat1_retrieval_bench.py` calls the real M2 retrieval path
(`relaylm.relaymem_retrieval.build_relaymem_retrieval_dry_run_artifact`,
the same function `app.py` calls for the `relaymem_retrieval` node) against
each generated store with a fixed, seeded 20-query set, `--repeat` times
each, and writes p50/p95/avg-selected-count JSON under `runtime/bench/results/`.
It makes no backend/LLM/network call. Both `--stores-root` (read) and
`--out-root` (write) are fail-closed the same way as the generator's
`--out-root`: either flag must resolve under `runtime/bench/`, or the bench
refuses to run rather than silently reading from or writing to a
production store root or a configured character store.

Reproduction:

```bash
PYTHONPATH=. python scripts/relaylm_lat1_bench_store_generator.py \
  --sizes 100,500,2000,5000 --out-root runtime/bench/stores

PYTHONPATH=. python scripts/relaylm_lat1_retrieval_bench.py \
  --stores-root runtime/bench/stores --repeat 5
```

**Interpretation note:** `discover_relaymem_page_candidates`'s internal
scan is capped at a fixed constant
(`_MAX_PRIORITY_DISCOVERY_CANDIDATES = 128` in
`relaylm/relaymem_retrieval.py`) regardless of store size or the
`max_candidates` argument. Bench results may plateau above that cap rather
than scale linearly with N -- record what is actually observed in
`docs/evaluation/lat1_retrieval_scaling_report.md` rather than assuming
linear scaling.

## Smoke coverage

- `scripts/relaylm_lat1_timing_smoke.py` -- direct artifact build: every
  timed node has a non-negative int `duration_ms` and both timestamps;
  every untimed node has all three fields `null`; `nodes_timed_count` +
  `nodes_untimed_count` equals the node count. Also drives one request
  through a fake backend and checks the persisted, projected trace record's
  `timing_summary` is present and numeric.
- `scripts/relaylm_lat1_timing_security_smoke.py` -- timing fields and
  `timing_summary` never carry anything but timestamps/ints/null; bench
  result JSON contains only the documented six numeric fields, never query
  text or synthetic page body content.
- `scripts/relaylm_lat1_bench_smoke.py` -- minimal (N=20) generate -> bench
  -> output-schema round trip completes locally in seconds; the generator's
  fail-closed rejection of an existing non-empty store directory is
  exercised directly.

## Non-goals

- No search algorithm, ranking, or candidate-limit (K) change.
- No embedding/ANN/vector DB introduction.
- No degradation ladder, timeout, or node-skip behavior change.
- No Secondary MEM integration.
- No SSE/stream chunk behavior change or per-chunk timing metadata.
- No O2/O3, scheduler, or always-on daemon change.
- No TTS/avatar timing (a later slice once voice-out ships).
