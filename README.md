# RelayLM

RelayLM is a persona-specialized OpenAI-compatible conversation proxy for local LLM applications, AI companions, VTubers, agents, and local inference runtimes.

It is not a language model or a memory database. RelayLM sits in front of an LLM backend and repacks persona, memory, RAG, recent turns, room/scene state, and spilled context into a token-budgeted, persona-stable, KV-reuse-aware effective context.

Initial product target:

- OpenWebUI model preset / avatar -> RelayLM -> LM Studio as the standard MVP UI/backend path
- URL-swap integration through an OpenAI-compatible `/v1/chat/completions` endpoint
- persona-stable and KV-reuse-aware context packing
- Open-LLM-VTuber as an optional frontend / example integration

## Core idea

RelayLM compiles memory, RAG, and chat history into a prefix-stable context layout so that engines such as vLLM and SGLang can reuse prefix/KV cache across turns and character threads.

The first practical value is simple:

> Make an AI VTuber or AI companion feel like it remembers unusually well, without requiring the frontend to manage long context directly.

RelayLM's longer-term product axis is conversation quality: preserve persona consistency, relationship continuity, memory warmth, and token-budget stability so the user wants to keep talking.

## Architecture

RelayLM uses the RelayStack architecture as a product/control-plane layer:

- RelayMEM: memory candidates and long-term memory sources
- RelayCTX: effective context construction and compression
- RelayKV: runtime/cache research boundary, developed in `rinsakamo/relay-kv`
- RelayPLC: policy, fallback, routing, and budget control
- RelayTRC: trace and lineage, deferred for the MVP
- Relay Adapter: OpenAI-compatible proxy and backend adapters

## Initial docs

- [VTuber memory proxy design](docs/vtuber_memory_proxy_design.md)
- [AI VTuber pipeline profile](docs/ai_vtuber_pipeline_profile.md)
- [Context packing design](docs/context_packing_design.md)
- [Persona-specialized proxy design](docs/persona_specialized_proxy_design.md)
- [RelaySOUL persona source calibration design](docs/relaysoul_design.md)
- [Safe SOUL / Scene / CTX compile chain](docs/safe_soul_scene_ctx_compile_chain.md)
- [Runtime compile gate design](docs/runtime_compile_gate_design.md)
- [Runtime compile artifact contract](docs/runtime_compile_artifact_contract.md)
- [RelayRUN runtime checkpoint design](docs/relayrun_runtime_checkpoint_design.md)
- [RelayRUN recovery response generator contract](docs/relayrun_recovery_response_generator_contract.md)
- [Scene lifecycle design](docs/scene_lifecycle_design.md)
- [Scene-aware memory scope design](docs/scene_memory_scope_design.md)
- [RelaySCN MVP scene policy](docs/relayscn_mvp_scene_policy.md)
- [RelayINT MVP design](docs/relayint_mvp_design.md)
- [MVP summaries and milestone notes](docs/mvp/README.md)
- [RelaySOUL patch candidate contract](docs/relaysoul_patch_candidate_contract.md)
- [RelaySOUL revision contract](docs/relaysoul_revision_contract.md)
- [RelaySOUL approval contract](docs/relaysoul_approval_contract.md)
- [RelaySOUL persistence contract](docs/relaysoul_persistence_contract.md)
- [RelaySOUL patch compile dry-run contract](docs/relaysoul_compile_dry_run_contract.md)
- [RelaySOUL persistence storage design](docs/relaysoul_persistence_storage_design.md)
- [RelaySOUL dry-run chain summary](docs/relaysoul_dry_run_chain_summary.md)
- [RelaySOUL preflight chain summary](docs/relaysoul_preflight_chain_summary.md)
- [RelaySOUL persistence preflight summary](docs/relaysoul_persistence_preflight_summary.md)
- [RelaySOUL apply execution gate design](docs/relaysoul_apply_execution_gate_design.md)
- [RelaySOUL rollback execution gate design](docs/relaysoul_rollback_execution_gate_design.md)
- [RelaySOUL storage writer gate design](docs/relaysoul_storage_writer_gate_design.md)
- [RelaySOUL persistence execution gate design](docs/relaysoul_persistence_execution_gate_design.md)
- [RelaySOUL gate design consistency review](docs/relaysoul_gate_design_consistency_review.md)
- [RelaySOUL explicit approval artifact contract](docs/relaysoul_explicit_approval_artifact_contract.md)
- [RelaySOUL preflight lineage freshness policy](docs/relaysoul_preflight_lineage_freshness_policy.md)
- [RelaySOUL gate dry-run CLI design](docs/relaysoul_gate_dry_run_cli_design.md)
- [RelayCTX Wake loop design](docs/relayctx_wake_loop_design.md)
- [RelayEMO return-side style adapter design](docs/relayemo_return_side_style_adapter_design.md)
- [RelayREF / RelaySLP MVP design](docs/relayref_relayslp_mvp_design.md)
- [RelayMEM MVP design](docs/relaymem_mvp_design.md)
- [RelayMEM SLP execution design](docs/relaymem_slp_execution_design.md)
- [RelayMEM retrieval execution design](docs/relaymem_retrieval_execution_design.md)
- [RelayMEM runtime payload diff evaluation smoke](docs/relaymem_runtime_payload_eval.md)
- [RelayMEM local LLM evaluation guide](docs/relaymem_local_llm_eval_guide.md)
- [RelayMEM local response comparison guide](docs/relaymem_local_response_comparison.md)
- [OpenWebUI + LM Studio MVP](docs/openwebui_lmstudio_mvp.md)
- [OpenWebUI + LM Studio manual smoke runbook](docs/openwebui_lmstudio_manual_smoke.md)
- [OpenWebUI model preset/avatar checklist](docs/openwebui_model_preset_checklist.md)
- [OpenWebUI route response differentiation checks](docs/openwebui_response_differentiation_checks.md)
- [OpenWebUI + LM Studio manual smoke results template](docs/openwebui_lmstudio_manual_smoke_results_template.md)
- [OpenWebUI + RelayLM + LM Studio manual smoke result (2026-05-26)](docs/openwebui_lmstudio_manual_smoke_result_2026_05_26.md)
- [OpenWebUI + RelayLM + LM Studio troubleshooting](docs/openwebui_lmstudio_troubleshooting.md)
- [OpenWebUI + LM Studio copy-ready config](examples/config/openwebui_lmstudio.yaml)
- [OpenWebUI example profiles](examples/profiles/)
- [Open-LLM-VTuber integration (optional example)](docs/open_llm_vtuber_integration.md)
- [Runtime architecture](docs/runtime_architecture.md)
- [RelayLM pipeline implementation plan](docs/pipeline_implementation_plan.md)
- [RelayLM pipeline responsibility design](docs/pipeline_responsibility_design.md)
- [Config schema](docs/config_schema.md)
- [Token policy profile settings](docs/token_policy_profiles.md)
- [Context compiler contract](docs/context_compiler_contract.md)
- [Product runtime hardening](docs/product_runtime_hardening.md)

## MVP direction

The first implementation is a thin OpenAI-compatible proxy with this standard MVP path:

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

Optional integration path:

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

For step-by-step OpenWebUI + LM Studio setup and route-model mapping, see [OpenWebUI + LM Studio MVP](docs/openwebui_lmstudio_mvp.md).

## MVP-0 quick start

Install locally:

```bash
pip install -e .
```

If the environment blocks package index access during editable install, use the current environment's build tools instead:

```bash
pip install -e . --no-build-isolation
```

Create a config:

```bash
cp config.example.yaml config.yaml
```

Run RelayLM through the installed console script:

```bash
relaylm --config config.yaml
```

If editable install failed before installing the console script, run the module directly from the repository root:

```bash
python -m relaylm.app --config config.yaml
```

Or run with uvicorn:

```bash
RELAYLM_CONFIG=config.yaml uvicorn relaylm.app:create_app --factory --host 127.0.0.1 --port 8090
```

Then point Open-LLM-VTuber's OpenAI-compatible base URL at:

```text
http://localhost:8090/v1
```

## Relationship to relay-kv

`relay-kv` remains the runtime/KV-cache research repository. RelayLM starts one layer above runtime APIs as a memory and context proxy. RelayLM should benefit from RelayKV's design lessons, especially working-set selection, anchor/recent/retrieved separation, Persona Anchor KV, and cache-aware layout, without mutating engine KV cache in the initial product.
