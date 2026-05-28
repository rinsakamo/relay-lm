# Runtime Compile Gate Design

## Scope

This document defines the runtime gate for deciding whether a compiled RelayLM context should be applied to an outbound backend request.

It focuses on runtime context application, not RelaySOUL persona-source mutation. RelaySOUL apply gates decide whether persona source artifacts may be mutated. The runtime compile gate decides whether already-loaded sources and runtime inputs may be compiled into the messages sent to the backend for the current request.

## Goal

After the Safe SOUL / Scene / CTX compile chain builds or plans a context, RelayLM needs an explicit decision point:

```text
incoming OpenAI-compatible request
  -> route / mode resolution
  -> profile and scene source loading
  -> compile plan / preflight
  -> runtime compile gate
  -> backend forwarding payload
```

The gate keeps the default proxy path safe while allowing controlled application of compiled persona/context messages.

## Non-goals

This design does not add:

- persona source mutation
- memory database writes
- direct KV-cache mutation
- backend scheduler changes
- post-generation response rewriting
- hard rejection of normal chat requests
- automatic persistence of compiled prompts
- automatic conversion of `room_anchor` content into other files

## Relationship to existing gates

### RelaySOUL apply execution gate

The RelaySOUL apply execution gate is for actual persona-source apply. It deals with approval artifacts, patch/revision lineage, persistence preflight, rollback readiness, and content-free audit metadata.

### Runtime compile gate

The runtime compile gate is for the current chat request. It decides whether the runtime should use compiled context messages, run diagnostics only, preserve pass-through behavior, or fall back.

```text
RelaySOUL apply gate:
  may persona source files be mutated?

Runtime compile gate:
  may compiled context be used for this request payload?
```

These gates are related but separate.

## Inputs

A runtime compile gate decision should receive:

- route
- mode
- backend model mapping
- character_id
- optional user_id / user_type
- optional scene_id
- optional room_id
- incoming OpenAI-compatible messages
- profile source loading result
- scene normalization result
- memory candidate summary
- block assembly result or dry-run plan
- token budget decision
- preflight status
- previous fallback or safety state when available

## Outputs

The gate should produce a small decision object:

```yaml
decision_state: COMPILE_APPLY
apply_compiled_messages: true
fallback_reason: null
diagnostics_only: false
selected_mode: memory_light
selected_route: relaylm-default
compiled_message_count: 2
omitted_block_ids: []
blocking_reasons: []
```

The exact runtime schema may evolve, but the decision must be easy to log and safe to inspect.

## Decision states

### PASS_THROUGH

Use the incoming request messages as-is, except for backend-compatible model mapping and normal adapter behavior.

Use when:

- route mode is `pass_through`
- compilation is disabled
- the request is an internal planning/tool/structured-output call that should not be persona-repacked
- the gate cannot safely determine whether compilation should apply

### COMPILE_DRY_RUN

Build a compile plan and diagnostics, but do not alter outbound messages.

Use when:

- validating new compile behavior
- collecting diagnostics for future apply readiness
- investigating token budget or block ordering without runtime behavior change

### COMPILE_SHADOW_ONLY

Build compiled messages and diagnostics, but forward a safer payload, usually original messages or a minimal fallback.

Use when:

- preflight is structurally safe but apply readiness is not yet proven
- comparing compiled context behavior against pass-through behavior
- collecting diagnostics for future gating thresholds

### COMPILE_APPLY

Use compiled messages for the backend request.

Use only when:

- route/mode allows compile apply
- profile and scene loading succeeded or explicit fallback sources were used
- preflight passed
- token budget decision is safe
- no blocking reasons exist
- the compiled payload preserves OpenAI-compatible semantics

### COMPILE_FALLBACK

Use a safe fallback payload instead of either full compiled context or naive pass-through.

Use when:

- compilation partially fails but the request should still be served
- stable persona files are missing and fallback SOUL policy is enabled
- dynamic blocks exceed budget and must be omitted
- adapter constraints require a smaller or simpler message shape

## Required gate checks

The gate should check:

- route is resolved
- backend is resolved
- mode is recognized
- profile source loading did not crash
- optional fields such as `room_anchor`, `scene_state`, and `room_state` are handled safely
- block ordering follows stability rules
- dynamic scene/retrieval content is not placed into stable prefix
- token budget status is not blocking
- fallback policy is available when required sources are missing
- outbound message list remains OpenAI-compatible

## Fail-safe behavior

The runtime compile gate should prefer safe service continuity over hard failure.

```text
invalid or unknown mode -> PASS_THROUGH or COMPILE_FALLBACK
missing optional field -> continue without that block
profile loading TypeError -> bug; should be covered by smoke tests
preflight blocked -> COMPILE_FALLBACK or PASS_THROUGH
budget blocked -> omit/compress dynamic blocks or fallback
adapter incompatibility -> PASS_THROUGH
```

Hard rejection should be reserved for explicit future policy decisions, not for normal compile uncertainty.

## Mode mapping

Initial mapping:

```text
pass_through:
  PASS_THROUGH

memory_light:
  COMPILE_APPLY when dry-run/preflight is ready
  COMPILE_FALLBACK or PASS_THROUGH when blocked

memory_full:
  COMPILE_DRY_RUN or COMPILE_SHADOW_ONLY until retrieval/budget behavior is proven

future persona_finalizer:
  apply only to final natural-language responses, not planning/tool calls
```

## Diagnostics

The gate should log enough metadata to debug decisions without inserting diagnostics into the prompt.

Suggested fields:

- decision_state
- apply_compiled_messages
- diagnostics_only
- fallback_reason
- blocking_reasons
- selected_route
- selected_mode
- backend
- character_id
- scene_id when available
- optional room_id when available
- block_ids
- omitted_block_ids
- token_budget_status
- stable_prefix_hash when available
- profile_source_status
- scene_source_status

## Interaction with token budgets

Token budget planning should happen before the final gate. The gate consumes the budget decision and decides whether the compiled payload is safe to apply.

Budget outcomes may map to gate decisions:

```text
within_budget -> COMPILE_APPLY eligible
trimmed_dynamic_blocks -> COMPILE_APPLY eligible with diagnostics
blocked_required_prefix -> COMPILE_FALLBACK
unknown_budget -> COMPILE_DRY_RUN or COMPILE_SHADOW_ONLY
```

Stable persona sources should not be mutated or rewritten to satisfy a runtime budget. Runtime budget pressure should omit, compress, or defer dynamic content first.

## Interaction with Scene

Scene affects compile apply through:

- `scene_state` prompt content
- `scene_id` diagnostics and memory scope
- scene-aware token budget decisions
- scene transition diagnostics in future work

`room_id` should remain optional host metadata. It may affect scoping and diagnostics, but it should not force a prompt block by default.

## Artifact boundary

Runtime compile gate decisions are runtime diagnostics, not RelaySOUL persistence artifacts.

```text
compile gate decision:
  transient runtime decision about this request

RelaySOUL approval/apply artifact:
  content-free audit object for persona-source mutation

trace event:
  machine-readable runtime event, optionally summarized later
```

Compiled prompts may contain user-visible content and must not be stored as content-free RelaySOUL artifacts by default.

## Minimal MVP target

A minimal runtime compile gate should support:

1. pass-through mode never mutates messages
2. memory-light mode can apply compiled profile messages when preflight is ready
3. blocked compile plans fall back safely
4. optional `room_anchor` absence does not crash profile loading or gate logic
5. `scene_state` and `room_state` alias behavior are covered by smoke tests
6. decision payloads include decision state, fallback reason, mode, route, and omitted blocks

## Future extensions

Future work can add:

- shadow compare between pass-through and compiled payloads
- per-route apply thresholds
- scene transition risk scoring
- token budget risk scoring
- user/operator-visible diagnostics endpoint
- RelayTRC trace integration
- profile prefix hash stability checks
- memory-full apply readiness gates

## Initial implementation note (MVP)

Current implementation is diagnostics/trace-only for compile decision dry-run:

- emits a compile decision dry-run object into runtime diagnostics
- propagates the object into trace metadata when trace is enabled
- does not apply compiled messages
- does not mutate outbound backend forwarding payload

This keeps runtime behavior fail-safe while making gate decisions observable.


- request path now emits compile decision dry-run diagnostics for normal `/v1/chat/completions` handling, while keeping outbound payload behavior unchanged.
