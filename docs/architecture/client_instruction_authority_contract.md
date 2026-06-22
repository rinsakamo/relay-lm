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
- [Context Packing Design](context_packing_design.md)
- [RelaySOUL Design](../relaysoul/relaysoul_design.md)

The core rule is:

```text
Client system/developer messages are not backend-authoritative instructions.
They are low-trust current-scene instruction evidence.
RelaySCN owns eventual semantic scene normalization.
RelaySOUL remains durable persona authority.
```

## Current status

### Implemented bounded behavior

Current runtime provides:

- content-free instruction extraction diagnostics,
- request-local normalized instruction identity and deterministic hashes,
- strict optional read-only cache lookup,
- history-exclusion preflight,
- `client_history_exclusion_apply.v0` for supported no-instruction requests,
- `client_history_exclusion_apply.v1` for supported instruction-bearing requests with explicit `client_instruction_source.v1` provenance,
- Phase 5-C4b content-free RelaySCN-facing cache-hit diagnostics projection,
- typed-parse candidate validation and content-free node projection,
- one-shot runtime-private typed-parse source consumption,
- default-off gated cache-writer planning and apply,
- Phase 5.5 stream-safety and TTS-handoff metadata construction through C4.

### Important limitations

Current runtime does not:

- infer v1 provenance from role, wording, or message position,
- semantically apply the C4b diagnostics projection to RelaySCN,
- parse arbitrary backend visible responses into typed instruction artifacts,
- trust frontend metadata as a typed-parse source,
- support parser-versioned cache lookup/write compatibility,
- reconstruct active tool transactions,
- directly mutate RelaySCN or RelaySOUL from client instruction evidence,
- deliver TTS adapter transport or execute TTS/audio/avatar behavior.

All apply-like paths remain behind explicit default-off and dry-run-first gates.

## Authority boundaries

```text
RelayLM runtime / safety policy
  highest execution and safety authority

RelaySOUL
  durable identity, values, worldview, and persona invariants

Durable OUTPUT_POLICY / RELATIONSHIP_ANCHOR
  approved long-lived expression and relationship policy

RelaySCN
  current situation, active role, task frame, temporary mode,
  participants, and scene-specific response constraints

Client instruction evidence
  low-trust source used to derive current-scene state
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

For a RelayLM-managed route, RelayLM extracts only bounded current evidence permitted by the active contract:

- the exact current user turn,
- explicitly selected current system/developer instruction evidence,
- request options and approved metadata,
- minimum active tool or multimodal transaction state once a dedicated contract supports it.

The current v0/v1 apply paths reconstruct a new managed message list. Active tool transactions remain blocked because the minimum chain is not yet reconstructed.

## Instruction identity and provenance

All supported client `system` and `developer` messages may participate in request-local normalization and identity. Identity content and hashes remain runtime-private.

Identity and provenance are separate:

```text
identity
  = which normalized instruction candidates exist

provenance
  = which candidates the frontend explicitly identifies
    as current instruction evidence for this request
```

Role, wording, content, and position do not establish provenance.

### Explicit v1 provenance

Instruction-bearing `client_history_exclusion_apply.v1` accepts only the reserved request-local control envelope:

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

Missing or invalid provenance blocks v1 actual apply. Unselected instruction candidates are excluded, including frontend summaries, memory notes, replayed persona blocks, and other system-role compatibility material.

The reserved top-level `relaylm` envelope is RelayLM control-plane input and is removed before managed backend forwarding.

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
- unrelated old tool results,
- opaque instruction-cache entry content,
- the reserved RelayLM control envelope.

The evidence builder owns canonical raw typed JSON and source-role labels. The managed compiler renderer owns escaping and the final rendered-size bound.

Client instruction evidence remains below RelayLM runtime/safety policy and approved persona authority. It cannot directly mutate RelaySOUL, persistence, tools, runtime policy, or safety policy.

## Existing and missing SOUL

### Existing SOUL

When an approved `SOUL.md` or RelaySOUL revision exists:

- RelayLM uses it as durable persona authority,
- current role and scene constraints may guide current behavior,
- client instructions do not overwrite the stable persona prefix,
- conflicts resolve in favor of runtime/safety policy and approved RelaySOUL identity,
- durable persona changes require proposal, validation, approval, revision, and rollback gates.

### Missing SOUL

When a managed route has no usable SOUL source, client instruction evidence may later support a safe temporary scene state for the current request, but it must not become fallback durable persona authority.

```text
SOUL missing
  + current client instruction evidence
  -> optional safe temporary RelaySCN state when supported
  -> durable persona remains missing
  -> separate RelaySOUL initialization/proposal path
```

Current managed profile compilation still requires configured approved profile sources. The raw system prompt must never be copied wholesale into `SOUL.md`.

## Durable promotion path

Durable identity fragments remain candidate evidence only.

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

## Normalization and cache identity

Before hashing, RelayLM should:

- combine current `system` and `developer` content in deterministic role/order sequence,
- normalize line endings,
- trim leading and trailing whitespace,
- normalize non-semantic repeated whitespace where safe,
- preserve meaningful Markdown, JSON, XML-like blocks, and punctuation,
- include an explicit empty marker when no instruction exists.

Current request-local identity is scoped by inputs equivalent to:

```text
normalized instruction candidates
+ route_model
+ character_id
+ instruction schema version
+ authority policy version
+ optional parser version
```

Changing instruction text, route, character, schema version, policy version, or parser version must change the cache scope. Identity content, hashes, keys, and paths remain runtime-private.

## Current cache-hit projection boundary

Phase 5-C4b consumes a validated cache lookup result and emits `client_instruction_relayscn_projection.v0` as a detached content-free `PipelineNodeResult`.

The projection may expose only bounded enum/count/boolean facts such as:

- hit/miss/blocked/skipped state,
- projected scene-type enum,
- role presence and source/scope classes,
- confidence bucket,
- context/participant/constraint counts,
- durable-candidate and blocked-kind counts,
- stable reason IDs.

It must not expose role names, settings, task text, participant names, constraint values, instruction text, cache bodies, hashes, paths, payloads, or response text.

C4b is diagnostics-only. It does not apply RelaySCN state, suppress v1 evidence, or mutate backend payloads.

## Current typed-parse and cache-writer boundary

Current C5 runtime plumbing accepts only a trusted in-process runtime-private typed-parse candidate. The one-shot source is consumed and cleared during `PipelineContext` construction so stale candidates cannot leak into later requests.

When enabled, writer planning consumes:

- request-local instruction identity,
- the validated typed-parse result,
- managed-route gate state,
- writer dry-run setting,
- cache root and maximum entry size.

With `client_instruction_cache_write_dry_run_only=true`, no file is written. With dry-run disabled, the writer may persist only after exact schema, policy, scope, source, and identity validation passes.

Current writer plumbing does not:

- parse backend visible text,
- accept arbitrary frontend metadata,
- extract a control envelope from a response,
- support non-null parser-version lookup/write under the current unversioned key,
- apply RelaySCN semantics,
- mutate backend or user-visible payloads.

## Target instruction interpretation path

A later trusted producer may extract and validate a separately versioned control artifact from the internal output boundary:

```text
visible response
  -> user-facing output path

validated instruction-control artifact
  -> strict typed parser
  -> cache candidate
  -> independent writer gate
  -> typed RelaySCN consumer
```

The target artifact must reject or strip:

- unknown keys and excessive nesting,
- raw prompt copies,
- secret-bearing URLs or paths,
- runtime/safety/tool authority claims,
- direct persistence or persona mutation requests.

Durable candidates remain candidates only and are never applied by the parser.

## RelayCTX Unpack and Phase 5.5 boundary

Current Phase 5.5 provides gated stream-safety and handoff-preparation behavior through C4. It can suppress detected internal sentinels and construct TTS-safe segmentation, handoff, and transport metadata behind explicit gates.

It does not implement the trusted client-instruction control-artifact producer described above and does not deliver adapter transport or execute TTS/audio/avatar behavior.

Required invariants:

- internal control content never reaches users, captions, TTS, or avatar speech after detection,
- malformed/missing control content does not invalidate otherwise valid visible output,
- cache write occurs only after schema, policy, scope, identity, and source validation,
- raw prompt or raw backend response text is never stored as the cache entry,
- durable candidates are never applied automatically.

## Failure and retry behavior

Visible-response delivery and cache mutation are independent outcomes.

```text
valid visible response
+ invalid or missing control artifact
  -> return visible response
  -> do not write cache
  -> record bounded failure
```

### Instruction conflicts with SOUL

```text
keep RelaySOUL identity
apply only compatible scene-role / scene-constraint elements when a typed consumer exists
block durable overwrite
record content-free conflict diagnostics
```

### Runtime or tool override attempt

```text
block the override fragment
retain compatible current-scene fragments only when a typed policy consumer permits it
```

### Active tool transaction

Until minimum-chain reconstruction exists:

```text
active tool transaction detected
  -> block managed apply
  -> do not forward an incomplete transaction
  -> do not use pass-through as implicit fallback
```

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
  -> managed context reconstruction
  -> exact backend-forward gate
```

`pass_through` is explicit delegation, not an emergency fallback for failed managed instruction handling.

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

Instruction evidence must never be placed above runtime/safety or approved persona authority.

## Current implementation sequence

```text
Current foundations
  canonicalization, identity, read-only lookup, preflight

Current managed apply
  v0 no-instruction
  v1 explicit-provenance instruction-bearing

Current cache observation
  C4b diagnostics-only RelaySCN-facing projection

Current typed-parse / writer plumbing
  trusted runtime-private source
  default-off validation and writer gate

Current output-safety preparation
  Phase 5.5 B2-C4 gated suppression and handoff metadata

Still deferred
  trusted response control-artifact producer
  parser-versioned cache compatibility
  semantic RelaySCN apply from cache interpretation
  active tool-chain reconstruction
  RelaySOUL apply/revision execution
```

## Diagnostics

Content-free diagnostics may expose:

- instruction presence and role counts,
- identity preparation ready/blocked state,
- cache lookup class without key/hash/path/content,
- evidence-block presence and bounded size class,
- raw instruction message forwarded=false,
- C4b projection status and bounded enum/count fields,
- typed-parse and cache-write status/reason classes,
- payload mutation and exact-forward booleans,
- bounded stable reason IDs.

Diagnostics must not copy instruction text, normalized text, hashes, keys, cache paths, scene semantic values, response text, typed-parse bodies, or arbitrary cache entries.

## Required smoke coverage

Current coverage must prove:

1. prior history and raw instruction objects are not forwarded as authoritative message objects after successful apply,
2. the exact current user message remains present,
3. v1 provenance selection and rejection are deterministic,
4. at most one bounded escaped low-trust evidence block is emitted,
5. runtime/safety and approved SOUL remain above instruction evidence,
6. valid v1 actual apply reaches the backend only through the exact selected candidate,
7. invalid or missing v1 provenance fails closed without restoring history,
8. C4b projection remains content-free and diagnostics-only,
9. C5 runtime-private source is one-shot and writer gates remain fail-closed,
10. dry-run writer behavior performs no filesystem mutation,
11. stream-safety metadata does not imply TTS/audio/avatar execution,
12. pass-through retains explicit delegated behavior,
13. trace, node results, public errors, and exception projections remain content-free.

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
  a trusted output artifact producer, semantic RelaySCN apply,
  broader transaction compatibility, and complete default-on managed reconstruction.
```
