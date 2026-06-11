# RelayLM Documentation

This page is the entry point for RelayLM documentation.

## Start here

- [Architecture docs](architecture/README.md)
- [MVP summaries and milestone notes](mvp/README.md)
- [Config schema](config_schema.md)
- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)
- [OpenWebUI + LM Studio manual smoke runbook](openwebui_lmstudio_manual_smoke.md)

## Architecture

Use these docs to understand the RelayLM pipeline, responsibility boundaries, and profile-specific runtime design.

- [Architecture docs index](architecture/README.md)
- [Runtime architecture](architecture/runtime_architecture.md)
- [Product runtime hardening](architecture/product_runtime_hardening.md)
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md)
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md)
- [AI VTuber pipeline profile](architecture/ai_vtuber_pipeline_profile.md)
- [VTuber memory proxy design](architecture/vtuber_memory_proxy_design.md)
- [Persona-specialized proxy design](architecture/persona_specialized_proxy_design.md)
- [Open-LLM-VTuber integration](architecture/open_llm_vtuber_integration.md)
- [RelayINT MVP design](architecture/relayint_mvp_design.md)
- [RelayREF / RelaySLP MVP design](architecture/relayref_relayslp_mvp_design.md)
- [RelayMEM MVP design](architecture/relaymem_mvp_design.md)
- [RelayMEM SLP execution design](architecture/relaymem_slp_execution_design.md)
- [RelayMEM retrieval execution design](architecture/relaymem_retrieval_execution_design.md)
- [RelayEMO return-side style adapter design](architecture/relayemo_return_side_style_adapter_design.md)

## MVP summaries

MVP summaries and MVP-focused implementation notes are collected under `docs/mvp/`.

- [MVP summaries and milestone notes](mvp/README.md)

Future MVP summaries should be created directly under `docs/mvp/` and linked from the MVP index.

## Contracts and safety gates

These docs describe artifact schemas, dry-run contracts, approval boundaries, and persistence/apply gates.

- [Runtime compile artifact contract](runtime_compile_artifact_contract.md)
- [Context compiler contract](context_compiler_contract.md)
- [RelaySOUL patch candidate contract](relaysoul_patch_candidate_contract.md)
- [RelaySOUL revision contract](relaysoul_revision_contract.md)
- [RelaySOUL approval contract](relaysoul_approval_contract.md)
- [RelaySOUL persistence contract](relaysoul_persistence_contract.md)
- [RelaySOUL patch compile dry-run contract](relaysoul_compile_dry_run_contract.md)
- [RelaySOUL explicit approval artifact contract](relaysoul_explicit_approval_artifact_contract.md)
- [RelaySOUL preflight lineage freshness policy](relaysoul_preflight_lineage_freshness_policy.md)

## OpenWebUI / LM Studio setup and smoke

- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)
- [OpenWebUI + LM Studio manual smoke runbook](openwebui_lmstudio_manual_smoke.md)
- [OpenWebUI model preset/avatar checklist](openwebui_model_preset_checklist.md)
- [OpenWebUI route response differentiation checks](openwebui_response_differentiation_checks.md)
- [OpenWebUI + LM Studio manual smoke results template](openwebui_lmstudio_manual_smoke_results_template.md)
- [OpenWebUI + RelayLM + LM Studio manual smoke result (2026-05-26)](openwebui_lmstudio_manual_smoke_result_2026_05_26.md)
- [OpenWebUI + RelayLM + LM Studio troubleshooting](openwebui_lmstudio_troubleshooting.md)

## RelayMEM and local behavior evaluation

- [RelayMEM runtime payload diff evaluation smoke](relaymem_runtime_payload_eval.md)
- [RelayMEM local LLM evaluation guide](relaymem_local_llm_eval_guide.md)
- [RelayMEM local response comparison guide](relaymem_local_response_comparison.md)

## RelaySOUL design and execution gates

- [RelaySOUL persona source calibration design](relaysoul_design.md)
- [RelaySOUL dry-run chain summary](relaysoul_dry_run_chain_summary.md)
- [RelaySOUL preflight chain summary](relaysoul_preflight_chain_summary.md)
- [RelaySOUL persistence preflight summary](relaysoul_persistence_preflight_summary.md)
- [RelaySOUL apply execution gate design](relaysoul_apply_execution_gate_design.md)
- [RelaySOUL rollback execution gate design](relaysoul_rollback_execution_gate_design.md)
- [RelaySOUL storage writer gate design](relaysoul_storage_writer_gate_design.md)
- [RelaySOUL persistence execution gate design](relaysoul_persistence_execution_gate_design.md)
- [RelaySOUL gate design consistency review](relaysoul_gate_design_consistency_review.md)
- [RelaySOUL gate dry-run CLI design](relaysoul_gate_dry_run_cli_design.md)

## Examples

- [OpenWebUI + LM Studio copy-ready config](../examples/config/openwebui_lmstudio.yaml)
- [OpenWebUI example profiles](../examples/profiles/)
