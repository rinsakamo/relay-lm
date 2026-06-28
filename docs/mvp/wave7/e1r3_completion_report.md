---
relaylm_doc_type: implementation_completion_report
relaylm_authority: e1r3_implementation_completion_report
relaylm_status: historical_after_merge
relaylm_volatility: low
relaylm_owner: evaluation
relaylm_current_status_source: ../../PROJECT_STATUS.md
---
# E1-R3 Completion Report

Source PR: #436.

## Scope

Implements E1-R3 provenance-preserving Primary MEM formation summary.

## Implementation boundary

- Adds a deterministic speaker-provenance formation helper.
- Partitions user assertion, assistant acknowledgement, assistant speculation/non-factual context, scene qualification, trust admission, and excluded evidence.
- Routes finalized-turn governed experience construction through a user-only `memory_candidate_payload`.
- Keeps the existing C1-5 protected-source payload compatible by not adding the formation summary to the exact protected source payload.
- Adds content-free projection flags/counts for formation provenance.

## Non-goals

- E1-R4 retrieval-response grounding and unsupported-detail suppression.
- O2/O3 supervised or always-on operation.
- Scheduler loops, polling, sleep, daemon, service supervision, or worker pools.
- Browser-owned trusted admission.
- Automatic character-store bootstrap.
- Pin / Unpin, Held Apply / Discard, Forget, Correct, Merge, Supersession, or Secondary MEM runtime changes.
- RelaySOUL mutation, TTS/audio/avatar/Live2D/ASR, or peer transport.

## Tests / smokes run

Connector-local validation performed against the new helper and slice smokes:

```bash
PYTHONPATH=/mnt/data/e1r3 python -m compileall -q /mnt/data/e1r3/relaylm /mnt/data/e1r3/scripts
PYTHONPATH=/mnt/data/e1r3 python /mnt/data/e1r3/scripts/relaylm_e1r3_provenance_formation_summary_smoke.py
PYTHONPATH=/mnt/data/e1r3 python /mnt/data/e1r3/scripts/relaylm_e1r3_provenance_formation_security_smoke.py
```

Expected repository validation after checkout / CI:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_e1r3_provenance_formation_summary_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r3_provenance_formation_security_smoke.py
PYTHONPATH=. python scripts/relaylm_e1_evaluation_consolidation_smoke.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6c1_primary_worker_smoke.py
PYTHONPATH=. python scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py
PYTHONPATH=. python scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py
```

## Content leakage review

Public projections expose only statuses, counts, and booleans. They do not expose raw user text, assistant text, protected source body, queue payload, store root, source path, claim token, lease owner, token digest, source digest, or raw memory body.

## Authority preservation

E1-R3 preserves C1-5 protected-source authority, B2 queue authority, B3 lifecycle authority, C2 execution authority, M3a-M3h write authority, M2 retrieval authority, I-4 lifecycle exclusion, I-5 Pin governance, and I-7 Held Governance. It changes only the worker-internal formation-summary semantics and the user-only text handed to the existing governed experience summary helper.

## Downstream handoff to E1-R4

E1-R4 remains planned/unimplemented for evidence-grounded recall behavior and unsupported-detail suppression. E1-R3 proves that formation evidence is speaker-provenance-safe; it does not prove that later assistant responses cite or phrase retrieved memory safely.
