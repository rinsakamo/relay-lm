# RelayINT MVP Design

## Purpose

RelayINT is RelayLM's synchronous pre-action interpretation layer.

It resolves what the user means before RelayMEM Retrieval, RelayCTX Repack, and the Main LLM act.

RelayINT is not a memory database, not a long-term learning layer, not an output observer, and not the final response generator.

## Core positioning

```text
RelaySCN
  scene and policy

RelayEMO
  affect estimate and expression state

RelayINT
  intent, references, topic/action anchors, proceed/clarify/retrieve decision

RelayMEM Retrieval
  approved long-term memory read

RelayCTX
  short-term working state and prompt construction

RelayREF
  post-generation output observation

RelaySLP
  deferred memory/SOUL compilation
```

## Canonical runtime position

```text
User input
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval, only when needed and allowed
  -> RelayCTX Repack
  -> Main LLM
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> User output
```

RelayINT runs before Retrieval so long-term memory is not used to guess ambiguous references silently.

## RelayINT versus RelayREF and RelaySLP

```text
RelayINT
  understand and gate this turn before generation

RelayREF
  observe generated output after Unpack

RelaySLP
  organize governed evidence for future turns later
```

RelayINT may emit request-local interpretation artifacts. It must not update MEM or SOUL.

## Relation to RelayCTX working state

RelayCTX working state may include:

- current topic,
- active task or question,
- prior decision,
- referable items,
- unresolved slots,
- next expected action.

RelayINT reads this state when resolving short references and continuation intent.

RelayCTX Unpack does **not** automatically commit a candidate into working memory. The safe boundary is:

```text
Main LLM output
  -> RelayCTX Unpack
  -> visible response
  + detached ctx_working_update candidate
  -> schema/policy validation
  -> separate request-local apply/commit decision
```

Unpack itself does not persist, commit, or mutate RelayCTX working memory.

## Reference-resolution policy

Recommended precedence:

```text
1. explicit nouns and constraints in the current user turn
2. RelayCTX request-local/RAM-side working state
3. minimum user confirmation among plausible candidates
4. RelayMEM Retrieval only after an explicit or confirmed long-term scope
```

Decision examples:

| State | RelayINT action | RelayMEM action |
|---|---|---|
| One clear active-CTX referent | resolve and continue | do not retrieve |
| Multiple plausible active-CTX referents | ask candidate clarification | do not retrieve |
| No active-CTX candidate | ask open clarification | do not retrieve |
| Explicit memory request with clear scope | permit retrieval when scene allows | retrieve allowed scope |
| Confirmed reference but CTX lacks facts | request retrieval | retrieve allowed scope |
| Scene blocks external memory | continue/clarify within policy | do not retrieve |

An ambiguous reference must never trigger silent long-term recall.

## MVP responsibilities

RelayINT should:

1. detect pronoun-like and continuation references,
2. resolve references against RelayCTX working state when confidence is high,
3. identify topic and action anchors,
4. classify user intent,
5. decide whether memory retrieval is needed,
6. block retrieval for unresolved ambiguity,
7. emit clarification or recovery intent when confidence is insufficient,
8. emit a content-free decision projection.

## Runtime-private intent artifact

A request-local artifact may contain semantic content:

```yaml
relayint_runtime_intent:
  schema_version: relayint.intent.v1
  path: fast_path
  source: current_turn
  resolved_reference: true
  resolved_reference_text: "それ"
  resolved_to: relayint_mvp_scope
  topic_anchor: relayint
  user_intent: continue_design
  action_intent: define_mvp_scope
  mem_query_needed: false
  mem_query_reason: null
  ambiguity:
    has_ambiguity: false
    candidates: []
  confidence: 0.88
  action: continue_without_clarification
```

This artifact is content-bearing and remains request-local or protected by an explicit diagnostic policy.

## Content-free intent projection

Default trace/audit surfaces receive only allowlisted metadata:

```yaml
relayint_projection:
  schema_version: relayint.projection.v1
  path: fast_path
  llm_called: false
  reference_present: true
  reference_resolved: true
  ambiguity_present: false
  ambiguity_candidate_count: 0
  mem_query_needed: false
  confidence_band: high
  action: continue_without_clarification
  reason_ids:
    - single_high_salience_referent
    - active_topic_continuation
```

Do not persist resolved reference text, candidate labels, topic strings, or user message content in the default projection.

## MEM retrieval decision

RelayINT decides whether retrieval is needed; RelayMEM performs the read.

```text
clear short-term CTX resolution
  -> mem_query_needed=false

explicit or confirmed long-term recall scope
  -> mem_query_needed=true

ambiguous reference
  -> mem_query_needed=false
  -> clarification required

scene policy blocks external memory
  -> mem_query_needed=false
  -> current-context-only handling
```

## Quick clarification route

A quick clarification is an explicit short-circuit route, not direct response-body mutation by RelayINT.

```text
RelayINT clarification candidate
  -> compatibility and active-transaction gates
  -> RelaySCN scene/formality/recovery gate
  -> RelayRUN short-circuit route and checkpoint state
  -> output adapter
  -> RelayCTX visible/internal safety boundary when applicable
  -> Return-side RelayEMO bounded style hint
  -> Output-side RelaySCN observation
  -> user-visible clarification
```

Rules:

- default-off until its apply gate is enabled,
- no quick clarification during incompatible tool/structured/multimodal transactions,
- no bypass of recovery or safety policy,
- no direct user-visible text finalized by RelayRUN,
- templated text remains bounded and passes the normal output contract,
- content-free diagnostics record template ID/class, not the rendered text.

## Recovery interaction

RelayINT may request recovery when:

- context candidates remain contradictory,
- repeated user correction indicates drift,
- scene stability is too low,
- a safe next action cannot be determined.

RelaySCN resolves recovery policy; RelayRUN orchestrates waiting-user or recovery state. RelayINT does not rewrite scene policy or emit recovery text directly.

## Execution paths

### Fast Path

- deterministic rules and scoring,
- default path,
- no LLM call,
- reads bounded current-turn and CTX working metadata.

### Main LLM Short-INT

- optional and default-off,
- short structured interpretation only,
- must not reuse the normal answer as an unvalidated intent artifact.

### Small LLM INT

- future optimization,
- requires measured CPU/RAM latency and cache/session behavior,
- not part of RelayINT's component definition.

## Threshold posture

Thresholds are policy/config values, not durable semantic truth. Suggested categories:

```text
high confidence
  continue automatically

medium confidence
  ask bounded candidate clarification

low confidence
  ask open clarification or enter recovery
```

Exact numeric defaults belong in implementation/config documentation and tests.

## Non-goals

RelayINT does not:

- write MEM,
- mutate RelaySOUL,
- inspect the generated answer,
- commit CTX update candidates by itself,
- restore cross-thread history,
- silently retrieve memory for ambiguity,
- directly mutate response bodies without the explicit clarification route,
- expose semantic intent content through default trace/audit records.

## Summary

```text
current turn + RelaySCN policy + RelayCTX working state
  -> RelayINT resolve / clarify / retrieve decision
  -> RelayMEM only when explicit and allowed
  -> RelayCTX Repack
```
