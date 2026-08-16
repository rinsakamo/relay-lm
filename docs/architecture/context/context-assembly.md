---
relaylm_doc_type: subsystem_architecture
relaylm_authority: relayctx_context_selection_packing_and_backend_assembly_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: context
relaylm_update_trigger:
  - RelayCTX selection, packing, ordering, or budget responsibility changes
  - managed-route client-authority or history reconstruction changes
  - RelayREL, RelaySCN, RelayEMO, RelayINT, or RelayMEM context handoff changes
  - backend-bound context privacy or content-free diagnostics boundaries change
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact context artifact, message, block, token-budget, cache, or renderer schemas
  - relationship, scene, affect, intent, memory, or durable-character semantic decisions
  - backend transport, model invocation, output finalization, or persistence implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../pipeline-responsibilities.md
  - ../runtime/request-response-pipeline.md
  - ../relationship/relationship-state.md
  - ../scene/scene-model.md
  - ../emotion/affect-modulation.md
  - ../memory/retrieval-and-grounding.md
  - ../memory/scene-memory-scope.md
  - ../privacy/protected-source-and-disclosure.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayCTX and runtime maintainers
  - memory, relationship, scene, emotion, intent, and backend integration maintainers
  - privacy, performance, and prompt-assembly reviewers
relaylm_authority_level: subsystem
---
# RelayCTX Context Assembly

## Purpose

This page is the canonical subsystem architecture for selecting, ordering, packing, and rendering the bounded context that RelayLM sends to a backend model on managed routes.

RelayCTX treats prompt construction as context compilation, not transcript concatenation.

Its stable responsibility is:

```text
approved durable character/runtime policy
  + target relationship policy
  + current scene policy
  + bounded affect/expression hints
  + intent/reference control
  + selected ordinary-memory evidence
  + RelayLM-owned short-term working state
  + current user turn
  -> smallest sufficient, authority-preserving backend context
```

RelayCTX does not decide relationship truth, scene identity, affect state, memory authority, durable persona, or persistence. It consumes the outputs of those owners and decides what bounded context is necessary for the current backend call.

## Managed-route authority boundary

Managed routes reconstruct backend context from RelayLM-owned authorities rather than replaying arbitrary client history.

Conceptually:

```text
client payload
  -> validate current turn
  -> extract bounded current instruction evidence
  -> preserve active protocol/tool transaction state
  -> exclude untrusted prior history by default
  -> resolve RelayLM-owned component artifacts
  -> RelayCTX assembly
```

Raw client `system` or `developer` messages are not fallback SOUL, relationship, scene, memory, or trusted history sources.

Explicit pass-through routes are a separate delegated-authority mode and are not redefined by this page.

## Upstream ownership arrives before packing

RelayCTX receives already-owned semantics after the applicable request-path stages.

The stable dependency order is:

```text
RelayREL
  -> RelaySCN
  -> RelayEMO
  -> RelayINT / reference-intent control
  -> exact ordinary-memory reader decision and Retrieval
  -> RelayCTX Repack
```

RelayCTX must not repair a missing upstream decision by reparsing raw user text as relationship, scene, affect, intent, memory, or durable-persona authority.

If an upstream authority is absent or invalid, packing degrades or omits that input according to its contract rather than inventing a replacement owner.

## Selection is not concatenation

RelayCTX may retain more working state than it sends to the model.

```text
RelayCTX working state
  current topic
  active task/question
  previous bounded decision
  referable items
  unresolved slots
  selected recent continuity metadata

backend-selected context
  only the subset required for this request
```

State being present in RAM, a session cache, or a working artifact does not imply that it belongs in every prompt or that it may be persisted durably.

## Smallest sufficient context

A token budget is an upper bound, not a target.

RelayCTX prefers the smallest sufficient context that preserves correctness, character continuity, authority, and protocol compatibility.

Stable selection priority is:

1. preserve required runtime/safety and approved durable character anchors;
2. preserve protocol/tool/multimodal state required for a valid transaction;
3. include the selected relationship, scene, affect, and intent guidance needed for the current action;
4. include selected short-term continuity needed to understand the current request;
5. include ordinary-memory evidence only when the exact reader/retrieval path selected it;
6. stop adding context when the request can be answered safely and coherently.

Unused budget remains unused.

## Stable-to-dynamic ordering

Context is ordered from stable approved policy toward volatile current evidence.

A responsibility-level ordering is:

```text
stable prefix
  common runtime policy
  approved SOUL / STYLE / BOUNDARY / durable expression policy
  optional approved durable lore

semi-stable policy/context
  selected relationship policy
  approved stable memory/knowledge summaries where applicable

request-local dynamic context
  scene policy/state needed by the request
  affect/expression hint
  intent/reference hint
  selected ordinary-memory evidence
  selected RelayLM-owned recent continuity
  minimum protocol/tool/multimodal state
  current user input
  response instruction
```

Exact block names and renderer syntax remain implementation details.

The invariant is that volatile request evidence does not silently become a higher-authority stable prefix.

## Durable character sources

Approved durable character sources may contribute stable prompt policy through their owning compiler/activation path.

Examples include portable identity, style, boundary, emotion-response profile, and optional lore sources.

RelayCTX does not edit or approve those sources. It consumes only accepted projections.

Current scene role, target relationship state, retrieved memory, current affect, and current topic remain outside portable SOUL identity.

## Relationship policy input

RelayREL supplies target-specific interaction policy for the governed target.

RelayCTX may place a bounded projection where it can influence response generation, while preserving that:

- relationship state is target-specific;
- it is not factual memory;
- strong relationship does not imply disclosure permission;
- missing relationship state fails closed toward less target-specific permission;
- RelayCTX does not mutate relationship sources.

## Scene policy input

RelaySCN supplies the current request/scene semantics and downstream policy.

RelayCTX may include only the bounded scene information necessary for the current action.

Scene state must not become a container for relationship state, affect, working transcript, memory prose, or durable persona.

Scene/audience policy may narrow what context or memory evidence is appropriate, but does not choose the ordinary-memory reader family.

## Affect/expression input

RelayEMO supplies transient affect/expression hints under relationship and scene constraints.

RelayCTX treats them as dynamic guidance, not truth or durable character state.

Affect failure or uncertainty degrades toward the approved durable voice rather than causing the prompt compiler to invent stronger emotion.

## Intent and reference input

RelayINT/reference-control artifacts may tell RelayCTX what action is intended, whether ambiguity requires clarification, or which bounded references are relevant.

RelayCTX does not become the intent analyzer merely because it consumes those decisions.

Unknown or invalid control artifacts fail closed according to their contract rather than being reconstructed from arbitrary old client messages.

## Ordinary-memory integration

RelayCTX receives memory only after the exact ordinary-memory reader authority has already been resolved.

Current RT-1 topology is:

```text
primary_only
  -> retained Primary compatibility retrieval may provide bounded selected evidence

neither
  -> no ordinary durable-memory evidence

subjective_only
  -> finalized Subjective retrieval may provide bounded selected evidence
  -> no Primary discovery, ranking, or fallback
```

RelayCTX does not choose among these branches.

It packs only the selected request-local evidence produced by the owning Retrieval path.

An empty, failed, privacy-suppressed, or scene-incompatible result does not authorize RelayCTX to probe another memory family.

## Memory evidence remains lower authority than policy

Selected memory evidence is dynamic evidence, not runtime policy or durable character instruction.

Packing preserves the authority ordering that runtime/safety, approved character boundaries, target relationship policy, scene/privacy policy, and exact reader/lifecycle gates cannot be overridden by a retrieved snippet.

Memory paths, store roots, selector/control metadata, raw lineage internals, retry state, and unrestricted operational metadata do not belong in the backend prompt merely because they were used to verify retrieval.

## Scene-memory and disclosure narrowing

A selected memory may still be inappropriate to disclose in the current scene or audience.

RelayCTX assembly therefore consumes already-governed narrowing decisions or bounded evidence needed by the final grounding/output policy.

It does not convert successful retrieval into disclosure permission.

A private motivation may inform a safe high-level response without copying the protected detail into the prompt/output surface when the applicable policy forbids that use.

## Selected recent context

Recent context means RelayLM-owned selected continuity, not the original frontend transcript array.

Stable rules are:

- include only what the current action requires;
- keep the current user turn distinct;
- do not restore excluded client history as a budget fallback;
- omission from the prompt is not a request to persist the omitted material;
- latency-sensitive routes keep continuity tightly bounded;
- old session state does not override a new governed target, scene, route, or instruction authority.

## Client instruction evidence

When an owning authority permits first-pass client instruction evidence, RelayCTX may include one bounded escaped low-trust block.

That evidence:

- remains below runtime/safety and approved durable authorities;
- excludes prior client history unless an explicit contract allows otherwise;
- disappears when a validated cached/compiled interpretation supersedes it;
- is not copied into default diagnostics;
- does not become durable SOUL, relationship, scene, or memory by being placed in a prompt.

## Protocol and tool state

RelayCTX preserves the minimum compatible tool, multimodal, transaction, or protocol state necessary for a valid backend call.

Protocol preservation does not grant semantic authority to tool metadata.

Sensitive identifiers and internal control structures remain bounded to the exact adapter/runtime need and are not surfaced in generic diagnostics or character prose.

## Budget degradation

When context exceeds the allowed budget, degradation removes lower-value optional context before damaging authority anchors.

A stable order is:

1. remove diagnostics-only/preview material;
2. reduce optional retrieved evidence according to Retrieval/grounding priorities;
3. reduce optional working-state hints;
4. shorten selected recent continuity;
5. use an authority-safe refusal/fallback if no valid payload can remain.

RelayCTX must not solve budget pressure by:

- dropping required safety/boundary policy;
- restoring raw prior client history;
- mutating durable character sources;
- changing the ordinary-memory reader family;
- fabricating relationship or scene state;
- serializing control metadata as substitute context.

## Cache-friendly stability

Stable approved prefixes should remain byte-stable where practical to improve backend prefix/KV reuse and reduce accidental prompt drift.

Volatile values such as timestamps, random IDs, request correlation, current topic, retrieved evidence, current scene, affect, and current input belong in dynamic portions rather than contaminating stable prefixes.

Cache friendliness is an optimization beneath authority. A cached prefix never overrides a newer approved source revision or current safety/relationship/scene decision.

## Rendering boundary

RelayCTX may render selected blocks into backend-compatible messages or tagged context according to the active adapter/contract.

Machine contracts remain typed/data-shaped even when the model-conditioning surface uses simple tags.

Rendering syntax does not become persistence authority, and a prompt block is not an audit record merely because it is structured.

## Runtime-private versus content-free observability

Compiled context and backend-bound messages are content-bearing runtime-private artifacts.

Generic trace/audit projections remain content-free by default.

They may expose bounded metadata such as:

- block presence/counts;
- stability classes;
- token/budget bands or bounded values;
- source/authority classes;
- reader-decision class;
- omission/degradation reason IDs;
- payload-mutation booleans;
- protocol-state presence flags.

They do not expose by default:

- prompt text;
- relationship bodies;
- scene body/participant values;
- memory prose;
- protected source content;
- raw client instructions;
- backend-visible response text;
- unrestricted file paths, namespaces, tokens, IDs, or internal control records.

A content-bearing compiled request must not be persisted wholesale merely because a nested diagnostics projection is content-free.

## Repack versus Unpack

RelayCTX Repack owns request-side selection/assembly.

RelayCTX Unpack owns the context-side separation of visible response from internal candidates/control artifacts according to its accepted runtime contract.

Neither operation gains durable memory, relationship, scene, SOUL, or client-instruction commit authority merely because it handles those artifacts.

Response finalization, transport, and any durable evidence capture remain separately owned.

## Failure behavior

Context assembly fails closed toward less optional context, not broader semantic authority.

```text
memory unavailable
  -> omit durable-memory context
  -> do not switch reader family

relationship state invalid
  -> reduce target-specific behavior
  -> do not borrow another target's state

scene state unresolved
  -> use conservative allowed scene behavior
  -> do not invent permissive scope

affect unavailable
  -> use approved durable style without extra modulation

budget cannot preserve required authority/protocol state
  -> refuse or use an explicitly accepted safe fallback
  -> do not replay raw client history
```

## Current versus target

This page is current as the canonical RelayCTX responsibility map.

Some richer workspace tiers, cache strategy, structured context schemas, client-instruction handling, or context-selection algorithms may remain target or partially implemented. Project Status remains authoritative for exact completion.

The permanent architecture does not preserve old Primary-only I1 injection wording as unconditional current serving. Primary evidence may be packed only while the exact RT-1 reader decision is `primary_only`; `subjective_only` uses finalized Subjective evidence only, and `neither` supplies no ordinary durable-memory context.

## Stable invariants

- RelayCTX compiles selected context; it does not concatenate arbitrary client history on managed routes.
- Upstream semantic owners decide relationship, scene, affect, intent/reference, and memory authority before packing.
- A token budget is an upper bound, not a fill target.
- Stable approved policy precedes volatile request evidence.
- RelayCTX working state is broader than prompt-selected context and is not automatically durable.
- Only evidence from the exact selected ordinary-memory reader family may enter ordinary memory context.
- Empty/failed/suppressed memory does not trigger cross-family fallback.
- Retrieved evidence remains below runtime/safety/character/relationship/scene/privacy authority.
- Scene/audience/disclosure constraints remain separate from successful retrieval.
- Raw prior client history is not restored as a degradation fallback.
- Stable-prefix caching never overrides a newer authority revision.
- Compiled prompts/messages are runtime-private; generic diagnostics are content-free by default.
- Repack/Unpack do not gain durable mutation authority.
- Failure closes toward less optional context, not broader authority.

## Non-goals

This architecture does not define:

- exact block/message/tag schemas;
- exact token budgets, ranking weights, or cache implementation;
- relationship, scene, affect, intent, or memory semantic algorithms;
- backend/model transport or invocation;
- output finalization or TTS/avatar rendering;
- durable memory, relationship, scene, SOUL, or client-instruction mutation;
- pass-through route semantics beyond acknowledging delegated authority;
- project-level implementation sequencing.

## Related architecture

- [Character Workspace Source Compiler](../character-workspace/source-compiler.md)
- [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md)
- [Runtime Request / Response Pipeline](../runtime/request-response-pipeline.md)
- [RelayREL Relationship State](../relationship/relationship-state.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [RelayEMO Affect Modulation](../emotion/affect-modulation.md)
- [Ordinary Memory Retrieval and Grounding](../memory/retrieval-and-grounding.md)
- [Scene-Aware Memory Scope](../memory/scene-memory-scope.md)
- [Protected Source and Disclosure](../privacy/protected-source-and-disclosure.md)
