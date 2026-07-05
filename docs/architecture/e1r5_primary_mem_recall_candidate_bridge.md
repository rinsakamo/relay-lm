---
relaylm_doc_type: implementation_handoff
relaylm_authority: e1r5_primary_mem_recall_candidate_discovery_bridge
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - Primary recall candidate discovery changes
  - namespace token compatibility changes
  - E1 recall proof boundary changes
  - lifecycle eligibility integration changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - MVP roadmap sequencing
  - worker, queue, scheduler, or store mutation authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - e1_evaluation_consolidation.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - e1r4_retrieval_response_grounding.md
  - e1r5_post_wave7_correction_convergence_audit.md
  - project_execution_plan.md
  - ../mvp/wave7/e1r5_completion_report.md
---
# E1-R5 Primary MEM Recall Candidate Discovery Bridge

Last reviewed: 2026-07-06 JST

## Status

E1-R5 is current implemented. It adds a bounded request-side fallback for character-scoped Primary MEM recall after E1-R4 grounding. PM-D8 is closed by PR #491: the former bridge behavior is now canonicalized in Primary recall, and the former `relaymem_primary_recall_candidate_bridge_runtime` module remains compatibility no-op only.

E1-R4 already builds backend-bound grounded recall instructions from selected Primary MEM evidence, but local E2E evaluation found a pre-grounding gap: formed Primary MEM pages could exist under the character-scoped store while `selected_count` stayed `0` because no Primary MEM page became an M2 selected candidate.

E1-R5 corrects that proof boundary. The current E1 recall path is therefore not "M2 alone always selects current Primary MEM". The current boundary is:

```text
M2 remains the preferred relevance owner.
If no eligible scoped Primary candidate survives existing M2 narrowing,
E1-R5 may derive bounded candidates from scoped Primary index/log/page controls,
then hand the selected evidence to the existing RelayCTX / E1-R4 grounded recall path.
```

## Problem

The failing local path was:

```text
trusted Home / explicit trusted request
  -> durable source and queue evidence
  -> local worker drain
  -> Primary MEM durable formation
  -> character-scoped Primary MEM index/log/page creation
  -> later SOUL Lab Home recall
  -> Primary recall projection attempted
  -> selected_count: 0
  -> primary_recall_no_scoped_match
```

The symlink workaround `runtime/memory/memory -> runtime/memory/characters/<hash>/memory` could make the index/log visible to older flat-store diagnostics, but it did not guarantee that the page became an eligible Primary recall candidate. The issue was candidate bridging, not only path visibility.

## Implemented boundary

The preferred M2 path remains the first relevance owner. The canonical Primary recall implementation now owns the former E1-R5 bridge behavior, and the E1-R5 fallback only runs after the scoped Primary recall adapter cannot select an eligible Primary candidate from existing M2 results.

When the fallback runs, it:

1. resolves the character-scoped store root from configured root + route character id;
2. reads only bounded Primary MEM control files from that scoped root;
3. derives bounded Primary page candidates from index entries for the exact namespace;
4. validates page path, schema, digest, index entry, and log entry consistency;
5. applies Primary retrieval lifecycle eligibility through the shared I-4D current-state eligibility index;
6. checks bounded query relevance against validated Primary `summary` and `title` fields when query hints are available;
7. rebuilds the existing bounded snippet handoff consumed by RelayCTX and E1-R4 grounded recall.

The canonical fallback does not depend on the compatibility symlink and does not materialize an unbounded tree.

## Namespace decision

Primary recall now accepts the same namespace token shape used by the queue/worker side, including slash-style namespaces such as `character/default`. The goal is to avoid a formation-success / recall-reject split. Character and namespace values remain runtime-private and are not exposed in public projections.

## Lifecycle eligibility ownership

E1-R5 does not own an independent lifecycle policy. The implementation calls the shared Primary retrieval eligibility index used by I-4D before a fallback candidate can become selected evidence.

The current implementation is no longer an active runtime monkey-patch over the original I-1 adapter. PR #491 folded bounded fallback discovery, slash-permitting scope and namespace token handling, lifecycle eligibility integration, relevance bounds, and content-free public projection handling into the canonical Primary recall path.

## PM-D8 closure

PM-D8 is absorbed and closed by PR #491. The former runtime bridge module remains compatibility no-op only; canonical behavior now lives in `relaymem_primary_recall` / `apply_relaymem_primary_recall_scope(...)`.

The PR #491 fold-in preserves the current ownership rule: M2 remains preferred, E1-R5 is fallback only when M2 yields no eligible scoped Primary candidate, and lifecycle eligibility remains shared with I-4D.

## Grounded recall behavior

When the fallback selects a Primary MEM page, E1-R4 grounded recall receives the same selected-memory shape as the M2 path. Backend-bound context may include the bounded supported summary as private evidence, and the instruction continues to require unsupported-detail suppression:

```text
Use only grounded_recall_context evidence_items for remembered facts.
Do not invent dates, names, preferences, quantities, relationships, or causes.
Say the retrieved memory does not support unsupported details.
```

## Public projection

Public diagnostics remain content-free. Allowed public fields include counts and booleans such as:

```text
primary_candidate_discovery_attempted
primary_candidate_count
grounding_enabled
grounded_item_count
unsupported_detail_policy
evidence_content_included=false
runtime_private_evidence_omitted=true
```

The projection must not include raw memory text, raw transcript text, protected source body, queue payload, store root, source path, claim token, lease owner, token digest, source digest, page digest, lineage, or exact private ids.

## Validation boundary

E1-R5 validation is recorded in the completion report and must remain part of the current E1 recall regression set:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_bridge_relevance_bounds_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_response_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_security_smoke.py
PYTHONPATH=. python scripts/relaylm_e1_evaluation_consolidation_smoke.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
```

## Non-goals

E1-R5 does not add O2/O3 supervision, polling, daemons, new queue authority, worker authority, browser-owned trust, automatic bootstrap, broad memory layout migration, Pin / Unpin semantics, Held Apply / Discard behavior, Forget / Correct behavior, Secondary MEM consolidation, RelaySOUL mutation, media runtime work, or post-hoc visible response rewriting.

## Source evidence

- [E1-R5 completion report](../mvp/wave7/e1r5_completion_report.md)
- [E1-R5 Post-Wave-7 Correction Convergence Audit](e1r5_post_wave7_correction_convergence_audit.md)
- Source PR: #439
- Canonical fold-in PR: #491
