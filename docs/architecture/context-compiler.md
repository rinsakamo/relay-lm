# Context Compiler

The Context Compiler constructs the smallest sufficient cognitive context for the current turn **as the character**.

## Inputs

- Identity Core;
- relevant Canonical State;
- RelayLM-owned recent message Events used as Working Context;
- retrieved crystallized memory and targeted Event evidence when those layers are enabled;
- the current governed Event;
- minimum protocol/tool state;
- applicable audience/privacy/capability narrowing.

## Output

A bounded `CognitiveInput` object.

The durable memory model and the per-turn cognitive working set are intentionally different:

```text
Durable semantic layer
  Event Journal       what occurred / provenance
  Canonical State     accepted current understanding
  MEMORY.md / notes   crystallized long-term semantic synthesis

          ↓ selection / compilation

Per-turn cognitive layer
  Identity            protected
  Current Event       protected
  Relevant State      current accepted understanding
  Working Context     recent conversational continuity
  Retrieved Memory    optional long-term semantic context
  Event Evidence      targeted grounding / chronology
```

> **Persistence decides what RelayLM knows. Context selection decides what RelayLM thinks about now.**

## Authority and continuity rules

- Raw client transcript replay is not a trusted context mechanism.
- Working Context is built only from RelayLM-owned persisted Events.
- Working Context may contain both user-authored and assistant-authored dialogue and must preserve actor/source provenance.
- Assistant-authored Working Context supports conversational continuity, reference resolution, and unfinished dialogue. It does **not** prove user facts, preferences, goals, experiences, or external events merely because the assistant said them before.
- User-authored Working Context is evidence of what the user said, with the temporal and semantic limits of that utterance; prompt residence does not make it timeless external truth.
- Relevant accepted State may influence the response without being recited.
- Current-state conflicts are resolved by authority/source role before relevance ranking. A stale memory or assistant assertion cannot override active Canonical State for a current-state claim.
- Event Journal remains occurrence/provenance authority for what happened even when current State has changed.
- Retrieval and Context compilation are read/select/project operations. They never mutate Canonical State or durable memory.

> **Continuity relevance does not imply factual authority.**

## Context residency lifecycle

Context residency is distinct from semantic memory lifecycle.

```text
Semantic lifecycle
  Event → State → Crystallization → MEMORY

Context residency lifecycle
  admit → retain → downrank → evict → retrieve again
```

Eviction from Working Context means only that the material is no longer in the current cognitive working set. It does not delete the source Event, Canonical State, or crystallized memory. Older material may later re-enter Context through retrieval.

This distinction prevents token-budget pressure from becoming accidental forgetting.

## Current Working Context implementation

The first bounded Working Context slice was implemented by #1278.

Current defaults:

```text
max message Events: 6
max content chars: 4000
```

The cap applies to Working Context only. Identity, active Canonical State, and the Current Event are not evicted by this cap.

Additional rules:

- the Current Event is excluded from Working Context because it is already carried separately as `input`;
- only RelayLM-persisted user/assistant message Events are eligible;
- selected prior material is returned in chronological order;
- a normal prior `user → assistant` exchange is admitted atomically so budget pressure does not leave an orphan assistant assertion in Context;
- an unmatched user Event may be admitted by itself;
- an unmatched assistant Event is not admitted by itself;
- zero Working Context budget leaves Identity, State, and Current Event intact.

These are deterministic residency rules, not semantic truth rules.

## Current active-State selection primitive

`compile_cognitive_input` now supports an optional explicit `max_state_records` cap for large active-State sets.

Eligibility is applied before ranking: only records with `status == "active"` and no `valid_to` are candidates. The selector never changes State records or provenance.

Current behavior is deliberately conservative:

- `max_state_records=None` preserves the previous behavior and projects every eligible active State record;
- if the eligible set already fits the explicit cap, order and contents are unchanged;
- only under explicit cap pressure, deterministic lexical relevance against the Current Event is used;
- specific State-key matches receive the strongest lexical weight, followed by matching semantic value text and then State-class text;
- positive lexical matches are ranked before zero-match fallback records;
- ties and fallback are deterministic by existing State order;
- after selection, records are projected in their original Canonical State order rather than score order;
- `max_state_records=0` removes only the State projection; Identity, Current Event, and Working Context remain independent;
- negative caps fail explicitly.

The current lexical selector is candidate selection, not authority. It does not mutate State, call an LLM, resolve contradictions, or infer truth from similarity.

The ordinary runtime does **not** yet impose a default State cap, so existing turns continue to receive all eligible active State unless a caller explicitly requests bounded State selection. Runtime budget policy and stronger semantic/multilingual discovery remain #1267 work.

### Content-free State selection diagnostics

Callers that explicitly need selection evidence may use `compile_cognitive_input_with_diagnostics`. It returns the same `CognitiveInput` produced by the ordinary compiler plus a diagnostics tuple. The ordinary `compile_cognitive_input` path does not generate or persist diagnostics.

The current diagnostics surface covers only the `canonical_state` layer and exposes aggregate, content-free fields:

- selection mode: `unbounded`, `within_budget`, `zero_budget`, or `lexical_ranked`;
- eligible / selected / evicted record counts;
- budget unit (`records`), explicit limit, used count, and whether budget pressure occurred;
- selected lexical-match count and selected deterministic-fallback count when lexical ranking is active;
- evicted-by-budget-limit count.

Diagnostics deliberately exclude State IDs, keys, values, source Event IDs, Current Event content/ID, and any other semantic payload. They are observations about selection mechanics, not a new truth source, persistence layer, ranking authority, or telemetry requirement.

This first diagnostics slice is record-count based because the current explicit State cap is record-count based. Cross-layer token cost, Working Context diagnostics, retrieved-memory/Event diagnostics, and total-budget degradation/fallback reporting remain later #1267 work.

## Budget model

Context budgeting is role-aware rather than one flat relevance competition.

Conceptually:

```text
protected tier   Identity + Current Event
current tier     relevant active Canonical State
working tier     bounded recent conversational continuity
retrieved tier   MEMORY chunks + targeted Events
reserve tier     prompt / schema / provider overhead
```

Budgets should use floors/caps/residual allocation rather than fixed percentages that must always be consumed. Correct but irrelevant memory should remain out of Context; token availability alone is not a reason to inject it.

## Deferred selection work

#1267 remains the authority for later Context selection and retrieval work, including:

- runtime default State budgeting and stronger semantic/multilingual relevance beyond the current explicit lexical primitive;
- `unresolved`, `referent`, and `active_task` retention beyond pure recency;
- crystallized `MEMORY.md` retrieval;
- targeted Event evidence retrieval;
- source-role-aware stale/conflict suppression;
- redundancy reduction across State / Working Context / Memory / Events;
- total token-aware tier budgeting and cross-layer diagnostics;
- embedding/index acceleration only after authority eligibility is preserved.

The governing principle is:

> **Retrieve by relevance, assemble by authority.**
