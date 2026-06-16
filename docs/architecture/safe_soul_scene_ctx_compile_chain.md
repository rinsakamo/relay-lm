# Safe SOUL / Scene / CTX Compile Chain

## Goal

This document defines the safe compile chain that turns approved durable persona sources, request-local scene policy, selected memory evidence, RelayLM-owned short-term context, and the current user turn into an OpenAI-compatible backend payload.

```text
approved durable sources
  + RelaySCN request-local state/policy
  + RelayINT proceed/retrieval decision
  + RelayMEM read-only evidence
  + RelayCTX working-state selection
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> RelayRUN orchestration
  -> backend adapter
```

The chain must preserve client-authority boundaries, component ownership, content-free observability, and safe fallback behavior.

Current implementation phase and sequencing live in [Pipeline Implementation Plan](pipeline_implementation_plan.md). This document defines stable ownership and invariants.

## Ownership

### RelaySOUL

RelaySOUL owns approved durable persona-source revision and approval workflows:

- `SOUL.md`,
- durable `OUTPUT_POLICY.md`,
- durable relationship principles or anchors,
- revision, approval, persistence, and rollback artifacts.

RelaySOUL does not own request-local scene state, current conversation continuity, compiled memory pages, or normal-turn prompt construction.

### RelaySCN

RelaySCN owns request-local semantic situation and policy:

- scene type,
- current role,
- compact setting/task/participants,
- bounded scene constraints,
- safety sensitivity,
- formality,
- memory scope,
- expression allowance,
- recovery and confirmation policy,
- persistence gates.

RelaySCN does not own affect state, short-term conversation working state, durable persona revision, or memory writes.

### RelayINT

RelayINT owns pre-action interpretation:

- reference resolution,
- ambiguity and clarification decisions,
- action intent,
- proceed/block decision,
- whether RelayMEM Retrieval is needed.

RelayINT does not retrieve memory itself and does not write MEM or SOUL.

### RelayMEM Retrieval

RelayMEM Retrieval reads approved long-term memory evidence under RelaySCN and RelayINT constraints. It returns candidates and provenance to RelayCTX.

It does not own prompt layout or memory mutation.

### RelayCTX

RelayCTX owns:

- selection from request-local working state,
- context block assembly,
- stable-to-dynamic ordering,
- token-budget degradation,
- backend message rendering,
- visible/internal response separation through Unpack.

RelayCTX does not decide scene policy, memory persistence, or persona revision.

### RelaySLP

RelaySLP is out-of-band from the normal answer path. It compiles governed evidence into memory updates, held candidates, rejected candidates, or RelaySOUL proposals through explicit persistence and approval gates.

### RelayRUN and adapters

RelayRUN orchestrates node order, fallback/recovery, checkpoints, idempotency, and runtime state. Adapters preserve OpenAI-compatible request/response semantics.

Neither owns semantic persona, scene, intent, memory, or prompt-policy decisions.

## Source classes

### Stable persona sources

```text
common_runtime_policy
approved SOUL.md
approved OUTPUT_POLICY.md
approved relationship anchor
```

These form the stable prefix and should remain byte-for-byte stable when possible.

### Slow durable memory sources

```text
approved stable memory summary
approved durable user/character memory summaries
```

These are owned by RelayMEM storage and compiled through RelaySLP, not RelaySOUL.

### Request-local dynamic sources

```text
RelaySCN scene_state / scene_policy
RelayINT intent and retrieval decision
RelayMEM selected evidence
RelayCTX-selected short-term context
current user turn
minimum compatible tool/multimodal transaction state
response instruction
```

### External host metadata

```text
character_id
user_id / user_type
scene_id
session_id
optional room_id
route / mode / backend identifiers
```

Host metadata supports scoping, routing, diagnostics, and namespace isolation. It must not become prompt text by default.

## Client-authority prerequisite

For a managed route:

```text
original client messages
  -> validated current-turn extraction
  -> bounded current instruction-evidence extraction
  -> active transaction preservation check
  -> prior client history exclusion
  -> RelaySCN normalization
  -> RelayLM-owned context reconstruction
```

Client-provided messages are request evidence, not automatically trusted backend context.

Raw client `system` or `developer` messages are not RelaySOUL sources. They may appear only as bounded low-trust first-pass evidence under the Client Instruction Authority Contract.

## Compile chain

### 1. Scope resolution

Resolve and validate:

- route and mode,
- character and user namespace,
- scene/session/room metadata,
- backend target,
- compatibility-sensitive request shape.

Missing optional host metadata must not crash or block ordinary compatible requests.

### 2. Approved source loading

Load only configured or approved durable sources. Missing durable sources follow an explicit safe policy; they do not authorize copying raw client prompts into persona files.

### 3. RelaySCN normalization

Normalize scene evidence into request-local `scene_state` and `scene_policy`.

Scene state remains dynamic. It must not be promoted into the stable prefix or persisted as durable persona merely because it affected one response.

### 4. RelayINT decision

Resolve the current action, references, ambiguity, and retrieval need.

An unresolved reference blocks silent long-term memory retrieval. Clarification candidates must pass scene and compatibility gates.

### 5. RelayMEM read-only selection

When RelayINT and RelaySCN permit retrieval, RelayMEM selects bounded approved evidence and returns a runtime-private candidate artifact.

RelayMEM does not insert messages directly, choose final block order, or write memory during this stage.

### 6. RelayCTX working-state selection

RelayCTX selects only the short-term context needed for the current action. Internal working state is not copied wholesale into the prompt.

### 7. Block assembly

Recommended order:

```text
stable_prefix
  common_runtime_policy
  character_soul_anchor
  character_output_policy
  relationship_anchor

slow_prefix
  stable_memory_summary
  approved durable memory summaries

dynamic_suffix
  scene_state
  intent hints required for the current action
  retrieved_memory
  retrieved_rag
  selected RelayLM-owned recent context
  minimum protocol state
  latest_input
  response_instruction
```

Dynamic content appears after durable identity and output policy.

### 8. Token-budget planning

RelayCTX applies conservative degradation in this order:

1. remove diagnostics-only or preview context,
2. reduce retrieved memory/RAG,
3. reduce optional short-term hints,
4. shorten selected recent context,
5. block or use an authority-safe fallback when no valid payload remains.

Stable persona sources must not be mutated to satisfy a request budget.

### 9. Preflight

Preflight verifies:

- client-authority prerequisites,
- source approval and scope,
- block order and stability class,
- compatibility-sensitive request preservation,
- token-budget feasibility,
- content-bearing/runtime-private versus content-free projection separation.

Preflight validates structure and readiness. It does not itself authorize apply.

### 10. Runtime Compile Gate

The gate consumes route/mode, RelaySCN, RelayINT, RelayMEM, RelayCTX, and compatibility outcomes.

```text
APPLY
  use RelayLM-compiled messages

SHADOW_ONLY
  compute plans/projections without changing the backend payload

PASS_THROUGH
  allowed only for an explicit pass-through route or an explicitly compatible delegated-authority path

BLOCKED / RECOVERY / SAFE_FALLBACK
  use authority-safe handling without restoring excluded client history or instructions
```

For managed routes, compile failure must not fall back to raw client history or raw client system/developer messages.

### 11. RelayRUN orchestration and forwarding

RelayRUN records node states and chooses the already-defined runtime route. The adapter forwards the final OpenAI-compatible payload without changing semantic decisions.

## Artifact boundaries

### Content-bearing runtime artifacts

Examples:

- normalized RelaySCN state,
- RelayINT resolved reference text,
- RelayMEM snippets or page content,
- RelayCTX block content,
- backend messages,
- Unpack candidates.

These remain request-local or use explicitly protected diagnostic storage.

### Content-free projections

Default trace/audit projections contain only typed allowlisted metadata:

- presence flags,
- counts,
- enum/class values,
- confidence bands,
- budget numbers,
- stable reason identifiers,
- node status,
- payload-mutation booleans.

They must not contain raw messages, prompt blocks, memory bodies, scene semantic text, paths, or final response text.

## Failure invariants

- Explicit pass-through behavior remains unchanged.
- Managed routes never restore excluded client authority as fallback.
- Active tool transactions and unsupported structured/multimodal shapes fail closed or remain unchanged.
- Retrieval misses do not broaden memory scope silently.
- Malformed internal candidates never reach the user.
- Visible recovery text goes through the normal output pipeline.
- No normal-turn compile stage writes MEM or SOUL.

## Non-goals

This chain does not introduce:

- direct KV-cache mutation,
- backend scheduler changes,
- memory writes in the synchronous compile path,
- persona-source mutation during normal chat,
- frontend UI, TTS, ASR, or avatar ownership,
- generic recursive trace sanitization,
- a standalone `RelayPLC` semantic component.

## Summary

```text
approved SOUL and durable policy
  + RelaySCN request-local policy
  + RelayINT action/retrieval decision
  + RelayMEM read-only evidence
  + RelayCTX-selected short-term context
  -> RelayCTX Repack
  -> authority-safe gate
  -> RelayRUN
  -> adapter

Out-of-band:
  governed evidence -> RelaySLP -> gated MEM updates / SOUL proposals
```
