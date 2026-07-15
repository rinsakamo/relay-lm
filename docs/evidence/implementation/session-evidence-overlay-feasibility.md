---
relaylm_doc_type: evidence
relaylm_authority: session_evidence_overlay_implementation_feasibility_record
relaylm_status: historical
relaylm_volatility: high
relaylm_owner: context_memory
relaylm_update_trigger:
  - the Session Evidence Overlay proposal changes materially
  - RelayCTX cross-request working-state storage is implemented
  - response finalization or RelaySLP reconciliation ownership changes
relaylm_not_authoritative_for:
  - accepted architecture
  - current runtime behavior
  - exact production schema or implementation sequence
  - durable MEM authority
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_source_commit: 103bc03f90c9fda089b5a9e0d5197607e96a303f
relaylm_recorded_on: 2026-07-15
relaylm_related_proposals:
  - ../../proposals/subjective-memory-formation-consolidation-and-retrieval.md
relaylm_code_sources:
  - ../../../relaylm/request_scope.py
  - ../../../relaylm/pipeline_context.py
  - ../../../relaylm/relayctx_unpack.py
  - ../../../relaylm/relayctx_unpack_runtime.py
  - ../../../relaylm/adapter.py
  - ../../../relaylm/managed_chat_response.py
  - ../../../relaylm/relaymem_slp_finalized_turn_source.py
relaylm_related_contracts:
  - ../../contracts/context_compiler_contract.md
---

# Session Evidence Overlay Implementation Feasibility

## Result

A Session Evidence Overlay is implementable within RelayLM's existing component boundaries. It does not require a second durable MEM authority or synchronous RelaySLP execution.

It is not, however, an existing feature waiting to be enabled. The repository already contains most request-local and finalized-turn primitives, but it does not yet contain the cross-request session store, deterministic overlay reconciliation, next-turn lookup and packing, or stream-completion ordering needed for production behavior.

The practical assessment is:

```text
request-local prototype       feasible with low-to-moderate change
non-stream cross-turn MVP     feasible with moderate change
stream-safe cross-turn MVP    feasible with moderate-to-high change
production lifecycle          feasible but requires explicit contracts and integration tests
```

## Existing reusable boundaries

### Session identity already exists

`RequestScopeIdentity` resolves `session_id` from an allowlisted request header or request metadata and merges it with route scope. The same scope also carries user, room, and scene identity. A future overlay can therefore use an explicit composite key instead of deriving identity from message content.

Recommended key:

```text
character_id
+ memory_namespace
+ session_id
+ optional user_id / room_id / scene_id fence
```

Missing or conflicting identity must fail closed to no overlay rather than fall back to a global session.

### Request-local private candidate storage already exists

`PipelineContext` already owns `ctx_working_update_candidate` as detached request-local content-bearing state. It is explicitly non-persistent and is excluded from content-bearing diagnostics.

This proves that a private typed candidate can pass through the request pipeline without becoming trace authority. It does not provide cross-request continuity by itself.

### Strict response-side extraction already exists

RelayCTX Unpack already:

- accepts an explicit trailing JSON block rather than guessing structure from prose;
- preserves visible text when the candidate is malformed;
- validates an allowlist and size bound;
- produces a detached candidate;
- records only content-free diagnostics;
- forbids persistence at the Unpack boundary.

The semantic memory sidecar should reuse these principles, but it should use a separate schema and parser rather than overloading `relayctx_working_update.v0`.

### Response finalization already owns SLP handoff

Managed response handling already captures finalized visible assistant output, binds the resolved `session_id`, constructs finalized-turn evidence, and schedules RelaySLP enqueue after a successful response. Both stream and non-stream paths already converge on finalized-turn capture and protected-source construction.

This provides a natural place to admit a validated overlay update without moving durable formation into the latency-critical path.

### Protected turn evidence already contains session lineage

`RelayMEMSLPFinalizedTurnSource` already carries:

- character and namespace;
- run and turn identity;
- optional `session_id`;
- governed user and assistant messages;
- source lineage fingerprint;
- scene and affect artifacts.

The overlay can therefore remain a rebuildable working projection whose eventual RelaySLP reconciliation always returns to protected source evidence.

### The target compiler already anticipates short-term CTX input

The context compiler contract already defines `RelayCTX-selected short-term context` and `selected_recent_context` as target managed-compiler inputs. The current compiler does not yet consume them. A Session Evidence Overlay therefore fits the target architecture, but depends on that target compiler or an equivalent dynamic-suffix injection boundary.

## Missing implementation pieces

### 1. Cross-request overlay store

The current `PipelineContext` is request-local. A new app-scoped store is required.

Minimum interface:

```python
read_snapshot(scope_key) -> OverlaySnapshot
apply_turn_update(scope_key, expected_revision, turn_update) -> ApplyResult
acknowledge_slp(scope_key, source_lineage_fingerprints) -> ApplyResult
expire(scope_key) -> None
```

The initial implementation may be RAM-only and rebuildable. It must not write MEM Markdown or become the authority for user facts.

Required properties:

- character, namespace, and session isolation;
- bounded candidates, text, evidence spans, and relation hints;
- monotonic revision or compare-and-swap protection;
- idempotency by run/turn/source-lineage identity;
- per-session concurrency fencing;
- TTL and least-recently-used eviction;
- no raw candidate content in trace projections;
- explicit loss-on-restart semantics for an RAM-only MVP.

### 2. Deterministic in-session reconciliation

The overlay should perform only bounded, reversible working-state operations:

```text
same scoped semantic key + same compatible value
  -> attach another source reference

explicit correction
  -> mark the earlier session candidate retracted

new incompatible current-state value
  -> shadow the earlier candidate for this session

materially different subject, modality, time, project, relationship, or scene
  -> retain as a separate candidate
```

It must not issue final `reinforce_memory`, `supersede_memory`, or canonical-MEM decisions. Those remain RelaySLP/MEM authority.

### 3. Next-turn lookup and packing

At the start of a managed request, RelayLM must read the overlay snapshot after scope resolution and before final context packing.

The snapshot may:

- contribute bounded query facets to RelayMEM candidate generation;
- shadow a durable candidate for the current session when direct current-session evidence conflicts;
- boost compatible durable candidates;
- provide a compact `session_continuity` block to RelayCTX.

It must not be inserted automatically in full. RelayCTX should select the smallest sufficient subset and place it in the dynamic suffix after durable character authority.

### 4. Response-finalization update

For non-stream responses, a validated sidecar or deterministic current-turn candidate can be admitted after visible-text extraction and before returning the response, provided the operation is bounded, local, and does not invoke RelaySLP or storage I/O.

For streaming responses, a Starlette `BackgroundTask` is insufficient as the only overlay update mechanism. The next request may race the background task immediately after the stream completes. A stream-safe implementation should commit the bounded overlay update inside the stream finalization wrapper before it emits terminal completion, or explicitly accept and test a one-turn lag.

The preferred invariant is:

```text
visible stream fully finalized
  -> sidecar/current-turn candidate validated
  -> bounded overlay compare-and-swap committed
  -> stream iterator terminates
  -> deferred RelaySLP work may continue separately
```

### 5. SLP reconciliation

RelaySLP must rebuild Shared Assessment from protected source evidence. It may use overlay grouping and correction hints as advisory indexing information, but it must not promote the overlay snapshot directly into durable MEM.

After a durable receipt is published, the overlay store should acknowledge the exact source-lineage fingerprints covered by that receipt and then:

- remove candidates fully represented by durable state;
- retain newer, unresolved, or contradictory candidates;
- replace shadow hints with the newly current durable MEM identity where available;
- remain idempotent under worker replay and response-loss replay.

A missing or delayed acknowledgement must cause duplicate provisional context at worst, never loss or corruption of protected evidence.

## Proposed provisional schema

```yaml
schema_version: relayctx.session_evidence_overlay.v0
scope:
  character_id: default
  namespace: character_default
  session_id: session-123
revision: 7
candidates:
  - candidate_id: session:session-123:run-42:0
    status: provisional
    semantic_key:
      subject: user
      predicate: prefers
      scope: focused_work
    object_text: tea
    polarity: positive
    modality: asserted_state
    temporal_kind: current_state
    source_lineage_fingerprints:
      - sha256:...
    evidence_spans:
      - source_role: user
        quote: "最近は仕事中なら紅茶かな"
    shadows_durable_mem_ids:
      - mem:coffee-preference
    first_seen_at: system_owned
    last_seen_at: system_owned
```

The exact schema is undecided. In particular, timestamps, source fingerprints, and scope identity are system-owned; model output may only propose bounded semantic fields and source spans.

## Suggested implementation slices

### SEO-0: Contract and isolated store

- define overlay, scope-key, snapshot, update, and content-free projection contracts;
- implement a bounded in-memory store with revision fencing, idempotency, TTL, and isolation;
- no prompt injection, Retrieval change, or SLP acknowledgement.

### SEO-1: Non-stream continuity

- parse a separate bounded semantic sidecar or deterministic current-user candidate;
- synchronously admit the bounded update before a successful non-stream response returns;
- load the snapshot on the next request;
- inject only a compact `session_continuity` dynamic block;
- validate correction, shadowing, missing-session, conflict, eviction, and restart-loss behavior.

### SEO-2: Retrieval interaction

- allow explicit overlay facets to influence candidate generation and deterministic ranking;
- preserve durable lifecycle and correction authority;
- expose compact ranking reasons to RelayCTX and the main LLM;
- ensure an overlay candidate cannot make a hidden or recovery-required MEM retrieval-eligible.

### SEO-3: Stream-safe finalization

- extend finalized stream capture with an exact finalization callback;
- commit the bounded overlay update before terminal stream completion;
- test disconnects, partial streams, malformed sidecars, backend errors, and immediate next-request races.

### SEO-4: RelaySLP acknowledgement

- bind durable receipts to covered source-lineage fingerprints;
- acknowledge or retire corresponding provisional candidates idempotently;
- test duplicate workers, response-loss replay, stale overlay revisions, and delayed acknowledgement.

### SEO-5: Optional restart recovery

Only if user experience requires it, add a short-lived checkpoint to durable operation state. The checkpoint remains rebuildable working state and must not become MEM prose authority. A RAM-only implementation should be preferred until restart-loss measurements justify this extra lifecycle.

## Main risks

| Risk | Required safeguard |
|---|---|
| cross-session leakage | exact composite scope key; no global fallback; isolation tests |
| stale overlay beats corrected durable state | durable lifecycle/correction gate remains authoritative; revision and acknowledgement |
| current-turn response latency regression | bounded local parse and compare-and-swap only; no LLM, vector build, fsync, or RelaySLP inline |
| stream race | finalization callback before terminal completion or an explicitly tested one-turn-lag contract |
| model-fabricated candidate | evidence-span verification; nullable fields; advisory semantic fields only |
| overlay becomes shadow MEM store | TTL, bounds, rebuildable status, no Markdown authority, no ordinary MEM API exposure |
| repeated prompt bloat | compact selection, canonical provisional collapse, strict token budget |
| restart loss surprises the model | explicit reset semantics and optional later checkpointing |
| SLP replay removes newer state | source-lineage acknowledgement plus compare-and-swap revision fencing |

## Validation gates

A production implementation should demonstrate:

- zero cross-character, namespace, user, room, scene, and session leakage;
- deterministic correction and shadow behavior;
- current-session evidence outranks an incompatible stale durable MEM without mutating it;
- historical queries can still retrieve the older durable MEM;
- missing or invalid `session_id` produces no overlay read or write;
- malformed sidecars preserve visible responses and produce no overlay mutation;
- p50/p95 request overhead remains within an accepted local budget;
- immediate next requests observe the completed previous turn for both non-stream and stream paths;
- disconnects and failed backend responses do not publish completed-turn candidates;
- overlay loss or eviction never deletes protected evidence or durable MEM;
- SLP acknowledgement is replay-safe and does not remove newer unresolved candidates;
- prompt selection remains bounded as session length grows.

## Conclusion

The Session Evidence Overlay is structurally compatible with RelayLM and can be implemented without weakening MEM authority. Existing code already supplies session identity, request-local private candidates, strict response unpacking, finalized-turn source capture, and deferred RelaySLP handoff.

The irreducible new work is a bounded cross-request store, next-turn selection and packing, deterministic in-session reconciliation, stream-safe finalization ordering, and SLP receipt acknowledgement. This should be treated as a dedicated implementation track rather than folded casually into the semantic-sidecar parser or durable MEM store.
