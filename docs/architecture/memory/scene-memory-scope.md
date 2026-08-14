---
relaylm_doc_type: concept_policy
relaylm_authority: scene_aware_memory_scope_and_disclosure_semantics
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - RelaySCN memory-scope or audience policy changes
  - ordinary Retrieval scope or disclosure semantics change
  - scene-wiki matching or scene-classifier authority changes
  - deferred memory formation begins consuming new governed scene evidence
relaylm_not_authoritative_for:
  - exact scene-state, scene-policy, scene-wiki, classifier, retrieval, or memory schemas
  - exact matching, ranking, token-budget, cache, or classifier algorithms
  - scene lifecycle, reader selection, memory mutation, or disclosure-policy implementation
  - current implementation completion or R5/R6 retirement approval
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../scene/scene-model.md
  - retrieval-and-grounding.md
  - formation.md
  - system.md
  - ../../contracts/scene-classifier.md
  - ../relayscn_mvp_scene_policy.md
  - ../subjective-mem-retrieval-projection-hard-cutover.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelaySCN and RelayMEM integration maintainers
  - ordinary Retrieval and deferred formation maintainers
  - privacy, audience, and disclosure reviewers
relaylm_authority_level: concept
---
# Scene-Aware Memory Scope

## Authority summary

Scene-aware memory scope is a bounded cross-subsystem policy that lets an accepted RelaySCN scene narrow which already-authorized memory evidence is appropriate for retrieval, disclosure, or deferred persistence.

It does not create memory authority, choose the ordinary reader family, establish relationship trust, or turn a scene-classifier/wiki match into permission to read or write durable memory.

Exact scene interpretation remains owned by [RelaySCN Scene Model](../scene/scene-model.md). Exact reader selection and candidate eligibility remain owned by [Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md). Exact durable formation remains owned by [Subjective Memory Formation](formation.md).

## Problem

Memory relevance is not purely lexical or global. The same character may have durable memories that are appropriate in one situation and inappropriate in another because the active task, audience, participants, setting, formality, safety posture, or disclosure context differs.

A naive scene-memory integration can fail in dangerous ways:

- scene labels can become a second reader selector;
- classifier output can open broad memory access;
- a scene-wiki match can be mistaken for disclosure permission;
- scene end can incorrectly delete or hide durable memory;
- a roleplay scene can overwrite relationship trust or durable persona;
- scene metadata can be persisted as memory without governed formation;
- a scope miss can trigger fallback to another memory family.

Scene-aware memory scope prevents these authority collapses by treating scene information as a narrowing input only.

## Scene scope narrows, never expands, authority

The stable rule is:

```text
exact ordinary reader authority
  -> exact current memory-family scope and lifecycle eligibility
  -> accepted RelaySCN scene-policy narrowing
  -> scene-compatible candidates only
  -> ordinary ranking / grounding
```

Scene policy may reduce an already-authorized retrieval set. It cannot expand it beyond character, workspace, participant, relationship, lifecycle, provenance, disclosure, or RT-1 authority.

Examples:

- a `current_project` scene may prefer or require project-scoped memory when that memory family is already selected;
- a formal or sensitive scene may suppress otherwise eligible personal detail;
- a roleplay scene may narrow allowed scene-specific memory but cannot make private unrelated memory visible;
- an unknown scene may require conservative/default scope rather than broadening access.

A scene scope value is not a capability token.

## Reader authority remains first

RT-1 ordinary-memory authority is resolved before scene-aware candidate selection can touch a durable memory family.

```text
primary_only
  -> retired Primary reader remains unavailable
  -> scene policy opens no durable memory

neither
  -> no durable-memory retrieval, regardless of scene

subjective_only
  -> scene policy may narrow the already-authorized finalized Subjective candidate set only
  -> no Primary fallback or probing
```

A scene-policy request for a memory scope cannot turn `neither` into a reader, cannot convert `subjective_only` into Primary access, and cannot restore Primary after a failed or empty Subjective retrieval.

## Scene authority precedes scene-memory matching

Only accepted RelaySCN state/policy may constrain memory scope.

Candidate scene sources such as classifier output, lexical heuristics, or scene-wiki matches do not directly open memory access.

ACG-6 already implements a bounded scene-classifier and structured scene-wiki matcher. Its outputs are candidates and diagnostics. They remain subject to Analyzer Candidate Governance and RelaySCN source precedence before permissive scene policy may open.

Stable consequences are:

- untrusted classifier output may restrict or fail closed but does not broaden memory access;
- a scene-wiki match is not an authorization credential;
- explicit trusted route/scene state remains higher authority than a classifier candidate;
- raw aliases, labels, or scene body text do not become memory scope directly;
- matching code does not mutate scene-wiki definitions or memory.

## Scene-wiki matching semantics

Structured scene definitions may provide safe IDs, scene types, families, aliases, or other bounded matching features through their owning current contract.

A match means only that current request evidence corresponds to a known scene definition strongly enough to produce a candidate or accepted scene interpretation under RelaySCN governance.

It does not mean:

- all memory tagged with the scene is safe to disclose;
- the matched scene owns participant identity;
- the match grants relationship trust;
- the match may bypass lifecycle/currentness rules;
- the matched definition is itself a durable memory record;
- the matched scene may write memory automatically.

Full file-first scene-wiki source/compiler/activation behavior remains separately governed and is not defined here.

## Matching is not retrieval ranking

Scene matching and memory ranking are separate responsibilities.

```text
scene evidence
  -> RelaySCN scene authority/policy

memory evidence
  -> reader authority
  -> lifecycle/scope/provenance eligibility
  -> scene-aware narrowing
  -> relevance/ranking
```

A strong scene match does not make an irrelevant memory relevant. A strong retrieval score does not override scene disclosure restrictions.

Exact lexical/vector/semantic scene-memory matching and ranking weights remain implementation details rather than concept authority.

## Audience and participant scope

Scene context may describe participants or audience, but those labels are not durable identity or relationship authority.

Scene-aware memory handling must distinguish:

- who is currently present or expected to receive the response;
- which relationship identities are governed and trusted;
- which memory evidence is scoped to a participant/relationship/workspace;
- which disclosure restrictions apply in the current scene.

Stable rules are:

- a larger audience can only narrow disclosure;
- adding a participant does not automatically authorize that participant's private memory;
- a scene role does not create relationship trust;
- absence of a participant from scene context does not erase durable relationship state;
- participant metadata mismatch fails closed rather than guessing identity.

## Disclosure boundary

Scene policy is one input to disclosure, not the whole disclosure authority.

A memory may be canonically valid and retrieval-eligible yet still inappropriate to surface in a particular scene because of audience, relationship, safety, privacy, or explicit scene restrictions.

Conversely, a permissive scene cannot disclose memory that fails the selected memory authority's provenance, scope, lifecycle, or privacy rules.

The stable ordering is conservative:

```text
canonical eligible memory
  + exact current reader authority
  + relationship / participant scope
  + scene / audience narrowing
  + privacy / disclosure policy
  -> candidate may enter grounding
```

Failure at a later narrowing step does not cause fallback to a different memory family.

## Retrieval scope examples

Conceptual scope classes may include project, participant, relationship, scene-family, task, or ordinary/global-compatible memory where their exact contracts support them.

These are policy concepts, not a fixed enum declared by this page.

A scope comparison should be explicit and explainable. Unknown, incompatible, ambiguous, or unverifiable scope fails closed when disclosure depends on exact matching.

The system must not infer broad scope merely because a memory lacks optional scene metadata.

## Scene transition

Scene transition changes request-time policy; it does not mutate existing durable memories by itself.

When a scene changes:

- previously scene-compatible memories may become ineligible for the next request;
- newly compatible memories may become eligible only if all other authority gates pass;
- request-local selected-memory artifacts from the previous request do not carry authority forward;
- the transition does not hide, correct, pin, delete, purge, or otherwise lifecycle-mutate memory;
- the transition does not rewrite relationship state or durable persona.

A scene end likewise does not delete scene-associated memory automatically.

## Deferred formation boundary

Governed scene evidence may inform deferred assessment or Subjective formation when the formation contract allows it.

Scene evidence can help explain context such as task, setting, participants, formality, or situation. It does not independently prove a user fact or authorize durable persistence.

Stable rules are:

- the interactive response path remains separate from deferred formation;
- scene evidence must retain provenance/source authority;
- current RelaySCN state is not copied wholesale into memory prose;
- a classifier/wiki candidate that never became accepted scene authority does not become durable memory evidence merely because it existed;
- scene transition or persistence-allowed policy does not itself commit memory.

## Scene-specific memory and general memory

Scene-aware scope does not require a separate scene-memory store.

Durable memory remains under the selected canonical memory authority. Scene-related metadata or references may be part of an exact memory contract when justified, but they do not create another store, selector, or lifecycle.

A memory that is useful across scenes should not be trapped behind an incidental historical scene identifier unless its governing scope contract requires that restriction.

A memory genuinely scoped to a specific scene/room/audience must not silently broaden to general retrieval merely because later scene metadata is missing.

## Room and session metadata

Operational `session_id`, optional `room_id`, host channel identifiers, or frontend conversation IDs may help scene interpretation or scoping under their own contracts.

They remain operational/potentially sensitive metadata rather than prompt text or durable memory identity by default.

Stable rules are:

- session is operational and scene is semantic;
- room IDs do not become user-facing memory content by default;
- a room change does not automatically mean a new semantic scene;
- a repeated room ID does not prove the same scene or same disclosure audience;
- diagnostics omit or transform sensitive external identifiers according to their owning policy.

## Privacy and diagnostics

Scene-aware memory decisions may require protected scene, participant, or memory semantics internally.

Public/audit diagnostics remain content-free by default. They may expose bounded classes such as:

- scene authority/source class;
- scene-match presence/strength bucket;
- memory-scope match/mismatch class;
- candidate counts;
- disclosure-restriction presence;
- reason IDs.

They do not expose scene body text, memory prose, participant identities, relationship content, raw aliases, prompts, paths, namespaces, or unvalidated external metadata merely for diagnostics.

## Primary post-retirement boundary

Scene policy cannot create or revive reader authority. Under `primary_only` or `neither`, it opens no durable-memory family and cannot resolve a Primary root, store, candidate, recall, or fallback path.

Retained Primary scene-related artifacts may remain as historical, operational, migration, characterization, or regression evidence. Their existence does not authorize ordinary Primary serving. Under `subjective_only`, scene policy may only narrow the already-authorized Subjective candidate set; mismatch or empty results never probe Primary.

## Relationship to RelaySCN

[RelaySCN Scene Model](../scene/scene-model.md) owns scene authority, source precedence, lifecycle, role/context/constraints, and normalized policy.

This concept begins only after accepted scene policy exists. It owns the meaning of using that policy to narrow memory scope and disclosure.

## Relationship to RelayMEM

[Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md) owns reader selection, memory-family access, lifecycle/currentness eligibility, candidate discovery, ranking, and grounding.

This concept contributes a cross-cutting narrowing rule. It does not create a second Retrieval implementation.

## Invariants

- Scene-aware memory scope narrows already-authorized memory access; it never expands authority.
- The ordinary reader decision is resolved before scene-aware candidate selection touches a memory family.
- `neither` remains no-reader regardless of scene.
- `subjective_only` never falls back to Primary because of scene mismatch or empty results.
- Scene classifier and scene-wiki matcher outputs are candidates, not memory authority.
- Scene matching and memory ranking remain separate responsibilities.
- Audience/participant context can only narrow disclosure; it does not create relationship trust.
- Scene transition/end does not mutate or delete durable memory by itself.
- Governed scene evidence may inform deferred formation but does not itself prove a durable fact or authorize commit.
- Scene-related memory does not require a separate canonical memory store.
- Runtime/private scope reasoning stays separate from content-free diagnostics.

## Non-goals

This concept does not define:

- exact scene or memory scope schemas;
- exact scene-wiki source/compiler/UI behavior;
- a ranking or matching algorithm;
- memory reader selection;
- relationship identity/trust authority;
- durable memory mutation or deletion;
- automatic persistence on scene transition;
- disclosure policy beyond scene-aware narrowing;
- R5/R6 implementation or Primary retirement.

## Related architecture

- [RelaySCN Scene Model](../scene/scene-model.md)
- [Ordinary Memory Retrieval and Grounding](retrieval-and-grounding.md)
- [Subjective Memory Formation](formation.md)
- [Memory Subsystem Architecture](system.md)
- [Scene Classifier Contract](../../contracts/scene-classifier.md)
