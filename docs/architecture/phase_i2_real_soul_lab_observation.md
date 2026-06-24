# Phase I-2 Real SOUL Lab Observation

Status: implemented on the Phase I-2 feature branch; pending review and merge.

## Purpose

Phase I-2 connects the existing SOUL Lab Observation surface to real RelayLM
runtime evidence produced by the completed Phase I-1 two-turn Primary MEM path.
The slice is observe-only. It does not add any memory or SOUL mutation.

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

Observation receipts must never repair a queue, recreate protected source,
publish a Primary page, change retrieval, or drive a retry/terminal transition.
Receipt capture is best-effort and must not fail the visible response, roll back
Primary MEM, or change the worker result.

## Explicit scope

There is no global server-owned active character. Every observation route uses
an explicit `character_id` path segment and an explicit `namespace` query
parameter. The pair must already exist in canonical model-route configuration.
The configured RelayMEM root is resolved through the existing opaque character
partition resolver; a request never constructs a filesystem path directly from
the browser-provided character value.

Unknown characters return not found. Known characters with an unmapped
namespace, unavailable store, or incomplete scope fail closed and return an
explicit unavailable projection without guessing another partition.

## Read APIs

All routes are owned by `relaylm.soul_lab_app`, require both a loopback listen
configuration and an actual loopback ASGI peer, and return
`Cache-Control: no-store`.

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

POST, PUT, PATCH, and DELETE are not implemented for observation resources and
therefore return the existing method-not-allowed response without mutation.

## Public schemas

The public browser contracts are exact and versioned:

- `relaylm.lab.last_run.v0`
- `relaylm.lab.memory_recent.v0`
- `relaylm.lab.memory_held.v0`
- `relaylm.lab.memory_used.v0`

Every response includes:

- `source: relaylm_runtime`
- `read_only: true`
- an explicit availability state
- an explicit capability marker
- exact character and namespace scope
- bounded reason IDs
- only allowlisted keys

Raw dataclasses, Pydantic `repr`, queue records, protected sources, traces,
exceptions, prompts, transcripts, backend payloads, paths, credentials, digests,
lease metadata, and full memory pages are never serialized.

## Latest completed run

The latest-run projection is based only on completed run receipts. Partial or
in-progress captures are not promoted to a completed run. Ordering uses the
canonical UTC completion timestamp and an opaque run-id tiebreaker, never
filesystem modification time or incidental directory/dictionary order.

The projection includes bounded statuses and counts for:

- RelaySLP
- RelayRUN
- RelayCTX Repack
- RelayCTX Unpack observation availability
- formed, held, and blocked worker outcomes correlated to that run
- memories actually included in backend-bound context
- bounded recovery/reason state

## Recently formed Primary memories

The recent-memory projection reads the actual character partition and reuses
the existing Phase I-1 Primary page, canonical index, canonical log, namespace,
digest, lineage, and index/log-link validation. It does not introduce a second
memory parser.

Ordering follows canonical durable log order. Each page is validated before any
bounded summary is exposed. A malformed page, unsafe file, symlink, path escape,
namespace mismatch, or index/log inconsistency is omitted fail-closed and
reported only through a stable reason ID.

The endpoint returns at most 50 records and currently exposes only fields that
can be safely proven from the existing Primary schema. `formed_at` remains null
and confidence remains `not_recorded` when the authoritative schema does not
record those values; the projection does not invent them.

## Held and blocked outcomes

Held and blocked outcomes are not Primary memories and are never placed in the
retrieval store. Existing durable artifacts did not preserve enough bounded
human-facing evidence across restart, so Phase I-2 adds the minimum secondary
receipt:

```text
relaylm.lab.memory_outcome_receipt.v0
```

The receipt is written after the worker result is known and contains only:

- exact run/namespace/turn correlation
- a runtime-private opaque job correlation digest
- formed/held/blocked classification copied from the authoritative worker result
- bounded title and summary from the already validated governed experience
- stable bounded reason IDs
- observation timestamp

Retry-released and transition-failed attempts are not misrepresented as a
terminal held/blocked result. Receipt failure is swallowed after the worker has
produced its authoritative result.

## Used-memory evidence

Phase I-2 records evidence at the existing RelayCTX runtime injection boundary,
after selection and payload mutation have been decided. The receipt schema is:

```text
relaylm.lab.used_memory_receipt.v0
```

It distinguishes:

- retrieval attempted
- candidate discovered
- selected
- RelayCTX injection performed
- backend-bound payload included the memory
- response generation completed, proven separately by the completed run receipt

Only actually injected identities are included in the public item list.
Selected-but-not-injected candidates are represented by stage booleans, not as
used items.

Each used item stores an opaque Primary memory identity and the bounded summary
that was injected for that run. At read time the current representation is
resolved again through the validated Primary store. The API therefore keeps
`injected_summary` separate from `current_summary` and reports whether the
representation changed, preserving the future I-3 audit boundary.

## Durable observation store

Receipts live below the already resolved character store partition in a
dedicated `.relaylm-lab-observation-v0` directory. They are not memory pages and
are not indexed by M1/M2.

Storage properties:

- canonical UTF-8 JSON
- exact envelope and payload keys
- versioned payload schemas
- SHA-256 payload integrity check
- 64 KiB per receipt bound
- 256 receipts per kind read bound
- atomic temporary write plus no-clobber hard-link publication
- idempotent same-content replay
- symlink, unsafe file, and path-escape rejection
- corrupt-record isolation so one bad receipt does not hide valid siblings

Receipt filenames are derived from stable opaque correlations. Public APIs do
not expose receipt paths, filenames, payload digests, request IDs, or job
correlations.

## Runtime capture

`relaylm.soul_lab_observation` installs one narrow wrapper around the existing
runtime injection function only in the canonical Lab ASGI application. It does
not replace M2 or RelayCTX behavior. A bounded process-local pending map links
the already existing request/run identifiers to ASGI response completion.

`LabObservationResponseMiddleware` finalizes a run only after the final ASGI
response body is sent. Streaming responses are not marked complete at header
creation. Pending state is bounded and is not an authority; if the process dies
before response completion, no completed receipt is fabricated.

The Primary worker public seam invokes a best-effort observation capture only
after the authoritative worker result returns. The original result is returned
unchanged.

## Browser boundary

`apps/soul-lab/src/features/lab/observationApi.ts` validates exact keys, schema
versions, enums, booleans, non-negative counts, list bounds, title/summary
bounds, opaque identities, reason IDs, character/namespace equality, and
latest-run/used-run correlation.

The connected page uses `AbortController` plus a monotonically increasing
request generation. A delayed response from the previously selected character
is discarded and cannot be rendered under a new character.

UI states are explicit:

- loading
- real server-owned data
- valid empty state
- access refused
- invalid schema
- runtime unavailable
- explicit local-preview fallback

Server data and preview data are never mixed. The preview is shown only after a
user explicitly selects it and is labeled `Source: Local preview data`. Real
mode is labeled `Source: RelayLM runtime`.

Correct, forget, pin, merge, apply-held, and discard-held controls are disabled
and labeled as the next phase. React text rendering is used; no observation
content is inserted as HTML.

## Verification

The Phase I-2 smoke proves:

1. Turn 1 ordinary enqueue and C2 worker formation.
2. Turn 2 existing M2 selection and RelayCTX/backend-bound injection.
3. latest-run, recent-memory, held/blocked, and used-memory reads.
4. restart reconstruction from the durable Primary store and receipts.
5. wrong-character and wrong-namespace isolation.
6. loopback config plus actual peer enforcement.
7. POST/PUT/PATCH/DELETE refusal.
8. bounded lists and summaries.
9. corrupt receipt isolation and fail-closed behavior.
10. response leakage exclusions.
11. existing UI-A7 management routes, Phase 6 worker integration, and Phase I-1 regressions.
12. frontend typecheck and production build.

CI entrypoints:

```text
PYTHONPATH=.:scripts python scripts/relaylm_phase_i2_lab_observation_ci_runner.py
cd apps/soul-lab && npm run typecheck && npm run build
```

## Completion boundary

After merge, the implementation status is:

- I1-B producer: complete
- B3 lifecycle: complete
- C1-0 through C1-5: complete
- C2 one-job integration: complete
- I-1 next-turn Primary MEM recall: complete
- I-1 character/namespace isolation: complete
- I-2 real SOUL Lab observation: complete
- I-3 auditable Correct operation: next

Not completed by Phase I-2:

- memory Correct mutation
- forget
- pin/unpin
- merge
- held-memory apply/discard
- RelaySOUL mutation
- queue scanner/scheduler
- daemon/service lifecycle
- pre-enqueue background-finalizer crash recovery
- Secondary MEM consolidation
- static UI bundle serving
- TTS/audio/Live2D execution
