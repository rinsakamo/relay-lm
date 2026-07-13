---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r1_trusted_home_scene_admission_implementation_evidence
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_update_trigger:
  - metadata or link repair only
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1r1_trusted_home_scene_admission.md
  - ../../architecture/e1_evaluation_consolidation.md
  - ../../architecture/soul_lab_ui_b0_real_home_conversation.md
  - ../../architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
relaylm_not_authoritative_for:
  - current repository-wide implementation status
  - current trusted Home scene-admission runtime or trust policy
  - current source, queue, worker, or scheduler behavior
  - current implementation sequencing or release readiness
  - current operator procedure
relaylm_source_commit: 39c5b982c9883ee39792450d40e4528c8a8db84b
relaylm_source_origin_commit: 52768cbdac3c9630373a2c369574002ac196e72b
relaylm_source_pr: 433
relaylm_recorded_on: 2026-06-27
relaylm_source_blob: 3d4e78d63e4be836e1de8b0ad1781a513e5349bc
relaylm_source_content_sha256: 35c8d68527fea415465119f28ca366897ab7d320f6828fa92489dff4af58c6d7
relaylm_exact_source_snapshot: e1r1_completion_report-source.txt
---
# E1-R1 Trusted Home Scene Admission Completion Report

## Status and authority

This document is frozen implementation evidence for the E1-R1 trusted Home scene-admission slice introduced by PR #433, whose final source head is `39c5b982c9883ee39792450d40e4528c8a8db84b` and merge commit is `52768cbdac3c9630373a2c369574002ac196e72b`. Current repository-wide status belongs to [Project Status](../../PROJECT_STATUS.md). Current trusted Home scene-admission behavior belongs to [E1-R1 Trusted Home Scene Admission](../../architecture/e1r1_trusted_home_scene_admission.md), the production implementation, and the focused E1-R1 smoke suite.

The exact pre-cutover report is retained byte-for-byte as [e1r1_completion_report-source.txt](e1r1_completion_report-source.txt). Statements below describe the source PR boundary unless explicitly qualified. Legacy-path strings inside the exact snapshot are historical source text, not live repository references.

Last reviewed: 2026-06-27 JST

This report is evidence for one implementation pull request. It is not current runtime, repository-wide status, trust-policy, source/queue/worker behavior, sequencing, release-readiness, or operator-procedure authority.

## Scope

E1-R1 implements a bounded trusted Home scene-admission path for SOUL Lab Home-origin ordinary conversation. The path is server-owned and route-owned; client-provided trust claims are not accepted as persistence authority.

## Implemented production boundary

Implemented boundary:

```text
SOUL Lab Home-origin ordinary conversation
  -> server-owned route admission decision
  -> existing finalized-turn source builder
  -> existing C1-5 protected source persistence
  -> existing B2 durable queue admission
  -> existing O0/O1/C2 drain compatibility
```

The new gate is configured per route with `trusted_home_scene_admission_mode`:

```text
disabled | dry_run | apply
```

Default remains disabled. Dry-run mode reports a content-free preview without source/queue mutation. Apply mode delegates to the existing source/queue authority.

## Preserved authorities and non-goals

Preserved authorities:

- Existing Chat Completions request handling remains the Home conversation path.
- Existing finalized-turn source builder remains source authority.
- Existing durable protected-source and B2 durable queue publication remain admission authority.
- Existing O0/O1/C2 worker path remains drain authority.
- Existing content-free public projection rules remain in force.

Non-goals preserved:

- No E1-R2 bootstrap command.
- No E1-R3 provenance-preserving summary-quality implementation.
- No E1-R4 evidence-grounded generation behavior.
- No O2/O3 supervision or always-on operation.
- No TTS/audio/avatar/Live2D/ASR/peer transport.
- No new client-owned trust authority.
- No scheduler loop, polling loop, timer, daemon, service supervision, or background worker.
- No new queue format.

## Changed files

```text
relaylm/config.py
relaylm/pipeline_context.py
relaylm/request_scope.py
relaylm/trusted_home_scene_admission.py
relaylm/relaymem_slp_runtime_finalization.py
scripts/relaylm_e1r1_trusted_home_scene_admission_smoke.py
docs/architecture/e1r1_trusted_home_scene_admission.md
docs/evidence/implementation/e1r1_completion_report.md
.github/workflows/e1r1-trusted-home-scene-admission.yml
```

## Validation evidence

Expected validation at source PR #433:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_e1r1_trusted_home_scene_admission_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py docs/evidence/implementation/e1r1_completion_report.md
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```

Connector preparation validation performed in this environment:

```bash
python -m py_compile relaylm/config.py relaylm/pipeline_context.py relaylm/request_scope.py relaylm/trusted_home_scene_admission.py relaylm/relaymem_slp_runtime_finalization.py scripts/relaylm_e1r1_trusted_home_scene_admission_smoke.py
```

At source PR #433, the full repository checkout was unavailable in the connector environment, so GitHub Actions was the execution source of truth for full in-repo smoke validation. The dedicated E1-R1 workflow present at that source boundary is absent from the current tree and is not recreated during this cutover; current validation belongs to the consolidated runtime smoke inventory.

## Known limitations

- E1-R1 proves only trusted Home scene admission into the existing source/queue path; it does not prove E1-R2 bootstrap, E1-R3 speaker-provenance quality, or E1-R4 grounded recall behavior.
- E1-R1 does not start a worker, scheduler, service, daemon, polling loop, or always-on process.
- Shared current-status docs remain convergence-thread inputs after this implementation PR is merged.

## Shared documentation update inputs

After merge, shared docs should continue to state:

```text
E1-R1 trusted Home scene admission: complete
E1-R2 character-store bootstrap: pending
E1-R3 speaker-provenance-safe formation: pending
E1-R4 evidence-grounded recall response behavior: pending
Direct Home-origin formation now has a bounded server-owned route-admission path, but remains dependent on existing O0/O1/C2 drain operation for actual Primary MEM formation.
```

## Source pull request

- PR: #433
- URL: https://github.com/rinsakamo/relay-lm/pull/433
