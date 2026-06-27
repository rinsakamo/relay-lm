---
relaylm_doc_type: implementation_handoff
relaylm_authority: wave4_cross_slice_convergence_record
relaylm_status: historical_after_merge
relaylm_volatility: frozen
relaylm_owner: implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - project_execution_plan.md
  - current_target_migration_guide.md
  - relaymem_slp_current_target.md
  - wave3_cross_slice_convergence_audit.md
  - o1d2_scheduler_policy.md
  - phase_i4e_forget_api_ui.md
  - soul_lab_ui_b1a_lifecycle_visibility.md
  - phase_i5_pin_unpin_contract.md
  - phase_i7ab_held_apply_discard_contract.md
---
# Wave 4 Cross-Slice Convergence Audit

Last reviewed: 2026-06-27 JST.

This audit is the frozen convergence record for the merged Wave 4 implementation PRs. It reconciles shared documentation, current status, current/target guidance, index links, and documentation smoke after the individual PRs merged. It does not add production runtime behavior.

## Source PR inventory

| PR | Slice | Implemented boundary |
|---|---|---|
| #417 | I-5A | Pin / Unpin contract and read-only preflight |
| #418 | O1D2 | Bounded scheduler fairness / retry-time / backoff / jitter / pacing policy |
| #420 | I-4E | Loopback Forget API and SOUL Lab UI |
| #421 | UI-B1A | Read-only lifecycle and operation visibility |
| #423 | I-7A/B | Held Apply / Discard contract and read-only preflight |

PR #422 is not a Wave 4 implementation slice. It is the docs execution-plan / roadmap consolidation prerequisite that W4-INT builds on.

## Merge commit inventory

| PR | Merge commit |
|---|---|
| #417 I-5A | `2f8597911774b70f1c001db8332b3dfcc18d23ca` |
| #418 O1D2 | `49fb43130155826fcc8b2b951d77484ff8ddaddf` |
| #420 I-4E | `3e3d2570ecdfcde4c8bfdee06c5607cb6632c133` |
| #421 UI-B1A | `5736636da839486140f72c731f18a4a85c39b13c` |
| #422 docs consolidation prerequisite | `ff255b47ca8b1ef87837f65aa185dac1fa3faf56` |
| #423 I-7A/B | `5e0f866e959ab2bc5af00e0502b2026f4b52a779` |

W4-INT work started only after main contained all commits above.

## Wave 4 implemented boundary

Wave 4 implementation tracks are complete at these exact boundaries:

```text
O1D2 bounded scheduler policy/fairness/pacing: complete
Phase I-4E loopback Forget API and SOUL Lab UI: complete
UI-B1A read-only lifecycle visibility: complete
I-5A Pin / Unpin contract and read-only preflight: complete
I-7A/B Held Apply / Discard contract and read-only preflight: complete
```

The Wave 4 completion statement does not complete O1, I-4, I-5, or I-7 overall. W4-INT completes only after the convergence PR containing this audit is merged.

## Cross-slice authority map

| Area | Current authority after Wave 4 |
|---|---|
| Scheduler policy | O1D2 owns bounded content-free policy wrapping one existing O1D1 round. |
| Scheduler operation | O1E owns stale recovery, cancellation checkpoints, and graceful shutdown. O1F owns operational validation. O2/O3 remain later service/supervision candidates. |
| Forget current state and mutation fence | I-4B remains current-state resolver, shared mutation fence, preflight-token, and bounded history authority. |
| Forget hidden successor and apply | I-4C1 remains hidden-successor commit authority. I-4C2 remains recovery, tombstone, finalization, and public apply authority. |
| Forget product surface | I-4E owns the loopback-only API and SOUL Lab UI surface. I-4F remains full validation. |
| Ordinary retrieval lifecycle exclusion | I-4D remains ordinary M2 / RelayCTX lifecycle exclusion and historical overlay authority. |
| SOUL Lab lifecycle visibility | UI-B1A owns read-only lifecycle / operation visibility panels and loopback content-free route. |
| Pin / Unpin | I-5A owns only contract and read-only preflight. Runtime apply, durable Pin state, API/UI, and ranking behavior remain later. |
| Held outcome governance | I-7A/B owns only contract and read-only Apply / Discard preflight. Runtime Apply / Discard and durable governance evidence remain later. |

## Preserved non-goals

The convergence audit preserves the non-goals from the source PRs:

```text
No polling or recurring automatic scheduling.
No sleep/timers, daemonization, service supervision, or always-on operation.
No stale-claim recovery, cancellation checkpoints, graceful shutdown, or signal handling.
No global scheduler lock or durable scheduler journal.
No O1B/O1C discovery changes and no I1-GC/C2/B3/worker semantic changes.

No restore, purge, unhide, repair, physical deletion, or automatic recovery control.
No retrieval-filtering change beyond the already implemented I-4D boundary.
No M2 ranking change and no snippet construction change.
No queue/scheduler/worker durability change from Forget UI.

No Pin apply or Unpin apply.
No durable Pin state.
No hidden-memory retrieval.
No semantic content mutation.

No Held Apply runtime.
No Held Discard runtime.
No B3 queue mutation, retry release, or terminal commit for held governance.
No Primary MEM page/index/log writes from held governance preflight.
No C2 worker or O1 scheduler invocation from held governance preflight.

No durable transcript persistence.
No TTS/audio/avatar/Live2D/ASR.
No public or remote binding.
```

## Security and content-leakage review

Wave 4 keeps public and browser-facing projections bounded and content-free. The convergence review confirms:

- queue records and lifecycle panels expose bounded state labels, not source bodies;
- O1D2 policy hints avoid private identity inputs for deterministic jitter;
- I-5A and I-7A/B preflight projections are read-only and use opaque short-lived tokens or bounded operation identifiers;
- I-4E browser calls remain loopback-only and do not accept browser-owned store roots or backend authority;
- UI-B1A uses `Cache-Control: no-store` and does not create mutation controls;
- this audit records PR numbers, merge commits, file references, and authority boundaries only.

The audit intentionally omits private runtime source bodies, conversation bodies, credentials, local machine locations, queue lease secrets, and internal evidence bytes.

## Concurrency / race / stale-token review

Wave 4 does not add new production mutation paths beyond the already merged I-4E loopback surface over existing I-4B/I-4C1/I-4C2 authorities. The convergence review preserves these boundaries:

- I-4B remains the shared current-state resolver, mutation fence, token, and history authority.
- I-4C1/I-4C2 remain the only hidden successor / recovery / tombstone finalization authorities.
- I-5A Pin / Unpin preflight is read-only and does not create durable Pin state.
- I-7A/B held governance preflight is read-only and does not mutate B3 queue state, Primary MEM pages, or worker state.
- O1D2 returns policy hints for an external caller and does not start another round by itself.

## Documentation convergence changes

W4-INT updates these shared current documents after the Wave 4 implementation PRs merged:

```text
docs/PROJECT_STATUS.md
docs/architecture/project_execution_plan.md
docs/README.md
docs/architecture/README.md
docs/mvp/README.md
docs/architecture/current_target_migration_guide.md
docs/architecture/relaymem_slp_current_target.md
scripts/relaylm_documentation_current_boundary_smoke.py
scripts/relaylm_mvp_completion_report_smoke.py
```

W4-INT also adds this audit and a dedicated cross-slice smoke/workflow.

## Smoke / validation coverage

W4-INT adds `scripts/relaylm_wave4_cross_slice_convergence_smoke.py` and `.github/workflows/wave4-cross-slice-convergence.yml`.

The required convergence validation set is:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=.:scripts python scripts/relaylm_wave4_cross_slice_convergence_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_mvp_completion_report_smoke.py
PYTHONPATH=.:scripts python scripts/relaylm_docs_link_check.py
```

Representative source-PR smokes remain owned by their dedicated Wave 4 implementation workflows.

## Remaining post-Wave-4 work

```text
O1E stale recovery / cancellation checkpoints / graceful shutdown
O1F operational validation
I-4F full Forget crash/race/security/fresh-conversation validation
Pin / Unpin runtime apply, API/UI, durable state, and ranking behavior
Held Apply / Discard runtime, API/UI, and durable governance evidence
E1 evaluation consolidation
O2/O3 only after O1E/O1F or explicit MVP need
```

## Frozen next inputs

The next planning input after W4-INT merge is:

```text
Wave 4 implementation tracks complete.
W4-INT merged.
O1 overall remains in progress at O1E/O1F.
Phase I-4 overall remains in progress at I-4F.
I-5A is complete only at contract/read-only preflight boundary.
I-7A/B is complete only at contract/read-only preflight boundary.
Post-Wave-4 work may proceed from Project Status and Project Execution Plan.
```
