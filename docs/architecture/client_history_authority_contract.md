# Client History Authority Contract

## Purpose

This document defines how RelayLM treats conversation history and message arrays supplied by frontends such as OpenWebUI, AI VTuber applications, browser chat UIs, and other OpenAI-compatible clients.

It is a cross-cutting companion to:

- `client_instruction_authority_contract.md`,
- `pipeline_responsibility_design.md`,
- `pipeline_implementation_plan.md`,
- `phase5c4a_instruction_bearing_managed_apply_handoff.md`,
- `ai_vtuber_pipeline_profile.md`,
- `context_packing_design.md`,
- `relayint_mvp_design.md`,
- `scene_lifecycle_design.md`.

The contract fixes one source-of-truth rule:

```text
Client-provided messages are not authoritative backend context.
RelayLM constructs the backend-bound context.
```

## Status interpretation

Current implementation provides content-free canonicalization, runtime-private instruction identity, read-only cache lookup, history-exclusion preflight, and the default-off no-instruction `client_history_exclusion_apply.v0` path.

The active next slice is Phase 5-C4a instruction-bearing managed apply. Cache-hit RelaySCN projection is deferred to Phase 5-C4b, typed instruction parsing/cache write to Phase 5-C5, and Stream Unpack to Phase 5.5.

Target cache behavior described below remains authoritative design intent, but it is not current apply behavior until an implemented producer, consumer, and smoke contract exist.

## Motivation

Most OpenAI-compatible frontends resend their visible conversation history and system prompt on every request.

Typical client payloads contain:

- client `system` and `developer` messages,
- previous `user` messages,
- previous `assistant` messages,
- frontend summaries or memory notes,
- old tool results,
- the current user turn.

If RelayLM forwards that array unchanged while also injecting RelayCTX, RelayMEM, RelaySOUL, and RelaySCN state, the backend may receive duplicate, stale, or contradictory context.

Failure modes include:

- duplicate recent turns,
- frontend-generated summaries conflicting with RelayCTX state,
- stale assistant messages being treated as current truth,
- deleted or superseded information reappearing,
- replayed client prompts competing with RelaySOUL or RelaySCN,
- repeated memory blocks consuming token budget,
- old prompt-injection content surviving in history,
- unstable KV-prefix layout across frontends.

Therefore, the client message array is request evidence and compatibility data, not the canonical backend context.

## Shared client-message canonicalization boundary

RelayLM-managed routes should canonicalize the full client message array before RelayCTX Repack.

```text
client messages
  - system / developer
  - previous user / assistant history
  - frontend summary / memory
  - old tool results
  - current user turn

  -> client message canonicalization
  -> extract current request evidence
  -> exclude client-owned context
  -> reconstruct backend messages
```

The canonicalizer preserves only what is needed for the current request:

- latest valid user turn,
- all content parts belonging to that turn,
- current client system/developer instruction evidence,
- request-level options and approved metadata,
- minimum active tool or multimodal transaction state.

The canonicalizer does not treat preserved evidence as already-valid backend context. Each preserved element is routed to the subsystem that owns its meaning.

```text
current user turn
  -> RelayINT / RelayCTX

current client instruction evidence
  -> normalize / hash / cache lookup
  -> RelaySCN

active tool/multimodal chain
  -> compatibility transaction handling
```

## Core authority rule

For normal RelayLM-managed conversation requests, RelayLM should:

1. preserve the exact client payload as `original_payload` for request-local inspection,
2. extract the active user turn,
3. extract current system/developer instruction evidence,
4. resolve instruction evidence through the client-instruction hash/cache flow,
5. preserve only the minimum active transaction state,
6. exclude prior client history and raw client instructions from the normal backend-bound message list,
7. construct a new message list from RelayLM-owned state,
8. send only that reconstructed payload to the Main LLM backend.

Conceptually:

```text
Client payload
  -> current turn extraction
  -> instruction evidence extraction
  -> history exclusion
  -> instruction hash/cache resolution
  -> RelaySCN
  -> RelayCTX Repack

Backend payload
  - RelayLM runtime / safety policy
  - approved RelaySOUL and durable policies
  - normalized RelaySCN state
  - selected RelayCTX working context
  - selected RelayMEM blocks
  - minimum active transaction state
  - current user turn
```

The backend-bound payload must be reconstructed. It must not be produced by copying the client message list and deleting a few known fields.

## PipelineContext boundary

`PipelineContext.original_payload` and `PipelineContext.forwarded_payload` have different authority.

```text
original_payload
  = exact client request retained for request-local inspection,
    compatibility checks, and content-free diagnostics derivation

forwarded_payload
  = RelayLM-constructed backend request and the only payload
    permitted to reach the Main LLM backend
```

Any step that replaces the backend-bound payload should use `PipelineContext.replace_forwarded_payload(...)` with an explicit mutation reason.

Suggested reasons:

```text
client_current_turn_extracted
client_instruction_extracted
client_instruction_cache_hit
client_instruction_first_pass_added
client_history_excluded
relayctx_context_repacked
active_tool_transaction_preserved
active_multimodal_turn_preserved
```

## Current user-turn extraction

For ordinary text chat, the active turn is normally the latest valid `user` message.

RelayLM should preserve the whole current message object, not only its text string, because a current message may contain structured content parts.

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "この画像を見て"},
    {"type": "image_url", "image_url": {"url": "..."}}
  ]
}
```

The text and image parts belong to one active turn and should remain together.

If no valid active user turn can be extracted, RelayINT or compatibility handling should block, clarify, or fail closed instead of forwarding arbitrary old history.

## Current instruction evidence

Client `system` and `developer` messages cross the same canonicalization boundary as history, but they have one special pre-exclusion use.

Current implemented preparation:

```text
current system/developer instruction
  -> normalize and hash in request-local identity
  -> optional read-only cache lookup
  -> no current cache projection apply or cache write
```

Active Phase 5-C4a migration:

```text
supported instruction-bearing request
  -> at most one bounded escaped low-trust evidence block
  -> prior history and raw instruction message objects excluded
```

Target optimization after Phase 5-C4b:

```text
validated cache hit
  -> use allowlisted normalized RelaySCN projection
  -> suppress raw instruction evidence

cache miss
  -> permit one bounded first-pass interpretation
  -> validate a separately versioned control artifact
  -> write only through a later independent cache gate
```

The raw instruction is never persisted as scene state or SOUL. The canonical instruction behavior is defined in `client_instruction_authority_contract.md`.

## Default client-message policy

### Preserve for current-request processing

- latest valid user message,
- all current-turn multimodal content parts,
- current system/developer instruction evidence for identity and resolution,
- request-level generation and compatibility options,
- explicitly approved current-turn metadata,
- minimum active tool or multimodal transaction chain.

### Do not forward by default

- previous client `user` messages,
- previous client `assistant` messages,
- frontend-generated summaries,
- frontend-generated memory notes,
- frontend-replayed persona blocks,
- old tool results unrelated to the active transaction,
- old internal markers or diagnostic text,
- raw client system/developer message objects after instruction handling.

A pass-through route is the explicit exception. A failed RelayCTX Repack or failed instruction parse must not implicitly restore raw client context.

## Minimum transaction exceptions

The default policy is not equivalent to keeping only one message array element.

### Active tool transaction

A current tool loop may require:

```text
assistant tool_calls
  -> tool result
  -> current user or runtime continuation
```

RelayLM may preserve the minimum valid chain needed to keep the active transaction coherent. Unrelated earlier history remains excluded.

Until that reconstruction contract is implemented, managed apply must explicitly block active tool transactions rather than forward an incomplete chain.

### Current multimodal turn

All content parts of the current user turn should remain together.

Previous images or attachments should not be forwarded unless RelayCTX explicitly selects them and the backend/request contract supports them.

### Protocol compatibility

JSON mode, tool calling, or provider-specific structures may require bounded protocol state. Compatibility preservation is separate from semantic history authority.

## RelayCTX Repack responsibility

RelayCTX Repack is responsible for the final context seen by the Main LLM.

It should construct the backend request from:

- stable runtime/safety prefix,
- approved persona and durable policy state,
- normalized current scene state,
- selected working-memory blocks,
- selected long-term memory retrieval,
- minimum recent context chosen by RelayLM,
- current user input,
- minimum active transaction state.

During Phase 5-C4a, RelayCTX may include one bounded `client_instruction_evidence` block for supported instruction-bearing correctness whether cache lookup is disabled, misses, or reports a hit. This is a migration behavior, not the target cache optimization.

After validated cache projection exists, raw evidence should appear only on an unknown instruction identity requiring first-pass interpretation.

```text
UI display history != backend inference context
```

## Context source of truth

```text
Frontend
  owns display history, input widgets, avatars, and UX state

RelayLM
  owns instruction resolution, scene state, context selection,
  memory retrieval, persona continuity, and backend payload construction

Main LLM backend
  receives only RelayLM-repacked context
```

Frontend memory or summarization should be disabled where possible. When it cannot be disabled, RelayLM should neutralize it at the proxy boundary instead of requiring frontend-specific patches.

This applies directly to OpenWebUI, AITuber OnAir, Open-LLM-VTuber, and other OpenAI-compatible frontends.

## Diagnostics contract

RelayLM should record replacement behavior without copying ignored content.

```json
{
  "client_history_policy": "replace_with_relayctx",
  "client_message_count": 27,
  "client_role_counts": {
    "system": 1,
    "user": 13,
    "assistant": 13
  },
  "client_history_messages_excluded": 25,
  "active_turn_messages_preserved": 1,
  "client_instruction_messages_extracted": 1,
  "client_instruction_identity_present": true,
  "client_instruction_cache_status": "hit",
  "raw_client_instruction_message_forwarded": false,
  "low_trust_instruction_evidence_present": true,
  "active_tool_transaction_preserved": false,
  "active_multimodal_turn_preserved": false,
  "forwarded_context_source": "relayctx_repack"
}
```

Diagnostics should prefer counts, booleans, role distributions, source classes, and replacement reasons over raw message content. Hash values and semantic instruction content remain runtime-private under the current content-free audit contract.

## Failure behavior

### No active turn

```text
no valid current user turn
  -> do not use old history as a substitute
  -> emit blocked / invalid-request diagnostics
  -> clarify or fail closed
```

### Instruction parse failure

```text
valid visible response + invalid instruction artifact
  -> preserve visible response
  -> do not write instruction cache
  -> do not restore raw client history/system context
```

### Active transaction cannot be reconstructed

```text
required tool/multimodal chain cannot be determined
  -> do not create a malformed backend payload
  -> block or use an explicit compatibility route
```

### RelayCTX Repack failure

```text
current request evidence extracted
  -> RelayCTX cannot produce a valid backend payload
  -> do not fall back to raw client messages
  -> use defined safe failure/recovery behavior
```

Raw client messages must never become an emergency fallback because that would bypass the authority boundary precisely when the pipeline is least reliable.

## Implementation status and sequencing

Current implemented foundations:

```text
Phase 5-C1 / 5-C2 / 5-C3
  content-free canonicalization
  runtime-private instruction identity
  optional read-only cache lookup
  history-exclusion preflight

Phase 5-C1a compatibility slice
  no-instruction client_history_exclusion_apply.v0
  request-local runtime wiring
  backend-forward fail-closed gate
```

Active correctness slice:

```text
Phase 5-C4a
  instruction-bearing managed apply
  bounded escaped low-trust evidence
  current text/multimodal turn preservation
  active transaction preservation or explicit block
```

Deferred optimization and output work:

```text
Phase 5-C4b
  validated cache-hit RelaySCN projection

Phase 5-C5
  typed instruction artifact validation and cache write

Phase 5.5
  streaming control-envelope suppression / Stream Unpack
```

Later phase identifiers do not make target behavior current. Detailed sequencing is authoritative only in `pipeline_implementation_plan.md`.

## Required smoke coverage

Current and active correctness coverage must prove:

1. OpenWebUI-style full history plus current user turn reaches the backend only through RelayLM-selected context.
2. Client system/developer messages are extracted but not forwarded as authoritative message objects.
3. Supported instruction-bearing requests use at most one bounded escaped low-trust evidence block.
4. Frontend summary and memory-note messages are excluded.
5. Current multimodal user content remains intact.
6. Active tool transactions are preserved by an implemented contract or explicitly blocked.
7. Unrelated old tool messages are excluded.
8. Missing current user turn fails closed.
9. Instruction handling or RelayCTX failure does not restore raw client messages.
10. Diagnostics contain only typed content-free policy state.
11. Pass-through routes remain explicit exceptions only.
12. Cache disabled/miss/hit states do not inject opaque cache content before Phase 5-C4b.

Target cache and output phases must additionally prove validated cache projection, typed artifact validation/write, and non-leaking Stream Unpack when those phases are implemented.

## Route policy and exceptions

Default managed route target:

```text
client_history_policy = replace_with_relayctx
client_instruction_policy = relay_scn_first
```

Explicit pass-through route:

```text
client_history_policy = trust_client
client_instruction_policy = trust_client
```

These policy names describe the authority model and are not necessarily current configuration fields. Exceptions must be visible in route configuration and diagnostics. They must not arise implicitly because a managed pipeline step failed or was skipped.

## Final boundary

```text
The frontend may remember what it displayed and resend any message array.
RelayLM decides which current evidence is accepted and reconstructs
what the Main LLM is allowed to see for the current turn.
```