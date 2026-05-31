# RelayMEM Retrieval Execution Design

Date basis: 2026-05-31 JST

## Purpose

RelayMEM Retrieval execution is the runtime memory read path. It selects safe, relevant, token-budgeted compiled memory and passes it to RelayCTX.

Retrieval improves the current answer. It must not edit MEM or RelaySOUL.

## Core principle

```text
Retrieval only reads memory.
SLP edits or proposes memory changes.
```

Retrieval is latency-sensitive and should remain lightweight.

## Position in the RelayLM runtime stack

Canonical stack with RelayMEM retrieval:

```text
User input
↓
Input-side RelaySCN
↓
Input-side RelayEMO
↓
RelayMEM Retrieval
↓
RelayCTX Repack
↓
Main LLM
↓
RelayCTX Unpack
↓
Return-side RelayEMO
↓
Output-side RelaySCN
↓
User output
```

RelaySCN provides scene and memory-scope policy. RelayEMO may provide affect estimates for scene-aware gating, but raw affect estimates must not be persisted as long-term facts.

## Inputs

```text
Retrieval input:
- user input
- scene_state
- task_state
- memory_scope from RelaySCN
- token budget from RelayCTX
- memory index
- candidate MEM pages
- safety/persistence policy
```

## Outputs

```text
Retrieval output:
- selected memory candidates
- blocked memory candidates
- token-budgeted ctx_block
- diagnostics
- fallback reason, if any
```

## Execution flow

```text
user input
↓
scene/task estimate
↓
retrieval query build
↓
index search
↓
candidate pages load
↓
rank/filter
↓
safety gate
↓
token budget pack
↓
RelayCTX context block
↓
diagnostics
```

## Retrieval query build

Query should combine:

- user input
- route/model role
- scene_type
- task_state
- current project/page hints
- explicit user request terms

Example:

```json
{
  "query": "RelayMEM SLP Retrieval MVP design",
  "scene_type": "design_talk",
  "task_state": "architecture_design",
  "memory_scope": "project_and_concepts"
}
```

## Candidate sources

MVP should search compiled memory first.

Priority:

```text
1. memory/mem/index.md
2. selected project/concept summaries
3. selected full MEM pages
4. supporting claim pages
5. raw evidence only when verification is needed
```

Runtime should normally use compiled summaries rather than raw logs.

## Ranking axes

MVP ranking should be simple and explainable.

```yaml
ranking_score:
  semantic_match:
    description: Match with user input and query.

  task_relevance:
    description: Relevance to current scene/task.

  recency:
    description: Whether the memory is recently updated.

  stability:
    description: Whether the memory is stable or transient.

  source_level:
    description: raw, interpreted, synthesized, or user_approved.

  confidence:
    description: Confidence assigned by SLP or source metadata.

  safety_allowed:
    description: Whether current scene policy allows use.

  token_cost:
    description: Estimated token cost for packing.
```

Simple scoring formula for MVP:

```text
score =
  semantic_match
+ task_relevance
+ stability_bonus
+ user_approved_bonus
+ recency_bonus
- token_cost_penalty
- safety_risk_penalty
```

## Safety filter

Retrieval must block unsafe or unapproved memory from normal context packing.

Block from CTX:

- unapproved SOUL candidates
- raw user_affect_estimate
- low-confidence user attribute inference
- contradiction-unresolved claims
- stale project_state
- explicit_approval_required content
- recovery-scene-generated memory
- memory marked never_auto_promote

Blocked memory can appear in diagnostics but not in the generated CTX block.

## Token budget packing

RelayCTX should set or pass the memory token budget.

Example default:

```yaml
retrieval_budget:
  total_mem_tokens: 1200
  priority_order:
    - current project_state
    - user-approved preferences or constraints
    - relevant concept summaries
    - supporting claims
    - raw evidence snippets when needed
```

MVP should avoid rigid fixed quotas. It should pack by priority and stop when the token budget is exhausted.

## CTX block contract

Retrieval should return a completed block that RelayCTX can insert.

Example:

```text
[RelayMEM Context]

Scene:
- design_talk

Relevant project state:
- RelayMEM is being designed as a long-term memory compile layer.
- SLP handles memory consolidation, lint, and safe promotion.
- Retrieval handles runtime selection and CTX packing.

Relevant constraints:
- Do not directly mutate RelaySOUL from MEM.
- Do not persist raw user_affect_estimate as a long-term fact.
- Use approval gate for long-term identity or relationship changes.

Relevant concepts:
- Raw sources are primary evidence.
- MEM pages are synthesized secondary memory.
- index.md/log.md support retrieval and audit.

Retrieval diagnostics:
- selected_pages: projects/relaymem, concepts/slp, concepts/retrieval
- blocked_pages: none
[/RelayMEM Context]
```

## Retrieval artifact contract

Suggested dataclass shape:

```python
@dataclass
class RelayMemRetrievalCandidate:
    page_id: str
    memory_kind: str
    title: str
    summary: str
    selected_snippet: str | None
    source_level: str
    stability: str
    safety_scope: str
    confidence: float
    ranking_score: float
    token_estimate: int
    selection_reason: str
```

```python
@dataclass
class RelayMemRetrievalResult:
    retrieval_run_id: str
    query: str
    scene_state: str
    task_state: str | None
    token_budget: int
    used_tokens: int
    selected: list[RelayMemRetrievalCandidate]
    blocked: list[dict]
    fallback_reason: str | None
    ctx_block: str
    diagnostics: dict
```

## Example result

```json
{
  "retrieval_run_id": "ret_20260531_001",
  "query": "RelayMEM SLP Retrieval MVP design",
  "scene_state": "design_talk",
  "task_state": "architecture_design",
  "token_budget": 1200,
  "used_tokens": 640,
  "selected": [
    {
      "page_id": "projects/relaymem",
      "memory_kind": "project_state",
      "title": "RelayMEM",
      "summary": "RelayMEM is a long-term memory compile layer with separate SLP and Retrieval paths.",
      "selected_snippet": null,
      "source_level": "synthesized",
      "stability": "session_stable",
      "safety_scope": "free_to_update",
      "confidence": 0.92,
      "ranking_score": 0.88,
      "token_estimate": 180,
      "selection_reason": "current_project_state"
    }
  ],
  "blocked": [
    {
      "page_id": "affect/session_abc",
      "reason": "raw_user_affect_estimate_not_allowed_for_long_term_ctx"
    }
  ],
  "fallback_reason": null,
  "ctx_block": "[RelayMEM Context]...[/RelayMEM Context]",
  "diagnostics": {
    "selected_count": 1,
    "blocked_count": 1,
    "budget_exhausted": false
  }
}
```

## Scene-based retrieval policy

RelaySCN should influence memory scope.

Suggested defaults:

```yaml
scene_policy:
  casual_chat:
    retrieval_scope: light_profile_and_recent_project
    allow_user_preferences: true

  design_talk:
    retrieval_scope: project_and_concepts
    allow_user_preferences: true

  implementation_work:
    retrieval_scope: current_project_and_code_constraints
    allow_user_preferences: true

  review_work:
    retrieval_scope: current_context_and_project_constraints
    allow_user_preferences: limited

  formal_document:
    retrieval_scope: current_context_only_or_explicit_docs
    persistence_block: true

  medical_or_safety:
    retrieval_scope: current_context_only
    persistence_block: true

  recovery:
    retrieval_scope: current_context_only
    persistence_block: true
    user_confirmation_required: true
```

## Fallback behavior

Retrieval should not force memory into context.

Fallback reasons:

```text
no_relevant_memory
all_candidates_blocked
token_budget_exhausted
index_missing
memory_store_unavailable
scene_policy_blocks_memory
low_confidence_candidates_only
contradiction_unresolved
```

In fallback, RelayCTX should proceed with no RelayMEM block or a minimal diagnostic note.

## Diagnostics

Diagnostics should be visible in trace/debug mode.

Include:

- retrieval_run_id
- query
- scene_state
- selected pages
- blocked pages
- selection reasons
- blocked reasons
- token budget
- used tokens
- fallback reason
- index/source version if available

## Non-goals

- Do not update memory during Retrieval.
- Do not mutate RelaySOUL.
- Do not retrieve raw affect estimates into CTX.
- Do not pack unapproved SOUL candidates.
- Do not require vector DB in MVP.
- Do not run heavy lint/consolidation in the runtime path.

## Summary

RelayMEM Retrieval is the safe runtime read path:

```text
user input + scene/task -> index search -> candidate pages -> safety filter -> token-budgeted CTX block
```

It keeps runtime memory useful, bounded, and auditable while leaving memory editing to RelaySLP.

---

## Runtime dry-run artifact contract

RelayLM runtime diagnostics emit a diagnostics-only `relaymem_retrieval_artifact` for the current request. The MVP artifact consumes RelaySCN scene policy and RelayREF recovery guidance, but it does not search a long-term memory store, does not build a context block, does not edit MEM/SOUL, and does not mutate the forwarded backend payload.

```yaml
relaymem_retrieval_artifact:
  artifact_version: relaymem_retrieval.v0
  diagnostics_only: true
  apply_allowed: false
  retrieval_scope: project_context
  scene_type: design_talk
  query_summary:
    source: latest_user_message
    input_chars: 28
    term_hints:
      - RelayMEM
      - retrieval
    ambiguous_reference_terms_present: false
  selected: []
  blocked: []
  ctx_block: null
  fallback_reason: memory_store_not_configured
  token_budget:
    limit: 800
    source: runtime_config
  used_tokens: 0
  persistence_block: false
  persistence_block_reasons: []
```

Dry-run scope handling:

- `recovery` / `current_context_only` => no external MEM selection, `fallback_reason: current_context_only_no_external_mem` unless RelayREF reports an unresolved reference that requires confirmation.
- `formal_document` / `medical_or_safety` => external memory is blocked unless explicit evidence/docs are provided by a future retrieval gate.
- unknown or malformed RelaySCN artifact => fail closed with `fallback_reason: scene_policy_blocks_memory` and `persistence_block: true`.
- `design_talk` / `project_context` => dry-run eligible, but current MVP returns `selected: []`, `ctx_block: null`, and `fallback_reason: memory_store_not_configured`.

RelayMEM Retrieval must not silently resolve ambiguous references through MEM. If RelayREF marks `unresolved_reference_detected`, retrieval remains dry-run and requires confirmation instead of selecting long-term memory.
