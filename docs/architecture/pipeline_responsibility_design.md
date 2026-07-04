---
relaylm_doc_type: stable_architecture
relaylm_authority: component_responsibility_and_canonical_target_order
relaylm_status: current
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - component responsibility changes
  - canonical runtime order changes
  - stable ownership invariant changes
relaylm_not_authoritative_for:
  - current implementation phase status
  - exact schema details
  - smoke procedures
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - pipeline_implementation_plan.md
  - current_target_migration_guide.md
  - file_first_character_workspace_design.md
---
# RelayLM Pipeline Responsibility Design

## Purpose

This document defines the stable responsibility boundaries of the RelayLM runtime pipeline.

It does **not** define current implementation status, completed phases, or the next task. Those belong to [Project Execution Plan](project_execution_plan.md) and [Project Status](../PROJECT_STATUS.md).

When this document and an implementation-status note differ:

- this document is authoritative for component ownership and pipeline order,
- `docs/PROJECT_STATUS.md` is authoritative for current implementation status,
- `project_execution_plan.md` is authoritative for phase sequencing,
- dedicated module and contract documents are authoritative for exact schemas.

## Core rule

RelayLM keeps semantic decisions separate from runtime orchestration.

```text
REL = relationship state and interaction policy controller
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
SLP = out-of-band workspace compilation path for MEM / SCENE / REL candidates and persona proposals
Adapter = OpenAI-compatible transport boundary
```

The most important timing boundary is:

```text
RelayINT = before action
RelayREF = after response
RelaySLP = after the current user-visible answer
```

## Canonical runtime order

Target architecture:

```text
User input
  -> RelayRUN request shell
  -> PipelineContext
  -> RelayREL target relationship selection
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
  -> MEM update candidates
  -> SCENE update candidates
  -> REL update candidates
  -> SOUL / STYLE / EMOTION / MEMORY / BOUNDARY proposals
  -> persistence and approval gates
```

`RelayREL` appears before RelaySCN in the target order so route/session-authenticated target relationship context can influence scene, expression, disclosure, and memory policy. RelaySCN still owns current scene policy; REL does not override public/private scene constraints or safety gates.

The Runtime Compile Gate is a request-local decision phase. It consumes route, compatibility preflight, relationship, scene policy, intent, retrieval, and budget outcomes. It is not a standalone semantic component and must not be named as a separate `RelayPLC` module.

## Ownership invariants

1. RelayREL owns selected target relationship state and interaction policy, not character identity, memory truth, current emotion, or scene classification.
2. RelaySCN owns scene and policy, not prompt assembly.
3. RelayINT owns pre-action proceed/block/clarification, not memory search or final wording.
4. RelayMEM Retrieval reads approved memory; it never writes in the normal response path.
5. RelayCTX owns selected context layout and token-budget degradation, not semantic policy.
6. RelayREF observes generated output; it does not replace RelayINT, RelayREL, or RelaySCN.
7. RelayRUN owns execution state and recovery orchestration, not semantic meaning.
8. RelaySLP prepares deferred workspace changes; it does not answer the current turn.
9. Adapters preserve protocol and transport semantics; they do not decide persona, relationship, scene, or memory policy.
10. User-visible text must pass the normal output pipeline; RelayRUN and RelaySLP do not directly finalize character-facing text.
11. Typed content-free projections are used for audit/trace surfaces; raw request, prompt, memory, relationship, scene, and response bodies are not copied into generic diagnostics.

## Per-stage responsibilities

### 1. User input

Raw request evidence enters the proxy.

No semantic conclusion has yet been committed about:

- active relationship target,
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

RelayRUN remains semantic-neutral. It does not decide user intent, scene meaning, memory meaning, persona changes, relationship meaning, or final response style.

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

### 4. RelayREL

RelayREL resolves relationship state and interaction policy for the authenticated target(s) in the request.

Responsibilities:

- select the applicable `relationships/<target>.md` instance from route/session identity, not by unsafe text guessing;
- compile target-specific relationship roles, trust, attachment, permissions, disclosure limits, repair preferences, and EMO gain hints;
- provide relationship-conditioned constraints to SCN, EMO, MEM, CTX, INT, and SLP;
- keep `SOUL.md` portable by preventing target-specific relationship parameters from being treated as character identity;
- emit content-free relationship projections for diagnostics.

RelayREL answers: **what relationship-specific interaction policy applies to this target?**

RelayREL must not:

- mutate SOUL, STYLE, EMOTION, SCENE, MEMORY, or BOUNDARY sources;
- infer a new important relationship role from a single turn;
- override scene/public-context disclosure limits;
- turn relationship state into durable user facts without governed source lineage;
- expose target-specific private relationship values in default diagnostics.

### 5. Input-side RelaySCN

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
- provide policy constraints to INT, MEM, CTX, EMO, RUN, REL, and SLP.

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

### 6. Input-side RelayEMO

Input-side RelayEMO estimates affect and expression pressure without claiming to know the user's true emotion.

Responsibilities:

- emit bounded `user_affect_estimate`,
- initialize assistant expression/emotion state,
- emit affect/style intent vectors or hints,
- obey RelaySCN expression and safety gates,
- obey RelayREL relationship-conditioned expression permissions,
- keep confidence and uncertainty visible to downstream policy,
- avoid turning inferred affect into durable user fact.

RelayEMO does not own task routing, clarification decisions, memory writes, relationship writes, scene state, or persistence policy.

EMO answers: **what expression pressure is appropriate?**

### 7. RelayINT

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

RelayINT must not silently use long-term memory or relationship state to guess an ambiguous reference.

INT answers: **what is being requested, and may RelayLM safely proceed?**

### 8. RelayMEM Retrieval

RelayMEM Retrieval reads approved memory for the current answer.

Responsibilities:

- run scoped retrieval only when policy and intent allow it,
- preserve character and namespace isolation,
- enforce lifecycle eligibility before prompt construction,
- return bounded runtime-private evidence to RelayCTX,
- emit content-free retrieval projections for diagnostics.

RelayMEM Retrieval does not write memory in the normal response path. RelaySLP writes future memory after the answer.

### 9. RelayCTX Repack

RelayCTX owns backend-bound context construction and token-budget degradation.

Responsibilities:

- combine stable character/workspace sources, selected relationship state, selected scene policy, expression hints, memory evidence, short-term CTX, and the latest user input;
- preserve authority order;
- protect KV-cache-friendly stable prefixes where possible;
- degrade low-priority dynamic context before high-authority character and boundary sources;
- avoid leaking runtime-private evidence into public diagnostics.

The current runtime phase order inside RelayCTX Repack is:

```text
relaymem runtime CTX/snippet injection
  -> RelayCTX short-term runtime injection
  -> token_budget_truncation
```

`token_budget_truncation` runs last among these mutations, so it is the final gate on the forwarded payload's estimated token total; every prior injection phase's output is subject to it before the backend forward. Injection phases must not run after truncation, since nothing downstream re-enforces the budget.

RelayCTX answers: **what exact bounded context should the backend model receive?**

### 10. Main LLM / backend forward

The backend model renders the response from the RelayCTX-packed context. It does not own RelayLM memory, relationship, scene, emotion, or persistence state.

### 11. RelayCTX Unpack

RelayCTX Unpack separates safe visible output from internal candidates and observations.

It does not apply memory or persona changes directly.

### 12. RelayREF

RelayREF is post-generation only.

Responsibilities:

- observe generated output after RelayCTX Unpack,
- produce bounded output-side observations for SLP, EMO, SCN, and audit paths,
- avoid replacing RelayINT or same-turn scene/retrieval decisions.

REF answers: **what can be safely observed after the response exists?**

### 13. Return-side RelayEMO

Return-side RelayEMO may emit display / TTS / avatar hints after safe visible output exists.

It must not rewrite meaning, execute TTS/avatar behavior, or promote expression state into durable memory.

### 14. Output-side RelaySCN

Output-side RelaySCN observes response-complete scene, recovery, and persistence signals for the next turn and RelaySLP.

It is not a general output rewriter.

### 15. RelaySLP after-turn path

RelaySLP consumes governed evidence after the current answer.

Responsibilities:

- create or update memory candidates,
- create scene candidates and scene consolidation proposals,
- create relationship update candidates,
- create SOUL / STYLE / EMOTION / MEMORY / BOUNDARY proposals when durable source changes are justified,
- enforce source lineage, idempotency, approval, and safety scopes,
- avoid writing during the current response path.

RelaySLP answers: **what should be remembered, organized, proposed, or rejected after this turn?**

## Content-free projection rule

Default diagnostics may contain only allowlisted classes, booleans, counts, bands, reason IDs, and stable opaque identifiers.

They must not contain:

- raw user text,
- prompt fragments,
- relationship file bodies,
- scene page bodies,
- memory bodies,
- source evidence text,
- visible response text,
- private filesystem roots,
- or full runtime-private artifacts.

## Summary

```text
Target response path:
  REL -> SCN -> EMO -> INT -> MEM -> CTX -> LLM -> REF -> EMO/SCN observation

Target after-turn path:
  governed evidence -> SLP -> MEM / SCENE / REL candidates and persona proposals
```
