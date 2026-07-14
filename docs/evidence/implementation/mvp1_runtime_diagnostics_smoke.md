---
relaylm_doc_type: evidence
relaylm_authority: mvp1_runtime_diagnostics_smoke_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current diagnostics/API contract
  - current operator instructions
  - exact request diagnostics schema
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 2890b1d13e7a937611e4ca467f761738d2a0082c
relaylm_source_origin_commit: 4a97a4dc730c718d06e567ccfaf47db2d278357d
relaylm_source_pr: 10
relaylm_recorded_on: 2026-05-20
relaylm_source_blob: b5d2f6ff805832f71d89393d06d91c65add3e81c
relaylm_source_content_sha256: c9184d7a3b12c84b6aa3615a976118b9f6fd3c1d739eed1a453631898184acaf
relaylm_pre_cutover_blob: b5d2f6ff805832f71d89393d06d91c65add3e81c
relaylm_pre_cutover_content_sha256: c9184d7a3b12c84b6aa3615a976118b9f6fd3c1d739eed1a453631898184acaf
relaylm_exact_source_snapshot: mvp1_runtime_diagnostics_smoke-source.txt
---
# MVP-1 Runtime Diagnostics Smoke Evidence

This frozen record preserves the early MVP-1 server-free runtime diagnostics smoke as historical implementation evidence. The embedded commands and the described `RequestDiagnostics` header/log fields belong to that source boundary and are not the current diagnostics/API contract.

## Exact source

The submitted source is retained byte-for-byte as [mvp1_runtime_diagnostics_smoke-source.txt](mvp1_runtime_diagnostics_smoke-source.txt).

```text
old path: docs/mvp/mvp1_runtime_diagnostics_smoke.md
source PR: #10, merge 4a97a4dc730c718d06e567ccfaf47db2d278357d
source commit: 2890b1d13e7a937611e4ca467f761738d2a0082c
source blob: b5d2f6ff805832f71d89393d06d91c65add3e81c
source content SHA-256: c9184d7a3b12c84b6aa3615a976118b9f6fd3c1d739eed1a453631898184acaf
disposition: evidence_retained
```

No post-source modification exists; the source blob equals the pre-cutover blob.

## Current authority

`relaylm/diagnostics.py` now owns the current `RequestDiagnostics` implementation, which has grown well beyond this record's original request-id/mode/fallback-reason fields. Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md).
