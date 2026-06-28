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
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact RelayMEM or RelaySLP schemas
  - production admission trust policy
  - future speaker-provenance implementation details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - e1_local_runtime_evaluation_2026_06_25.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - project_execution_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_b0_real_home_conversation.md
  - soul_lab_ui_b1a_lifecycle_visibility.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i4e_forget_api_ui.md
  - phase_i4f_forget_validation.md
  - o1f_operational_validation.md
---
# E1 MVP Evaluation Evidence Consolidation

Last reviewed: 2026-06-28 JST.

## Purpose

This document consolidates the MVP E1 evaluation evidence after Wave 6 convergence. It records that E1-R1 and E1-R2 are now implemented while preserving the remaining quality gates for provenance and grounded recall.

E1 is evidence-first. E1-R1 adds route-owned trusted Home admission. E1-R2 adds explicit dry-run-first store bootstrap. E1 still does not implement speaker-provenance-safe summarization, evidence-grounded response behavior, polling, daemonization, service supervision, TTS/audio/avatar, ASR, peer transport, or RelaySOUL mutation authority.

## Current E1 proof boundary

The currently proven local E1 lane is:

```text
SOUL Lab Home-origin ordinary conversation or explicit trusted request
  -> route-owned trusted Home admission when E1-R1 is enabled
  -> durable source and queue evidence
  -> local operation drain
  -> Primary MEM durable formation
  -> later SOUL Lab Home recall
  -> Lab observation and lifecycle/governance visibility
```

E1-R1 route-owned trusted Home admission is implemented. Browser-owned trusted metadata remains rejected. E1-R2 character-store bootstrap is implemented as an explicit operator command, not automatic semantic memory creation.

Trusted Home admission is implemented, but formation quality risks are not solved. Recall evidence is present, but evidence-grounded response behavior is not fully evaluated.

## Evidence inventory

| Evidence step | Implemented evidence | Primary proof artifacts | Current interpretation |
|---|---|---|---|
| Real Home conversation | Implemented | `docs/architecture/soul_lab_ui_b0_real_home_conversation.md`, `docs/architecture/e1_local_runtime_evaluation_2026_06_25.md` | SOUL Lab Home can use the existing same-origin Chat Completions path for real text conversation. |
| Trusted Home admission | Implemented by E1-R1 | `docs/architecture/e1r1_trusted_home_scene_admission.md`, `docs/mvp/wave6/e1r1_completion_report.md` | Home-origin persistence may be admitted only by route-owned server configuration. Browser-owned trust is rejected. |
| Character-store bootstrap | Implemented by E1-R2 | `docs/architecture/e1r2_character_store_bootstrap.md`, `docs/mvp/wave6/e1r2_completion_report.md` | Local evaluation can prepare the minimum safe Primary store layout through an explicit dry-run-first operator command. |
| Durable source and queue evidence | Implemented | `docs/architecture/phase6c1_durable_protected_source_persistence.md`, `docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md`, `docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md` | Durable protected-source, queue, and durable-finalization evidence exist through completed authorities. |
| Local operation drain | Implemented as explicit bounded invocation | `docs/architecture/o0_local_one_job_runner.md`, `docs/architecture/o1f_operational_validation.md` | Operator-invoked local drain and caller-invoked O1 controls remain bounded and non-supervised. |
| Primary MEM durable formation | Implemented | `docs/architecture/phase6c1_primary_mem_worker_contract.md`, `docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md` | M3a-M3h durable formation and worker fault convergence are covered by existing production smokes. |
| Later Home recall | Implemented for eligible current Primary MEM | `docs/architecture/integration_i1_primary_mem_two_turn_recall.md`, `docs/architecture/phase_i4d_primary_retrieval_exclusion.md` | Later SOUL Lab Home requests can retrieve current eligible Primary MEM through M2 and RelayCTX. |
| User governance | Implemented through Correct, Forget, Pin, and Held Governance | `docs/architecture/phase_i3_auditable_primary_mem_correct.md`, `docs/architecture/phase_i4f_forget_validation.md`, `docs/architecture/phase_i5b_pin_unpin_apply.md`, `docs/architecture/phase_i7c_held_apply_discard_runtime.md` | Explicit governance surfaces are available without giving the browser queue, worker, scheduler, store-root, or route authority. |

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

Remaining quality work:

- E1-R3 provenance-preserving Primary MEM formation summary.
- E1-R4 retrieval-response grounding and unsupported-detail suppression.
- O2/O3 remain conditional on explicit MVP need and are not implied by E1-R1/R2.

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

Primary MEM formation quality must preserve:

- speaker provenance;
- scene qualification;
- user/character boundary;
- no hallucinated memory source;
- no mixing of backend acknowledgement or decoration with user claims;
- no promotion of assistant speculation into user fact evidence.

Remaining quality work:

```text
E1-R3 provenance-preserving Primary MEM formation summary
  -> user assertion evidence remains distinguishable
  -> assistant acknowledgement is separate or excluded from factual evidence
  -> assistant speculation is never promoted as user fact
```

## Evidence-grounded recall behavior

Later recall must be grounded in eligible current Primary MEM evidence. Hidden, prior, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, unresolved, and prior physical revisions must be excluded before backend-bound context construction.

Currently proven:

- current eligible Primary MEM can be selected by M2 and injected through RelayCTX;
- I-4D ordinary retrieval exclusion protects the lifecycle boundary;
- SOUL Lab can display used-memory/lifecycle evidence without mutation authority.

Remaining quality work:

```text
E1-R4 retrieval-response grounding and unsupported-detail suppression
  -> distinguish retrieved fact from inference
  -> avoid presenting unsupported details as remembered history
  -> keep retrieval evidence bounded and content-private in public projections
```

## Evaluation smoke boundary

`scripts/relaylm_e1_evaluation_consolidation_smoke.py` validates the post-E1-R1/R2 evidence inventory and remaining E1-R3/R4 quality gates. It does not require a live LLM, LM Studio, browser, network service, or workstation-local path.

Required validation set:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_e1_evaluation_consolidation_smoke.py
python scripts/relaylm_docs_link_check.py
python scripts/relaylm_documentation_current_boundary_smoke.py
python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```
