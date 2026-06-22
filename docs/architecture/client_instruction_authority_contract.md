# Client Instruction Authority Contract

## Purpose

This document defines how RelayLM treats client-supplied `system` and `developer` messages when building backend context.

It complements:

- [Client History Authority Contract](client_history_authority_contract.md)
- [Pipeline Responsibility Design](pipeline_responsibility_design.md)
- [Pipeline Implementation Plan](pipeline_implementation_plan.md)
- [Phase 5-C4a Implementation Handoff](phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Phase 5-C4b Cache-Hit RelaySCN Projection Handoff](phase5c4b_cache_hit_relayscn_projection_handoff.md)
- [Phase 5-C5c Runtime Cache-Writer Boundary Handoff](phase5c5c_runtime_cache_writer_boundary_handoff.md)
- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md)
- [Scene Lifecycle Design](scene_lifecycle_design.md)
- [RelaySCN MVP Scene Policy](relayscn_mvp_scene_policy.md)
- [Context Packing Design](context_packing_design.md)
- [Context Compiler Contract](../contracts/context_compiler_contract.md)
- [RelaySOUL Design](../relaysoul/relaysoul_design.md)

The core rule is:

```text
Client system/developer messages are not backend-authoritative instructions.
They are low-trust current-scene instruction evidence.
RelaySCN owns semantic normalization into scene state, role, context, and constraints.
RelaySOUL remains the durable persona authority.
```

## Status interpretation

### Current implemented

Current runtime provides:

- content-free instruction extraction diagnostics,
- request-local normalized instruction identity and deterministic hashes,
- optional strict read-only cache lookup,
- history-exclusion preflight classification,
- `client_history_exclusion_apply.v0` for supported no-instruction requests,
- `client_history_exclusion_apply.v1` for supported instruction-bearing requests with exact `client_instruction_source.v1` provenance,
- Phase 5-C4b content-free RelaySCN-facing projection diagnostics from validated cache hits,
- typed-parse candidate validation and content-free node results,
- one-shot trusted runtime-private typed-parse source consumption,
- default-off gated cache-writer planning and apply,
- Phase 5.5-B2 through C4 stream-safety and TTS-handoff metadata construction.

### Current limitations

Current runtime does not:

- infer v1 provenance from role, wording, content, or position,
- semantically apply the C4b diagnostics projection to RelaySCN,
- parse arbitrary backend visible responses into typed instruction artifacts,
- trust frontend metadata as a typed-parse source,
- support parser-versioned cache lookup/write compatibility,
- reconstruct active tool transactions,
- directly mutate RelaySCN or RelaySOUL from client instruction evidence,
- deliver adapter transport or execute TTS, audio, or avatar behavior.

All apply-like paths remain behind explicit default-off and dry-run-first gates. Target examples below remain design requirements unless an implemented schema, producer, consumer, and runtime position are named.

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

For a RelayLM-managed route, RelayLM extracts only the bounded current evidence permitted by the current contract:

- the exact current user turn,
- explicitly selected current system/developer instruction evidence for v1,
- request options and approved metadata,
- minimum active tool or multimodal transaction state only after a dedicated preservation contract exists.

The current v0/v1 apply paths construct a new managed message list. Active tool transactions remain blocked because the minimum chain is not yet reconstructed.

```text
previous user / assistant history
  -> excluded after successful managed apply
  -> replaced by RelayCTX / RelayMEM-owned state

current client system / developer candidates
  -> normalized into request-local identity
  -> optionally checked by read-only cache lookup
  -> only explicitly provenanced candidates may enter v1 evidence
```

## Instruction identity and provenance

All supported client `system` and `developer` messages may participate in request-local normalization and identity. Identity does not itself authorize forwarding.

```text
identity
  = which normalized candidates exist

provenance
  = which candidates the frontend explicitly identifies
    as current instruction evidence for this request
```

Role, wording, content, and message position do not establish provenance.

### Explicit v1 provenance

Instruction-bearing `client_history_exclusion_apply.v1` accepts only explicit provenance through the reserved request-local control envelope:

```json
{
  "relaylm": {
    "instruction_evidence": {
      "schema_version": "client_instruction_source.v1",
      "message_indices": [0]
    }
  }
}
```

Selected indices must:

- be non-empty, bounded, strictly increasing, and non-duplicated,
- be in range,
- point to `system` or `developer` messages,
- occur before the latest current user turn,
- exactly match request-local instruction identity candidates.

Missing or invalid provenance blocks v1 actual apply. Unselected system/developer candidates are excluded, including frontend summaries, memory notes, replayed persona blocks, and other role-encoded compatibility material.

The reserved top-level `relaylm` envelope is RelayLM control-plane input and is removed before managed backend forwarding.

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

The typed v1 scene shape and complete SCN-first runtime order remain target architecture. The current C4b projection is diagnostics-only and does not implement semantic RelaySCN apply.

## Current managed backend construction

### No-instruction v0

A supported v0 candidate contains:

```text
one RelayLM-owned compiled prefix
+ exact validated current user message
```

It requires zero client system/developer messages.

### Instruction-bearing v1

A supported v1 candidate contains:

```text
one RelayLM-owned compiled system message containing:
  approved runtime/profile/context blocks
  + one bounded escaped low-trust instruction-evidence block
+ exact validated current user message
```

The v1 candidate excludes:

- prior client user/assistant messages,
- raw client instruction message objects,
- unselected instruction candidates,
- frontend summaries and memory notes not explicitly selected,
- old unrelated tool results,
- opaque instruction-cache entry content,
- the reserved RelayLM control envelope.

The evidence builder emits canonical raw typed JSON with explicit source-role labels. The managed compiler renderer escapes the evidence and enforces the rendered-size bound immediately before final render.

Client instruction evidence is always below RelayLM runtime/safety policy and approved persona authority. It cannot directly mutate RelaySOUL, persistence, tools, runtime policy, or safety policy.

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

When a managed route has no usable SOUL source, client instruction evidence may support a safe temporary scene role or constraints only after a supported typed RelaySCN consumer exists.

```text
SOUL missing
  + current client instruction evidence
  -> safe temporary scene role/context when supported
  -> durable persona remains missing
  -> optional separate RelaySOUL initialization/proposal path
```

Current managed profile compilation still requires configured approved profile sources. The raw system prompt must never be copied wholesale into `SOUL.md` or treated as fallback SOUL authority.

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

## Current v1 evidence behavior

The current instruction-bearing correctness path uses normalized, explicitly selected request-local candidates to render at most one bounded low-trust evidence block.

Required properties:

- deterministic source order and explicit source-role labeling,
- one combined block at most,
- escaped control-sensitive delimiters,
- fixed deterministic size policy,
- authority below runtime/safety and approved persona blocks,
- no raw client instruction message object in backend messages,
- no content in trace, node results, public errors, or exception text.

Current migration behavior:

```text
cache disabled / miss / hit
  -> bounded selected evidence may be used for v1 correctness
  -> no opaque cache entry injection
  -> cache-hit diagnostics do not themselves suppress evidence
```

This behavior is not the target repeated-prompt optimization.

## Current cache-hit projection and target apply behavior

Phase 5-C4b currently emits `client_instruction_relayscn_projection.v0` as a detached content-free diagnostics summary from a validated cache hit.

It may expose only allowlisted enum/count/boolean-style facts and must not expose role names, scene values, instruction text, cache bodies, hashes, paths, payloads, or response text.

C4b does not currently:

- apply RelaySCN semantic state,
- suppress v1 instruction evidence,
- inject opaque cache content,
- mutate backend payloads.

The target repeated-prompt behavior remains:

```text
current client instruction
  -> normalize
  -> identity/hash
  -> cache lookup

validated semantic cache hit
  -> suppress repeated raw instruction evidence
  -> pass only allowlisted normalized RelaySCN state

cache miss
  -> use instruction once as bounded first-pass evidence
  -> request normal response plus a separately versioned control artifact
  -> validate artifact
  -> write only through the independent writer gate
```

A read-only hit or diagnostics projection does not prove that semantic projection apply exists. Opaque cache bodies must never be injected.

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

## Current typed-parse and cache-writer plumbing

Current C5 runtime plumbing accepts only a trusted in-process runtime-private typed-parse candidate. The source is consumed once and cleared during `PipelineContext` construction so stale candidates cannot leak into later requests.

When explicitly enabled, writer planning consumes:

- request-local instruction identity,
- the validated typed-parse result,
- managed-route gate state,
- writer dry-run setting,
- cache root and maximum entry size.

With `client_instruction_cache_write_dry_run_only=true`, no file is written. With dry-run disabled, the writer may persist only after exact schema, policy, scope, source, and identity validation passes.

Current C5 plumbing does not:

- parse backend visible text,
- accept arbitrary frontend metadata,
- extract a control envelope from a response,
- support non-null parser-version lookup/write under the current unversioned key,
- apply RelaySCN semantics,
- mutate backend or user-visible payloads.

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
- cache write occurs only after schema, policy, scope, identity, provenance, and source validation,
- raw prompt or raw backend response text is never stored as the cache entry,
- durable candidates are never applied automatically.

Current non-stream `relayctx_working_update.v0` does not implement this client-instruction parse contract. The future artifact must be separately versioned rather than overloading the existing CTX update envelope.

Current Phase 5.5-B2 through C4 provides gated internal-sentinel suppression and TTS-safe segmentation/handoff metadata construction. It does not implement the trusted client-instruction control-artifact producer, deliver adapter transport, or execute TTS/audio/avatar behavior.

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
+ invalid or missing control artifact
  -> return visible response
  -> do not write cache
  -> record bounded parse failure
```

A bounded retry policy should prevent indefinite reparsing. Repeated failure keeps instruction evidence non-authoritative and falls back only to an existing safe scene/default or explicit setup/repair path.

### Instruction conflicts with SOUL

```text
keep RelaySOUL identity
apply only compatible scene-role / scene-constraint elements
  when a typed semantic consumer exists
block durable overwrite
record content-free conflict diagnostics
```

### Instruction attempts runtime or tool override

```text
block the override fragment
retain compatible scene-role fragments only when a typed policy consumer permits it
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

The target behavior for an unchanged instruction is a validated semantic cache hit that suppresses repeated evidence and repeated RelaySOUL proposals. Current C4b provides only the content-free diagnostics projection; semantic suppression/apply is not current.

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
  -> explicit provenance selection for v1
  -> v0 or v1 managed context construction
  -> exact backend-forward gate
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

Instruction evidence must never be placed above runtime/safety or approved persona authority. A future validated semantic cache projection may suppress the repeated evidence block; current C4b diagnostics alone does not.

## Runtime node mapping

Current implemented request-local path:

```text
request parse
  -> instruction extraction/identity preparation
  -> optional read-only cache lookup
  -> C4b content-free cache-hit projection diagnostics
  -> optional trusted runtime-private typed-parse validation
  -> optional gated cache-writer planning/apply
  -> history-exclusion preflight
  -> v0 no-instruction or v1 explicit-provenance apply
  -> backend-forward exact-applied gate
```

Target later mapping adds:

```text
trusted response control-artifact producer
  -> separately versioned parse validation
  -> semantic RelaySCN state consumer
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> independent version-aware cache write
```

## Implementation sequencing

```text
Current foundations
  Phase 5-C1 / C2 / C3
    canonicalization, identity, read-only lookup, preflight

Current managed apply
  v0 no-instruction client_history_exclusion_apply.v0
  Phase 5-C4a explicit-provenance client_history_exclusion_apply.v1

Current cache observation
  Phase 5-C4b diagnostics-only RelaySCN-facing projection

Current typed-parse / writer plumbing
  Phase 5-C5 trusted runtime-private source validation
  default-off independent writer gate

Current output-safety preparation
  Phase 5.5-B2 through C4 suppression and handoff metadata

Deferred integration
  trusted response control-artifact producer
  parser-versioned lookup/write compatibility
  semantic RelaySCN apply from validated interpretation
  active tool-chain reconstruction
  RelaySOUL proposal/apply/revision execution
```

Older Phase 3/Phase 5 mappings are historical planning context and do not override this sequence.

## Diagnostics

Content-free diagnostics may expose:

- instruction presence and role counts,
- identity preparation ready/blocked state,
- cache lookup class without key/hash/path/content,
- evidence block presence and bounded size class,
- raw instruction message forwarded=false,
- C4b projection status and bounded enum/count fields,
- typed-parse and cache-write status/reason classes,
- payload mutation and exact-forward booleans,
- bounded stable reason IDs.

Diagnostics must not copy raw instruction text, normalized text, hashes, cache keys, cache paths, scene semantic values, response text, typed-parse bodies, or arbitrary cache entries.

## Required smoke coverage

### Current bounded behavior

1. Client instruction messages and prior history are not forwarded as authoritative message objects after successful apply.
2. The exact current text or multimodal user message remains present.
3. System-only, developer-only, and mixed role/order identity is deterministic.
4. v1 explicit provenance selection and rejection are deterministic.
5. At most one bounded escaped low-trust evidence block is emitted.
6. Runtime/safety and approved SOUL remain above instruction evidence.
7. Valid v1 actual apply reaches the backend only through the exact selected candidate.
8. Invalid or missing v1 provenance fails closed without restoring history.
9. Cache disabled/miss/hit states do not inject opaque cache content.
10. C4b projection remains content-free and diagnostics-only.
11. C5 runtime-private source is one-shot and writer gates remain fail-closed.
12. Dry-run writer behavior performs no filesystem mutation.
13. Active tool transactions block before backend forwarding.
14. Explicit pass-through retains delegated behavior.
15. Phase 5.5 metadata does not imply TTS/audio/avatar execution.
16. Trace, node results, public errors, and exception projections remain content-free.

### Deferred target phases

17. A validated semantic cache hit injects only an allowlisted RelaySCN state and suppresses repeated evidence.
18. Cache miss produces visible text plus a separately versioned control artifact.
19. Invalid control artifacts preserve valid visible output and do not write cache.
20. Valid artifacts write only through an independent schema/policy/scope/provenance/source gate.
21. Route, character, schema, policy, or parser-version changes invalidate cache scope.
22. Durable candidates never directly mutate SOUL.
23. Replayed prompts do not create repeated RelaySOUL proposals.
24. Streaming control markers never leak to users, captions, or TTS.

## Final boundary

```text
Client messages are request evidence, not backend authority.

Current managed correctness:
  v0 handles bounded no-instruction requests.
  v1 handles bounded explicit-provenance instruction-bearing requests.

Current cache work:
  C4b observes validated hits through content-free diagnostics.
  C5 validates trusted runtime-private typed candidates and can gate writes.

Still target:
  a trusted response artifact producer, semantic RelaySCN apply,
  broader transaction compatibility, and complete default-on managed reconstruction.

No path directly mutates RelaySOUL from ordinary client prompt replay.
```
