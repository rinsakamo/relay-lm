---
relaylm_doc_type: architecture_report
relaylm_authority: analyzer_candidate_governance_and_multilingual_schema_policy
relaylm_status: current
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - analyzer candidate schema changes
  - multilingual interpretation boundary changes
  - policy authority or safety gate changes
  - RelaySCN / RelayINT / RelayREF / RelayMEM / RelayEMO analyzer ownership changes
relaylm_not_authoritative_for:
  - current implemented runtime status
  - exact per-component implementation status
  - user-visible language or presentation style
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - project_execution_plan.md
  - pipeline_responsibility_design.md
  - p0_relayrel_relayscn_relayemo_ordering_fix.md
  - acg1_analyzer_candidate_governance_contract.md
  - acg2_grounded_recall_detail_safety.md
  - acg3_retrieval_query_normalization.md
  - acg4_reference_intent_analyzer.md
  - acg5_relayemo_scene_cleanup.md
  - acg6_scene_wiki_classifier.md
  - e1r4_retrieval_response_grounding.md
  - relaymem_slp_current_target.md
---
# Analyzer Candidate Governance and Multilingual Schema Policy

Last reviewed: 2026-07-03 JST

## Purpose

RelayLM must avoid distributing natural-language keyword dictionaries across RelaySCN, RelayINT, RelayREF, RelayMEM, RelayEMO, and RelayCTX. Each Relay layer should consume validated structured artifacts rather than reinterpreting multilingual user text independently.

This report records the priority architecture and implementation roadmap for analyzer candidate governance. It is introduced after the P0 RelayREL / RelaySCN / RelayEMO ordering work exposed that lexical scene parity creates unbounded validation work. The corrective design is to isolate free-text understanding behind candidate producers and authority gates.

## Core principle

```text
free-text understanding
  -> analyzer / classifier / candidate producer

authority decision
  -> authority gate / confidence gate / safety gate

behavior mapping
  -> policy compiler

runtime execution
  -> RelayCTX / RelayMEM / RelayEMO / response path
```

Natural-language heuristics, locale-specific detectors, and LLM classifier outputs are candidates. They are not authoritative policy decisions by default.

## Governance rules

```text
trusted / explicit / confirmed sources:
  may open broader retrieval, update gates, source mutation proposals, or output rewrite paths when the target contract permits them

heuristic / LLM candidate / locale-specific detector sources:
  may produce diagnostics and candidate labels
  may restrict behavior fail-closed
  must not open broad retrieval, memory update, SOUL mutation, or output rewrite authority by themselves
```

Required common fields for analyzer artifacts:

```text
schema_version
source
source_language
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
confidence
stability
content_free
validation_errors
```

Downstream components must treat invalid schema, unknown enum values, low confidence, language ambiguity, or missing authority as fail-closed or restrictive-only.

## Multilingual schema policy

RelayLM keeps analyzer schema keys, enum values, reason IDs, and policy fields in English. This does not mean that the LLM or analyzer returns English free-form prose. It means that arbitrary user input languages are normalized into English fixed schema values.

The downstream Relay layers read `requested_detail_types`, `reference_kind`, `scene_type`, `affect_candidate`, or similar fixed enum values. They do not parse the original Japanese, English, Chinese, Korean, or other-language user text again.

Rules:

- schema keys, enum values, reason IDs, and policy fields remain English-only;
- user-facing output language remains independent from analyzer schema language;
- raw user text, free-form rationale, and unvalidated signals must not appear in public diagnostics;
- LLM analyzer outputs must be JSON-only and schema-validated before downstream use;
- unknown enum values and malformed JSON fail closed;
- candidate outputs may strengthen safety restrictions but may not open permissive runtime policy without trusted authority.

## Plain-language phase aliases

```text
Phase A: Analyzer Governance
  -> ACG-1 Analyzer Candidate Governance contract (complete)

Phase B: Grounded Recall Detail Safety
  -> ACG-2 Grounded Recall Query Detail Analyzer (complete)

Phase C: Retrieval Query Normalization
  -> ACG-3 RelayMEM Query Analyzer / Retrieval Hint Normalization (complete)

Phase D: Reference/Intent Analyzer Consolidation
  -> ACG-4 RelayREF / RelayINT Reference Analyzer consolidation (complete)

Phase D2: RelayEMO scene cleanup
  -> ACG-5 RelayEMO scene ownership cleanup (complete)

Phase E: Scene-wiki Classifier
  -> ACG-6 SCN structured classifier and scene-wiki integration (complete)
```

ACG-0 is the prerequisite P0 ordering boundary and is complete through PR #458. ACG-1 through ACG-6 are now implemented as bounded candidate-governance slices. Character Workspace parser/compiler/UI work remains separate.

## Implemented phases

### ACG-0: Close the P0 RelaySCN ordering boundary

The P0 RelayREL / RelaySCN / RelayEMO ordering fix is complete through PR #458. Current request-path ordering is:

```text
RelayREL -> RelaySCN -> RelayEMO -> RelayINT -> RelayMEM -> RelayCTX
```

RelaySCN owns normalized scene policy input. RelayEMO must not be a scene-state source for RelaySCN. RelaySCN lexical heuristics are non-authoritative and can only restrict policy unless backed by trusted request metadata.

### ACG-1: Analyzer Candidate Governance contract

ACG-1 is complete as the shared Analyzer Candidate Governance contract/helper slice. It introduces `relaylm/analyzer_governance.py` and smoke coverage in `scripts/relaylm_analyzer_governance_smoke.py`.

Scope:

- define common authority fields;
- define candidate-vs-authoritative semantics;
- define content-free diagnostics rules;
- define fixed English enum policy;
- define fail-closed behavior for invalid or low-confidence analyzer output.

The ACG-1 handoff is [ACG-1 Analyzer Candidate Governance Contract](acg1_analyzer_candidate_governance_contract.md).

### ACG-2: Grounded Recall Query Detail Analyzer

ACG-2 is complete. It moves request-side remembered-detail detection out of ad hoc regex ownership and into a Query Detail Analyzer artifact consumed by Grounded Recall.

Existing regex checks remain as fallback candidates, but unsupported-detail suppression does not become weaker. The fallback is non-authoritative, restrictive-only, and may strengthen suppression only.

The ACG-2 handoff is [ACG-2 Grounded Recall Detail Safety](acg2_grounded_recall_detail_safety.md).

### ACG-3: RelayMEM Query Analyzer / Retrieval Hint Normalization

ACG-3 is complete. It replaces whitespace-split semantic ownership with a Retrieval Query Analyzer boundary while keeping the existing whitespace path as a fallback candidate rather than the meaning owner.

ACG-3 improves recall for languages without whitespace tokenization and reduces retrieval brittleness without opening broader retrieval, memory mutation, worker/scheduler behavior, or scene/lifecycle bypass authority.

The ACG-3 handoff is [ACG-3 Retrieval Query Normalization](acg3_retrieval_query_normalization.md).

### ACG-4: RelayREF / RelayINT Reference Analyzer consolidation

ACG-4 is complete. It unifies unresolved-reference, continuation, and prior-memory-request detection behind a shared reference analyzer candidate while preserving content-free public diagnostics and keeping fallback locale markers non-authoritative.

The ACG-4 handoff is [ACG-4 Reference Intent Analyzer](acg4_reference_intent_analyzer.md).

### ACG-5: RelayEMO scene ownership cleanup

ACG-5 is complete. RelayEMO owns affect and expression modulation, not scene policy. Any remaining scene-like output is a non-authoritative scene hint candidate and RelaySCN does not consume RelayEMO artifacts as scene authority.

The ACG-5 handoff is [ACG-5 RelayEMO Scene Cleanup](acg5_relayemo_scene_cleanup.md).

### ACG-6: SCN structured classifier and scene-wiki integration

ACG-6 is complete as the first safe SCN structured classifier and scene-wiki matching boundary.

Implemented scope:

- `relaylm/scene_classifier.py` produces fixed English `scene_policy_candidate` artifacts;
- `relaylm/scene_wiki_matcher.py` matches structured scene definitions by safe IDs/enums/aliases only;
- RelaySCN includes classifier and scene-wiki diagnostics while preserving explicit/trusted scene authority precedence;
- classifier and scene-wiki matches remain non-authoritative by default;
- safety, formal-document, and recovery candidates may restrict/fail closed;
- non-authoritative implementation/review/design/roleplay candidates cannot open broad retrieval or update policy;
- public diagnostics remain content-free;
- no scene-wiki page mutation, uppercase source mutation, Character Workspace parser/compiler/UI, or live LLM dependency is introduced.

The ACG-6 handoff is [ACG-6 Scene-Wiki Classifier Boundary](acg6_scene_wiki_classifier.md).

## Non-goals

This roadmap does not require:

- multilingual keyword parity in every Relay layer;
- making English free-form LLM prose authoritative;
- broad runtime policy from heuristic scene classification;
- Character Workspace parser/compiler/UI implementation;
- scene-wiki page generation or mutation;
- RelayEMO scene ownership restoration.

## Acceptance criteria

The governance direction is considered established when:

- P0 RelaySCN ordering no longer relies on RelayEMO scene fallback;
- heuristic scene signals cannot open permissive RelayMEM policy;
- analyzer schemas use fixed English enum values;
- public diagnostics remain content-free even for explicit metadata signals;
- Grounded Recall detail detection has a candidate artifact boundary;
- retrieval query hints are no longer semantically owned by whitespace splitting;
- RelayREF and RelayINT reference markers share the ACG-4 reference analyzer boundary;
- RelayEMO affect/expression ownership is separated from RelaySCN scene policy;
- RelaySCN has a structured scene classifier candidate and scene-wiki match boundary;
- scene-wiki matching does not mutate files and does not expose scene body text;
- classifier candidates cannot open broad retrieval, memory update, SOUL/source mutation, or output rewrite authority by themselves.
