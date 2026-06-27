---
relaylm_doc_type: implementation_handoff
relaylm_authority: phase_i2_real_soul_lab_observation
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: relaymem_soul_lab_integration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i3_auditable_primary_mem_correct.md
  - phase_i4d_primary_retrieval_exclusion.md
  - soul_lab_ui_b0_real_home_conversation.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - memory mutation
  - queue scheduling
  - runtime adapter execution
---
# Phase I-2 Real SOUL Lab Observation

Status: complete for the bounded Phase I-2 real observation boundary.

## Purpose

Phase I-2 connects the existing SOUL Lab Observation surface to real RelayLM runtime evidence produced by the completed Phase I-1 two-turn Primary MEM path. The slice is observe-only. It does not add any memory or SOUL mutation.

The production flow is:

```text
ordinary managed turn
  -> existing Phase 6 / Phase I-1 processing
  -> bounded runtime observation capture
  -> durable read-model receipts only where existing evidence is not restart-safe
  -> pure character/namespace-scoped projection
  -> loopback-only Lab management API
  -> exact browser schema validation
  -> Lab Observation UI
```

## Authority boundary

Phase I-2 does not change the existing authorities:

- B3 remains queue lifecycle authority.
- C1-2 and C1-3 remain worker execution and outcome authority.
- M3a through M3h remain Primary MEM persistence authority.
- M1/M2 remain retrieval and selection authority.
- RelayCTX remains backend-bound context authority.
- Lab observation receipts are secondary read-only evidence only.

Observation receipts must never repair a queue, recreate protected source, publish a Primary page, change retrieval, or drive a retry/terminal transition. Receipt capture is best-effort and must not fail the visible response, roll back Primary MEM, or change the worker result.

## Explicit scope

There is no global server-owned active character. Every observation route uses an explicit `character_id` path segment and an explicit `namespace` query parameter. The pair must already exist in canonical model-route configuration. The configured RelayMEM root is resolved through the existing opaque character partition resolver; a request never constructs a filesystem path directly from the browser-provided character value.

Unknown characters return not found. Known characters with an unmapped namespace, unavailable store, or incomplete scope fail closed and return an explicit unavailable projection without guessing another partition.

## Read APIs

All routes are owned by `relaylm.soul_lab_app`, require both a loopback listen configuration and an actual loopback ASGI peer, and return `Cache-Control: no-store`.

```text
GET /lab/api/characters/{character_id}/lab/last-run?namespace=...
GET /lab/api/characters/{character_id}/memory/recent?namespace=...&limit=...
GET /lab/api/characters/{character_id}/memory/held?namespace=...&limit=...
GET /lab/api/characters/{character_id}/lab/last-run/memory/used?namespace=...
```

The existing UI-A7 routes remain unchanged:

```text
GET /lab/api/settings
GET /lab/api/characters
```

POST, PUT, PATCH, and DELETE are not implemented for observation resources and therefore return the existing method-not-allowed response without mutation.

## Public schemas

The public browser contracts are exact and versioned:

- `relaylm.lab.last_run.v0`
- `relaylm.lab.memory_recent.v0`
- `relaylm.lab.memory_held.v0`
- `relaylm.lab.memory_used.v0`

Every response includes `source: relaylm_runtime`, `read_only: true`, explicit availability, explicit capability, exact character/namespace scope, bounded reason IDs, and only allowlisted keys.

Raw dataclasses, Pydantic `repr`, queue records, protected sources, traces, exceptions, prompts, transcripts, backend payloads, paths, credentials, digests, lease metadata, and full memory pages are never serialized.

## Latest completed run

The latest-run projection is based only on completed run receipts. Partial or in-progress captures are not promoted to a completed run. Ordering uses the canonical UTC completion timestamp and an opaque run-id tiebreaker, never filesystem modification time or incidental directory/dictionary order.

The projection includes bounded statuses and counts for RelaySLP, RelayRUN, RelayCTX Repack, RelayCTX Unpack observation availability, formed/held/blocked worker outcomes correlated to that run, memories actually included in backend-bound context, and bounded recovery/reason state.

## Recently formed Primary memories

The recent-memory projection reads the actual character partition and reuses the existing Phase I-1 Primary page, canonical index, canonical log, namespace, digest, lineage, and index/log-link validation. It does not introduce a second memory parser.

Ordering follows canonical durable log order. Each page is validated before any bounded summary is exposed. A malformed page, unsafe file, symlink, path escape, namespace mismatch, or index/log inconsistency is omitted fail-closed and reported only through a stable reason ID.

## Held and blocked outcomes

Held and blocked outcomes are not Primary memories and are never placed in the retrieval store. Existing durable artifacts did not preserve enough bounded human-facing evidence across restart, so Phase I-2 adds the minimum secondary receipt:

```text
relaylm.lab.memory_outcome_receipt.v0
```

The receipt is written after the worker result is known and contains exact run/namespace/turn correlation, a runtime-private opaque job correlation digest, formed/held/blocked classification copied from the authoritative worker result, bounded title/summary from the already validated governed experience, stable bounded reason IDs, and observation timestamp.

Retry-released and transition-failed attempts are not misrepresented as a terminal held/blocked result. Receipt failure is swallowed after the worker has produced its authoritative result.

## Used-memory evidence

Phase I-2 records evidence at the existing RelayCTX runtime injection boundary, after selection and payload mutation have been decided. The receipt schema is:

```text
relaylm.lab.used_memory_receipt.v0
```

It distinguishes retrieval attempted, candidate discovered, selected, RelayCTX injection performed, backend-bound payload included the memory, and response generation completed. Only actually injected identities are included in the public item list. Selected-but-not-injected candidates are represented by stage booleans, not as used items.

Each used item stores an opaque Primary memory identity and the bounded summary that was injected for that run. At read time the current representation is resolved again through the validated Primary store. The API therefore keeps `injected_summary` separate from `current_summary` and reports whether the representation changed, preserving audit boundaries.

I-4D later adds the separate read-only lifecycle overlay without rewriting these v0 receipts.

## Durable observation store

Receipts live below the already resolved character store partition in a dedicated `.relaylm-lab-observation-v0` directory. They are not memory pages and are not indexed by M1/M2.

Storage uses canonical UTF-8 JSON, exact envelope/payload keys, versioned payload schemas, SHA-256 payload integrity checks, fixed byte/read bounds, atomic temporary write plus no-clobber hard-link publication, idempotent same-content replay, symlink/unsafe/path-escape rejection, and corrupt-record isolation.

Receipt filenames are derived from stable opaque correlations. Public APIs do not expose receipt paths, filenames, payload digests, request IDs, or job correlations.

## Runtime capture

`relaylm.soul_lab_observation` installs one narrow wrapper around the existing runtime injection function only in the canonical Lab ASGI application. It does not replace M2 or RelayCTX behavior. A bounded process-local pending map links the already existing request/run identifiers to ASGI response completion.

`LabObservationResponseMiddleware` finalizes a run only after the final ASGI response body is sent. Streaming responses are not marked complete at header creation. Pending state is bounded and is not an authority; if the process dies before response completion, no completed receipt is fabricated.

The Primary worker public seam invokes a best-effort observation capture only after the authoritative worker result returns. The original result is returned unchanged.

## Browser boundary

`apps/soul-lab/src/features/lab/observationApi.ts` validates exact keys, schema versions, enums, booleans, non-negative counts, list bounds, title/summary bounds, opaque identities, reason IDs, character/namespace equality, and latest-run/used-run correlation.

The connected page uses `AbortController` plus a monotonically increasing request generation. A delayed response from the previously selected character is discarded and cannot be rendered under a new character.

UI states are explicit: loading, real server-owned data, valid empty state, access refused, invalid schema, runtime unavailable, and explicit local-preview fallback. Server data and preview data are never mixed. Real mode is labeled `Source: RelayLM runtime`.

Correct, forget, pin, merge, apply-held, and discard-held controls are disabled in this slice. React text rendering is used; no observation content is inserted as HTML.

## Verification

The Phase I-2 smoke proves ordinary enqueue/C2 worker formation, next-turn M2/RelayCTX injection, latest-run/recent-memory/held-blocked/used-memory reads, restart reconstruction, character/namespace isolation, loopback enforcement, method refusal, bounds, corrupt receipt isolation, response leakage exclusions, UI-A7 regressions, frontend typecheck, and production build.

CI entrypoints:

```text
PYTHONPATH=.:scripts python scripts/relaylm_phase_i2_lab_observation_ci_runner.py
cd apps/soul-lab && npm run typecheck && npm run build
```

## Completion boundary

Phase I-2 completes real SOUL Lab observation only. Later completed slices include Phase I-3 Correct, I-4B/I-4C1/I-4C2/I-4D lifecycle work, and UI-B0 real Home conversation. Their current status belongs to [Project Status](../PROJECT_STATUS.md) and their dedicated handoffs.

Phase I-2 does not implement memory mutation, Forget, Pin/Unpin, Merge, Held Apply/Discard, RelaySOUL mutation, queue scanner/scheduler, daemon/service lifecycle, I1-G durable-finalization replay, Secondary MEM consolidation, static UI bundle serving, or TTS/audio/Live2D execution.
