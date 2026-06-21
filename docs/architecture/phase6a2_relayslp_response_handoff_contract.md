---
relaylm_doc_type: implementation_contract
relaylm_authority: phase6a2_relayslp_response_handoff
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6-A2 helper schema or status vocabulary changes
  - Phase 6-B durable queue boundary lands
relaylm_not_authoritative_for:
  - RelayMEM candidate semantics
  - durable queue persistence
  - dispatch idempotency generation
  - worker execution
  - memory persistence apply
  - RelaySOUL mutation
relaylm_related_authority:
  - phase6_async_relayslp_bounded_slice.md
  - phase6a1_relayslp_job_admission_contract.md
  - pipeline_implementation_plan.md
  - relaymem_slp_current_target.md
---
# Phase 6-A2 RelaySLP Response-Finalization Handoff Contract

## Implemented boundary

Phase 6-A2 adds the helper-only `build_relaymem_slp_response_finalization_handoff(...)` boundary in `relaylm/relaymem_slp_response_handoff.py`.

It consumes one exact `relaymem.slp_job_admission_preflight.v0` result from Phase 6-A1 and may create one runtime-private metadata-only enqueue candidate after a finalized `turn_end` response.

Implemented schemas:

```text
relaymem.slp_response_handoff.v0
relaymem.slp_enqueue_candidate.v0
relaymem.slp_response_handoff_projection.v0
```

The initial handoff supports only:

```text
trigger_mode = turn_end
processing_stage = primary_formation | primary_write_preflight
source_event_kind = turn
```

`explicit_memory_request` remains admitted by A1 where valid, but is not a response-finalization trigger and therefore does not create an A2 candidate.

## Source validation

A2 requires the exact A1 private-result field set and schema version. It also requires the exact `relaymem.slp_job_admission_projection.v0` field set, strict projection booleans, exact correlation-presence keys, and equality between the A1 private result and its public projection for all shared status, enum, count, gate, policy, and reason fields.

A2 rejects:

- unknown or missing private-result or projection fields,
- non-boolean control or projection flags,
- unknown or non-string source statuses,
- projection/private-result mismatches,
- malformed or inconsistent correlation-presence metadata,
- prior queue I/O, enqueue, worker, RelaySLP, memory-write, RelaySOUL, or visible-response side effects,
- pre-existing dispatch or memory-write idempotency keys,
- inconsistent accepted-source gates,
- malformed correlation, namespace, count, lineage fingerprint, terminal status, or persistence-policy metadata.

The validator does not recursively traverse caller-controlled projection values. Fixed allowlists and direct type checks reject nested or content-bearing substitutions.

A1 `blocked`, `held`, and `skipped` statuses are propagated without producing a candidate. A2 retains the validated source trigger, processing stage, source-event kind, source count, correlation-presence booleans, and response-finalization signal independently of candidate creation so blocked or held diagnostics remain accurate.

The dedicated A2 CI workflow is also triggered when the A1 admission helper changes, because exact A1 result/projection drift is part of the A2 compatibility contract.

## Candidate boundary

A candidate is produced only when:

- A2 is explicitly enabled,
- A2 remains `dry_run_only=true`,
- the response-finalization signal is true,
- A1 status is `admitted_dry_run` or `eligible_for_enqueue`,
- the A1 source is a valid finalized `turn_end` result,
- the source lineage and persistence-policy gates remain valid.

The runtime-private candidate contains only bounded orchestration metadata and protected references. It contains no raw user/model text, visible response text, prompts, snippets, page content, patches, memory values, filesystem paths, or RelaySOUL content.

## No queue or apply behavior

Phase 6-A2 does not:

- perform queue I/O,
- durably enqueue a job,
- allocate a dispatch idempotency key,
- claim or lease work,
- invoke a worker or RelaySLP,
- generate or apply Primary/Secondary MEM writes,
- use the RelayMEM memory-write idempotency key,
- mutate RelaySOUL,
- delay, replace, or invalidate the finalized visible response.

The candidate always records:

```text
enqueue_requested = false
queue_io_performed = false
enqueued = false
worker_invoked = false
writes_memory = false
mutates_soul = false
changes_visible_response = false
dispatch_idempotency_key = ""
memory_write_idempotency_key = ""
```

## Public projection

`build_relaymem_slp_response_handoff_node_result(...)` emits the content-free `relaymem_slp_response_handoff` node result.

The public projection includes only status, bounded counts/enums, validated source correlation-presence booleans, finalization state, and reason IDs. These source fields remain present when a validated A1 result is held, blocked, skipped, or rejected by the A2 dry-run/finalization gate even though no candidate is created. The projection excludes the runtime-private candidate, run/session identifiers, namespace values, lineage fingerprints, and both idempotency-key domains.

## Next boundary

The next Phase 6 boundary is Phase 6-B: a separately designed bounded durable queue with dispatch idempotency and enqueue/claim/lease/terminal-state semantics. Phase 6-A2 must not be interpreted as implementing that queue.
