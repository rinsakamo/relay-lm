---
relaylm_doc_type: evaluation_consolidation
relaylm_authority: e1_mvp_evaluation_evidence_consolidation
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - E1 evaluation evidence changes
  - direct Home-origin trusted formation decision changes
  - local MVP evaluation workflow changes
  - provenance or recall quality work becomes implemented
  - Primary recall candidate discovery changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact RelayMEM or RelaySLP schemas
  - production admission trust policy
  - future recall-grounding implementation details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - e1r3_provenance_preserving_primary_mem_formation_summary.md
  - ../contracts/grounded-recall.md
  - ../evidence/waves/wave7_cross_slice_convergence_audit.md
  - project_execution_plan.md
  - relaymem_slp_current_target.md
  - ../contracts/ui/home-conversation.md
  - ../contracts/ui/lifecycle-visibility.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i4_primary_mem_forget_hide_contract.md
  - o1f_operational_validation.md
---
# E1 MVP Evaluation Evidence Consolidation

Last reviewed: 2026-06-29 JST.

## Purpose

This document consolidates the current MVP E1 evaluation evidence after RT-1D-R5 retirement. E1-R1 through E1-R4 remain implemented current evidence; E1-R5 remains historical implementation evidence whose ordinary Primary serving role was retired by RT-1D-R5.

E1 is evidence-first. E1-R1 adds route-owned trusted Home admission. E1-R2 adds explicit dry-run-first store bootstrap. E1-R3 adds speaker-provenance-safe Primary MEM formation summary construction. E1-R4 remains the shared grounding policy for already-selected current ordinary-memory evidence. E1-R5 historically added a bounded Primary candidate bridge, but it is not a current executable fallback. E1 still does not implement polling, daemonization, service supervision, TTS/audio/avatar, ASR, peer transport, or RelaySOUL mutation authority.

Wave 7 convergence is recorded in [Wave 7 Cross-Slice Convergence Audit](../evidence/waves/wave7_cross_slice_convergence_audit.md). E1-R5 was merged after W7-INT and is now reflected here as a post-Wave-7 correction to the E1 proof boundary.

## Current E1 proof boundary

The currently proven local E1 lane is:

```text
SOUL Lab Home-origin ordinary conversation or explicit trusted request
  -> route-owned trusted Home admission when E1-R1 is enabled
  -> durable source and queue evidence
  -> speaker-provenance-safe Primary MEM formation summary
  -> local operation drain
  -> Primary MEM durable formation
  -> current ordinary retrieval authority selection
  -> `subjective_only` finalized Subjective retrieval, or fail-closed `neither` for `primary_only`
  -> request-side grounded context and unsupported-detail suppression for already-selected evidence
  -> Lab observation and lifecycle/governance visibility
```

E1-R1 route-owned trusted Home admission is implemented. Browser-owned trusted metadata remains rejected. E1-R2 character-store bootstrap is implemented as an explicit operator command, not automatic semantic memory creation. E1-R3 provenance-preserving Primary MEM formation summary is implemented so user assertion evidence remains distinguishable from assistant acknowledgement/speculation and route-owned scene/trust qualification. E1-R4 retrieval-response grounding and unsupported-detail suppression remains valid for already-selected current ordinary-memory evidence. E1-R5 is retained only as historical completion and convergence evidence.

Current runtime proof is post-retirement: `primary_only` fails closed to `neither`; ordinary retrieval resolves no Primary root, opens no Primary store, discovers and selects no Primary candidate, performs no Primary recall or E1-R5 fallback, and releases no Primary evidence. Finalized Subjective ordinary retrieval supplies current evidence only when reader authority selects `subjective_only`.

## Evidence inventory

| Evidence step | Implemented evidence | Primary proof artifacts | Current interpretation |
|---|---|---|---|
| Real Home conversation | Implemented | `docs/contracts/ui/home-conversation.md`, `docs/evidence/evaluations/e1_local_runtime_evaluation_2026_06_25.md` | SOUL Lab Home can use the existing same-origin Chat Completions path for real text conversation. |
| Trusted Home admission | Implemented by E1-R1 | `docs/architecture/e1r1_trusted_home_scene_admission.md`, `docs/evidence/implementation/e1r1_completion_report.md` | Home-origin persistence may be admitted only by route-owned server configuration. Browser-owned trust is rejected. |
| Character-store bootstrap | Implemented by E1-R2 | `docs/architecture/e1r2_character_store_bootstrap.md`, `docs/evidence/implementation/e1r2_completion_report.md` | Local evaluation can prepare the minimum safe Primary store layout through an explicit dry-run-first operator command. |
| Provenance-preserving formation | Implemented by E1-R3 | `docs/architecture/e1r3_provenance_preserving_primary_mem_formation_summary.md`, `docs/evidence/implementation/e1r3_completion_report.md`, `docs/evidence/waves/wave7_cross_slice_convergence_audit.md`, `scripts/relaylm_e1r3_provenance_formation_summary_smoke.py`, `scripts/relaylm_e1r3_provenance_formation_security_smoke.py` | Primary MEM formation uses a user-only memory candidate payload and keeps assistant and scene/trust evidence separate. |
| Retrieval-response grounding | Implemented by the Grounded Recall contract | `docs/contracts/grounded-recall.md`, `docs/evidence/implementation/e1r4_completion_report.md`, `docs/evidence/waves/wave7_cross_slice_convergence_audit.md`, `scripts/relaylm_e1r4_grounded_recall_response_smoke.py`, `scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py`, `scripts/relaylm_e1r4_grounded_recall_security_smoke.py` | Later recall requests receive backend-bound grounded recall evidence and unsupported-detail suppression while public diagnostics remain content-free. |
| Post-retirement ordinary-memory boundary | E1-R5 historical completion plus current RT-1D-R5 regression | `docs/evidence/implementation/e1r5_completion_report.md`, `docs/evidence/waves/e1r5_post_wave7_correction_convergence_audit.md`, `scripts/relaylm_primary_recall_post_retirement_structure_smoke.py`, `scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py` | E1-R5 was implemented historically and PR #491 historically folded the bridge into Primary recall. Its ordinary-serving role is retired: `primary_only` fails closed to `neither`; current evidence comes from finalized Subjective retrieval under `subjective_only`, while E1-R4 remains shared grounding policy. |
| Durable source and queue evidence | Implemented | `docs/contracts/governed-source-capture-admission.md`, `docs/contracts/slp/durable-queue.md`, `docs/contracts/slp/durable-finalization.md` | Durable protected-source, queue, and durable-finalization evidence exist through completed authorities. |
| Local operation drain | Implemented as explicit bounded invocation | `docs/architecture/o0_local_one_job_runner.md`, `docs/architecture/o1f_operational_validation.md` | Operator-invoked local drain and caller-invoked O1 controls remain bounded and non-supervised. |
| Primary MEM durable formation | Implemented | `docs/architecture/memory/formation.md`, `docs/contracts/slp/primary-worker.md` | M3a-M3h durable formation and worker fault convergence are covered by existing production smokes. |
| Current ordinary-memory retrieval | Implemented for finalized Subjective memory | `scripts/relaylm_primary_recall_post_retirement_structure_smoke.py`, `docs/contracts/grounded-recall.md` | `subjective_only` may provide finalized Subjective ordinary-memory evidence; `primary_only` fails closed to `neither` and releases no Primary evidence. Grounded Recall grounds already-selected evidence. |
| User governance | Implemented through Correct, Forget, Pin, and Held Governance | `docs/evidence/implementation/phase-i3-auditable-primary-mem-correct-handoff.md`, `docs/architecture/phase_i4_primary_mem_forget_hide_contract.md`, `docs/contracts/ui/memory-pin-unpin-management.md`, `docs/contracts/memory/held-governance.md` | Explicit governance surfaces are available without giving the browser queue, worker, scheduler, store-root, or route authority. |

## Implemented evidence vs remaining quality work

Implemented evidence:

- UI-B0 real Home conversation is complete.
- UI-B1A lifecycle and operation visibility is complete and read-only.
- I1-GA through I1-GE are complete.
- O0 and O1A through O1F are complete at their bounded caller-invoked or validation-only boundaries.
- I-4B through I-4F are complete.
- I-5A/I-5B and I-7A/B/I-7C are complete at their documented boundaries.
- E1-R1 route-owned trusted Home admission is complete.
- E1-R2 dry-run-first character-store bootstrap is complete.
- E1-R3 provenance-preserving Primary MEM formation summary is complete.
- E1-R4 retrieval-response grounding and unsupported-detail suppression is complete.
- E1-R5 Primary MEM recall candidate discovery bridge is historically complete; its ordinary-serving role is retired by RT-1D-R5.

Remaining quality work:

- O2/O3 remain conditional on explicit MVP need and are not implied by E1-R1/R2/R3/R4/R5.

## Direct Home-origin admission decision record

| Option | Description | Benefits | Risks | Current decision |
|---|---|---|---|---|
| Option A | MVP formation remains operator/trusted-admission-path driven while Home is used for conversation, recall, observation, and governance. | Preserves the original trust boundary. | Less seamless than direct Home formation. | Historical Wave 5 decision; replaced by bounded E1-R1 when explicitly enabled. |
| Option B | Add a trusted scene-admission path to Home-origin requests. The trusted admission signal must be server-owned, route-owned, or otherwise authenticated and bounded. | Makes the direct Home product loop seamless for formation and later recall. | High risk if implemented as frontend-owned hidden metadata. | Implemented by E1-R1 through route-owned trusted Home scene admission. |

E1-R1 implements Option B only as a route-owned gate. It must not be interpreted as broad browser-owned trusted metadata, a new queue format, or an automatic scheduler/service.

## Character-store bootstrap ergonomics

E1-R2 idempotent character-store bootstrap command is implemented as:

```text
operator invocation
  -> config/root/character/scope validation
  -> dry-run bootstrap plan
  -> optional apply
  -> idempotent store layout preparation
  -> content-free projection
  -> return
```

E1-R2 does not enqueue jobs, start workers, run schedulers, create semantic Primary MEM pages, or repair malformed state silently.

## Speaker-provenance-safe memory summary formation

E1-R3 provenance-preserving Primary MEM formation summary is implemented as:

```text
exact finalized-turn source
  -> governed messages with explicit roles
  -> user_assertion_evidence
  -> assistant_acknowledgement_evidence
  -> assistant_speculation_or_non_factual_evidence
  -> scene_qualification_evidence
  -> trust_admission_evidence
  -> user-only memory_candidate_payload
```

The E1-R3 runtime helper preserves:

- speaker provenance;
- scene qualification;
- user/character boundary;
- no hallucinated memory source;
- no mixing of backend acknowledgement or decoration with user claims;
- no promotion of assistant speculation into user fact evidence.

Browser-owned trust remains rejected. Missing or unknown message roles fail closed.

## Evidence-grounded recall behavior

E1-R4 remains the shared grounding policy for already-selected current ordinary-memory evidence. Hidden, prior, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, unresolved, and prior physical revisions remain excluded before backend-bound context construction.

Current post-retirement boundary:

```text
reader authority `subjective_only`
  -> finalized Subjective ordinary retrieval
  -> E1-R4 grounded context and unsupported-detail suppression

reader authority `primary_only`
  -> fail closed to `neither`
  -> no Primary root resolution, store open, candidate discovery, selection, recall, fallback, or evidence release
```

E1-R5 and its PR #491 bridge fold-in remain historical implementation/convergence facts. They are not current executable evidence and cannot restore an ordinary Primary reader or fallback. Current regression is anchored by `scripts/relaylm_primary_recall_post_retirement_structure_smoke.py` and the content-free retained audit boundary by `scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py`.

## Evaluation smoke boundary

`scripts/relaylm_e1_evaluation_consolidation_smoke.py` validates the post-E1-R1/R2/R3/R4/R5 evidence inventory. It does not require a live LLM, LM Studio, browser, network service, or workstation-local path.

Required validation set:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_e1r3_provenance_formation_summary_smoke.py
python scripts/relaylm_e1r3_provenance_formation_security_smoke.py
python scripts/relaylm_e1r4_grounded_recall_response_smoke.py
python scripts/relaylm_e1r4_unsupported_detail_suppression_smoke.py
python scripts/relaylm_e1r4_grounded_recall_security_smoke.py
python scripts/relaylm_primary_recall_post_retirement_structure_smoke.py
python scripts/relaylm_e1r5_primary_mem_recall_audit_projection_smoke.py
python scripts/relaylm_phase_i1_two_turn_primary_recall_smoke.py
python scripts/relaylm_phase_i1_two_turn_primary_recall_security_smoke.py
python scripts/relaylm_phase_i4d_primary_retrieval_exclusion_smoke.py
python scripts/relaylm_e1_evaluation_consolidation_smoke.py
python scripts/relaylm_docs_link_check.py
python scripts/relaylm_documentation_current_boundary_smoke.py
python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```
