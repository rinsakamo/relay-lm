---
relaylm_doc_type: evidence
relaylm_authority: historical_phase_i3_auditable_primary_mem_correct_handoff
relaylm_status: frozen
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_source_pr: 379
relaylm_source_final_head: 21af3752884204b4b60b82b75146525a2b6a6fa2
relaylm_source_merge_commit: 74b308f341cb049e6adebbe2b0c959950198739a
relaylm_source_merged_at: 2026-06-24T14:50:28Z
relaylm_intermediate_prs:
  - 415
  - 647
relaylm_intermediate_merge_commits:
  - 394ea1628f2262625c460c60d6b218ccc90429ac
  - 954eee9d26bd14d27da3d9a37e3caff9e6b760a3
relaylm_source_blob: 6b621aa6b9ef51b846cacc1b49c18c0a54fc8043
relaylm_source_sha256: f9055b1369da26c80cce3217f3786f5a384477d301b57019be8b3f39212401f7
relaylm_recorded_on: 2026-06-24
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current Primary MEM correction runtime behavior
  - current public schema storage API or UI behavior
  - current repository-wide implementation status
  - Forget Hide Pin Held or later mutation governance
  - compatibility aliases redirects stubs dual-read or dual-write
relaylm_related_authority:
  - ../../architecture/integration_i1_primary_mem_two_turn_recall.md
  - ../../architecture/memory_lifecycle_design.md
  - ../../architecture/phase_i4_primary_mem_forget_hide_contract.md
  - ../../architecture/phase_i5_pin_unpin_contract.md
  - ../../architecture/phase_i7ab_held_apply_discard_contract.md
  - ../../architecture/soul_lab_ui_mvp.md
  - ../../architecture/soul_lab_runtime_mvp.md
  - ../../contracts/ui/home-conversation.md
  - ../../contracts/ui/lifecycle-visibility.md
---
# Phase I-3: Auditable Primary MEM Correct

> **Historical implementation evidence.** This frozen handoff records the bounded auditable Primary MEM Correct implementation delivered by PR #379 and its later documentation/link maintenance. It is not current runtime, schema, API/UI, storage, product, compatibility, alias, redirect, dual-read, or dual-write authority.

## Current authority boundary

Current Correct behavior is independently owned by:

- `relaylm/relaymem_primary_correction.py` and `relaylm/relaymem_primary_recall.py` for correction-chain persistence and current-revision retrieval behavior;
- `relaylm/soul_lab_memory_correction.py` and `relaylm/soul_lab_app.py` for loopback mutation, token, projection, isolation, and route behavior;
- `apps/soul-lab/src/features/lab/correctionApi.ts`, `PrimaryMemoryCorrectPanel.tsx`, and the current SOUL Lab frontend for exact browser validation and explicit confirmation behavior;
- `scripts/relaylm_phase_i3_primary_mem_correct_ci_runner.py` and the focused Phase I-3 functional, security, validation, path-safety, and fault smokes for executable validation;
- current memory-lifecycle and SOUL Lab architecture documents for cross-slice ownership boundaries;
- `docs/PROJECT_STATUS.md` for repository-wide current implementation status.

Last reviewed: 2026-06-24 JST

## Status

Implemented on the Phase I-3 feature boundary. This is a historical-after-merge handoff; current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md).

This slice closes the first observe/correct/retrieve product loop for one real formed Primary MEM:

```text
ordinary managed turn
  -> real Primary MEM formation and durable M3 state
  -> Phase I-2 Lab Observation selects the formed memory
  -> read-only correction preflight
  -> bounded semantic diff
  -> explicit token-authorized apply
  -> immutable successor Primary page
  -> canonical index/log convergence
  -> immutable correction audit receipt
  -> later ordinary managed turn
  -> existing M2 selects the corrected current revision
  -> existing RelayCTX injects the corrected summary
```

## Scope

Implemented:

- Correct for one validated formed Primary MEM,
- title and summary as the only mutable semantic fields,
- stable logical memory identity with monotonically increasing correction revision,
- immutable prior Primary page retention,
- bounded correction history projection,
- later-turn convergence through the existing M2 and RelayCTX path.

Not implemented by this slice:

- forget,
- pin or unpin,
- merge,
- held-memory apply or discard,
- Secondary MEM consolidation,
- RelaySOUL mutation or rollback,
- queue scanning, scheduling, or daemon lifecycle,
- visible-response to background-finalizer pre-enqueue crash durability,
- static SOUL Lab bundle serving,
- TTS, audio, or avatar execution.

## Identity and revision model

The original Primary page write identity is the stable logical `memory_id` exposed to SOUL Lab. A correction does not overwrite that page.

For revision `N`:

1. preflight validates the current physical page, canonical index, and canonical log;
2. apply publishes a deterministic successor page through M3e;
3. M3f constructs the canonical reconciliation plan;
4. M3g applies index-before-log convergence;
5. an immutable applied receipt links the prior physical page to the successor;
6. the stable logical `memory_id` now resolves to revision `N+1`.

The prior page remains durable audit evidence but is marked superseded by validated correction metadata. M2 excludes superseded and prepared-only successor pages, maps the current physical page back to the stable logical identity, and retains ownership of relevance selection.

No correction-specific retriever is introduced.

## Semantic mutation boundary

Allowed fields:

- `title`, bounded to the canonical Primary page title limit;
- `summary`, bounded to the canonical Primary page summary limit;
- a bounded user reason stored only in the correction audit receipt.

Preserved fields:

- logical memory identity,
- character and namespace,
- Primary memory layer and memory kind,
- source-event kind and lineage fingerprint,
- source/run/turn correlation already owned by the original page,
- original formed timestamp and queue/dispatch ownership,
- store root and canonical path derivation.

The correction reason and audit metadata are not retrieval candidates and are never added to RelayCTX.

## API

The loopback SOUL Lab wrapper exposes:

```text
POST /lab/api/characters/{character_id}/memory/{memory_id}/correct/preflight?namespace=...
POST /lab/api/characters/{character_id}/memory/{memory_id}/correct?namespace=...
GET  /lab/api/characters/{character_id}/memory/{memory_id}/corrections?namespace=...
```

### Preflight

Request schema:

```text
relaylm.lab.memory_correct_preflight_request.v0
```

Preflight is read-only. It validates exact request shape, target scope, canonical store state, expected revision, and candidate bounds. It returns only a bounded title/summary before-and-after diff plus an opaque short-lived apply token.

It does not publish a page, alter index/log state, finalize a receipt, or alter retrieval behavior.

### Apply

Request schema:

```text
relaylm.lab.memory_correct_apply_request.v0
```

Apply requires the exact token and expected revision. The token binds character, namespace, logical memory identity, current physical page identity, current and candidate revision, candidate semantic digest, operation ID, issue and expiry timestamps.

The browser does not interpret the token.

### History

Response schema:

```text
relaylm.lab.memory_corrections.v0
```

The bounded history includes opaque correction ID, revision transition, bounded reason, status, timestamp, and changed-field flags. It excludes paths, roots, digests, lineage, queue/lease identity, protected source, prompts, transcripts, and exceptions.

## Mutation access security

Mutation succeeds only when all of the following hold:

- configured RelayLM listen host is loopback,
- actual ASGI peer address is loopback,
- request media type is exactly `application/json`,
- request body is within the fixed byte bound,
- exact Pydantic schema validation succeeds with unknown fields forbidden,
- apply token is valid, unexpired, and exactly bound to the request,
- current revision and canonical target still match preflight.

`Host`, `Origin`, and forwarding headers are not locality authority. No wildcard CORS, form mutation, GET mutation, query-only apply, or browser-supplied filesystem path is accepted.

## Idempotency and concurrency

Correct operation idempotency is independent of B3 dispatch idempotency and M3 write idempotency.

An exact replay with the same operation ID, token digest, target revision, and candidate returns the original applied result without creating another page or revision.

A reused operation ID with different binding data fails as an operation conflict.

A per-memory lock and pending-operation fence ensure that at most one correction candidate can own a current revision. A second apply for the same revision fails stale or conflicting before successor publication.

## Audit and recovery

Runtime-private correction artifacts live under the scoped RelayMEM store and are not public projections or retrieval sources.

States:

```text
prepared
  -> successor page published
  -> index/log reconciled
  -> applied/reconciled receipt finalized
```

The prepared receipt contains the bounded semantic candidate needed for deterministic recovery. The applied receipt is content-free except for the bounded reason and audit transition metadata.

Recovery revalidates that the prepared operation still names the unique current prior physical page and revision before publishing or reconciling. It never rolls an already committed Primary state back because audit finalization or HTTP delivery failed.

A prepared-only successor is excluded from normal M2 and Lab current-memory reads. After index/log convergence but before HTTP response, exact replay returns the same immutable success receipt.

## Historical used-memory integrity

Phase I-2 used-memory receipts preserve what was actually injected into a past backend-bound request.

After correction:

- `injected_summary` remains the historical revision representation;
- `current_summary` may show the corrected current representation;
- `representation_changed` records that they differ.

The past run is never rewritten to appear as though it used the corrected revision.

## SOUL Lab behavior

Correct is available only in real-server mode and only for `formed` Primary MEM items. Mock fallback is preview-only. Held and blocked outcomes remain non-mutable.

The browser flow is:

```text
select formed memory
  -> edit title/summary and bounded reason
  -> request preflight
  -> review bounded diff
  -> explicit Confirm Apply
  -> refresh current memory and correction history
```

Character or memory changes abort/discard pending reads and tokens. Apply loading disables repeat submission. Responses are strict exact-key validated and rendered through React text nodes without HTML insertion.

## Validation

The Phase I-3 workflow covers normal correction and Lab refresh, later ordinary M2/RelayCTX retrieval convergence, old revision exclusion and stable logical identity, wrong character/namespace isolation, stale and concurrent revision fencing, exact idempotent replay, token tampering and missing-token rejection, corrupt/symlink/path fail-closed behavior, crash and response-loss recovery seams, historical used-memory integrity, request/response bounds and exact schemas, loopback config and peer enforcement, forbidden-information leakage checks, M3e through M3h, Phase 6-C1/C2, Phase I-1, Phase I-2, and SOUL Lab regressions, frontend typecheck, strict browser schema smokes, and production build.

## Next separate boundary

The next implementation priority must be selected from the existing architecture plan. Phase I-3 did not change this durability window:

```text
visible response delivery
  -> background finalizer source publication
  -> B2 queue publication
```

A process exit before source/queue publication is the I1-G pre-enqueue background-finalizer durability boundary and must not be reported as solved by Correct. Current status for that later track belongs to [Project Status](../../PROJECT_STATUS.md).
