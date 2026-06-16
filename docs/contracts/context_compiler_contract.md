# RelayLM Context Compiler Contract

## Purpose

RelayLM treats prompt construction as context compilation rather than simple concatenation.

This document separates the **current implemented profile compiler** from the **target RelayCTX-owned managed compiler**.

Current implementation status and sequencing live in [Pipeline Implementation Plan](../architecture/pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

## Current implemented compiler

The current compiler entrypoint is `compile_chat_payload_if_enabled()` in `relaylm/request_compiler.py`.

### Current runtime position

The current request path calls the profile compiler before the later RelayEMO, RelaySCN, RelayINT, and RelayMEM Retrieval artifacts are built:

```text
request payload
  -> route resolution
  -> compile_chat_payload_if_enabled
       profile compiler / configured seed memory
  -> PipelineContext creation
  -> RelayEMO
  -> RelaySCN
  -> RelayINT compatibility and fast-path diagnostics
  -> RelayMEM Retrieval/runtime injection phases
  -> backend forwarding
```

Therefore the current compiler does **not** yet consume normalized RelaySCN, typed RelayINT decisions, RelayMEM Retrieval results, or RelayCTX working state as direct compile inputs.

### Current inputs

The current profile compiler consumes:

```text
RelayLMConfig
ResolvedRoute
incoming payload/messages
configured persona/profile files
configured local seed-memory selection
compile/apply mode decision
```

### Current behavior

When the compile gate allows apply, the current implementation:

1. resolves profile files,
2. builds profile blocks,
3. computes persona-source budget diagnostics,
4. loads configured local seed-memory selection best-effort,
5. inserts that memory block into profile blocks,
6. compiles messages using the profile/system-fallback helper,
7. records stable-prefix and context-block diagnostics.

The current compiler returns `CompiledRequest` with fields including:

```text
payload
plan
decision
compiler_used
memory_block_used
memory_source
memory_selection_summary
memory_block_assembly
memory_fallback_reason
token_memory_dry_run
stable_prefix_hash
stable_prefix_block_ids
memory_adapter_dry_run/readiness/conflicts
context_block_summary
persona_source_budget_diagnostics
```

### Current limitations

The current implementation predates the target managed compiler boundary:

- it runs before SCN/INT/Retrieval artifacts exist,
- it accepts the incoming `messages` array as a compile input,
- it uses configured seed memory rather than the target typed Retrieval handoff,
- it does not receive RelayCTX working-state selection,
- it does not emit the proposed target block-plan/projection schemas,
- its `system_fallback` behavior belongs to the current compatibility compiler and must not be mistaken for the final managed-route authority model.

The client-history and instruction authority contracts still define the target safety boundary for managed routes. The implementation migration must reconcile the current profile compiler with those contracts explicitly rather than assuming that the target pipeline is already wired.

## Target managed compiler

The target context compiler is a RelayCTX responsibility. It turns approved durable sources, normalized RelaySCN policy, RelayINT decisions, selected RelayMEM evidence, RelayCTX-selected short-term context, and current request evidence into an OpenAI-compatible backend message list.

### Target goals

The target compiler preserves:

- approved persona authority,
- explicit client/backend authority boundaries,
- smallest-sufficient context selection,
- memory usefulness,
- low latency,
- prefix/KV reuse,
- TTS/avatar-safe output boundaries,
- content-free observability.

### Target inputs

A future managed compiler may receive:

- runtime mode and route config,
- approved RelaySOUL and durable output/relationship policy,
- normalized RelaySCN runtime artifact and scene policy,
- typed RelayINT proceed/block/retrieval decision,
- validated current user turn,
- validated current client-instruction cache result or one bounded first-pass evidence block,
- minimum active tool/multimodal transaction state,
- RelayMEM runtime-private retrieval evidence,
- RelayCTX-selected short-term context,
- optional RAG/spill evidence,
- token-budget hints,
- backend compatibility constraints.

The original client `messages` array is not accepted as already-valid managed-route context.

## Target client-authority prerequisite

For managed routes:

```text
original client messages
  -> current user-turn extraction
  -> current instruction-evidence extraction
  -> instruction identity/cache resolution
  -> active transaction preservation check
  -> prior client history exclusion
  -> RelaySCN normalization
  -> RelayLM-owned context compilation
```

A managed compiler failure must not restore excluded client history or raw client `system`/`developer` messages.

Explicit `pass_through` routes remain the delegated-authority exception.

## Target output

The future managed compiler should return:

- copied backend-bound payload/messages,
- selected backend model mapping,
- request-local block plan,
- content-free packing projection,
- explicit apply/blocked/fallback state.

A typical managed output shape is:

```text
system/developer area
  RelayLM-compiled stable and dynamic context

minimum protocol messages
  only when compatibility requires them

latest user
  validated current user turn near the end
```

## Target stability groups

### Stable prefix

```text
common_runtime_policy
character_soul_anchor
character_output_policy
relationship_anchor
```

### Slow prefix

```text
stable_memory_summary
approved durable user/character summaries
```

### Dynamic suffix

```text
scene_state
intent_context
retrieved_memory
retrieved_rag
selected_recent_context
minimum_protocol_state
latest_input
response_instruction
```

On an unknown instruction identity only, one bounded escaped `client_instruction_evidence` block may appear in the dynamic suffix when the authority contract permits it.

## Target component boundaries

### RelaySCN input

The compiler consumes normalized situation and policy. It does not classify scene or decide persistence policy.

### RelayINT input

The compiler consumes already-resolved intent hints when required. It does not resolve references or decide whether retrieval is allowed.

### RelayMEM input

RelayMEM returns runtime-private evidence with provenance and budget metadata. RelayCTX decides final inclusion and placement.

### RelayCTX working state

RelayCTX selects a bounded subset. Omitted fields remain available to runtime state and are not automatically forgotten or persisted.

## Target ContextBlock

A future internal block representation may use:

```yaml
block_id: character_soul_anchor
block_type: character_soul_anchor
stability_class: stable_prefix
source_class: approved_persona_revision
content: "..."
token_budget_hint: 800
include_in_prefix_cache_target: true
```

`content` is runtime-private. Default trace projections may retain only block IDs/types/classes, presence/counts, and budget metadata.

## Target rendering

A stable conditioning form may be:

```xml
<relaylm_context version="1">
  <common_runtime_policy>...</common_runtime_policy>
  <character_soul_anchor>...</character_soul_anchor>
  <character_output_policy>...</character_output_policy>
  <relationship_anchor>...</relationship_anchor>
  <stable_memory_summary>...</stable_memory_summary>
  <scene_state>...</scene_state>
  <intent_context>...</intent_context>
  <retrieved_memory>...</retrieved_memory>
  <selected_recent_context>...</selected_recent_context>
  <latest_input>...</latest_input>
  <response_instruction>...</response_instruction>
</relaylm_context>
```

Tags are for model conditioning, not audit storage.

## Internal output contracts

The current `relayctx_working_update.v0` candidate and the future client-instruction parse contract remain separate:

```text
relayctx_working_update.v0
  short-term CTX update candidate

client_instruction_parse.v1
  future typed interpretation of current client instruction evidence
```

`client_instruction_parse.v1` is not implemented by the current profile compiler and must not overload `relayctx_working_update.v0`.

RelayCTX Unpack separates candidates; it does not itself commit working state, write instruction cache, persist memory, or mutate RelaySOUL.

## Target budget planning

A token budget is an upper bound, not a target.

Degrade in this order:

1. remove diagnostics-only/preview blocks,
2. reduce RelayMEM/RAG evidence,
3. reduce optional CTX working hints,
4. shorten selected recent context,
5. block or use an authority-safe fallback when no valid payload remains.

Do not restore excluded client authority or mutate stable persona sources to fit a request.

## Runtime-private artifact versus projection

### Runtime-private compiler artifact

May contain:

- block content,
- scene semantics,
- selected short-term context,
- resolved intent text,
- memory evidence,
- backend messages.

### Content-free compiler projection

May contain only typed allowlisted fields:

- block IDs/types,
- stability/source classes,
- presence/counts,
- estimated budget values,
- omission reason IDs,
- instruction-cache status,
- apply state,
- payload-mutation boolean.

It must not contain raw messages, prompt content, memory bodies, scene semantic text, paths, internal candidate bodies, or final response text.

## Required migration scope

A future implementation migration should update together:

1. move managed compilation after canonicalization and required SCN/INT/Retrieval inputs,
2. separate the existing profile compiler from the target RelayCTX managed compiler by explicit schema/version/name,
3. remove raw client-history authority from managed compile inputs,
4. define typed SCN/INT/MEM/CTX handoffs,
5. preserve active tool/multimodal transactions,
6. define runtime-private block plans and content-free projections,
7. update compile/apply gates and fallback behavior,
8. update PipelineContext and backend-forward wiring,
9. update compiler, authority, and integration smoke tests.

## Final contract

```text
current
  profile compiler + incoming messages + configured seed memory
  before SCN/INT/Retrieval

target
  canonicalized current evidence
  + approved durable state
  + normalized SCN
  + typed INT decision
  + Retrieval evidence
  + selected CTX working state
  -> authority-safe RelayCTX managed compilation
```
