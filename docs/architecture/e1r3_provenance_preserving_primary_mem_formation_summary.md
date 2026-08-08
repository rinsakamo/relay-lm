---
relaylm_doc_type: implementation_handoff
relaylm_authority: e1r3_provenance_preserving_primary_mem_formation_summary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: evaluation
relaylm_update_trigger:
  - Primary MEM formation summary semantics change
  - finalized-turn source evidence schema changes
  - public diagnostics expose new evidence counts
  - RT-1 Primary writer decision carriage changes
  - RT-1D-R5 or R6 retires the Primary formation path
relaylm_not_authoritative_for:
  - E1-R4 retrieval-response grounding
  - queue lifecycle authority
  - worker execution or Primary writer authorization
  - RT-1 cutover state or retirement approval
  - browser-owned trusted admission
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - e1_evaluation_consolidation.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - e1r4_retrieval_response_grounding.md
  - relaymem_slp_current_target.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - ../evidence/waves/wave7_cross_slice_convergence_audit.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_durable_protected_source_persistence.md
---
# E1-R3 Provenance-Preserving Primary MEM Formation Summary

Last reviewed: 2026-08-08 JST.

## Purpose

E1-R3 makes the retained Primary MEM formation-summary boundary speaker-provenance-safe. The worker/source-side formation helper partitions finalized-turn evidence before a governed Primary candidate summary is built, so assistant acknowledgement, assistant speculation, backend decoration, scene qualification, and trust-admission evidence are not collapsed into user factual memory evidence.

E1-R3 is an implementation/evaluation handoff, not current Primary writer authority. Its output can remain useful as protected formation evidence and regression history, but durable Primary mutation is independently governed by the exact RT-1 Primary writer decision.

## Implemented boundary

```text
exact finalized-turn source
  -> ordered governed messages with explicit role
  -> route-owned scene/trust qualification
  -> speaker-provenance formation summary
  -> user-only memory_candidate_payload
  -> existing governed experience summary
  -> exact RT-1 Primary writer decision
       -> permitted: retained C1-5 / B2 / B3 / C2 / M3a-M3h compatibility path
       -> rejected: no Primary worker/pipeline mutation authority
```

The helper remains `relaylm.relaymem_provenance_formation_summary.build_relaymem_primary_formation_summary`.

It emits a runtime-private `relaymem.primary_formation_provenance_summary.v0` artifact with these explicit partitions:

```text
user_assertion_evidence
assistant_acknowledgement_evidence
assistant_speculation_or_non_factual_evidence
scene_qualification_evidence
trust_admission_evidence
excluded_evidence
```

Only `user_assertion_evidence` contributes to `memory_candidate_payload.summary_text` and `memory_candidate_payload.title`.

## RT-1 Primary writer boundary

RT-1D-R4 adds an immutable `SubjectiveMemRetrievalPrimaryWriterDecision` to the retained Primary formation path. The decision class is content-free and exact: Primary writes are `permitted` only strictly before durable `primary_writer_fenced`; at and after that fence they are `rejected`.

E1-R3 does not mint, reconstruct, infer, cache, or override that decision. In particular, successful formation-summary construction, a valid protected source, an existing queued job, an active lease, an old Primary page, or historical E1 completion evidence is never permission to write.

The downstream carriage is intentionally defensive:

```text
one queued-job runner
  -> requires exact writer decision and rejects non-permitted decisions before claim/execution
  -> C1 worker request carries the same decision
       -> worker rejects non-permitted decisions before source/pipeline execution
       -> M3 pipeline request carries the same decision
            -> pipeline rejects non-permitted decisions before protected-source consumption
```

The bounded rejected reason is `primary_writer_decision_rejected`. Existing queue/lease and M3 validation remain additional fences; they are not substitutes for writer authorization.

This document does not claim RT-1D-R5 retirement is complete. R5/R6 own the final removal or retained read-only disposition of Primary formation/worker surfaces after exact dependency characterization.

## Compatibility preservation

E1-R3 does not change the exact C1-5 protected-source payload, B2 queue record, B3 lifecycle, C2 worker adapter, M3a-M3h writer semantics, M2 retrieval compatibility behavior, I-4 lifecycle exclusion, I-5 Pin, or I-7 Held Governance authorities.

The compatibility interpretation is narrower than the historical implementation graph: those Primary worker/writer capabilities may execute only when the exact RT-1 writer decision permits them. E1-R3 completion does not preserve independent Primary mutation authority after `primary_writer_fenced`.

The runtime-private formation summary is attached to the finalized-turn source object and projected only as content-free counts and status flags. It is not added to the 16-field protected source payload consumed by C1-0/C1-2.

## Formation semantics

```text
role=user
  -> factual source candidate
  -> may contribute to memory_candidate_payload
  -> retained as speaker=user evidence

role=assistant
  -> acknowledgement / answer / speculation / decoration
  -> never promoted as user fact
  -> retained as acknowledgement or non-factual context evidence

scene/trust
  -> route-owned qualification only
  -> never copied into user memory body

missing / unknown role
  -> fail closed with source_role_missing or blocked_ambiguous_provenance

browser-owned trust
  -> rejected with blocked_browser_owned_trust
```

These provenance rules classify candidate content only. They do not authorize persistence, ordinary serving, or a reader/writer transition.

## Bounded statuses

The E1-R3 helper recognizes the bounded status vocabulary required by the slice:

```text
disabled
dry_run_ready
ready
formed
blocked_no_user_assertion
blocked_ambiguous_provenance
blocked_browser_owned_trust
blocked_untrusted_scene
blocked_source_invalid
source_role_missing
source_digest_mismatch
worker_input_invalid
pipeline_blocked
pipeline_failed
content_leakage_guard_failed
```

Downstream RT-1 writer rejection is owned by the runner/worker/pipeline boundaries and is not a new E1-R3 formation-summary status.

## Public diagnostics

Public projections remain content-free. They may expose counts and booleans such as:

```text
formation_user_assertion_evidence_count
formation_assistant_acknowledgement_evidence_count
formation_assistant_non_factual_evidence_count
assistant_text_promoted_to_user_fact = false
scene_text_promoted_to_user_fact = false
```

They must not expose raw user text, assistant text, protected source body, queue payload, store root, source path, claim token, lease owner, token digest, source digest, cutover binding, or private writer-decision identity.

## Current interpretation after RT-1D-R4

E1-R3 remains implemented and its provenance partition is still the accepted Primary-formation compatibility behavior. That statement is historical/capability evidence, not a claim that Primary formation is always authorized.

```text
writer decision = permitted
  -> E1-R3 output may continue through the retained governed Primary path

writer decision = rejected
  -> E1-R3 evidence cannot authorize Primary queue/worker/pipeline mutation
  -> no compatibility fallback re-enables the old writer
```

Ordinary reader authority is separately decided by RT-1. Formation-summary evidence does not select `primary_only`, restore Primary after `subjective_only`, or create dual serving.

## Non-goals

E1-R3 does not implement E1-R4 retrieval-response grounding, unsupported-detail suppression, RT-1 reader selection, RT-1 writer authorization, RT-1D-R5/R6 retirement, O2/O3, polling, service supervision, browser-owned trusted admission, automatic bootstrap, Pin/Unpin runtime changes, Held Apply/Discard runtime changes, Forget/Correct behavior changes, Secondary MEM consolidation, RelaySOUL mutation, TTS/audio/avatar/ASR, or public display of protected content.

## Validation

Required slice validation:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_e1r3_provenance_formation_summary_smoke.py
PYTHONPATH=. python scripts/relaylm_e1r3_provenance_formation_security_smoke.py
PYTHONPATH=. python scripts/relaylm_e1_evaluation_consolidation_smoke.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_mvp_completion_report_pr_link_smoke.py
```

The repository workflow/test registry remains the command authority; this list records the E1-R3 regression anchors and does not override current CI registration.

## Downstream E1-R4 boundary

E1-R3 protects formation evidence. E1-R4 remains the separate request-side one-authority retrieval-response grounding and unsupported-detail-suppression boundary: later responses must distinguish retrieved memory from inference and avoid presenting unsupported details as remembered history. E1-R4 does not turn E1-R3 formation evidence into current writer authorization or reader authority.
