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

RelayLM should keep analyzer schema keys, enum values, reason IDs, and policy fields in English. This does not mean that the LLM or analyzer returns English free-form prose. It means that arbitrary user input languages are normalized into English fixed schema values.

Example:

```json
{
  "schema_version": "relaylm.query_detail_analyzer.v0",
  "source_language": "ja",
  "requested_detail_types": ["date_or_time", "preference"],
  "confidence": 0.82,
  "is_estimate": true,
  "candidate_applied": false,
  "restrictive_only": true
}
```

The downstream Relay layers read `requested_detail_types`, `reference_kind`, `scene_type`, `affect_candidate`, or similar fixed enum values. They do not parse the original Japanese, English, Chinese, Korean, or other-language user text again.

Rules:

- schema keys, enum values, reason IDs, and policy fields remain English-only;
- user-facing output language remains independent from analyzer schema language;
- raw user text, free-form rationale, and unvalidated signals must not appear in public diagnostics;
- LLM analyzer outputs must be JSON-only and schema-validated before downstream use;
- unknown enum values and malformed JSON fail closed;
- candidate outputs may strengthen safety restrictions but may not open permissive runtime policy without trusted authority.

## Plain-language phase aliases

The ACG roadmap uses numbered implementation slices, but the product-level sequence also has a plain-language phase map:

```text
Phase A: Analyzer Governance
  -> ACG-1 Analyzer Candidate Governance contract (complete)

Phase B: Grounded Recall Detail Safety
  -> ACG-2 Grounded Recall Query Detail Analyzer (complete)

Phase C: Retrieval Query Normalization
  -> ACG-3 RelayMEM Query Analyzer / Retrieval Hint Normalization (complete)

Phase D: Reference/Intent Analyzer Consolidation
  -> ACG-4 RelayREF / RelayINT Reference Analyzer consolidation

Phase E: Scene-wiki Classifier
  -> ACG-6 SCN structured classifier and scene-wiki integration
```

ACG-0 is the prerequisite P0 ordering boundary and is complete through PR #458. ACG-1 is complete as the shared contract/helper slice. ACG-2 is complete as the Grounded Recall Query Detail Analyzer and request-side unsupported-detail safety slice. ACG-3 is complete as the Retrieval Query Analyzer / Retrieval Hint Normalization slice. ACG-5 remains inserted before Phase E to remove the remaining RelayEMO scene-ownership ambiguity so SCN scene-wiki work does not inherit a second scene owner.

## Priority implementation phases

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

This phase is documentation and schema-first. It does not introduce a large runtime classifier, and it does not implement ACG-3 through ACG-6 analyzer producers/classifiers.

### ACG-2: Grounded Recall Query Detail Analyzer

ACG-2 is complete. It moves request-side remembered-detail detection out of ad hoc regex ownership and into a Query Detail Analyzer artifact consumed by Grounded Recall.

Fixed English detail enum values:

```text
date_or_time
person_or_name
quantity
relationship
cause_or_reason
preference
location
identity
unknown
```

Existing regex checks remain as a fallback candidate, but unsupported-detail suppression does not become weaker. The fallback is non-authoritative, restrictive-only, and may strengthen suppression only.

ACG-2 does not require an LLM classifier, does not add post-hoc visible response rewriting, does not mutate memory, and does not expose raw user text, memory text, protected source bodies, free-form rationale, regex match bodies, filesystem paths, or queue payloads in public diagnostics.

The ACG-2 handoff is [ACG-2 Grounded Recall Detail Safety](acg2_grounded_recall_detail_safety.md).

### ACG-3: RelayMEM Query Analyzer / Retrieval Hint Normalization

ACG-3 is complete. It replaces whitespace-split semantic ownership with a Retrieval Query Analyzer boundary while keeping the existing whitespace path as a fallback candidate rather than the meaning owner.

Implemented scope:

- isolates RelayMEM query hint production behind `relaylm/retrieval_query_analyzer.py`;
- adds bounded language-tolerant fallback hints, including no-whitespace/CJK n-gram hints;
- keeps public `query_summary` and `retrieval_query_candidate` diagnostics content-free;
- keeps runtime-private bounded hints available to read-only RelayMEM candidate discovery and the E1-R5 bridge;
- prevents raw user text and private hint leakage in public diagnostics.

ACG-3 improves recall for languages without whitespace tokenization and reduces retrieval brittleness without opening broader retrieval, memory mutation, worker/scheduler behavior, or scene/lifecycle bypass authority.

The ACG-3 handoff is [ACG-3 Retrieval Query Normalization](acg3_retrieval_query_normalization.md).

### ACG-4: RelayREF / RelayINT Reference Analyzer consolidation

Unify unresolved-reference, continuation, and prior-memory-request detection behind a shared reference analyzer candidate.

Scope:

- replace duplicated fixed marker sets with one artifact;
- keep locale-specific markers as fallback candidate signals;
- make clarification / reflect suggestions restrictive-only unless trusted context resolves the reference;
- preserve content-free public diagnostics.

### ACG-5: RelayEMO scene ownership cleanup

RelayEMO should own affect and expression modulation, not scene policy.

Scope:

- rename or demote RelayEMO `scene_state` output to `scene_hint_candidate` if it remains useful for affect probing;
- ensure RelaySCN never consumes RelayEMO scene hints as authoritative state;
- keep affect candidates separate from scene policy and memory authority.

### ACG-6: SCN structured classifier and scene-wiki integration

Only after the authority contract and memory-safety analyzers are in place, introduce SCN structured classifier candidates and scene-wiki matching.

Scope:

- structured JSON classifier candidate;
- scene profile / scene-wiki matching;
- learned scene pattern consolidation;
- explicit confidence and authority gates;
- no direct broad retrieval or mutation authority from classifier output alone.

## Non-goals

This roadmap does not require:

- multilingual keyword parity in every Relay layer;
- making English free-form LLM prose authoritative;
- broad runtime policy from heuristic scene classification;
- Character Workspace parser/compiler/UI implementation;
- full SCN scene-wiki implementation before the memory-safety analyzers land.

## Acceptance criteria

The governance direction is considered established when:

- P0 RelaySCN ordering no longer relies on RelayEMO scene fallback;
- heuristic scene signals cannot open permissive RelayMEM policy;
- analyzer schemas use fixed English enum values;
- public diagnostics remain content-free even for explicit metadata signals;
- Grounded Recall detail detection has a candidate artifact boundary;
- retrieval query hints are no longer semantically owned by whitespace splitting;
- RelayREF and RelayINT reference markers are on a path to one shared analyzer artifact.
