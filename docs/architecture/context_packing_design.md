# RelayLM Context Packing Design

RelayLM treats prompt construction as context compilation, not concatenation.

The design goal is to combine:

- approved character-source stability,
- relationship-conditioned behavior,
- scene and affect policy,
- useful memory evidence,
- low latency,
- backend prefix/KV cache reuse,
- content-safe output handling,
- explicit client-authority boundaries.

Current implementation phase and sequencing live in [Project Execution Plan](project_execution_plan.md) and [Project Status](../PROJECT_STATUS.md). The file-first workspace target source tree and Tier 0-3 cache model live in [File-first Character Workspace Design](file_first_character_workspace_design.md). This document defines the lower-level context packing interpretation used by RelayCTX and should be read as the packing strategy beneath that workspace target.

## Relationship to the File-first Character Workspace tiers

The older `stable_prefix` / `slow_prefix` / `dynamic_suffix` terminology remains valid as a lower-level packing strategy, but it is no longer a separate canonical product model.

```text
File-first Character Workspace Tier 0-3
  -> product/source and cache-tier model

Context packing stable/slow/dynamic classes
  -> RelayCTX lower-level placement strategy within those tiers
```

Recommended mapping:

```text
Tier 0 runtime policy
  -> stable prefix

Tier 1 approved uppercase character sources
  -> stable prefix

Tier 2 selected relationship / scene / memory wiki pages or compiled summaries
  -> slow prefix or semi-stable prefix

Tier 3 current state, retrieval, current input, and response instruction
  -> dynamic suffix
```

If this document and `file_first_character_workspace_design.md` appear to disagree, the workspace design owns the product source tree and cache tier vocabulary. This document owns only the RelayCTX packing placement rules.

## Authority and ownership

### Approved durable character sources

File-first target portable character sources include:

```text
SOUL.md
  durable identity, values, temperament, and invariants

STYLE.md
  durable voice, tone, roleplay flavor, formatting, and output surface

EMOTION.md
  durable emotion-response profiles, not current emotion state

BOUNDARY.md
  character-specific privacy, pressure, intimacy, disclosure, and safety-expression limits

LORE.md
  optional world, backstory, setting, factions, and proper nouns
```

These sources come from RelaySOUL-approved source calibration or approved route configuration. Client `system` or `developer` messages are not fallback persona sources. On managed routes they are bounded low-trust evidence for RelaySCN / client-instruction authority handling.

### RelayREL relationship policy

RelayREL contributes relationship-conditioned interaction policy before RelaySCN and RelayEMO run:

```text
RELATIONSHIP.md
  relationship role and parameter vocabulary

relationships/<target>.md
  target-specific relationship instance such as relationships/user.md
```

Relationship state is distinct from durable character identity and from factual memory. It must not be folded back into `SOUL.md` or RelaySCN scene state by default.

### RelaySCN state

RelaySCN contributes request-local situation and policy:

- scene type,
- current role,
- compact setting/task/participants,
- bounded scene constraints,
- safety sensitivity,
- formality,
- memory scope,
- expression allowance,
- recovery/confirmation state.

RelaySCN state is dynamic and must not become stable persona content.

### RelayEMO state

Affect estimates and expression state belong to RelayEMO. RelayCTX may consume an allowlisted expression/output hint, but `scene_state` must not become the owner of current mood or affect inference.

### RelayCTX working state

RelayCTX may retain more request-local or RAM-side continuity state than the Main LLM receives:

```text
working state
  current topic
  active task / question
  prior decision
  referable items
  unresolved slots
  selected recent continuity metadata

prompt-selected context
  only the bounded hints needed for the current action
```

Working state is not automatically copied into the prompt and is not automatically persisted.

### RelayMEM evidence

RelayMEM Retrieval returns approved read-only evidence. RelayCTX decides final packing and placement. RelaySLP owns deferred memory compilation and writes.

## Managed-route prerequisite

For a managed route:

```text
client messages
  -> current-turn extraction
  -> bounded current instruction-evidence extraction
  -> active transaction preservation check
  -> prior client history exclusion
  -> RelayLM-owned context reconstruction
```

`recent context` in this document always means **selected RelayLM-owned recent context**, not the original frontend history array.

Explicit `pass_through` routes are the exception and intentionally preserve delegated client authority.

## Recommended request-path order before packing

RelayCTX receives upstream artifacts after the shipped P0-PIPE order:

```text
RelayREL
  -> RelaySCN
  -> RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
```

RelayCTX must not compensate for missing upstream ownership by reparsing raw user text as relationship, scene, affect, intent, or memory authority.

## Recommended context order

RelayLM orders context from stable to dynamic.

```text
1. common_runtime_policy
2. character_soul
3. character_style
4. character_boundary
5. character_emotion_profiles
6. optional_lore
7. relayrel_relationship_policy
8. stable_memory_policy_or_summary
9. relayscn_scene_policy / scene_state
10. relayemo_expression_hint
11. relayint_intent_or_reference_hint
12. retrieved_memory / RAG / spill chunks
13. selected RelayLM-owned recent context
14. minimum compatible tool/multimodal transaction state
15. latest_input
16. response_instruction
```

The core rule:

> Stable approved context goes first; bounded current evidence goes later.

This protects persona authority and improves prefix/KV reuse.

## Selection is not budget filling

A token budget is an upper bound, not a target.

RelayCTX Repack prefers the smallest sufficient context:

1. preserve required runtime and approved character-source anchors,
2. include RelayREL / RelaySCN / RelayEMO / RelayINT evidence needed for the current action,
3. include confirmed short-term context,
4. include long-term memory only when RelayINT and RelaySCN allow it,
5. stop when the answer can be generated safely and coherently.

Unused budget remains unused.

## Stability classes

### Stable prefix

```text
common_runtime_policy
SOUL.md-derived character_soul
STYLE.md-derived character_style
BOUNDARY.md-derived character_boundary
EMOTION.md-derived emotion response profiles
optional LORE.md-derived durable lore
```

Rules:

- no timestamps,
- no random IDs,
- no client instruction hash,
- no current topic,
- no retrieved snippets,
- no volatile scene or affect state,
- byte-for-byte stability where practical.

### Slow / semi-stable prefix

```text
RelayREL selected relationship policy
approved durable user/character memory summaries
selected scene-wiki summaries when stable enough
selected memory-wiki summaries when stable enough
```

These may change after a governed RelaySLP or relationship update, not every turn.

### Dynamic suffix

```text
scene_state
scene_policy deltas
current affect/expression hint
intent / reference hints
retrieved_memory
retrieved_rag
selected_recent_context
minimum_protocol_state
latest_input
response_instruction
```

Dynamic content must remain after durable character and relationship sources.

## Common runtime policy

The shared runtime block should remain short and character-neutral. It may include:

- internal-marker non-disclosure,
- basic safety constraints,
- compatibility-safe response requirements,
- output suitability requirements.

It is not the character's SOUL, current relationship state, or current scene.

## Character blocks

### Character soul

Contains approved durable identity, values, worldview, and invariants.

It must not contain current topic, scene role, user-specific transient memory, RAG content, relationship-instance state, or client prompt replay.

### Character style

Contains approved durable expression policy. Temporary response constraints belong to RelaySCN or the current request, not automatic edits to durable style policy.

### Character boundary

Contains character-specific privacy, pressure, intimacy, disclosure, and safety-expression limits. It does not replace global runtime/safety policy.

### Emotion response profiles

Contains approved durable mappings for how the character expresses emotion classes. Current affect estimate and expression pressure belong to RelayEMO state and remain dynamic.

### Relationship policy

Contains RelayREL-approved relationship role/parameter guidance and selected target-specific relationship state. It is distinct from factual memory and should update only through a governed path.

## Scene block

`scene_state` is compact request-local situation content. Recommended shape:

```yaml
scene_state:
  schema_version: relayscn.scene_state.v1
  scene_type: review_work
  confidence: 0.90
  stability: 0.84
  scene_role:
    role_name: technical_reviewer
    role_scope: scene
    role_source: route_or_validated_instruction
  scene_context:
    setting: pull_request_review
    task: review_changed_files
    participants:
      - user
      - assistant
  scene_constraints:
    - constraint_type: evidence_required
      value: true
  task_state: review_changed_files
  safety_sensitivity: low
  formality: medium
  memory_scope: current_project
  expression_allowance: suppressed
  recovery_mode: false
  user_confirmation_required: false
```

Do not place these RelayREL/RelayCTX/RelayEMO-owned values into `scene_state`:

- target-specific relationship state,
- current mood or raw affect estimate,
- open questions list,
- recently discussed points,
- full current-topic continuity notes,
- referable items or unresolved slots,
- transcript-shaped conversation history.

RelaySCN may expose policy classes that constrain EMO or CTX without owning their semantic state.

## Retrieved memory and RAG

Retrieved evidence is dynamic and lower authority than runtime policy, approved durable character sources, relationship policy, and scene policy.

RelayCTX should preserve:

- provenance class,
- scope,
- confidence,
- contradiction/approval state,
- token estimate.

Blocked or unapproved evidence must not enter the prompt.

## Selected recent context

Selected recent context is derived from RelayLM-owned working state or approved short-term state.

Rules:

- include only what is required for the current action,
- preserve the current user turn separately,
- do not reinsert excluded frontend history,
- do not treat omission as permission to persist the omitted material,
- keep latency-sensitive profiles tightly bounded.

## XML-like rendering

Use stable simple tags for model conditioning. Example:

```xml
<relaylm_context version="1">
  <common_runtime_policy>...</common_runtime_policy>
  <character_soul>...</character_soul>
  <character_style>...</character_style>
  <character_boundary>...</character_boundary>
  <character_emotion_profiles>...</character_emotion_profiles>
  <relationship_policy>...</relationship_policy>
  <stable_memory_summary>...</stable_memory_summary>
  <scene_state>...</scene_state>
  <scene_policy>...</scene_policy>
  <expression_hint>...</expression_hint>
  <intent_context>...</intent_context>
  <retrieved_memory>...</retrieved_memory>
  <selected_recent_context>...</selected_recent_context>
  <latest_input>...</latest_input>
  <response_instruction>...</response_instruction>
</relaylm_context>
```

Machine contracts remain JSON/dataclass-shaped. Tags are for model conditioning, not audit records.

## Unknown client instruction

When the current instruction identity is unknown and the authority contract permits first-pass evidence, RelayCTX may include one bounded escaped block:

```xml
<client_instruction_evidence trust="untrusted" first_seen="true">
  ...bounded current evidence...
</client_instruction_evidence>
```

It must:

- remain below runtime policy and approved RelaySOUL / RelayREL / RelaySCN authority,
- exclude prior client history,
- be absent on a validated cache hit,
- never be copied into default diagnostics,
- never become `SOUL.md` automatically.

## Control-artifact boundary

`relayctx_working_update.v0` and future client-instruction interpretation are separate contracts.

A future client-instruction control artifact should use an independent schema such as `client_instruction_parse.v1`. It must not overload or reinterpret `relayctx_working_update.v0`.

RelayCTX Unpack separates visible output from internal candidates. It does not commit working state, write instruction cache, or persist memory by itself.

## Budget degradation

Degrade in this order:

1. remove diagnostics-only or preview context,
2. reduce retrieved memory/RAG,
3. reduce optional working-state hints,
4. shorten selected recent context,
5. block or use an authority-safe fallback when no valid payload remains.

Do not restore raw client history or mutate durable character sources as fallback.

## Content-bearing versus content-free surfaces

Content-bearing runtime objects include compiled blocks, relationship semantics, scene semantics, resolved references, memory evidence, and backend messages.

Default trace/audit projections include only:

- block presence/counts,
- stability classes,
- budget values,
- source classes,
- reason identifiers,
- payload-mutation booleans.

They must not include prompt text, relationship bodies, memory bodies, scene semantic text, paths, or final responses.

## Non-goals

Context packing does not:

- classify relationship, scene, or affect,
- resolve ambiguity,
- retrieve or write memory,
- mutate RelaySOUL,
- own frontend history authority,
- own backend transport,
- expose content-bearing blocks through default diagnostics.

## Summary

```text
approved durable character sources
  + RelayREL relationship policy
  + RelaySCN request-local policy
  + RelayEMO expression hint
  + RelayINT action hints
  + RelayMEM approved evidence
  + RelayCTX-selected short-term context
  + current user turn
  -> stable-to-dynamic packing
  -> conservative budget
  -> authority-safe backend messages
```

## I1 bounded Primary MEM injection

RelayCTX receives a request-local selected-memory artifact after the Primary recall selection path and exact scope/integrity validation. M2 remains the preferred relevance owner. When M2 yields no eligible scoped Primary candidate, the E1-R5 bounded scoped Primary candidate bridge may supply a fallback candidate before the bounded RelayCTX injection step. Only bounded Primary summary evidence is inserted before the latest user message. `SOUL.md`, `STYLE.md`, `BOUNDARY.md`, RelayREL relationship policy, RelaySCN scene policy, and current RelayEMO expression constraints remain higher authority; path, identity, lineage, retry, and control-file metadata are excluded from the backend prompt and public diagnostics.
