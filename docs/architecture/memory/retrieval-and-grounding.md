---
relaylm_doc_type: subsystem_architecture
relaylm_authority: ordinary_memory_retrieval_selection_and_grounding_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - ordinary memory authority selection changes
  - Primary or Subjective retrieval ownership changes
  - selected-memory handoff or grounded-recall policy changes
  - Subjective projection admission or usage-finalization changes
  - Primary compatibility reader or fallback retirement changes
relaylm_not_authoritative_for:
  - repository-wide current implementation completion or sequencing
  - exact RT-1 durable cutover state or retirement approval
  - exact retrieval request, projection, usage-event, or grounding schemas
  - exact ranking, embedding, lexical matching, tokenization, or candidate-budget algorithms
  - memory formation, lifecycle mutation, or storage-repair semantics
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source:
  - ../../adr/0003-subjective-mem-direction.md
  - ../../adr/0005-subjective-mem-storage-authority.md
relaylm_related_authority:
  - ../relaymem_retrieval_execution_design.md
  - ../subjective-mem-retrieval-projection-hard-cutover.md
  - ../e1r4_retrieval_response_grounding.md
  - ../e1r5_primary_mem_recall_candidate_bridge.md
  - ../integration_i1_primary_mem_two_turn_recall.md
  - ../phase_i4d_primary_retrieval_exclusion.md
  - ../acg3_retrieval_query_normalization.md
  - ../relaymem_slp_current_target.md
  - ../runtime/request-response-pipeline.md
  - formation.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - ordinary Retrieval maintainers
  - RelayCTX and grounded-recall maintainers
  - RT-1 cutover and Primary-retirement reviewers
relaylm_authority_level: subsystem
---
# Ordinary Memory Retrieval and Grounding

## Purpose

This page is the canonical subsystem architecture for ordinary durable-memory Retrieval after RT-1 established one reader authority per managed request.

It owns the stable responsibility split between:

1. selecting exactly one ordinary durable-memory authority, or none;
2. performing candidate discovery and eligibility only inside that selected authority;
3. handing already-selected evidence to one shared request-side grounding policy; and
4. keeping runtime-private evidence separate from content-free public diagnostics.

It does not own exact runtime schemas, ranking algorithms, lifecycle mutation, storage repair, or the repository-wide completion state. Exact current implementation and retirement status remain owned by [Project Status](../../PROJECT_STATUS.md), while the detailed hard-cutover state machine remains owned by [RT-1 Subjective MEM Retrieval Projection and Hard Cutover](../subjective-mem-retrieval-projection-hard-cutover.md).

## Stable authority model

Ordinary Retrieval is synchronous and read-only with respect to canonical memory. Its first semantic decision is which durable-memory family is allowed to serve the request.

```text
managed request
  -> exact ordinary-memory reader decision
  -> selected authority only
  -> scoped candidate discovery and eligibility
  -> request-local selected evidence
  -> RelayCTX repack
  -> shared grounded-recall policy
  -> backend-bound request
```

The reader decision dominates configuration, store presence, old success, ranking output, and grounding output. None of those subordinate facts may choose or restore a memory authority.

At most one durable-memory family is active for one ordinary request. Primary and Subjective evidence are never ordinary co-authorities and are never combined as a fallback strategy.

## Current reader classes

The current RT-1 reader decision retains three bounded values while exposing only one ordinary serving family:

```text
primary_only
  -> ordinary Primary serving is retired
  -> fail closed to `neither` / no-reader behavior
  -> no Primary root resolution, store open, discovery, selection, recall, fallback, or evidence release

neither
  -> no ordinary durable-memory reader

subjective_only
  -> finalized Subjective reader only
  -> no Primary probing or fallback
```

A missing, malformed, foreign, stale, or otherwise invalid decision fails closed through the cutover owner rather than selecting another family. `primary_only` is not a current serving capability; its presence as a decision value does not restore the retired reader. `neither` is a deliberate no-reader state. `subjective_only` is the sole ordinary serving state, and failed, refused, empty, stale, or malformed Subjective retrieval releases no durable-memory evidence and never falls back to Primary.

## Authority selection precedes memory access

The ordinary Retrieval facade resolves the immutable reader decision before touching an ordinary memory family.

This ordering is a security and semantic boundary:

- a configured Primary root is not permission to read Primary;
- a valid Subjective projection is not permission to serve Subjective before the reader decision selects it;
- a previous successful Primary or Subjective request does not carry authority into a later request;
- query intent, scene policy, ranking score, grounding status, or empty results do not change the selected family;
- a request-local retrieval artifact cannot become a durable selector by being persisted or replayed.

Execution offload, thread scheduling, and process placement are runtime mechanics only and do not own reader authority.

## Retrieval inputs and narrowing

After authority selection, ordinary Retrieval may consume bounded request context such as:

- RelayINT retrieval/reference intent;
- RelaySCN scene and audience policy;
- current request messages or normalized query hints;
- exact character/workspace/namespace/scope bindings;
- the selected family's current source and lifecycle evidence;
- bounded candidate and token budgets.

RelayINT and RelaySCN may narrow, block, or shape retrieval inside the already-selected family. They cannot override the RT-1 reader decision.

Query normalization, lexical matching, embeddings, vectors, similarity, and ranking are candidate-generation or ordering mechanisms only. They cannot make a stale, hidden, cross-scope, unauthorized, corrupt, or non-current revision eligible.

## Primary post-retirement handling

An exact `primary_only` decision performs no ordinary durable-memory retrieval. Retrieval must not resolve a Primary root, open a Primary store, inspect controls, discover or rank candidates, invoke historical E1-R5 fallback, select Primary evidence, or release it to grounding.

Retained Primary modules and artifacts may support explicitly classified read-only admin/history, observation, mutation governance, recovery, characterization, migration, and regression responsibilities. None of those responsibilities is an ordinary Retrieval branch, reader, ranking owner, or fallback.

## Subjective ordinary retrieval

Inside an exact `subjective_only` decision, ordinary Retrieval uses only finalized Subjective authority.

The stable flow is:

```text
subjective_only
  -> current projection generation bound to canonical source authority
  -> exact current eligible Subjective revision selection
  -> runtime-private prepared handoff
  -> exact durable content-free usage finalization
  -> sealed admitted handoff
  -> fresh request-local grounding evidence
```

The retrieval projection is disposable derived state. Canonical Subjective Markdown, exact current selectors, finalized publication/lifecycle receipts, and their accepted authorization lineage remain authoritative.

A projection row is not eligible merely because it exists. Selection must remain bound to one exact current revision, canonical source, accepted scope, supported lifecycle/mutation state, and current projection generation.

Only the admitted handoff released after exact usage finalization may release Subjective evidence to the request path. Projection disagreement, source disagreement, stale generation, selection refusal, empty selection, usage-finalization failure, conflict, or malformed state releases no durable-memory evidence.

The usage ledger is evidence that an exact admitted selection was durably accounted for. It is not a second memory store, a ranking authority, or a fallback selector.

## Eligibility before ranking

Across any selected family, candidate ordering occurs only after mandatory eligibility constraints.

Stable exclusion classes include evidence that is:

- not current or not the latest accepted revision;
- hidden, held, superseded, purged, prepared, or recovery-required;
- in a non-retrieval mutation state;
- outside the admitted character/workspace/participant/relationship/scene scope;
- unsupported, corrupt, ambiguous, or unverifiable under the selected family's canonical contracts;
- unsafe by path or file-type rules where filesystem-backed evidence is involved;
- excluded by current lifecycle or retrieval-visibility policy.

Pinning may be a bounded ordering hint only after eligibility. Similarity, usage, salience, conviction, and relevance never override currentness, scope, lifecycle, authorization, or disclosure boundaries.

## Shared grounding boundary

Candidate discovery and reader selection end before response grounding begins.

The shared grounding policy consumes already-selected ordinary-memory evidence from the family named by the request's ordinary-memory authority:

```text
selected evidence from exactly one authority
  -> RelayCTX repack
  -> grounded-recall context
  -> support classification
  -> unsupported-detail suppression
  -> backend-bound request
```

Grounding is storage-neutral at this boundary. It does not probe another family, choose a reader, infer fallback permission, or combine Primary and Subjective selections.

The live E1-R4 implementation remains the detailed compatibility/implementation source for the grounding policy. Its stable responsibility is to distinguish supported, inferred, ambiguous, excluded, or unsupported recalled detail and to prevent a request for unsupported detail from becoming a fabricated remembered fact.

If no selected ordinary-memory evidence exists, grounding produces a bounded no-evidence result rather than claiming remembered support.

## Provenance and support

Grounding judges support from the already-admitted evidence shape. It does not reinterpret storage existence, cutover state, or a lifecycle receipt as semantic support.

Stable support rules include:

- accepted user-origin evidence may directly support a recalled fact;
- accepted scene or other provenance may support bounded inference without becoming a direct user assertion;
- assistant acknowledgement, speculation, decoration, or unknown provenance does not become a directly supported user fact;
- missing provenance fails closed;
- lifecycle- or scope-excluded evidence is not restored by grounding;
- Pin does not create support or bypass exclusion;
- held/governance evidence does not become ordinary recalled support until its owning authority makes it eligible.

The backend instruction may distinguish inference from direct support and suppress unsupported names, dates, quantities, preferences, relationships, causes, or other detail classes requested by the user when the admitted evidence does not support them.

## Request-local private evidence and public diagnostics

Selected memory prose and grounded backend context are runtime-private, request-local data.

They must not be copied into generic pipeline results, durable public diagnostics, trace projections, workflow logs, stdout/stderr, or browser-readable audit payloads merely because Retrieval succeeded.

Public and durable diagnostic surfaces remain content-free. They may expose bounded status, counts, booleans, reason identifiers, authority class, eligibility/fallback counts, grounding status, or omission flags, but not raw memory text, prompt text, store roots, paths, namespaces, lineage, digests, claim/lease material, or exact private identities.

A request-local artifact may contain content-bearing fields even when one nested diagnostic projection is content-free. Callers must use the typed projection intended for persistence rather than serializing an entire private runtime artifact.

## Failure model

Retrieval fails closed at the owning boundary rather than changing memory authority.

Examples:

```text
invalid reader decision
  -> no unauthorized memory-family access

primary_only
  -> retired Primary reader remains unavailable
  -> no Primary access or evidence release
  -> no Subjective substitution

neither
  -> no durable-memory retrieval

subjective_only projection/selection/finalization failure
  -> no admitted durable-memory evidence
  -> no Primary fallback

grounding/provenance/support failure
  -> omit or suppress unsupported recalled detail
  -> do not choose a different reader
```

Retrieval failure never authorizes canonical memory mutation or post-hoc visible-response rewriting.

## Relationship to formation and mutation

Ordinary Retrieval improves the current answer; deferred formation improves future memory.

```text
interactive path
  -> read-only ordinary Retrieval
  -> Main LLM response
  -> finalized Evidence

out-of-band path
  -> assessment / formation / lifecycle authority
  -> canonical durable memory changes
```

Retrieval never writes canonical memory, lifecycle state, relationship state, preferences, or RelaySOUL state. A later lifecycle mutation invalidates or excludes stale retrieval evidence through the owning current-state/projection contracts; Retrieval does not repair that mutation.

## Current migration and retirement boundary

The stable architecture is one-authority selection plus one common grounding policy. Primary ordinary-reader/fallback execution is retired; separately classified Primary admin, mutation, recovery, characterization, migration, and regression surfaces may remain without serving authority.

Lane D documentation canonicalization does not authorize deleting runtime, tests, migration evidence, or operational consumers before exact Lane R dependency review completes.

The retired Primary serving path does not require a second grounding design. The same storage-neutral grounding responsibility continues to consume already-selected evidence from the surviving ordinary authority.

## Source and evidence disposition

This canonical page absorbs stable architecture from the current Retrieval execution design and the E1/I1/RT-1 source family. Those source pages remain valid for their narrower roles while exact consumers still depend on them:

- `relaymem_retrieval_execution_design.md` — current implementation and R5 transition detail;
- `subjective-mem-retrieval-projection-hard-cutover.md` — accepted RT-1 cutover/projection authority;
- `e1r4_retrieval_response_grounding.md` — grounding implementation/regression handoff;
- `e1r5_primary_mem_recall_candidate_bridge.md` — Primary-only compatibility/evaluation evidence;
- `integration_i1_primary_mem_two_turn_recall.md` — historical Primary two-turn compatibility proof;
- `phase_i4d_primary_retrieval_exclusion.md` — Primary lifecycle/currentness compatibility evidence.

They are not competing permanent subsystem-architecture parents. Their final retirement or evidence disposition is handled atomically after their continuing consumers and R5/R6 removal gates are satisfied.

## Stable invariants

- The ordinary reader decision is resolved before ordinary memory-family access.
- At most one durable-memory authority serves an ordinary request.
- `neither` is a valid no-reader state.
- No empty, failed, stale, or refused Subjective result falls back to Primary.
- Candidate discovery and ranking never override lifecycle, scope, currentness, authorization, or disclosure eligibility.
- Subjective evidence is released only through its exact admitted/finalized handoff.
- Grounding consumes only already-selected evidence from the named authority.
- Grounding never selects a reader or combines memory families.
- Unsupported remembered detail is suppressed rather than fabricated.
- Content-bearing selected evidence remains request-local and private.
- Public/audit projections remain content-free.
- Retrieval is read-only and does not become a mutation or recovery authority.
- Primary compatibility retirement is an explicit owned migration, not fallback-driven behavior drift.

## Non-goals

This architecture does not authorize:

- RT-1D-R5/R6 implementation or Primary deletion;
- dual read, dual write, reader precedence, or cross-authority fallback;
- automatic Primary-to-Subjective content migration;
- lifecycle mutation, storage repair, queue mutation, or worker mutation;
- a specific ranking/vector/search backend;
- generic persistence of request-private evidence;
- browser-owned memory authority;
- post-hoc rewriting of an already delivered visible response;
- RelaySOUL mutation, Secondary consolidation, or media-runtime behavior.
