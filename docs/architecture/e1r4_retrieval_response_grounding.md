---
relaylm_doc_type: implementation_handoff
relaylm_authority: e1_r4_retrieval_response_grounding
relaylm_status: transitional
relaylm_volatility: medium
relaylm_owner: e1_quality_gates
relaylm_update_trigger:
  - grounded recall context schema changes
  - backend-bound recall instruction changes
  - ordinary memory authority selection or selected-memory handoff changes
  - public grounded-recall projection changes
  - retrieval eligibility or provenance support rules change
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - Primary or Subjective candidate discovery/ranking authority
  - RT-1D cutover state, R5 retirement completion, or Primary deletion approval
  - memory formation or lifecycle mutation internals
  - queue lifecycle, worker execution, or browser trust admission
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_current_exact_contract: ../contracts/grounded-recall.md
relaylm_related_contracts:
  - ../contracts/grounded-recall.md
relaylm_related_authority:
  - subjective-mem-retrieval-projection-hard-cutover.md
  - e1_evaluation_consolidation.md
  - e1r3_provenance_preserving_primary_mem_formation_summary.md
  - e1r5_primary_mem_recall_candidate_bridge.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - memory/pinned-memory.md
  - ../contracts/memory/held-governance.md
---
# Ordinary Memory Retrieval-Response Grounding Compatibility Handoff

Last reviewed: 2026-08-08 JST

## Transitional status

Historical handoff identity: **E1-R4 Retrieval-Response Grounding**.

E1-R4 introduced the current request-side grounded-recall policy. The policy
continues to be live after RT-1D authority transfer, but this legacy
underscore-named E1 handoff is transitional documentation rather than the final
permanent responsibility-level path.

- owner: E1 quality gates / ordinary memory grounding;
- current consumers: RelayCTX repack, ordinary Primary-only and Subjective-only
  retrieval paths, E1 regression/evaluation, and response-safety reviewers;
- removal gate: a permanent responsibility-oriented grounding document preserves
  the exact private context, support classification, suppression, projection,
  privacy, and validation contracts, and all E1/index/validator consumers migrate
  atomically;
- replacement validation: both Primary-only compatibility and finalized
  Subjective-only ordinary requests continue to consume the same grounding policy
  without dual-read, content leakage, or unsupported-detail regression.

RT-1D-R5 may retire Primary reader/fallback inputs to this policy; it does not
retire the grounding policy itself.

The permanent exact owner of the live Grounded Recall context and projection is
the [Grounded Recall Contract](../contracts/grounded-recall.md). This handoff
retains implementation mapping, regression evidence, and the source-family
retirement boundary; its repeated field and policy descriptions are
implementation evidence for that contract, not a second semantic authority.

## Implementation responsibility

The E1-R4 implementation provides request-side transformation from **already
selected ordinary memory evidence** into the bounded private backend grounding
and content-free diagnostics defined by the [Grounded Recall
Contract](../contracts/grounded-recall.md). It does not choose which durable
memory authority serves the request.

The ordinary Retrieval stage first names exactly one authority in
`ordinary_memory_authority`. RelayCTX repack then consumes selected memories from
that named family only:

```text
primary_only
  -> Primary recall runtime selected memories

subjective_only
  -> admitted/finalized Subjective runtime selected memories

neither / missing / malformed authority
  -> no selected ordinary memory
```

Primary and Subjective selected memories are never combined. Grounding cannot
probe the other family, infer fallback authority, or turn an empty selection into
a cross-authority retry.

The implementation anchor remains
`relaylm/relaymem_grounded_recall_response.py`, invoked from RelayCTX repack after
the retrieval authority decision and before the backend-bound request is
finalized.

## Request-side only boundary

Grounding builds the private backend-bound
`relaymem.grounded_recall_context.v0` context and its instruction under the
[Grounded Recall Contract](../contracts/grounded-recall.md). It does not:

- rewrite the visible response after generation;
- alter SSE semantics;
- select or rank durable memories;
- authorize a Primary or Subjective reader;
- recover from an empty/failed Subjective result by reading Primary;
- expose private evidence in public diagnostics.

If no selected ordinary memory exists, the helper produces a bounded
`no_retrieved_evidence` result and no memory evidence is injected as remembered
support.

## Private grounded-recall context

The private context contains bounded fields of this shape:

```text
grounded_recall_context:
  enabled
  evidence_items:
    memory_ref
    revision_ref
    lifecycle_current_eligible
    pinned
    provenance_source
    fact_text
    support_level
    unsupported_detail_policy
  excluded_evidence:
    memory_ref
    support_status
    reason
    content_included=false
  unsupported_detail_policy
  unsupported_detail_count
  ambiguous_evidence_count
  query_detail_types
  instruction
  backend_messages
```

`fact_text` and backend grounding messages are runtime-private evidence. They are
not public diagnostics, durable usage prose, trace payloads, or a second memory
store.

The context schema is storage-neutral at this boundary: the caller has already
selected exactly one ordinary authority. Grounding judges the admitted evidence
shape and support, not whether it originated from the retained Primary
compatibility path or the finalized Subjective path.

## Support classification

The bounded support statuses remain:

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

Stable rules:

- user-assertion provenance may be directly supported;
- accepted scene/other provenance may support inference but is not automatically
  a direct user fact;
- assistant acknowledgement, speculation, decoration, non-factual context, and
  unknown provenance are not admitted as directly supported recalled facts;
- missing provenance fails closed as `provenance_missing`;
- hidden, prior, prepared, recovery-required, corrupt, deleted, tombstoned, held,
  or cross-scope evidence is excluded before grounding;
- Pin may affect order only for evidence that is already eligible; Pin does not
  create support or override scope/lifecycle exclusion;
- governance/held evidence remains excluded until its owning lifecycle authority
  has made it eligible ordinary memory evidence.

Grounding does not reinterpret a cutover fence, lifecycle decision, projection
receipt, or store record as semantic support.

## Unsupported-detail policy

The backend instruction requires remembered facts to be grounded in admitted
support, requires inference to remain identifiable as inference, and suppresses
unsupported dates, names, preferences, quantities, relationships, causes, and
other requested detail classes that the admitted evidence does not support.

A request for unsupported detail increments bounded unsupported-detail
diagnostics and may produce the exact runtime status
`unsupported_detail_suppressed`.

No retrieved evidence produces no evidence items and an instruction that prevents
a false claim of remembered support.

## Content-free public projection

`RelayMEMGroundedRecallResult.to_log_dict()` exposes only bounded diagnostics,
including fields such as:

```text
grounding_enabled=true
grounded_item_count=2
unsupported_detail_policy="suppress"
unsupported_detail_count=1
evidence_content_included=false
runtime_private_evidence_omitted=true
```

The projection must not expose raw memory text, raw user/assistant text, protected
source bodies, queue payloads, store roots, paths, namespaces, claim tokens,
lease owners, digests, lineage, exact private identifiers, or backend grounding
messages.

This content-free projection may be consumed by SOUL Lab observation and
used-memory lifecycle surfaces without becoming a memory-text display or serving
authority.

## Runtime statuses

The bounded status vocabulary remains:

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

Status values are diagnostics about grounding execution. They do not authorize a
reader, mutate memory, or prove that an unavailable authority may be retried.

## RT-1 / R5 boundary

RT-1 chooses the one ordinary memory authority before E1-R4 grounding runs. The
current grounding policy therefore survives Primary reader retirement:

- while `primary_only` remains valid, it may ground selected Primary compatibility
  evidence;
- after finalized `subjective_only` transfer, it grounds only the admitted
  Subjective selected-memory handoff;
- `neither` grounds no durable-memory evidence;
- failed or empty Subjective selection/finalization never causes Primary fallback.

R5 owns retirement of replaced Primary discovery/reader/fallback surfaces and
temporary rehearsal/shadow surfaces. It does not need a second grounding policy
for Subjective memory and must not clone E1-R4 semantics into the cutover owner.

## Privacy and failure boundary

Grounding is fail-closed over malformed request shape, unsupported policy values,
scope disagreement, lifecycle exclusion, provenance failure, ambiguous evidence,
or content-leakage guard failure.

Runtime-private evidence remains bounded and request-local. Public/log projections
remain content-free even when private grounding was successfully applied.

No grounding result may expose credentials, raw paths, memory bodies outside the
bounded backend context, source bodies, queue internals, claim/lease state, or
cutover identifiers.

## Validation

The historical E1-R4 validation slice remains regression evidence for this live
policy. Current validation must continue to cover both the stable schema/policy
and the one-authority caller behavior.

Core existing anchors include:

```bash
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_response_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_security_smoke.py
PYTHONPATH=. python scripts/relaylm_e1_evaluation_consolidation_smoke.py
```

RT-1 request-path/runtime coverage additionally proves that grounding receives
selected memories only from the authority named by the exact reader decision and
that Primary/Subjective evidence is never combined.

The current workflow/registry remains the command authority; this handoff is not
a second CI registry.

## Non-goals

No memory authority selection, candidate discovery/ranking, Primary or Subjective
lifecycle mutation, RT-1D-R5 completion, Primary deletion, queue/worker/scheduler
ownership, browser trust, Secondary consolidation, RelaySOUL mutation, media
runtime execution, or post-hoc visible-response rewriting is authorized here.
