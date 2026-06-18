# Client History Authority Contract

## Purpose

This document defines how RelayLM treats message arrays supplied by OpenAI-compatible frontends.

The source-of-truth rule is:

```text
Client-provided messages are request evidence and compatibility data.
They are not authoritative backend context.
RelayLM constructs the backend-bound context on managed routes.
```

## Current status

Current implementation includes:

- content-free client-message canonicalization dry-run,
- runtime-private client-instruction identity,
- read-only instruction-cache lookup,
- history-exclusion preflight,
- `client_history_exclusion_apply.v0` for supported no-instruction requests,
- `client_history_exclusion_apply.v1` for supported instruction-bearing requests.

Cache-hit RelaySCN projection, typed instruction parsing/cache write, active tool-chain reconstruction, and Stream Unpack remain later work.

## Client-message authority boundary

Typical frontend payloads may include:

- client system/developer messages,
- previous user/assistant history,
- frontend summaries or memory notes,
- replayed persona blocks,
- old tool results,
- the current user turn.

Managed routes must not treat this array as canonical backend context. RelayLM extracts bounded current evidence, applies subsystem-owned validation, and reconstructs the backend payload.

## PipelineContext boundary

```text
original_payload
  = exact client request retained request-locally for validation

forwarded_payload
  = RelayLM-constructed backend request and the only payload
    permitted to reach the managed Main LLM backend
```

Every backend-bound replacement uses `PipelineContext.replace_forwarded_payload(...)` with an explicit reason.

## Current user turn

For ordinary chat, the active turn is the latest valid `user` message. RelayLM preserves the entire message object, not merely extracted text, so supported multimodal parts remain together.

If no valid current user turn exists, managed apply fails closed.

## Client instruction identity

All supported client `system` and `developer` messages may participate in request-local normalization and identity. This identity is content-bearing and runtime-private. It is not itself permission to forward every candidate.

Identity and provenance are separate:

```text
identity
  = which normalized system/developer candidates exist

provenance
  = which identity candidates the frontend explicitly identifies
    as current instruction evidence for this request
```

Role, content, and message position do not establish provenance.

## Explicit instruction provenance

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

Missing or invalid provenance blocks v1 actual apply.

Unselected system/developer candidates are excluded from the v1 evidence block. This is the required boundary for frontend summaries, frontend memory notes, replayed persona blocks, and other system-role compatibility material that is not explicitly identified as current instruction evidence.

The reserved top-level `relaylm` envelope is RelayLM control-plane input and is removed before managed backend forwarding. Explicit pass-through routes remain client-owned and unchanged.

## Managed backend construction

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

## Evidence rendering and authority

The evidence builder emits canonical raw typed JSON with explicit source-role labels. The managed compiler renderer escapes the evidence and enforces the rendered-size bound immediately before final render.

Client instruction evidence is always below RelayLM runtime/safety policy and approved persona authority. It cannot directly mutate RelaySOUL, persistence, tools, runtime policy, or safety policy.

## Active transaction exceptions

An active tool transaction may require assistant tool-call and tool-result continuity. Phase 5-C4a does not reconstruct that minimum chain, so such requests remain blocked rather than partially forwarded.

Compatible current multimodal user content is preserved as one current turn.

## Backend-forward rule

History-exclusion apply remains default-off and dry-run-only by default.

For explicit actual apply on a managed route:

- only an exact typed `applied` result may reach the backend,
- v1 additionally requires that the adapter receive the exact selected candidate,
- downstream payload mutation causes backend blocking,
- failure never restores raw client history as fallback.

## Diagnostics and persistence

Runtime-private identity, provenance selection, and payload candidates may contain content. Persisted audit, trace, public errors, and node results contain only bounded status values, counts, booleans, source mode, and reason IDs.

They do not contain:

- instruction or user text,
- source index values,
- hashes or cache keys,
- raw messages or payload candidates,
- cache bodies,
- paths or URLs derived from private runtime state.

## Safe defaults

```text
client_history_exclusion_apply_enabled=false
client_history_exclusion_apply_dry_run_only=true
```

No client-authority migration may silently enable actual apply, infer provenance from message wording, restore prior history after failure, or promote instruction evidence into durable persona authority.
