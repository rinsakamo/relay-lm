# RelayLM Context Compiler Contract

RelayLM treats prompt construction as context compilation, not simple concatenation.

The context compiler is a RelayCTX responsibility. It turns approved durable sources, normalized RelaySCN policy, RelayINT decisions, selected RelayMEM evidence, RelayCTX-selected short-term context, and current request evidence into an OpenAI-compatible backend message list.

Current implementation status and sequencing live in [Pipeline Implementation Plan](../architecture/pipeline_implementation_plan.md) and [Project Status](../PROJECT_STATUS.md).

## Goals

The compiler preserves:

- approved persona authority,
- explicit client/backend authority boundaries,
- smallest-sufficient context selection,
- memory usefulness,
- low latency,
- prefix/KV reuse,
- TTS/avatar-safe output boundaries,
- content-free observability.

## Inputs

The compiler may receive:

- runtime mode and route config,
- approved RelaySOUL and durable output/relationship policy,
- normalized RelaySCN runtime artifact and scene policy,
- RelayINT proceed/block and retrieval decisions,
- latest validated current user turn,
- validated current client-instruction cache result or one bounded first-pass evidence block,
- minimum active tool/multimodal transaction state,
- RelayMEM runtime-private retrieval evidence,
- RelayCTX-selected short-term context,
- optional RAG/spill evidence,
- token-budget hints,
- backend compatibility constraints.

The original client `messages` array is not accepted as already-valid managed-route context.

## Client-message authority prerequisite

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

The compiler must not restore raw client history or raw client `system`/`developer` messages after a managed-route failure.

Explicit `pass_through` routes intentionally preserve delegated client authority and are the only default exception.

## Output

The compiler returns:

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

Backend adapters may split compiled context across supported message roles, but must not change semantic ownership.

## Stability groups

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

On a validated cache hit, raw client instruction evidence must not appear.

## Component boundaries

### RelaySCN input

The compiler receives normalized situation and policy. It does not classify scene or resolve persistence policy.

`scene_state` may include role, compact setting/task/participants, bounded constraints, task state, safety sensitivity, formality, memory scope, expression allowance, and recovery/confirmation state.

It must not be used as the owner of:

- raw affect or mood estimates,
- current topic notes,
- open questions,
- recently discussed points,
- referable items,
- unresolved slots.

Those belong to RelayEMO or RelayCTX working state.

### RelayINT input

The compiler consumes already-resolved intent hints only when needed for the current action. It does not resolve references or decide whether retrieval is allowed.

### RelayMEM input

RelayMEM returns approved runtime-private evidence with provenance and budget metadata. RelayCTX chooses final inclusion and placement.

RelayMEM does not insert backend messages as its semantic responsibility.

### RelayCTX working state

The compiler selects a bounded subset from working state. Omitted fields remain available to the runtime and are not automatically forgotten or persisted.

## ContextBlock

An internal block representation should include:

```yaml
block_id: character_soul_anchor
block_type: character_soul_anchor
stability_class: stable_prefix
source_class: approved_persona_revision
content: "..."
token_budget_hint: 800
include_in_prefix_cache_target: true
```

Required fields:

- stable `block_id`,
- semantic `block_type`,
- `stability_class`,
- non-secret `source_class`,
- runtime-private `content`,
- token/budget metadata,
- prefix-cache eligibility.

Filesystem paths, raw prompt text, and memory bodies must not be copied into default trace projections.

## Rendering

Use stable limited tags for model conditioning:

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

Machine contracts remain JSON/dataclass-shaped. Tags are not audit records.

## Unknown client instruction

On a cache miss, RelayCTX may include one bounded low-trust block:

```xml
<client_instruction_evidence trust="untrusted" first_seen="true">
  ...bounded current evidence...
</client_instruction_evidence>
```

It remains below runtime/safety policy and approved RelaySOUL authority.

## Internal output contracts

RelayCTX Unpack may separate visible response content from internal candidates.

The contracts must remain independent:

```text
relayctx_working_update.v0
  candidate short-term CTX update

client_instruction_parse.v1
  future typed interpretation of current client instruction evidence
```

`client_instruction_parse.v1` is a deferred optimization contract. It must not overload, reinterpret, or be stored inside `relayctx_working_update.v0`.

Until the dedicated typed parser/cache-write phase is implemented, documentation must not imply that a generic control envelope automatically creates RelaySCN cache state.

When implemented, the future flow is:

```text
visible response
  -> normal output pipeline

client_instruction_parse.v1 candidate
  -> strict schema validation
  -> authority/policy validation
  -> normalized RelaySCN candidate
  -> independent cache-write gate
```

A malformed internal candidate must not invalidate otherwise valid visible output, but it must block its own apply/write path.

RelayCTX Unpack does not commit working state, write cache entries, persist memory, or mutate RelaySOUL by itself.

## Budget planning

A token budget is an upper bound, not a target.

Degrade in this order:

1. remove diagnostics-only/preview blocks,
2. reduce RelayMEM/RAG evidence,
3. reduce optional CTX working hints,
4. shorten selected recent context,
5. block or use an authority-safe fallback when no valid payload remains.

Do not restore excluded client history or mutate stable persona sources to fit a request.

## Runtime Compile Gate

The gate consumes compiler preflight plus RelaySCN, RelayINT, compatibility, and RelayRUN routing requirements.

```text
APPLY
  use compiled messages

SHADOW_ONLY
  record plan/projection without payload change

PASS_THROUGH
  explicit pass-through route only

BLOCKED / RECOVERY / SAFE_FALLBACK
  managed-route authority-safe handling
```

Managed compilation failure must not fall back to raw client authority.

## Runtime-private artifact versus projection

### Runtime-private compiler artifact

May contain:

- block content,
- scene semantics,
- selected short-term context,
- resolved intent text,
- memory evidence,
- backend messages.

It remains request-local or protected by explicit access and retention policy.

### Content-free compiler projection

May contain only typed allowlisted fields:

- block IDs/types,
- stability classes,
- presence/counts,
- source classes,
- estimated budget values,
- omission reason identifiers,
- instruction cache status,
- apply state,
- payload mutation boolean.

It must not contain raw messages, prompt content, memory bodies, scene semantic text, local paths, internal control bodies, or final response text.

## Compatibility

Tool calls, structured output, multimodal content, and provider-specific request shapes must be preserved or explicitly blocked by preflight. They must not be flattened into ordinary text.

Active tool transactions must remain intact or block managed repacking.

## Failure boundary

```text
instruction evidence invalid
  -> no typed parse/cache write
  -> do not restore raw client messages

RelayCTX Repack invalid
  -> no partial mixed-trust payload
  -> authority-safe blocked/recovery/fallback route

RelayCTX Unpack candidate invalid
  -> preserve safely recoverable visible output
  -> suppress malformed internal content
  -> no candidate apply
```

## Final contract

```text
Client messages are request evidence, not managed backend context.
RelayCTX receives approved durable state, normalized RelaySCN policy,
RelayINT decisions, RelayMEM evidence, selected short-term context,
and the validated current turn.
It reconstructs an authority-safe backend payload and emits only
content-free diagnostics by default.
```
