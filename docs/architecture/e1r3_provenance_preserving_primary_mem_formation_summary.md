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
relaylm_not_authoritative_for:
  - E1-R4 retrieval-response grounding
  - queue lifecycle authority
  - worker execution authority
  - browser-owned trusted admission
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - e1_evaluation_consolidation.md
  - e1r1_trusted_home_scene_admission.md
  - e1r2_character_store_bootstrap.md
  - e1r4_retrieval_response_grounding.md
  - wave7_cross_slice_convergence_audit.md
  - phase6_i1b_runtime_enqueue_source_capture_handoff.md
  - phase6c1_primary_mem_worker_contract.md
  - phase6c1_one_claimed_primary_worker_handoff.md
  - phase6c1_relaymem_primary_pipeline_compose.md
  - phase6c1_durable_protected_source_persistence.md
---
# E1-R3 Provenance-Preserving Primary MEM Formation Summary

Last reviewed: 2026-06-28 JST.

## Purpose

E1-R3 makes Primary MEM formation summary construction speaker-provenance-safe. The worker-internal formation helper partitions finalized-turn evidence before the governed Primary MEM summary is built, so assistant acknowledgement, assistant speculation, backend decoration, scene qualification, and trust admission evidence are not collapsed into user factual memory evidence.

## Implemented boundary

```text
exact finalized-turn source
  -> ordered governed messages with explicit role
  -> route-owned scene/trust qualification
  -> speaker-provenance formation summary
  -> user-only memory_candidate_payload
  -> existing governed experience summary
  -> existing C1-5 / B2 / B3 / C2 / M3a-M3h path
```

The new helper is `relaylm.relaymem_provenance_formation_summary.build_relaymem_primary_formation_summary`.

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

## Compatibility preservation

E1-R3 does not change the exact C1-5 protected-source payload, B2 queue record, B3 lifecycle, C2 worker adapter, M3a-M3h writer, M2 retrieval, I-4 lifecycle exclusion, I-5 Pin, or I-7 Held Governance authorities.

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

## Public diagnostics

Public projections remain content-free. They may expose counts and booleans such as:

```text
formation_user_assertion_evidence_count
formation_assistant_acknowledgement_evidence_count
formation_assistant_non_factual_evidence_count
assistant_text_promoted_to_user_fact = false
scene_text_promoted_to_user_fact = false
```

They must not expose raw user text, assistant text, protected source body, queue payload, store root, source path, claim token, lease owner, token digest, or source digest.

## Non-goals

E1-R3 does not implement E1-R4 retrieval-response grounding, unsupported-detail suppression, O2/O3, polling, service supervision, browser-owned trusted admission, automatic bootstrap, Pin/Unpin runtime changes, Held Apply/Discard runtime changes, Forget/Correct behavior changes, Secondary MEM consolidation, RelaySOUL mutation, TTS/audio/avatar/ASR, or public display of protected content.

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

## Downstream E1-R4 boundary

E1-R3 protects formation evidence. E1-R4 is now implemented as the separate request-side retrieval-response grounding and unsupported-detail suppression boundary: later responses must distinguish retrieved memory from inference and avoid presenting unsupported details as remembered history.
