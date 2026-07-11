---
relaylm_doc_type: evidence
relaylm_authority: e1r5_post_wave7_correction_convergence_record
relaylm_status: frozen
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Primary recall adapter behavior
  - exact E1-R5 or E1-R4 contracts
  - Wave 8 and later implementation status
relaylm_source_commit: 676678a004c688eca856e37b3ecf48f98801452c
relaylm_source_pr: 498
relaylm_origin_pr: 452
relaylm_recorded_on: 2026-06-30
relaylm_source_blob: 0d7cbceca1259d127ebf4fa1a7f91bcbf9e144e5
relaylm_source_content_sha256: 552e8744b3f32f2e4c21eb8273f56fe0ee4f95e22cf33ad7ae734625dcc41edb
---
# E1-R5 Post-Wave-7 Correction Convergence Audit

Generated: 2026-06-30 JST.

## Status and authority

The correction audit was introduced through PR #452. Its exact pre-cutover source was later converged through PR #498 after PR #491 closed PM-D8 by folding the bounded E1-R5 fallback into the canonical Primary recall adapter.

This document is frozen historical evidence for that post-Wave-7 correction point. Current repository status, current E1 behavior, and exact lower-level contracts remain authoritative in their dedicated current documents. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md).

The exact submitted source is retained byte-for-byte as [e1r5_post_wave7_correction_convergence_audit-source.txt](e1r5_post_wave7_correction_convergence_audit-source.txt).

## Purpose

This audit records the post-Wave-7 E1-R5 correction convergence after the E1 recall proof boundary was corrected. It is historical evidence. Current repository status remains owned by [Project Status](../../PROJECT_STATUS.md), and MVP sequencing and Post-MVP decision debt remain owned by [Project Execution Plan](../../architecture/project_execution_plan.md).

E1-R5 is a correction to the Wave 7 E1 proof boundary. It does not reopen Wave 7 and does not add production authority beyond the bounded request-side fallback described in [E1-R5 Primary MEM Recall Candidate Discovery Bridge](../../architecture/e1r5_primary_mem_recall_candidate_bridge.md).

## Source PR inventory

| Slice | Source PR | Dedicated handoff | Completion report |
|---|---:|---|---|
| E1-R5 bounded scoped Primary MEM recall candidate discovery bridge | #439 | [E1-R5 Primary MEM Recall Candidate Discovery Bridge](../../architecture/e1r5_primary_mem_recall_candidate_bridge.md) | [E1-R5 completion report](../../mvp/wave7/e1r5_completion_report.md) |
| PM-D8 E1-R5 bridge canonical Primary recall adapter fold-in | #491 | [E1-R5 Primary MEM Recall Candidate Discovery Bridge](../../architecture/e1r5_primary_mem_recall_candidate_bridge.md) | n/a |

## Converged correction boundary

```text
M2 remains the preferred relevance owner.
E1-R5 is a bounded scoped Primary candidate fallback only when M2 yields no eligible scoped Primary candidate.
E1-R5 reuses the shared I-4D lifecycle eligibility index.
E1-R5 hands selected evidence to the existing RelayCTX / E1-R4 grounded recall path.
```

Current docs must not read the E1 recall proof as "M2 alone always selects current eligible scoped Primary MEM". The corrected proof boundary is M2-preferred recall plus the E1-R5 bounded scoped candidate fallback for the no-M2-scoped-candidate gap.

## Authority compatibility

- E1-R5 does not replace M2 as the preferred relevance owner.
- E1-R5 does not own an independent lifecycle policy; hidden, prepared, recovery-required, corrupt, prior, and cross-scope candidates remain excluded through the shared I-4D eligibility path.
- E1-R5 does not create new memory mutation, queue, worker, scheduler, browser trust, RelaySOUL, or media runtime authority.
- E1-R4 remains request-side only and consumes the selected-memory shape produced by either the M2-preferred path or the E1-R5 fallback.

## PM-D8 closure

PM-D8 is closed by PR #491: the bounded E1-R5 Primary MEM candidate fallback is folded into the canonical Primary recall adapter.

```text
PM-D8: E1-R5 bounded Primary MEM candidate fallback folded into canonical Primary recall adapter in PR #491
```

The former runtime bridge module remains compatibility no-op only. The canonical fold-in preserves the same E1-R5 smoke coverage expectations and remains related to PM-D5 historically because both touch Primary recall layout discovery and adapter/root handling.

## Validation boundary

The correction remains covered by the E1-R5 and adjacent E1/I-4D smoke set:

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

## Non-goals preserved

This convergence audit does not implement O2/O3, polling, daemons, service supervision, worker pools, browser-owned trust, new lifecycle authority, memory mutation, RelaySOUL mutation, TTS/audio/avatar/Live2D/ASR, or post-hoc visible response rewriting.
