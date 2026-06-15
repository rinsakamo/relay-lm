# RelayLM Pipeline Responsibility Design

## Purpose

This document defines the stable responsibility boundaries of the RelayLM runtime pipeline.

It does **not** define current implementation status, completed phases, or the next task. Those belong to [Pipeline Implementation Plan](pipeline_implementation_plan.md).

When this document and an implementation-status note differ:

- this document is authoritative for component ownership and pipeline order,
- `pipeline_implementation_plan.md` is authoritative for phase status and sequencing,
- dedicated module and contract documents are authoritative for schema details.

## Core rule

RelayLM keeps semantic decisions separate from runtime orchestration.

```text
SCN = scene and policy controller
EMO = affect / expression controller
INT = input-side intent and ambiguity gate
MEM Retrieval = read-only memory retrieval
CTX Repack = Main LLM input construction
Main LLM = response generation
CTX Unpack = visible-output and internal-candidate separation
REF = output-side observer
Output-side SCN = next-turn scene and persistence observation
RUN = runtime orchestration, fallback/recovery, checkpointing, and trace
SLP = out-of-band memory / SOUL compilation path
Adapter = OpenAI-compatible transport boundary
```

The most important timing boundary is:

```text
RelayINT = before action
RelayREF = after response
```

## Canonical runtime order

```text
User input
  -> RelayRUN request shell
  -> PipelineContext
  -> Input-side RelaySCN
  -> Input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM / backend forward
  -> RelayCTX Unpack
  -> RelayREF
  -> Return-side RelayEMO
  -> Output-side RelaySCN
  -> RelayRUN final artifact / trace / checkpoint summary
  -> User output

Out-of-band after-turn path:
  governed evidence
  -> RelaySLP
  -> MEM update candidates / SOUL proposals
  -> persistence and approval gates
```

The Runtime Compile Gate is a request-local decision phase. It consumes route, compatibility preflight, scene policy, intent, retrieval, and budget outcomes. It is not a standalone semantic component and must not be named as a separate `RelayPLC` module.

## Ownership invariants

1. RelaySCN owns scene and policy, not prompt assembly.
2. RelayINT owns pre-action proceed/block/clarification, not memory search or final wording.
3. RelayMEM Retrieval reads approved memory; it never writes in the normal response path.
4. RelayCTX owns selected context layout and token-budget degradation, not semantic policy.
5. RelayREF observes generated output; it does not replace RelayINT or RelaySCN.
6. RelayRUN owns execution state and recovery orchestration, not semantic meaning.
7. RelaySLP prepares deferred memory and SOUL candidates; it does not answer the current turn.
8. Adapters preserve protocol and transport semantics; they do not decide persona, scene, or memory policy.
9. User-visible text must pass the normal output pipeline; RelayRUN and RelaySLP do not directly finalize character-facing text.
10. Typed content-free projections are used for audit/trace surfaces; raw request, prompt, memory, and response bodies are not copied into generic diagnostics.

## Per-stage responsibilities

### 1. User input

Raw request evidence enters the proxy.

No semantic conclusion has yet been committed about:

- scene,
- user intent,
- reference resolution,
- retrieval need,
- clarification need,
- Main LLM execution,
- persistence,
- or short-circuit behavior.

Client-provided messages are request evidence, not automatically trusted backend context. Current-turn and current-instruction evidence are handled through the applicable client-authority contracts.

### 2. RelayRUN request shell

RelayRUN owns runtime execution state and lifecycle.

Responsibilities:

- create and propagate `run_id` / `turn_id`,
- establish request and node execution state,
- record started / completed / skipped / blocked / failed states,
- maintain checkpoint and resume metadata,
- connect trace, diagnostics, and artifact lineage,
- apply retry, timeout, skip, fallback, and recovery orchestration,
- preserve idempotency and duplicate-prevention rules,
- aggregate request-end status,
- expose waiting-user and recovery-transition state.

RelayRUN remains semantic-neutral. It does not decide user intent, scene meaning, memory meaning, persona changes, or final response style.

### 3. PipelineContext

`PipelineContext` is the request-local coordination object.

Responsibilities:

- preserve `original_payload`,
- hold the current backend-bound `forwarded_payload`,
- replace the forwarded payload only through explicit mutation methods,
- record payload replacement reasons,
- hold route and request-scope state,
- hold runtime-private content-bearing intermediate results,
- collect ordered `PipelineNodeResult` records,
- collect detached Unpack/update candidates,
- provide stable handoffs to diagnostics and RelayRUN,
- prevent scattered untracked request mutation.

Runtime-private content-bearing fields must not be copied directly into content-free diagnostics.

### 4. Input-side RelaySCN

Input-side RelaySCN estimates the current scene and resolves current-turn policy.

Responsibilities:

- classify scene type,
- estimate safety sensitivity,
- estimate formality,
- select memory scope,
- select expression allowance,
- determine persistence blocking,
- determine recovery mode,
- determine whether user confirmation is required,
- provide policy constraints to INT, MEM, CTX, EMO, RUN, and SLP.

Representative scene types include:

- `casual_chat`,
- `design_talk`,
- `implementation_work`,
- `review_work`,
- `formal_document`,
- `system_ops`,
- `vtuber_roleplay`,
- `medical_or_safety`,
- `recovery`.

SCN answers: **what situation and policy govern this turn?**

### 5. Input-side RelayEMO

Input-side RelayEMO estimates affect and expression pressure without claiming to know the user's true emotion.

Responsibilities:

- emit bounded `user_affect_estimate`,
- initialize assistant expression/emotion state,
- emit affect/style intent vectors or hints,
- obey RelaySCN expression and safety gates,
- keep confidence and uncertainty visible to downstream policy,
- avoid turning inferred affect into durable user fact.

RelayEMO does not own task routing, clarification decisions, memory writes, or persistence policy.

EMO answers: **what expression pressure is appropriate?**

### 6. RelayINT

RelayINT is the input-side semantic gate.

Responsibilities:

- classify user intent,
- detect unresolved references,
- resolve high-confidence references from current CTX working state,
- detect missing slots,
- decide whether the request may proceed,
- decide whether clarification is required,
- decide whether memory retrieval is needed,
- decide whether a safe high-confidence clarification may short-circuit the Main LLM,
- emit continue / block / short-circuit decisions and reasons.

RelayINT owns pre-action ambiguity handling.

Examples:

```text
"次に進もう"
  -> continue from the current grounded project state when confidence is sufficient.

"それを直して"
  -> ask clarification when the target cannot be resolved safely.

"前に決めた内容を思い出して"
  -> request scoped RelayMEM retrieval when the requested memory scope is explicit or confirmed.
```

RelayINT must not silently use long-term memory to guess an ambiguous reference.

INT answers: **what is being requested, and may RelayLM safely proceed?**

### 7. RelayMEM Retrieval

RelayMEM Retrieval is read-only in the normal response path.

Responsibilities:

- retrieve relevant compiled memory pages or snippets,
- obey RelaySCN memory scope,
- obey RelayINT retrieval intent,
- filter stale, contradictory, unsafe, blocked, or unapproved memory,
- emit bounded retrieval candidates or blocks,
- record empty, miss, and blocked reasons,
- preserve source and confidence metadata for downstream selection.

RelayMEM Retrieval does not mutate MEM or SOUL. Writes and consolidation belong to RelaySLP and persistence gates.

MEM Retrieval answers: **what approved memory evidence is useful for this turn?**

### 8. RelayCTX Repack

RelayCTX Repack constructs the backend-bound context.

Responsibilities:

- combine RelayLM-owned system/developer policy, current user evidence, approved memory, scene state, and selected recent context,
- preserve stable persona and policy prefixes,
- keep dynamic evidence after stable anchors,
- select the smallest sufficient context rather than filling the token budget,
- inject approved short-term CTX and memory blocks,
- apply token-budget degradation,
- preserve compatibility-sensitive request fields,
- record every backend-bound payload replacement reason,
- produce the final candidate `forwarded_payload` for compile-gate approval.

RelayCTX Repack does not decide scene, intent, retrieval authority, persistence, or runtime fallback.

CTX Repack answers: **what exactly should the Main LLM see?**

### 9. Runtime Compile Gate

The Runtime Compile Gate decides whether the prepared request may be forwarded in its current form.

Inputs may include:

- route and mode,
- client-authority preflights,
- request compatibility,
- RelaySCN policy,
- RelayINT decision,
- retrieval status,
- CTX Repack result,
- token-budget status,
- active tool transaction state.

Outputs include:

- ready / blocked / skipped / degraded decision,
- stable blocked or fallback reasons,
- selected runtime route,
- content-free decision artifact.

It does not generate semantic content and does not replace RelayRUN orchestration.

### 10. Main LLM / backend forward

The Main LLM generates the response from the approved backend-bound request.

Responsibilities:

- answer the user's request,
- produce user-visible response content,
- optionally emit explicitly versioned internal candidates when a safe contract exists,
- preserve tool/structured-output behavior when applicable,
- avoid owning checkpointing, persistence, scene policy, or memory mutation.

Transport and backend failures are runtime failures. They are normalized by adapters and RelayRUN rather than classified as INT or REF failures.

Main LLM answers: **what should be said or emitted?**

### 11. RelayCTX Unpack

RelayCTX Unpack separates visible output from internal candidates.

Responsibilities:

- extract user-visible response text or output parts,
- suppress or block internal markers,
- parse only explicitly supported versioned candidate envelopes,
- validate shape, size, ordering, and allowed fields,
- detach valid candidates from user-visible output,
- block malformed or ambiguous candidates,
- prevent MEM, SOUL, SLP, or CTX updates when Unpack validation fails,
- emit content-free diagnostics and a node result.

Fail-safe rule:

```text
When safely recoverable visible output exists, preserve it.
When internal parsing fails, block internal candidates and record diagnostics.
```

CTX Unpack answers: **what is safe to show, and what remains only a candidate?**

### 12. RelayREF

RelayREF is the output-side observer.

Responsibilities:

- inspect response-level diagnostics after generation,
- detect empty or invalid output,
- detect internal-marker or diagnostic leakage,
- detect likely scene/policy mismatch as an observation,
- emit observations for Output-side SCN, RelayRUN, and future SLP analysis.

RelayREF does not own:

- pre-action clarification,
- normal-turn regeneration,
- hidden meaning-changing rewrites,
- scene transitions,
- memory writes,
- direct user-visible replacement by default.

REF answers: **did anything concerning happen after generation?**

### 13. Return-side RelayEMO

Return-side RelayEMO controls expression after visible response content is available.

Responsibilities:

- apply scene-gated tone/style adjustments,
- add or suppress allowed text markers,
- provide TTS/avatar expression hints,
- bound expression intensity,
- avoid meaning-changing rewrites,
- suppress expression where formality, review, safety, or recovery policy requires it.

Meaning-changing repair is routed through REF / SCN / RUN policy, not hidden inside EMO.

Return-side EMO answers: **how should the response be expressed?**

### 14. Output-side RelaySCN

Output-side RelaySCN observes the completed turn and prepares next-turn policy.

Responsibilities:

- evaluate scene transition,
- consume REF and Unpack observations,
- emit next-turn recovery hints,
- emit persistence-block reasons,
- determine whether the next turn enters recovery,
- keep ordinary scene transitions as next-turn state rather than rewriting the current response.

Immediate current-response blocking is reserved for cases such as:

- safety-critical mismatch,
- internal leakage,
- empty or invalid output,
- recovery-critical invalid state.

Output-side SCN answers: **what scene and policy should govern the next turn?**

### 15. User output

The user receives output only after the applicable visible-output, scene, expression, and transport gates.

Normal responses must not expose internal diagnostics, prompt blocks, private memory content, runtime-private artifacts, or internal candidate envelopes.

### 16. RelaySLP / deferred persistence path

RelaySLP is outside the latency-critical normal response path.

Responsibilities:

- read governed raw evidence and runtime artifacts,
- extract memory and SOUL candidates,
- classify safety and target scope,
- merge, hold, reject, or propose candidates,
- maintain lineage and source references,
- lint compiled memory,
- update indexes/logs through explicit apply gates,
- emit SOUL proposals rather than mutating SOUL directly.

SLP does not directly produce the current response or bypass waiting-user, scene, approval, and persistence gates.

SLP answers: **what should be organized or proposed for later persistence?**

### 17. Adapter boundary

Adapters preserve frontend/backend interoperability.

Responsibilities:

- preserve OpenAI-compatible request and response shape,
- preserve streaming semantics,
- map configured model names and headers,
- normalize transport errors,
- hide backend-specific transport details,
- avoid semantic changes to persona, scene, intent, memory, or response meaning.

Adapters answer: **how is the approved request transported compatibly?**

## INT and REF do not conflict

RelayINT and RelayREF may both observe ambiguity, but they operate at different times and authority levels.

| Module | Timing | Authority | Example |
|---|---|---|---|
| RelayINT | Before Main LLM | continue / short-circuit / block | “The target is unresolved; ask clarification.” |
| RelayREF | After Main LLM | observe / warn / diagnose | “The response may have answered an unresolved target.” |

```text
RelayINT decides whether to proceed.
RelayREF reports what happened after proceeding.
```

REF observations may inform future INT policy, Output-side SCN, RelayRUN diagnostics, or SLP candidates, but REF does not take over normal-turn control.

## Failure and degradation routes

### INT clarification

```text
RelayINT
  -> clarification decision
  -> compatibility and scene gates
  -> normal output pipeline
  -> RelayRUN artifact / checkpoint state
  -> user output
```

The Main LLM may be bypassed only through an explicit safe short-circuit route.

### MEM retrieval blocked or empty

```text
RelayMEM Retrieval
  -> empty / miss / blocked result
  -> CTX Repack without the blocked memory block
  -> diagnostics and node result
  -> Main LLM continues when the request is not memory-dependent
```

Memory-dependent requests may require clarification or a visible memory-unavailable response.

### CTX Repack token pressure

Default degradation order:

1. remove diagnostics/trace-only context,
2. reduce retrieved memory,
3. reduce optional short-term CTX hints,
4. shorten selected conversation context,
5. block or use an explicitly approved safe fallback when no valid request can be produced.

Required persona, safety, current-turn, and compatibility evidence must not be silently discarded.

### Pipeline node result

`PipelineNodeResult` is the common content-free record of what a node observed or decided.

```text
pipeline node executes
  -> PipelineNodeResult is recorded
  -> PipelineContext preserves order
  -> RelayRUN consumes status/reasons according to the active routing policy
```

A node result describes a node outcome; it does not by itself own semantic policy or transport behavior.

### Main LLM / backend failure

Examples:

- timeout,
- connection error,
- invalid backend response,
- stream failure before first visible chunk,
- stream failure after partial output.

These are adapter / RelayRUN runtime failures. They are not INT or REF semantic failures.

### CTX Unpack failure

```text
preserve safely recoverable visible output
block incomplete or invalid internal candidates
record content-free Unpack diagnostics
never expose internal markers
```

### Partial stream / output-adapter failure

```text
safe visible chunks already emitted
  -> preserve emitted chunks
  -> block incomplete candidates
  -> record partial-stream state
  -> avoid duplicate replay
  -> prepare next-turn recovery when required
```

### REF warning

REF observations remain diagnostics/policy evidence unless an explicit output gate handles leakage, empty output, invalid output, or a safety-critical mismatch.

## Status and sequencing ownership

Implementation status, compatibility aliases, current default gates, completed phases, and the next safe implementation boundary are maintained only in [Pipeline Implementation Plan](pipeline_implementation_plan.md).

This responsibility document should change only when the intended ownership or canonical pipeline itself changes.
