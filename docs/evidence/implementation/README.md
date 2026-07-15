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

- [MVP-0 pass-through proxy](mvp0_pass_through_proxy.md) — frozen URL-swap pass-through skeleton evidence from PR #4/#5; current proxy/pipeline behavior remains architecture-owned.
- [MVP-1 runtime diagnostics smoke](mvp1_runtime_diagnostics_smoke.md) — frozen server-free diagnostics smoke evidence from PR #10; current diagnostics contract remains code-owned.
- [MVP-2 memory-light apply](mvp2_memory_light_apply.md) — frozen `memory_light` payload-compilation helper evidence from PR #21; current compile-apply behavior remains contract-owned.
- [MVP-2 profile file loading](mvp2_profile_file_loading.md) — frozen placeholder profile-file loading evidence from PR #14; current character workspace and profile-resolution behavior remain architecture-owned.
- [MVP-2 context compiler contract](mvp2_context_compiler_contract.md) — frozen first-code-level context-compiler contract evidence from PR #13; current primitives, ordering, and the corrected stable-prefix block set remain contract-owned.
- [MVP-2 gated compile decision](mvp2_gated_compile_decision.md) — frozen first compile-apply gate evidence from PR #20; current `CompileApplyDecision` semantics and decision taxonomy remain contract-owned.
- [MVP-2 runtime memory-light apply](mvp2_runtime_memory_light_apply.md) — frozen runtime-wiring evidence from PR #22 connecting memory-light compilation to `/v1/chat/completions`; current apply/mode/diagnostics behavior remains contract- and architecture-owned.
- [MVP-2 incoming system prompt fallback](mvp2_incoming_system_fallback.md) — frozen client system/developer compatibility-helper evidence from PR #17 (revised by PR #246); current instruction authority remains architecture-owned, and its still-valid text-normalization, render-order, and escaping rules were absorbed into the Context Compiler Contract.
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
- [E1-R1 completion report](e1r1_completion_report.md) — frozen route-owned trusted Home scene-admission evidence from PR #433; current behavior and trust policy remain handoff-, implementation-, and focused-smoke-owned.
- [E1-R2 completion report](e1r2_completion_report.md) — frozen dry-run-first idempotent character-store bootstrap evidence from PR #432; current command and store-layout behavior remain handoff-, implementation-, and focused-smoke-owned.
- [Docs Horizontal Status Sweep completion report](docs_horizontal_status_sweep_completion_report.md) — frozen docs-only horizontal status-convergence evidence from PR #434; current status, documentation model, and sequencing remain owned elsewhere.
- [E1 MVP Evaluation Evidence Consolidation completion report](e1_completion_report.md) — frozen docs-only evaluation-consolidation evidence from PR #425; current E1 behavior and interpretation remain architecture-, handoff-, implementation-, and evaluation-owned.
- [O1E completion report](o1e_completion_report.md) — frozen bounded scheduler operational-controls evidence from PR #426; current behavior remains handoff-, implementation-, contract-, and focused-smoke-owned.
- [I-4F completion report](i4f_completion_report.md) — frozen validation-only Forget product-completion evidence from PR #427; current behavior remains handoff-, implementation-, contract-, focused-smoke-, and UI-validation-owned.
- [O1D2 completion report](o1d2_completion_report.md) — frozen bounded scheduler-policy evidence from PR #418; current behavior remains handoff-, implementation-, configuration-, and focused-smoke-owned.
- [I-4E completion report](i4e_completion_report.md) — frozen loopback Forget API/UI evidence from PR #420; current behavior remains I-4 handoff-, implementation-, focused-smoke-, and UI-validation-owned.
- [UI-B1A completion report](ui_b1a_completion_report.md) — frozen read-only lifecycle-visibility evidence from PR #421; current behavior remains handoff-, projection-, SOUL Lab-, and focused-smoke-owned.
- [I-5A completion report](i5a_completion_report.md) — frozen Pin / Unpin contract and read-only-preflight evidence from PR #417; current behavior remains I-5A/I-5B handoff-, implementation-, fence-, and focused-smoke-owned.
- [I-7A/B completion report](i7ab_completion_report.md) — frozen Held Apply / Discard contract and read-only-preflight evidence from PR #423; current behavior remains I-7A/B/I-7C handoff-, implementation-, contract-, and focused-smoke-owned.
- [I1-GE completion report](i1ge_completion_report.md) — frozen durable-finalization crash/restart validation evidence from PR #411; current behavior remains handoff-, production-authority-, and focused-smoke-owned.
- [I-4D completion report](i4d_completion_report.md) — frozen Primary MEM lifecycle-aware retrieval exclusion evidence from PR #414; current behavior remains handoff-, implementation-, and focused-smoke-owned.
- [O1D1 completion report](o1d1_completion_report.md) — frozen accepted scheduler gates and one production round evidence from PR #412; current behavior remains handoff-, implementation-, configuration-, and focused-smoke-owned.
- [MVP-40 RelayCTX short-term extraction dry-run](mvp40_relayctx_short_term_extraction_dry_run.md) — frozen extraction-schema evidence from PR #234; current four-stage chain authority remains [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md)-owned.
- [MVP-41 RelayCTX short-term block assembly dry-run](mvp41_relayctx_short_term_block_assembly_dry_run.md) — frozen assembly-schema and priority-order evidence from PR #235; current authority remains [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md)-owned.
- [MVP-42 RelayCTX short-term runtime injection preflight](mvp42_relayctx_short_term_runtime_injection_preflight.md) — frozen preflight-schema evidence from PR #236; current authority remains [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md)-owned; the apply path this preflight predates now exists (MVP-43, default-off).
- [MVP-43 RelayCTX short-term runtime injection apply gate](mvp43_relayctx_short_term_runtime_injection_apply_gate.md) — frozen apply-gate evidence from PR #237 (pre-cutover wording reworded 2026-06-11); its 4-condition gate list is known-incomplete against current code (13 blocked reasons); current full gate/blocked-reason taxonomy remains [RelayCTX Short-Term Runtime Contract](../../contracts/relayctx_short_term_runtime_contract.md)-owned.
- [MVP-45 RelayINT fast path dry-run](mvp45_relayint_fast_path_dry_run.md) — frozen fast-path-schema evidence from PR #239; current chain authority remains [RelayINT Quick-Clarification Runtime Contract](../../contracts/relayint_quick_clarification_runtime_contract.md)-owned; the marker heuristics it describes as local are now ACG-4-consolidated.
- [MVP-46 RelayINT quick clarification preflight](mvp46_relayint_quick_clarification_preflight.md) — frozen preflight-schema evidence from PR #240; current authority remains [RelayINT Quick-Clarification Runtime Contract](../../contracts/relayint_quick_clarification_runtime_contract.md)-owned.
- [MVP-47 RelayINT quick clarification apply plan](mvp47_relayint_quick_clarification_apply_plan.md) — frozen plan-only apply evidence from PR #241 (squash-merged); current apply-plan gate/blocked-reason taxonomy remains [RelayINT Quick-Clarification Runtime Contract](../../contracts/relayint_quick_clarification_runtime_contract.md)-owned; actual user-visible apply remains deferred.
- [MVP-48 pipeline node result scaffold](mvp48_pipeline_node_result_scaffold.md) — frozen scaffold evidence from a direct-push documentation commit (no source PR); its "historical RelayINT / RelayREF compatibility boundary" section is superseded by [PM-D6](../../architecture/pm_d6_relayint_native_artifact_relayref_wrapper_removal.md); current `PipelineNodeResult` shape and node-name authority remain [PipelineNodeResult Contract](../../contracts/pipeline_node_result_contract.md)-owned.
- [MVP audit trace projection boundary](audit_trace_projection_boundary.md) — frozen typed-projection-boundary evidence from PR #264 (real merge, source and origin commit distinct); zero live referrers before this cutover; current audit-trace persistence, projector registries, and content-free validation remain [Audit Trace Content-Free Contract](../../architecture/audit_trace_content_free_contract.md)- and [PipelineNodeResult Contract](../../contracts/pipeline_node_result_contract.md)-owned.
