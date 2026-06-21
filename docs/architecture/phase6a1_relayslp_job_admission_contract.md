---
relaylm_doc_type: implementation_contract
relaylm_authority: phase6a1_relayslp_job_admission
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-A1 helper schema or status vocabulary changes
  - Phase 6-A2 response-finalization handoff lands
relaylm_not_authoritative_for:
  - RelayMEM memory candidate semantics
  - durable queue or worker execution
  - memory persistence apply
  - RelaySOUL mutation
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - relaymem_slp_current_target.md
  - relaymem_mvp_implementation_plan.md
---
# Phase 6-A1 RelaySLP Job Admission Contract

## Implemented boundary

Phase 6-A1 adds the helper-only `build_relaymem_slp_job_admission_preflight(...)` boundary in `relaylm/relaymem_slp_job_admission.py`.

It validates bounded deferred-job metadata and a content-free `relaymem.primary_source_lineage.v0` artifact. It does not enqueue work, invoke a worker, invoke RelaySLP, write memory, mutate RelaySOUL, or change visible response delivery.

Implemented private and projection schemas:

```text
relaymem.slp_job_admission_preflight.v0
relaymem.slp_job_admission_projection.v0
```

Initially supported triggers:

```text
turn_end
explicit_memory_request
```

Initially supported processing stages:

```text
primary_formation
primary_write_preflight
```

Implemented outcomes:

```text
skipped
blocked
held
admitted_dry_run
eligible_for_enqueue
```

`eligible_for_enqueue` is structural eligibility only. Phase 6-A1 performs no queue I/O and creates no durable job.

## Safety boundary

The helper is default-off, dry-run-first, and fail-closed. It validates correlation, namespace, source count, source event kind, runtime terminal state, visible-response finalization for `turn_end`, persistence-policy status, and the upstream lineage schema.

The public projection excludes runtime-private identifiers, lineage fingerprints, dispatch idempotency keys, memory-write idempotency keys, raw text, prompts, messages, snippets, page content, patches, candidate arrays, filesystem paths, and RelaySOUL content.

Phase 6-A1 does not create either idempotency layer:

- dispatch idempotency remains a later Phase 6 queue/orchestration responsibility;
- memory-write idempotency remains RelayMEM write-preflight/persistence responsibility.

## Next boundary

Phase 6-A2 may add a default-off, dry-run-only response-finalization handoff that consumes the A1 decision and creates a bounded enqueue candidate without queue I/O. A2 must not be inferred as implemented by this contract.
