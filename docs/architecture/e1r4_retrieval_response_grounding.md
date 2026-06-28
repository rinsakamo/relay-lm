---
relaylm_doc_type: implementation_handoff
relaylm_authority: e1_r4_retrieval_response_grounding
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: e1_quality_gates
relaylm_update_trigger:
  - grounded recall context schema changes
  - backend-bound recall instruction changes
  - public used-memory projection changes
  - retrieval eligibility or provenance support rules change
relaylm_not_authoritative_for:
  - Primary MEM formation summary internals
  - queue lifecycle authority
  - worker execution authority
  - browser-owned trust admission
relaylm_related_authority:
  - e1_evaluation_consolidation.md
  - e1r3_provenance_preserving_primary_mem_formation_summary.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i5b_pin_unpin_apply.md
  - phase_i7c_held_apply_discard_runtime.md
---
# E1-R4 Retrieval-Response Grounding

Last reviewed: 2026-06-28 JST.

## Purpose

E1-R4 adds request-side, backend-bound recall grounding for later Home / ordinary managed request responses that use retrieved Primary MEM. It keeps retrieved facts separate from inference and makes unsupported dates, names, preferences, quantities, relationships, and causes harder to emit as remembered facts.

The implementation boundary is `relaylm/relaymem_grounded_recall_response.py` with deterministic smokes under `scripts/relaylm_e1r4_*_smoke.py`.

## Request-side decision

E1-R4 is request-side only. It builds a `relaymem.grounded_recall_context.v0` private backend-bound contract and instruction. It does not rewrite visible responses after generation, does not alter SSE semantics, and does not expose private evidence in public diagnostics.

## Grounded recall context

The private backend-bound context contains:

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

`fact_text` is runtime-private backend evidence. Public diagnostics never include raw memory text, raw user text, raw assistant text, protected source body, queue payload, store root, source path, claim token, lease owner, token digest, or source digest.

## Support classification

Minimum support statuses are implemented:

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

Rules:

- `user_assertion` / `user_assertion_only` provenance is directly supported.
- `scene_qualification` / `other_allowed_source` may be inference support, but not direct user fact.
- assistant acknowledgement, assistant speculation, assistant non-factual context, assistant decoration, and unknown provenance are not injected as supported recalled facts.
- missing provenance fails closed as `provenance_missing`.
- hidden, prior, prepared, recovery_required, corrupt, deleted, tombstoned, held, and cross-scope memories are excluded before grounding.
- Pin may rank eligible evidence earlier; Pin does not override lifecycle/scope and does not create support.
- Held Governance evidence is excluded unless a later authority has made it eligible Primary MEM.

## Unsupported detail behavior

The backend instruction says to answer remembered facts only from `directly_supported` evidence, mark inference as inference, and avoid inventing dates, names, preferences, quantities, relationships, or causes. If a query asks for a detail that the retrieved fact text does not support, the context records `unsupported_detail_count > 0` and status `unsupported_detail_suppressed`.

No retrieved evidence produces a context with no evidence items and an instruction to avoid claiming remembered support.

## Public projection

`RelayMEMGroundedRecallResult.to_log_dict()` returns content-free diagnostics such as:

```text
grounding_enabled=true
grounded_item_count=2
unsupported_detail_policy="suppress"
unsupported_detail_count=1
evidence_content_included=false
runtime_private_evidence_omitted=true
```

This projection is safe for SOUL Lab observation / used-memory lifecycle surfaces. It is intentionally not a memory text display.

## Runtime statuses

E1-R4 defines the bounded statuses:

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

## Non-goals

E1-R4 does not implement O2/O3, polling, supervision, daemonization, browser-owned trust, new queue lifecycle authority, new worker execution authority, Pin / Unpin mutation changes, Held Apply / Discard changes, Forget / Correct changes, Merge / Supersession, Secondary MEM consolidation, RelaySOUL mutation, TTS/audio/avatar/Live2D/ASR, or post-hoc visible response rewriting.

## Validation

Slice validation:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_response_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_security_smoke.py
PYTHONPATH=. python scripts/relaylm_e1_evaluation_consolidation_smoke.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```
