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
  - project_execution_plan.md
  - relaymem_slp_current_target.md
  - soul_lab_ui_b0_real_home_conversation.md
  - soul_lab_ui_b1a_lifecycle_visibility.md
  - integration_i1_primary_mem_two_turn_recall.md
  - phase_i2_real_soul_lab_observation.md
  - phase_i4d_primary_retrieval_exclusion.md
  - phase_i4e_forget_api_ui.md
  - phase_i4f_forget_validation.md
  - o1e_scheduler_operational_controls.md
  - o1f_operational_validation.md
  - i1g_pre_enqueue_durable_finalization_contract.md
  - i1ge_durable_finalization_crash_validation.md
---
# E1 MVP Evaluation Evidence Consolidation

Last reviewed: 2026-06-27 JST.

## Purpose

This document consolidates the MVP E1 evaluation evidence after Wave 4 and the later O1F horizontal status sweep. It makes the direct Home-origin Primary MEM formation decision explicit and records the remaining quality and ergonomics work needed before a trustworthy local MVP evaluation.

E1 is evidence-first. It does not implement trusted scene admission, speaker-provenance summarization, evidence-grounded generation, bootstrap automation, polling, daemonization, service supervision, TTS/audio/avatar, ASR, peer transport, or any memory mutation authority.

## Current E1 proof boundary

The currently proven local E1 lane is:

```text
explicit scene-qualified trusted request
  -> durable source and queue evidence
  -> local operation drain
  -> Primary MEM durable formation
  -> later SOUL Lab Home recall
  -> Lab observation and lifecycle visibility
```

The currently unproven product lane is:

```text
SOUL Lab Home-origin ordinary conversation
  -> trusted scene admission
  -> Primary MEM formation
```

Home conversation is real, but Home-origin trusted memory formation is not proven. Trusted formation lane is proven, but all formation quality risks are not solved. Recall evidence is present, but evidence-grounded response behavior is not fully evaluated.

## Evidence inventory

| Evidence step | Implemented evidence | Primary proof artifacts | Current interpretation |
|---|---|---|---|
| Real Home conversation | Implemented | `docs/architecture/soul_lab_ui_b0_real_home_conversation.md`, `docs/architecture/e1_local_runtime_evaluation_2026_06_25.md` | SOUL Lab Home can use the existing same-origin Chat Completions path for real text conversation. |
| Trusted formation lane | Implemented through a separate admission path | `docs/architecture/e1_local_runtime_evaluation_2026_06_25.md`, `docs/architecture/phase6_i1b_runtime_enqueue_source_capture_handoff.md` | Explicit scene-qualified managed requests can enter the existing formation pipeline. |
| Durable source and queue evidence | Implemented | `docs/architecture/phase6c1_durable_protected_source_persistence.md`, `docs/architecture/phase6b2_relayslp_atomic_durable_enqueue.md`, `docs/architecture/i1g_pre_enqueue_durable_finalization_contract.md`, `docs/architecture/i1ge_durable_finalization_crash_validation.md` | Durable protected-source, queue, and durable-finalization evidence exist through the completed authorities. |
| Local operation drain | Implemented as explicit bounded invocation | `docs/architecture/o0_local_one_job_runner.md`, `docs/architecture/phase6c2_one_queued_primary_worker_integration.md`, `scripts/relaylm_o0_local_one_job_runner_ci_runner.py`, `scripts/relaylm_phase6c2_one_queued_job_runner_ci_runner.py` | Operator-invoked local drain can process at most one eligible job. O1E/O1F add caller-invoked controls and validation but still no polling or service supervision. |
| Primary MEM durable formation | Implemented | `docs/architecture/phase6c1_primary_mem_worker_contract.md`, `docs/architecture/phase6c1_one_claimed_primary_worker_handoff.md`, `docs/architecture/phase6c1_relaymem_primary_pipeline_compose.md`, `scripts/relaylm_phase6c1_primary_worker_smoke.py`, `scripts/relaylm_phase6c1_worker_crash_convergence_smoke.py` | M3a-M3h durable formation, index/log convergence, and worker fault convergence are covered by existing production smokes. |
| Later Home recall | Implemented for eligible current Primary MEM | `docs/architecture/integration_i1_primary_mem_two_turn_recall.md`, `docs/architecture/e1_local_runtime_evaluation_2026_06_25.md`, `docs/architecture/phase_i4d_primary_retrieval_exclusion.md` | Later SOUL Lab Home requests can retrieve current eligible Primary MEM through M2 and RelayCTX. |
| Lab observation | Implemented read-only | `docs/architecture/phase_i2_real_soul_lab_observation.md`, `docs/architecture/soul_lab_ui_b1a_lifecycle_visibility.md` | SOUL Lab can observe formed memory, latest run evidence, lifecycle state, and operation status without gaining mutation authority. |
| Lifecycle exclusion and Forget governance | Implemented | `docs/architecture/phase_i4d_primary_retrieval_exclusion.md`, `docs/architecture/phase_i4e_forget_api_ui.md`, `docs/architecture/phase_i4f_forget_validation.md` | Hidden, prior, prepared, recovery-required, corrupt, ambiguous, unsafe, cross-scope, unresolved, and prior physical revisions are excluded from ordinary M2/RelayCTX; Forget API/UI and validation are complete. |

## Implemented evidence vs assumptions

Implemented evidence:

- UI-B0 real Home conversation is complete.
- UI-B1A lifecycle and operation visibility is complete and read-only.
- I1-GA through I1-GE are complete.
- O0 and O1A through O1F are complete at their bounded caller-invoked or validation-only boundaries.
- I-4B through I-4F are complete.
- I-5A and I-7A/B are complete only for contract and read-only preflight.
- The local E1 proof demonstrates explicit scene-qualified trusted request -> O0 terminal success -> Primary MEM -> later Home recall.

Assumptions and future work:

- Direct Home-origin Primary MEM formation remains unproven.
- Home requests do not currently carry a server-owned trusted scene-admission projection.
- Character-store bootstrap remains operator-facing and brittle for local evaluation.
- Speaker-provenance-safe Primary MEM summary formation remains quality work.
- Strict evidence-grounded response behavior remains quality work.
- O2/O3, Pin runtime behavior, Held runtime behavior, Merge/Supersession, Secondary MEM, and RelaySOUL proposal/intervention/rollback remain outside this E1 consolidation.

## Direct Home-origin formation decision record

| Option | Description | Benefits | Risks | MVP decision |
|---|---|---|---|---|
| Option A | MVP formation remains operator/trusted-admission-path driven. Home is used for real conversation, recall, observation, Correct/Forget governance, lifecycle visibility, and evaluation of formed memories. | Preserves the trust boundary already proven by the repository. Avoids browser self-asserted persistence policy. Keeps MVP evaluation possible without silently weakening scene admission. | Local MVP is less seamless: an operator must still use a trusted formation lane for new memory evidence. | Recommended for the current MVP boundary. |
| Option B | Add a future trusted scene-admission path to Home-origin requests. The trusted admission signal must be server-owned, route-owned, or otherwise authenticated and bounded. | Makes the direct Home product loop seamless for formation and later recall. | High risk if implemented as frontend-owned hidden metadata or broad runtime behavior. Requires a dedicated trust-boundary design and validation. | Deferred. |

E1 records Option A as the recommended current MVP decision. Option B is deferred to a future bounded follow-up named **E1-R1 trusted Home scene-admission path**. That follow-up must not allow the browser to self-assert arbitrary trusted scene policy and must not add hidden runtime signals without a documented trust boundary.

## Character-store bootstrap ergonomics

Current local evaluation assumes the character-scoped Primary store has already been initialized with the expected directory and control-file shape. The existing runtime intentionally does not auto-create this authority during worker execution.

Current operator-facing risks:

- bootstrap is manual;
- missing store structure can block a job before useful memory evidence is formed;
- retry behavior can be confusing if the failed job remains outside the next O0 selection boundary;
- local evaluation instructions are scattered across historical evidence and architecture docs.

Smallest future improvement:

```text
E1-R2 idempotent character-store bootstrap command
  -> explicit operator invocation
  -> default-off / dry-run-first
  -> content-free projection
  -> no queue, worker, scheduler, or memory-mutation authority transfer
```

This improvement should make local evaluation repeatable without hiding the authority boundary between operator bootstrap, RelayMEM store layout, queue processing, and Home UI.

## Speaker-provenance-safe memory summary formation

Primary MEM formation quality must preserve:

- speaker provenance;
- scene qualification;
- user/character boundary;
- no hallucinated memory source;
- no mixing of backend acknowledgement or decoration with user claims;
- no promotion of assistant speculation into user fact evidence.

Currently proven:

- the production pipeline can durably form a Primary MEM from trusted evidence;
- the local E1 record identified a provenance defect where assistant-authored text can be stored with user evidence.

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

E1 adds `scripts/relaylm_e1_evaluation_consolidation_smoke.py` and `.github/workflows/e1-evaluation-consolidation.yml`.

The smoke is docs-only. It validates required E1 anchors, verifies linked evidence documents and scripts exist, confirms the decision record remains explicit, and forbids leakage-oriented example labels. It does not require a live LLM, LM Studio, browser, network service, or workstation-local path.

Required validation set:

```bash
python -m compileall relaylm scripts
python scripts/relaylm_e1_evaluation_consolidation_smoke.py
python scripts/relaylm_docs_link_check.py
python scripts/relaylm_documentation_current_boundary_smoke.py
python scripts/relaylm_mvp_completion_report_smoke.py docs/mvp/wave5/e1_completion_report.md
python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```

## Frozen E1 follow-up names

```text
E1-R1 trusted Home scene-admission path
E1-R2 idempotent character-store bootstrap command
E1-R3 provenance-preserving Primary MEM formation summary
E1-R4 retrieval-response grounding and unsupported-detail suppression
```

These follow-ups are independent from O1E/O1F and O2/O3. Operational automation can process more eligible work, but it does not by itself make Home-origin requests trusted for formation, create missing character stores safely, repair speaker-provenance defects, or force evidence-grounded generation.
