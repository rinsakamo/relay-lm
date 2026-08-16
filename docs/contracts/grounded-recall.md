---
relaylm_doc_type: contract
relaylm_authority: current_grounded_recall_context_and_content_free_projection_exact_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - grounded-recall context or public projection schema changes
  - evidence support, provenance, lifecycle, scope, or privacy rules change
  - selected-memory handoff or ordinary-memory authority boundaries change
  - backend grounding instruction or unsupported-detail suppression changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status or sequencing
  - ordinary-memory reader selection, candidate discovery, ranking, or storage
  - memory formation, lifecycle mutation, or retrieval projection generation
  - query-detail analyzer field ownership or shared analyzer governance
  - response generation, visible-response rewriting, or transport semantics
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../architecture/memory/retrieval-and-grounding.md
  - ../architecture/subjective-mem-retrieval-projection-hard-cutover.md
  - ../architecture/e1_evaluation_consolidation.md
relaylm_related_contracts:
  - query-detail-analyzer.md
  - analyzer-candidate.md
relaylm_verified_by:
  - ../../scripts/relaylm_e1r4_grounded_recall_response_smoke.py
  - ../../scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
  - ../../scripts/relaylm_e1r4_grounded_recall_security_smoke.py
  - ../../scripts/relaylm_acg2_query_detail_analyzer_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - RelayCTX request-side grounding maintainers
  - ordinary Retrieval and Subjective retrieval maintainers
  - privacy, diagnostics, evaluation, and security reviewers
relaylm_authority_level: exact_contract
---
# Grounded Recall Contract

## Authority summary

This contract owns the exact current request-side Grounded Recall boundary
implemented by:

```text
relaylm/relaymem_grounded_recall_response.py
```

It defines the private backend-bound context and the content-free public
projection built from already selected ordinary-memory evidence. The retained
E1-R4 document is an implementation and regression handoff; it is not a second
semantic owner.

The stable flow is:

```text
one already-selected ordinary-memory authority
  -> selected-memory handoff
  -> Grounded Recall support and safety classification
  -> private backend context
  -> content-free public projection
```

Grounding does not select a reader, discover or rank candidates, mutate memory,
or rewrite a visible response after generation.

## Current implementation boundary

The exact producer is:

```text
relaylm/relaymem_grounded_recall_response.py
```

RelayCTX invokes it from:

```text
relaylm/relayctx_repack.py
```

RelayCTX consumes selected memories from exactly the ordinary authority named
by `ordinary_memory_authority`:

```text
primary_only
  -> primary_recall_runtime.selected_memories

subjective_only
  -> the admitted Subjective runtime selected_memories

neither / missing / malformed / unknown
  -> no selected ordinary-memory evidence
```

The Grounded Recall producer never probes the other family. Primary and
Subjective evidence are never combined by this boundary.

Subjective retrieval selection imports the context schema read-only and uses
the exact handoff shape:

```text
relaymem.grounded_recall_context.v0.evidence_items
```

Selection, projection generation, lifecycle authority, and durable usage
finalization remain owned by their respective memory contracts. Grounding only
consumes the already-selected handoff.

## Schema identities

The exact private context schema is:

```text
relaymem.grounded_recall_context.v0
```

The exact content-free public projection schema is:

```text
relaymem.grounded_recall_projection.v0
```

The implementation bounds the private evidence handoff to at most 32 items and
bounds each normalized fact text to 2,048 characters. These are safety bounds,
not candidate-discovery or ranking policies.

## Input validation and failure boundary

`build_grounded_recall_context(...)` accepts:

```text
retrieved_memories: list | tuple
query_text: str
character_id: optional scope value
namespace: optional scope value
enabled: bool
unsupported_detail_policy: suppress | qualify_uncertain | omit
query_detail_candidate: optional request-local candidate
```

The input shape fails closed when `enabled` is not an exact boolean,
`unsupported_detail_policy` is outside its accepted set, `query_text` is not a
string, `retrieved_memories` is not a list or tuple, or the evidence bound is
exceeded. Disabled grounding returns no private context and does not mutate the
backend payload.

An empty selected-memory sequence produces a private context with no evidence
items and an instruction that does not claim remembered support. It does not
trigger retrieval, fallback, or a second authority.

Evidence is excluded rather than relaxed when scope, lifecycle, provenance,
shape, fact text, or support validation fails. No failure path authorizes
canonical memory mutation or post-hoc visible-response rewriting.

## Private context shape

When a bounded context is built, its top-level fields are exactly:

```text
schema_version
runtime_private
enabled
evidence_items
excluded_evidence
unsupported_detail_policy
unsupported_detail_count
ambiguous_evidence_count
query_detail_types
unsupported_detail_risk
query_detail_analysis
instruction
backend_messages
```

Each admitted `evidence_items` entry contains exactly the current fields:

```text
memory_ref
revision_ref
lifecycle_current_eligible
pinned
provenance_source
fact_text
support_level
unsupported_detail_policy
```

Each `excluded_evidence` entry is content-free and contains:

```text
memory_ref
support_status
reason
content_included=false
```

`fact_text` and the backend grounding message are request-local private
evidence. They are never a public diagnostic, durable usage event, generic
trace payload, or second memory store.

## Evidence linkage and ordering

The producer accepts only the selected-memory values supplied by its caller.
It does not infer a candidate from store presence, configuration, old success,
query intent, ranking output, or a grounding result.

For each admitted item:

- `memory_ref` is derived from a bounded safe memory identifier and falls back
  to a generated local reference when the identifier is unsafe;
- `revision_ref` is derived from a bounded revision value and never exposes a
  long digest as a public reference;
- `lifecycle_current_eligible` is true only after lifecycle validation;
- `pinned` is an ordering hint only after eligibility and support checks;
- `provenance_source` is normalized from the selected evidence;
- `fact_text` is normalized and bounded before it enters the private context;
- `support_level` is either `directly_supported` or
  `inferred_from_supported` for admitted items.

Eligible items are ordered with pinned items first and then by safe
`memory_ref`. This is not retrieval ranking and cannot make excluded evidence
eligible.

## Scope and lifecycle rules

When a caller supplies `character_id` or `namespace`, a selected item with a
different non-null value is excluded. Explicit `cross_scope`, `scope_mismatch`,
or `excluded_by_scope` markers are excluded.

The excluded lifecycle states are exactly:

```text
hidden
prior
prepared
recovery_required
corrupt
deleted
tombstoned
held
```

The eligible lifecycle states are exactly:

```text
active
current
eligible
pinned
```

An unrecognized lifecycle state is ambiguous and is not admitted. Explicit
`hidden`, `prepared`, `recovery_required`, or `corrupt` flags and
`current=false` are also fail-closed exclusions.

## Provenance and support vocabulary

The exact support vocabulary is:

```text
directly_supported
inferred_from_supported
unsupported
no_retrieved_evidence
ambiguous_evidence
excluded_by_lifecycle
excluded_by_scope
provenance_missing
content_leakage_guard_failed
```

The direct provenance sources are:

```text
user_assertion
user_assertion_only       # normalized to user_assertion
primary_recall_selected_memory
```

The bounded inference sources are:

```text
scene_qualification
other_allowed_source
```

The unsupported provenance sources are:

```text
assistant_acknowledgement
assistant_speculation
assistant_non_factual_context
assistant_decoration
unknown
```

Formation-summary user-assertion evidence is normalized to direct support, and
the current Primary selected-memory shape is recognized only when its bounded
summary/snippet and evidence identity are present. Missing provenance is not
converted into support. Any other provenance is ambiguous.

Directly supported evidence may be presented as remembered fact. Inferred
evidence must remain identifiable as inference. Unsupported, ambiguous,
missing-provenance, lifecycle-excluded, and scope-excluded evidence cannot
become remembered support through Pin, ranking, or grounding.

## Unsupported-detail policy

Grounding consumes the restrictive Query Detail Analyzer projection but does
not own its schema or governance. The exact current detail classes are the
analyzer contract's responsibility.

The producer counts requested detail classes not supported by the admitted
fact text. The bounded policy values are:

```text
suppress
qualify_uncertain
omit
```

The backend instruction must not invent dates, names, preferences, quantities,
relationships, locations, identities, or causes. When requested detail is not
supported, `unsupported_detail_count` is bounded and the response instruction
suppresses, omits, or qualifies the detail according to the selected policy.

The instruction never changes ordinary-memory authority and never authorizes a
retry against another family.

## Public projection

`RelayMEMGroundedRecallResult.to_log_dict()` emits the exact projection
identity and content-free diagnostics. Its fields are:

```text
schema_version
diagnostics_only
content_free
grounding_enabled
status
backend_request_changed
grounded_item_count
excluded_evidence_count
unsupported_detail_policy
unsupported_detail_count
ambiguous_evidence_count
query_detail_type_count
query_detail_unsupported_detail_risk
query_detail_source_class
query_detail_restrictive_only
query_detail_content_free
evidence_content_included
runtime_private_evidence_omitted
raw_memory_text_included
raw_user_text_included
raw_assistant_text_included
protected_source_body_included
queue_payload_included
store_root_included
source_path_included
claim_token_included
lease_owner_included
token_digest_included
source_digest_included
blocked_reason_ids
```

The projection must remain content-free. It must not expose raw memory text,
raw user or assistant text, protected source bodies, queue payloads, store
roots, source paths, namespaces, lineage, claim or lease material, digests,
exact private identifiers, or backend grounding messages.

## Runtime status vocabulary

The declared exact status vocabulary is:

```text
disabled
ready
grounding_applied
no_retrieved_evidence
unsupported_detail_suppressed
ambiguous_evidence
provenance_missing
retrieval_excluded
context_build_failed
backend_request_unchanged
content_leakage_guard_failed
```

The current builder emits the applicable statuses from this vocabulary for its
validation, empty-evidence, support, and grounding branches. The status is a
diagnostic result; it is not reader authority, mutation authority, a durability
receipt, or proof that another retrieval family may be tried.

## Request-path and validation anchors

The exact request-path caller is:

```text
relaylm/relayctx_repack.py
```

The current Subjective selected-memory consumer imports only the schema and
bounded constants:

```text
relaylm/subjective_mem/retrieval_selection.py
```

The focused validation anchors are:

```text
scripts/relaylm_e1r4_grounded_recall_response_smoke.py
scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
scripts/relaylm_e1r4_grounded_recall_security_smoke.py
scripts/relaylm_acg2_query_detail_analyzer_smoke.py
scripts/relaylm_e1_evaluation_consolidation_smoke.py
```

These commands validate the current implementation and its integration. The
contract does not create a second workflow, registry, schema validator, or
runtime path.

## Non-goals and removal boundary

This contract does not own ordinary reader selection, retrieval candidate
discovery or ranking, storage, projection generation, usage-ledger finalization,
memory formation, lifecycle mutation, Primary/Subjective cutover, response
generation, visible-response rewriting, queue or worker execution, browser
trust, or source-retirement disposition.

The E1-R4 implementation handoff remains retained as transitional
implementation/regression evidence until a later bounded retirement transaction
proves that all current consumers use this contract and that the focused
validation/evidence surface remains protected.
