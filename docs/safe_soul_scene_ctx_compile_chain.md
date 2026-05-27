# Safe SOUL / Scene / CTX Compile Chain

## Goal

This document defines the design target for a safe compile chain that turns persona source files, scene state, memory candidates, recent turns, and the latest user input into an OpenAI-compatible prompt payload.

The goal is not to add a new runtime mutation path. The goal is to make the existing RelayLM context compiler direction explicit and safe:

```text
SOUL / OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  -> SCENE_STATE
  -> RelayCTX block assembly
  -> token budget planning
  -> preflight / diagnostics
  -> gated runtime apply
  -> backend OpenAI-compatible messages
```

## Non-goals

This design does not introduce:

- model weight training
- direct KV-cache mutation
- backend scheduler changes
- memory database writes
- persona source mutation during normal chat forwarding
- automatic rewriting of `room_anchor` into other fields
- runtime persistence of user-visible content
- hard rejection of normal chat requests

## Terms

### RelaySOUL

RelaySOUL owns persona-source revision workflow and approval-oriented calibration. It produces or updates source artifacts such as `SOUL.md`, `OUTPUT_POLICY.md`, `RELATIONSHIP_ANCHOR.md`, `STABLE_MEMORY_SUMMARY.md`, and `SCENE_STATE.md` through dry-run, approval, revision, persistence, and rollback workflows.

### Scene

Scene is the current conversational situation. It is represented by `scene_id` metadata and `SCENE_STATE.md` / `scene_state` content.

Scene is the compile target. `room_id` is only optional external host metadata, such as a frontend room, stream, channel, or conversation space.

### RelayCTX

RelayCTX owns effective context construction. It decides how selected persona, scene, memory, retrieved context, recent turns, and latest input are arranged into a token-budgeted prompt layout.

### Context compiler

The context compiler is the RelayCTX runtime component that renders selected blocks into OpenAI-compatible messages.

### RelayPLC

RelayPLC owns policy, routing, budget, fallback, and apply decisions. In this chain it decides whether to apply a compiled context, run shadow/dry-run diagnostics only, or preserve pass-through behavior.

## Source classes

The compile chain should classify inputs before rendering.

```text
stable persona sources
  common_runtime_policy
  SOUL.md
  OUTPUT_POLICY.md
  RELATIONSHIP_ANCHOR.md

slow memory/profile summaries
  STABLE_MEMORY_SUMMARY.md
  durable user memory summary
  durable character memory summary

dynamic scene and conversation state
  SCENE_STATE.md / scene_state
  retrieved memory candidates
  RAG or spill chunks
  recent turns
  latest input
  response instruction

external host metadata
  room_id
  session_id
  frontend route metadata
```

Only selected source content should enter the compiled prompt. External host metadata is available for scoping, routing, diagnostics, and memory boundaries, but should not become prompt text by default.

## Safe chain stages

### 1. Scope resolution

Resolve operator-facing scope:

```text
character_id
user_id / user_type
scene_id
session_id
optional room_id
route
mode
backend
```

Safety rule: missing optional host metadata must not block normal chat forwarding.

### 2. Source loading

Load profile source files and runtime inputs:

```text
common_runtime_policy
SOUL.md
OUTPUT_POLICY.md
optional room_anchor
optional RELATIONSHIP_ANCHOR.md
optional STABLE_MEMORY_SUMMARY.md
optional SCENE_STATE.md / scene_state
incoming OpenAI-compatible messages
```

Safety rule: optional legacy fields such as `room_anchor` must not cause `Path(None)` or equivalent crashes.

### 3. Scene normalization

Normalize dynamic situation state:

```text
preferred: scene_state
legacy alias: room_state -> scene_state when scene_state is unset
metadata: room_id remains external host metadata
```

Safety rule: dynamic scene content must not be promoted into stable prefix blocks.

### 4. Candidate selection

RelayMEM may provide memory candidates, retrieval results, or spill chunks. RelayMEM proposes candidates; RelayCTX chooses how to pack selected candidates.

Safety rule: memory candidate selection must not mutate the memory store during prompt compilation.

### 5. Block assembly

RelayCTX assembles blocks by stability class:

```text
stable_prefix
  common_runtime_policy
  character_soul_anchor
  character_output_policy
  relationship_anchor

slow_prefix
  stable_memory_summary
  durable memory summaries

dynamic_suffix
  scene_state
  retrieved_memory
  retrieved_rag
  recent_turns
  latest_input
  response_instruction
```

`room_anchor` may be emitted only when present, and should remain legacy compatibility content rather than a required block.

Safety rule: dynamic content should appear after persona and output policy so RAG, memory, and scene state do not rewrite identity.

### 6. Token budget planning

Plan approximate or tokenizer-aware budgets before rendering.

Minimum diagnostics should record:

- route
- mode
- character_id
- scene_id when available
- optional room_id when available
- block IDs
- stability classes
- omitted blocks and reasons
- approximate token or character budgets
- whether compilation was applied, shadow-only, or skipped

Safety rule: budget planning should omit or compress dynamic content before mutating stable persona sources.

### 7. Preflight

Preflight validates that the compiled context is structurally safe:

- required stable persona sources are available or fallback policy is defined
- optional legacy fields are handled safely
- block order follows stability rules
- dynamic content is not placed into stable prefix
- token budget decision is recorded
- pass-through fallback remains available

Safety rule: preflight failure should produce diagnostics and fall back safely, not crash the normal request path.

### 8. Gate

RelayPLC makes the final apply decision:

```text
APPLY
  use compiled messages

SHADOW_ONLY
  build diagnostics, but forward original or safer messages

PASS_THROUGH
  preserve incoming messages

FALLBACK
  use a safe minimal context or backend-compatible fallback
```

Safety rule: approval and preflight are not the same as gate. Approval accepts a proposed change. Preflight validates structure. Gate decides current runtime application.

### 9. Render and forward

Render selected blocks into OpenAI-compatible messages and forward through the adapter.

Safety rule: backend adapters preserve OpenAI-compatible semantics and should not expose internal tags or diagnostics unless explicitly requested.

## Compile states

Suggested state names:

```text
PASS_THROUGH
COMPILE_DRY_RUN
COMPILE_SHADOW_ONLY
COMPILE_APPLY
COMPILE_FALLBACK
```

These states should be diagnostic states first. Runtime behavior should remain conservative until smoke tests and manual checks show stable behavior.

## Artifact boundary

This chain should not confuse runtime compiled context with RelaySOUL persistence artifacts.

```text
RelaySOUL artifact
  approval / patch / revision / persistence / rollback audit object

Runtime compile plan
  transient diagnostic and decision object for prompt compilation

Memory record
  durable memory source item or retrieved candidate

Trace event
  runtime diagnostic line, optionally promoted later to an audit artifact
```

Content-free RelaySOUL artifacts should remain content-free. Runtime compiled prompts may contain user-visible content, but they should not be persisted as RelaySOUL artifacts by default.

## Minimal MVP target

A useful MVP for this chain is:

1. profile source loading handles optional legacy `room_anchor`
2. `scene_state` is preferred and `room_state` remains a legacy alias
3. context blocks are assembled by stability class
4. token budget diagnostics are emitted
5. preflight can explain omitted blocks and fallback reasons
6. gate can choose pass-through, shadow-only, or apply
7. smoke tests cover safe optional-field behavior and profile compile paths

## Future extensions

Future work can add:

- scene-aware memory scope selection
- scene transition diagnostics
- approval-aware SOUL revision application
- token-budget-aware scene compression
- profile prefix hash diagnostics
- per-character runtime instances for stronger prefix reuse
- RelayTRC lineage for compile plans and runtime decisions

These should be added after the minimal safe chain is stable.
