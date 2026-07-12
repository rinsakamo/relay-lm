---
relaylm_doc_type: documentation_index
relaylm_authority: implementation_evidence_collection_router
relaylm_status: current
relaylm_volatility: low
relaylm_owner: documentation
relaylm_update_trigger:
  - an implementation evidence record is added, moved, or retired
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact contracts
  - implementation sequencing
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_decision_source: ../../adr/0002-documentation-information-architecture.md
---
# Implementation Evidence

This collection preserves bounded implementation and smoke evidence after its active design or operational authority has moved elsewhere. Commands and expectations inside exact source snapshots describe their historical boundary and are not automatically current instructions.

## Early MVP smoke records

- [MVP-1 API diagnostics smoke](mvp1_api_diagnostics_smoke.md)
- [MVP-1 config and routing smoke](mvp1_config_routing_smoke.md)
- [MVP-2 memory-light API smoke](mvp2_memory_light_api_smoke.md)
- [MVP-2 profile compile dry-run](mvp2_profile_compile_dry_run.md)
- [MVP-2 compiled system message](mvp2_compiled_system_message.md)
- [MVP-2 config profile resolution](mvp2_config_profile_resolution.md)
- [MVP-2 dry-run diagnostics headers](mvp2_dry_run_diagnostics_headers.md)
- [MVP eval runner completion report](mvp_eval_runner_completion_report.md) — frozen implementation evidence from PR #451; current runner behavior remains code-owned.
- [O2/O3 and PM-D5-D7 docs convergence completion report](o2_o3_pm_d5_d7_docs_convergence_completion_report.md) — frozen documentation-convergence evidence from PR #490; current status remains Project Status-owned.
- [E2 Value Smoke Harness completion report](e2_value_smoke_harness_completion_report.md) — frozen harness implementation evidence from PR #481; later human judgment remains release-readiness-owned.
- [Twin Extraction Tooling completion report](twin_extraction_completion_report.md) — frozen offline-tooling implementation evidence from PR #503; current operation remains runbook-owned.
- [LAT-1 Latency Measurement completion report](lat1_latency_measurement_completion_report.md) — frozen measurement-implementation evidence from PR #505; current schema and results remain architecture/evaluation-owned.
- [E1-R3 completion report](e1r3_completion_report.md) — frozen provenance-preserving formation-summary implementation evidence from PR #436; current behavior remains architecture-owned.
- [E1-R4 completion report](e1r4_completion_report.md) — frozen retrieval-response grounding implementation evidence from PR #437; current behavior remains architecture-owned.
- [E1-R5 completion report](e1r5_completion_report.md) — frozen bounded Primary recall candidate-discovery implementation evidence from PR #439; current behavior and the PR #491 fold-in remain architecture-owned.
- [O1F completion report](o1f_completion_report.md) — frozen validation-only scheduler operational-hardening evidence from PR #429; current behavior remains architecture, implementation, and focused-smoke-owned.
- [I-5B completion report](i5b_completion_report.md) — frozen Pin / Unpin apply, API/UI, durable-governance, and ranking-hint evidence from PR #430; current behavior remains handoff-, implementation-, and focused-smoke-owned.
- [I-7C completion report](i7c_completion_report.md) — frozen Held Apply / Discard runtime-governance, API/UI, durable-evidence, and leakage-boundary evidence from PR #431; current behavior remains handoff-, implementation-, and focused-smoke-owned.
