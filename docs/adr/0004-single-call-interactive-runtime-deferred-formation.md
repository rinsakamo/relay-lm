---
relaylm_doc_type: adr
relaylm_authority: decision_to_adopt_single_call_interactive_runtime_and_deferred_subjective_formation
relaylm_status: target
relaylm_decision_status: accepted
relaylm_decided_on: 2026-07-19
relaylm_volatility: low
relaylm_owner: architecture
relaylm_update_trigger:
  - interactive Main LLM timing changes
  - RelayCTX session-continuity ownership changes
  - RelaySLP formation timing changes
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
  - ../architecture/runtime_dataflow_modes.md
  - ../architecture/relayref_output_observation_design.md
  - ../architecture/relayrun_resource_scheduling_design.md
  - ../architecture/subjective_mem_deferred_formation_design.md
---
# ADR 0004: Single-call interactive runtime and deferred subjective formation

## Status

Accepted as target architecture on 2026-07-19. Implementation remains separately governed by the Project Execution Plan and Project Status.

## Context

RelayLM runs primarily on local 7B–13B-class models and a single latency-sensitive GPU. The interactive path must preserve conversational tempo, TTS continuity, and predictable fallback behavior. Subjective memory formation, by contrast, benefits from reading several turns together after corrections, qualifications, and topic boundaries become visible.

Treating Shared Assessment and Subjective MEM formation as mandatory second and third Main LLM calls inside every interactive turn would:

- compete with the current response and TTS for the same backend;
- make the next user turn wait for memory work that is not required to answer it;
- form fragmented per-turn memories before natural clarification arrives;
- encourage longer user-facing replies merely to hide internal latency;
- blur RelayCTX continuity, RelayREF observation, and RelaySLP compilation ownership.

The architecture already separates RelayINT before action, RelayREF after response, and RelaySLP after the current user-visible answer. This ADR fixes the timing and ownership consequences of that separation.

## Decision

### 1. One Main LLM call on the ordinary interactive critical path

A normal managed conversation turn uses one response-generation call:

```text
User input
  -> governed source capture
  -> RelayRUN request shell
  -> RelayREL
  -> input-side RelaySCN
  -> input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval, when allowed
  -> RelayCTX Repack
  -> Main LLM response generation
  -> RelayCTX Unpack
  -> RelayREF
  -> return-side RelayEMO
  -> output-side RelaySCN
  -> user / TTS / avatar output
```

The Main LLM owns response generation only. It does not commit MEM, scene, affect, relationship, SOUL, or persistence state. A bounded internal candidate may accompany the response, but owning components validate and apply only their own fields.

Clarification, block, pass-through, and recovery modes may avoid the Main LLM or use a governed fallback. They do not create a general requirement for an additional memory-formation call inside the turn.

### 2. Governed evidence persists independently of response and memory formation

Source occurrence, evidence admission, turn admission, response success, CTX continuity, and durable memory formation remain orthogonal.

```text
Source occurrence
  -> governed SourceEvent / Protected Source Evidence

Admitted turn
  -> interactive response path

Protected Source Evidence
  -> deferred RelaySLP formation path
```

RelayATN rejection, Main LLM failure, SLP deferral, or SLP failure must not erase admitted governed evidence.

### 3. RelayCTX owns immediate and session-local continuity

During an active conversation, RelayCTX owns the bounded working state needed to continue naturally:

- current topic and task;
- active question and unresolved slots;
- prior decisions and referable items;
- selected recent continuity;
- session-local correction overlays;
- session-local recall suppression.

A current correction or qualification is placed later than retrieved durable MEM in the packed context. RelayCTX may therefore suppress an old formulation or prefer newer current evidence without mutating durable MEM.

RelayCTX is not a pending-MEM authority. Governed Evidence, not CTX alone, is the durable source for later formation.

### 4. RelaySLP forms memory out of band and preferably by episode

RelaySLP runs after the user-visible response, normally when one of these conditions occurs:

- the session becomes idle;
- the scene or topic crosses a meaningful boundary;
- the session closes;
- enough governed evidence accumulates;
- an explicit remember intent raises priority;
- an operator or scheduler invokes SLP;
- the backend has sufficient resource budget.

RelaySLP may read multiple related SourceEvents together. It produces or updates:

```text
Protected Source Evidence
  -> character-independent Shared Assessment
  -> SOUL-conditioned Subjective MEM proposal
  -> deterministic validation and policy gates
  -> RelayMEM / workspace commit or hold
```

For the initial target, one structured SLP call may emit both a Shared Assessment section and a Subjective MEM proposal section. The logical authority boundary remains intact:

- Protected Source Evidence and Shared Assessment remain independent of SOUL;
- only subjective meaning, salience, interpretation, and relation choice may be conditioned by an identified SOUL revision;
- `MEMORY.md`, `BOUNDARY.md`, RelayREL, and RelaySCN constrain formation and persistence without rewriting evidence support.

### 5. Additional LLM adjudication is an SLP exception, not an interactive call

Difficult cases may be held for later adjudication, including:

- material contradiction;
- uncertain participant or relationship identity;
- private/group scope conflict;
- a possible correction or supersession with unclear target;
- several plausible existing MEM relations.

The default response is `hold`, `abstain`, or evidence-only. A later SLP adjudication call is optional and must not block the conversation.

### 6. RelayREF is a low-authority post-generation observer

RelayREF observes what the generated response actually did after RelayCTX Unpack. It may report bounded observations such as:

- speech-act class;
- answer or clarification completion candidate;
- repair or apology attempt;
- assistant inference presence;
- topic or task-boundary candidate;
- unresolved-reference presence.

RelayREF does not rewrite the response, replace RelayINT, classify the authoritative scene, infer durable affect facts, or form MEM. RelayCTX, RelayEMO, RelaySCN, and RelaySLP consume only the observations relevant to their own authority.

### 7. RelayRUN owns job timing; a Resource Provider reports hardware facts

A runtime Resource Provider reports backend and hardware observations such as active generation, queue depth, resource pressure, recent latency, cancellation capability, and backend health.

RelayRUN owns:

- priority and admission;
- run now, defer, busy-skip, cancel, retry, or coalesce;
- node and job lifecycle;
- idempotency and duplicate prevention;
- fallback and recovery orchestration.

RelayRUN remains semantic-neutral. The owning component defines the semantic fallback for a skipped or deferred job.

Default priority direction:

```text
interactive response and voice-out
  > explicit governed user mutation
  > mandatory lightweight output processing
  > Primary Subjective MEM formation
  > Secondary consolidation
  > embedding, cache maintenance, and evaluation
```

A separate host-level supervisor is not required for the initial single-backend, single-GPU deployment. It becomes relevant only when several RelayRUN instances or several GPU-consuming subsystems require shared host allocation.

### 8. Conversational forgetting is not durable deletion

Natural-language requests such as “do not bring that up again in this conversation” or “forget what I just said” default to RelayINT/RelayCTX session-local suppression when the scope is conversational.

Durable Forget or canonical memory modification occurs only through a governed management path, such as:

- the Character Workspace / SOUL Lab Forget operation;
- direct human editing of canonical Markdown memory pages;
- a future explicit management command with equivalent authority.

After a durable canonical mutation, stale cache projections must fail closed and must not remain retrieval-visible.

## Mode consequences

### Managed text conversation

One Main LLM response call. Evidence capture and CTX continuity are synchronous; SLP is deferred.

### Voice / TTS conversation

Voice-out remains higher priority than SLP. RelayLM does not lengthen the answer merely to hide formation latency.

### Immediate correction

RelayCTX prefers the newest current evidence and may apply a session overlay. RelaySLP later reconciles durable MEM.

### High load

Evidence capture and the interactive answer remain available. Optional probes and SLP work defer or busy-skip according to RelayRUN policy.

### Session transition

RelayCTX is not persisted wholesale. A bounded continuity handoff may retain evidence references or explicitly typed assistant/system-origin provisional continuity. It is not automatically a new user-evidence fact.

### Continuous input

RelayATN may reject, hold, or select a turn before RelayRUN exists. Evidence admission remains separate, and RelayATN never writes RelayCTX or durable MEM.

## Consequences

### Positive

- Conversational latency is not coupled to memory-formation completion.
- Several turns can form one coherent episodic memory instead of fragmented per-turn records.
- Current corrections naturally outrank old retrieval inside the active conversation.
- The architecture remains usable on one local GPU with TTS.
- RelayRUN resource control remains separate from semantic meaning.
- The three-layer evidence/assessment/subjective-memory model remains intact without requiring three synchronous calls.

### Costs

- Newly discussed content may not become durable MEM before the next turn or next session.
- Pending evidence and formation jobs require durable queue and catch-up behavior.
- Session overlays and continuity handoffs require bounded owning contracts.
- SLP must support coalescing or re-evaluating pending work when later evidence arrives.

## Rejected alternatives

### Run response, Shared Assessment, and Subjective MEM synchronously every turn

Rejected because the latter two operations are not required for the current answer and create unacceptable coupling to local-backend latency.

### Extend user-facing responses to create hidden SLP time

Rejected because it increases cognitive load, occupies the backend longer, and distorts character behavior for an internal scheduling concern.

### Treat RelayCTX as the durable pending-memory store

Rejected because RelayCTX is bounded, rebuildable working state. Governed Evidence and the durable SLP queue own persistence before MEM formation.

### Let RelayRUN decide semantic fallback

Rejected because RelayRUN owns timing and execution, while each semantic component owns the meaning of its degraded result.

### Interpret every natural-language “forget” as durable deletion

Rejected because conversational suppression and governed canonical mutation have different scope, reversibility, and error cost.

## Fixed boundaries

- The ordinary interactive critical path uses one Main LLM response-generation call.
- Evidence capture is independent of turn admission, response success, and SLP completion.
- RelayCTX owns immediate/session continuity, not durable MEM.
- RelaySLP forms Subjective MEM out of band, preferably across an episode or bounded evidence group.
- Shared Assessment remains character-independent even when generated in the same structured SLP call as a Subjective MEM proposal.
- RelayREF observes output and does not rewrite or persist semantic state.
- RelayRUN schedules work but does not decide semantic meaning.
- Conversational suppression is not durable Forget.
- Durable canonical mutation invalidates stale retrieval projections before ordinary retrieval may continue.
