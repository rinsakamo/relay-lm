---
relaylm_doc_type: contract
relaylm_authority: current_reference_intent_analyzer_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: analyzers
relaylm_update_trigger:
  - Reference/Intent Analyzer schema or enum changes
  - reference-kind priority, ambiguity, clarification, or confidence semantics change
  - analyzer normalization or fail-closed behavior changes
  - RelayREF or RelayINT consumption of the shared analyzer changes
  - public reference/intent projection changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - shared Analyzer Candidate Governance fields or thresholds
  - exact locale-marker literal inventory beyond the current detector categories and compatibility examples
  - RelayINT quick-clarification preflight/apply-plan schemas
  - target relayint.intent.v1 migration completion
  - memory reader selection, retrieval ranking, persistence, scene policy, or RelayCTX storage semantics
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/analyzers/candidate-governance.md
  - ../architecture/analyzers/reference-and-intent.md
  - ../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md
relaylm_related_contracts:
  - analyzer-candidate.md
  - relayint_quick_clarification_runtime_contract.md
relaylm_verified_by:
  - ../../scripts/relaylm_acg4_reference_intent_analyzer_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Reference/Intent Analyzer maintainers
  - RelayREF and RelayINT request-interpretation maintainers
  - RelayMEM Retrieval, RelayCTX, multilingual, privacy, security, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Reference / Intent Analyzer Contract

## Authority summary

This contract owns the exact current shared Reference/Intent Analyzer boundary implemented by:

```text
relaylm/reference_intent_analyzer.py
```

The analyzer centralizes request-local unresolved-reference, continuation, prior-memory-request, ambiguous-choice, context-repair, and related intent detection behind one ACG-governed candidate artifact.

The stable current flow is:

```text
latest user text + optional request-local context hints
  -> shared locale/marker candidate detection
  -> fixed reference/intent schema
  -> Analyzer Candidate Governance normalization
  -> content-free public projection
  -> RelayREF / RelayINT compatibility consumers
```

The analyzer is an interpretation candidate producer. It does not choose an ordinary memory reader, open broad retrieval, authorize memory mutation, persist a reference, override scene/privacy policy, or directly emit user-visible clarification text.

## Current implementation anchors

The exact producer and normalizer live in:

```text
relaylm/reference_intent_analyzer.py
```

Current integration evidence is exercised by:

```text
scripts/relaylm_acg4_reference_intent_analyzer_smoke.py
```

Current downstream compatibility consumers include RelayREF and RelayINT. Their own action-plan and runtime contracts remain separate authorities.

## Current schema identity

The exact current schema identifier is:

```text
relaylm.reference_intent_analyzer.v0
```

The exact analyzer kind is:

```text
reference_intent_candidate
```

A different analyzer kind normalizes to `unknown` and records `invalid_analyzer_kind`.

A missing or different schema version records `unknown_enum_value`.

## Reference-kind vocabulary

The current accepted reference kinds are exactly:

```text
none
unresolved_deictic
prior_turn_reference
prior_memory_reference
ambiguous_choice
context_repair_request
unknown
```

Unknown or malformed input normalizes to:

```text
unknown
```

and records:

```text
unknown_enum_value
```

## Intent-kind vocabulary

The current accepted intent kinds are exactly:

```text
continuation
clarification_request
prior_memory_request
correction_request
review_request
implementation_request
unknown
```

A string input is treated as one intent value. Other iterable inputs are normalized item by item and de-duplicated in first-seen order.

If any normalized intent value is `unknown`, the normalized intent list collapses to exactly:

```text
["unknown"]
```

An empty intent list is valid when no current intent marker is detected.

## Analyzer inputs

`analyze_reference_intent(...)` currently accepts:

```text
messages
text
ctx_hints
source
source_language
```

Current defaults are:

```text
source = locale_marker
ctx_hints = {}
```

When `text` is a string, that exact request-local string is the detection input.

Otherwise the analyzer walks `messages` from newest to oldest and uses the newest mapping whose `role` is `user`.

For string message content, the string is used directly.

For sequence-style content, the analyzer joins the `text` value of mapping items with newline separators.

Other content shapes produce an empty input string.

Raw text is detection input only and is not copied into the public projection.

## Language handling

When `source_language` is supplied, it is passed to shared governance as the requested source-language value.

Otherwise current language detection delegates to the shared reference-language detector in:

```text
relaylm/_analyzer_text_features.py
```

The public schema exposes only the normalized bounded source-language value produced by governance.

## Marker categories

Current detection counts marker matches in these shared categories:

```text
PRIOR_MEMORY_REQUEST_MARKERS
CONTINUATION_MARKERS
UNRESOLVED_REFERENCE_MARKERS
AMBIGUOUS_CHOICE_MARKERS
CONTEXT_REPAIR_MARKERS
CORRECTION_MARKERS
REVIEW_MARKERS
IMPLEMENTATION_MARKERS
```

The exact literal inventory remains an implementation detail of the shared text-feature helper, but category ownership is centralized here: RelayREF and RelayINT do not regain independent competing natural-language dictionaries for this responsibility.

Compatibility evidence currently includes at least:

```text
unresolved/reference:
  それ
  これ
  あれ
  さっき
  どっち
  どれ
  この件
  前の
  which one
  what was that
  what were we

prior memory:
  前に話した
  覚えてる
  思い出して
  前回
  previous
  remember

continuation:
  続き
  その方向
  それで
  continue
```

These examples are compatibility probes, not a second marker-list authority.

## Reference-kind selection priority

Current reference-kind selection is deterministic and priority ordered.

Given current category counts, the analyzer returns the first matching class in this exact order:

```text
prior_memory_count > 0
  -> prior_memory_reference

ambiguous_choice_count > 0
  -> ambiguous_choice

context_repair_count > 0
  -> context_repair_request

continuation_count > 0
  -> prior_turn_reference

unresolved_count > 0
  -> unresolved_deictic

otherwise
  -> none
```

A lower-priority marker does not replace a higher-priority classification when both are present.

## Intent construction order

Current intent kinds are appended in this exact order when their conditions are true:

```text
continuation
clarification_request
prior_memory_request
correction_request
review_request
implementation_request
```

The conditions are:

```text
continuation
  -> continuation marker count > 0

clarification_request
  -> unresolved marker count > 0

prior_memory_request
  -> prior-memory marker count > 0

correction_request
  -> correction marker count > 0

review_request
  -> review marker count > 0

implementation_request
  -> implementation marker count > 0
```

This intent list is descriptive candidate structure. It does not itself authorize the corresponding downstream action.

## Request-local context signal

Current ambiguity handling recognizes a bounded request-local context signal.

A context signal is present when any of these keys contains a non-empty string:

```text
current_topic
active_question
next_expected_action
```

or when `referable_items` is a list containing at least one mapping with a non-empty string in any of:

```text
label
kind
id
topic_anchor
text
name
```

The analyzer checks only whether a usable signal exists. It does not copy those context values into public diagnostics and does not persist them.

## Ambiguity rule

Current `ambiguity_detected` behavior is exactly:

```text
reference_kind == none
  -> false

prior_memory_request_detected == true
  -> false

continuation_detected == true
  -> not ctx_signal_present

all other non-none reference kinds
  -> true
```

Therefore a continuation candidate with an adequate current request-local context signal can remain non-ambiguous, while the same continuation without such a signal becomes ambiguous.

A prior-memory request is not marked ambiguous by this helper merely because it refers to earlier information; downstream retrieval and scope gates remain authoritative.

## Clarification recommendation

Current clarification recommendation is:

```text
clarification_recommended =
  unresolved_reference_detected
  OR ambiguity_detected
```

This is a candidate recommendation only. It does not authorize a visible response short circuit.

The separate RelayINT quick-clarification runtime contract owns current plan-only clarification stages and their compatibility gates.

## Reference-term count

Current `reference_terms_detected_count` is exactly the sum of:

```text
prior_memory_count
+ continuation_count
+ unresolved_count
```

It does not include ambiguous-choice, context-repair, correction, review, or implementation marker counts.

This distinction is observable in current behavior and must not be silently rewritten as a count of all analyzer signals.

## Confidence rule

The current confidence score is exact and branch ordered:

```text
prior_memory_request_detected
  -> 0.82

ambiguity_detected
  -> 0.48

continuation_detected AND ctx_signal_present
  -> 0.84

reference_kind == none
  -> 0.74

otherwise
  -> 0.60
```

The same value is supplied to shared governance as both:

```text
confidence
stability
```

These numbers are analyzer confidence/stability inputs only. They are not source provenance, memory confidence, scene authority, or mutation permission.

## Current governance construction

`analyze_reference_intent(...)` constructs the shared governance artifact with:

```text
analyzer_kind = reference_intent_candidate
source = caller source, default locale_marker
source_language = normalized/detected language
is_estimate = true
source_authoritative = false
candidate_applied = reference_terms_detected_count > 0
policy_authority = restrictive if clarification_recommended else none
restrictive_only = true
confidence = current confidence score
stability = current confidence score
content_free = true
```

Current reason IDs are:

```text
reference_kind != none
  -> fail_closed_candidate_source

ambiguity_detected OR clarification_recommended
  -> candidate_not_applied
```

The candidate remains subordinate to shared Analyzer Candidate Governance.

Locale/marker detection does not become trusted merely because a confidence value is high.

## Current candidate-applied nuance

`candidate_applied` is currently initialized from:

```text
reference_terms_detected_count > 0
```

Because the count includes prior-memory, continuation, and unresolved markers only, an `ambiguous_choice` or `context_repair_request` can exist while the initial count-derived candidate-applied flag is false.

This is current behavior, not authority for downstream code to ignore those reference kinds.

## Normalized artifact keys

The normalized artifact currently returns these keys:

```text
schema_version
analyzer_kind
source
source_language
reference_kind
intent_kinds
ambiguity_detected
unresolved_reference_detected
prior_memory_request_detected
continuation_detected
clarification_recommended
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
reference_terms_detected_count
runtime_policy_open_allowed
governance
governance_public
```

The analyzer also accepts those schema keys when normalizing an artifact.

## Unsupported-field handling

The current explicit raw/content-like key names are:

```text
assistant_text
external_signal_body
memory_text
queue_payload
rationale
raw_assistant_text
raw_text
raw_user_text
signals
source_markdown
user_text
```

An unsupported key in that set is dropped and records:

```text
raw_diagnostic_field_dropped
```

Other unsupported keys are dropped and record:

```text
unsupported_field_dropped
```

Discarded values are not echoed into the normalized public projection.

## Fail-closed enum normalization

A malformed analyzer kind becomes:

```text
analyzer_kind = unknown
```

A malformed reference kind becomes:

```text
reference_kind = unknown
```

A malformed intent member becomes `unknown`; if present, the full normalized intent list becomes exactly `["unknown"]`.

The normalizer defines an invalid-detection condition when any of these are true:

```text
analyzer_kind == unknown
reference_kind == unknown
intent_kinds == ["unknown"]
```

## Invalid detection flags are removed

When the invalid-detection condition is true, the following normalized booleans are forced false:

```text
ambiguity_detected
unresolved_reference_detected
prior_memory_request_detected
continuation_detected
clarification_recommended
```

If the input attempted to set any of those flags true, normalization records:

```text
invalid_detection_flags_dropped
```

The same invalid-detection condition also forces:

```text
reference_terms_detected_count = 0
candidate_applied = false
policy_authority = none
runtime_policy_open_allowed = false
```

Malformed candidate structure therefore loses action authority rather than retaining optimistic detection flags.

## Governance normalization fallback

When the input contains a mapping under `governance`, that mapping is normalized by shared Analyzer Candidate Governance.

When no valid governance mapping is present, this analyzer builds a fail-closed governance artifact with:

```text
analyzer_kind = reference_intent_candidate
source = supplied bounded source or unknown
source_language = supplied bounded language or und
is_estimate = true
source_authoritative = false
candidate_applied = false
policy_authority = none
restrictive_only = true
confidence = 0.0
stability = 0.0
content_free = true
```

Existing validation errors are carried into that governance normalization.

## Runtime-policy-open field

The normalized artifact reports:

```text
runtime_policy_open_allowed
```

as:

```text
false
  when invalid-detection condition is true

otherwise
  can_open_runtime_policy(normalized_governance)
```

The current default locale-marker analyzer construction is non-authoritative/restrictive and therefore does not open runtime policy.

A consumer must not treat this field as memory reader selection or mutation authority even if a future separately trusted governance source becomes eligible under the shared governance contract.

## Public projection

`reference_intent_public_projection(...)` exposes exactly:

```text
schema_version
analyzer_kind
source
source_language
reference_kind
intent_kinds
ambiguity_detected
unresolved_reference_detected
prior_memory_request_detected
continuation_detected
clarification_recommended
confidence_bucket
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
content_free
reason_ids
validation_error_ids
reference_terms_detected_count
runtime_policy_open_allowed
governance
```

`intent_kinds`, `reason_ids`, and `validation_error_ids` are exposed as tuple projections.

`governance` is the shared content-free governance projection, not the internal governance artifact.

The public projection does not expose raw user text, assistant text, matched marker bodies, memory text, protected source bodies, free-form rationale, queue payloads, or private context values.

## Legacy RelayINT mapping

`relayint_legacy_reference_kind(...)` currently maps the normalized analyzer artifact in this exact priority:

```text
prior_memory_request_detected
  -> prior_memory_request

continuation_detected
  -> continuation

unresolved_reference_detected
  -> pronoun_like

otherwise
  -> none
```

Malformed artifacts that lose their detection flags therefore map to `none`.

This function is a compatibility adapter. It does not redefine the analyzer's reference-kind vocabulary.

## RelayREF compatibility consumption

Current ACG-4 smoke evidence requires RelayREF dry-run output to consume the shared analyzer and preserve content-free unresolved-reference behavior.

The shared analyzer is the lexical/marker owner. RelayREF does not regain authority to create a competing marker dictionary for the same reference semantics.

## RelayINT compatibility consumption

Current RelayINT fast-path evidence requires the shared analyzer to drive compatible fields such as:

```text
explicit_prior_memory_request_detected
detected_reference_kind
ambiguity_detected
reference_intent_analyzer
```

The fast-path action taxonomy, confidence thresholds, quick-clarification stages, request compatibility gate, and plan-only apply behavior remain owned by the separate RelayINT quick-clarification runtime contract.

## Authority separation

The following are distinct decisions:

```text
reference/intent candidate detected
  != candidate structurally valid
  != source authoritative
  != runtime policy may open
  != RelayINT action selected
  != durable retrieval authorized
  != memory reader family selected
  != user-visible clarification applied
```

No consumer may collapse those transitions merely because the analyzer detected a prior-memory or continuation marker.

## Failure direction

Current failures close toward less inferred authority:

```text
unknown schema / analyzer kind / enum
  -> bounded unknown
  -> detection flags removed when invalid
  -> candidate_applied false
  -> policy_authority none
  -> runtime_policy_open_allowed false

raw/content-like unsupported field
  -> value dropped
  -> bounded validation error only

ambiguous reference without usable current context
  -> ambiguity true
  -> clarification recommended
  -> no broad retrieval authority minted
```

The analyzer never repairs malformed content by echoing unknown values into public diagnostics.

## Stable invariants

- `relaylm.reference_intent_analyzer.v0` is the current producer schema.
- `reference_intent_candidate` is the current analyzer kind.
- Reference and intent enum vocabularies remain bounded English machine values.
- Reference-kind selection follows the current priority order.
- Marker-source detection is non-authoritative by default.
- Current context affects continuation ambiguity only through bounded presence checks.
- Prior-memory request detection does not itself create ambiguity or reader authority.
- Clarification recommendation is `unresolved OR ambiguous`.
- Public diagnostics remain content-free.
- Unknown enum structure fails closed and cannot retain positive detection flags.
- RelayREF and RelayINT consume the shared analyzer rather than owning competing marker semantics.
- Shared Analyzer Candidate Governance remains the authority for common source/policy normalization.
- RelayINT runtime action/clarification planning remains separately owned.

## Non-goals

This contract does not define:

- a full LLM intent classifier;
- exact future `relayint.intent.v1` migration completion;
- RelayINT quick-clarification action-plan taxonomies;
- ordinary memory reader selection;
- Primary versus Subjective retrieval authority;
- retrieval eligibility, ranking, lifecycle, or provenance rules;
- memory mutation or persistence;
- RelaySCN scene classification;
- RelayCTX durable storage;
- user-visible clarification rendering or response short-circuit execution;
- source retirement or redirect creation;
- repository-level implementation sequencing.

## Related authority

- [Analyzer Candidate Governance Contract](analyzer-candidate.md)
- [Reference and Intent Architecture](../architecture/analyzers/reference-and-intent.md)
- [RelayINT Quick-Clarification Runtime Contract](relayint_quick_clarification_runtime_contract.md)
- [PM-D6 RelayINT Native Artifact / RelayREF Wrapper Removal](../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md)
