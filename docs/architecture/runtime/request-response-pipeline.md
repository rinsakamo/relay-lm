---
relaylm_doc_type: system_architecture
relaylm_authority: managed_request_response_pipeline_modes_and_response_finalization
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: runtime
relaylm_update_trigger:
  - canonical request or response stage order changes
  - streaming or response-finalization ownership changes
  - RelayREF consumer boundary changes
  - pass-through or session-continuity mode changes
relaylm_not_authoritative_for:
  - exact stage schemas or wire envelopes
  - exact SourceEvent or Evidence Admission contracts
  - exact RelayCTX working-state schema
  - exact scheduler priority values
  - exact Subjective MEM formation schema
  - current implementation status or sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0004-single-response-call-ordinary-conversation-deferred-formation.md
relaylm_related_authority:
  - ../pipeline_responsibility_design.md
  - ../context_packing_design.md
  - ../relayscn_mvp_scene_policy.md
  - ../../relayemo_mvp_initial_design.md
  - ../relayint_mvp_design.md
  - ../relayatn_reflex_layer_design.md
  - scheduler.md
  - ../memory/formation.md
---
# RelayLM Request / Response Pipeline

## Authority summary

This document is authoritative for target request/response timing, mode-specific handoffs, streaming versus response-complete finalization, and the RelayREF observation boundary. Component ownership remains defined by Pipeline Responsibility Design; exact artifacts and gates belong in contracts.

## System context

RelayLM uses four non-competing lanes:

```text
durable character authority
  SOUL / MEMORY / BOUNDARY / STYLE / EMOTION / SCENE
  RELATIONSHIP / relationships/<target> / optional LORE

governed evidence
  source occurrence -> SourceEvent -> Evidence Admission
  -> Protected Source Evidence

interactive runtime
  RUN -> REL -> SCN -> EMO -> INT -> MEM Retrieval
  -> CTX -> Main LLM -> streaming/output pipeline

deferred formation
  governed evidence -> RelaySLP assessment
  -> Shared Assessment -> subjective formation
  -> governed persistence
```

The lanes share opaque identities and revision references. They do not share write authority.

## Common timing rules

1. The ordinary managed no-tool conversational path requires one Main LLM response-generation call.
2. Optional analyzer probes and tool transactions are separately governed and are not counted as mandatory response-generation calls.
3. Protected Source Evidence is durable independently of response and SLP success.
4. RelayMEM Retrieval is read-only in the interactive path.
5. RelayCTX owns bounded current/session working state and prompt layout, not durable memory.
6. Streaming chunk emission and response-complete finalization are separate paths.
7. RelayREF observes finalized generated output and does not delay the first visible token.
8. Output-side observations do not retroactively change same-turn input-side SCN, EMO, INT, Retrieval, or packing.
9. RelaySLP runs outside the current user-visible answer and preferably groups related evidence by episode.
10. Default trace and checkpoint surfaces remain content-free.

Mode-specific artifacts should distinguish at least:

```text
observed_in_turn
produced_after_response
effective_from_turn
expires_after_turn_or_session
source_revision_refs
```

## Mode 1: Managed text conversation

### Request path

```text
current user input
  -> governed user-origin SourceEvent capture
  -> RelayRUN request shell / PipelineContext
  -> RelayREL target relationship selection
  -> input-side RelaySCN state and policy
  -> input-side RelayEMO bounded affect/expression pressure
  -> RelayINT intent, reference, and retrieval decision
  -> RelayMEM Retrieval when allowed
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> Main LLM response generation
```

### Context order

Stable approved sources precede dynamic evidence. Newer current evidence follows retrieved durable MEM:

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
minimum compatible tool/multimodal transaction state
latest input
response instruction
```

This is an input-control rule. It makes explicit current evidence more salient but does not guarantee probabilistic model output.

### Streaming and response-complete branches

```text
Main LLM stream
  |- chunk branch
  |    -> incremental RelayCTX Unpack / safety boundary
  |    -> user-visible chunk
  |    -> TTS / avatar adapter when enabled
  |    -> RelayRUN chunk and adapter idempotency
  |
  `- response-complete branch
       -> finalized assistant-origin Evidence
       -> RelayCTX final Unpack validation
       -> RelayREF response observation
       -> owning CTX / EMO / SCN consumers
       -> RelayRUN end-of-turn finalization
       -> durable SLP coverage / enqueue reference
```

Already emitted text is never replaced or replayed after the first visible token.

## Assistant-origin Evidence versus RelayREF observation

A finalized assistant response and a RelayREF observation are distinct.

```text
assistant-origin Evidence
  exact protected response content or protected reference
  speaker/producer provenance
  complete / truncated / cancelled / transport-failed status
  emitted-range information when partial

RelayREF observation
  bounded low-authority statement about response behavior
```

The Evidence authority owns admission, retention, and lineage. RelayREF does not create a user-origin fact and does not become the response-content authority.

## RelayREF output observation

RelayREF answers:

> What can be safely observed about the generated response after that response exists?

### Inputs

RelayREF may consume:

- safe finalized output or an opaque protected response reference;
- detached bounded structured candidates after Unpack validation;
- run, turn, and response identity;
- bounded generation metadata;
- opaque references to current INT, SCN, EMO, and Evidence artifacts when comparison is needed.

RelayREF should not require the full prompt, all SOUL text, all retrieved MEM, or full client history.

### Output classes

A bounded response observation may include:

- speech act;
- answer-completion candidate;
- clarification-requested candidate;
- repair or apology attempt;
- user-claim-repeated candidate;
- assistant-inference-present candidate;
- unsupported-assertion candidate;
- topic-shift or task-boundary candidate;
- unresolved-reference presence;
- complete, truncated, cancelled, or transport-failed class.

These are observations, not authority transfers.

### Consumer boundaries

```text
RelayCTX
  validates whether its own working-state candidate should change

Return/output RelayEMO
  owns any resulting display, TTS, or avatar expression hint

Output-side RelaySCN
  owns next-turn scene, recovery, and persistence observations

RelaySLP
  distinguishes assistant response/reaction from user-origin claims

Audit
  receives only content-free allowlisted projection
```

RelayREF does not mutate consumer state directly.

### Implementation order

RelayREF should prefer the lowest-cost sufficient method:

```text
1. validated bounded candidate emitted with the Main LLM output
2. deterministic parser and transport metadata
3. bounded heuristic
4. optional structured probe only when resource policy permits
```

An ordinary RelayREF observation must not require another Main LLM response-generation call. An optional probe is busy-skippable or deferred and cannot delay visible output.

### Failure behavior

```text
candidate missing or invalid
  -> safe partial observation or observation_unavailable

optional probe busy or timeout
  -> no response delay

RelayREF failure
  -> RelayRUN records content-free failure
  -> consumers use safe defaults
  -> no MEM, SCN, EMO, REL, or SOUL mutation
```

## Mode 2: Voice / TTS / avatar conversation

The semantic request path is the same as managed text conversation. Adapters perform ASR, TTS, display, and avatar execution; RelayEMO emits engine-neutral expression hints only.

```text
ASR result -> managed request path
visible chunks -> adapter execution
response complete -> REF / output observations / finalization
```

Voice-out outranks deferred SLP when both share a constrained resource. RelayLM does not lengthen responses merely to create hidden formation time.

## Mode 3: Clarification, block, and short-circuit

RelayINT may prevent normal Main LLM execution when an action cannot safely proceed.

```text
REL -> SCN -> EMO -> INT
                    |- continue -> Retrieval -> CTX -> Main LLM
                    |- clarification -> bounded clarification path
                    `- block -> governed safe response or protocol error
```

A short-circuit does not erase admitted evidence or authorize a memory write. User-visible output still passes the normal output and RUN accounting boundary.

## Mode 4: Current-conversation correction

```text
new correction SourceEvent
  -> RelayINT correction/reference candidate
  -> RelayCTX recent context and optional session overlay
  -> newer evidence packed after older retrieved MEM
```

A session overlay may request:

```text
prefer newer current evidence
do not intentionally privilege the older formulation
suppress a resolved matched MEM from active-session packing
```

The overlay is a best-effort prompt-selection mechanism. It does not guarantee model output and does not change canonical MEM lifecycle. RelaySLP later reconciles durable memory.

## Mode 5: Conversational recall suppression

Natural-language requests such as “do not bring that up again in this conversation” default to session-local behavior when a durable management operation was not invoked.

```text
RelayINT suppression intent
  -> RelayCTX session recall suppression
  -> RelaySCN topic transition when appropriate
```

The effect is limited to current prompt selection and conversational behavior. It does not delete Protected Source Evidence or canonical Markdown MEM.

## Mode 6: Session close and new-session catch-up

RelayCTX working state is not persisted wholesale. An owning path may emit a bounded continuity handoff containing evidence references and typed state classes.

```text
CTX unresolved or active continuity
  -> continuity handoff candidate
  -> durable supporting SourceEvent references where available
```

A CTX inference does not become user-origin fact because it crossed a session boundary. Unsupported continuity remains assistant/system-origin and provisional.

A new session may use canonical Subjective MEM retrieval plus bounded pending continuity and limited recent unformed evidence references when an exact owning contract allows it. It must not inject all pending source content as durable MEM.

## Mode 7: Continuous input and RelayATN

RelayATN exists before a normal RelayRUN request shell in continuous-input environments.

```text
source occurrence
  |- governed Evidence Admission
  `- RelayATN reject / hold / select / content-free flag
                    `- admitted -> RelayRUN managed path
```

RelayATN never writes RelayCTX, scene, relationship, or durable memory state. Turn rejection does not imply evidence rejection.

## Mode 8: Durable Forget or direct Markdown editing

Durable management mutations are not ordinary conversational suppression.

```text
explicit management action
  -> RelayMEM lifecycle mutation fence
  -> canonical revision
  -> old projection retrieval-ineligible
  -> rebuild or fail-closed state
```

```text
human Markdown edit
  -> schema/revision validation
  -> conflict check against pending SLP write
  -> canonical commit
  -> cache invalidation / rebuild
```

Already emitted output cannot be withdrawn, but the mutation fence may immediately prevent future retrieval, packing, and uncommitted writes from using the old revision.

Evidence purge remains a separate evidence-governance operation.

## Mode 9: Stream failure and recovery

```text
before stream opens
  -> safe fallback, governed error, or normal recovery

after stream opens but before first token
  -> recovery constrained by transport capability

after first visible token
  -> no replacement or replay of emitted text
  -> partial assistant-origin Evidence records emitted status/range
  -> response-complete or failure finalization proceeds once
```

SLP failure never invalidates already delivered output.

## Mode 10: Explicit pass-through

Pass-through delegates backend context authority to the client.

Default pass-through behavior:

```text
client request -> protocol adapter -> backend
```

It does not silently add managed retrieval, managed CTX replacement, automatic memory Evidence capture, RelayREF semantic observation, SLP enqueue, or character-memory mutation. Minimum transport and RUN accounting may remain when required by the adapter contract.

A route may enable Evidence capture, RelayREF, or deferred formation only through a separate explicit opt-in contract. Such opt-in remains isolated from managed-route assumptions.

## Ownership matrix

| Artifact or decision | Owner | Important non-owners |
|---|---|---|
| SourceEvent, admission, retention, correction lineage | Evidence authority | ATN, CTX, REF, SLP, MEM |
| Turn admission | RelayATN | Evidence authority, RUN, INT |
| Run/turn and stream status, timeout, retry | RelayRUN | SCN, EMO, SLP |
| Relationship policy | RelayREL | SCN, CTX, MEM |
| Scene and persistence/disclosure policy | RelaySCN | EMO, CTX, REF |
| Affect estimate and expression state | RelayEMO | SCN, MEM, REF |
| Intent and pre-action ambiguity | RelayINT | REF, MEM, RUN |
| Approved durable memory retrieval | RelayMEM Retrieval | CTX, Main LLM |
| Context selection, session overlay, packing | RelayCTX | SCN, EMO, MEM |
| Generated response content | Main LLM through normal output pipeline | RUN, REF, SLP |
| Finalized assistant-origin Evidence | Evidence authority | REF, CTX, SLP |
| Post-generation response observation | RelayREF | INT, SCN, MEM |
| Canonical Subjective MEM lifecycle | RelayMEM / canonical workspace commit | SLP proposal, cache projection |

## Fixed invariants

- No response-path stage writes durable MEM.
- No CTX field becomes durable evidence merely by remaining in working state.
- No REF observation becomes a user claim or response-content authority.
- No EMO estimate becomes durable user affect fact.
- No output-side artifact is applied retroactively to the same response.
- No current correction is represented as a guaranteed model-output result.
- No conversational suppression is represented as durable deletion.
- No stale cache revision remains ordinary-retrieval eligible after canonical mutation.
- No pass-through route gains managed memory behavior without explicit opt-in authority.
