# RelayINT MVP Design

Date basis: 2026-06-07 JST

## Purpose

RelayINT is the synchronous intent / interpretation layer of RelayLM.

It corresponds to the earlier small-cerebellum discussion: a lightweight runtime intelligence layer that improves perceived conversational intelligence by resolving what the user means before RelayMEM, RelayCTX, and the main LLM act.

RelayINT is not a memory database, not a long-term learning layer, and not the final response generator.

## Core positioning

```text
RelaySCN = reads the scene / conversational frame
RelayEMO = reads and expresses affect
RelayINT = reads intent, references, topic anchors, and action intent
RelayMEM = reads long-term memory
RelayCTX = builds the current thinking context
RelaySLP = asynchronously consolidates memory and concepts
RelayRUN = orchestrates runtime execution and recovery
RelaySOUL = preserves stable identity, relationship principles, and approval boundaries
```

RelayINT exists because scene, affect, memory, and context packing do not fully cover user intent.

Without RelayINT, RelayLM may over-clarify short references such as `それ`, `続き`, `前のやつ`, or `この方向で`, creating an annoying user experience even when the current CTX working memory already contains enough information to continue.

## Runtime position

MVP runtime order with RelayINT:

```text
User input
↓
Input-side RelaySCN
↓
Input-side RelayEMO
↓
RelayINT
↓
RelayMEM Retrieval, only when needed
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

RelayINT should run after RelaySCN and input-side RelayEMO because intent resolution depends on scene policy, memory scope, formality, recovery state, and affect-sensitive clarification behavior.

RelayINT should run before RelayMEM Retrieval because MEM should not be used to silently guess ambiguous references.

## Sync INT vs async SLP

```text
RelayINT = understand this turn now
RelaySLP = organize memory for future turns later
```

RelayINT is synchronous and low-latency. It helps the current answer avoid avoidable misunderstandings.

RelaySLP is asynchronous or deferred. It reads raw conversation evidence, INT artifacts, CTX unpack artifacts, and existing MEM pages later, then extracts candidates, classifies safety, merges, holds, rejects, or proposes memory updates.

Important boundary:

```text
RelayINT may emit runtime interpretation artifacts.
RelayINT must not update MEM directly.
RelayINT must not mutate SOUL.
RelaySLP may later inspect INT artifacts as evidence, but persistence remains gated.
```

## Relation to short-term CTX working memory

Return-side RelayCTX unpacks the main LLM output into:

```text
user_visible_response
ctx_working_update
```

RelayCTX validates, compresses, and commits the safe parts of `ctx_working_update` into RAM-side working memory.

On the next turn, RelayINT reads that CTX working memory first. It should prefer current RAM-side CTX over long-term MEM for short references and active-topic continuation.

Example CTX working fields used by RelayINT:

```yaml
ctx_working_memory:
  current_topic: RelayINT throughput policy
  active_question: MVP scope for RelayINT
  last_decision:
    text: RelayINT is a synchronous small-cerebellum intent layer
    status: agreed
    confidence: 0.91
  referable_items:
    - label: RelayINT Fast Path
      kind: component
      salience: 0.92
    - label: Main LLM Short-INT
      kind: option
      salience: 0.84
  unresolved_slots: []
  next_expected_action: define MVP implementation scope
```

RelayINT converts the latest user input plus CTX state into a compact intent artifact.

## Reference resolution and recall interaction policy

RelayINT should separate short-term reference resolution from long-term memory retrieval.

Recommended precedence:

```text
1. current user turn and explicit nouns
2. current RAM-side CTX working state
3. user confirmation of one candidate
4. RelayMEM retrieval, only when explicitly requested or still needed after confirmation
```

Decision policy:

| State | RelayINT action | RelayMEM action |
|---|---|---|
| One clear active-CTX referent | continue with resolved reference | do not retrieve |
| Multiple plausible active-CTX referents | ask candidate confirmation | do not retrieve |
| No active-CTX candidate | ask open clarification | do not retrieve |
| User explicitly requests remembered information | confirm scope when needed | retrieval may run |
| User confirms a reference but CTX lacks the needed facts | request retrieval | retrieval may run |

An ambiguous reference must never trigger silent long-term recall. Retrieval can broaden the evidence only after the user has named, requested, or confirmed the intended scope.

For a recall operation that cannot safely complete in the ordinary single-pass path, RelayINT may use a two-step interaction contract:

```text
turn 1:
  detect explicit or confirmed recall need
  -> ask/record the minimum required confirmation
  -> no long-term memory mutation

turn 2 after confirmation:
  RelayMEM Retrieval reads the allowed scope
  -> RelayCTX Repack inserts the selected memory block
  -> Main LLM produces the final answer
```

A short character-facing acknowledgement such as a thinking or recall-pause phrase is optional presentation behavior. It must pass the normal output pipeline and scene/EMO gates, and RelayRUN must not directly finalize that text. The core contract is confirmation and safe repacking, not the wording of the pause.

## MVP responsibilities

RelayINT MVP should do the following:

```text
1. Detect pronoun-like and continuation references.
2. Resolve references against CTX working memory when confidence is high.
3. Identify topic anchors and user action intent.
4. Decide whether MEM retrieval is needed.
5. Avoid MEM lookup for ambiguous references.
6. Emit clarification intent when confidence is low.
7. Emit diagnostics for all decisions.
```

MVP should not attempt to solve deep semantic ambiguity, durable memory consolidation, or long-term personalization.

## Intent artifact schema

Initial artifact:

```yaml
relayint_intent:
  schema_version: relayint.intent.v0
  path: fast_path

  source: current_turn
  llm_called: false

  resolved_reference: true
  resolved_reference_text: それ
  resolved_to: RelayINT MVP scope

  topic_anchor: RelayINT
  user_intent: continue_design
  action_intent: define_mvp_scope

  mem_query_needed: false
  mem_query_reason: null

  ambiguity:
    has_ambiguity: false
    candidates: []

  confidence: 0.88
  action: continue_without_clarification

  diagnostics:
    fast_path_reason:
      - single_high_salience_referable_item
      - active_topic_matches_user_continuation
    safety_notes: []
```

When the reference is ambiguous:

```yaml
relayint_intent:
  schema_version: relayint.intent.v0
  path: fast_path
  llm_called: false

  resolved_reference: false
  resolved_reference_text: それ
  resolved_to: null

  topic_anchor: null
  user_intent: continue_or_apply_unknown
  action_intent: unknown

  mem_query_needed: false
  mem_query_reason: ambiguous_reference_blocked

  ambiguity:
    has_ambiguity: true
    candidates:
      - RelayINT Fast Path MVP
      - Main LLM Short-INT extension
      - small LLM INT runtime

  confidence: 0.48
  action: ask_clarification
```

## MEM retrieval decision

RelayINT decides whether MEM retrieval is needed, but RelayMEM performs the retrieval.

MVP rules:

```text
Short-term CTX resolves the reference clearly
→ mem_query_needed=false

User explicitly asks for prior memory / previous thread / remembered design
→ mem_query_needed=true

Reference is confirmed but CTX lacks enough evidence
→ mem_query_needed=true

Reference is ambiguous
→ mem_query_needed=false and ask clarification

Scene policy restricts retrieval
→ mem_query_needed=false or current_context_only, depending on scene_policy
```

MEM must not be used as a silent fallback for ambiguous references.

## Quick clarification route

RelayINT may produce a quick clarification intent when it should not continue automatically.

The quick path is:

```text
RelayINT
↓
Return/input-compatible RelayEMO clarification style adjustment
↓
RelaySCN scene/formality/recovery gate
↓
short user-visible clarification response
```

This route avoids a full normal answer when the correct next action is a small clarification.

MVP can start with templated clarification text, for example:

```text
「それ」は RelayINT MVP の範囲の話？ それとも小型LLMを入れる話？
```

Return-side EMO may soften tone, reduce dominance, and keep the clarification from feeling like an interrogation. RelaySCN should enforce scene policy and recovery rules.

## Throughput policy

RelayINT is not defined as a small-LLM layer. It is a fast intent runtime with optional LLM paths.

MVP execution paths:

```text
Fast Path:
  deterministic rules and scoring over CTX working memory
  default path
  no LLM call

Main LLM Short-INT:
  optional, default-off, dry-run initially
  short context and structured output only
  useful when main LLM cache reuse is hot

Small LLM INT:
  future optimization
  requires CPU/RAM runtime and conversation/session cache evaluation
```

MVP should implement Fast Path first and expose diagnostics showing when an LLM path would have been useful.

Suggested path selection:

```yaml
relayint_execution_policy:
  fast_path_confidence_gte: 0.80
  ask_confirmation_range: [0.55, 0.80]
  ask_open_clarification_lt: 0.55

  llm_path_default_enabled: false
  main_llm_short_int_default_enabled: false
  small_llm_int_default_enabled: false
```

Main LLM Short-INT may be faster than a CPU small LLM when GPU KV/prefix cache reuse is hot and the INT context is short. Small LLM INT should not be assumed faster until measured with session/cache behavior.

## MVP non-goals

MVP should not include:

```text
- always-on LLM parsing
- always-on small LLM runtime
- CPU/RAM small LLM session cache
- INT-specific KV cache management
- direct MEM updates from INT
- direct SOUL mutation from INT
- cross-thread memory restore
- response-body mutation without explicit quick clarification apply gate
- silent MEM lookup for ambiguous references
```

## Suggested MVP sequence

```text
MVP-44: RelayINT design doc
  Define component responsibility, runtime position, INT/SLP split, CTX/MEM relation, and throughput policy.

MVP-45: RelayINT Fast Path dry-run
  Add diagnostics-only resolver over current user input and CTX-style working memory metadata.

MVP-46: RelayINT quick clarification preflight
  Emit clarification candidate artifacts without mutating response bodies.

MVP-47: RelayINT gated quick clarification apply
  Default-off / dry-run-only apply path for low-risk clarification responses.

MVP-48+: Main LLM Short-INT dry-run
  Optional structured LLM path with latency and cache-reuse diagnostics.
```

## Core design statement

RelayINT is the synchronous small-cerebellum layer of RelayLM.

It improves perceived conversational intelligence by resolving references, topic anchors, user intent, action intent, and retrieval intent before MEM, CTX, and the main LLM act.

RelayINT should reduce unnecessary clarification loops, but it must still ask or enter recovery when confidence, evidence, or scene stability is low.
