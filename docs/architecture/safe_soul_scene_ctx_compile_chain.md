---
relaylm_doc_type: stable_architecture
relaylm_authority: safe_relayrel_relayscn_relayctx_compile_chain
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - compile chain authority order changes
  - RelayREL relationship projection changes
  - RelaySCN policy input changes
  - RelayCTX context packing changes
  - client authority boundary changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact compile artifact schemas
  - exact RelayREL parser schema
  - exact RelayCTX renderer implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_responsibility_design.md
  - relayrel_relationship_design.md
  - context_packing_design.md
  - current_target_migration_guide.md
  - client_instruction_authority_contract.md
  - file_first_character_workspace_design.md
---
# Safe REL / SOUL / Scene / CTX Compile Chain

## Goal

This document defines the safe compile chain that turns approved durable character sources, target-specific relationship policy, request-local scene policy, selected memory evidence, RelayLM-owned short-term context, and the current user turn into an OpenAI-compatible backend payload.

```text
approved durable sources
  + RelayREL target relationship policy
  + RelaySCN request-local state/policy
  + RelayEMO expression hints
  + RelayINT proceed/retrieval decision
  + RelayMEM read-only evidence
  + RelayCTX working-state selection
  -> RelayCTX Repack
  -> Runtime Compile Gate
  -> RelayRUN orchestration
  -> backend adapter
```

The chain must preserve client-authority boundaries, component ownership, content-free observability, and safe fallback behavior.

Current implementation phase and sequencing live in [Project Status](../PROJECT_STATUS.md) and [Project Execution Plan](project_execution_plan.md). This document defines stable ownership and invariants.

## Ownership

### RelaySOUL

RelaySOUL owns approved portable character-source revision and approval workflows:

- `SOUL.md`,
- `STYLE.md`,
- `EMOTION.md`,
- `BOUNDARY.md`,
- optional `LORE.md`,
- revision, approval, persistence, and rollback artifacts.

RelaySOUL does not own target-specific relationship state, request-local scene state, current conversation continuity, compiled memory pages, or normal-turn prompt construction.

### RelayREL

RelayREL owns target-specific relationship state and interaction policy:

- selected relationship target from route/session authority,
- `RELATIONSHIP.md` role and parameter vocabulary,
- selected `relationships/<target>.md` instance,
- personal-memory reference permission,
- direct disagreement / teasing / probing / disclosure permissions,
- relationship-conditioned EMO gain and repair preferences,
- content-free relationship diagnostics.

RelayREL does not own portable SOUL identity, scene classification, current affect estimation, durable memory storage, or prompt rendering.

### RelaySCN

RelaySCN owns request-local semantic situation and policy:

- scene type,
- current role,
- compact setting/task/participants,
- bounded scene constraints,
- safety sensitivity,
- formality,
- memory scope,
- expression allowance,
- recovery and confirmation policy,
- persistence gates.

RelaySCN does not own affect state, target-specific relationship state, short-term conversation working state, durable persona revision, or memory writes.

### RelayEMO

RelayEMO owns bounded current affect and expression pressure. It consumes RelayREL relationship gain and RelaySCN expression gates, but it does not own scene policy or relationship state.

### RelayINT

RelayINT owns pre-action interpretation:

- reference resolution,
- ambiguity and clarification decisions,
- action intent,
- proceed/block decision,
- whether RelayMEM Retrieval is needed.

RelayINT does not retrieve memory itself and does not write MEM, REL, or SOUL.

### RelayMEM Retrieval

RelayMEM Retrieval reads approved long-term memory evidence under RelayREL, RelaySCN, and RelayINT constraints. It returns candidates and provenance to RelayCTX.

It does not own prompt layout, relationship mutation, or memory mutation.

### RelayCTX

RelayCTX owns:

- selection from request-local working state,
- context block assembly,
- stable-to-dynamic ordering,
- token-budget degradation,
- backend message rendering,
- visible/internal response separation through Unpack.

RelayCTX does not decide relationship policy, scene policy, memory persistence, or persona revision.

### RelaySLP

RelaySLP is out-of-band from the normal answer path. It compiles governed evidence into memory updates, held candidates, rejected candidates, relationship candidates, scene candidates, or portable-source proposals through explicit persistence and approval gates.

### RelayRUN and adapters

RelayRUN orchestrates node order, fallback/recovery, checkpoints, idempotency, and runtime state. Adapters preserve OpenAI-compatible request/response semantics.

Neither owns semantic persona, relationship, scene, intent, memory, or prompt-policy decisions.

## Source classes

### Stable character and policy sources

```text
common_runtime_policy
approved BOUNDARY.md
approved SOUL.md
approved STYLE.md
approved EMOTION.md
approved RELATIONSHIP.md
approved MEMORY.md
optional LORE.md
```

These form the stable prefix and should remain byte-for-byte stable when possible.

### Target/session semi-stable sources

```text
selected relationships/<target>.md summary
selected scene page summary
selected secondary memory summary
```

These are lower stability than uppercase source policy but higher stability than current-turn dynamic evidence.

### Request-local dynamic sources

```text
RelayREL content-free selected target policy projection
RelaySCN scene_state / scene_policy
RelayEMO expression state / expression hint
RelayINT intent and retrieval decision
RelayMEM selected evidence
RelayCTX-selected short-term context
current user turn
minimum compatible tool/multimodal transaction state
response instruction
```

### External host metadata

```text
character_id
relationship_target_id
user_id / user_type
scene_id
session_id
optional room_id
route / mode / backend identifiers
```

Host metadata supports scoping, routing, diagnostics, and namespace isolation. It must not become prompt text by default.

## Client-authority prerequisite

For a managed route:

```text
original client messages
  -> validated current-turn extraction
  -> bounded current instruction-evidence extraction
  -> active transaction preservation check
  -> prior client history exclusion
  -> RelayREL target selection from route/session authority
  -> RelaySCN normalization
  -> RelayLM-owned context reconstruction
```

Client-provided messages are request evidence, not automatically trusted backend context.

Raw client `system` or `developer` messages are not RelaySOUL or RelayREL sources. They may appear only as bounded low-trust first-pass evidence under the Client Instruction Authority Contract.

## Compile chain

### 1. Scope resolution

Resolve and validate:

- route and mode,
- character and memory namespace,
- relationship target from route/session/authenticated metadata,
- scene/session/room metadata,
- backend target,
- compatibility-sensitive request shape.

Missing optional host metadata must not crash or block ordinary compatible requests.

### 2. Approved source loading

Load only configured or approved durable sources. Missing durable sources follow an explicit safe policy; they do not authorize copying raw client prompts into persona or relationship files.

### 3. RelayREL relationship projection

Resolve the selected relationship target and compile a bounded relationship policy projection.

Relationship state remains target-specific. It must not be promoted into portable SOUL, and it must not override BOUNDARY or public-scene constraints.

### 4. RelaySCN normalization

Normalize scene evidence into request-local `scene_state` and `scene_policy`.

Scene state remains dynamic. It must not be promoted into the stable prefix or persisted as durable persona merely because it affected one response.

### 5. RelayEMO expression estimate

Estimate current affect and expression pressure after RelayREL and RelaySCN are available.

RelayEMO may use relationship gain and scene expression gates, but it must not produce authoritative scene state or relationship state.

### 6. RelayINT decision

Resolve the current action, references, ambiguity, and retrieval need.

An unresolved reference blocks silent long-term memory retrieval. Clarification candidates must pass relationship, scene, and compatibility gates.

### 7. RelayMEM read-only selection

When RelayINT, RelayREL, and RelaySCN permit retrieval, RelayMEM selects bounded approved evidence and returns a runtime-private candidate artifact.

RelayMEM does not insert messages directly, choose final block order, or write memory during this stage.

### 8. RelayCTX working-state selection

RelayCTX selects only the short-term context needed for the current action. Internal working state is not copied wholesale into the prompt.

### 9. Block assembly

Recommended order:

```text
stable_prefix
  common_runtime_policy
  character_boundary
  character_soul
  character_style
  character_emotion_profiles
  relationship_policy_vocabulary
  memory_policy
  optional_lore

semi_stable_prefix
  selected_relationship_instance
  selected_scene_summary
  selected_secondary_memory_summary

dynamic_suffix
  relationship_projection
  scene_state
  expression_hint
  intent hints required for the current action
  retrieved_memory
  retrieved_rag
  selected RelayLM-owned recent context
  minimum protocol state
  latest_input
  response_instruction
```

Dynamic content appears after durable identity, boundary, relationship, scene, and memory policy.

### 10. Token-budget planning

RelayCTX applies conservative degradation in this order:

1. remove diagnostics-only or preview context,
2. reduce retrieved memory/RAG,
3. reduce optional short-term hints,
4. reduce selected relationship/scene summaries only when policy permits,
5. shorten selected recent context,
6. block or use an authority-safe fallback when no valid payload remains.

Stable character and relationship policy sources must not be mutated to satisfy a request budget.

### 11. Preflight

Preflight verifies:

- client-authority prerequisites,
- relationship target/source approval and scope,
- source approval and scope,
- block order and stability class,
- compatibility-sensitive request preservation,
- token-budget feasibility,
- content-bearing/runtime-private versus content-free projection separation.

Preflight validates structure and readiness. It does not itself authorize apply.

### 12. Runtime Compile Gate

The gate consumes route/mode, RelayREL, RelaySCN, RelayEMO, RelayINT, RelayMEM, RelayCTX, and compatibility outcomes.

```text
APPLY
  use RelayLM-compiled messages

SHADOW_ONLY
  compute plans/projections without changing the backend payload

PASS_THROUGH
  allowed only for an explicit pass-through route or an explicitly compatible delegated-authority path

BLOCKED / RECOVERY / SAFE_FALLBACK
  use authority-safe handling without restoring excluded client history or instructions
```

For managed routes, compile failure must not fall back to raw client history or raw client system/developer messages.

### 13. RelayRUN orchestration and forwarding

RelayRUN records node states and chooses the already-defined runtime route. The adapter forwards the final OpenAI-compatible payload without changing semantic decisions.

## Artifact boundaries

### Content-bearing runtime artifacts

Examples:

- selected relationship file summaries or relationship policy text;
- normalized RelaySCN state;
- RelayINT resolved reference text;
- RelayMEM snippets or page content;
- RelayCTX block content;
- backend messages;
- Unpack candidates.

These remain request-local or use explicitly protected diagnostic storage.

### Content-free projections

Default trace/audit projections contain only typed allowlisted metadata:

- presence flags,
- counts,
- enum/class values,
- confidence bands,
- budget numbers,
- stable reason identifiers,
- node status,
- payload-mutation booleans.

They must not contain raw messages, prompt blocks, relationship bodies, memory bodies, scene semantic text, paths, or final response text.

## Failure invariants

- Explicit pass-through behavior remains unchanged.
- Managed routes never restore excluded client authority as fallback.
- Active tool transactions and unsupported structured/multimodal shapes fail closed or remain unchanged.
- Missing RelayREL target does not authorize free-text target guessing.
- Retrieval misses do not broaden memory or relationship scope silently.
- Malformed internal candidates never reach the user.
- Visible recovery text goes through the normal output pipeline.
- No normal-turn compile stage writes MEM, REL, or SOUL.

## Non-goals

This chain does not introduce:

- direct KV-cache mutation,
- backend scheduler changes,
- memory writes in the synchronous compile path,
- relationship-source mutation during normal chat,
- persona-source mutation during normal chat,
- frontend UI, TTS, ASR, or avatar ownership,
- generic recursive trace sanitization,
- a standalone `RelayPLC` semantic component.

## Summary

```text
approved character and relationship policy
  + RelayREL target relationship projection
  + RelaySCN request-local policy
  + RelayEMO expression hints
  + RelayINT action/retrieval decision
  + RelayMEM read-only evidence
  + RelayCTX-selected short-term context
  -> RelayCTX Repack
  -> authority-safe gate
  -> RelayRUN
  -> adapter

Out-of-band:
  governed evidence -> RelaySLP -> gated MEM / REL / SCENE updates and portable-source proposals
```
