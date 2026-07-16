---
relaylm_doc_type: template
relaylm_authority: non_authoritative_lat1_retrieval_scaling_report_template
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - the LAT-1 retrieval scaling method's measurement fields change
  - the evidence-collection destination or naming convention changes
relaylm_not_authoritative_for:
  - any specific dated retrieval-scaling result
  - repeatable evaluation method
  - current runtime implementation status
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
relaylm_related_authority:
  - ../../evaluation/lat1-retrieval-scaling.md
---

# LAT-1 Retrieval Scaling Report Template

This is a **non-authoritative template**, not evidence. It carries no
measured conclusion and no record of any real run. Every placeholder below
must be replaced with a real value before the filled-in copy is treated as
evidence.

## Use rules

- Replace every `<placeholder>` cell with a real, locally-measured value.
  A cell still reading `<placeholder>` is not a completed record.
- Follow the reproduction steps and interpretation method in
  [LAT-1 Retrieval Scaling Method](../../evaluation/lat1-retrieval-scaling.md);
  this template does not repeat that method's field definitions or
  reproduction commands.
- A completed run is a **distinct, dated evidence record**. Save the
  filled-in copy under `docs/evidence/evaluations/` using a deterministic
  dated name that does not overwrite a prior run, for example
  `docs/evidence/evaluations/lat1-retrieval-scaling-YYYY-MM-DD.md`. Do not
  edit this template in place to record a result, and do not overwrite an
  earlier dated record with a later run.
- This template itself is never evidence and carries no measured
  conclusion, regardless of how many placeholder cells are filled in a
  draft copy.
- Do not commit content-bearing or private runtime data (query text,
  synthetic-store page bodies, machine-identifying detail beyond what the
  execution-environment fields ask for). The bench CLIs already write only
  content-free JSON; do not paste anything beyond the documented six
  numeric fields per store size.

## Execution environment

| Field | Value |
|---|---|
| Date | `<placeholder>` |
| Machine / CPU | `<placeholder>` |
| Filesystem (e.g. local SSD, network mount, container overlay) | `<placeholder>` |
| Python version | `<placeholder>` |
| `relaylm` commit / branch | `<placeholder>` |
| `--repeat` | `<placeholder>` |
| `--max-candidates` (bench flag; mirrors `config.memory.candidate_limit`) | `<placeholder>` |
| Concurrent load on the machine during the run | `<placeholder>` |

## Results by store size (N)

| N (store size) | query_count | repeat | p50_ms | p95_ms | avg_selected_count |
|---|---|---|---|---|---|
| 100 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |
| 500 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |
| 2000 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |
| 5000 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |

Paste the contents of `runtime/bench/results/lat1_retrieval_bench_results.json`
(or the equivalent rows) into the table above after a real run.

## Linear scaling coefficient estimate

- Estimated slope (ms per additional 1000 store pages): `<placeholder>`
- Does `p50_ms`/`p95_ms` continue increasing beyond the internal discovery
  cap, or plateau? `<placeholder>`
- If it plateaus, at approximately which N does it plateau? `<placeholder>`

## Felt limit N judgment

- Felt limit N: `<placeholder>`
- Basis for this judgment: `<placeholder>`
- Implication for candidate-limit (K), ANN adoption, or Secondary MEM
  integration priority (design decision only; not made in this report):
  `<placeholder>`

## Source pull request

- PR: `<placeholder>`
- URL: `<placeholder>`
