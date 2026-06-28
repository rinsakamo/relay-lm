---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r3_implementation_completion_report
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: evaluation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md
  - ../../architecture/e1_evaluation_consolidation.md
  - ../../architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md
---
# E1-R3 Provenance-Preserving Primary MEM Formation Summary Completion Report

## Scope

E1-R3 implements provenance-preserving Primary MEM formation summary construction.

Implemented boundary:

```text
finalized-turn source
  -> explicit speaker partition
  -> user assertion evidence
  -> assistant acknowledgement / non-factual evidence
  -> scene/trust qualification evidence
  -> user-only memory candidate payload
  -> existing governed experience summary
```

## Implemented production boundary

Implemented production behavior:

- Added `relaylm.relaymem_provenance_formation_summary`.
- Added deterministic `relaymem.primary_formation_provenance_summary.v0` runtime-private formation evidence.
- Partitioned user assertion, assistant acknowledgement, assistant speculation/non-factual context, scene qualification, trust admission, and excluded evidence.
- Routed finalized-turn governed experience construction through a user-only `memory_candidate_payload`.
- Preserved the exact existing C1-5 protected-source payload shape by keeping the E1-R3 formation summary outside the protected-source payload.
- Added content-free public projection counts and provenance flags.
- Updated Phase 6 runtime enqueue validation so the protected governed experience summary is expected to be user-only while assistant text remains in protected governed messages and private provenance evidence.

## Preserved authorities and non-goals

Preserved authorities:

- C1-5 protected-source persistence remains the protected-source authority.
- B2 queue publication and B3 lifecycle authorities remain unchanged.
- C2/C1-2 worker execution remains unchanged.
- M3a-M3h write authorities remain unchanged.
- M2 retrieval, I-4 lifecycle exclusion, I-5 Pin, and I-7 Held Governance remain unchanged.

Non-goals preserved:

- No E1-R4 retrieval-response grounding or unsupported-detail suppression.
- No O2/O3 supervision or always-on operation.
- No scheduler loop, polling, sleep, daemon, service supervision, or worker pool.
- No browser-owned trusted admission.
- No automatic character-store bootstrap.
- No Pin / Unpin, Held Apply / Discard, Forget, Correct, Merge, Supersession, or Secondary MEM runtime changes.
- No RelaySOUL mutation, TTS/audio/avatar/Live2D/ASR, or peer transport.

## Changed files

```text
relaylm/relaymem_provenance_formation_summary.py
relaylm/relaymem_slp_finalized_turn_source.py
scripts/relaylm_e1r3_provenance_formation_summary_smoke.py
scripts/relaylm_e1r3_provenance_formation_security_smoke.py
scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py
scripts/relaylm_e1_evaluation_consolidation_smoke.py
scripts/relaylm_documentation_current_boundary_smoke.py
docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md
docs/mvp/wave7/e1r3_completion_report.md
docs/PROJECT_STATUS.md
docs/architecture/e1_evaluation_consolidation.md
docs/architecture/project_execution_plan.md
docs/architecture/relaymem_slp_current_target.md
docs/README.md
docs/architecture/README.md
docs/mvp/README.md
```

## Validation evidence

Expected validation:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_e1r3_provenance_formation_summary_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r3_provenance_formation_security_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6_runtime_enqueue_source_capture_smoke.py
PYTHONPATH=. python scripts/relaylm_e1_evaluation_consolidation_smoke.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave7/e1r3_completion_report.md
PYTHONPATH=. python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```

Connector-preparation note: this branch was prepared through the GitHub connector because the local `~/work/relay-lm` checkout is unavailable in this environment. Python syntax for the new module and slice smokes was checked before pushing; full repository validation is expected to run in GitHub Actions.

## Known limitations

- E1-R3 does not make later assistant responses evidence-grounded.
- E1-R3 does not implement unsupported-detail suppression.
- E1-R3 does not alter which Primary MEM candidates are retrieved later.
- E1-R3 does not change the C1-5 protected-source payload schema.
- E1-R3 does not process already queued or already formed memory.
- E1-R3 does not expose raw provenance evidence in public diagnostics.

## Shared documentation update inputs

After merge, a later convergence PR should update shared status/index documents to state:

```text
E1-R3 provenance-preserving Primary MEM formation summary: complete
Boundary: speaker-provenance-safe formation summary, user-only memory candidate payload
Authority preserved: no queue, worker, scheduler, retrieval, lifecycle, or response-grounding authority changes
Remaining E1 follow-up: E1-R4 retrieval-response grounding and unsupported-detail suppression
```

## Source pull request

- PR: #436
- URL: https://github.com/rinsakamo/relay-lm/pull/436
