---
relaylm_doc_type: stable_architecture
relaylm_authority: runtime_mode_data_flow_and_timing
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - canonical runtime mode changes
  - interactive versus deferred timing changes
  - component handoff order changes
  - session continuity or durable mutation entry points change
relaylm_not_authoritative_for:
  - component responsibility outside mode-specific timing and handoff
  - exact SourceEvent, CTX, REF, SLP, MEM, or RUN schemas
  - current implementation status
  - implementation sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0004-single-call-interactive-runtime-deferred-formation.md
  - pipeline_responsibility_design.md
  - context_packing_design.md
  - memory_lifecycle_design.md
  - relayref_output_observation_design.md
  - relayrun_resource_scheduling_design.md
  - subjective_mem_deferred_formation_design.md
  - relayatn_reflex_layer_design.md
---
# RelayLM Runtime Dataflow Modes

## Purpose

This document defines the target mode-specific timing and dataflow of RelayLM while preserving the component ownership in [Pipeline Responsibility Design](pipeline_responsibility_design.md).

The stable architecture uses four non-competing lanes:

```text
Durable character authority
  SOUL / MEMORY / BOUNDARY / STYLE / EMOTION / SCENE
  RELATIONSHIP / relationships/<target> / optional LORE

Governed evidence
  Source occurrence -> SourceEvent -> Evidence Admission
  -> Protected Source Evidence

Interactive runtime
  RUN -> REL -> SCN -> EMO -> INT -> MEM Retrieval
  -> CTX -> Main LLM -> Unpack -> REF -> return EMO -> output SCN

Deferred formation
  governed evidence -> SLP -> Shared Assessment
  -> Subjective MEM / SCENE / REL candidates and source proposals
  -> governed persistence
```

The lanes share opaque references, turn identity, and revision identity. They do not share write authority.

## Common ownership and timing rules

1. The ordinary interactive path uses one Main LLM response call.
2. Protected Source Evidence is durable independently of response or SLP success.
3. RelayMEM Retrieval is read-only in the interactive path.
4. RelayCTX owns bounded current/session working state and prompt layout, not durable memory.
5. RelayREF observes the generated response only after RelayCTX Unpack.
6. Output-side observations do not retroactively change same-turn input-side SCN, EMO, INT, Retrieval, or packing.
7. RelaySLP runs after the current user-visible answer and preferably groups related evidence by episode.
8. RelayRUN owns execution timing and resource admission, not semantic meaning.
9. Default trace and checkpoint surfaces remain content-free.

## Artifact timing vocabulary

Mode-specific artifacts should distinguish at least:

```text
observed_in_turn
produced_after_response
effective_from_turn
expires_after_turn_or_session
source_revision_refs
```

A post-response scene transition or expression observation must not be represented as if it had conditioned the response that produced it.

## Mode 1: Managed text conversation

### Flow

```text
Current user input
  -> governed source capture
  -> RelayRUN request shell / PipelineContext
  -> RelayREL target relationship selection
  -> input-side RelaySCN state and policy
  -> input-side RelayEMO bounded affect/expression pressure
  -> RelayINT intent, reference, and retrieval decision
  -> RelayMEM Retrieval when allowed
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM response call
  -> RelayCTX Unpack
  -> RelayREF response observation
  -> return-side RelayEMO hints
  -> output-side RelaySCN next-turn observation
  -> RelayRUN finalization
  -> user output
```

### Packing order

Stable approved character and boundary sources remain before dynamic state. Newer current conversation evidence remains after retrieved durable memory:

```text
runtime policy
SOUL / STYLE / BOUNDARY / EMOTION profiles / optional LORE
RelayREL policy and selected relationship instance
MEMORY policy or stable memory summary
RelaySCN state/policy
RelayEMO expression hint
RelayINT hint
retrieved Subjective MEM
selected RelayLM-owned recent context and session overlays
latest input
response instruction
```

This order allows a current correction to outrank an older retrieved formulation without mutating durable MEM during the response path.

### After-turn handoff

The response path emits opaque references and bounded observations for later SLP. It does not wait for Shared Assessment or Subjective MEM formation.

## Mode 2: Voice / TTS / avatar conversation

The semantic flow is identical to managed text conversation. Adapters perform ASR, TTS, display, or avatar execution; RelayEMO emits engine-neutral expression hints only.

```text
ASR result -> normal managed input path
safe visible response -> return-side EMO hints -> TTS/avatar adapter
```

Priority direction:

```text
interactive response and voice-out > deferred SLP
```

RelayLM does not lengthen a response merely to create hidden time for memory formation. If TTS uses another resource and the Main LLM backend becomes idle, RelayRUN may admit deferred SLP opportunistically.

## Mode 3: Clarification, block, or short-circuit

RelayINT may prevent normal Main LLM execution when the current action cannot safely proceed.

```text
REL -> SCN -> EMO -> INT
                    |- continue -> Retrieval -> CTX -> Main LLM
                    |- clarification -> bounded clarification path
                    `- block -> governed safe response or protocol error
```

A short-circuit does not erase admitted evidence and does not authorize a memory write. The output still passes the normal visible-output and RUN accounting boundary when user-visible text is emitted.

## Mode 4: Current-conversation correction

Example:

```text
“Earlier I said tea, but more precisely it was herbal tea.”
```

### Immediate path

```text
new correction SourceEvent
  -> RelayINT correction/reference candidate
  -> RelayCTX recent context and optional session overlay
  -> Main LLM receives newer current evidence after older retrieved MEM
```

A session overlay may express only a temporary packing instruction such as:

```text
prefer newer current evidence
do not assert the old form
suppress this retrieved item for the active session
```

It does not change the canonical MEM lifecycle.

### Deferred path

RelaySLP later reads the correction and related evidence together and decides whether the durable result is no change, reinforcement, refinement, a held correction candidate, or another governed relation outcome.

## Mode 5: Conversational recall suppression

Natural-language requests such as “do not bring that up again in this conversation” default to a session-local interpretation when durable deletion was not explicitly invoked through a management surface.

```text
RelayINT suppression intent
  -> RelayCTX session recall suppression
  -> RelaySCN topic transition when appropriate
```

The effect is limited to current prompt selection and conversational behavior. It does not delete Protected Source Evidence or canonical Markdown MEM.

## Mode 6: Idle or episode-boundary RelaySLP

### Trigger classes

- idle interval;
- topic or scene boundary;
- session close;
- bounded evidence-count threshold;
- explicit remember intent;
- manual or scheduled invocation;
- available backend resource budget.

### Formation flow

```text
related governed Evidence refs
+ validated REF / SCN / REL / bounded EMO observations
+ CTX episode-boundary or continuity refs
+ existing Subjective MEM candidates
+ identified SOUL / MEMORY / BOUNDARY / relationship revisions
  -> RelaySLP
     -> character-independent Shared Assessment
     -> SOUL-conditioned Subjective MEM proposal
     -> deterministic validation and policy gates
     -> commit, hold, abstain, or evidence-only
```

An initial implementation may produce the Shared Assessment section and Subjective MEM proposal section in one structured SLP call. The fields and validators must preserve their authority boundary.

Difficult relation or correction cases default to hold. Additional SLP adjudication is optional and never blocks the interactive response.

## Mode 7: High load or busy-skip

A Runtime Resource Provider reports hardware/backend facts. RelayRUN compares those facts with job requirements and chooses execution timing.

```text
Resource Provider snapshot
  -> RelayRUN admission / scheduling
     |- run now
     |- defer
     |- busy-skip
     |- cancel and retry
     |- coalesce
     `- block or fallback
```

Semantic fallback remains owned by the affected component:

```text
EMO structured probe skipped -> EMO heuristic or neutral result
SCN optional classifier skipped -> SCN safe default or bounded heuristic
SLP deferred -> evidence-only / pending formation
Secondary consolidation skipped -> existing canonical MEM remains unchanged
```

Evidence capture and interactive response remain higher priority than deferred formation.

## Mode 8: Session close and new-session catch-up

RelayCTX working state is not persisted wholesale. At session close, an owning path may emit a bounded continuity handoff containing references and state classes needed for safe continuation.

```text
CTX unresolved or active continuity
  -> continuity handoff candidate
  -> durable reference to supporting SourceEvents where available
```

A CTX inference does not become a user-origin fact merely because it crossed a session boundary. When no explicit user evidence supports the handoff, it remains typed as assistant/system-origin provisional continuity.

A new session may use:

```text
canonical Subjective MEM retrieval
+ bounded pending continuity
+ limited recent unformed evidence references when the owning contract permits
```

It must not inject all pending source content as if it were durable MEM.

## Mode 9: Continuous input and RelayATN

RelayATN exists before a normal RelayRUN request shell in continuous-input environments.

```text
Source occurrence
  |- governed evidence-admission path
  `- RelayATN reject / hold / select / content-free flag
                    `- admitted -> RelayRUN interactive path
```

RelayATN never writes RelayCTX, scene, relationship, or durable memory state. Turn rejection does not imply evidence rejection.

## Mode 10: Durable Forget or direct Markdown editing

### Governed UI Forget

```text
explicit management action
  -> RelayMEM lifecycle operation
  -> canonical Markdown revision
  -> stale cache projection becomes retrieval-ineligible
  -> new projection or fail-closed rebuild state
```

### Direct Markdown edit

```text
human edit
  -> schema and revision validation
  -> conflict check against pending SLP write
  -> canonical revision commit
  -> cache invalidation / rebuild
```

SLP and human edits must not silently overwrite each other. Conflict produces hold, rebase, or explicit resolution.

Evidence purge remains a separate evidence-governance operation and is not implied by MEM Forget.

## Mode 11: Stream failure and recovery

### Before backend stream opens

RelayRUN may choose safe fallback, governed error, or normal output-pipeline recovery.

### After stream opens but before first token

Recovery is constrained by transport capabilities.

### After first user-visible token

RelayRUN must not replace or replay already emitted text. Per-chunk and end-of-turn idempotency prevent duplicate TTS or avatar output.

SLP failure never invalidates an already valid visible response.

## Mode 12: Explicit pass-through

A route explicitly configured as pass-through delegates message-history and backend-context authority to the client according to the pass-through contract.

```text
client request -> protocol adapter -> backend
```

Managed-route context reconstruction, character packing, governed retrieval, and CTX replacement are not silently added to a pass-through route.

## Ownership matrix

| Artifact or decision | Owner | Important non-owners |
|---|---|---|
| SourceEvent, admission, retention, correction lineage | Evidence authority | ATN, CTX, SLP, MEM |
| Turn admission | RelayATN | Evidence authority, RUN, INT |
| Run/turn status, timeout, retry, priority | RelayRUN | SCN, EMO, SLP |
| Relationship policy | RelayREL | SCN, CTX, MEM |
| Scene and persistence/disclosure policy | RelaySCN | EMO, CTX, REF |
| Affect estimate and expression state | RelayEMO | SCN, MEM, REF |
| Intent and pre-action ambiguity | RelayINT | REF, MEM, RUN |
| Approved durable memory retrieval | RelayMEM Retrieval | CTX, Main LLM |
| Context selection, session overlay, packing | RelayCTX | SCN, EMO, MEM |
| Visible response | Main LLM through normal output pipeline | RUN, REF, SLP |
| Post-generation response observation | RelayREF | INT, SCN, MEM |
| Shared Assessment production | RelaySLP assessment stage | SOUL, CTX, Main LLM |
| Subjective MEM candidate | RelaySLP formation stage | CTX, REF, RUN |
| Canonical Subjective MEM lifecycle | RelayMEM / canonical workspace commit | SLP proposal, SQLite cache |
| Resource facts | Runtime Resource Provider | RUN semantic policy |
| Resource admission and scheduling | RelayRUN | Resource Provider, semantic components |

## Fixed consistency checks

- No response-path stage writes durable MEM.
- No CTX field becomes durable evidence merely by being retained in working state.
- No REF observation becomes a user claim.
- No EMO estimate becomes durable user affect fact.
- No output-side artifact is applied retroactively to the same response.
- No RUN resource decision invents semantic meaning.
- No conversational suppression is represented as durable deletion.
- No stale cache revision remains ordinary-retrieval eligible after canonical mutation.
