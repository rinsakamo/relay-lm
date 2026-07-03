---
relaylm_doc_type: architecture_report
relaylm_authority: acg3_retrieval_query_normalization
relaylm_status: current
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - Retrieval Query Analyzer schema changes
  - RelayMEM query hint generation changes
  - public retrieval diagnostics changes
  - analyzer candidate authority gate changes
relaylm_not_authoritative_for:
  - ACG-2 Grounded Recall detail analyzer status
  - ACG-4 RelayREF / RelayINT consolidation
  - ACG-5 RelayEMO scene ownership cleanup
  - ACG-6 SCN scene-wiki classifier implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - analyzer_candidate_governance.md
  - project_execution_plan.md
  - e1r4_retrieval_response_grounding.md
  - e1r5_primary_mem_recall_candidate_bridge.md
  - relaymem_slp_current_target.md
---
# ACG-3 Retrieval Query Normalization

Last reviewed: 2026-07-03 JST

## Purpose

ACG-3 isolates RelayMEM retrieval-query understanding behind a structured Retrieval Query Analyzer candidate artifact. The old whitespace-oriented query term builder remains available only as a fallback candidate source; it no longer owns semantic interpretation of multilingual retrieval intent.

The implementation is intentionally bounded. It is not a semantic retriever, does not add an external tokenizer dependency, and does not authorize broader retrieval or memory mutation.

## Implemented boundary

```text
latest user text
  -> Retrieval Query Analyzer candidate
  -> backend-private bounded hint strings
  -> existing read-only RelayMEM candidate discovery
  -> content-free public query projection
```

The analyzer uses the shared ACG-1 governance helper fields and fixed English schema / enum values. Heuristic, locale-marker, and fallback-regex sources remain non-authoritative:

```text
source_authoritative = false
restrictive_only = true
can_open_runtime_policy = false
```

## Artifact shape

The Retrieval Query Analyzer wrapper records the ACG governance projection plus ACG-3-specific fields:

```text
schema_version
analyzer_kind = retrieval_query_candidate
source
source_language
query_hint_strategy
query_hint_count
has_ambiguous_reference
structured_terms
bounded_ngram_hints
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

`structured_terms`, `bounded_ngram_hints`, and `backend_private_hints` are internal/backend-private. They must not be copied into public diagnostics.

## Hint strategies

```text
whitespace_fallback
  -> preserves useful existing English / whitespace-separated hints

bounded_ngram_fallback
  -> provides bounded character n-gram hints for no-whitespace text

mixed_fallback
  -> combines bounded whitespace and character hints when no-whitespace or CJK text would otherwise be brittle

empty_fallback
  -> explicit fail-closed no-hint state
```

Unknown hint strategies fail closed and produce no backend-private hints.

## Public diagnostics

Public query diagnostics remain content-free. They may expose only fixed values and counts:

```text
source_class
source_language
query_hint_strategy
query_hint_count
has_ambiguous_reference
confidence_bucket
stability_bucket
reason_ids
validation_error_ids
content_free = true
```

They must not expose raw query text, generated n-gram strings, memory text, protected source bodies, filesystem paths, queue payloads, or free-form rationale.

## Safety guarantees

ACG-3 does not:

- broaden retrieval scope by itself;
- admit hidden, prepared, recovery-required, corrupt, cross-scope, or prior physical revisions;
- bypass I-4D lifecycle exclusion;
- bypass E1-R5 scoped Primary bridge constraints;
- mutate memory;
- add worker, scheduler, queue, or background behavior;
- consolidate RelayREF / RelayINT reference ownership;
- implement RelayEMO scene cleanup;
- implement SCN scene-wiki classification.

Existing scene policy, unresolved-reference, lifecycle, and E1-R5 protections remain downstream gates. Retrieval query hints can help the existing read-only selection path find candidates, but they cannot make those candidates eligible when another gate excludes them.

## Validation

The ACG-3 smoke covers:

```text
scripts/relaylm_acg3_retrieval_query_normalization_smoke.py
```

It checks that existing English hints still work, no-whitespace Japanese/multilingual queries produce bounded private hints, public projections do not leak raw query text or private n-grams, fallback sources cannot open runtime policy, unknown strategies fail closed, ambiguous reference handling stays restrictive, and scene/lifecycle protections are not bypassed.
