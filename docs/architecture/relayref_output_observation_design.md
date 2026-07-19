---
relaylm_doc_type: stable_architecture
relaylm_authority: relayref_output_observation_boundary
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayREF input or output ownership changes
  - post-generation observation consumers change
  - RelayCTX Unpack and RelayREF separation changes
  - RelayREF gains or loses an LLM-backed probe
relaylm_not_authoritative_for:
  - exact RelayREF wire schema
  - current RelayREF implementation status
  - RelayINT pre-action semantics
  - RelaySCN, RelayEMO, RelayCTX, or RelaySLP owned state
  - implementation sequencing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../adr/0004-single-call-interactive-runtime-deferred-formation.md
  - pipeline_responsibility_design.md
  - runtime_dataflow_modes.md
  - context_packing_design.md
  - relayscn_mvp_scene_policy.md
  - relayemo_mvp_initial_design.md
  - relaymem_slp_execution_design.md
---
# RelayREF Output Observation Design

## Purpose

RelayREF is RelayLM's low-authority post-generation observer. It answers:

> What can be safely observed about the response after the response exists?

RelayREF does not decide what the user requested, generate the answer, rewrite the answer, or persist memory. It allows output-side components and deferred RelaySLP to distinguish the Main LLM's actual response behavior from user-origin evidence.

## Timing boundary

```text
RelayINT
  before action: intent, references, ambiguity, proceed/block/clarify

Main LLM
  response generation

RelayCTX Unpack
  syntactic separation of visible text and internal candidates

RelayREF
  after response: bounded semantic observation

Return-side RelayEMO / Output-side RelaySCN / RelayCTX / RelaySLP
  consume only their owned subset
```

RelayREF output never retroactively changes same-turn input-side SCN, EMO, INT, Retrieval, or RelayCTX packing.

## Input boundary

RelayREF may receive:

- the safe visible response after RelayCTX Unpack;
- detached bounded internal observation candidates;
- `run_id`, `turn_id`, and `response_id`;
- opaque references to current INT, SCN, EMO, and Evidence artifacts when needed for comparison;
- bounded generation metadata such as completion or truncation class.

RelayREF should not require the complete prompt, all SOUL text, all retrieved MEM, or the full client history for ordinary observation.

## Output boundary

RelayREF emits a bounded runtime-private response observation. Candidate observation classes include:

- speech act: answer, question, acknowledgement, correction, apology, refusal, or other;
- answer-completion candidate;
- clarification-requested candidate;
- repair-attempted candidate;
- user-claim-repeated candidate;
- assistant-inference-present candidate;
- unsupported-assertion candidate;
- topic-shift candidate;
- task-boundary candidate;
- unresolved-reference presence;
- response truncation or incomplete-output class.

These are observations, not authority transfers.

Example target shape:

```yaml
relayref_response_observation:
  schema_version: relayref.response_observation.v0
  turn_id: turn-123
  response_id: response-123
  speech_act: answer
  answer_completion_candidate: true
  clarification_requested: false
  repair_attempted: false
  user_claim_repeated: false
  assistant_inference_present: true
  unsupported_assertion_candidate: false
  topic_shift_candidate: false
  task_boundary_candidate: false
  unresolved_reference_present: false
  observation_source: structured_candidate
  confidence_band: medium
```

Exact field names and validation rules belong to a dedicated contract.

## Why RelayREF exists

### Separate user claims from assistant inference

Example:

```text
User: “I have been a little tired lately.”
Assistant: “Work must have been busy.”
```

The user's self-report and the assistant's inference are different artifacts:

```text
Protected Source Evidence
  user reported recent tiredness

RelayREF observation
  assistant inference about work busyness appeared in the response
```

RelaySLP may use the latter as evidence about the character's own reaction or as a warning not to promote the inference into grounded user content. RelayREF never upgrades it to a user fact.

### Observe what actually happened, not only what was intended

RelayINT may decide that an answer is needed. RelayREF may later observe that the generated response instead asked a clarification question, attempted a repair, or ended incomplete. This allows next-turn state to follow the emitted response without pretending the input plan was executed perfectly.

### Provide bounded output-side handoffs

RelayREF is the single post-generation observation source for the owning consumers. This prevents RelayCTX, RelayEMO, RelaySCN, and RelaySLP from separately reparsing the visible response into competing interpretations.

## Consumer boundaries

### RelayCTX

RelayCTX may use a RelayREF observation to decide whether its own working-state candidate should be accepted, for example:

- an active question was answered;
- a clarification is now pending;
- an expected next action was stated;
- an unresolved reference remains.

RelayREF does not mutate RelayCTX directly. RelayCTX validates and writes only its own working-state schema.

### Return-side RelayEMO

RelayEMO may use response-act and repair/apology observations to produce bounded display, TTS, or avatar expression hints. RelayEMO owns the resulting expression state and remains unable to rewrite response meaning or persist durable user-affect facts.

### Output-side RelaySCN

RelaySCN may use topic-shift, task-boundary, recovery, or clarification observations to decide next-turn scene transitions and persistence/recovery observations. RelaySCN remains the authoritative scene owner.

### RelaySLP

RelaySLP may use RelayREF observations to:

- distinguish user-origin claims from assistant inference;
- identify what the character noticed or responded to;
- identify a response-complete episode boundary;
- avoid forming memory from a truncated or malformed response;
- retain bounded non-authoritative reaction evidence.

RelayREF does not create Shared Assessment, Subjective MEM, relation decisions, or persistence actions.

### Audit and diagnostics

Default audit receives a content-free projection only, such as:

```yaml
relayref_projection:
  schema_version: relayref.projection.v0
  observation_present: true
  source_class: structured_candidate
  speech_act_class: answer
  assistant_inference_present: true
  clarification_requested: false
  repair_attempted: false
  topic_shift_present: false
  task_boundary_present: false
  unresolved_reference_present: false
  response_complete: true
  confidence_band: medium
```

Default trace must not contain visible response text, prompt text, user text, MEM bodies, or semantic observation excerpts.

## Observation implementation order

RelayREF should prefer the lowest-cost sufficient method:

```text
1. validated structured candidate emitted with the Main LLM response
2. deterministic parser and transport/generation metadata
3. bounded heuristic classification
4. optional small structured probe only when policy and resource budget allow
```

An ordinary RelayREF observation must not require another Main LLM call. An optional probe is deferrable or busy-skippable and must not delay the user-visible response.

## Candidate validation

A structured candidate from the Main LLM remains low authority. RelayREF validates:

- schema version;
- allowlisted fields and enum values;
- bounded lengths and counts;
- finite confidence values when numeric confidence is allowed;
- consistency with transport facts, such as truncation or empty output;
- absence of internal-marker recursion;
- absence of copied prompt, MEM, or user content in content-free fields.

Invalid candidates produce `observation_unavailable` or a safe partial observation. They do not invalidate an otherwise safe visible response.

## Failure behavior

```text
candidate missing
  -> deterministic/heuristic observation when available

candidate invalid
  -> block candidate only
  -> preserve visible response

optional probe busy or timeout
  -> observation unavailable or partial
  -> no response delay

RelayREF internal failure
  -> RelayRUN records content-free failure
  -> return-side consumers use their safe defaults
  -> no MEM, SCN, EMO, REL, or SOUL mutation
```

## Non-ownership rules

RelayREF does not own:

- user intent or pre-action clarification;
- reference resolution authority;
- scene state or scene policy;
- current affect or expression state;
- CTX working state;
- Shared Assessment;
- Subjective MEM;
- relationship state;
- SOUL or other uppercase-source proposals;
- persistence eligibility;
- final user-visible wording;
- TTS or avatar execution.

## Relationship to RelayCTX Unpack

```text
RelayCTX Unpack
  syntax, marker separation, JSON parsing, size and envelope validation

RelayREF
  bounded meaning-level observation after separation
```

Unpack may route detached candidates to RelayREF, but it does not perform RelayREF's semantic observation or apply the result.

## Relationship to RelayINT

```text
RelayINT: what is requested and may the system proceed?
RelayREF: what did the generated response actually do?
```

RelayREF cannot repair an unsafe pre-action decision retroactively. It can only inform next-turn state, output-side safety handling, deferred SLP, and audit.

## Relationship to RelaySLP

```text
RelayREF
  output observation only

RelaySLP
  later evidence grouping, Shared Assessment, subjective formation,
  candidate relations, and governed workspace updates
```

RelayREF never acts as a lightweight memory writer.

## Fixed boundaries

- RelayREF runs only after safe output separation.
- RelayREF observations are low-authority and bounded.
- The ordinary path does not require a separate RelayREF LLM call.
- RelayREF does not rewrite visible output.
- RelayREF does not replace RelayINT, RelaySCN, RelayEMO, RelayCTX, RelaySLP, or RelayMEM.
- Assistant inference observed by RelayREF never becomes a user-origin claim merely through observation.
- Output-side observations are effective only for later output handling, next-turn state, deferred SLP, or audit.
