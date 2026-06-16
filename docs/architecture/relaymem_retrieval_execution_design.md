# RelayMEM Retrieval Execution Design

## Purpose

RelayMEM Retrieval is the synchronous, read-only memory path for the current response.

```text
Retrieval improves the current answer.
RelaySLP improves future memory.
```

Retrieval must not edit RelayMEM, mutate RelaySOUL, resolve ambiguous references silently, or own prompt layout.

Current implementation status and sequencing remain in [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md). This document defines the stable responsibility and artifact boundaries.

## Canonical runtime position

```text
User input
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval, only when RelayINT and RelaySCN allow it
  -> RelayCTX Repack
  -> Main LLM
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> User / TTS / Avatar output
```

RelayREF is post-generation only. RelayMEM Retrieval must never depend on RelayREF observations for the same request.

Reference and recall ownership:

- RelayINT resolves current-turn references against RelayCTX working state.
- RelayINT decides whether long-term retrieval is needed.
- RelaySCN limits the allowed memory scope and safety posture.
- RelayMEM performs the bounded read.
- RelayCTX decides how selected evidence is packed.

## Inputs

RelayMEM Retrieval consumes only validated request-local inputs:

```text
- current user turn or a bounded retrieval query derived from it
- RelayINT retrieval decision
- resolved or confirmed reference scope
- RelaySCN scene_policy and relaymem_retrieval_scope
- character/user/project/session namespaces
- RelayCTX memory token-budget hint
- approved memory index and compiled MEM pages
- runtime configuration and compatibility gates
```

A valid RelayINT input should expose at least:

```yaml
mem_query_needed: true
mem_query_reason: explicit_recall_request
reference_resolution_state: resolved
confirmed_scope: current_project
```

Retrieval must remain blocked when:

- the reference is unresolved or requires confirmation,
- RelayINT did not authorize retrieval,
- RelaySCN limits the request to current context only,
- the scene policy blocks external memory evidence,
- required namespace or compatibility information is malformed.

## Outputs

Retrieval produces two different representations.

### Runtime-private retrieval result

The request-local result may contain content needed by RelayCTX:

```yaml
relaymem_retrieval_runtime:
  persistence: request_local
  retrieval_scope: project_context
  reference_resolution_state: resolved
  selected_candidates:
    - page_id: projects/relaylm
      evidence_id: evidence:0
      memory_kind: project_state
      confidence: 0.91
      ranking_score: 0.87
      token_estimate: 180
      bounded_snippet: "..."
  blocked_candidates: []
  ctx_block_candidate:
    estimated_tokens: 180
    entries:
      - evidence_id: evidence:0
        included: true
  fallback_reason: null
```

This artifact is content-bearing. It must remain request-local or use an explicitly protected diagnostic surface with separate access control and retention.

### Content-free retrieval projection

Default trace and audit surfaces receive only an allowlisted projection:

```yaml
relaymem_retrieval_projection:
  schema_version: relaymem.retrieval_projection.v1
  retrieval_requested: true
  retrieval_scope_class: project_context
  reference_resolution_state: resolved
  selected_count: 1
  blocked_count: 0
  candidate_count: 1
  ctx_block_candidate_present: true
  evidence_snippet_present: true
  token_budget: 800
  estimated_tokens: 180
  budget_exhausted: false
  fallback_reason: none
  payload_mutation_applied: false
```

Default projections must not contain:

- raw or normalized user text,
- query terms or `term_hints`,
- MEM page paths, titles, summaries, or snippets,
- root paths or local filesystem details,
- prompt preview text,
- backend message bodies,
- arbitrary nested runtime artifacts.

Use typed allowlisted projection code rather than generic recursive sanitization.

## Retrieval flow

```text
RelayINT retrieval decision
  -> namespace and scene-scope validation
  -> bounded query preparation
  -> compiled-memory index search
  -> candidate page loading
  -> ranking
  -> safety and authority filtering
  -> evidence bounding
  -> token-budget candidate assembly
  -> RelayCTX handoff
```

### Query preparation

The query may combine:

- explicit nouns from the current user turn,
- RelayINT topic and action anchors,
- confirmed recall scope,
- RelaySCN scene type and task state,
- approved project or concept hints.

The runtime query is content-bearing and must not be copied into default trace records.

### Candidate sources

Preferred source order:

1. approved compiled-memory index,
2. selected project, concept, or session summaries,
3. selected full MEM pages,
4. supporting claim pages,
5. raw evidence only under an explicit verification path.

Normal retrieval should prefer compiled summaries over raw logs.

### Ranking

Ranking should remain bounded and explainable. Useful axes include:

- semantic match,
- current-task relevance,
- scope match,
- source approval level,
- confidence,
- stability,
- recency,
- contradiction state,
- estimated token cost.

Ranking scores are runtime-private. Default diagnostics should expose counts or bands, not source text.

## Safety and authority filter

Block from ordinary RelayCTX packing:

- unapproved RelaySOUL candidates,
- explicit-approval-required content,
- unresolved contradictions,
- stale or superseded project state when a current source exists,
- raw affect estimates or sensitive attribute inference,
- low-confidence personal inference,
- recovery-generated memory that has not passed a later persistence review,
- candidates outside the active namespace or scene scope.

Retrieval must not convert blocked candidates into prompt hints merely because the token budget has space.

## Token-budget boundary

RelayCTX owns the overall prompt budget and supplies the memory budget or budget hint. RelayMEM Retrieval:

- estimates candidate cost conservatively,
- orders candidates by approved priority,
- stops before exceeding the memory budget,
- returns omitted and blocked counts,
- does not attempt to fill unused budget,
- does not mutate stable persona blocks to make room.

Tokenizer-exact claims must not be made when only an estimate is available.

## RelayCTX handoff

RelayMEM returns evidence candidates or a `ctx_block_candidate`; RelayCTX owns final layout and rendering.

```text
RelayMEM
  selected evidence + provenance + token estimates

RelayCTX
  final block selection
  placement after stable persona sources
  overall budget degradation
  backend message construction
```

RelayMEM must not insert a backend `system` message directly as its semantic responsibility. Any existing compatibility helper that performs gated payload insertion is an implementation mechanism orchestrated through RelayCTX/PipelineContext and must preserve the same ownership boundary.

## Reference ambiguity contract

```text
ambiguous reference
  -> RelayINT asks or prepares clarification
  -> no long-term retrieval

resolved or explicitly confirmed recall scope
  -> RelayINT may request retrieval
  -> RelayMEM reads only the allowed scope
```

A retrieval miss is not permission to broaden the scope silently.

## Fallback behavior

Valid fallback reasons include:

```text
retrieval_not_requested
reference_unresolved
scene_policy_blocks_memory
current_context_only
no_relevant_memory
all_candidates_blocked
token_budget_exhausted
index_missing
memory_store_unavailable
namespace_invalid
```

When memory is optional, RelayCTX proceeds without a RelayMEM block. When the user request is memory-dependent, RelayINT/RelayRUN may require clarification, a blocked state, or an approved recovery path.

## Compatibility boundary

Tool calls, structured output, multimodal content, and provider-specific message shapes must remain unchanged unless a dedicated compatibility gate allows managed repacking.

Retrieval evidence must not be used to reconstruct or alter an active tool transaction.

## Persistence boundary

Retrieval is read-only:

- no page update,
- no index update,
- no raw-event append as a side effect of retrieval,
- no RelaySOUL proposal,
- no user-preference write,
- no relationship update.

Those actions belong to deferred RelaySLP and their applicable scene, approval, and persistence gates.

## Non-goals

RelayMEM Retrieval does not:

- classify the scene,
- resolve ambiguous references,
- inspect the generated answer,
- own prompt ordering,
- produce user-visible clarification text,
- write memory,
- mutate RelaySOUL,
- expose content-bearing retrieval artifacts through default trace/audit projections.

## Summary

```text
RelaySCN policy
  + RelayINT retrieval decision and confirmed scope
  -> RelayMEM read-only selection
  -> runtime-private evidence artifact
  -> content-free diagnostic projection
  -> RelayCTX final packing
```
