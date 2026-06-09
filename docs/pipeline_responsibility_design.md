# RelayLM Pipeline Responsibility Design

## Purpose

This document describes the responsibility boundary of the RelayLM runtime pipeline.

It complements `docs/pipeline_implementation_plan.md`:

- `pipeline_implementation_plan.md` defines implementation order.
- This document defines pipeline responsibilities, current-vs-target differences, and INT / REF boundaries.

## Core rule

RelayLM should keep semantic responsibilities separate from runtime orchestration responsibilities.

```text
SCN = scene and policy controller
EMO = affect / expression controller
INT = input-side gate
MEM Retrieval = read-only memory retrieval
CTX Repack = Main LLM input construction
Main LLM = response generation
CTX Unpack = response/output candidate separation
REF = output-side observer
Output-side SCN = next-turn scene and persistence policy observation
RUN = runtime orchestration and checkpointing
SLP = out-of-band memory / SOUL compilation path
```

The most important boundary is:

```text
RelayINT = before action
RelayREF = after response
```

## Target runtime order

```text
User input
  -> RelayRUN request start / request shell
  -> PipelineContext
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Main LLM / backend forward
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> RelayRUN final artifact / trace / checkpoint summary
  -> User output
```

## Current implementation caveats

The target order above is the design direction, not a statement that every layer is fully implemented today.

Current caveats:

- `app.py` still carries too much orchestration and payload mutation logic.
- `PipelineContext` is the intended stabilization point for forwarded payload replacement, node results, diagnostics, and future RelayRUN handoff.
- Current `RelayRUN` is mostly a request-end artifact writer. It is not yet a true cross-cutting node-state reporter.
- Current `relayref.py` is named like REF, but its behavior is input-side unresolved reference / quick clarification logic. In the target design this is closer to RelayINT.
- `RelayCTX Unpack` is not yet a real response separation layer. Main LLM output is mostly returned directly.
- Early RelayREF should be lightweight and diagnostics-only. It should not require a second Main LLM call in the near term.

## Per-stage responsibilities

### 1. User input

Raw user input enters the proxy.

At this point, RelayLM has not yet committed to:

- the scene,
- the user's intent,
- whether memory should be retrieved,
- whether clarification is needed,
- whether the Main LLM should be called,
- or whether the request should short-circuit.

### 2. RelayRUN request shell

RelayRUN owns runtime execution state, not semantic meaning.

Current role:

- request-end artifact writing,
- trace / diagnostics artifact connection,
- recovery-related artifact summaries,
- request-level checkpoint-like records.

Target role:

- run_id / turn_id management,
- per-node status reporting,
- node started / completed / blocked / failed state,
- runtime checkpoint persistence,
- resume metadata,
- transport/runtime failure handling,
- recovery transition artifact creation.

RelayRUN should remain semantic-neutral. It should not decide user intent, scene, memory meaning, or final response style.

### 3. PipelineContext

PipelineContext is the request-local coordination object.

Responsibilities:

- keep the current forwarded payload,
- record forwarded payload replacement reasons,
- collect node results,
- collect diagnostics,
- provide a stable handoff point for RelayRUN artifacts,
- avoid scattered mutation of `forwarded_payload` inside `app.py`.

Target behavior:

```text
Any runtime step that replaces the backend-bound payload should do so through PipelineContext and provide a reason.
```

### 4. Input-side RelaySCN

Input-side RelaySCN estimates the current scene and resolves scene policy for the current turn.

Responsibilities:

- classify scene type,
- estimate safety sensitivity,
- estimate formality,
- choose memory scope,
- choose expression allowance,
- decide whether persistence should be blocked,
- decide whether recovery mode is needed,
- provide policy constraints to downstream modules.

Example scene types:

- casual_chat,
- design_talk,
- implementation_work,
- review_work,
- formal_document,
- system_ops,
- vtuber_roleplay,
- recovery,
- medical_or_safety.

SCN answers: what kind of situation is this?

### 5. Input-side RelayEMO

Input-side RelayEMO estimates affect and expression intent without claiming to know the user's true emotion.

Responsibilities:

- emit `user_affect_estimate`,
- initialize `assistant_emotion_state`,
- emit `affect_intent_vector`,
- respect scene policy,
- keep expression hints gated by confidence, scene, and safety.

RelayEMO should not own task routing, clarification decisions, memory writes, or final persistence decisions.

EMO answers: what tone or expression pressure is appropriate?

### 6. RelayINT

RelayINT is the input-side gate.

Responsibilities:

- classify user intent,
- detect unresolved references,
- detect missing slots,
- decide whether the request can proceed,
- decide whether clarification is needed,
- decide whether a high-confidence short-circuit clarification should bypass the Main LLM,
- emit blocked / short-circuit / continue decisions.

RelayINT owns pre-action ambiguity handling.

Examples:

```text
"次に進もう"
  -> infer continuation intent from current project context when confidence is sufficient.

"それを直して"
  -> unresolved target may require clarification.

"マージして"
  -> task intent is repository operation, but target branch / PR must be grounded by current context or tool state.
```

RelayINT answers: what is being requested, and can RelayLM safely proceed?

### 7. RelayMEM Retrieval

RelayMEM Retrieval is read-only in the normal response path.

Responsibilities:

- retrieve relevant compiled memory pages or snippets,
- respect scene memory scope,
- filter stale / contradictory / unsafe / unapproved memory,
- emit token-budgeted retrieval blocks,
- emit diagnostics when memory is blocked or empty.

RelayMEM Retrieval should not mutate MEM or SOUL.

Memory writes belong to SLP / MEM compilation paths outside the normal response path.

MEM Retrieval answers: what should RelayLM remember for this turn?

### 8. RelayCTX Repack

RelayCTX Repack builds the payload that will be sent to the Main LLM.

Responsibilities:

- combine system / developer / user / memory / recent context inputs,
- stabilize prompt layout,
- preserve persona-stable and KV-reuse-aware layout where possible,
- inject approved memory or short-term CTX blocks,
- apply token budget truncation,
- record all payload mutation reasons,
- produce the final backend-bound forwarded payload.

Current overlap:

- `request_compiler.py`,
- memory injection,
- short-term CTX injection,
- token budget truncation,
- forwarded payload stabilization.

Because this stage is heavy, it should be hardened before adding more downstream behavior.

CTX Repack answers: what exactly should the Main LLM see?

### 9. Main LLM / backend forward

The Main LLM generates the response.

Responsibilities:

- answer the user's request,
- produce user-visible response text,
- optionally emit structured internal/update candidates only when a safe format exists,
- avoid owning runtime checkpointing, persistence, or scene policy decisions.

Transport and backend failures are not semantic failures. They should be normalized by proxy transport / RelayRUN handling.

Main LLM answers: what should be said?

### 10. RelayCTX Unpack

RelayCTX Unpack separates the Main LLM output into user-visible text and internal candidates.

Responsibilities:

- extract user-visible response text,
- strip or block internal markers,
- parse optional `ctx_working_update`,
- block unsafe or malformed update candidates,
- prevent MEM / SOUL / SLP candidates from being accepted when unpacking fails.

MVP fail-safe behavior:

```text
If user-visible text is available, return it.
If internal candidate parsing fails, block internal updates and record diagnostics.
```

CTX Unpack answers: what is safe to show, and what is only an internal candidate?

### 11. RelayREF

RelayREF is the output-side observer.

Responsibilities:

- inspect response-level diagnostics after Main LLM output,
- detect empty response,
- detect internal marker leakage,
- detect obviously unsafe diagnostic leakage,
- detect likely scene / policy mismatch as warning only,
- emit observations for Output-side RelaySCN, RelayRUN diagnostics, and future SLP.

Early RelayREF should not:

- regenerate by default,
- replace user-visible output by default,
- own clarification decisions,
- own scene transitions,
- own memory writes,
- require a second Main LLM call.

RelayREF answers: did anything concerning happen after generation?

### 12. Return-side RelayEMO

Return-side RelayEMO adjusts expression after the main response is available.

Responsibilities:

- apply scene-gated tone adjustment,
- add or suppress text markers,
- provide TTS / avatar style hints when allowed,
- avoid meaning-changing rewrites,
- suppress expression in formal, safety, review, or recovery-sensitive scenes.

If meaning-changing repair is needed, it should be routed through REF / SCN / RUN policy rather than hidden inside EMO.

Return-side EMO answers: how should this response be expressed?

### 13. Output-side RelaySCN

Output-side RelaySCN observes the completed turn and prepares next-turn scene state.

Responsibilities:

- evaluate next-turn scene transition,
- emit recovery hints,
- emit persistence block reasons,
- decide whether next turn should enter recovery mode,
- consume REF observations and unpack diagnostics,
- keep normal scene transition as next-turn state rather than rewriting the current response.

Immediate current-response blocking should be limited to:

- safety-critical mismatch,
- internal leakage,
- empty or invalid output,
- recovery-critical cases.

Output-side SCN answers: what scene should govern the next turn?

### 14. User output

The user receives the final response after output-side policy and expression gates.

Normal responses should not expose internal diagnostics unless an explicit diagnostics mode is enabled.

### 15. RelaySLP / memory write path

RelaySLP is not part of the normal synchronous response path.

Responsibilities:

- compile memory candidates,
- structure raw evidence,
- prepare MEM update candidates,
- prepare SOUL proposal candidates,
- route candidates through persistence gates,
- preserve lineage and approval state.

SLP should not block normal response latency unless the scene or user explicitly requests a synchronous review.

SLP answers: what should be organized or proposed for persistence later?

## INT and REF do not conflict

RelayINT and RelayREF can both see ambiguity, but they act at different times and with different authority.

| Module | Timing | Authority | Example |
|---|---|---|---|
| RelayINT | Before Main LLM | Gate / continue / short-circuit / block | "This request is ambiguous; ask clarification." |
| RelayREF | After Main LLM | Observe / warn / diagnose | "The response may have answered an unresolved reference." |

Boundary rule:

```text
RelayINT decides whether to proceed.
RelayREF reports what happened after proceeding.
```

REF findings may inform future INT policy, Output-side SCN, RelayRUN diagnostics, or SLP candidates, but REF should not directly take over normal-turn control in the MVP.

## Failure routes

### INT high-confidence clarification

```text
RelayINT
  -> SHORT_CIRCUIT_CLARIFICATION
  -> quick clarification template
  -> minimal output-side processing
  -> RelayRUN artifact / diagnostics
  -> user output
```

The Main LLM should normally be bypassed for high-confidence clarification.

### MEM retrieval blocked or empty

```text
RelayMEM Retrieval
  -> empty or blocked retrieval result
  -> CTX Repack without retrieved memory
  -> diagnostics records blocked reasons
  -> Main LLM continues
```

Only memory-dependent requests should surface this to the user.

### CTX Repack token pressure

Degrade in this order:

1. Remove diagnostics / trace-only context.
2. Reduce retrieved memory.
3. Reduce short-term CTX blocks.
4. Shorten conversation history.
5. Use a safe fallback response if no valid payload can be produced.

### Main LLM / backend failure

Backend transport failures belong to proxy transport / RelayRUN handling.

Examples:

- timeout,
- connection error,
- invalid backend response,
- stream failure before first token,
- stream failure after partial output.

These should be recorded as runtime failures, not as RelayINT or RelayREF semantic failures.

### CTX Unpack failure

```text
Return user-visible response text when available.
Block ctx_working_update / MEM / SOUL / SLP candidates.
Record unpack_failed diagnostics.
```

### REF warning

Early RelayREF warnings should be diagnostics-only unless they detect:

- internal marker leakage,
- forbidden diagnostic leakage,
- empty response,
- safety-critical mismatch.

## Near-term implementation stance

The near-term goal is not to implement every target stage fully.

The safe order is:

```text
app.py lightweight separation
  -> documentation consolidation
  -> CTX Repack boundary hardening
  -> RelayINT split / alias from current relayref.py behavior
  -> minimal RelayCTX Unpack
  -> failure route table / node result handling
  -> lightweight RelayREF diagnostics-only observer
  -> Output-side SCN
  -> RelayRUN cross-cutting checkpoint layer
  -> RelaySLP separation
```

Do not make RelayREF smart before input and context boundaries are stable.

Do not make RelayRUN semantic before node reporting and checkpoints are stable.

Do not let Retrieval mutate memory in the normal response path.
