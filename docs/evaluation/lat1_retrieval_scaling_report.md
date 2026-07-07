---
relaylm_doc_type: evaluation_record
relaylm_authority: lat1_retrieval_scaling_bench_evidence
relaylm_status: target
relaylm_volatility: high
relaylm_owner: evaluation
relaylm_update_trigger:
  - a real LAT-1 retrieval scaling bench run is recorded here
  - the bench CLI's query set, repeat count, or candidate limit changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - search algorithm, ranking, or candidate-limit design decisions
  - repository-wide completion status
relaylm_current_status_source: ../PROJECT_STATUS.md
---

# LAT-1 Retrieval Scaling Report

This report records real, locally-run measurements of M2 retrieval
(`build_relaymem_retrieval_dry_run_artifact`) latency against synthetic
Primary MEM stores of increasing size. It is evaluation evidence only. It
does not change search algorithm, ranking, or candidate-limit (K) design;
those remain separate design decisions this report can inform.

Results below are a template. They are blank until a maintainer runs the
bench locally and records real numbers. This file must not be read as
current-status authority while results are unfilled.

## How to reproduce

```bash
PYTHONPATH=. python scripts/relaylm_lat1_bench_store_generator.py \
  --sizes 100,500,2000,5000 --out-root runtime/bench/stores

PYTHONPATH=. python scripts/relaylm_lat1_retrieval_bench.py \
  --stores-root runtime/bench/stores --repeat 5
```

Both commands are local-only, bounded, and write exclusively under the
gitignored `runtime/bench/` directory. See
[LAT-1 Latency Measurement](../architecture/lat1_latency_measurement.md) for
what each command does and does not measure.

## Execution environment

Record the reference configuration used for the run below before filling in
results, since retrieval latency is sensitive to hardware, filesystem, and
concurrent load.

| Field | Value |
|---|---|
| Date | Not yet measured. |
| Machine / CPU | Not yet measured. |
| Filesystem (e.g. local SSD, network mount, container overlay) | Not yet measured. |
| Python version | Not yet measured. |
| `relaylm` commit / branch | Not yet measured. |
| `--repeat` | Not yet measured. |
| `--max-candidates` (bench flag; mirrors `config.memory.candidate_limit`) | Not yet measured. |
| Concurrent load on the machine during the run | Not yet measured. |

## Results by store size (N)

| N (store size) | query_count | repeat | p50_ms | p95_ms | avg_selected_count |
|---|---|---|---|---|---|
| 100 | 20 | - | Not yet measured. | Not yet measured. | Not yet measured. |
| 500 | 20 | - | Not yet measured. | Not yet measured. | Not yet measured. |
| 2000 | 20 | - | Not yet measured. | Not yet measured. | Not yet measured. |
| 5000 | 20 | - | Not yet measured. | Not yet measured. | Not yet measured. |

Paste the contents of `runtime/bench/results/lat1_retrieval_bench_results.json`
(or the equivalent rows) into the table above after a real run.

## Linear scaling coefficient estimate

M2 retrieval's file-scan primitive (`discover_relaymem_page_candidates`) caps
its own directory scan at a fixed internal discovery limit
(`_MAX_PRIORITY_DISCOVERY_CANDIDATES` in `relaylm/relaymem_retrieval.py`)
regardless of the `max_candidates` argument passed in. This means retrieval
latency is not necessarily linear in N above that cap -- it may plateau. Use
this section to record what was actually observed, not an assumption:

- Estimated slope (ms per additional 1000 store pages), from `p50_ms` deltas
  between adjacent N values: Not yet measured.
- Does `p50_ms`/`p95_ms` continue increasing beyond the internal discovery
  cap, or plateau? Not yet measured.
- If it plateaus, at approximately which N does it plateau? Not yet measured.

## "Felt limit N" judgment

Use this section to record a judgment call, not just raw numbers: at what
store size N does retrieval latency become large enough to matter for the
user-perceived response time budget (see `pipeline_overhead_ms` and
`retrieval_ms` in the RelayRUN `timing_summary`, described in
[LAT-1 Latency Measurement](../architecture/lat1_latency_measurement.md))?

- Felt limit N: Not yet measured.
- Basis for this judgment (e.g. percentage of a target response-time budget
  consumed by `retrieval_ms` at that N): Not yet measured.
- Implication for candidate-limit (K), ANN adoption, or Secondary MEM
  integration priority (design decision only; not made in this report):
  Not yet measured.
