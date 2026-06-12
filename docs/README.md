# RelayLM Documentation

This page is the entry point for RelayLM documentation.

## Start here

- [Architecture docs](architecture/README.md)
- [MVP summaries and milestone notes](mvp/README.md)
- [Contract docs](contracts/README.md)
- [Smoke and validation docs](smoke/README.md)
- [Config schema](config_schema.md)
- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)

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

Contract, artifact, schema, approval, and gate docs are collected under `docs/contracts/`.

- [Contract docs](contracts/README.md)

## Setup, smoke, and validation

- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)
- [Smoke and validation docs](smoke/README.md)

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
