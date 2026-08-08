---
relaylm_doc_type: contract
relaylm_authority: current_analyzer_candidate_governance_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: analyzers
relaylm_update_trigger:
  - analyzer candidate schema keys or enum values change
  - source-authority or runtime-open policy changes
  - candidate normalization or fail-closed validation changes
  - public content-free projection changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - analyzer producer/classifier algorithms or prompts
  - RelaySCN, RelayINT, RelayMEM, RelayEMO, RelayCTX, or response-policy semantics
  - source-specific authority facts supplied by routes, tools, explicit actions, or product policy
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/analyzers/candidate-governance.md
  - ../architecture/analyzers/reference-and-intent.md
  - ../architecture/acg1_analyzer_candidate_governance_contract.md
relaylm_verified_by:
  - ../../scripts/relaylm_analyzer_governance_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - shared analyzer candidate producers and consumers
  - RelaySCN, RelayINT, RelayMEM, RelayEMO, RelayCTX, and runtime-policy maintainers
  - privacy, diagnostics, security, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Analyzer Candidate Governance Contract

## Authority summary

This contract owns the exact current shared Analyzer Candidate Governance boundary implemented by:

```text
relaylm/analyzer_governance.py
```

The contract exists so heuristic/model-derived analyzer output remains a **candidate** unless a separately trusted authority permits it to affect runtime policy.

The shared boundary owns:

- the current common candidate schema and enum vocabulary;
- source-class normalization;
- fail-closed authority normalization;
- bounded runtime-open eligibility;
- validation/error reason sanitization;
- content-free public projection.

It does not own the semantic logic of any individual analyzer producer.

## Current schema version

The exact current schema identifier is:

```text
relaylm.analyzer_candidate_governance.v0
```

A different or missing `schema_version` is normalized with validation error:

```text
unknown_enum_value
```

## Current analyzer kinds

The current common analyzer kinds are exactly:

```text
affect_candidate
query_detail_candidate
reference_intent_candidate
retrieval_query_candidate
scene_policy_candidate
```

Normalization may additionally emit the fail-closed token:

```text
unknown
```

An unknown analyzer kind cannot retain runtime authority.

## Current source classes

The exact current source classes are:

```text
confirmed_user_action
fallback_regex
heuristic
llm_candidate
locale_marker
trusted_explicit
trusted_route
trusted_tool_signal
unknown
```

The trusted source-class set is exactly:

```text
confirmed_user_action
trusted_explicit
trusted_route
trusted_tool_signal
```

The non-authoritative source-class set is exactly:

```text
fallback_regex
heuristic
llm_candidate
locale_marker
unknown
```

Source class is a candidate-governance input. A class name alone does not make a source authoritative; the normalized artifact must also satisfy the current authority rules.

## Current policy-authority values

The exact current policy-authority vocabulary is:

```text
bounded
broad
mutation
none
open
restrictive
rewrite
scene_policy
update
```

The only authority in the current runtime-open set is:

```text
bounded
```

No other policy-authority token opens runtime policy through `can_open_runtime_policy(...)`.

## Runtime-open thresholds

The exact current minimums are:

```text
confidence >= 0.4
stability  >= 0.4
```

Both values are normalized into finite floats within `[0.0, 1.0]`. Invalid, non-finite, boolean, negative, or greater-than-one values normalize to `0.0` with the appropriate malformed-value validation error.

## Confidence and stability buckets

The exact public bucket rules are:

```text
value >= 0.75 -> high
value >= 0.40 -> medium
otherwise     -> low
```

The current bucket vocabularies are therefore:

```text
low
medium
high
```

## Current artifact keys

The normalized internal artifact contains exactly:

```text
schema_version
analyzer_kind
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
reason_ids
enum_values
```

`build_analyzer_candidate_artifact(...)` accepts those fields as its shared schema and treats additional keyword fields as unsupported diagnostics rather than extending authority dynamically.

## Builder defaults

Current builder defaults are:

```text
source_language = und
is_estimate = true
source_authoritative = false
candidate_applied = false
policy_authority = none
restrictive_only = null
confidence = 0.0
stability = 0.0
content_free = false
validation_errors = []
reason_ids = []
enum_values = []
```

The builder then normalizes the constructed artifact through the same canonical normalization path used by direct validation.

## Unknown extra fields

Additional builder fields do not become new schema keys.

Known raw/content-like key names are dropped with:

```text
raw_diagnostic_field_dropped
```

Other unsupported keys are dropped with:

```text
unsupported_field_dropped
```

The normalized public projection never echoes the discarded value.

## Raw/content-like field names

The current explicitly recognized raw/content-like key set is:

```text
assistant_text
external_signal_body
filesystem_path
memory_text
queue_payload
rationale
raw_assistant_text
raw_text
raw_user_text
relationship_markdown
scene_markdown
signals
source_markdown
user_text
```

These names are validation/drop guards, not accepted public fields.

## Source-language normalization

`source_language` must be a string that, after trim/lowercase normalization:

- is non-empty;
- is at most 16 characters;
- contains only ASCII alphanumeric characters, `-`, or `_`.

Failure normalizes to:

```text
und
```

and records:

```text
invalid_source_language
```

The current shared contract does not infer a locale from user text.

## Boolean normalization

Required boolean-like fields are accepted only when the input is an actual boolean or `None` where a default is defined.

The current fields and malformed-value errors are:

```text
is_estimate            -> malformed_is_estimate
source_authoritative   -> malformed_source_authoritative
candidate_applied      -> malformed_candidate_applied
content_free           -> invalid_content_free_flag
```

`restrictive_only` is optional; a non-boolean, non-null value records:

```text
malformed_restrictive_only
```

and normalizes to `None` before authority rules derive its final boolean value.

## Analyzer-kind fail closed

If `analyzer_kind` is not one of the current common kinds:

```text
analyzer_kind = unknown
validation error += invalid_analyzer_kind
```

Before the normalized artifact is returned, an `unknown` analyzer kind forces:

```text
source_authoritative = false
policy_authority = none
restrictive_only = true
candidate_applied = false
```

The contract never guesses a nearby analyzer kind.

## Source-class fail closed

If `source` is not one of the current source classes:

```text
source = unknown
validation error += invalid_source_class
```

An `unknown` source ultimately forces:

```text
source_authoritative = false
policy_authority = none
restrictive_only = true
candidate_applied = false
```

Unknown source content cannot open runtime behavior.

## Unknown policy authority

If `policy_authority` is outside the exact current vocabulary:

```text
policy_authority = none
validation error += unknown_policy_authority
```

The unknown value is not preserved into the public projection.

## Non-authoritative source rule

For any source in:

```text
fallback_regex
heuristic
llm_candidate
locale_marker
unknown
```

normalization enforces:

```text
source_authoritative = false
restrictive_only = true
```

If the source claimed `source_authoritative=true`, normalization also records:

```text
non_authoritative_source
```

If a non-authoritative source requests a policy authority other than `none` or `restrictive`, normalization records:

```text
policy_authority_not_permitted
```

and closes the effective authority to `none`.

A requested `restrictive` authority may remain `restrictive`, but it does not enter the runtime-open set.

## Non-authoritative candidate application

For `source=unknown`, normalization additionally forces:

```text
candidate_applied = false
```

Other known non-authoritative sources may retain the candidate-applied boolean as a diagnostic fact, but they remain restrictive-only and cannot pass current runtime-open authority.

A candidate-applied flag is therefore never sufficient authority by itself.

## Non-authoritative reason IDs

Normalization appends one of these bounded reasons:

```text
heuristic
  -> heuristic_restrictive_only

llm_candidate
  -> llm_candidate_restrictive_only

fallback_regex / locale_marker / unknown
  -> fail_closed_candidate_source
```

These reason IDs are diagnostics and do not elevate authority.

## Trusted-source rule

For a trusted/confirmed source class, `restrictive_only` is derived when omitted:

```text
restrictive_only = policy_authority not in {bounded}
```

If the artifact requests `bounded` while `source_authoritative` is false:

```text
validation error += policy_authority_not_permitted
policy_authority = none
restrictive_only = true
```

Thus a trusted class still needs an explicit authoritative source decision before it can retain the current runtime-open policy class.

## Authoritative but unapplied candidate

For a trusted source with:

```text
source_authoritative = true
candidate_applied = false
```

normalization appends:

```text
candidate_not_applied
```

This reason does not itself invalidate the artifact, but `can_open_runtime_policy(...)` still requires `candidate_applied=true`.

## Validation summary object

`validate_analyzer_candidate_artifact(...)` returns `AnalyzerCandidateValidation` with:

```text
artifact
is_valid
validation_error_ids
```

`is_valid` is exactly:

```text
not validation_error_ids
```

`to_public_dict()` emits the normal content-free projection and adds:

```text
is_valid
```

No raw validation detail is added.

## Policy-authoritative predicate

`is_policy_authoritative(...)` first normalizes the artifact.

It returns true only when all are true:

```text
validation_errors is empty
source is in trusted source classes
source_authoritative is true
policy_authority != none
```

This predicate can therefore recognize a trusted restrictive authority as policy-authoritative while still not allowing it to open runtime behavior.

## Runtime-open predicate

`can_open_runtime_policy(...)` requires all of:

```text
is_policy_authoritative(...) is true
candidate_applied is true
policy_authority == bounded
restrictive_only is false
confidence >= 0.4
stability >= 0.4
```

Failure of any term returns false.

The current shared governance contract does not provide a generic path for `broad`, `open`, `update`, `rewrite`, `mutation`, or `scene_policy` to open runtime behavior.

## Reason-ID sanitization

The current known reason-ID set is exactly:

```text
candidate_not_applied
fail_closed_candidate_source
heuristic_restrictive_only
invalid_analyzer_kind
invalid_content_free_flag
invalid_source_class
invalid_source_language
llm_candidate_restrictive_only
malformed_candidate_applied
malformed_confidence
malformed_is_estimate
malformed_reason_id
malformed_restrictive_only
malformed_source_authoritative
malformed_stability
non_authoritative_source
policy_authority_not_permitted
raw_diagnostic_field_dropped
unsupported_field_dropped
unknown_enum_value
unknown_policy_authority
unknown_reason
```

Unknown/malformed reason input is replaced by the fixed token:

```text
unknown_reason
```

and records `malformed_reason_id` as appropriate.

Reason lists are de-duplicated while preserving first occurrence order.

## Enum-value sanitization

`enum_values` may contain only values from the current analyzer kinds, source classes, policy authorities, confidence/stability buckets, known reason IDs, current schema version, or `unknown`.

Malformed/unknown enum values become:

```text
unknown_enum_value
```

and the same bounded validation token is recorded.

The public projection does not expose the private/internal `enum_values` array.

## Content-free public projection

`content_free_projection(...)` emits exactly:

```text
schema_version
analyzer_kind
source_class
source_authoritative
policy_authority
restrictive_only
candidate_applied
confidence_bucket
stability_bucket
reason_ids
validation_error_ids
content_free
```

The projection always sets:

```text
content_free = true
```

It emits bucketed confidence/stability rather than raw numeric values.

It uses `source_class` rather than the internal `source` key.

## Public projection omissions

The current public projection does not expose:

- raw user or assistant text;
- free-form analyzer rationale;
- source Markdown;
- memory text;
- relationship or scene Markdown;
- queue payload bodies;
- filesystem paths;
- raw external signal bodies;
- raw confidence/stability numbers;
- internal enum-value arrays.

The shared contract is intentionally usable for public/content-free diagnostics without turning candidate analysis into a content-bearing trace surface.

## Enum introspection

`analyzer_governance_enum_values()` returns sorted tuples for:

```text
analyzer_kind
source_class
policy_authority
confidence_bucket
stability_bucket
reason_id
schema_key
```

The analyzer-kind tuple includes the fail-closed `unknown` token.

The schema-key tuple is the union of current accepted artifact keys, public projection keys, and the shared validation/public helper keys `is_valid`, `source_class`, and `validation_error_ids`.

## Candidate versus authority invariant

The foundational rule is:

```text
candidate signal
  != trusted source
  != source_authoritative
  != policy authority
  != candidate applied
  != runtime-open authority
```

A model/heuristic can produce a useful candidate without acquiring the power to broaden retrieval, mutate memory/SOUL, rewrite output, or become current scene policy.

## Restrictive-only use

Heuristic/model/locale/fallback candidates may still support restrictive or fail-closed behavior when their owning consumer explicitly uses them that way.

The shared governance layer does not define the consumer-specific restriction semantics.

It only ensures such candidates cannot silently become a generic positive/opening authority.

## Producer responsibility

Individual producers remain responsible for their own semantic evidence and candidate-specific fields before they enter the shared governance boundary.

Examples include:

- Grounded Recall/query-detail producers;
- retrieval-query normalization;
- reference/intent analysis;
- affect cleanup/candidates;
- scene-policy classification.

Those producers must not treat a shared governance projection as semantic proof beyond the authority encoded by this contract.

## Consumer responsibility

Consumers must preserve their own domain gates.

Passing `can_open_runtime_policy(...)` means only that the shared candidate-governance preconditions for the current bounded runtime-open class are satisfied.

It does not by itself authorize:

- a specific memory mutation;
- a SOUL patch;
- a scene state change;
- a broad retrieval fallback;
- response rewriting;
- disclosure of protected content.

The owning subsystem remains final authority for those effects.

## Stable invariants

- The current shared schema is `relaylm.analyzer_candidate_governance.v0`.
- Analyzer/source/policy vocabularies are fixed and English-only at this contract boundary.
- Unknown analyzer/source/policy input fails closed to bounded fixed tokens.
- Non-authoritative source classes cannot retain runtime-opening authority.
- A trusted source class alone is insufficient; explicit `source_authoritative` is also required.
- Current generic runtime-open authority is only `bounded`.
- Runtime opening additionally requires applied candidate, non-restrictive state, and confidence/stability at least 0.4.
- Unknown/malformed reason and enum input is sanitized rather than echoed.
- Public diagnostics are content-free and use buckets rather than raw confidence/stability values.
- Candidate governance does not own producer semantics or downstream subsystem mutation authority.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- individual analyzer prompts or classifier logic;
- model selection;
- domain-specific confidence thresholds beyond the shared runtime-open gate;
- RelaySCN scene-selection semantics;
- RelayINT request semantics;
- RelayMEM retrieval/mutation semantics;
- RelayEMO affect-state semantics;
- RelayCTX persistence/context semantics;
- response rewriting or disclosure policy;
- source retirement;
- repository-level sequencing.

## Related architecture and transitional source

- [Analyzer Candidate Governance Architecture](../architecture/analyzers/candidate-governance.md)
- [Reference and Intent Analyzer Architecture](../architecture/analyzers/reference-and-intent.md)
- [ACG-1 transitional implementation contract](../architecture/acg1_analyzer_candidate_governance_contract.md)
