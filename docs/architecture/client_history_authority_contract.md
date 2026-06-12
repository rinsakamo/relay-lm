# Client History Authority Contract

## Purpose

This document defines how RelayLM treats conversation history supplied by frontends such as OpenWebUI, AI VTuber applications, chat UIs, and other OpenAI-compatible clients.

It is a cross-cutting companion to:

- `pipeline_responsibility_design.md`
- `pipeline_implementation_plan.md`
- `ai_vtuber_pipeline_profile.md`
- `context_packing_design.md`
- `relayctx_wake_loop_design.md`

The contract fixes one source-of-truth rule:

```text
Client-provided conversation history is not authoritative context.
RelayLM is the authority that constructs the backend-bound context.
```

## Motivation

Most OpenAI-compatible frontends resend their visible conversation history on every request.

Examples include:

- OpenWebUI,
- AI VTuber frontends,
- browser chat applications,
- agent/chat SDKs,
- clients that maintain their own summaries or memory notes.

If RelayLM forwards this history unchanged while also injecting RelayCTX, RelayMEM, RelaySOUL, and scene state, the backend may receive duplicate or contradictory context.

Typical failure modes include:

- duplicate recent turns,
- frontend-generated summaries conflicting with RelayCTX state,
- stale assistant messages being treated as current truth,
- deleted or superseded information reappearing,
- client persona/system prompts overriding RelaySOUL,
- repeated memory blocks consuming the token budget,
- prompt-injection text surviving inside old assistant or user messages,
- unpredictable KV-prefix layout across different frontends.

Therefore, frontend history is input evidence and compatibility data, not the canonical backend context.

## Core authority rule

For normal conversation requests, RelayLM should:

1. preserve the original client payload for request-local diagnostics and compatibility inspection,
2. extract the active current-turn input,
3. exclude prior client conversation messages from the backend-bound message list,
4. construct a new message list from RelayLM-owned state,
5. send only that reconstructed payload to the Main LLM backend.

Conceptually:

```text
Client payload
  - client system prompt
  - previous user messages
  - previous assistant messages
  - client summary / memory note
  - current user turn

  -> active-turn extraction
  -> client-history exclusion
  -> RelayCTX Repack

Backend payload
  - RelayLM-owned stable system / developer prefix
  - approved RelaySOUL / policy state
  - RelaySCN / RelayEMO constraints
  - selected RelayCTX working context
  - selected RelayMEM retrieval blocks
  - minimum required active transaction state
  - current user turn
```

The backend-bound payload must be reconstructed, not produced by copying the client message list and deleting a few known fields.

## PipelineContext boundary

`PipelineContext.original_payload` and `PipelineContext.forwarded_payload` have different authority.

```text
original_payload
  = exact client request retained for request-local inspection,
    compatibility checks, and diagnostics metadata

forwarded_payload
  = RelayLM-constructed backend request and the only payload
    permitted to reach the Main LLM backend
```

Any step that replaces the backend-bound payload should continue to use `PipelineContext.replace_forwarded_payload(...)` with an explicit mutation reason.

Suggested replacement reasons include:

```text
client_current_turn_extracted
client_history_excluded
relayctx_context_repacked
active_tool_transaction_preserved
active_multimodal_turn_preserved
```

## Active current-turn extraction

For ordinary text chat, the active turn is normally the latest valid `user` message.

RelayLM should preserve the whole current message object, not only its text string, because the current message may contain structured content parts.

Example:

```json
{
  "role": "user",
  "content": [
    {"type": "text", "text": "この画像を見て"},
    {"type": "image_url", "image_url": {"url": "..."}}
  ]
}
```

The text and image parts belong to one active user turn and should remain together.

If no valid active user turn can be extracted, RelayINT or request compatibility handling should block, clarify, or fail closed instead of silently forwarding arbitrary old history.

## Default client-message policy

### Preserve for current-turn processing

- the latest valid user message,
- all content parts belonging to that message,
- request-level generation and compatibility options,
- explicitly approved current-turn metadata,
- the minimum state required for an active tool or multimodal transaction.

### Do not forward by default

- previous client `user` messages,
- previous client `assistant` messages,
- frontend-generated summaries,
- frontend-generated memory notes,
- frontend-replayed persona blocks,
- old tool results that are not part of the active transaction,
- old internal markers or diagnostic text,
- client system prompts when RelaySOUL / route policy is authoritative.

Client-supplied system or developer messages may be inspected as low-trust transient hints only when an explicit route policy allows it. They must not silently become RelaySOUL or overwrite the stable RelayLM prefix.

## Exceptions requiring minimal transaction preservation

The default rule is not equivalent to blindly keeping only one array element. Some active requests require a minimal message chain.

### Active tool transaction

A current tool loop may require:

```text
assistant tool_calls
  -> tool result
  -> current user continuation or runtime continuation
```

RelayLM may preserve the minimum chain needed to keep that active transaction valid.

It should not preserve unrelated earlier conversation history merely because tools are present.

### Multimodal current turn

All content parts of the current user turn should be preserved together.

Previous images or attachments should not be forwarded unless RelayCTX explicitly selects them as current context and the backend/request contract supports them.

### Protocol compatibility

Some clients may send message structures needed for JSON mode, tool calling, or provider-specific compatibility.

RelayLM should preserve only the minimum protocol state required for the current request. Compatibility preservation must remain separate from semantic conversation-history authority.

## RelayCTX Repack responsibility

RelayCTX Repack is responsible for the final context seen by the Main LLM.

After active-turn extraction, it should construct the backend payload from:

- stable system/developer prefix,
- approved persona and policy state,
- current scene state,
- selected working-memory blocks,
- selected long-term memory retrieval,
- minimum recent context chosen by RelayLM,
- current user input,
- minimum active transaction state when required.

RelayCTX should not assume that the frontend's visible history is already an acceptable context window.

The UI may own display history. RelayLM owns inference context.

```text
UI display history != backend inference context
```

## Context and memory source of truth

When this contract is enabled:

```text
Frontend
  owns display state, input widgets, avatars, and local UX history.

RelayLM
  owns context selection, working-memory state, memory retrieval,
  persona continuity, scene state, and backend payload construction.

Main LLM backend
  receives only the RelayLM-repacked context.
```

Frontend memory or summarization should be disabled where possible.

If a frontend cannot disable its own history resend behavior, RelayLM should neutralize that history at the proxy boundary rather than requiring frontend-specific patches.

This applies directly to:

- OpenWebUI,
- AITuber OnAir,
- Open-LLM-VTuber,
- other OpenAI-compatible chat frontends.

## AI VTuber profile application

For the AI VTuber profile, the normal input path becomes:

```text
Frontend text / comment / device speech-to-text result
  -> client payload with frontend-visible history
  -> RelayLM active-turn extraction
  -> prior frontend history excluded
  -> RelayINT / RelayMEM Retrieval / RelayCTX Repack
  -> Main LLM
```

AITuber or streaming frontends may retain recent messages for display, moderation, comment selection, or viewer UX. Those messages are not automatically authoritative Main LLM context.

Comment-selection metadata, viewer identity, relationship state, and current event metadata may be accepted as explicit current-turn inputs when a route contract defines them. They should not be smuggled into inference through replayed chat history.

## Diagnostics contract

RelayLM should record that client history was replaced without copying the full ignored content into runtime artifacts.

Suggested diagnostics:

```json
{
  "client_history_policy": "replace_with_relayctx",
  "client_message_count": 27,
  "client_role_counts": {
    "system": 1,
    "user": 13,
    "assistant": 13
  },
  "client_history_messages_excluded": 26,
  "active_turn_messages_preserved": 1,
  "active_tool_transaction_preserved": false,
  "active_multimodal_turn_preserved": false,
  "forwarded_context_source": "relayctx_repack"
}
```

Diagnostics should prefer counts, booleans, role distributions, and replacement reasons over raw message content.

This reduces artifact growth and avoids duplicating potentially sensitive conversation history.

## Failure behavior

### No active turn

```text
No valid current user turn
  -> do not forward old history as a substitute
  -> emit blocked / invalid-request diagnostics
  -> clarify or fail closed according to request compatibility policy
```

### Active transaction cannot be reconstructed

```text
Tool or multimodal transaction required
  -> minimum valid chain cannot be determined
  -> do not create a malformed backend payload
  -> block or use compatibility fallback
```

### RelayCTX Repack failure

```text
Active turn extracted
  -> RelayCTX cannot produce a valid backend payload
  -> do not fall back to raw client history
  -> use the defined safe fallback / failure route
```

Raw client history must not become an emergency fallback because that would bypass the context-authority boundary precisely when the pipeline is least reliable.

## Implementation phase mapping

This contract is part of Phase 3 RelayCTX Repack boundary hardening.

Required implementation order:

```text
1. Add deterministic active-turn extraction.
2. Preserve original_payload separately.
3. Construct a fresh backend-bound message list.
4. Exclude prior client history by default.
5. Add minimum tool / multimodal transaction preservation.
6. Add replacement diagnostics and smoke coverage.
7. Only then expand profile-specific context assembly.
```

Phase 3 should not be considered behaviorally complete until frontend-supplied history is prevented from bypassing RelayCTX Repack.

## Required smoke coverage

Minimum smoke cases:

1. OpenWebUI-style full history plus current user turn results in only RelayLM-selected context and the current turn reaching the backend.
2. Client system prompt does not override RelayLM-owned system/persona prefix.
3. Frontend summary and memory-note messages are excluded.
4. Current multimodal user content remains intact.
5. Minimum active tool transaction state is preserved when required.
6. Unrelated old tool messages are excluded.
7. Missing current user turn fails closed.
8. Repack failure does not fall back to raw client history.
9. Diagnostics contain counts and policy state without copying ignored message content.
10. Existing pass-through routes remain explicitly exempt only when their route contract intentionally delegates context authority to the client.

## Route policy and explicit exceptions

The default RelayLM-managed conversation route should use:

```text
client_history_policy = replace_with_relayctx
```

An explicit pass-through or compatibility route may use:

```text
client_history_policy = trust_client
```

but only when that route intentionally delegates context ownership to the client.

The exception must be visible in route configuration and diagnostics. It must not arise implicitly because RelayCTX Repack failed or was skipped.

## Final boundary

```text
The frontend may remember what it displayed.
RelayLM decides what the Main LLM is allowed to remember for the current turn.
```
