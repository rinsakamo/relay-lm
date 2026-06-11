# RelayMEM SLP Execution Design

Date basis: 2026-05-31 JST

## Purpose

RelayMEM SLP execution is the memory compile path. It reads raw evidence, extracts memory candidates, classifies safety, merges or holds candidates, lints memory, updates indexes/logs, and emits SOUL promotion candidates when needed.

SLP improves memory quality. It is not responsible for producing the current answer.

## Core principle

```text
SLP edits or proposes memory changes.
Retrieval only reads memory.
```

SLP must remain gated because it can affect future behavior.

## Inputs

```text
SLP input:
- recent conversation raw log
- user-explicit memory requests
- ctx_working_update artifacts
- existing MEM pages
- existing index/log
- scene_state and memory_scope from RelaySCN
- optional RelaySOUL constraints
- optional user-approved memory records
```

## Outputs

```text
SLP output:
- memory candidates
- proposed page updates
- created/updated page list
- held candidates
- rejected candidates
- lint diagnostics
- relation updates
- index/log updates
- SOUL promotion candidates
```

## Execution flow

```text
raw event append
↓
candidate extraction
↓
memory_kind classification
↓
safety_scope classification
↓
existing MEM lookup
↓
merge / update / hold / reject
↓
relation typing
↓
lint
↓
index rebuild or patch
↓
log append
↓
optional apply gate
```

## Step details

### 1. Raw event append

Store primary evidence before summarizing it.

Examples:

```text
memory/raw/conversations/session_20260531_001.jsonl
memory/raw/events/relaymem_slp_run_20260531_001.jsonl
```

Raw sources must remain available for later audit and recompile.

### 2. Candidate extraction

Extract possible memory candidates from recent raw sources.

Candidate examples:

- project state update
- concept definition
- design decision
- user workflow preference
- relation between concepts
- contradiction candidate
- stale claim candidate
- SOUL promotion candidate

### 3. memory_kind classification

Classify each candidate.

```yaml
memory_kind:
  - raw_event
  - session_summary
  - project_state
  - concept
  - claim
  - preference
  - relation
  - soul_candidate
  - rejected_or_blocked_candidate
```

### 4. safety_scope classification

Classify update safety.

```yaml
safety_scope:
  free_to_update:
    action: apply may be allowed when apply gate is enabled

  review_required:
    action: hold candidate and report diagnostics

  explicit_approval_required:
    action: convert to SOUL proposal or approval artifact

  never_auto_promote:
    action: reject or store only as blocked diagnostic, not durable fact
```

Important rule:

```text
Do not persist raw user_affect_estimate as a long-term fact.
```

If affect-related information is useful, store only aggregate policy diagnostics or scene-level outcomes, and only when allowed by scene policy.

### 5. Existing MEM lookup

Before creating a new page, SLP checks existing pages and index aliases.

Possible decisions:

```text
create_page
update_page
append_claim
merge_duplicate
mark_stale
add_relation
hold_for_review
propose_soul_update
reject
```

### 6. Merge / update / hold / reject

SLP should use conservative defaults.

```text
free_to_update -> apply or proposed_apply
review_required -> hold
explicit_approval_required -> SOUL proposal
never_auto_promote -> reject or blocked diagnostic
```

### 7. Relation typing

SLP should attach typed relations where possible.

Suggested relation types:

```text
supports
contradicts
refines
supersedes
depends_on
part_of
example_of
risk_for
derived_from
candidate_for_soul
blocked_from_soul
```

### 8. Lint

SLP lint checks memory quality.

Checks:

- duplicate concepts
- identity/alias split
- stale claims
- contradictory claims
- orphan pages
- untyped relation overuse
- missing source references
- unsafe promotion candidates
- low-confidence personal inference

### 9. Index update

Update `memory/mem/index.md` and optional relation graph.

Index entries should include:

- page id
- title
- memory kind
- summary
- tags
- aliases
- safety scope
- source level
- stability
- last updated

### 10. Log append

Append every SLP run to `memory/mem/log.md` or JSONL audit log.

Log should include:

- run id
- input refs
- candidates count
- updated pages
- held candidates
- rejected candidates
- SOUL candidates
- diagnostics

## Trigger modes

### Manual SLP

Triggered when the user explicitly asks to remember, organize, document, or consolidate.

```text
trigger:
  user_explicit_memory_request = true
```

### Turn-end dry-run SLP

Triggered after a response to generate diagnostics and candidates without applying them.

```text
trigger:
  relaymem_slp_dry_run_enabled = true
```

### Sleep / Reflection SLP

Triggered when context pressure is high, the conversation is tangled, or the user permits a sleep/reflection cycle.

```text
trigger:
  context_pressure_high = true
  or user_requested_sleep = true
  or unresolved_context_confusion = true
```

If confusion remains unresolved, RelaySCN may switch to recovery scene and block persistence.

## SLP artifact contract

Suggested dataclass shape:

```python
@dataclass
class RelayMemSlpCandidate:
    candidate_id: str
    memory_kind: str
    title: str
    summary: str
    source_refs: list[str]
    target_page: str | None
    relation_hints: list[dict]
    source_level: str
    stability: str
    safety_scope: str
    confidence: float
    proposed_action: str
    blocked_reason: str | None
```

```python
@dataclass
class RelayMemSlpResult:
    slp_run_id: str
    mode: str
    input_refs: list[str]
    candidates: list[RelayMemSlpCandidate]
    updated_pages: list[str]
    created_pages: list[str]
    held_candidates: list[str]
    soul_candidates: list[str]
    diagnostics: dict
```

## Example artifact

```json
{
  "slp_run_id": "slp_20260531_001",
  "mode": "dry_run",
  "input_refs": [
    "memory/raw/conversations/session_20260531_001.jsonl"
  ],
  "updated_pages": [
    "memory/mem/projects/relaymem.md",
    "memory/mem/concepts/slp.md"
  ],
  "created_pages": [
    "memory/mem/concepts/llm_wiki.md"
  ],
  "index_updated": true,
  "relations_added": [
    {
      "source": "llm_wiki",
      "type": "refines",
      "target": "relaymem"
    }
  ],
  "held_candidates": [
    {
      "kind": "preference",
      "reason": "review_required"
    }
  ],
  "soul_candidates": [
    {
      "candidate_id": "soul_candidate_001",
      "approval_required": true,
      "reason": "long_term_identity_or_policy_change"
    }
  ],
  "diagnostics": {
    "duplicate_candidates": 1,
    "contradiction_candidates": 0,
    "stale_candidates": 0,
    "orphan_pages": 0
  }
}
```

## Safety behavior

SLP should fail closed when uncertain.

Persistence should be blocked when:

- scene_state is recovery
- scene_state is medical_or_safety
- scene_state is formal_document
- user confirmation is required
- confidence is low
- stability is low
- SLP confusion remains unresolved
- contradiction is unresolved
- source reference is missing
- candidate requires explicit approval

## MVP defaults

```yaml
relaymem_slp:
  dry_run_default: true
  apply_enabled_default: false
  auto_apply_scope:
    - free_to_update
  hold_scope:
    - review_required
  soul_proposal_scope:
    - explicit_approval_required
  reject_or_block_scope:
    - never_auto_promote
```

## Non-goals

- Do not answer the current user request from SLP directly.
- Do not mutate RelaySOUL.
- Do not persist raw affect estimates as long-term facts.
- Do not auto-apply review_required or explicit_approval_required candidates.
- Do not run heavy memory compilation inside the latency-critical Retrieval path.

## Summary

RelayMEM SLP is the memory compiler path:

```text
raw events -> candidates -> safety classification -> merge/update/hold -> lint -> index/log -> SOUL candidates
```

It makes future memory better while preserving auditability and preventing RelaySOUL pollution.
