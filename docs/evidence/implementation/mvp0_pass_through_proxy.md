---
relaylm_doc_type: evidence
relaylm_authority: mvp0_pass_through_proxy_evidence
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_not_authoritative_for:
  - current proxy, config, or operator behavior
  - current request pipeline responsibility
  - exact runtime contracts
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 5b164e0deb371c9c8de0d3b7c57f38084077e2dc
relaylm_recorded_on: 2026-05-20
relaylm_source_blob: 9bd2eb600ae7586a337e58c19bdb868d1c3d1e4f
relaylm_source_content_sha256: bad628ffc3748fe0ae41c704960eb087b0402ef4ebf905d5542f98929f8e10a2
---
# MVP-0 Pass-through Proxy Evidence

This frozen record preserves the early MVP-0 URL-swap pass-through proxy skeleton as historical implementation evidence. Its install/run commands, config example, and "preserved seams" statements belong to that source boundary and are not current proxy, config, or operator authority.

## Exact source

The submitted source is retained byte-for-byte as [mvp0_pass_through_proxy-source.txt](mvp0_pass_through_proxy-source.txt).

```text
old path: docs/mvp/mvp0_pass_through_proxy.md
source PR: #4 (rinsakamo/mvp0-pass-through-proxy), merge eab60e55d9c3899ca54be473faed2d8bafff4c60
source commit: 5b164e0deb371c9c8de0d3b7c57f38084077e2dc
source blob: 5a98f4066458a34a34ff6e88c4a651ac77b59722
post-source modification: PR #5 (rinsakamo/mvp0-offline-install-docs), merge 1d5e23ae4d64d6aec1292bf737f5272219ddf5ba, commit 5d2e9f0665e9ff840327ae093dc48fdddd6e7dd8
pre-cutover blob: 9bd2eb600ae7586a337e58c19bdb868d1c3d1e4f
pre-cutover content SHA-256: bad628ffc3748fe0ae41c704960eb087b0402ef4ebf905d5542f98929f8e10a2
disposition: evidence_retained
```

PR #5 added an offline `pip install -e . --no-build-isolation` fallback and a `python -m relaylm.app` direct-run fallback after PR #4's initial skeleton; both PRs are pre-cutover history for this one record. No modification occurred between PR #5 and the pre-cutover snapshot above.

## Current authority

Current request-pipeline responsibility and ordering belong to [Pipeline Responsibility Design](../../architecture/pipeline_responsibility_design.md) and [Runtime Architecture](../../architecture/runtime_architecture.md). Repository-wide current implementation status remains owned by [Project Status](../../PROJECT_STATUS.md). This record does not describe current memory, RAG, SOUL, or context-compilation behavior, all of which were explicitly out of scope for MVP-0.
