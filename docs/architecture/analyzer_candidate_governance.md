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

## Priority implementation phases

### ACG-0: Close the P0 RelaySCN ordering boundary

Complete the P0 RelayREL / RelaySCN / RelayEMO ordering fix before starting Character Workspace reset work.

Required boundary:

```text
RelayREL -> RelaySCN -> RelayEMO -> RelayINT -> RelayMEM -> RelayCTX
```

RelaySCN owns normalized scene policy input. RelayEMO must not be a scene-state source for RelaySCN. RelaySCN lexical heuristics are non-authoritative and can only restrict policy unless backed by trusted request metadata.

### ACG-1: Analyzer Candidate Governance contract

Introduce a shared architecture contract for analyzer candidate artifacts.

Scope:

- define common authority fields;
- define candidate-vs-authoritative semantics;
- define content-free diagnostics rules;
- define fixed English enum policy;
- define fail-closed behavior for invalid or low-confidence analyzer output.

This phase should be documentation and schema-first. It should not introduce a large runtime classifier.

### ACG-2: Grounded Recall Query Detail Analyzer

Move request-side remembered-detail detection out of ad hoc regex ownership and into a query detail analyzer artifact.

Why this is first among implementation phases:

- unsupported detail suppression directly protects remembered-fact correctness;
- current detail detection is language-limited;
- missing detail detection can allow unsupported dates, names, quantities, relationships, causes, or preferences to pass through without suppression.

Target candidate artifact:

```text
query_detail_analyzer
  -> requested_detail_types
  -> unsupported_detail_risk
  -> source_language
  -> confidence
  -> restrictive_only
```

Existing regex checks may remain as a fallback candidate, but unsupported-detail suppression must not become weaker. Low confidence should prefer restrictive suppression rather than permissive recall.

### ACG-3: RelayMEM Query Analyzer / Retrieval Hint Normalization

Replace whitespace-split query hints with a language-tolerant query analyzer boundary.

Scope:

- isolate `_term_hints` as a fallback candidate;
- add language-neutral fallback hints such as bounded character n-grams or validated structured search terms;
- keep public query summaries content-free;
- prevent raw user text leakage in diagnostics.

This improves recall for languages without whitespace tokenization and reduces retrieval brittleness.

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
