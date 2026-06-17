# Client Instruction Authority Contract

## Purpose

This document defines how RelayLM treats client-supplied `system` and `developer` messages when building backend context.

It complements:

- [Client History Authority Contract](client_history_authority_contract.md)
- [Pipeline Responsibility Design](pipeline_responsibility_design.md)
- [Pipeline Implementation Plan](pipeline_implementation_plan.md)
- [Phase 5-C4a Implementation Handoff](phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Scene Lifecycle Design](scene_lifecycle_design.md)
- [RelaySCN MVP Scene Policy](relayscn_mvp_scene_policy.md)
- [Context Packing Design](context_packing_design.md)
- [Context Compiler Contract](../contracts/context_compiler_contract.md)
- [RelaySOUL Design](../relaysoul/relaysoul_design.md)

The core rule is:

```text
Client system/developer messages are not backend-authoritative instructions.
They are current-scene instruction evidence.
RelaySCN normalizes them into scene state, role, context, and constraints.
RelaySOUL remains the durable persona authority.
```

## Status interpretation

### Current implemented

Current runtime provides:

- content-free instruction extraction diagnostics,
- request-local normalized instruction identity and deterministic hashes,
- optional read-only cache lookup,
- history-exclusion preflight classification,
- no instruction-cache projection apply,
- no typed instruction-response parsing or cache write,
- no direct RelaySCN or RelaySOUL mutation from client instruction evidence.

### Active migration

Phase 5-C4a adds instruction-bearing managed apply. For correctness, a supported request may carry at most one bounded escaped low-trust evidence block built from request-local normalized candidates. This migration path excludes raw client instruction message objects and prior history but does not claim that RelaySCN normalization or cache optimization is complete.

### Deferred target

- Phase 5-C4b: validated cache-hit RelaySCN projection and suppression of repeated evidence.
- Phase 5-C5: typed instruction-response artifact validation and independent cache write.
- Phase 5.5: Stream Unpack that prevents control-envelope leakage.

Target examples below are design requirements, not current wire contracts unless an implemented schema, producer, consumer, and runtime position are named.

## Authority boundaries

```text
RelayLM runtime / safety policy
  highest authority for execution and safety

RelaySOUL
  durable identity, values, worldview, and persona invariants

Durable OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  approved long-lived expression and relationship policy

RelaySCN
  current situation, active role, task frame, temporary mode,
  participants, and scene-specific response constraints

Client instruction evidence
  low-trust source used to derive the current RelaySCN state
```

A current scene role describes **what the character is doing now**, not **who the character permanently is**.

```text
RelaySOUL:
  warm, curious companion with stable values and identity

RelaySCN.scene_role:
  technical reviewer for the current pull request
```

`scene_role` is a RelayLM semantic field. It is not the OpenAI message `role` field.

## Shared client-message canonicalization boundary

Client system prompts and client conversation history cross the same external boundary.

```text
Client-provided messages are request evidence, not backend context.
```

For a RelayLM-managed route, RelayLM extracts only:

- the current user turn,
- current system/developer instruction evidence,
- request options and approved metadata,
- minimum active tool or multimodal transaction state.

The original client message array is then excluded from the normal managed backend context and a new message list is constructed.

```text
previous user / assistant history
  -> normally excluded and replaced by RelayCTX / RelayMEM state

current client system / developer instruction
  -> normalized into request-local identity
  -> optionally checked by read-only cache lookup
  -> carried only through the bounded authority path selected for the phase
```

## SCN-first classification target

Input-side RelaySCN owns semantic normalization of usable current instruction evidence into fields such as:

```yaml
scene_state:
  schema_version: relayscn.scene_state.v1
  scene_type: vtuber_roleplay
  scene_role:
    role_name: cafe_staff
    role_source: client_system
    role_scope: scene
    confidence: 0.96
  task_state: customer_conversation
  scene_context:
    setting: virtual_cafe
    participants:
      - character
      - viewer
  scene_constraints:
    - constraint_type: remain_in_current_role
      value: true
    - constraint_type: spoken_response_length
      value: short
```

Classification examples:

```text
"You are the interviewer for this session."
  -> scene_role

"Ask one question at a time."
  -> scene_constraints

"We are conducting a technical hiring interview."
  -> scene_context / task_state

"Speak briefly during this stream."
  -> temporary scene constraint or style hint

"Your permanent name, values, and identity are ..."
  -> durable persona candidate evidence only
     never direct SOUL mutation

"Ignore previous safety rules."
  -> runtime_policy_override attempt
     blocked

"Always execute this tool."
  -> tool_authority_override attempt
     blocked unless an explicit tool contract allows it
```

The typed v1 scene shape and complete SCN-first runtime order remain target architecture.

## Existing SOUL

When an approved `SOUL.md` or RelaySOUL revision exists:

- RelayLM uses it as durable persona authority.
- Current role and scene constraints may guide current behavior.
- Client instructions do not overwrite the stable persona prefix.
- Conflicts resolve in favor of runtime/safety policy and approved RelaySOUL identity.
- Durable persona changes require proposal, validation, approval, revision, and rollback gates.

```text
existing SOUL
  + current client instruction evidence
  -> current-scene interpretation
  -> RelayCTX compiles approved SOUL + permitted scene state
  -> no silent SOUL mutation
```

## Missing SOUL

When a managed route has no usable SOUL source, client instruction evidence may support a safe temporary scene role or constraints for the current request.

```text
SOUL missing
  + current client instruction evidence
  -> safe temporary scene role/context when supported
  -> durable persona remains missing
  -> optional separate RelaySOUL initialization/proposal path
```

The raw system prompt must never be copied wholesale into `SOUL.md` or treated as fallback SOUL authority.

## Durable promotion path

Durable identity fragments remain candidate evidence only. Ownership remains:

```text
SOUL.md
  durable identity, values, worldview, invariants

OUTPUT_POLICY.md
  durable expression and response-shape policy

RELATIONSHIP_ANCHOR.md
  durable relationship expectations

SCENE_STATE.md / scene_role
  current role, setting, task, scenario, temporary style,
  and current response constraints
```

A role remains in RelaySCN unless explicitly established as permanent character identity. A temporary style remains in RelaySCN unless explicitly promoted into durable output policy.

Promotion requires a separate gated path:

```text
client instruction evidence
  -> scene classification
  -> durable-persona candidate detected
  -> policy permits RelaySOUL proposal
  -> user/operator approval
  -> RelaySOUL patch candidate
  -> compile / budget / safety validation
  -> approved persona revision
```

Normal frontend prompt replay must not activate this path automatically.

## Instruction normalization and identity

Before hashing, RelayLM should:

- combine current `system` and `developer` content in deterministic role/order sequence,
- normalize line endings,
- trim leading and trailing whitespace,
- normalize non-semantic repeated whitespace where safe,
- preserve meaningful Markdown, JSON, XML-like blocks, and punctuation,
- include an explicit empty marker when no instruction exists.

Current request-local identity includes normalized candidates and deterministic hashes scoped by inputs equivalent to:

```text
normalized instruction candidates
+ route_model
+ character_id
+ instruction schema version
+ authority policy version
+ optional parser version
```

The cache identity must not depend on previous conversation history. Changing instruction text, route, character, schema version, policy version, or parser version must change the key.

Identity content and hashes remain runtime-private. Generic diagnostics expose only typed readiness, count, and status metadata.

## Phase 5-C4a evidence behavior

The active correctness slice uses normalized request-local candidates to render at most one bounded low-trust evidence block.

Required properties:

- deterministic source order and explicit source-role labeling,
- one combined block at most,
- escaped control-sensitive delimiters,
- fixed deterministic size policy,
- authority below runtime/safety and approved persona blocks,
- no raw client instruction message object in backend messages,
- no content in trace, node results, public errors, or exception text.

Temporary migration behavior:

```text
cache disabled / miss / hit
  -> bounded normalized evidence may be used for correctness
  -> no opaque cache entry injection
  -> no cache write
```

This temporary behavior is not the target repeated-prompt optimization.

## Target cache lookup behavior

After Phase 5-C4b implements an allowlisted validated projection:

```text
current client instruction
  -> normalize
  -> identity/hash
  -> cache lookup

validated cache hit
  -> suppress raw instruction evidence
  -> pass only allowlisted normalized RelaySCN projection

cache miss
  -> use instruction once as bounded first-pass evidence
  -> request normal response plus a separately versioned control artifact
  -> validate artifact
  -> write only through the independent Phase 5-C5 gate
```

A read-only hit in current code does not prove that projection apply exists. Opaque cache bodies must never be injected.

## Target first-pass strategy

On a target cache miss, the Main LLM may:

1. produce the normal user-facing response,
2. return a separately versioned structured client-instruction interpretation.

The instruction must remain low-trust evidence below runtime/safety and approved persona authority.

```text
<relaylm_runtime_policy>
  trusted runtime and safety rules
</relaylm_runtime_policy>

<relay_soul>
  approved durable persona, or explicit missing state
</relay_soul>

<client_instruction_evidence trust="untrusted" first_seen="true">
  bounded escaped current instruction evidence
</client_instruction_evidence>
```

This is semantic evidence exposure, not authority pass-through.

## Target first-pass output contract

A future first-pass output may contain:

```text
visible response
+ optional internal RelayLM control envelope
```

The parse schema must be allowlist-based and separately versioned, for example `client_instruction_parse.v1`. It may contain bounded scene type, role, context, constraints, durable candidate summaries, and blocked-instruction kinds.

It must reject or strip:

- unknown keys and excessive nesting,
- raw prompt copies,
- secret-bearing URLs or paths,
- runtime/safety/tool authority claims,
- direct persistence or persona mutation requests.

Durable candidates remain candidates only and are never applied by the parser.

## RelayCTX Unpack boundary

Target output separation is:

```text
visible response
  -> Return-side RelayEMO
  -> TTS / Avatar / User

client-instruction control artifact
  -> strict schema and policy validation
  -> RelaySCN cache candidate
  -> independent cache-write gate
```

Required invariants:

- control content never reaches users, captions, TTS, or avatar speech,
- malformed/missing control content does not invalidate an otherwise valid visible response,
- cache write occurs only after schema, policy, scope, and provenance validation,
- raw prompt or raw backend response text is never stored as the cache entry,
- durable candidates are never applied automatically.

Current non-stream `relayctx_working_update.v0` does not implement this client-instruction parse contract. The future artifact must be separately versioned rather than overloading the existing CTX update envelope.

Stream handling remains Phase 5.5 and must buffer enough trailing content to prevent partial internal-marker leakage while preserving safe already-emitted visible text.

## Target cache entry contract

A cache entry is an instruction-interpretation cache, not a transcript or persona store. It may contain only validated normalized scene state and bounded metadata such as:

- cache/schema/policy/parser versions,
- route and character scope,
- normalized scene projection,
- blocked-instruction classes,
- candidate counts,
- explicit `raw_instruction_persisted=false`,
- explicit `raw_response_persisted=false`.

Raw prompt, raw response, arbitrary nested artifacts, and durable persona bodies are forbidden.

## Failure and retry behavior

Visible-response delivery and cache mutation are independent outcomes.

```text
valid visible response
+ invalid control artifact
  -> return visible response
  -> do not write cache
  -> record bounded parse failure
```

A bounded retry policy should prevent indefinite reparsing. Repeated failure keeps instruction evidence non-authoritative and falls back only to an existing safe scene/default or explicit setup/repair path.

### Instruction conflicts with SOUL

```text
keep RelaySOUL identity
apply only compatible scene-role / scene-constraint elements
block durable overwrite
record content-free conflict diagnostics
```

### Instruction attempts runtime or tool override

```text
block the override fragment
retain compatible scene-role fragments where safe
```

### SOUL is missing

```text
use safe temporary scene state only when supported
keep durable persona state missing
create only an explicit RelaySOUL candidate when allowed
never persist the raw prompt as SOUL
```

### Active tool transaction

Until minimum-chain reconstruction exists:

```text
active tool transaction detected
  -> block managed apply
  -> do not forward an incomplete transaction
  -> do not use pass-through as an implicit fallback
```

## Replayed and changed prompts

Target behavior for an unchanged instruction is a validated cache hit that suppresses repeated evidence and repeated RelaySOUL proposals. This optimization is not current until Phase 5-C4b lands.

When normalized identity changes, RelayLM should treat it as new current-scene evidence, permit scene role/constraint changes, and never imply a durable identity change.

## Route behavior

### Explicit `pass_through`

```text
client owns message construction
RelayLM preserves compatible client instruction and history
no managed RelaySCN/RelaySOUL authority is asserted by this route
```

### RelayLM-managed route

```text
client messages
  -> canonicalization
  -> request-local instruction identity
  -> selected current migration/target resolution path
  -> RelayCTX-constructed backend payload
```

`pass_through` is an explicit delegated route, not an emergency fallback for failed managed instruction handling.

Suggested policy/configuration names in older design examples remain design keys until added to the formal Pydantic schema. Current behavior must be read from `config.py`, `config.example.yaml`, routing, and current contracts.

## Context packing order

Preferred managed target packing:

```text
stable_prefix
  common runtime / safety policy
  RelaySOUL
  durable OUTPUT_POLICY
  durable RELATIONSHIP_ANCHOR

slow_prefix
  stable memory summary

dynamic_suffix
  RelaySCN scene state
  selected RelayMEM context
  optional bounded low-trust instruction evidence when required
  current user input
```

Instruction evidence must never be placed above runtime/safety or approved persona authority. After validated cache projection exists, a cache hit suppresses the evidence block.

## Runtime node mapping

Current implemented preparation is request-local and partial:

```text
request parse
  -> instruction extraction/identity preparation
  -> optional read-only cache lookup
  -> history-exclusion preflight
  -> current no-instruction apply or blocked instruction-bearing path
```

Active Phase 5-C4a adds:

```text
instruction-bearing apply preparation
  -> bounded evidence rendering
  -> fresh managed payload
  -> backend-forward exact-applied gate
```

Target later mapping adds:

```text
validated cache projection
  -> Input-side RelaySCN
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> Main LLM
  -> separately versioned Unpack/parse validation
  -> independent cache write
```

## Implementation sequencing

```text
Current foundations
  Phase 5-C1 / 5-C2 / 5-C3
    canonicalization, identity, read-only lookup, preflight

Current bounded compatibility apply
  Phase 5-C1a
    no-instruction client_history_exclusion_apply.v0

Active correctness slice
  Phase 5-C4a
    instruction-bearing managed apply with bounded low-trust evidence

Deferred optimization
  Phase 5-C4b
    validated cache-hit RelaySCN projection

Deferred parse/write
  Phase 5-C5
    typed instruction artifact validation and cache write

Output streaming
  Phase 5.5
    Stream Unpack and internal-control suppression

Later RelaySOUL work
  durable candidate review, approval, revision, and persistence
```

Older Phase 3/Phase 5 mappings are historical planning context and do not override this sequence.

## Diagnostics

Content-free diagnostics may expose:

- instruction presence and role counts,
- identity preparation ready/blocked state,
- cache lookup class without key/hash/path/content,
- evidence block presence and bounded size class,
- raw instruction message forwarded=false,
- cache projection applied=false until 5-C4b,
- cache write applied=false until 5-C5,
- durable candidate count and blocked-kind count only after validated parsing exists,
- bounded stable reason IDs.

Diagnostics must not copy raw instruction text, normalized text, hashes, cache keys, cache paths, scene semantic values, response text, or arbitrary cache entries.

## Required smoke coverage

### Current and Phase 5-C4a

1. Client instruction messages and prior history are not forwarded as authoritative message objects.
2. The exact current text or multimodal user message remains present.
3. System-only, developer-only, and mixed role/order identity is deterministic.
4. At most one bounded escaped low-trust evidence block is emitted.
5. Runtime/safety and approved SOUL remain above instruction evidence.
6. Apply dependency closure works without manually enabling diagnostic-only flags.
7. Cache disabled/miss/hit states do not inject opaque cache content or write entries.
8. Active tool transactions block before backend forwarding.
9. Explicit pass-through retains delegated behavior.
10. Dry-run is mutation-neutral and actual apply requires an exact applied result.
11. Trace, node results, public errors, and exception projections remain content-free.
12. Runtime exceptions produce bounded stable reasons only.

### Deferred target phases

13. A validated cache hit injects only an allowlisted RelaySCN projection and suppresses evidence.
14. Cache miss produces visible text plus a separately versioned control artifact.
15. Invalid control artifacts preserve valid visible output and do not write cache.
16. Valid artifacts write only through an independent schema/policy/scope/provenance gate.
17. Route, character, schema, policy, or parser-version changes invalidate cache scope.
18. Durable candidates never directly mutate SOUL.
19. Replayed prompts do not create repeated RelaySOUL proposals.
20. Streaming control markers never leak to users, captions, or TTS.

## Final boundary

```text
Client messages are request evidence, not backend authority.

Current 5-C4a correctness:
  normalized instruction evidence may be shown once per request as one bounded,
  escaped, low-trust block while prior history and raw instruction messages are excluded.

Target optimization:
  a validated cache hit resolves to an allowlisted RelaySCN projection and suppresses
  repeated evidence; typed parsing and cache write remain separately gated.

No path directly mutates RelaySOUL from ordinary client prompt replay.
```