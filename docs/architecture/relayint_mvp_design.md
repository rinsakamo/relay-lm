# RelayINT MVP Design

## Purpose

RelayINT is RelayLM's synchronous pre-action interpretation layer.

This document separates the **current implemented compatibility and fast-path artifacts** from the **target typed RelayINT intent/retrieval contract**.

RelayINT is not a memory database, long-term learning layer, output observer, or final response generator.

## Current implemented RelayINT paths

The current implementation in `relaylm/relayint.py` contains two distinct paths.

### Current reference-repair compatibility wrapper

`build_relayint_reference_repair_dry_run()` is a compatibility wrapper around the historical input-side RelayREF dry-run helper.

It currently:

- calls the legacy `build_relayref_dry_run_artifact()`,
- preserves the old artifact shape/behavior,
- adds `relayint_alias: true`,
- adds `source_compat_module: relayref`.

This is semantically an input-side RelayINT responsibility, but it is not yet a clean typed RelayINT artifact.

The current `app.py` still stores this compatibility result in a variable named `relayref_artifact` and passes it to RelayMEM Retrieval v0.

### Current fast-path artifact

`build_relayint_fast_path_dry_run()` returns:

```text
relayint_fast_path_dry_run.v0
```

Current properties:

- deterministic heuristic path,
- optional/default-off by configuration,
- dry-run and content-free,
- no LLM call,
- no MEM lookup,
- no backend payload mutation,
- no response mutation.

Current fields include:

```yaml
relayint_fast_path_dry_run:
  schema_version: relayint_fast_path_dry_run.v0
  enabled: true
  dry_run_only: true
  content_free: true
  llm_called: false
  mem_lookup_executed: false
  detected_reference_kind: prior_memory_request
  reference_terms_detected_count: 1
  explicit_prior_memory_request_detected: true
  candidate_action: recall_then_answer_candidate
  mem_query_needed_candidate: true
  confidence_bucket: high
  ambiguity_detected: false
  llm_path_would_call: false
  decision_reasons: []
  latest_user_message_present: true
  latest_user_message_chars: 12
  latest_user_message_is_short: true
  ctx_working_metadata: {}
  safety_gates:
    content_free: true
    llm_call_allowed: false
    mem_lookup_allowed: false
    backend_payload_mutation_allowed: false
    response_mutation_allowed: false
```

This artifact is not the same as the proposed runtime-private `relayint.intent.v1` object.

### Current Retrieval handoff limitation

Current RelayMEM Retrieval does not yet consume `relayint_fast_path_dry_run.v0` as its primary typed decision.

Instead, Retrieval v0 consumes the historical RelayREF-shaped compatibility artifact for unresolved-reference blocking and separately derives query terms from raw messages.

Thus these statements are target architecture, not fully implemented current behavior:

- RelayINT alone authorizes long-term retrieval,
- Retrieval receives a typed confirmed scope,
- Retrieval receives no raw message array,
- RelayINT runtime-private intent and content-free projection are producer-separated.

### Current quick-clarification artifacts

The current module also contains content-free preflight/apply-plan helpers for quick clarification, including:

```text
relayint_quick_clarification_preflight.v0
relayint_quick_clarification_apply_plan.v0
```

These helpers evaluate scene and request compatibility and preserve fail-closed/default-off behavior. Current runtime apply/short-circuit behavior must be read from the latest implementation status and app wiring; the design target remains that visible clarification follows the normal output safety contract and RelayRUN orchestration.

## Current runtime position

After P0-PIPE / PR #458, current request-path ordering is:

```text
request/profile compilation
  -> RelayREL content-free relationship projection
  -> RelaySCN v0
  -> Input-side RelayEMO
  -> RelayINT historical compatibility reference repair
  -> RelayINT fast-path dry-run
  -> RelayINT quick-clarification preflight/apply planning
  -> RelayMEM Retrieval v0
  -> later RelayCTX/backend phases
```

This current order includes the shipped P0 ordering correction. RelayINT itself still differs from the target typed v1 contract below because it uses compatibility artifacts and Retrieval v0 still derives some query terms from raw messages.

## Target canonical position

```text
User input
  -> RelayREL
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

Target RelayINT runs after relationship/scene/affect policy setup and before Retrieval so long-term memory is not used to guess ambiguous references silently.

## Target component boundary

```text
RelayREL
  relationship-conditioned policy

RelaySCN
  scene and policy

RelayEMO
  affect estimate and expression pressure

RelayINT
  intent, references, topic/action anchors, proceed/clarify/retrieve decision

RelayMEM Retrieval
  approved long-term memory read

RelayCTX
  short-term working state and prompt construction

RelayREF
  post-generation output observation

RelaySLP
  deferred memory/SOUL proposal compilation
```

RelayINT may emit request-local interpretation artifacts. It never writes MEM or SOUL.

## Relation to RelayCTX working state

RelayCTX working state may include:

- current topic,
- active task/question,
- prior decision,
- referable items,
- unresolved slots,
- next expected action.

RelayINT reads this state when resolving short references and continuation intent.

RelayCTX Unpack only detaches a `relayctx_working_update.v0` candidate. It does not automatically commit or persist it.

## Target reference-resolution policy

Recommended precedence:

```text
1. explicit nouns and constraints in the current user turn
2. RelayCTX request-local/RAM-side working state
3. minimum user confirmation among plausible candidates
4. RelayMEM Retrieval only after explicit or confirmed long-term scope
```

| State | Target RelayINT action | Target RelayMEM action |
|---|---|---|
| One clear active-CTX referent | resolve and continue | do not retrieve |
| Multiple plausible active-CTX referents | ask candidate clarification | do not retrieve |
| No active-CTX candidate | ask open clarification | do not retrieve |
| Explicit memory request with clear scope | permit when scene allows | retrieve allowed scope |
| Confirmed reference but CTX lacks facts | request retrieval | retrieve allowed scope |
| Scene blocks external memory | continue/clarify within policy | do not retrieve |

Ambiguous references must never trigger silent long-term recall.

## Target runtime-private intent artifact

A future content-bearing request-local artifact may use:

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
  reference_resolution_state: resolved
  confirmed_scope: current_project
  ambiguity:
    has_ambiguity: false
    candidates: []
  confidence: 0.88
  action: continue_without_clarification
```

This artifact is target v1, not the current `relayint_fast_path_dry_run.v0` shape.

## Target content-free projection

Default persisted trace/audit should receive only:

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
  content_free: true
```

Do not persist resolved-reference text, candidate labels, topic strings, or user message content in the projection.

## Target MEM decision

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

## Target quick-clarification route

```text
RelayINT clarification candidate
  -> compatibility and active-transaction gates
  -> RelaySCN scene/formality/recovery gate
  -> RelayRUN short-circuit/checkpoint route
  -> normal visible/internal output safety boundary
  -> Return-side RelayEMO bounded hint
  -> Output-side RelaySCN observation/gate
  -> user-visible clarification
```

Target rules:

- default-off until apply is explicitly enabled,
- no incompatible tool/structured/multimodal short circuit,
- no safety/recovery bypass,
- no direct user-visible text finalized by RelayRUN,
- templated text remains bounded,
- generic diagnostics retain template IDs/classes, not rendered text.

## Recovery interaction

RelayINT may request recovery when context candidates remain contradictory, repeated correction indicates drift, scene stability is too low, or no safe next action can be determined.

RelaySCN resolves policy; RelayRUN orchestrates waiting-user/recovery state. RelayINT does not emit recovery text directly.

## Required migration scope

A future implementation migration should update together:

1. retire/rename the historical RelayREF-shaped compatibility artifact,
2. define `relayint.intent.v1` runtime-private output,
3. define `relayint.projection.v1` persisted projection,
4. connect the typed decision to RelayMEM Retrieval,
5. remove Retrieval dependence on raw messages for authorization/scope,
6. preserve current fast-path safety gates and reason IDs,
7. update quick-clarification consumers and RelayRUN wiring,
8. preserve the shipped P0 order `RelayREL -> RelaySCN -> RelayEMO -> RelayINT`,
9. update INT/MEM/trace/integration smoke tests,
10. preserve v0 compatibility through explicit schema/version handling.

## Non-goals

RelayINT does not:

- claim target v1 is already implemented,
- write MEM,
- mutate RelaySOUL,
- inspect generated output,
- commit CTX candidates by itself,
- silently retrieve for ambiguity,
- expose semantic intent content through target generic trace records.

## Summary

```text
current
  RelayREL -> RelaySCN -> RelayEMO -> historical RelayREF-shaped RelayINT compatibility artifact
  + independent content-free fast-path dry-run v0
  + quick-clarification preflight/apply artifacts

target
  REL policy + SCN policy + CTX working state + current turn
  -> typed RelayINT intent v1
  -> typed retrieval decision/confirmed scope
  -> RelayMEM Retrieval
```
