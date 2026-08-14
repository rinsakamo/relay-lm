---
relaylm_doc_type: subsystem_architecture
relaylm_authority: reference_candidate_and_relayint_request_interpretation_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: analyzers
relaylm_update_trigger:
  - shared Reference/Intent Analyzer responsibility changes
  - RelayINT reference, ambiguity, continuation, clarification, or retrieval-need ownership changes
  - analyzer-governance authority for reference/intent candidates changes
  - typed RelayINT migration changes current-versus-target boundaries
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact reference/intent candidate schemas, marker sets, confidence thresholds, or model prompts
  - exact future relayint.intent.v1 / projection schemas or migration completion
  - memory reader selection, retrieval ranking, persistence, scene policy, or RelayCTX storage semantics
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - candidate-governance.md
  - ../../contracts/reference-intent-analyzer.md
  - ../relayint_mvp_design.md
  - ../context/context-assembly.md
  - ../memory/retrieval-and-grounding.md
  - ../scene/scene-model.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Reference/Intent Analyzer and RelayINT maintainers
  - RelayCTX, RelayMEM Retrieval, RelaySCN, and request-pipeline maintainers
  - multilingual, ambiguity, privacy, evaluation, and documentation reviewers
relaylm_authority_level: subsystem
---
# Reference and Intent Architecture

## Purpose

This page is the canonical responsibility map for reference/continuation candidate detection and RelayINT request-local interpretation.

The stable boundary is:

```text
current user input + bounded request context
  -> shared Reference/Intent Analyzer candidate
  -> Analyzer Candidate Governance validation
  -> RelayINT interpretation
  -> continue | clarify | request bounded retrieval | other owning action
```

The analyzer identifies possible structure. RelayINT and downstream owners decide what the request may actually do.

## Current versus target implementation

The shared ACG-4 Reference/Intent Analyzer is current and consolidates previously duplicated free-text marker detection behind one governed candidate artifact.

RelayINT itself still contains compatibility and dry-run/current artifacts while a cleaner typed v1 contract remains target migration work.

Therefore this canonical page is current for responsibility boundaries, not a claim that every target typed artifact or migration step is complete.

Project Status remains authoritative for exact completion.

## Candidate producer and action owner are separate

The Reference/Intent Analyzer may detect candidate classes such as:

- unresolved/deictic reference;
- prior-turn reference;
- prior-memory reference;
- ambiguous choice;
- context-repair request;
- continuation;
- clarification request;
- correction/review/implementation-like request classes where the owning contract supports them.

These are bounded machine candidates, not final request authority.

RelayINT owns request-local interpretation and whether the request should proceed, clarify, or ask the memory layer for a bounded retrieval attempt.

## Shared analyzer replaces duplicated lexical ownership

RelayREF/RelayINT-style paths must not maintain independent natural-language dictionaries as competing semantic authorities for the same reference boundary.

Locale markers and fallback regexes may remain implementation aids, but they produce non-authoritative candidates through the shared governance layer.

Downstream components consume structured results rather than reparsing the same Japanese/English/etc. phrases into separate policy.

## Fixed schema vocabulary

Reference/intent candidate keys and enum values use bounded machine vocabulary independent of user language.

User-facing output language remains separate.

Raw user text and matched marker bodies do not become public diagnostic protocol.

## Marker sources are non-authoritative

Locale markers, regexes, and heuristic detectors are non-authoritative by default.

They may:

- indicate that clarification may be safer;
- indicate possible continuation or prior-memory intent;
- narrow behavior conservatively;
- contribute content-free diagnostics.

They must not by themselves:

- open broad memory retrieval;
- choose a memory reader family;
- authorize memory mutation;
- create durable reference truth;
- bypass scene/privacy/safety gates;
- force a meaning-changing output path.

## Ambiguity fails closed

Ambiguous references do not silently trigger long-term recall merely to guess what the user meant.

The stable preference is:

```text
clear current-turn noun/reference
  -> use it

one clear active request-local referent
  -> continue within current context

multiple plausible referents
  -> clarify or conservatively defer

no adequate current-context referent
  -> clarify unless an explicit/confirmed memory scope authorizes retrieval
```

The exact scoring/threshold logic remains implementation-specific.

## Current-context resolution precedes durable retrieval

Short references should use bounded current/request-local continuity before attempting durable memory.

RelayCTX may provide working-state hints such as current topic, active task, prior decision, referable items, or unresolved slots under its own contract.

RelayINT may consume those hints. It does not own or persist RelayCTX working state.

## Retrieval need is not reader authority

RelayINT may determine that durable retrieval is or is not needed for the current request.

That decision is distinct from ordinary-memory reader authority.

Current topology remains:

```text
RelayINT
  -> retrieval needed / not needed / clarify

RT-1 + Retrieval
  -> primary_only | neither | subjective_only
  -> exact eligible retrieval path
```

RelayINT cannot restore a fenced/retired reader, create cross-family fallback, or select Primary versus Subjective merely from intent detection.

## Explicit or confirmed long-term scope

Long-term retrieval becomes reasonable only when request meaning and applicable scene/privacy scope are sufficiently explicit or confirmed under the owning contracts.

Examples include an explicit request to remember something previously discussed or a resolved reference whose needed facts are absent from current context.

Even then, RelayINT requests retrieval; Retrieval independently applies reader, scope, lifecycle, privacy, and eligibility gates.

## Scene policy remains external

RelaySCN owns current scene and scene policy.

RelayINT may consume scene constraints when deciding whether clarification/retrieval/action is compatible.

It does not classify the scene simply because a reference or request type suggests one.

A reference/intent candidate cannot open memory or output behavior forbidden by current scene policy.

## Relationship and affect remain external

Relationship or affect context may influence bounded conversational handling through their owners, but Reference/Intent analysis does not create RelayREL or RelayEMO authority.

A marker like “remember” does not prove relationship permission for personal-memory disclosure.

## Clarification is an action, not authority bypass

When ambiguity is material, RelayINT may produce a clarification candidate/plan under its current contracts.

Visible clarification must still follow the normal output/runtime safety path.

RelayINT does not gain permission to emit ungoverned user-visible text merely because clarification is short.

## Quick-clarification compatibility boundary

Current RelayINT includes bounded quick-clarification preflight/apply-plan helpers.

Their stable architectural meaning is:

- default/fail-closed behavior remains conservative;
- incompatible tool/structured/multimodal transactions are not short-circuited casually;
- recovery/safety/scene constraints remain authoritative;
- the plan is not direct durable state mutation;
- rendered clarification content does not become generic diagnostics.

Exact runtime wiring belongs to current implementation contracts/status.

## Compatibility artifacts do not define permanent ownership

Historical RelayREF-shaped compatibility artifacts and current dry-run fast-path artifacts may remain in implementation while migration proceeds.

Their existence does not change the stable ownership model:

- reference/intent understanding belongs in the shared analyzer + RelayINT boundary;
- Retrieval owns memory access;
- RelayCTX owns working/context state;
- RelaySCN owns scene policy;
- RelayRUN owns orchestration.

## Analyzer confidence is not action authority

High reference/intent confidence from a heuristic or LLM candidate does not independently authorize a permissive action.

Candidate source authority and downstream gates remain separate from confidence.

Unknown/malformed/low-confidence candidates fail closed toward clarification, reduced assumptions, or owning fallback.

## Corrections and context repair

A possible correction/context-repair marker may guide RelayINT toward clarification or the appropriate existing correction/governance path.

The analyzer does not itself mutate memory or rewrite prior Evidence.

Memory Correct/Forget and other durable operations remain under their own governance contracts.

## Prior-memory request boundary

A detected prior-memory request indicates possible user intent to use durable memory.

It does not mean:

- durable memory exists;
- a matching memory is eligible;
- a reader family is available;
- disclosure is permitted;
- retrieval must succeed.

An empty/blocked retrieval does not authorize the Reference/Intent layer to search another memory family.

## Continuation boundary

Continuation intent may allow the request to reuse bounded current working context when the referent is sufficiently clear.

Continuation does not mean replaying arbitrary frontend history or restoring excluded client messages.

RelayCTX remains responsible for selected RelayLM-owned recent context.

## Public diagnostics are content-free

Default Reference/Intent diagnostics may expose bounded values such as:

- reference kind;
- intent kind/class counts;
- ambiguity present/absent;
- candidate source class;
- source-authoritative/restrictive-only status;
- confidence/stability band;
- candidate-applied status;
- clarification/retrieval-needed booleans or bounded action class;
- reason/validation IDs.

They do not expose by default:

- raw user/assistant text;
- matched marker text;
- resolved-reference text;
- candidate labels containing private content;
- memory bodies;
- relationship/scene bodies;
- free-form model rationale;
- filesystem or queue internals.

## Runtime-private semantic content

A future/current runtime-private RelayINT object may contain semantic interpretation needed within the request.

That content is not automatically suitable for persisted/public trace.

Content-free projections remain separate from content-bearing request-local interpretation.

## Failure behavior

Reference/Intent failure closes toward less assumption and no broader memory authority.

```text
analyzer malformed/unknown
  -> non-authoritative unknown
  -> clarify / conservative owning fallback

ambiguous reference
  -> no silent long-term recall
  -> clarify or defer

explicit memory request but reader unavailable
  -> retrieval unavailable/empty handling
  -> no cross-family fallback

scene blocks memory
  -> current-context-only or clarify
  -> no analyzer override

quick-clarification path invalid
  -> use normal response path
  -> no safety/recovery bypass
```

## Stable invariants

- Shared Reference/Intent analysis replaces duplicated lexical policy ownership for this boundary.
- Marker/regex/heuristic candidates are non-authoritative by default.
- Candidate detection and RelayINT action interpretation remain separate gates.
- Ambiguous references do not silently trigger durable memory retrieval.
- Current/request-local context is preferred before durable recall for short references.
- RelayINT may request retrieval but does not choose/restore the ordinary-memory reader family.
- Retrieval independently applies RT-1, scope, lifecycle, privacy, and selection authority.
- RelaySCN remains scene-policy owner.
- RelayCTX remains working/context-state owner.
- Analyzer confidence is not provenance or permissive action authority.
- Correction/context-repair candidates do not mutate memory directly.
- Continuation does not restore arbitrary excluded client history.
- Clarification follows normal output/runtime safety authority.
- Runtime-private semantic interpretation remains separate from content-free diagnostics.
- Current compatibility artifacts do not redefine permanent component ownership.

## Non-goals

This architecture does not define:

- exact locale marker lists;
- exact candidate enum/schema inventory;
- exact confidence thresholds;
- exact typed RelayINT v1 schema or migration completion;
- memory reader selection/ranking;
- scene classification;
- durable memory mutation;
- RelayCTX persistence;
- final response generation;
- repository-level implementation sequencing.

## Related architecture

- [Analyzer Candidate Governance](candidate-governance.md)
- [Reference/Intent Analyzer Contract](../../contracts/reference-intent-analyzer.md)
- [RelayINT MVP Design](../relayint_mvp_design.md)
- [RelayCTX Context Assembly](../context/context-assembly.md)
- [RelayMEM Retrieval and Grounding](../memory/retrieval-and-grounding.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
