---
relaylm_doc_type: contract
relaylm_authority: current_retrieval_query_analyzer_and_private_hint_projection_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: analyzers
relaylm_update_trigger:
  - Retrieval Query Analyzer schema or hint strategy changes
  - backend-private retrieval hint generation or bounding changes
  - ambiguous-reference detection changes
  - public retrieval-query projection changes
  - dry-run retrieval consumption of analyzer hints changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - shared Analyzer Candidate Governance fields or thresholds
  - ordinary memory reader authority or Primary/Subjective cutover state
  - retrieval evidence eligibility, lifecycle, provenance, scope, or final ranking authority
  - RelayINT reference-resolution authority
  - memory mutation, storage repair, worker, scheduler, queue, or background behavior
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/analyzers/candidate-governance.md
  - ../architecture/memory/retrieval-and-grounding.md
  - ../architecture/e1r5_primary_mem_recall_candidate_bridge.md
relaylm_related_contracts:
  - analyzer-candidate.md
relaylm_verified_by:
  - ../../scripts/relaylm_acg3_retrieval_query_normalization_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Retrieval Query Analyzer maintainers
  - RelayMEM read-only retrieval and diagnostics maintainers
  - analyzer governance, multilingual, privacy, security, and documentation reviewers
relaylm_authority_level: exact_contract
---
# Retrieval Query Analyzer Contract

## Authority summary

This contract owns the exact current Retrieval Query Analyzer boundary implemented by:

```text
relaylm/retrieval/query_analyzer.py
```

and its bounded consumption in the legacy/current dry-run retrieval assembly path implemented by:

```text
relaylm/retrieval/dry_run.py
```

The analyzer turns request-local query text into bounded **backend-private hint strings** plus a separate **content-free public projection**.

It is a restrictive interpretation helper only. It does not choose the ordinary memory family, widen retrieval scope, make an ineligible memory eligible, resolve ambiguous references, authorize mutation, or mint durable state.

The current responsibility split is:

```text
request-local latest user text
  -> Retrieval Query Analyzer
  -> bounded private hint candidates
  -> already-authorized read-only candidate discovery

same analyzer artifact
  -> content-free public projection
  -> diagnostics only
```

The private hint artifact may contain derived query strings. The public projection must not.

## Current implementation anchors

The exact current analyzer owner is:

```text
relaylm/retrieval/query_analyzer.py
```

The current retrieval consumer and projection assembly are:

```text
relaylm/retrieval/dry_run.py
relaylm/retrieval/candidates.py
```

The shared analyzer-governance authority remains:

```text
relaylm/analyzer_governance.py
```

This contract does not duplicate the shared governance field/threshold contract. It defines the producer-specific Retrieval Query Analyzer behavior layered on top of that shared authority.

## Current schema identity

The exact current Retrieval Query Analyzer schema version is:

```text
relaylm.retrieval_query_analyzer.v0
```

The analyzer kind is exactly:

```text
retrieval_query_candidate
```

The current producer always builds its shared governance artifact with that analyzer kind.

## Current hint-strategy vocabulary

The exact accepted strategy set is:

```text
empty_fallback
whitespace_fallback
bounded_ngram_fallback
mixed_fallback
```

A caller-supplied strategy outside this set does not select a nearby strategy.

It becomes the internal token:

```text
unknown
```

and adds:

```text
unknown_query_hint_strategy
```

to validation errors. An unknown strategy emits no backend-private hints.

## Current analyzer bounds

The current analyzer-level bounds are:

```text
maximum emitted backend-private hints = 6
maximum ordinary hint length          = 32 characters
maximum generated n-gram hints        = 6
maximum generated n-gram length       = 8 characters
```

`max_hints` is normalized into the inclusive range:

```text
0..6
```

Boolean values are not treated as integer hint limits; they fall back to the default bound.

Values that cannot be converted to an integer also fall back to the default.

## Input normalization

`analyze_retrieval_query(...)` accepts request-local text as:

```text
str | None
```

Any non-string value is treated as empty text.

The producer may receive:

```text
source
source_language
query_hint_strategy
max_hints
```

The source defaults to:

```text
heuristic
```

The source language uses the explicitly supplied value when truthy; otherwise it is estimated from the request-local text by the bounded analyzer text-feature helper.

This contract does not grant source authority merely because a caller supplied a source name or language.

## Current whitespace hint extraction

Whitespace fallback starts from the request-local text with newlines replaced by spaces, then splits on ASCII space.

Each candidate passes through the bounded cleaner:

```text
trim configured surrounding punctuation/whitespace
collapse internal whitespace runs to one ASCII space
truncate to at most 32 characters
```

Whitespace terms shorter than three characters are discarded.

Duplicates are removed while preserving first-seen order.

Extraction stops at the normalized `max_hints` bound.

## Current bounded n-gram extraction

The n-gram path first compacts the input by removing configured punctuation/spacing characters and ASCII control characters.

The compact source is truncated to at most:

```text
128 characters
```

If fewer than two compact characters remain, no n-gram hint is emitted.

The current n-gram width is:

```text
3 characters when compact length >= 3
2 characters when compact length == 2
```

Generated n-grams are cleaned, must remain at least two characters, are de-duplicated in first-seen order, and stop at the configured bounded n-gram count.

This is a bounded lexical candidate mechanism. It is not semantic retrieval authority.

## Automatic strategy selection

When no explicit `query_hint_strategy` is supplied, current selection is deterministic:

```text
whitespace terms + n-grams + no-whitespace text
  -> mixed_fallback

whitespace terms + n-grams + CJK text
  -> mixed_fallback

whitespace terms only or ordinary whitespace text
  -> whitespace_fallback

no whitespace terms + n-grams
  -> bounded_ngram_fallback

no usable hints
  -> empty_fallback
```

The selected strategy determines which private hints are returned.

## Strategy output behavior

### `whitespace_fallback`

The private hint list is the bounded whitespace-term list.

### `bounded_ngram_fallback`

The private hint list is the bounded n-gram list.

### `mixed_fallback`

The private hint list is the first-seen-order de-duplicated concatenation of:

```text
whitespace terms
then n-gram hints
```

bounded to the normalized maximum.

### `empty_fallback`

The private hint list is empty.

### unknown strategy

The private hint list is empty and the validation error records `unknown_query_hint_strategy`.

There is no permissive fallback from an unknown strategy to broad query text.

## Current analyzer artifact

The producer returns a mapping containing the current producer-specific fields:

```text
schema_version
analyzer_kind
governance
source
source_language
query_hint_strategy
query_hint_count
has_ambiguous_reference
structured_terms
bounded_ngram_hints
backend_private_hints
confidence
is_estimate
source_authoritative
candidate_applied
policy_authority
restrictive_only
content_free
reason_ids
validation_errors
```

The internal artifact is intentionally **not** a content-free public object because it can contain:

```text
structured_terms
bounded_ngram_hints
backend_private_hints
```

Its current `content_free` field is therefore:

```text
false
```

The artifact must not be copied wholesale into generic/public diagnostics.

## Current governance request

The producer asks the shared analyzer-governance builder for a restrictive candidate with:

```text
analyzer_kind       = retrieval_query_candidate
is_estimate         = true
source_authoritative = false
candidate_applied   = false
policy_authority    = restrictive
restrictive_only    = true
content_free        = true
```

Producer confidence/stability are currently:

```text
private hints exist:
  confidence = 0.35
  stability  = 0.40

no private hints:
  confidence = 0.0
  stability  = 0.0
```

Those values are candidate metadata only. They do not grant retrieval authority.

## Runtime-open invariant

The Retrieval Query Analyzer is not an authority-opening producer.

For the current fallback source classes exercised by this boundary, including:

```text
heuristic
fallback_regex
locale_marker
```

the analyzer remains:

```text
source_authoritative = false
restrictive_only = true
can_open_runtime_policy = false
```

A query hint may improve candidate discovery inside an already-authorized read-only path. It may not open a memory family, expand scene scope, bypass lifecycle exclusion, or authorize mutation.

## Backend-private hint accessor

`retrieval_query_backend_hints(...)` is the bounded accessor for private hint strings.

If the supplied artifact is not a mapping, it returns:

```text
[]
```

If `query_hint_strategy` is not in the exact accepted strategy set, it returns:

```text
[]
```

`backend_private_hints` must be a non-string sequence. Otherwise the accessor returns no hints.

Each returned item is re-cleaned to the 32-character ordinary hint bound.

Hints shorter than two characters are discarded.

Duplicates are removed in first-seen order.

The accessor emits at most six hints even if a malformed artifact contains more.

Thus a constructed or corrupted artifact cannot bypass the analyzer-level hint bound merely by populating its private tuple directly.

## Ambiguous-reference marker

The producer exposes a bounded boolean:

```text
has_ambiguous_reference
```

computed by the shared analyzer text-feature marker set.

This flag is evidence for restrictive handling only.

It does not resolve the reference and does not override RelayINT authority.

The current dry-run retrieval path separately honors its RelayINT unresolved-reference input and can block discovery with:

```text
unresolved_reference_requires_confirmation
```

The analyzer flag is not an alternate reference-resolution owner.

## Public projection

The public projection is produced only through:

```text
public_retrieval_query_projection(...)
```

The exact current public keys are:

```text
schema_version
analyzer_kind
source_class
source_language
query_hint_strategy
query_hint_count
has_ambiguous_reference
source_authoritative
policy_authority
restrictive_only
candidate_applied
confidence_bucket
stability_bucket
can_open_runtime_policy
reason_ids
validation_error_ids
content_free
```

The current public projection always reports:

```text
schema_version = relaylm.retrieval_query_analyzer.v0
analyzer_kind  = retrieval_query_candidate
content_free   = true
```

The public strategy projection preserves the four accepted strategy tokens and maps everything else to:

```text
unknown
```

`query_hint_count` is bounded into:

```text
0..6
```

before public exposure.

## Public-content exclusion

The public projection must not expose:

```text
raw query text
structured_terms
bounded_ngram_hints
backend_private_hints
memory text
protected source bodies
filesystem paths
queue payloads
free-form rationale
```

The public output may expose fixed enum/status values, booleans, counts, reason IDs, validation-error IDs, and shared governance buckets only.

The current ACG-3 smoke explicitly checks that raw no-whitespace Japanese and multilingual query strings and their generated private hints do not appear in the serialized public projection.

## Invalid public input behavior

If `public_retrieval_query_projection(...)` receives a non-mapping artifact, it first builds the current empty-query analyzer artifact and projects that bounded result.

It does not echo or stringify the invalid object into diagnostics.

If the embedded `governance` value is not a mapping, the shared governance public projection is invoked with no usable candidate authority rather than trusting arbitrary content.

## Dry-run retrieval integration

The current dry-run retrieval assembly extracts the latest user text from the request-local `messages` sequence.

For string message content, the exact string is used request-locally.

For structured sequence content, only mapping items containing a string `text` field are collected and joined with newline characters.

No user message yields an empty string.

The current retrieval path passes this latest-user text into `_term_hints(...)` before read-only candidate discovery.

`_term_hints(...)` calls the Retrieval Query Analyzer with:

```text
source = heuristic
max_hints = 12
```

but the analyzer itself clamps that requested limit to its current maximum of six.

The consumer may then add bounded legacy Japanese recall phrases before returning at most twelve consumer-side query terms.

That consumer-side supplement does not change the Retrieval Query Analyzer's six-hint exact bound and does not make the analyzer a memory authority.

## Candidate discovery use

The resulting query-term hints are supplied to the existing dry-run candidate-selection owner only after scene/reference/store fallback checks have produced the surrounding retrieval state.

They can contribute lexical/keyword matching for candidate discovery.

They cannot make candidate discovery proceed when the owning retrieval path has already blocked it for reasons such as:

```text
scene policy
unresolved reference
store state
retrieval scope
```

They also do not determine final evidence eligibility or lifecycle authority.

## Runtime-private retrieval projection

The dry-run retrieval artifact separately records:

```text
retrieval_query_private
```

with current shape:

```text
schema_version = relaymem.retrieval_query_private_hints.v0
runtime_private = true
content_free = false
source = retrieval_query_analyzer
backend_private_hints
query_hint_count
```

This object is request-local/private because it contains the actual hint strings.

It is distinct from the public `retrieval_query_candidate` projection.

## Public retrieval summary separation

The dry-run artifact also emits a content-free `query_summary` through the retrieval candidate helper.

The current ACG-3 validation requires that public summary/projection surfaces expose counts/status instead of private terms.

The private hint tuple remains available only in the runtime-private branch of the artifact.

## Restrictive downstream gates remain authoritative

Retrieval Query Analyzer hints do not bypass:

```text
scene policy restrictions
current-context-only restrictions
RelayINT unresolved-reference handling
memory-family reader authority
lifecycle/current-revision eligibility
scope/namespace/character binding
Primary/Subjective cutover state
retrieval dry-run/apply gates
```

A successful lexical match is not authority to serve a candidate.

The analyzer owns query interpretation candidates, not memory eligibility.

## No mutation authority

This boundary is read-only with respect to durable RelayLM state.

It does not:

```text
write Primary MEM
write Subjective MEM
pin or unpin memory
hide, forget, restore, or correct memory
write SOUL, SELF, REL, SCN, GOAL, STYLE, or workspace source files
create queue jobs
advance durable worker state
write scheduler state
```

Any such behavior belongs to another authority.

## No semantic-retriever claim

The current analyzer is deliberately bounded lexical normalization.

It does not claim:

```text
embedding retrieval
semantic vector search
external tokenizer ownership
LLM query rewriting
cross-memory-family search
reference resolution
factual support classification
retrieval ranking authority
```

Character n-grams and whitespace terms are candidate hints only.

## Failure direction

The stable failure direction is toward fewer private hints and less authority:

```text
non-string query
  -> empty source text
  -> bounded empty/derived result only

invalid max_hints
  -> bounded default

unknown explicit strategy
  -> strategy unknown
  -> no backend-private hints
  -> validation error

invalid/missing artifact passed to private accessor
  -> no backend-private hints

invalid artifact passed to public projection
  -> bounded empty-query projection

ambiguous reference
  -> restrictive signal only
  -> no silent reference resolution
```

There is no fail-open path that substitutes raw request text as unrestricted retrieval authority.

## Stable invariants

- Analyzer schema is `relaylm.retrieval_query_analyzer.v0`.
- Analyzer kind is `retrieval_query_candidate`.
- Accepted hint strategies are exactly the four current fallback strategies.
- Unknown strategy emits no private hints and records `unknown_query_hint_strategy`.
- Analyzer-level private hint count is bounded to six.
- Ordinary private hints are bounded to 32 characters.
- Generated n-grams are bounded and derived only from request-local text.
- Private hint strings never belong in the public projection.
- The internal producer artifact is not itself content-free because it carries private strings.
- The public projection is content-free and count/status based.
- Fallback query analysis remains non-authoritative and restrictive-only.
- Analyzer confidence does not become memory or retrieval authority.
- Ambiguous-reference detection does not become RelayINT authority.
- Query hints can improve already-authorized read-only candidate discovery only.
- Query hints cannot widen scene, lifecycle, scope, reader, or mutation authority.
- No durable state mutation belongs to this boundary.

## Non-goals

This contract does not define:

- shared Analyzer Candidate Governance threshold semantics;
- ordinary reader selection between Primary, Subjective, or neither;
- the final RT-1D R5/R6 retirement result;
- exact memory-store schema or physical layout;
- final candidate ranking or tie-breaking policy;
- evidence provenance or grounding support classification;
- memory formation/update/forget/restore/correct/pin/unpin semantics;
- RelaySCN scene classification;
- RelayINT reference or intent authority;
- external embeddings, vector databases, or tokenizer dependencies;
- worker, queue, scheduler, or background processing;
- source retirement or redirect/migration completion.

## Related authority

- [Analyzer Candidate Governance Contract](analyzer-candidate.md)
- [Analyzer Candidate Governance Architecture](../architecture/analyzers/candidate-governance.md)
- [Ordinary Memory Retrieval and Grounding](../architecture/memory/retrieval-and-grounding.md)
- [E1-R5 Primary MEM Recall Candidate Bridge](../architecture/e1r5_primary_mem_recall_candidate_bridge.md)
