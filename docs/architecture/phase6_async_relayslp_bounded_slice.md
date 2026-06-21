---
relaylm_doc_type: implementation_plan
relaylm_authority: phase6_async_relayslp_bounded_slice
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - Phase 6 RelaySLP slice lands
  - deferred job admission or orchestration semantics change
  - RelayMEM-M3 or M4 producer consumer boundary changes
  - RelayRUN retry checkpoint or idempotency ownership changes
relaylm_not_authoritative_for:
  - RelayMEM candidate semantic classification
  - exact durable MEM page index or log schemas
  - RelaySOUL approval or revision schemas
  - SOUL Lab runtime TTS audio or avatar execution
relaylm_related_authority:
  - pipeline_implementation_plan.md
  - relaymem_mvp_implementation_plan.md
  - relaymem_slp_execution_design.md
  - relaymem_slp_current_target.md
  - memory_lifecycle_design.md
  - relayrun_runtime_checkpoint_design.md
  - ../PROJECT_STATUS.md
---
# Phase 6 Asynchronous RelaySLP Bounded Slice

## Status

Phase 6 is planned. This document defines the first bounded implementation sequence after Phase 5.5 closes for RelayLM Core.

The first implementation boundary is:

```text
Phase 6-A0 documentation boundary
  -> Phase 6-A1 deferred RelaySLP job-admission preflight helper
```

Phase 6-A0 is docs-only. Phase 6-A1 must remain helper-only, default-off, dry-run-first, fail-closed, and free of persistence or request-runtime wiring.

## Purpose

RelaySLP is the deferred memory compiler. It improves future memory after the normal response path and must not delay or invalidate an already valid visible response.

Phase 6 introduces the asynchronous orchestration boundary around RelaySLP without duplicating the independent RelayMEM-M track's memory semantics or persistence preflight.

```text
completed or eligible runtime event
  -> deferred SLP job admission preflight
  -> admitted / held / blocked / skipped
  -> later queue and worker boundary
  -> RelayMEM-owned candidate or persistence processing
```

The initial slice defines whether a future deferred job is structurally admissible. It does not execute the job.

## Ownership split

### RelayMEM-M owns memory semantics

The independent RelayMEM-M track owns:

- Primary MEM candidate classification,
- memory kind and safety scope,
- RelaySCN persistence-policy interpretation,
- RelayEMO salience metadata interpretation,
- Primary MEM source lineage and write preflight,
- memory-write idempotency,
- Primary-to-Secondary MEM consolidation semantics,
- durable page, index, and log formats and apply primitives.

Phase 6 must consume these bounded artifacts when their producers exist. It must not independently redefine them.

### Phase 6 owns deferred execution orchestration

Phase 6 owns:

- deferred job admission,
- trigger and processing-stage classification,
- run, turn, session, and namespace correlation,
- dispatch idempotency,
- enqueue, claim, lease, retry, and terminal-state orchestration in later slices,
- content-free job status projections,
- RelayRUN checkpoint and retry integration in later slices,
- ensuring visible response delivery remains independent from SLP execution.

### RelayRUN owns control state, not memory meaning

RelayRUN may own job correlation, node state, checkpoint state, retry eligibility, and duplicate-dispatch prevention. It must not decide memory meaning, candidate safety scope, page content, consolidation meaning, or SOUL mutation eligibility.

### RelaySLP does not mutate SOUL

RelaySLP may produce a RelaySOUL proposal candidate through a separately governed path. It must never write RelaySOUL files or apply identity, values, output-policy, or relationship-anchor changes directly.

## Relationship to RelayMEM-M3b

RelayMEM-M3b is the Primary MEM write-preflight boundary. It owns content-free source-lineage validation, bounded target classification, autonomous-apply eligibility, and memory-write idempotency.

Phase 6-A must not duplicate those responsibilities.

The two idempotency layers are distinct:

```text
Dispatch idempotency
  prevents the same deferred SLP job from being enqueued or claimed twice
  owned by Phase 6 orchestration / RelayRUN control state

Memory-write idempotency
  prevents the same candidate or page update from being durably applied twice
  owned by RelayMEM write preflight and persistence apply
```

A job may be retried while a previously completed memory write must remain deduplicated. Therefore these keys must not be collapsed into one artifact or treated as interchangeable.

## Phase 6-A1: deferred job-admission preflight

### Goal

Define a pure helper that decides whether a deferred RelaySLP job request is structurally admissible without enqueueing, executing, or persisting anything.

Suggested module:

```text
relaylm/relaymem_slp_job_admission.py
```

Suggested entry point:

```text
build_relaymem_slp_job_admission_preflight(...)
```

The exact function and schema names remain implementation details until the helper lands.

### Initial inputs

The helper should accept only bounded metadata and protected references, not arbitrary runtime dumps:

- explicit `enabled` and `dry_run_only` gates,
- trigger mode,
- requested processing stage,
- run and turn correlation,
- optional session correlation,
- memory namespace,
- source event kind,
- governed evidence or source-lineage reference presence,
- upstream artifact schema/version,
- bounded source count,
- visible-response finalization state,
- runtime terminal status,
- persistence-policy class or upstream policy status.

Runtime-private references or fingerprints must not appear in the public projection.

### Trigger modes

The target trigger vocabulary is:

```text
turn_end
explicit_memory_request
session_end
communication_end
scheduled_consolidation
recovery_followup
lab_memory_operation
```

Phase 6-A1 should initially allow only the smallest justified subset, preferably:

```text
turn_end
explicit_memory_request
```

Unknown or unsupported trigger modes must fail closed.

### Processing stages

The target processing-stage vocabulary is:

```text
primary_formation
primary_write_preflight
secondary_consolidation
memory_operation
lint
```

The admission helper transports and validates the stage identifier. It must not implement the stage's memory semantics.

### Admission outcomes

The bounded status vocabulary should distinguish at least:

```text
skipped
blocked
held
admitted_dry_run
eligible_for_enqueue
```

`eligible_for_enqueue` does not mean that a queue, worker, or persistence apply exists. It means only that later enqueue wiring may proceed when all explicit gates exist.

### Required blocking

Admission must block when:

- the feature is disabled,
- the trigger or processing stage is unknown,
- required correlation or namespace metadata is malformed,
- required governed evidence or source lineage is absent,
- the upstream artifact schema is unsupported,
- the visible response is not in a safe terminal state for a turn-end trigger,
- runtime status indicates blocked, failed, waiting-user, or unresolved recovery unless that trigger is explicitly supported,
- RelaySCN or upstream policy blocks persistence,
- input attempts to supply raw user, model, prompt, snippet, page, or SOUL content through the admission metadata surface.

The helper must not infer persistence permission from successful visible output alone.

## Content-free projection

The public node-result or diagnostics projection may expose only bounded allowlisted fields such as:

- schema version,
- enabled and dry-run booleans,
- admission status,
- trigger-mode enum,
- processing-stage enum,
- bounded source count,
- correlation-presence booleans,
- source-reference-valid boolean,
- visible-response-finalized boolean,
- retry class,
- blocked reason IDs.

It must not expose:

- raw user or model text,
- visible response text,
- prompt or backend payload content,
- candidate normalized values,
- memory page titles, bodies, summaries, snippets, or patches,
- filesystem paths,
- source fingerprints or lineage identifiers,
- dispatch or memory-write idempotency keys,
- RelaySOUL content,
- runtime-private candidate arrays.

## Phase 6-A1 non-goals

Phase 6-A1 does not implement:

- request-runtime wiring,
- a background thread, process, scheduler, or worker,
- filesystem or database job queues,
- enqueue delivery,
- claim or lease state,
- Primary MEM candidate generation,
- Primary MEM write preflight,
- Primary or Secondary MEM writes,
- Secondary MEM consolidation,
- page, index, or log updates,
- generic RelayRUN resume or retry apply,
- RelaySOUL proposal generation or mutation,
- SOUL Lab memory APIs,
- TTS, audio, transport delivery, Live2D, avatar, or lip-sync behavior.

## Later bounded sequence

```text
Phase 6-A0
  documentation and ownership boundary

Phase 6-A1
  helper-only deferred job-admission preflight

Phase 6-A2
  response-finalization handoff
  default-off and dry-run-only
  creates an enqueue candidate without queue I/O

Phase 6-B
  bounded durable queue
  dispatch idempotency
  enqueue / claim / lease / terminal states

Phase 6-C
  worker execution
  invokes RelayMEM-owned Primary formation, write preflight, or Secondary consolidation artifacts

Phase 6-D
  gated page/index/log persistence apply
  memory-write idempotency
  partial-failure and reconciliation handling

Phase 6-E
  RelayRUN checkpoint, retry budget, restart recovery, and terminal-failure integration
```

Each later slice requires its own explicit bounded design and smoke coverage. This document does not claim those stages are implemented.

## Safety invariants

All Phase 6 slices must preserve:

- normal response and stream delivery do not wait for persistence I/O,
- SLP failure does not invalidate an already valid visible response,
- default-off and dry-run-first gates,
- fail-closed schema, namespace, policy, and lineage handling,
- content-bearing material remains inside protected memory/SLP domains,
- default trace, audit, public errors, and node-result projections remain content-free,
- ordinary safe MEM formation may be autonomous when RelayMEM gates pass,
- review-required, approval-required, destructive, contradictory, sensitive, or cross-namespace operations remain held or blocked,
- RelaySLP never directly mutates SOUL,
- Phase 5.5 stream/TTS behavior remains unchanged,
- TTS, audio, adapter delivery, Live2D/avatar, and lip-sync execution remain SOUL Lab Runtime MVP responsibilities.

## Phase 6-A1 smoke expectations

The helper slice should cover:

- disabled skip,
- dry-run admission,
- explicit apply/enqueue gate still unsupported or false,
- unknown trigger block,
- unknown processing-stage block,
- malformed correlation block,
- missing namespace block,
- missing governed evidence/source-lineage block,
- unsupported upstream schema block,
- non-terminal turn-end block,
- persistence-policy block,
- waiting-user/recovery block,
- bounded source-count enforcement,
- content-free projection,
- proof that runtime-private references, fingerprints, idempotency keys, raw text, paths, and candidate arrays are absent from public diagnostics.

## Completion criteria for Phase 6-A0

Phase 6-A0 is complete when:

1. this bounded-slice document is linked from the current documentation indexes,
2. the pipeline plan identifies Phase 6-A1 as the next RelayLM Core implementation boundary,
3. the RelayMEM / RelaySLP current-target document distinguishes admission orchestration from RelayMEM-M memory semantics,
4. the RelayMEM-M independent plan records that M3b/M4 artifacts are upstream semantic inputs rather than Phase 6 duplicates,
5. no runtime, config, persistence, stream, TTS, audio, avatar, or SOUL behavior changes.
