---
relaylm_doc_type: subsystem_architecture
relaylm_authority: analyzer_candidate_schema_validation_and_authority_governance_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: analyzers
relaylm_update_trigger:
  - shared analyzer candidate authority semantics change
  - analyzer source/authority class policy changes
  - multilingual fixed-schema or public diagnostic boundary changes
  - candidate producers gain or lose downstream runtime-opening authority
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact analyzer dataclasses, enum sets, confidence thresholds, model prompts, or producer algorithms
  - exact RelaySCN, RelayINT, RelayMEM, RelayEMO, RelayCTX, or response-policy semantics
  - current source-specific authority facts supplied by route, tool, user confirmation, or product policy
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../analyzer_candidate_governance.md
  - ../acg1_analyzer_candidate_governance_contract.md
  - ../acg2_grounded_recall_detail_safety.md
  - ../acg3_retrieval_query_normalization.md
  - ../acg4_reference_intent_analyzer.md
  - ../acg5_relayemo_scene_cleanup.md
  - ../acg6_scene_wiki_classifier.md
  - ../scene/scene-model.md
  - ../memory/retrieval-and-grounding.md
  - ../emotion/affect-modulation.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - analyzer producer and shared-governance maintainers
  - RelaySCN, RelayINT, RelayMEM, RelayEMO, RelayCTX, and response-policy maintainers
  - multilingual, privacy, security, evaluation, and documentation reviewers
relaylm_authority_level: subsystem
---
# Analyzer Candidate Governance

## Purpose

This page is the canonical subsystem architecture for structured analyzer candidates and the authority gates that prevent heuristic or model-generated interpretation from silently becoming runtime policy.

RelayLM centralizes free-text interpretation behind bounded candidate producers so downstream components consume validated structured artifacts rather than each maintaining separate multilingual keyword semantics.

The stable model is:

```text
free text / bounded external signal
  -> analyzer or classifier candidate producer
  -> fixed schema + source classification
  -> validation + authority gate
  -> restrictive candidate or accepted bounded decision input
  -> downstream semantic owner
```

The candidate-governance layer decides whether an analyzer artifact is structurally valid and what authority class it may carry. It does not become the semantic owner of scene, intent, memory, affect, relationship, context, or output behavior.

## Candidate is not authority by default

Analyzer output is evidence or a candidate interpretation unless a separate trusted authority contract explicitly allows more.

The permanent distinction is:

```text
candidate produced
  != candidate valid
  != source authoritative
  != policy authority granted
  != candidate applied
  != downstream action permitted
```

An LLM producing high confidence does not itself satisfy any of the later transitions.

## Why a shared governance layer exists

Without a shared boundary, each Relay component could independently reinterpret natural language and accidentally mint policy from locale markers, regexes, or LLM prose.

That creates several failure modes:

- a scene keyword opens broader memory retrieval;
- a remembered-detail regex weakens unsupported-detail suppression;
- a reference heuristic becomes a durable intent decision;
- an affect guess becomes scene authority;
- multilingual parity requires duplicated keyword dictionaries across components;
- public diagnostics leak raw user text or free-form model rationale.

Shared candidate governance prevents these interpretation helpers from gaining implicit authority.

## Stable processing separation

RelayLM keeps four responsibilities separate:

```text
free-text understanding
  -> candidate producer

candidate trust / validation
  -> analyzer governance

component policy decision
  -> owning Relay component / authority gate

runtime execution
  -> owning request/response or persistence path
```

A candidate producer may improve understanding without becoming the component that authorizes a runtime effect.

## Fixed schema language

Analyzer contract keys, enum values, authority classes, and reason IDs use fixed English schema vocabulary.

This is an interoperability rule, not a user-language preference.

User input may be Japanese, English, Chinese, Korean, or another language. A producer normalizes that input into bounded schema values, and downstream components consume the schema rather than reparsing multilingual text.

User-facing response language remains independent from analyzer schema language.

## No free-form policy protocol

Free-form model prose is not a machine policy contract.

Where an LLM-backed analyzer is used, its result must be parsed and validated into the accepted bounded schema before downstream use.

Malformed JSON, unknown enums, unrecognized authority values, or unbounded rationale fail closed rather than being interpreted opportunistically.

## Common authority dimensions

Analyzer artifacts share responsibility-level dimensions such as:

- schema/analyzer kind;
- source class;
- source language where relevant;
- estimate status;
- source-authoritative boolean;
- candidate-applied boolean;
- policy-authority class;
- restrictive-only status;
- confidence/stability class;
- content-free projection status;
- validation/reason identifiers.

Exact field names and enum members remain implementation-contract details.

## Source classification

Source class is separate from analyzer confidence.

Conceptually, sources divide into trusted/confirmed classes and candidate-only classes.

Trusted classes may include bounded route metadata, explicitly trusted tool signals, or confirmed user actions when their owning contract says they are authoritative.

Candidate-only classes include heuristics, LLM candidates, locale markers, fallback regexes, unknown/malformed sources, and similar interpretation helpers.

A source does not become authoritative merely because the candidate producer assigned high confidence.

## Explicit authoritative-source requirement

Even a generally trusted source class is not automatically authoritative in every contract.

The caller/owner must explicitly mark or validate the source as authoritative under the target component contract.

This prevents a generic governance helper from converting all route or tool metadata into unrestricted policy authority.

## Non-authoritative candidate rule

Heuristic/LLM/locale/fallback candidates may:

- produce bounded candidate labels;
- improve recall or normalization within an already-authorized path;
- request re-check/escalation by the owning component;
- strengthen conservative restrictions;
- contribute content-free diagnostics.

They must not by themselves:

- open broad memory retrieval;
- authorize memory update or lifecycle mutation;
- write SOUL/REL/SCN/workspace sources;
- create current scene authority;
- create durable relationship authority;
- relax privacy/disclosure boundaries;
- enable a meaning-changing output rewrite;
- create public content-bearing diagnostics.

## Restrictive-only semantics

A non-authoritative candidate may be permitted to make behavior more conservative without gaining permission to make it more permissive.

Examples include:

- suppressing unsupported detail;
- recommending clarification;
- tightening a scene-sensitive action;
- disabling a risky rewrite;
- requesting an owning authority re-check.

The important invariant is asymmetric authority:

```text
candidate may close or narrow when contract permits
candidate may not open broader authority without trusted owner approval
```

## Fail-closed validation

Invalid candidate structure removes authority rather than being partially trusted.

Stable failure behavior includes:

- unknown analyzer kind -> unknown/non-authoritative;
- unknown source class -> non-authoritative/restrictive;
- unknown policy authority -> no policy authority;
- invalid confidence/stability -> conservative low/unknown class;
- malformed required fields -> candidate not applied;
- unknown reason/enum text -> bounded unknown token rather than raw echo;
- invalid content-free projection -> no generic public disclosure.

Validation errors remain bounded identifiers, not free-form internal exception leakage.

## Candidate application is explicit

`candidate_applied` or equivalent status is a result of a validated owning decision, not a producer request.

A producer can propose a candidate. The relevant component decides whether it is eligible to affect bounded behavior.

This preserves component ownership while allowing shared analyzers.

## Downstream owner remains authoritative

Candidate governance never replaces the target component.

Examples:

```text
scene candidate
  -> RelaySCN decides current scene/policy

reference/intent candidate
  -> RelayINT/reference owner decides request behavior

retrieval-query candidate
  -> Retrieval owner decides eligible query/retrieval behavior

affect candidate
  -> RelayEMO decides bounded affect/expression state

query-detail candidate
  -> Grounding/detail-safety owner decides allowed remembered-detail behavior
```

The governance helper validates candidate authority; it does not execute those component decisions itself.

## Query-detail candidate boundary

Grounded Recall/detail safety may consume a structured candidate describing which remembered detail classes appear to be requested.

Fallback lexical/regex signals remain non-authoritative and may not weaken unsupported-detail suppression.

Analyzer uncertainty closes toward less unsupported detail, not broader invention.

The candidate does not grant memory reader access or disclosure permission.

## Retrieval-query normalization boundary

Retrieval query analysis may normalize bounded query hints for languages where whitespace splitting is insufficient.

The analyzer can improve candidate discovery while remaining subordinate to reader authority, scope, lifecycle, privacy, and final retrieval selection.

A query candidate does not:

- select Primary versus Subjective authority;
- create cross-family fallback;
- open a memory namespace;
- authorize mutation;
- turn analyzer confidence into retrieval evidence confidence.

## Reference and intent boundary

A shared reference/intent candidate may identify possible unresolved reference, continuation, remembered-item request, or related request structure.

Locale markers and heuristics remain candidate signals rather than durable intent authority.

The owning intent/reference stage decides whether clarification, reference resolution, continuation handling, or another action is valid.

## Affect candidate boundary

Affect analysis produces uncertainty-preserving candidate information for RelayEMO.

It does not create normalized scene policy, memory truth, relationship state, or durable user facts.

Scene-like affect signals remain at most non-authoritative/restrictive hints; RelaySCN remains the scene owner.

## Scene candidate boundary

Structured scene classifier and scene-wiki matching may produce bounded `scene_policy_candidate`-like artifacts.

Trusted explicit/route scene authority keeps precedence under the RelaySCN contract.

Classifier/wiki candidates are non-authoritative by default.

They may support conservative scene restrictions, but do not open broad retrieval/update policy or mutate scene wiki/source content.

## Safe ID and enum matching

Where analyzers match structured definitions such as scene wiki entries, matching should use bounded safe IDs/enums/aliases rather than arbitrary page prose as executable policy.

This reduces the risk that content-bearing source text becomes an unvalidated control language.

Exact matching contracts remain with the producer/owner.

## Multilingual responsibility

The purpose of multilingual analyzers is not perfect keyword parity in every component.

The stable direction is:

```text
multilingual input
  -> one bounded interpretation candidate
  -> fixed schema
  -> downstream component uses fixed schema
```

Components should not reintroduce broad locale-specific semantic ownership merely because a fallback detector is convenient.

Fallback lexical logic may remain as a candidate/fail-safe under explicit non-authoritative rules.

## Confidence is not provenance

Analyzer confidence measures the producer's certainty about an interpretation.

It is not:

- source provenance;
- evidence truth confidence;
- memory strength;
- relationship trust;
- scene authority;
- disclosure permission;
- mutation permission.

High confidence from a low-authority source remains low authority.

## Stability is not authority

Likewise, repeated/stable analyzer output does not become authority automatically.

A heuristic that repeatedly returns the same result remains a heuristic until an owning contract accepts a source transition.

## Candidate scores do not become durable state

Candidate probabilities, confidence, heuristic scores, embedding similarity, or classifier logits do not become durable memory/relationship/persona values merely because they are useful to runtime interpretation.

Durable formation/update remains governed separately.

## Content-bearing runtime artifacts

Analyzer producers may need bounded content-bearing input/output internally to perform interpretation.

Those runtime-private artifacts are not generic diagnostics.

Their handling follows the owning privacy, request-scope, retention, and protected-source contracts.

## Public content-free projection

Default analyzer diagnostics expose only bounded fixed metadata.

Safe classes may include:

- analyzer kind;
- source class;
- source-authoritative boolean;
- policy-authority class;
- restrictive-only boolean;
- candidate-applied boolean;
- confidence/stability buckets;
- reason IDs;
- validation-error IDs;
- content-free marker.

They do not expose by default:

- raw user or assistant text;
- free-form analyzer rationale;
- model chain-of-thought;
- unvalidated external signal bodies;
- memory/relationship/scene/source prose;
- filesystem paths;
- queue/runtime payload bodies;
- secrets or credentials.

## Unknown values are not echoed

Unknown enum/reason/source values are normalized to fixed bounded unknown tokens rather than copied verbatim into public diagnostics.

This prevents malformed or attacker-controlled strings from becoming a diagnostic exfiltration channel.

## Error handling

Analyzer failure should degrade the analyzer-assisted feature, not seize unrelated authority.

Examples:

```text
query analyzer invalid
  -> use accepted conservative fallback / reduced hints
  -> do not broaden memory authority

reference candidate invalid
  -> unresolved / clarify / owning fallback
  -> do not infer hidden reference authority

affect candidate invalid
  -> safe heuristic/neutral path
  -> no scene or durable-state mutation

scene classifier invalid
  -> explicit/trusted scene authority remains
  -> candidate cannot open permissive policy
```

## Candidate producers do not own current status

A producer implementation can be complete while a downstream feature remains partial or disabled.

This canonical page therefore records responsibility boundaries rather than a dated list of implementation phases.

Project Status remains authoritative for exact implementation completion.

## Current implementation basis

The current architecture is grounded in the shared ACG-1 governance helper/contract and implemented bounded ACG producer slices for detail safety, retrieval-query normalization, reference/intent consolidation, RelayEMO scene cleanup, and structured scene classification/wiki matching.

Those implementation handoffs retain exact local schema and producer behavior. This page owns only the stable cross-analyzer governance model.

## Stable invariants

- Free-text interpretation is isolated behind candidate producers rather than duplicated as policy logic across Relay components.
- Analyzer schema keys/enums/reason IDs use fixed bounded machine vocabulary.
- Candidate production, validation, source authority, policy authority, application, and runtime effect remain separate gates.
- Heuristic/LLM/locale/fallback candidates are non-authoritative by default.
- Non-authoritative candidates may narrow/restrict only when their target contract permits; they do not open broad authority.
- High analyzer confidence does not turn a low-authority source into provenance or policy authority.
- Invalid/unknown schema values fail closed and disable authority.
- Downstream Relay components retain semantic ownership.
- Retrieval/query candidates cannot choose or restore ordinary-memory reader authority.
- Affect candidates cannot become scene authority or durable truth.
- Scene candidates cannot relax trusted scene/privacy/memory policy.
- Candidate scores do not become durable MEM/REL/SOUL state.
- Generic public diagnostics remain content-free.
- Unknown attacker-controlled values are represented by bounded unknown tokens rather than echoed.
- Analyzer failure degrades the assisted feature without broadening unrelated authority.

## Non-goals

This architecture does not define:

- exact analyzer schemas or enum inventories;
- exact confidence thresholds;
- exact heuristic, embedding, classifier, or LLM implementation;
- model-specific prompts;
- scene classification semantics themselves;
- reference/intent semantics themselves;
- retrieval ranking/reader authority;
- memory mutation or formation;
- relationship state;
- durable SOUL/persona changes;
- current implementation sequencing.

## Related architecture

- [Analyzer Candidate Governance and Multilingual Schema Policy](../analyzer_candidate_governance.md)
- [ACG-1 Analyzer Candidate Governance Contract](../acg1_analyzer_candidate_governance_contract.md)
- [ACG-2 Grounded Recall Detail Safety](../acg2_grounded_recall_detail_safety.md)
- [ACG-3 Retrieval Query Normalization](../acg3_retrieval_query_normalization.md)
- [ACG-4 Reference Intent Analyzer](../acg4_reference_intent_analyzer.md)
- [ACG-5 RelayEMO Scene Cleanup](../acg5_relayemo_scene_cleanup.md)
- [ACG-6 Scene Wiki Classifier](../acg6_scene_wiki_classifier.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [RelayMEM Retrieval and Grounding](../memory/retrieval-and-grounding.md)
- [RelayEMO Affect Modulation](../emotion/affect-modulation.md)
