---
relaylm_doc_type: implementation_completion_report
relaylm_authority: phase_i4f_forget_product_validation_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/phase_i4f_forget_validation.md
  - ../../architecture/phase_i4e_forget_api_ui.md
  - ../../architecture/phase_i4d_primary_retrieval_exclusion.md
  - i4c2-primary-forget-recovery-finalization-handoff.md
  - i4c1-primary-forget-hidden-successor-handoff.md
  - ../../architecture/phase_i4b_primary_current_state_shared_fence.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current Forget runtime, API, UI, lifecycle-exclusion, recovery, or token behavior
  - current implementation sequencing or release readiness
  - current operator procedure
  - restore, unhide, purge, physical deletion, or batch Forget behavior
relaylm_source_commit: 2aac80c51c65b64dc70fd2c5f58b6ac729e89a23
relaylm_source_origin_commit: 937718dcb328fda5e3e37bb951b39fc66629f57a
relaylm_source_pr: 427
relaylm_recorded_on: 2026-06-27
relaylm_source_blob: f7c451802f97109fd431cbb1f6a57910d4ea5b93
relaylm_source_content_sha256: 45e486844536829d23b9e303ef5e7925385f94ac5887027669facadafc9bbce5
relaylm_pre_cutover_blob: f7c451802f97109fd431cbb1f6a57910d4ea5b93
relaylm_pre_cutover_content_sha256: 45e486844536829d23b9e303ef5e7925385f94ac5887027669facadafc9bbce5
relaylm_exact_source_snapshot: i4f_completion_report-source.txt
---
# I-4F Forget Product Completion Validation Report

## Status and authority

This document is frozen implementation evidence for the validation-only I-4F Forget product-completion slice introduced by PR #427, whose final source head is `2aac80c51c65b64dc70fd2c5f58b6ac729e89a23` and merge commit is `937718dcb328fda5e3e37bb951b39fc66629f57a`. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md). Current I-4F validation authority belongs to [Phase I-4F Forget Product Completion Validation](../../architecture/phase_i4f_forget_validation.md), the existing production implementation and I-4 contracts, the focused I-4F smoke suite, and the SOUL Lab Forget UI validation.

The exact pre-cutover report is retained byte-for-byte as [i4f_completion_report-source.txt](i4f_completion_report-source.txt). The source PR final-head, source merge, and pre-cutover `main` forms all use Git blob `f7c451802f97109fd431cbb1f6a57910d4ea5b93` and content SHA-256 `45e486844536829d23b9e303ef5e7925385f94ac5887027669facadafc9bbce5`; no post-source report modification exists.

Last reviewed: 2026-06-27 JST

This report is frozen evidence for one implementation pull request. It is not current runtime, repository-wide status, sequencing, release-readiness, or operator-procedure authority. This cutover changes documentation paths, documentation validation, and CI selection only; it changes no runtime behavior.

## Scope

At source PR #427, I-4F completed validation of explicit Forget / Hide for one real current active Primary MEM across loopback API, lifecycle apply/recovery, ordinary retrieval and RelayCTX exclusion, UI refresh, restart, concurrency, stale-client, token, security, and scope-isolation boundaries.

I-4F was validation-first and added no new production mutation authority. No production bug fix was required in the source PR.

## Implemented production boundary

The recorded source boundary proves:

- read-only preflight before explicit apply;
- strict apply-token binding and bounded replay behavior;
- existing I-4C1/I-4C2 hidden-successor, crash-recovery, finalization, tombstone, and response-loss behavior;
- I-4D fail-closed ordinary M2/RelayCTX exclusion across hidden, prepared, corrupt, ambiguous, unsafe, cross-scope, unresolved, and prior physical revisions;
- loopback-only I-4E API access and explicit SOUL Lab confirmation;
- fresh process history reread, stale-browser response fencing, fresh ordinary conversation exclusion, and bounded lifecycle visibility;
- no private path, token digest, raw tombstone, reason body, exception, or memory-content leakage.

## Preserved authorities and non-goals

- I-4B remains current-state resolver, shared mutation fence, read-only preflight, token validation, and bounded history authority.
- I-4C1 remains durable prepared evidence and hidden-successor lifecycle commit authority.
- I-4C2 remains prepared resume, convergence, tombstone finalization, public apply, and response-loss replay authority.
- I-4D remains ordinary M2/RelayCTX exclusion and historical lifecycle-overlay authority.
- I-4E remains loopback-only API and SOUL Lab Forget UI authority.
- UI-B1A remains read-only lifecycle and operation visibility only.

I-4F did not implement restore, unhide, purge, physical deletion, batch Forget, Secondary MEM consolidation, RelaySOUL mutation, Pin / Unpin runtime behavior, Held Apply / Discard runtime behavior, queue/worker/scheduler behavior, polling, sleep loops, daemonization, supervision, or always-on operation.

## Changed files at the source boundary

The source PR changed the I-4F architecture handoff, five focused validation smokes, its completion report, its then-dedicated workflow, and shared documentation/status validation. It changed no production module. The complete historical changed-file list remains byte-exact in the attached source snapshot.

## Validation evidence

The focused source commands remain recorded in [the exact snapshot](i4f_completion_report-source.txt). Current cutover validation uses the canonical report path:

```bash
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py --check-model docs/evidence/implementation/i4f_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py --check-all
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_fault_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_concurrency_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_security_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_phase_i4f_forget_validation_ui_smoke.py
```

The dedicated I-4F workflow present at the source boundary is absent from the current tree and is not recreated. Current I-4A through I-4F backend/API/UI regressions and the completion-report check are routed through the consolidated UI `forget_lifecycle_regressions` group; SOUL Lab frontend validation remains owned by the consolidated UI workflow.

## Known limitations

Forget product-complete does not include restore, unhide, purge, physical deletion, or batch Forget. The source-boundary statements that I-5A and I-7A/B had only contract/read-only preflight and that O1E/O1F/O2/O3 were separate work remain historical statements; later current status belongs to current documentation and dedicated evidence. Direct Home-origin Primary MEM formation was outside this validation slice.

## Shared documentation update inputs

- Completion wording: Phase I-4F full Forget validation is complete; Phase I-4 overall is complete through explicit Forget / Hide product validation.
- Forget product-complete means explicit loopback/SOUL Lab Forget can hide one current active Primary MEM and prove later ordinary retrieval/RelayCTX exclusion under crash, race, stale-browser, token, security, restart, fresh-conversation, and scope-isolation conditions.
- Current authority remains with the I-4F handoff, existing production implementation and I-4 contracts, focused smokes, and SOUL Lab UI validation.
- This cutover changes no runtime behavior, schema, configuration, mutation authority, or historical validation conclusion.

## Source pull request

- PR: #427
- URL: https://github.com/rinsakamo/relay-lm/pull/427
