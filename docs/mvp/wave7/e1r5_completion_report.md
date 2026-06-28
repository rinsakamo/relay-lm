---
relaylm_doc_type: implementation_completion_report
relaylm_authority: wave_slice_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - cross-slice sequencing
  - other phase completion
---
# E1-R5 Completion Report — Primary MEM Recall Candidate Discovery Bridge

Last reviewed: 2026-06-28 JST

This report is evidence for one implementation pull request. It is not repository-wide current-status authority and does not open the next wave or release/evaluation gate.

## Scope

E1-R5 fixes the request-side gap where a durable character-scoped Primary MEM page can exist but later recall still projects `selected_count: 0` because no scoped Primary page becomes a selected M2 candidate.

Base branch: `main`.

Start main SHA: `cc1417f93b679e3c2ca2bb5ed78f53e2cb93ad7a`.

## Implemented production boundary

E1-R5 adds a bounded Primary MEM candidate discovery bridge inside the request-side Primary recall runtime path.

The existing M2 candidate path remains the preferred relevance owner. The E1-R5 fallback runs only when no eligible scoped Primary candidate survives existing M2 narrowing. It then derives bounded candidates from the character-scoped Primary index/log controls, validates page schema, path, namespace, digest, index/log consistency, lifecycle eligibility, and query relevance, then rebuilds the existing RelayCTX / E1-R4 grounded recall handoff.

The bridge remains fail-closed when `query_summary.term_hints` is absent or empty. In that case it records `primary_candidate_query_terms_missing` and does not promote the first scoped Primary MEM from the index fallback.

Fallback relevance is evaluated only against memory content fields (`summary` and `title`), not storage metadata such as page path or memory kind. Discovery scans the loaded bounded control index before namespace and relevance filtering so later eligible entries are not skipped by a pre-filter cap.

CJK gram-only relevance now requires a meaningful overlap threshold before a fallback candidate is treated as relevant, preventing weak common-phrase overlaps from grounding unrelated Primary MEM.

E1-R5 also preserves the bridge discovery diagnostics through the audit projection contract so persisted traces retain whether fallback discovery ran and how many bounded candidates it found.

Primary recall now accepts the same namespace token shape used by queue/worker formation, including slash-style namespace tokens such as `character/default`, while keeping exact namespace values runtime-private.

## Preserved authorities and non-goals

E1-R5 does not add worker, queue, scheduler, browser trust, store mutation, RelaySOUL, Pin / Unpin, Held Governance, Forget / Correct, TTS/audio/avatar, O2/O3 authority, or post-hoc visible response rewriting.

The configured RelayMEM root remains operator-owned. Character id is converted to an opaque hash partition and is not used directly as a path component. Public diagnostics remain content-free and must not expose store roots, page paths, digests, lineage, private ids, queue payloads, or protected source bodies.

## Changed files

Production / runtime:

- `relaylm/relaymem_primary_recall_candidate_bridge_runtime.py`
- `relaylm/audit_projection_contracts.py`
- `relaylm/__init__.py`

Tests / smokes:

- `scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py`
- `scripts/relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py`
- `scripts/relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py`
- `scripts/relaylm_e1r5_primary_mem_recall_bridge_relevance_bounds_smoke.py`
- `scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py`

Documentation:

- `docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md`
- `docs/mvp/wave7/e1r5_completion_report.md`

## Validation evidence

New validation coverage:

```text
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_bridge_relevance_bounds_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py
```

Regression targets carried in the PR body:

```text
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_response_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r4_grounded_recall_security_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i2_real_soul_lab_observation_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py
PYTHONPATH=. python scripts/relaylm_e1_evaluation_consolidation_smoke.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```

Review follow-up on PR #439 added fail-closed coverage for empty `query_summary.term_hints` after automated review identified that empty query terms could otherwise promote an unrelated first scoped Primary MEM.

A later review follow-up tightened fallback relevance so storage metadata cannot satisfy query matching and removed the pre-filter 128-entry index scan cap.

Additional review follow-up tightened weak CJK gram-only relevance and preserved E1-R5 Primary recall discovery fields in audit projections.

The execution environment used for the initial PR preparation did not contain a local checkout of `rinsakamo/relay-lm`, so full repository smoke execution remains a PR/CI gate.

## Known limitations

E1-R5 does not implement a broader retrieval ranking engine. It only bridges the missing character-scoped Primary MEM candidate handoff when bounded query hints are available.

E1-R5 does not make filesystem scans, does not depend on a `runtime/memory/memory` symlink workaround, and does not migrate older flat-store memory layouts.

## Shared documentation update inputs

Wave convergence wording:

```text
E1-R5 is complete for scoped Primary MEM recall candidate discovery. It preserves M2 as the preferred relevance owner, adds a bounded index/log/page fallback only when scoped Primary MEM is otherwise not selected, and keeps the fallback fail-closed without query hints.
```

Handoff path:

```text
docs/architecture/e1r5_primary_mem_recall_candidate_bridge.md
docs/mvp/wave7/e1r5_completion_report.md
```

Cross-slice risk:

```text
The bridge must remain bounded, exact-namespace, lifecycle-aware, content-free in public projections, content-only for relevance, audit-visible for public discovery diagnostics, and fail-closed without query hints.
```

Recommended next phase:

```text
No new wave is opened by this report. Continue with PR/CI review and only converge shared status documentation after merge.
```

## Source pull request

- PR: #439
- URL: https://github.com/rinsakamo/relay-lm/pull/439
