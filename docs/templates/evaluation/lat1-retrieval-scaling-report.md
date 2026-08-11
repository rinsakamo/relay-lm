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
  - ../../operations/lat1-retrieval-scaling.md
---

# LAT-1 Retrieval Scaling Report Template

This is a **non-authoritative template**, not evidence. It carries no
measured conclusion and no record of any real run. Every placeholder below
must be replaced with a real value before the filled-in copy is treated as
evidence.

**Copying and filling in this file's body is not sufficient by itself.**
A filled-in copy is only a completed evidence record once it also replaces
this template's own front matter (`relaylm_doc_type: template`,
`relaylm_status: target`, this shared non-authoritative authority key) with
the canonical evidence front matter below, is saved under
`docs/evidence/evaluations/` using the deterministic collision-safe naming
convention, and passes the repository's `check_lat1_evaluation_evidence_records`
semantic-audit check. A body with every cell filled in but the template's
own front matter left unchanged is still a template, not evidence.

## Canonical front matter for a completed record

Do not keep this template's own front matter in a completed copy. Replace
it with front matter of this shape, replacing every placeholder value with
a concrete one:

```yaml
---
relaylm_doc_type: evidence
relaylm_authority: lat1_retrieval_scaling_run_<YYYY-MM-DD>_<short-commit>
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current runtime implementation status
  - repeatable evaluation methodology
  - repository-wide implementation status
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: <exact 40-character lowercase RelayLM commit SHA>
relaylm_source_pr: <source PR number, or omit this key entirely if none>
relaylm_recorded_on: <YYYY-MM-DD>
relaylm_related_authority:
  - ../../operations/lat1-retrieval-scaling.md
---
```

- `relaylm_doc_type` must be `evidence` -- never `evaluation_record` (a
  retired, existing-only pre-cutover type) and never left as `template`.
- `relaylm_authority` must be specific to this one dated run, not shared
  with the method's `lat1_retrieval_scaling_bench_method` authority or this
  template's own `non_authoritative_lat1_retrieval_scaling_report_template`
  authority, and not reused by any other completed record.
  `lat1_retrieval_scaling_run_<date>_<short-commit>` is a deterministic,
  collision-safe pattern for this.
- `relaylm_status` must be `frozen` (or `historical` once a later
  authoritative source supersedes it) -- the canonical evidence statuses
  this documentation model requires, never `target` or `current`.
  `relaylm_owner` must be `evaluation`.
- `relaylm_recorded_on` must be a concrete `YYYY-MM-DD` date, matching the
  date embedded in the filename below.
- `relaylm_source_commit` must be the exact 40-character lowercase RelayLM
  commit SHA the run was measured against -- a branch name alone is not
  sufficient, since branches move and a SHA does not.
- `relaylm_source_pr` records the source pull request when this run was
  produced as part of one; omit the key entirely when there is none.
- `relaylm_related_authority` must link back to the canonical
  [LAT-1 Retrieval Scaling Method](../../operations/lat1-retrieval-scaling.md),
  which owns the reproduction procedure and interpretation method this
  record does not repeat.

## Use rules

- Replace every `<placeholder>` cell with a real, locally-measured value.
  A cell still reading `<placeholder>`, `TBD`, or `Not yet measured` is not
  a completed record.
- Follow the reproduction steps and interpretation method in
  [LAT-1 Retrieval Scaling Method](../../operations/lat1-retrieval-scaling.md);
  this template does not repeat that method's field definitions or
  reproduction commands.
- A completed run is a **distinct, dated evidence record**. Save the
  filled-in copy under `docs/evidence/evaluations/` using the deterministic,
  collision-safe naming convention
  `lat1-retrieval-scaling-YYYY-MM-DD-HHMMSSZ-<short-commit>.md` (UTC
  timestamp plus a short commit prefix). Do not use a date-only filename:
  two runs performed on the same date would silently collide and one would
  overwrite the other. Do not edit this template in place to record a
  result.
- This template itself is never evidence and carries no measured
  conclusion, regardless of how many placeholder cells are filled in a
  draft copy, until its front matter is also replaced as described above.
- Do not commit content-bearing or private runtime data (query text,
  synthetic-store page bodies, machine-identifying detail beyond what the
  execution-environment fields ask for, credentials, or tokens). The bench
  CLIs already write only content-free JSON; do not paste anything beyond
  the documented numeric fields per store size.

## Execution environment

| Field | Value |
|---|---|
| Date | `<placeholder>` |
| Machine / CPU | `<placeholder>` |
| Filesystem (e.g. local SSD, network mount, container overlay) | `<placeholder>` |
| Python version | `<placeholder>` |
| Exact RelayLM commit SHA | `<placeholder>` |
| Branch or tag (optional context only) | `<placeholder>` |
| `--repeat` | `<placeholder>` |
| `--max-candidates` (bench flag; mirrors `config.memory.candidate_limit`) | `<placeholder>` |
| Concurrent load on the machine during the run | `<placeholder>` |

The exact RelayLM commit SHA row is mandatory and must be a full
40-character lowercase SHA, matching `relaylm_source_commit` above. The
branch or tag row is optional context only -- a branch name never
substitutes for the exact commit SHA, since a branch moves and a run must
remain reproducible against the exact commit it was measured on.

## Results by store size (N)

| N (store size) | query_count | repeat | p50_ms | p95_ms | avg_selected_count |
|---|---|---|---|---|---|
| 100 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |
| 500 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |
| 2000 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |
| 5000 | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` | `<placeholder>` |

Paste the contents of `runtime/bench/results/lat1_retrieval_bench_results.json`
(or the equivalent rows) into the table above after a real run. Every cell
must be a real non-negative number, and `p95_ms` must be greater than or
equal to `p50_ms` for each row.

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
