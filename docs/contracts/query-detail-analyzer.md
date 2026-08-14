---
relaylm_doc_type: contract
relaylm_authority: current_query_detail_analyzer_and_grounded_recall_detail_safety_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: analyzers
relaylm_update_trigger:
  - Query Detail Analyzer schema or detail enum changes
  - fallback-regex or structured-candidate merge semantics change
  - analyzer-governance restriction of query-detail candidates changes
  - public query-detail projection changes
  - Grounded Recall unsupported-detail consumption changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - shared Analyzer Candidate Governance fields or thresholds
  - full Grounded Recall evidence eligibility, provenance, lifecycle, or scope policy
  - ordinary memory retrieval authority, ranking, reader selection, or mutation
  - exact lexical regex pattern text beyond the bounded current detail classes
  - R5/R6 Primary MEM retirement or cutover authority
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/analyzers/candidate-governance.md
  - ../architecture/memory/retrieval-and-grounding.md
  - ../architecture/e1r4_retrieval_response_grounding.md
relaylm_related_contracts:
  - analyzer-candidate.md
relaylm_verified_by:
  - ../../scripts/relaylm_acg2_query_detail_analyzer_smoke.py
  - ../../scripts/relaylm_e1r4_grounded_recall_response_smoke.py
  - ../../scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - query-detail analyzer and Grounded Recall maintainers
  - analyzer governance, retrieval, grounding, privacy, and diagnostics maintainers
  - multilingual, security, evaluation, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Query Detail Analyzer Contract

## Authority summary

This contract owns the exact current Query Detail Analyzer artifact and the narrow Grounded Recall detail-safety handoff that consumes it.

The current implementation anchors are:

```text
relaylm/query_detail_analyzer.py
relaylm/relaymem_grounded_recall_response.py
```

The stable flow is:

```text
private request query text
  + optional structured query-detail candidate
  -> bounded fallback detection
  -> fixed detail-enum normalization
  -> shared Analyzer Candidate Governance normalization
  -> restrictive QueryDetailAnalysis
  -> Grounded Recall requested-detail support check
  -> content-free public diagnostics
```

This boundary detects which classes of remembered detail appear to be requested. It does not itself select a memory reader, retrieve memory, grant disclosure permission, mutate memory, or authorize broad runtime policy.

## Relationship to shared Analyzer Candidate Governance

The shared exact governance contract is:

```text
docs/contracts/analyzer-candidate.md
```

That contract owns common analyzer kinds, source classes, policy-authority vocabulary, confidence/stability thresholds, normalization, and generic content-free projection.

This contract owns the **query-detail producer-specific** shape and fail-closed behavior layered on top of that shared governance.

A query-detail candidate cannot use a generic governance value to open broader runtime authority. If shared governance would otherwise consider the normalized candidate runtime-opening, Query Detail Analyzer forcibly closes it back to restrictive behavior.

## Current schema identity

The exact current Query Detail Analyzer schema identifier is:

```text
relaylm.query_detail_analyzer.v0
```

The exact analyzer kind is:

```text
query_detail_candidate
```

## Current detail vocabulary

The accepted requested-detail enum values are exactly:

```text
cause_or_reason
date_or_time
identity
location
person_or_name
preference
quantity
relationship
unknown
```

No free-form detail label becomes part of the artifact.

An invalid candidate detail value normalizes to:

```text
unknown
```

and records:

```text
unknown_enum_value
```

## QueryDetailAnalysis shape

`QueryDetailAnalysis` is immutable and contains exactly:

```text
schema_version
analyzer_kind
source
source_language
requested_detail_types
unsupported_detail_risk
confidence
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
content_free
reason_ids
validation_errors
governance_artifact
```

`governance_artifact` is runtime/internal governance state and is excluded from the dataclass representation. Generic/public consumers use the content-free projection rather than the raw governance mapping.

`content_free` is true for every returned `QueryDetailAnalysis`.

`unsupported_detail_risk` is true exactly when normalized `requested_detail_types` is non-empty, except that validation failure with no surviving detail types is closed to `unknown`, which also makes the risk true.

## Bounded fallback detail detection

When request text is a non-empty string, the current fallback detector can identify these classes:

```text
date_or_time
person_or_name
quantity
relationship
cause_or_reason
preference
location
identity
```

The fallback recognizes bounded English and Japanese lexical forms for those classes.

The exact regex spellings remain implementation detail; the contract boundary is that fallback output is limited to the fixed enum above and is never authoritative.

A self-identity query that matches the dedicated self-identity form does not keep `person_or_name` merely because a broader person/name pattern also matched. When `identity` is present from the self-identity query, that overlapping `person_or_name` fallback classification is removed.

Fallback detail types are de-duplicated while preserving first occurrence order.

## No structured candidate

When `candidate is None`, Query Detail Analyzer uses only the bounded fallback result.

If fallback detail types are present, the current normalized input is:

```text
source = fallback_regex
source_language = inferred bounded language
confidence = 0.66
stability = 0.5
is_estimate = true
source_authoritative = false
candidate_applied = true
policy_authority = restrictive
restrictive_only = true
reason_ids = (fail_closed_candidate_source,)
```

If fallback detail types are empty, the same fallback source is used with:

```text
confidence = 0.0
stability = 0.0
candidate_applied = false
policy_authority = none
restrictive_only = true
```

The fallback never opens permissive policy.

## Non-mapping structured candidate

A non-null candidate that is not a mapping fails closed.

The requested-detail result is the union of:

```text
fallback detail types
+ unknown
```

The current governance inputs are:

```text
source = unknown
confidence = 0.0
stability = 0.0
is_estimate = true
source_authoritative = false
candidate_applied = false
policy_authority = none
restrictive_only = true
reason_ids = (fail_closed_candidate_source,)
validation_errors = (unknown_enum_value,)
```

Raw candidate content is not copied into the public result.

## Mapping candidate detail normalization

For a mapping candidate, `requested_detail_types` accepts:

- a string, treated as one candidate value;
- another iterable, treated as a sequence of candidate values;
- `None`, treated as no candidate detail values.

A non-iterable non-string value produces `unknown` plus `unknown_enum_value`.

Each value is normalized to a bounded token. Values outside the accepted detail vocabulary become `unknown` and add `unknown_enum_value`.

If the mapping omits the `requested_detail_types` key entirely, the analyzer adds:

```text
requested_detail_types += unknown
validation_errors += unknown_enum_value
```

The final requested-detail sequence is the de-duplicated, first-occurrence-preserving union:

```text
fallback detail types
+ structured candidate detail types
```

Structured output therefore cannot erase a restrictive fallback detail classification.

## Candidate metadata inputs

A mapping candidate may provide the current analyzer-governance inputs:

```text
source
source_language
confidence
stability
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
reason_ids
validation_errors
```

Missing values use the current producer defaults before shared governance normalization:

```text
confidence = 0.0
stability = 0.0
is_estimate = true
source_authoritative = false
candidate_applied = bool(merged requested detail types)
policy_authority = restrictive if merged requested detail types else none
restrictive_only = true
reason_ids = ()
validation_errors = ()
```

The producer always supplies shared governance with:

```text
analyzer_kind = query_detail_candidate
content_free = true
```

## Source-language handling

Fallback source language is inferred through the bounded shared text-feature helper.

A candidate-provided `source_language` is accepted only when it is:

- a non-empty string after trim;
- at most 16 characters;
- composed only of ASCII alphanumeric characters, `-`, or `_`.

It is normalized to lowercase.

Invalid candidate language does not become a new public token; the analyzer falls back to the bounded language inferred from the request text.

## Unsupported and raw-like extra fields

These mapping keys are the producer-recognized input surface:

```text
schema_version
analyzer_kind
source
source_language
requested_detail_types
unsupported_detail_risk
confidence
stability
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
content_free
reason_ids
validation_errors
```

Other keys are passed only through fail-closed governance validation.

The producer classifies these extra key names as raw/content-like:

```text
assistant_text
external_signal_body
filesystem_path
memory_text
protected_source_body
queue_payload
rationale
raw_assistant_text
raw_text
raw_user_text
regex_match_body
source_body
user_text
```

Such keys add:

```text
raw_diagnostic_field_dropped
```

Other unsupported extra keys add:

```text
unsupported_field_dropped
```

Their values do not extend the Query Detail Analyzer schema or become public diagnostics.

## Query-detail authority is restrictive only

After shared governance normalization, Query Detail Analyzer checks the normalized artifact with the shared runtime-open predicate.

If that predicate would allow runtime policy to open, Query Detail Analyzer forcibly changes the normalized governance result to:

```text
validation_errors += policy_authority_not_permitted
policy_authority = restrictive
restrictive_only = true
source_authoritative = false
```

The query-detail boundary therefore cannot become a permissive runtime-opening authority even if a structured candidate claims a trusted source, high confidence, or broader policy authority.

Its role is detail-safety restriction only.

## Validation-error final closure

If governance/producer validation errors exist and no normalized requested detail type remains, the returned analysis is closed to:

```text
requested_detail_types = (unknown,)
unsupported_detail_risk = true
```

Malformed analyzer input therefore cannot silently mean "no detail restriction".

## Public projection

`QueryDetailAnalysis.to_public_dict()` returns a content-free projection with the current fields:

```text
schema_version
analyzer_kind
source_class
source_language
requested_detail_types
requested_detail_type_count
unsupported_detail_risk
source_authoritative
policy_authority
restrictive_only
candidate_applied
confidence_bucket
stability_bucket
reason_ids
validation_error_ids
content_free
raw_user_text_included
raw_assistant_text_included
raw_memory_text_included
protected_source_body_included
free_form_rationale_included
regex_match_body_included
queue_payload_included
filesystem_path_included
```

The fixed disclosure booleans are:

```text
content_free = true
raw_user_text_included = false
raw_assistant_text_included = false
raw_memory_text_included = false
protected_source_body_included = false
free_form_rationale_included = false
regex_match_body_included = false
queue_payload_included = false
filesystem_path_included = false
```

The public projection uses the shared governance contract for source class, authority, policy, restrictive status, candidate-applied status, confidence/stability buckets, and bounded governance reason/error IDs.

Producer validation errors are appended to governance validation errors and de-duplicated without exposing the rejected raw value.

## Mapping/None public helpers

`query_detail_public_projection(...)` accepts either:

- an existing `QueryDetailAnalysis`;
- a mapping-like candidate;
- `None`.

A non-analysis input is normalized through `analyze_query_detail_candidate(candidate=...)` before projection.

`requested_detail_types_from_analysis(...)` follows the same rule and returns the normalized requested-detail tuple.

These helpers do not bypass the producer normalization path.

## Grounded Recall consumption boundary

`build_grounded_recall_context(...)` invokes Query Detail Analyzer after its top-level request-shape and unsupported-detail-policy validation and before evidence-item support analysis.

The accepted `unsupported_detail_policy` values are exactly:

```text
suppress
qualify_uncertain
omit
```

This contract does not redefine full Grounded Recall evidence eligibility. It owns only how the query-detail analysis participates in the current unsupported-detail safety check.

The runtime-private grounded-recall context records:

```text
query_detail_types
unsupported_detail_risk
query_detail_analysis
```

where `query_detail_analysis` is the **public content-free projection**, not raw request text or a raw structured candidate.

## Current requested-detail support check

Grounded Recall joins the eligible evidence-item `fact_text` values and checks requested detail classes against bounded evidence patterns.

The current support check accounts for exactly:

```text
date_or_time
quantity
person_or_name
relationship
cause_or_reason
preference
location
identity
unknown
```

Each missing requested class contributes at most one to `unsupported_detail_count`.

`unknown` always contributes one unsupported detail.

For a generic `preference` request, evidence must contain a bounded preference-like form.

For an English `favorite <detail>` / `favourite <detail>` request recognized by the current favorite-detail detector, evidence must contain a matching `favorite <detail>` or `favourite <detail>` form; unrelated preference text is not enough for that requested sub-detail.

## Unsupported-detail result

After eligible evidence items are built, Grounded Recall computes `unsupported_detail_count` from the query-detail analysis.

When there is at least one eligible evidence item and at least one unsupported requested detail, the current result is:

```text
status = unsupported_detail_suppressed
backend_request_changed = true
blocked_reasons = (requested_detail_not_supported_by_retrieved_memory,)
```

The grounded context remains runtime-private and the instruction tells the backend not to present unsupported remembered detail as supported memory.

For `qualify_uncertain`, the current instruction tells the backend to qualify the unsupported detail as uncertain rather than present it as memory.

For `suppress` and the current `omit` branch, the instruction tells the backend to suppress/omit the unsupported detail and state that the memory does not support it.

This is request-side grounding. It is not post-hoc visible-response rewriting.

## No-evidence direction

If the retrieved-memory sequence is empty, Grounded Recall returns its existing `no_retrieved_evidence` result with a runtime-private context containing the Query Detail Analyzer projection.

The backend instruction states that no retrieved evidence is present and that it must not claim to remember the requested detail.

The query-detail producer does not synthesize evidence when retrieval returned none.

## Grounded Recall public diagnostics

Grounded Recall's content-free log projection exposes query-detail metadata only through bounded fields such as:

```text
query_detail_type_count
query_detail_unsupported_detail_risk
query_detail_source_class
query_detail_restrictive_only
query_detail_content_free
```

It does not add raw request text, memory text, protected source bodies, queue payloads, filesystem paths, or private evidence arrays to public diagnostics.

## Failure-direction invariants

The current boundary fails toward **more restriction**, never toward invented detail authority:

```text
no structured candidate
  -> bounded restrictive fallback

malformed non-mapping candidate
  -> fallback union unknown

missing requested_detail_types
  -> unknown restriction

unknown detail enum
  -> unknown restriction

structured candidate disagrees with fallback
  -> union, not permissive replacement

candidate attempts runtime-open authority
  -> policy_authority_not_permitted
  -> restrictive / non-authoritative

validation failure with no surviving detail
  -> unknown restriction

unknown requested detail in Grounded Recall
  -> unsupported detail count increments
```

There is no path in this contract where malformed analyzer input weakens unsupported-detail suppression.

## Stable invariants

- Query Detail Analyzer schema identity is `relaylm.query_detail_analyzer.v0`.
- Analyzer kind is `query_detail_candidate`.
- Requested-detail vocabulary is fixed and English-schema based.
- Fallback regex output is candidate-only and restrictive.
- Structured candidates are unioned with fallback detail types rather than replacing them.
- Unknown/malformed detail input closes to `unknown`.
- Query Detail Analyzer refuses runtime-opening authority even when shared governance would otherwise permit it.
- Public projection is content-free and uses bounded reason/error IDs.
- Grounded Recall consumes detail classes request-side; Query Detail Analyzer does not rewrite visible output.
- Unsupported requested detail cannot become remembered fact merely because a candidate says it was requested.
- Query-detail analysis does not select memory authority, grant retrieval/disclosure access, or mutate persistent state.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- the shared Analyzer Candidate Governance schema outside the producer-specific binding described here;
- full Grounded Recall context/evidence schema;
- memory lifecycle/scope/provenance eligibility;
- Primary versus Subjective MEM reader selection;
- retrieval ranking or candidate discovery;
- memory write, Correct, Forget, Restore, Pin/Unpin, or Held governance;
- LLM classifier prompts or a requirement to use an LLM classifier;
- exact regex source-code literals;
- visible-response rewriting;
- worker, queue, scheduler, or background execution;
- source retirement or documentation migration disposition.

## Related authority

- [Analyzer Candidate Governance](../architecture/analyzers/candidate-governance.md)
- [Memory Retrieval and Grounding](../architecture/memory/retrieval-and-grounding.md)
- [E1-R4 Retrieval Response Grounding source](../architecture/e1r4_retrieval_response_grounding.md)
- [Analyzer Candidate Governance exact contract](analyzer-candidate.md)
