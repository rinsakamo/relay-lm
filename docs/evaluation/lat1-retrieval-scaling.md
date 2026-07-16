---
relaylm_doc_type: evaluation_method
relaylm_authority: lat1_retrieval_scaling_bench_method
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - the bench CLI's query set, repeat count, or candidate limit changes
  - the M2 retrieval discovery cap or scaling behavior changes
  - the interpretation method for a completed run changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - search algorithm, ranking, or candidate-limit design decisions
  - any specific dated retrieval-scaling result
  - repository-wide completion status
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/lat1_latency_measurement.md
  - ../templates/evaluation/lat1-retrieval-scaling-report.md
---

# LAT-1 Retrieval Scaling Method

## Purpose

This document owns the repeatable method for measuring M2 retrieval
(`build_relaymem_retrieval_dry_run_artifact`) latency against synthetic
Primary MEM stores of increasing size. It defines how to reproduce a run,
what to record, and how to interpret the result. It does not itself
record a result: no real N=100/500/2000/5000 run has been measured through
this method, and this document must not be read as claiming one has.

Completing a run does not change search algorithm, ranking, or
candidate-limit (K) design; those remain separate design decisions this
method can inform.

## Prerequisites

- A local RelayLM checkout with `relaylm` importable (`PYTHONPATH=.`).
- Enough free disk space and time to generate synthetic stores up to the
  largest configured size under the gitignored `runtime/bench/` directory.
- No production Primary MEM store, character workspace, or backend/LLM
  connection is required; both commands below are local-only, bounded,
  fully synthetic, and never call a backend.

## How to reproduce

```bash
PYTHONPATH=. python scripts/relaylm_lat1_bench_store_generator.py \
  --sizes 100,500,2000,5000 --out-root runtime/bench/stores

PYTHONPATH=. python scripts/relaylm_lat1_retrieval_bench.py \
  --stores-root runtime/bench/stores --repeat 5
```

Both commands write exclusively under the gitignored `runtime/bench/`
directory and refuse (fail-closed) to read from or write to a production
store root or a configured character store. See
[LAT-1 Latency Measurement](../architecture/lat1_latency_measurement.md)
for what each command does and does not measure, and for the
`timing_summary.retrieval_ms` field this bench is meant to inform.

## Expected generated artifact

A completed run writes `runtime/bench/results/lat1_retrieval_bench_results.json`,
a content-free JSON file with `query_count`, `repeat`, `p50_ms`, `p95_ms`, and
`avg_selected_count` per store size. This file is local-only and gitignored;
it is not itself an evidence record.

## Measurement fields

Record the reference configuration used for a run, since retrieval latency
is sensitive to hardware, filesystem, and concurrent load:

- Date
- Machine / CPU
- Filesystem (e.g. local SSD, network mount, container overlay)
- Python version
- `relaylm` commit / branch
- `--repeat`
- `--max-candidates` (bench flag; mirrors `config.memory.candidate_limit`)
- Concurrent load on the machine during the run

Per store size (N): `query_count`, `repeat`, `p50_ms`, `p95_ms`,
`avg_selected_count`.

## Interpretation method

M2 retrieval's file-scan primitive (`discover_relaymem_page_candidates`)
caps its own directory scan at a fixed internal discovery limit
(`_MAX_PRIORITY_DISCOVERY_CANDIDATES` in `relaylm/relaymem_retrieval.py`)
regardless of the `max_candidates` argument passed in. This means retrieval
latency is not necessarily linear in N above that cap -- it may plateau.
Interpretation of a completed run must record what was actually observed,
not an assumption:

- Estimated slope (ms per additional 1000 store pages), from `p50_ms`
  deltas between adjacent N values.
- Whether `p50_ms`/`p95_ms` continues increasing beyond the internal
  discovery cap, or plateaus.
- If it plateaus, at approximately which N.

## Plateau and felt-limit evaluation method

Interpretation of a completed run must also record a judgment call, not
just raw numbers: at what store size N does retrieval latency become large
enough to matter for the user-perceived response time budget (see
`pipeline_overhead_ms` and `retrieval_ms` in the RelayRUN `timing_summary`,
described in
[LAT-1 Latency Measurement](../architecture/lat1_latency_measurement.md))?

- Felt limit N.
- Basis for this judgment (e.g. percentage of a target response-time
  budget consumed by `retrieval_ms` at that N).
- Implication for candidate-limit (K), ANN adoption, or Secondary MEM
  integration priority (design decision only; not made by this method or
  any single run).

## Recording a completed run

A completed run is evidence, not method, and does not live here. Use
[LAT-1 Retrieval Scaling Report Template](../templates/evaluation/lat1-retrieval-scaling-report.md)
to fill in a dated record, then commit it under
`docs/evidence/evaluations/` using a deterministic dated name. This
document is not updated with per-run results.

## Non-goals

- No search algorithm, ranking, or candidate-limit (K) change.
- No embedding/ANN/vector DB introduction.
- No claim that a real scaling result has been recorded by this document.
- No production Primary MEM store, character workspace, or backend/LLM
  behavior change.
