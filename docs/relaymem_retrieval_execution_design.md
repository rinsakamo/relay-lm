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

---

## File-backed store dry-run/read-only stage

The RelayMEM file-backed store MVP starts as a read-only diagnostics layer. Runtime may inspect the expected layout and report store readiness, but it must not inject retrieved MEM into `ctx_block` yet and must not write MEM/SOUL state.

Default layout:

```text
memory/raw/
memory/mem/index.md
memory/mem/log.md
memory/mem/projects/
memory/mem/concepts/
memory/mem/summaries/
memory/mem/relations/
```

Store diagnostics are nested under `relaymem_retrieval_artifact.store_diagnostics`:

```yaml
store_diagnostics:
  schema_version: relaymem.store_diagnostics.v0
  diagnostics_only: true
  read_only: true
  store_enabled: false
  retrieval_dry_run_only: true
  root_path: .
  root_present: false
  index_present: false
  log_present: false
  pages_discovered: 0
  page_paths: []
  blocked_files: []
  fallback_reason: memory_store_disabled
```

Fail-soft rules:

- disabled store => `fallback_reason: memory_store_disabled`
- missing root => `fallback_reason: memory_store_root_missing`
- missing index => `fallback_reason: memory_store_index_missing`
- unsupported or unreadable files => entries in `blocked_files`
- valid store => `fallback_reason: memory_store_read_only_dry_run`

This stage is intentionally read-only. It validates layout and exposes diagnostics so later retrieval work can safely add ranking/selection gates without changing backend forwarding payloads or automatically updating MEM/SOUL.

---

## Selection dry-run diagnostics

After the read-only store inspector is available, RelayMEM Retrieval may also emit bounded page-selection diagnostics. This is still dry-run only: selected MEM candidates are not inserted into `ctx_block`, not forwarded to the backend, and not written back to MEM/SOUL.

Candidate discovery rules:

- Read `memory/mem/index.md` only as a bounded UTF-8 sample.
- Consider only compiled MEM pages under:
  - `memory/mem/projects/*.md`
  - `memory/mem/concepts/*.md`
  - `memory/mem/summaries/*.md`
- Do not select `memory/raw/` files in this stage.
- Respect max candidate and max read-byte limits.
- Report malformed or unreadable pages in `blocked` / `blocked_files`.

Artifact shape:

```yaml
relaymem_retrieval_artifact:
  selected: []
  selected_mem_candidates:
    - path: memory/mem/projects/relaymem.md
      source: mem_page
      reason: keyword_match
      estimated_chars: 320
      estimated_tokens: 80
      applied_to_ctx: false
  blocked:
    - path: memory/mem/projects/broken.md
      reason: malformed_or_unreadable_file
  ctx_block: null
  apply_allowed: false
  diagnostics_only: true
```

Safety gates:

- `recovery` / `current_context_only` => no external MEM candidates.
- `formal_document` / `medical_or_safety` => no external MEM candidates.
- unknown or malformed RelaySCN artifact => fail closed.
- RelayREF unresolved reference => no MEM candidates; ask for confirmation instead.

This stage proves that the runtime can inspect file-backed MEM pages and produce auditable selection diagnostics while preserving the current backend payload and avoiding all MEM/SOUL mutation.

---

## CTX block candidate dry-run diagnostics

RelayMEM Retrieval may now assemble a token-budgeted `ctx_block_candidate` from `selected_mem_candidates`. This remains diagnostics-only: the runtime does not copy the candidate into `ctx_block`, does not inject it into backend prompts, does not mutate request metadata, and does not edit MEM/SOUL. A future apply gate must be introduced separately before any candidate can affect runtime context.

Minimal artifact shape:

```yaml
relaymem_retrieval_artifact:
  selected: []
  selected_mem_candidates:
    - path: memory/mem/projects/relaymem.md
      source: mem_page
      reason: keyword_match
      estimated_chars: 320
      estimated_tokens: 80
      applied_to_ctx: false
  ctx_block: null
  ctx_block_candidate:
    schema_version: relaymem.ctx_block_candidate.v0
    diagnostics_only: true
    applied_to_ctx: false
    source: selected_mem_candidates
    budget:
      token_limit: 800
      estimated_tokens: 80
      truncated: false
    entries:
      - path: memory/mem/projects/relaymem.md
        source: mem_page
        reason: keyword_match
        estimated_tokens: 80
        included: true
        truncated: false
        applied_to_ctx: false
    blocked: []
  apply_allowed: false
  diagnostics_only: true
```

Token-budget rules:

- Use the runtime RelayMEM retrieval token budget resolved from `memory.token_budget` or `memory.token_budget_hint`.
- Estimate tokens with the MVP heuristic `estimated_chars // 4`, with a minimum of one token for non-empty candidates.
- Include candidates only while the cumulative estimated tokens remain within the diagnostics budget.
- Candidates that exceed the diagnostics budget remain unapplied and are reported with `reason: token_budget_exceeded`.
- `budget.estimated_tokens` is diagnostic only and must not be treated as prompt token usage.

Safety gates are unchanged:

- `recovery` / `current_context_only` leaves `ctx_block_candidate.entries` empty.
- `formal_document` / `medical_or_safety` leaves entries empty.
- Unknown or malformed RelaySCN artifacts fail closed and leave entries empty.
- RelayREF unresolved references leave entries empty so ambiguous references are not silently resolved through MEM.
- `ctx_block` remains `null`, `apply_allowed` remains `false`, and every entry has `applied_to_ctx: false`.

---

## Apply readiness gate dry-run diagnostics

RelayMEM Retrieval also emits apply-readiness diagnostics for the `ctx_block_candidate`. This is a gate report only. It does not enable runtime CTX injection, does not change the backend forwarding payload, and does not edit MEM/SOUL. `apply_allowed` remains `false` until a separate future apply PR implements and reviews the runtime gate.

Additional artifact fields:

```yaml
relaymem_retrieval_artifact:
  apply_allowed: false
  apply_decision: dry_run_only
  apply_readiness_score: 0.833
  apply_blocked_reasons:
    - dry_run_only
    - retrieval_dry_run_only
    - ctx_block_apply_disabled
    - runtime_ctx_injection_not_implemented
  apply_preconditions:
    scene_policy_allows_apply: true
    reference_resolved: true
    candidate_entries_present: true
    included_entries_present: true
    token_budget_allows_candidate: true
    retrieval_dry_run_only: true
    ctx_block_apply_enabled: false
    ctx_block_injection_enabled: false
    backend_payload_mutation_allowed: false
    mem_soul_mutation_allowed: false
```

MVP decision order:

- `blocked_scene_policy` for recovery/current-context-only retrieval, formal documents, medical/safety scenes, unknown scenes, or malformed RelaySCN artifacts.
- `blocked_unresolved_reference` when RelayREF requires confirmation.
- `blocked_no_candidates` when no CTX block candidate entries exist.
- `blocked_token_budget` when token-budget packing truncated the candidate.
- `dry_run_only` when candidates are otherwise valid but retrieval remains dry-run or `memory.ctx_block_apply_enabled` is false.
- `eligible_but_not_applied` only means the dry-run diagnostics preconditions look eligible; runtime apply is still intentionally not implemented and `apply_allowed` remains false.

Default config remains safe:

```yaml
memory:
  retrieval_dry_run_only: true
  ctx_block_apply_enabled: false
```

Future apply work must add a separate reviewed gate before any `ctx_block_candidate` can become `ctx_block`, alter request metadata, or affect backend prompts.

---

## CTX injection plan dry-run diagnostics

RelayMEM Retrieval may produce a `ctx_injection_plan` from the diagnostics-only `ctx_block_candidate` and apply-readiness result. This plan is a preview contract only: it does not create `ctx_block`, does not mutate request metadata, does not alter the backend forwarding payload, and does not edit MEM/SOUL.

Minimal artifact shape:

```yaml
relaymem_retrieval_artifact:
  ctx_block: null
  apply_allowed: false
  ctx_injection_plan:
    schema_version: relaymem.ctx_injection_plan.v0
    diagnostics_only: true
    applied: false
    payload_mutation_allowed: false
    target: backend_messages
    insertion_point: before_latest_user
    preview_text: |-
      [RelayMEM Context Candidate]
      - memory/mem/projects/relaymem.md (reason: keyword_match)
      This block is diagnostics-only and was not injected.
    estimated_tokens: 80
    source: ctx_block_candidate
    source_entries:
      - path: memory/mem/projects/relaymem.md
        reason: keyword_match
        estimated_tokens: 80
    blocked_reasons:
      - runtime_ctx_injection_not_implemented
      - backend_payload_mutation_disabled
```

Plan generation rules:

- A preview is generated only from `ctx_block_candidate.entries` where `included: true`.
- A preview is eligible only when `apply_decision` is `dry_run_only` or `eligible_but_not_applied`.
- `blocked_scene_policy`, `blocked_unresolved_reference`, `blocked_no_candidates`, and `blocked_token_budget` produce no preview text and include the apply decision in `blocked_reasons`.
- Preview text is deterministic and uses entry path/reason metadata only; current MEM page bodies are not packed into the preview.
- `applied` remains `false`, `payload_mutation_allowed` remains `false`, and `apply_allowed` remains `false`.

Future apply work must introduce an explicit reviewed runtime gate before this plan can become an injected backend message or persisted context block.

---

## Gated runtime CTX injection apply path

RelayMEM runtime CTX injection remains disabled by default. When both explicit config gates are opened, RelayLM may convert an eligible `ctx_injection_plan` preview into a short system message inserted into the forwarded backend messages. This is the first minimal apply path for RelayMEM retrieval context, but it still does not edit MEM/SOUL and does not inject MEM page bodies.

Default-safe config:

```yaml
memory:
  retrieval_dry_run_only: true
  ctx_block_apply_enabled: false
```

Apply gates that must all pass:

- `memory.ctx_block_apply_enabled == true`
- `memory.retrieval_dry_run_only == false`
- `relaymem_retrieval_artifact.apply_decision == eligible_but_not_applied`
- `ctx_injection_plan.preview_text` is non-empty
- `ctx_injection_plan.applied == false`
- scene policy did not block retrieval/apply
- RelayREF did not require unresolved-reference confirmation
- token-budget packing did not block the candidate

Runtime result diagnostics are emitted separately from the dry-run plan:

```yaml
runtime_ctx_injection_result:
  schema_version: relaymem.runtime_ctx_injection_result.v0
  attempted: true
  applied: true
  insertion_point: before_latest_user
  inserted_message_role: system
  inserted_chars: 188
  estimated_tokens: 47
  blocked_reasons: []
  payload_mutation_applied: true
  original_message_count: 1
  forwarded_message_count: 2
```

Insertion contract:

- Insert one `role: system` message immediately before the latest user message.
- The inserted content starts with `[RelayMEM Context]`.
- The inserted content uses only candidate path/reason metadata from the plan source entries.
- It does not include MEM page bodies yet.
- It instructs the backend to treat memory hints as contextual hints, not standalone facts.
- The original request payload/messages are copied; RelayLM does not mutate the caller-provided payload object in place.

Blocked/runtime-safe cases:

- default config remains no-op and reports blocked reasons.
- recovery/current-context-only scenes do not inject.
- formal-document and medical/safety scenes do not inject.
- unresolved references do not inject.
- token-budget blocked candidates do not inject.
- no-candidate plans do not inject.

This stage intentionally keeps MEM/SOUL mutation out of scope. Future work may add page-body packing, stronger provenance, and stricter downstream apply gates.

Token-budget ordering:

- Runtime CTX injection runs before message-level token-budget truncation.
- When `memory.token_budget_truncation_enabled` is true, the injected RelayMEM system message is part of the payload evaluated by truncation.
- The backend receives only the final post-truncation payload.
- `runtime_ctx_injection_result` records whether the RelayMEM context message was inserted, while `token_budget_truncation` records any subsequent truncation of the injected payload.

Prompt metadata safety:

- Runtime CTX injection sanitizes RelayMEM path/reason metadata before embedding it in a system message.
- Newlines, tabs, carriage returns, ASCII control characters, role-like colon separators, quotes/backticks, and brackets are normalized before insertion.
- Long metadata values are truncated before insertion.
- Raw MEM page bodies remain excluded from runtime CTX injection.

Preserved-budget overflow guard:

- When token-budget truncation is enabled, RelayLM checks the would-be preserved set before inserting RelayMEM context.
- The check estimates all preserved system messages, the latest user message, and the candidate RelayMEM system message.
- If that preserved set would exceed `memory.token_budget`, runtime CTX injection is skipped before payload mutation.
- The runtime result reports `relaymem_context_would_break_token_budget`, and token-budget truncation still evaluates the non-injected payload.

## Bounded page snippet extraction dry-run

RelayMEM retrieval may build bounded page snippet diagnostics from `selected_mem_candidates`, but this phase does not inject MEM page body content into the runtime prompt. Snippet extraction is a diagnostics-only evidence preparation step for future apply gates.

Default-safe config:

- `memory.snippet_extraction_enabled`: default `false`
- `memory.snippet_dry_run_only`: default `true`
- `memory.max_snippet_chars`: default `512`
- `memory.max_snippet_candidates`: default `3`

When enabled, extraction is limited to selected candidate paths under these MEM page scopes:

- `memory/mem/projects/*.md`
- `memory/mem/concepts/*.md`
- `memory/mem/summaries/*.md`

The extraction helper must not read `memory/raw`, must not follow symlinks, and must block root-outside path traversal attempts. Reads are bounded by `max_read_bytes`, snippets are bounded by `max_snippet_chars`, and malformed UTF-8 fails soft into blocked diagnostics instead of failing the request.

Snippet candidates use this diagnostics-only shape:

```yaml
snippet_candidates:
  - path: memory/mem/projects/relaymem.md
    source: mem_page
    evidence_kind: bounded_page_snippet
    snippet_text: "..."
    snippet_chars: 240
    estimated_tokens: 60
    applied_to_ctx: false
    safe_for_prompt_preview: false
    blocked_reasons: []
```

Safety gates skip snippet extraction for:

- `recovery` scene policy
- `current_context_only` retrieval scope
- `formal_document` scene policy
- `medical_or_safety` scene policy
- unknown or malformed RelaySCN artifacts
- unresolved RelayREF references
- empty selected MEM candidates
- token-budget-blocked retrieval artifacts

## Evidence envelope dry-run contract

RelayMEM retrieval artifacts include an evidence envelope next to `snippet_candidates`:

```yaml
evidence_envelope:
  schema_version: relaymem.evidence_envelope.v0
  diagnostics_only: true
  applied_to_ctx: false
  source: selected_mem_candidates
  snippets:
    - path: memory/mem/projects/relaymem.md
      evidence_kind: bounded_page_snippet
      snippet_chars: 240
      estimated_tokens: 60
      content_included_in_runtime_prompt: false
  blocked:
    - path: memory/raw/example.md
      reason: unsupported_scope
```

The envelope is emitted in diagnostics / trace metadata so future review can compare candidate snippets against retrieval decisions. It is not a prompt contract yet.

Blocked reasons include:

- `path_outside_mem_scope`
- `malformed_utf8`
- `unsupported_scope`
- `read_limit_exceeded`
- `symlink_blocked`
- `file_missing`
- `unreadable_file`

## No runtime snippet injection yet

The gated runtime CTX injection path remains metadata-only. Runtime prompt content may include sanitized path/reason metadata from the CTX injection plan, but it must not include `snippet_text` or raw MEM page body content in this phase.

Before any future snippet apply gate, RelayMEM still needs stricter CTX packing, source evidence review, user-visible/debug diagnostics, and explicit policy for when snippet text is allowed to become prompt-visible.

## CTX block candidate evidence metadata dry-run

`ctx_block_candidate.entries` now carries diagnostics-only evidence metadata that links an entry back to the bounded snippet evidence envelope. This does not make snippet text prompt-visible and does not create a runtime `ctx_block`.

Entry-level evidence metadata:

```yaml
ctx_block_candidate:
  schema_version: relaymem.ctx_block_candidate.v0
  diagnostics_only: true
  applied_to_ctx: false
  entries:
    - path: memory/mem/projects/relaymem.md
      source: mem_page
      reason: keyword_match
      estimated_tokens: 80
      included: true
      truncated: false
      applied_to_ctx: false
      evidence_id: evidence:0
      snippet_available: true
      evidence_kind: bounded_page_snippet
      snippet_chars: 240
      snippet_estimated_tokens: 60
      snippet_included_in_runtime_prompt: false
```

Linking rules:

- `evidence_envelope.snippets[*].evidence_id` is stable within the request artifact and matches `ctx_block_candidate.entries[*].evidence_id` when a bounded snippet is available.
- `selected_index` is included in the evidence envelope so duplicate paths can still be tied back to the selected candidate order.
- If extraction is disabled or skipped, entries remain metadata-only with `snippet_available: false`, `evidence_kind: none`, zero snippet counts, and `snippet_included_in_runtime_prompt: false`.
- If extraction is blocked for an entry, `evidence_envelope.blocked[*].evidence_id` can be referenced by the entry and the entry may expose `evidence_blocked_reason` without carrying `snippet_text`.

Safety posture:

- `snippet_text` is not copied into `ctx_block_candidate.entries`.
- `snippet_text` is not copied into runtime CTX injection source entries.
- Runtime prompts remain path/reason metadata-only in this phase.
- `ctx_block` remains `null` and `apply_allowed` remains `false`.
- Recovery, current-context-only, formal-document, medical/safety, unknown/malformed scene, and unresolved-reference paths do not produce snippet-bearing CTX entries.

Future phase:

- A gated snippet-bearing CTX block can use `evidence_id` links to decide which evidence snippets are eligible for prompt-visible packing.
- That future gate must still enforce source evidence policy, stricter token budgeting, scene/ref safety, and user/debug observability before copying any snippet body into a runtime prompt.

## Snippet apply readiness dry-run

RelayMEM now reports snippet-specific apply readiness next to the broader `apply_decision`. This is still diagnostics-only: snippet-bearing CTX blocks are not applied, `ctx_block` remains `null`, `apply_allowed` remains `false`, and runtime CTX injection remains path/reason metadata-only.

Artifact fields:

```yaml
relaymem_retrieval_artifact:
  snippet_apply_decision: dry_run_only
  snippet_apply_readiness_score: 0.875
  snippet_apply_blocked_reasons:
    - dry_run_only
    - snippet_dry_run_only
    - snippet_apply_disabled
    - runtime_snippet_injection_not_implemented
  snippet_apply_preconditions:
    scene_policy_allows_apply: true
    reference_resolved: true
    candidate_entries_present: true
    evidence_envelope_present: true
    snippet_candidates_present: true
    included_snippet_entries_present: true
    snippet_budget_allows_candidate: true
    snippet_dry_run_only: true
    snippet_apply_enabled: false
    runtime_snippet_injection_enabled: false
    backend_payload_mutation_allowed: false
    mem_soul_mutation_allowed: false
```

Decision states:

- `blocked_scene_policy`: recovery, current-context-only, formal-document, medical/safety, unknown, or malformed scene policy blocks snippet apply.
- `blocked_unresolved_reference`: RelayREF requires confirmation before memory evidence can be applied.
- `blocked_no_candidates`: no CTX block candidate entries exist.
- `blocked_no_snippet`: candidate entries exist but no bounded snippet is available.
- `blocked_snippet_evidence`: snippet evidence exists only as blocked evidence diagnostics.
- `blocked_snippet_budget`: included snippet metadata exceeds `memory.snippet_budget`.
- `dry_run_only`: snippet evidence is present, but `memory.snippet_dry_run_only` is true or `memory.snippet_apply_enabled` is false.
- `eligible_but_not_applied`: snippet evidence passes dry-run readiness gates, but runtime snippet insertion is not implemented.

Default-safe config:

```yaml
memory:
  snippet_dry_run_only: true
  snippet_apply_enabled: false
  snippet_budget: 512
```

Safety posture:

- `snippet_text` is not copied into `ctx_block_candidate.entries`.
- `snippet_text` is not copied into runtime CTX injection source entries or backend payloads.
- `snippet_included_in_runtime_prompt` remains `false`.
- Runtime snippet injection remains disabled even when readiness reports `eligible_but_not_applied`.
- MEM/SOUL state is not written or updated.

Future phase:

- A gated snippet-bearing CTX block can use `snippet_apply_*` diagnostics as the review surface before allowing any snippet body into a prompt.
- That future apply gate must keep explicit scene/reference safety, source evidence policy, strict token packing, and user/debug observability.
