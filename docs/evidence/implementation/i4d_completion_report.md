---
relaylm_doc_type: implementation_completion_report
relaylm_authority: phase_i4d_primary_retrieval_exclusion_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase_i4d_primary_retrieval_exclusion.md
  - ../waves/wave3_cross_slice_convergence_audit.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Primary MEM retrieval, lifecycle, or historical-projection behavior
  - Forget mutation, restore, or physical deletion behavior
relaylm_source_commit: 81c58516a4ba04c6e439ff17d633575bb193f843
relaylm_source_origin_commit: 48e890f05f76196b73267559b079f4a05c441077
relaylm_source_pr: 414
relaylm_recorded_on: 2026-06-27
relaylm_source_blob: eecdd09ad3e6f2cc344b955f1962d034d7f321bb
relaylm_source_content_sha256: 6fc50a3b977636be47e270f21df4764127b695a280ef41996441a1589ce7eedc
relaylm_pre_cutover_blob: eecdd09ad3e6f2cc344b955f1962d034d7f321bb
relaylm_pre_cutover_content_sha256: 6fc50a3b977636be47e270f21df4764127b695a280ef41996441a1589ce7eedc
relaylm_exact_source_snapshot: i4d_completion_report-source.txt
---
# Phase I-4D Implementation Completion Report

## Status and authority

This is frozen implementation evidence for PR #414. Current behavior belongs to [Phase I-4D Primary Retrieval Exclusion](../../architecture/phase_i4d_primary_retrieval_exclusion.md), the current Primary MEM lifecycle/retrieval implementation, the I-4 continuation handoffs and focused smokes, and the current lifecycle projection/UI authorities where applicable.

The [exact snapshot](i4d_completion_report-source.txt) is byte-identical to the source final-head, source merge, and pre-cutover forms: blob `eecdd09ad3e6f2cc344b955f1962d034d7f321bb`, SHA-256 `6fc50a3b977636be47e270f21df4764127b695a280ef41996441a1589ce7eedc`. No post-source report modification exists.

## Scope

PR #414 implemented ordinary Primary MEM lifecycle-aware retrieval exclusion, filtering non-canonical, hidden, prepared, recovery-required, corrupt, ambiguous, or unsafe candidates after M2 relevance selection and before RelayCTX/backend-bound injection, plus a read-only versioned historical lifecycle projection.

## Implemented production boundary

The recorded surface reuses the I-4B/I-4C2 current-state scanner, builds one bounded request-scoped lifecycle index, and filters after M2 selection. Only the canonical current physical revision remains eligible. The durable `relaylm.lab.memory_used.v0` receipt is unchanged; a new `relaylm.lab.memory_used_lifecycle.v1` overlay is added.

## Preserved authorities and non-goals

I-4B remains current-state/fence authority, I-4C1 remains hidden-successor authority, I-4C2 remains recovery/finalization authority. This cutover adds no Forget mutation API/UI, restore, purge, physical deletion, or scheduler/worker change.

## Changed files

The source PR changed the retrieval eligibility/runtime integration modules, the SOUL Lab lifecycle projection/parser/API, seven permanent smokes, one then-dedicated workflow, one architecture handoff, and this report. This cutover changes no production file.

## Validation evidence

Current validation uses the canonical report, Wave 3 convergence and security smokes, the focused I-4D lifecycle/prior-revision/recovery/RelayCTX/history/fresh-conversation/security smokes, and I-4B/I-4C1/I-4C2 regressions.

## Known limitations

This source slice did not itself add Forget mutation API/UI (I-4E) or the full product-completion validation matrix (I-4F).

## Shared documentation update inputs

- Historical completion: Primary lifecycle-aware retrieval exclusion completed at PR #414.
- Current authority: [Phase I-4D Primary Retrieval Exclusion](../../architecture/phase_i4d_primary_retrieval_exclusion.md), current Primary MEM lifecycle/retrieval implementation, I-4 continuation handoffs, and focused smokes.
- Runtime non-change: this cutover changes documentation and validation paths only; no runtime behavior changes.

## Source pull request

- PR: #414
- URL: https://github.com/rinsakamo/relay-lm/pull/414
