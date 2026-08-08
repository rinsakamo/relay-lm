---
relaylm_doc_type: subsystem_architecture
relaylm_authority: relayscn_scene_state_policy_and_lifecycle_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: scene
relaylm_update_trigger:
  - RelaySCN scene-state or scene-policy responsibility changes
  - scene source precedence or classifier ownership changes
  - scene lifecycle, role, audience, or persistence/disclosure policy changes
  - RelayREL, RelayEMO, RelayCTX, RelayMEM, or RelayRUN scene integration changes
relaylm_not_authoritative_for:
  - repository-wide current implementation completion or sequencing
  - exact scene-state, scene-policy, role, context, constraint, or projection schemas
  - exact classifier heuristics, thresholds, model, cache, or persistence implementation
  - exact memory retrieval, lifecycle mutation, relationship, affect, or runtime-checkpoint semantics
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../relayscn_mvp_scene_policy.md
  - ../scene_lifecycle_design.md
  - ../runtime/request-response-pipeline.md
  - ../runtime/compile-and-checkpoint.md
  - ../memory/retrieval-and-grounding.md
  - ../memory/system.md
  - ../pipeline-responsibilities.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelaySCN and runtime maintainers
  - RelayREL, RelayEMO, RelayCTX, and RelayMEM integration maintainers
  - scene-aware memory and disclosure policy reviewers
relaylm_authority_level: subsystem
---
# RelaySCN Scene Model

## Purpose

This page is the canonical subsystem architecture for RelaySCN scene interpretation, request-local scene policy, scene lifecycle, and downstream scene constraints.

RelaySCN answers two bounded questions:

1. **What semantic situation is active now?**
2. **What temporary policy follows from that situation for this request or scene?**

It does not own durable persona, relationship state, affect state, conversation working memory, memory records, runtime checkpointing, or general output rewriting.

Exact current implementation remains documented by the current RelaySCN handoffs and Project Status. This page owns stable responsibility, not an exact v0/v1 wire schema.

## Stable component boundary

```text
RelayREL
  -> relationship-conditioned interaction bounds

RelaySCN
  -> scene interpretation
  -> scene_state
  -> scene_policy

RelayEMO
  -> scene-constrained affect/expression handling

RelayINT / RelayMEM / RelayCTX
  -> consume relevant scene policy

RelayRUN
  -> runtime transition/checkpoint execution
```

Scene state must not become a catch-all container for another component's authority.

## Scene state

`scene_state` is request-local normalized semantic situation state.

Stable conceptual dimensions may include:

- scene type;
- confidence and stability;
- previous scene type and bounded transition class;
- current scene role;
- compact setting/task/participants;
- bounded temporary constraints;
- task state;
- safety sensitivity;
- formality;
- allowed memory scope;
- expression allowance;
- recovery state;
- user-confirmation requirement.

The exact field set and schema version remain contract/implementation details.

Scene state does **not** own:

- target-specific relationship state;
- mood or raw affect estimates;
- current topic notes or open questions;
- transcript-shaped recent turns;
- referable items or unresolved reference slots;
- memory-page bodies;
- durable persona traits.

Those belong to RelayREL, RelayEMO, RelayCTX, RelayINT/RelayREF, RelayMEM, or RelaySOUL respectively.

## Scene policy

`scene_policy` is the normalized downstream policy derived from accepted scene state.

Stable responsibilities may constrain:

- RelayCTX packing mode;
- RelayEMO marker/expression allowance;
- RelayMEM retrieval scope;
- memory-persistence eligibility or blocking;
- durable-persona proposal gating;
- SLP participation mode;
- user-confirmation requirements;
- diagnostic requirements;
- whether any exceptional output-side intervention is allowed.

Downstream components consume normalized scene policy rather than raw client instructions or host metadata.

Scene policy narrows a downstream authority; it does not replace it. A scene policy that allows memory retrieval does not choose the ordinary memory reader family, and a persistence-allowed scene does not authorize a durable memory mutation by itself.

## Scene role

`scene_role` describes what the character is doing in the current turn or scene.

```text
RelaySOUL
  who the character is durably

RelayREL
  how the character relates to a target

scene_role
  what function the character performs now
```

A scene role is temporary. It is not the OpenAI message `role` field and is not silently promoted into RelaySOUL.

Initial stable role scopes are bounded to turn or scene meaning. Longer-lived role/persona changes require their own durable authority.

## Scene context and constraints

Scene context is a compact description of setting, task, participants, and active situation.

Scene constraints are bounded temporary rules such as response brevity, clarification requirements, formal-mode restrictions, evidence requirements, or expression suppression.

Neither may become:

- a second transcript;
- a copy of RelayCTX working memory;
- durable relationship state;
- unrestricted client-instruction authority;
- hidden memory content.

Scene constraints remain below runtime/safety policy, approved durable persona policy, and approved relationship policy.

## Scene source precedence

Scene interpretation follows explicit source precedence rather than merging all available hints as peers.

The stable target order is conceptually:

```text
trusted route/operator scene configuration
  -> validated current client-instruction evidence
  -> route-approved request metadata
  -> approved continuation state
  -> current-turn heuristic/estimate
  -> safe default / unknown
```

Current RelaySCN v0 implements a smaller subset of this model, using explicit request metadata/payload state before a lightweight current-message heuristic and finally unknown/fail-closed state.

Raw client `system` or `developer` messages are evidence, not normalized scene authority. They must pass the owning client-instruction authority flow before affecting RelaySCN.

## Classifier ownership

RelaySCN owns normalized scene classification and scene-policy resolution.

A classifier, heuristic, cache, or model may produce evidence for RelaySCN, but the classification mechanism does not acquire authority over relationship state, memory, SOUL, or runtime policy.

Stable rules are:

- classifier confidence is evidence, not permission to bypass higher authority;
- low-confidence or unresolved scenes fail closed where a specific scene is required;
- unknown scene may still allow ordinary compatible chat when no stronger restriction is required;
- affect evidence from RelayEMO does not own normalized scene state;
- output observations may influence a later scene transition but do not retroactively redefine same-turn input state.

## Runtime order

The stable input-side ordering is:

```text
canonicalized request/client evidence
  -> RelayREL
  -> RelaySCN
  -> RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval when allowed
  -> RelayCTX Repack
  -> Main LLM
```

This order matters because relationship-conditioned policy constrains scene interpretation, and normalized scene policy constrains affect/expression and downstream memory/context behavior.

RelayREF is post-generation and does not guide same-turn input-side scene classification or Retrieval.

## Scene lifecycle

### Start

A scene starts when trusted configuration, approved metadata/instruction evidence, continuation state, or current-turn evidence establishes a semantic situation.

Missing explicit scene metadata does not itself require failure when a safe ordinary interpretation exists.

### Update

A scene may update when task, setting, participants, role, validated instruction identity, recovery state, or safety posture materially changes.

A normal topic update in RelayCTX does not automatically require a scene transition.

### Continue

A scene continues while its semantic situation and policy remain sufficiently stable.

Repeated equivalent evidence may confirm the scene but must not create repeated transitions or durable-persona proposals.

### Transition

A transition occurs when scene meaning or policy materially changes, including role, context, memory scope, safety posture, or required output constraints.

Changed hashes or metadata are evidence only; semantic validation determines transition meaning.

### End

A scene ends when host/operator authority resets it, a different semantic situation becomes current, or recovery establishes a new approved state.

Scene end does not automatically delete memory, persist constraints, mutate relationship state, or promote a scene role into durable persona.

## Output-side RelaySCN

Output-side RelaySCN consumes validated post-generation observations after response-context unpacking, reference analysis, and return-side affect processing.

Its normal responsibility is next-turn scene/recovery/persistence observation.

Immediate same-response intervention is limited to bounded safety, leakage, invalid-output, recovery, or wrong-continuation risks owned by the applicable runtime policy.

RelaySCN is not a general prose rewriter.

## Runtime-private state and content-free projection

Runtime-private scene artifacts may contain normalized role names, setting/task/participant semantics, constraint values, and transition candidates when downstream runtime components need them.

Persisted/general diagnostic projections remain content-free by default. They may expose bounded classes, booleans, counts, confidence/stability bands, transition presence, policy classes, or persistence reason IDs.

They must not expose raw role names, setting/task prose, participant values, constraint values, prompt fragments, visible response text, or other protected semantic content merely for diagnostics.

## Audience and disclosure boundary

Scene context may include participants and audience-relevant policy, but RelaySCN does not own the underlying durable identity or relationship graph.

Scene policy may narrow what memory scope or disclosure is appropriate for the current situation. It cannot expand disclosure beyond the selected memory authority's own scope/provenance rules.

Stable rules are:

- a broader scene audience cannot make private or out-of-scope memory eligible;
- a narrower/formal/sensitive scene may suppress otherwise eligible retrieval or persistence;
- scene role does not create relationship trust;
- participant labels do not replace governed participant identity;
- disclosure remains bounded by privacy/provenance/memory/relationship authority in addition to scene policy.

The dedicated scene-memory-scope and protected-source/disclosure concepts own the cross-subsystem concept details once synthesized; this parent scene architecture owns only RelaySCN's role in the chain.

## Memory boundary

Scene policy may constrain retrieval scope and persistence policy, but scene state is not a memory record.

```text
RelaySCN scene policy
  -> may narrow allowed memory scope / persistence

RelayMEM
  -> retains memory authority, lifecycle, eligibility, and reader selection
```

Scene transition or scene end does not itself authorize a memory write.

A scene retrieval scope cannot override the exact RT-1 ordinary reader decision, lifecycle exclusion, character/workspace scope, provenance, or disclosure policy.

RelaySLP may use governed scene evidence during deferred formation under its own authority; RelaySCN does not directly create durable memory merely because a scene is stable.

## Scene wiki direction

The target documentation graph anticipates a scene-wiki/file-first representation for durable or reusable scene material. That target concept is not equivalent to current request-local `scene_state`.

Until an exact source/compiler/activation authority is separately accepted and implemented:

- reusable scene source material is not silently treated as current scene state;
- editing a scene file does not automatically activate a request policy;
- request-local scene state remains derived from accepted current evidence;
- no scene-wiki document becomes a memory store, relationship store, or durable persona source by default.

This page intentionally does not invent a scene-wiki schema or claim its implementation is complete.

## Current versus target

Current RelaySCN v0 and the accepted richer scene model are not identical.

Current implementation already preserves the ordering-critical boundary `RelayREL -> RelaySCN -> RelayEMO` and current scene-source precedence over explicit request metadata, heuristic estimate, and unknown/fail-closed state.

Richer role/context/constraint/task/safety/formality/memory-scope fields and their exact typed schemas remain target or separately evolving details unless Project Status says otherwise.

Permanent architecture therefore owns responsibility and dependency direction rather than pretending a target v1 example is the current wire format.

## Stable invariants

- RelaySCN owns scene interpretation and scene-policy resolution.
- RelaySCN follows RelayREL and precedes RelayEMO on the input side.
- Scene state is request/scene semantic state, not relationship, affect, CTX transcript, memory, or SOUL authority.
- Scene policy narrows downstream behavior but does not replace downstream semantic authority.
- Raw client instructions are evidence, not normalized scene state.
- Scene role is temporary and is not silently promoted into durable persona.
- Scene transition is semantic, not a hash-change side effect.
- Scene end does not delete memory or persist temporary constraints automatically.
- Output-side RelaySCN normally informs next-turn state rather than rewriting ordinary output.
- Runtime-private scene semantics are distinct from content-free diagnostic projection.
- Scene scope may narrow memory/disclosure but cannot bypass memory reader, lifecycle, provenance, or privacy authority.
- Scene-wiki/file-first target material does not become active scene state without a separate accepted activation boundary.

## Non-goals

This architecture does not define:

- exact scene_state or scene_policy schemas;
- a particular classifier, heuristic, threshold, model, or cache;
- durable relationship, affect, CTX, memory, or SOUL state;
- memory retrieval or mutation implementation;
- client-instruction authority rules;
- a scene-wiki file schema or activation workflow;
- backend routing or general output rewriting;
- exact runtime checkpoint/recovery implementation.

## Related architecture

- [RelaySCN MVP Scene Policy](../relayscn_mvp_scene_policy.md)
- [Scene Lifecycle Design](../scene_lifecycle_design.md)
- [Runtime Request / Response Pipeline](../runtime/request-response-pipeline.md)
- [Memory Subsystem Architecture](../memory/system.md)
- [Ordinary Memory Retrieval and Grounding](../memory/retrieval-and-grounding.md)
