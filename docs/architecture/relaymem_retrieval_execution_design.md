# RelayMEM Retrieval Execution Design

## Purpose

RelayMEM Retrieval is the synchronous, read-only memory path for the current response.

```text
Retrieval improves the current answer.
RelaySLP improves future memory.
```

This document separates the **current implemented `relaymem_retrieval.v0` path** from the **target INT-driven retrieval and artifact boundary**.

Current implementation status and sequencing remain in [Pipeline Implementation Plan](pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

## Current implemented path: `relaymem_retrieval.v0`

The current implementation is centered on `build_relaymem_retrieval_dry_run_artifact()` in `relaylm/relaymem_retrieval.py`.

### Current runtime order

The current request path is approximately:

```text
request/profile compilation
  -> Input-side RelayEMO
  -> RelaySCN v0 scene-policy artifact
  -> RelayINT compatibility reference-repair wrapper
       historical RelayREF-shaped artifact
  -> optional RelayINT fast-path dry-run artifact
  -> RelayMEM Retrieval v0
  -> later RelayCTX/runtime injection phases
  -> backend forwarding
```

The variable and function boundary used by Retrieval still names the compatibility input `relayref_artifact`. Its producer is now the RelayINT compatibility wrapper around the historical input-side RelayREF implementation.

Therefore, the current path is semantically moving toward RelayINT, but the Retrieval function does **not yet consume the independent `relayint_fast_path_dry_run.v0` decision as its primary typed input**.

### Current inputs

Current Retrieval v0 accepts inputs equivalent to:

```text
relayscn_scene_policy_artifact
relayref_artifact
messages
token_budget
store_diagnostics
candidate/snippet/apply feature flags and limits
```

Current behavior:

- unresolved-reference blocking is derived from the historical RelayREF-shaped compatibility artifact,
- query terms are derived from the latest user text in `messages`,
- RelaySCN v0 controls scene and retrieval scope,
- file-store diagnostics and candidates feed selection/snippet planning,
- the helper remains dry-run/diagnostics-oriented even though later gated runtime-injection phases may consume its candidates.

### Current artifact shape

The current helper returns one broad artifact:

```yaml
relaymem_retrieval_v0:
  artifact_version: relaymem_retrieval.v0
  diagnostics_only: true
  apply_allowed: false
  retrieval_scope: project_context
  scene_type: design_talk
  query_summary: {}
  selected_mem_candidates: []
  blocked: []
  ctx_block: null
  ctx_block_candidate: {}
  ctx_block_snippet_candidate: {}
  ctx_injection_plan: {}
  snippet_runtime_injection_plan: {}
  snippet_candidates: []
  evidence_envelope: {}
  fallback_reason: memory_store_not_configured
  token_budget: {}
  used_tokens: 0
  persistence_block: false
  persistence_block_reasons: []
  apply_decision: blocked
  apply_readiness_score: 0.0
  apply_blocked_reasons: []
  snippet_apply_decision: blocked
  store_diagnostics: {}
```

This artifact may contain content-bearing or sensitive operational fields, including:

- query summaries or term-derived metadata,
- page and store metadata,
- selected candidates,
- snippet candidates/evidence,
- root/path-related store diagnostics,
- runtime-injection preview material.

`diagnostics_only: true` does **not** make the whole artifact safe for generic persistence.

The typed audit projector introduced by the content-free trace work must reduce this artifact to an allowlisted content-free subset before persisted trace/audit output. Unknown or content-bearing nested fields must be omitted.

### Current limitations

The current v0 path does not yet provide the target contract described below:

- no dedicated `relayint.intent.v1` input,
- no explicit confirmed-scope typed handoff,
- no clean split between a runtime-private retrieval result and a public content-free projection at the producer boundary,
- no replacement of the historical `relayref_artifact` parameter name/shape,
- raw request messages still participate in query preparation,
- one large artifact carries both runtime planning and diagnostic metadata.

## Target canonical runtime position

The target architecture is:

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

RelayREF is post-generation only. Target RelayMEM Retrieval must never depend on same-request output-side RelayREF observations.

Reference and recall ownership:

- RelayINT resolves current-turn references against RelayCTX working state,
- RelayINT decides whether long-term retrieval is needed,
- RelaySCN limits allowed memory scope and safety posture,
- RelayMEM performs the bounded read,
- RelayCTX decides final evidence packing.

## Target typed inputs

A future typed RelayINT handoff should expose fields equivalent to:

```yaml
relayint_intent:
  schema_version: relayint.intent.v1
  mem_query_needed: true
  mem_query_reason: explicit_recall_request
  reference_resolution_state: resolved
  confirmed_scope: current_project
```

Target Retrieval consumes only validated request-local inputs:

```text
current user turn or a bounded derived retrieval query
RelayINT retrieval decision
resolved or confirmed reference scope
RelaySCN scene_policy and retrieval scope
validated namespaces
RelayCTX memory-budget hint
approved compiled-memory index/pages
runtime compatibility gates
```

Target Retrieval remains blocked when:

- the reference is unresolved or needs confirmation,
- RelayINT did not authorize retrieval,
- RelaySCN limits the request to current context,
- the scene policy blocks external memory evidence,
- namespace or compatibility information is malformed.

## Target output split

### Runtime-private retrieval result

The request-local result may contain content required by RelayCTX:

```yaml
relaymem_retrieval_runtime:
  schema_version: relaymem.retrieval_runtime.v1
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

This artifact is content-bearing and remains request-local or in an explicitly protected diagnostic domain.

### Content-free retrieval projection

Default persisted trace/audit receives a typed allowlisted projection:

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
  content_free: true
```

Default projections must not contain:

- raw/normalized user text,
- query terms or term hints,
- page paths/titles/summaries/snippets,
- root paths or filesystem details,
- prompt preview text,
- backend message bodies,
- arbitrary nested runtime artifacts.

Use typed projection code, not generic recursive sanitization.

## Target retrieval flow

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

Preferred candidate source order:

1. approved compiled-memory index,
2. selected project/concept/session summaries,
3. selected full MEM pages,
4. supporting claim pages,
5. raw evidence only under an explicit verification path.

Normal retrieval should prefer compiled summaries over raw logs.

## Safety and authority filter

Block from ordinary RelayCTX packing:

- unapproved RelaySOUL candidates,
- explicit-approval-required content,
- unresolved contradictions,
- stale/superseded project state when a current source exists,
- raw affect estimates or sensitive-attribute inference,
- low-confidence personal inference,
- recovery-generated memory without later persistence review,
- candidates outside the active namespace or scene scope.

Retrieval must not fill unused token budget with blocked or weak evidence.

## RelayCTX handoff

RelayMEM returns candidates, provenance, and token estimates. RelayCTX owns final inclusion, layout, degradation, and backend message construction.

Any current compatibility helper that performs gated payload insertion is an implementation mechanism, not RelayMEM's semantic ownership.

## Persistence boundary

Retrieval is read-only:

- no page/index update,
- no raw-event append as a retrieval side effect,
- no RelaySOUL proposal,
- no preference or relationship write.

Those actions belong to deferred RelaySLP and applicable scene/approval/persistence gates.

## Required migration scope

A future implementation migration should update together:

1. rename/remove the historical `relayref_artifact` Retrieval input,
2. define a typed RelayINT-to-Retrieval handoff,
3. use canonicalized current-turn evidence instead of raw message arrays,
4. split runtime-private Retrieval data from the content-free producer projection,
5. update app/PipelineContext wiring,
6. update runtime-injection consumers,
7. update trace projectors,
8. update Retrieval and integration smoke tests,
9. preserve compatibility through explicit schema/version handling.

## Summary

```text
current
  relaymem_retrieval.v0
  SCN v0 + historical RelayREF-shaped INT compatibility input
  + raw messages + broad diagnostics/runtime artifact

target
  typed RelayINT decision + SCN policy
  -> read-only Retrieval
  -> runtime-private evidence artifact
  -> content-free persisted projection
  -> RelayCTX final packing
```
