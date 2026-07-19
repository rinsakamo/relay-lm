---
relaylm_doc_type: adr
relaylm_authority: decision_to_adopt_single_response_call_ordinary_conversation_and_deferred_subjective_formation
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-19
relaylm_supersedes: []
relaylm_superseded_by: null
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - ordinary conversational Main LLM timing changes
  - RelayCTX session-continuity ownership changes
  - RelaySLP assessment or formation timing changes
  - RelayRUN resource-scheduling ownership changes
  - durable Forget entry-point policy changes
relaylm_not_authoritative_for:
  - exact SourceEvent or evidence-admission schema
  - exact RelayCTX working-state or session-overlay schema
  - exact RelayREF observation schema
  - exact Shared Assessment or Subjective MEM schema
  - exact RelayRUN resource-provider or job-request schema
  - exact storage, cache-invalidation, commit, or migration mechanics
  - current implementation status or implementation sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - 0003-subjective-mem-direction.md
  - relayatn_pre_request_authority_separation.md
  - ../architecture/pipeline_responsibility_design.md
  - ../architecture/runtime/request-response-pipeline.md
  - ../architecture/runtime/scheduler.md
  - ../architecture/memory/formation.md
---
# ADR 0004: Single-response-call ordinary conversation and deferred subjective formation

## Status

Accepted as target architecture on 2026-07-19. Implementation remains separately governed by the Project Execution Plan and Project Status.

## Context

RelayLM primarily targets local 7B–13B-class models and a latency-sensitive single-GPU environment. Ordinary conversation must preserve conversational tempo, streaming, TTS continuity, and predictable fallback behavior. Subjective memory formation benefits from reading related turns together after corrections, qualifications, and topic boundaries become visible.

Treating Shared Assessment and Subjective MEM formation as mandatory second and third Main LLM calls inside every ordinary conversational turn would:

- compete with response generation and TTS for the same backend;
- delay a later user turn for memory work not required to answer it;
- form fragmented per-turn memory before natural clarification arrives;
- encourage longer user-facing replies merely to hide internal latency;
- blur RelayCTX continuity, RelayREF observation, and RelaySLP compilation ownership.

The architecture already separates RelayINT before action, RelayREF after generated output, and RelaySLP outside the current user-visible answer. This ADR fixes the timing and ownership consequences of that separation.

## Decision

### 1. One Main LLM response-generation call on the ordinary no-tool conversational critical path

A normal managed no-tool conversation turn requires one Main LLM response-generation call:

```text
current user input
  -> governed source capture
  -> RelayRUN request shell
  -> RelayREL
  -> input-side RelaySCN
  -> input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval, when allowed
  -> RelayCTX Repack
  -> Main LLM response generation
  -> streaming/output pipeline
```

This decision does not prohibit:

- a separately governed optional SCN, EMO, INT, or REF analyzer probe;
- a multi-call tool transaction whose exact lifecycle is governed by a tool contract;
- deferred RelaySLP assessment, subjective formation, or adjudication;
- explicit pass-through behavior.

Optional probes must remain busy-skippable or otherwise governed and must not become an implicit second mandatory response-generation call.

The Main LLM owns response generation only. It does not commit MEM, scene, affect, relationship, SOUL, or persistence state. A bounded internal candidate may accompany output, but owning components validate and apply only their own fields.

### 2. Streaming emission and response-complete finalization are separate paths

The first user-visible token must not wait for a response-complete RelayREF observation.

```text
Main LLM stream
  |- chunk path
  |    -> incremental Unpack and safety boundary
  |    -> user / TTS / avatar emission
  |    -> RelayRUN chunk idempotency
  |
  `- response-complete path
       -> finalized assistant-origin Evidence
       -> RelayREF response-complete observation
       -> return/output observations for owning components
       -> RelayRUN end-of-turn finalization
```

Per-chunk emission and response-complete finalization have separate timing and idempotency. Output-side observations never retroactively condition the response that produced them.

### 3. Governed evidence persists independently of response and memory formation

Source occurrence, evidence admission, turn admission, response success, CTX continuity, and durable memory formation remain orthogonal.

```text
source occurrence
  -> governed SourceEvent / Protected Source Evidence

admitted turn
  -> interactive response path

Protected Source Evidence
  -> deferred RelaySLP path
```

RelayATN rejection, Main LLM failure, SLP deferral, or SLP failure must not erase admitted governed evidence.

A finalized assistant response is represented separately from RelayREF observation:

```text
assistant-origin Evidence
  what response content was actually emitted and its completion status

RelayREF observation
  bounded low-authority classification of what that response did
```

Assistant-origin Evidence never becomes user-origin fact merely because it is retained for formation.

### 4. RelayCTX owns immediate and session-local continuity

During an active conversation, RelayCTX owns bounded working state needed for natural continuation:

- current topic and task;
- active question and unresolved slots;
- prior decisions and referable items;
- selected recent continuity;
- session-local correction overlays;
- session-local recall suppression.

Newer correction or qualification evidence is packed later and more saliently than older retrieved MEM. When a correction target is resolved, RelayCTX may suppress the matched old item from session-local packing. This is a best-effort input-control guarantee, not a guarantee about probabilistic Main LLM output.

RelayCTX must not intentionally privilege a resolved older formulation over explicit newer evidence. It cannot guarantee that a model will never repeat old content.

RelayCTX is not a pending-MEM authority. Governed Evidence, not CTX alone, is the durable source for later formation.

### 5. RelaySLP forms memory out of band and preferably by episode

RelaySLP runs after the current user-visible response, normally when one or more of these conditions occur:

- the session becomes idle;
- the scene or topic crosses a meaningful boundary;
- the session closes;
- enough governed evidence accumulates;
- an explicit remember intent raises priority;
- an operator or scheduler invokes SLP;
- the backend has sufficient resource budget.

RelaySLP may read multiple related SourceEvents together.

The reference formation path is split:

```text
Protected Source Evidence
  -> SLP Assessment Pass without SOUL or character identity
  -> validated character-independent Shared Assessment
  -> SLP Subjective Formation Pass
       + identified SOUL revision
       + MEMORY policy revision
       + BOUNDARY revision
       + bounded REL / SCN constraints
       + non-authoritative EMO evidence
  -> Subjective MEM proposal
  -> deterministic validation and policy gates
  -> RelayMEM / workspace commit or hold
```

This preserves ADR 0003 structurally: evidence support and Shared Assessment are not conditioned by SOUL.

A fused one-call SLP output is not the reference path. It may exist only as a non-authoritative optimization experiment after Japanese fixtures show acceptable equivalence and low SOUL contamination against the split reference path. A fused result must fail closed to split processing when its boundary cannot be validated.

### 6. Additional LLM adjudication is a deferred SLP exception

Difficult cases may be held for later adjudication, including:

- material contradiction;
- uncertain participant or relationship identity;
- private/group scope conflict;
- a possible correction or supersession with unclear target;
- several plausible existing MEM relations.

The default result is hold, abstain, or evidence-only. A later SLP adjudication call is optional and must not block conversation.

### 7. RelayREF is a low-authority response-complete observer

RelayREF observes what generated output actually did after safe output separation. It may report bounded observations such as:

- speech-act class;
- answer or clarification completion candidate;
- repair or apology attempt;
- assistant inference presence;
- topic or task-boundary candidate;
- unresolved-reference presence;
- complete, truncated, cancelled, or transport-failed output class.

RelayREF does not rewrite output, replace RelayINT, classify authoritative scene, infer durable affect facts, or form MEM. RelayCTX, RelayEMO, RelaySCN, and RelaySLP consume only observations relevant to their own authority.

Ordinary RelayREF processing must not require another Main LLM response-generation call.

### 8. RelayRUN owns orchestration across separate control and compute domains

A Runtime Resource Provider reports backend and hardware observations such as active generation, queue depth, resource pressure, recent latency, cancellation capability, and backend health.

RelayRUN owns operational timing and lifecycle but keeps two priority domains distinct.

```text
control-plane fence domain
  Correct / Forget / lifecycle mutation fence
  revision invalidation
  retrieval exclusion
  cancellation and conflict signal

compute/resource domain
  interactive response generation
  voice-out
  optional probes
  Primary Subjective MEM formation
  Secondary consolidation
  maintenance
```

Control-plane mutation fences are not merely lower-priority GPU jobs. They may become effective immediately for future retrieval, packing, and uncommitted writes even when already-emitted visible output cannot be withdrawn.

The Resource Provider reports facts; RelayRUN chooses run now, defer, busy-skip, cancel, retry, or operational-job coalescing. RelayRUN remains semantic-neutral. The owning component defines semantic fallback.

A separate host-level supervisor is unnecessary for the initial single-backend, single-GPU deployment. It becomes relevant only when several RelayRUN instances or GPU-consuming subsystems require shared host allocation.

### 9. Conversational forgetting is not durable deletion

Natural-language requests such as “do not bring that up again in this conversation” or “forget what I just said” default to RelayINT/RelayCTX session-local suppression when no durable management authority was invoked.

Durable Forget or canonical memory modification occurs only through a governed management path, such as:

- Character Workspace / SOUL Lab Forget;
- the governed loopback API;
- direct human editing of canonical Markdown memory pages;
- a future explicit management command with equivalent authority.

After durable canonical mutation, stale cache projections must fail closed and must not remain retrieval-visible. Evidence purge remains a separate evidence-governance operation.

### 10. Pass-through delegates context authority and disables managed memory by default

Explicit pass-through delegates backend context authority to the client. By default it does not silently add:

- managed RelayCTX reconstruction;
- RelayMEM retrieval;
- automatic governed Evidence capture for memory formation;
- RelayREF semantic observation;
- RelaySLP enqueue or character-memory mutation.

Minimum transport and RelayRUN accounting may remain when required by the adapter/runtime contract. Evidence capture, RelayREF, or deferred formation may be enabled only by a separate explicit route contract and remain isolated from managed-route assumptions.

## Consequences

### Positive

- Conversational latency is not coupled to memory-formation completion.
- Related turns can form one coherent episodic memory instead of fragmented per-turn records.
- Current corrections become more salient without synchronous durable mutation.
- The architecture remains usable on one local GPU with TTS.
- Shared Assessment remains structurally independent of SOUL.
- Assistant response content and REF observation remain separate evidence classes.
- Mutation fences are not confused with GPU job priority.

### Costs

- Newly discussed content may not become durable MEM before the next turn or session.
- Pending evidence and formation jobs require durable queue and catch-up behavior.
- Session overlays and continuity handoffs require bounded owning contracts.
- The split reference SLP path may require two deferred model calls.
- Tool transactions, pass-through opt-ins, and streaming finalization require separate exact contracts.

## Rejected alternatives

### Run response, Shared Assessment, and Subjective MEM synchronously every turn

Rejected because the latter operations are not required for the current answer and create unacceptable coupling to local-backend latency.

### Extend user-facing responses to create hidden SLP time

Rejected because it increases cognitive load, occupies the backend longer, and distorts character behavior for an internal scheduling concern.

### Treat RelayCTX as the durable pending-memory store

Rejected because RelayCTX is bounded, rebuildable working state. Governed Evidence and durable operational coverage own persistence before MEM formation.

### Use one SOUL-bearing fused SLP call as the reference path

Rejected because instruction-only field separation cannot structurally guarantee that Shared Assessment remained independent of SOUL.

### Let RelayRUN decide semantic fallback

Rejected because RelayRUN owns timing and execution, while each semantic component owns the meaning of its degraded result.

### Interpret every natural-language “forget” as durable deletion

Rejected because conversational suppression and governed canonical mutation have different scope, reversibility, and error cost.

## Fixed boundaries

- The ordinary managed no-tool conversational critical path requires one Main LLM response-generation call.
- Streaming chunk emission and response-complete observation/finalization are separate paths.
- Evidence capture is independent of turn admission, response success, and SLP completion.
- Finalized assistant output and RelayREF observation are separate artifacts.
- RelayCTX owns immediate/session continuity, not durable MEM.
- Correction handling is best-effort input control and does not guarantee probabilistic model output.
- The reference SLP path validates Shared Assessment before SOUL-conditioned subjective formation.
- Additional adjudication is optional and confined to deferred SLP.
- RelayRUN separates control-plane fences from compute/resource priority and does not decide semantic meaning.
- Conversational suppression is not durable Forget.
- Explicit pass-through disables managed memory behavior by default unless a separate route contract opts in.
- Durable canonical mutation invalidates stale retrieval projections before ordinary retrieval may continue.
