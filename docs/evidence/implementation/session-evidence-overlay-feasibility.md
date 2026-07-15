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
  - SCN or EMO conditioning boundaries change
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

It is not, however, an existing feature waiting to be enabled. The repository already contains most request-local and finalized-turn primitives, but it does not yet contain the cross-request session store, deterministic overlay reconciliation, next-turn lookup and packing, stream-completion ordering, or RelaySLP acknowledgement needed for production behavior.

The practical assessment is:

```text
request-local prototype       feasible with low-to-moderate change
non-stream cross-turn MVP     feasible with moderate change
stream-safe cross-turn MVP    feasible with moderate-to-high change
production lifecycle          feasible but requires explicit contracts and integration tests
```

## Design correction recorded by this assessment

The feasible and semantically safe target is:

> RelaySLP subjective formation is SOUL-centered, SCN-grounded, and EMO-decoupled.

This does not mean that SCN or EMO disappears from the system.

```text
online response and provisional continuity
  SOUL + REL + current SCN + current EMO
  -> hot provisional interpretation
  -> Session Evidence Overlay

deferred Shared Assessment
  Protected Source Evidence
  + CTX system metadata
  + normalized SCN facts
  -> character-independent evidence interpretation

deferred Subjective MEM formation
  Shared Assessment
  + stable SOUL
  + bounded REL identity/history
  + normalized SCN facts needed for scope
  + provisional reaction as non-authoritative evidence
  - current EMO
  - transient SCN expression pressure
  -> cold durable interpretation

persistence decision
  scene policy + privacy + lifecycle gates
  -> apply / hold / reject
```

SCN is required for contextual correctness but must be split into:

1. normalized scene facts for speaker, addressee, role-play, task, audience, and scope;
2. persistence/disclosure policy for apply, hold, reject, namespace, and privacy;
3. transient expression allowance for the online response only.

Current EMO may be retained as evidence that the character reacted in a particular way. It must not become evidence that the user objectively had the state the character inferred.

## Existing reusable boundaries

### Session identity already exists

`RequestScopeIdentity` resolves `session_id` from an allowlisted request header or request metadata and merges it with route scope. The same scope also carries user, room, and scene identity.

Recommended overlay key:

```text
character_id
+ memory_namespace
+ session_id
+ optional user_id / room_id / scene_id fence
```

Missing or conflicting identity must fail closed to no overlay rather than fall back to a global session.

### Request-local private candidate storage already exists

`PipelineContext` already owns `ctx_working_update_candidate` as detached request-local content-bearing state. It is explicitly non-persistent and excluded from content-bearing diagnostics.

This proves that a private typed candidate can pass through the request pipeline without becoming trace authority. It does not provide cross-request continuity by itself.

### Strict response-side extraction already exists

RelayCTX Unpack already:

- accepts an explicit trailing JSON block rather than guessing structure from prose;
- preserves visible text when the candidate is malformed;
- validates an allowlist and size bound;
- produces a detached candidate;
- records only content-free diagnostics;
- forbids persistence at the Unpack boundary.

A semantic memory sidecar should reuse these principles but use a separate schema and parser rather than overload `relayctx_working_update.v0`.

### Response finalization already owns SLP handoff

Managed response handling already captures finalized visible assistant output, binds the resolved `session_id`, constructs finalized-turn evidence, and schedules RelaySLP enqueue after a successful response.

Both stream and non-stream paths already converge on finalized-turn capture and protected-source construction. This provides a natural place to admit a validated overlay update without moving durable formation into the latency-critical path.

### Protected turn evidence already contains session lineage

`RelayMEMSLPFinalizedTurnSource` already carries:

- character and namespace;
- run and turn identity;
- optional `session_id`;
- governed user and assistant messages;
- source lineage fingerprint;
- scene and affect artifacts.

The overlay can therefore remain a rebuildable working projection whose eventual RelaySLP reconciliation always returns to Protected Source Evidence.

### The target compiler already anticipates short-term CTX input

The context compiler contract already defines `RelayCTX-selected short-term context` and `selected_recent_context` as target managed-compiler inputs.

The current compiler does not yet consume them. A Session Evidence Overlay fits the target architecture but depends on the target compiler or an equivalent dynamic-suffix injection boundary.

## Proposed runtime model

### Overlay snapshot

```yaml
schema_version: relayctx.session_evidence_overlay.v0
scope_key:
  character_id: default
  namespace: character_default
  session_id: session-123
  user_id: user-123
  room_id: null
  scene_id: home-chat
revision: 17
updated_at: 2026-07-15T18:00:00+09:00
candidates: []
```

### Provisional candidate

```yaml
candidate_id: session:session-123:turn-42:claim-1
source_lineage_fingerprint: sha256:...
source_turn_ref: turn-42
status: provisional
semantic_facets:
  subject: user
  predicate: prefers
  object_text: tea
  polarity: positive
  modality: asserted_preference
  temporal_kind: current_state
  scene_scope: focused_work
shadows_durable_candidates:
  - mem:coffee-preference
correction_of: null
provisional_interpretation:
  perceived_significance: user may be seeking a calmer work routine
  current_scene_ref: scene:focused-work
  affect_ref: emo:concerned
  authority: non_authoritative
```

### Required state transitions

```text
new grounded candidate
  -> provisional

same compatible claim in same source group
  -> collapse source refs, no independent-strength increase

explicit current-session correction
  -> prior candidate retracted_in_session
  -> successor provisional candidate

new incompatible current state
  -> prior candidate shadowed_in_session
  -> new provisional candidate

RelaySLP durable receipt
  -> acknowledge matching source lineage
  -> remove, replace, or retain bounded reaction evidence

TTL / eviction / invalid scope
  -> drop overlay projection
  -> preserve Protected Source Evidence
```

## Missing implementation pieces

### 1. Cross-request overlay store

The current `PipelineContext` is request-local. A new app-scoped store is required.

Minimum interface:

```python
read_snapshot(scope_key) -> OverlaySnapshot
apply_turn_update(scope_key, expected_revision, turn_update) -> ApplyResult
acknowledge_slp(scope_key, source_lineage_fingerprints) -> ApplyResult
evict_expired(now) -> EvictionResult
```

Required properties:

- exact composite scope isolation;
- optimistic revision fencing or one equivalent serializing mechanism;
- idempotency by source lineage and turn identity;
- bounded candidates, text, and total bytes per session;
- TTL and deterministic eviction;
- no unbounded global dictionary;
- no content-bearing default trace projection.

### 2. Separate sidecar and overlay schemas

`relayctx_working_update.v0` should remain the current short-term task/topic contract.

The memory sidecar and Session Evidence Overlay need separate schemas because they have different consumers, validation rules, authority, retention, and reconciliation.

Suggested separation:

```text
relayctx_working_update.v0
  -> current topic/task/decision continuity

relaymem.semantic_sidecar.v0
  -> online semantic hints and provisional reaction

relayctx.session_evidence_overlay.v0
  -> cross-request current-session working projection
```

### 3. Non-stream response finalization update

For a successful non-stream response:

```text
backend response
  -> RelayCTX sidecar/unpack validation
  -> finalized visible-text capture
  -> Protected Source Evidence preparation
  -> bounded overlay update
  -> response return
  -> deferred RelaySLP enqueue
```

The synchronous portion must be limited to local validation, source-lineage binding, and revision-fenced in-memory update.

It must not perform:

- new LLM inference;
- embedding or vector construction;
- filesystem durability;
- SQLite fsync;
- RelaySLP execution;
- broad durable-memory lookup.

### 4. Stream-safe finalization ordering

The current stream path uses wrappers and a post-response `BackgroundTask`. If overlay update occurs only in the background task, an immediate next request may arrive before the previous turn's provisional state is visible.

Required ordering:

```text
final visible stream chunk accepted
  -> finalized-turn source becomes available
  -> bounded overlay update commits
  -> terminal stream completion is released
  -> asynchronous RelaySLP work may continue later
```

This likely requires a finalization callback owned by the stream wrapper or response-finalization boundary, not an ordinary post-response task alone.

Failure policy should be fail-open for the visible response and fail-closed for overlay mutation:

- never corrupt or delay an otherwise valid response indefinitely;
- never apply a partial or unscoped overlay update;
- emit content-free failure diagnostics;
- allow the next turn to fall back to durable Retrieval and selected recent context.

### 5. Next-turn lookup and packing

Before Retrieval and final RelayCTX packing:

```text
resolved scope
  -> read overlay snapshot
  -> validate revision / TTL / scope
  -> derive bounded query facets and session candidates
  -> apply Retrieval boosts and shadows
  -> select minimum sufficient overlay hints
  -> pack in dynamic suffix after stable authority
```

The entire overlay must not be copied into the prompt. Selection should prefer:

1. explicit corrections and retractions relevant to the current query;
2. current-session state that shadows an incompatible durable MEM;
3. referable entities or decisions lost from recent-message compaction;
4. unresolved uncertainty needed for a safe answer.

### 6. Retrieval interaction

The overlay is not an ordinary Retrieval corpus.

Permitted effects:

- add bounded query facets;
- boost a compatible durable MEM;
- shadow an incompatible durable MEM within the same session;
- add one bounded provisional candidate block;
- expose a correction or uncertainty reason.

Forbidden effects:

- global retrieval visibility;
- durable lifecycle mutation;
- permanent confidence reduction;
- canonical MEM selection;
- cross-character or cross-session ranking influence.

### 7. RelaySLP acknowledgement

RelaySLP must not acknowledge overlay state by text similarity alone.

Acknowledgement should bind:

- character and namespace;
- session ID when present;
- source-lineage fingerprint;
- source turn or protected-source identity;
- durable receipt or deterministic no-change outcome;
- overlay revision precondition.

Possible outcomes:

```text
formed / reinforced / refined / superseded
  -> remove provisional semantic candidate
  -> durable MEM becomes normal authority

leave_as_evidence / no_change
  -> remove candidate or retain only bounded reaction evidence by policy

held / failed / recovery_required
  -> retain bounded candidate until TTL or explicit reconciliation

stale or duplicate acknowledgement
  -> idempotent no-op
```

### 8. Restart semantics

The initial implementation should treat the overlay as RAM-only and rebuildable.

A restart loses provisional continuity but must not lose Protected Source Evidence or durable MEM.

An optional short-lived checkpoint can be considered only after measuring:

- restart frequency during real use;
- continuity value;
- privacy implications;
- recovery and stale-state complexity;
- whether source replay is sufficiently cheap.

A checkpoint must remain derived state and must not become a second MEM authority.

## SCN and EMO implementation boundary

### Normalized SCN facts

Required for Shared Assessment:

- participants;
- speaker and addressee;
- ordinary versus role-play mode;
- task/project scope;
- public/private audience;
- scene identifier and semantic scope;
- quotation, hypothetical, or staged context when known.

These fields prevent context loss. They should be passed as typed facts or refs, not as free-form scene prose that invites invention.

### SCN persistence/disclosure policy

Required after candidate formation:

- persistence allowed/blocked;
- target memory scope;
- disclosure scope;
- safety sensitivity;
- user confirmation requirement.

This policy gates the operation. It must not generate content or increase factual confidence.

### Transient SCN expression allowance

Not eligible for durable formation conditioning:

- playfulness gain;
- formality gain;
- character-expression allowance;
- current response style pressure;
- current probe or disclosure impulse.

These remain online-response inputs.

### EMO

Current EMO is not eligible as durable fact or direct formation conditioning.

It may be retained as:

- a bounded reference to the character's affect at the turn;
- provisional perceived significance;
- reaction intensity;
- an episodic detail when later grounded and selected by SOUL-centered reflection.

It must not:

- increase evidence confidence;
- prove user intent or affect;
- authorize relationship-state change;
- bypass sensitive-inference or persistence gates;
- be copied automatically into Subjective MEM.

## Concurrency and failure cases

Required cases include:

- two simultaneous turns for one session;
- same turn replayed after response loss;
- duplicate sidecar extraction;
- correction racing an older update;
- eviction racing a read;
- RelaySLP acknowledgement racing a new turn;
- stream completion racing the next request;
- character or namespace change under the same frontend session ID;
- missing, malformed, or conflicting session identity;
- process restart before or after RelaySLP enqueue.

Recommended rule:

> Scope mismatch, stale revision, malformed candidate, or uncertain lineage produces no overlay mutation and never broadens authority.

## Performance assessment

The synchronous work is computationally small if bounded correctly:

- strict JSON/schema validation;
- evidence-span verification against the current turn;
- composite-key lookup;
- small-list deterministic reconciliation;
- revision-fenced RAM update;
- bounded dynamic-suffix selection.

It should not materially affect first-token latency because most work occurs at or after response finalization. The main risk is total response completion latency on streaming turns and contention under rapid same-session requests.

Required measurements:

- overlay parse/update p50 and p95;
- lock or revision-conflict rate;
- bytes and candidate count per active session;
- stream terminal-chunk overhead;
- immediate next-request visibility;
- prompt token overhead;
- TTL eviction cost;
- conversation-quality change with overlay disabled versus enabled.

## Privacy and observability

Content-bearing overlay state is runtime-private.

Default diagnostics may include only:

- schema version;
- scope completeness flags, not raw IDs;
- candidate counts;
- correction/shadow counts;
- revision conflict count;
- TTL/eviction state;
- acknowledgement outcome;
- bounded reason IDs;
- parse/update latency;
- content-free apply status.

They must not include raw user text, sidecar bodies, affect descriptions, entity values, session IDs, namespace values, or source-lineage fingerprints.

## Proposed implementation slices

### SEO-0: contract and isolated store

- exact schema and typed models;
- app-scoped bounded RAM store;
- composite scope key;
- revision fencing and idempotency;
- TTL and eviction;
- no prompt injection or Retrieval influence;
- unit and security tests.

### SEO-1: non-stream continuity

- validate semantic sidecar after non-stream response;
- bind protected source lineage;
- apply bounded overlay update before response return;
- read on the next request;
- pack one bounded provisional block;
- no durable write.

### SEO-2: Retrieval interaction

- query-facet assistance;
- compatible boost;
- session-local shadow;
- correction and uncertainty reasons;
- deterministic fallback to durable Retrieval.

### SEO-3: stream-safe finalization

- terminal-stream callback;
- finalized-turn source availability;
- bounded update before terminal completion;
- next-request race tests;
- cancellation and client-disconnect behavior.

### SEO-4: RelaySLP acknowledgement

- lineage-bound receipts;
- replay-safe removal/replacement;
- held/failure behavior;
- stale acknowledgement protection;
- no text-similarity-only cleanup.

### SEO-5: optional restart recovery

- implement only if measured value justifies it;
- derived checkpoint with expiry;
- source replay and stale-state rejection;
- no new durable MEM authority.

## Validation gates

### Functional continuity

- a new preference affects the next turn without waiting for RelaySLP;
- an explicit correction shadows the earlier session candidate;
- current-session state may shadow but not mutate durable MEM;
- unrelated queries do not receive irrelevant overlay content;
- SLP acknowledgement returns authority to durable MEM cleanly.

### Conditioning correctness

Compare:

1. Shared Assessment only;
2. Shared Assessment plus SOUL;
3. Shared Assessment plus SOUL and normalized SCN facts;
4. the recommended model plus bounded REL history;
5. the recommended model with current EMO incorrectly included;
6. direct copying of hot provisional interpretation.

The recommended model must improve scene, role-play, audience, and task-scope correctness without increasing emotional overinterpretation or transient mood persistence.

### Isolation and security

- character isolation;
- namespace isolation;
- session isolation;
- user, room, and scene fences when configured;
- missing identity fail-closed behavior;
- no global fallback;
- no content-bearing trace or header projection;
- malformed sidecar cannot alter visible text or durable state.

### Concurrency and replay

- same-session concurrent updates;
- stale revision rejection;
- response replay;
- duplicate source lineage;
- stream-to-next-request race;
- acknowledgement/update race;
- eviction/read race;
- process restart.

### Performance

- no LLM, vector, fsync, SQLite, or RelaySLP work in the synchronous update;
- bounded p50/p95 overlay latency;
- bounded memory per session and globally;
- bounded prompt overhead;
- no material normal-conversation quality regression.

## Overall feasibility conclusion

The design is implementable and fits RelayLM's target component boundaries.

The key architectural distinction is:

```text
Session Evidence Overlay
  = hot, affect- and scene-aware, provisional continuity

RelaySLP Shared Assessment
  = character-independent, normalized-scene-grounded evidence reconciliation

RelaySLP Subjective MEM formation
  = stable-SOUL-centered, bounded-REL-aware, EMO-decoupled reflection

Scene policy
  = persistence and disclosure gate

RelayMEM
  = durable governed authority
```

This preserves the interesting property that the character's immediate emotional interpretation remains visible in the continuing conversation while preventing transient EMO or expression pressure from becoming durable truth.

The implementation should proceed only through explicit SEO slices and evaluation gates. This evidence record does not itself accept the architecture or authorize production behavior.