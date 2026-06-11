# RelayLM Architecture Docs

This directory indexes RelayLM architecture and pipeline design documents.

The core architecture documents are being consolidated out of the top-level `docs/` directory. During this transition, some links still point to legacy `../*.md` files until the documents are physically moved in small follow-up batches.

## Pipeline architecture

- [Pipeline implementation plan](../pipeline_implementation_plan.md)
- [Pipeline responsibility design](../pipeline_responsibility_design.md)
- [Runtime architecture](../runtime_architecture.md)
- [Product runtime hardening](../product_runtime_hardening.md)

## Profile-specific architecture

- [AI VTuber pipeline profile](../ai_vtuber_pipeline_profile.md)
- [VTuber memory proxy design](../vtuber_memory_proxy_design.md)
- [Persona-specialized proxy design](../persona_specialized_proxy_design.md)
- [Open-LLM-VTuber integration](../open_llm_vtuber_integration.md)

## Context and scene architecture

- [Context packing design](../context_packing_design.md)
- [Safe SOUL / Scene / CTX compile chain](../safe_soul_scene_ctx_compile_chain.md)
- [RelayCTX Wake loop design](../relayctx_wake_loop_design.md)
- [Scene lifecycle design](../scene_lifecycle_design.md)
- [Scene-aware memory scope design](../scene_memory_scope_design.md)
- [RelaySCN MVP scene policy](../relayscn_mvp_scene_policy.md)

## Module responsibility docs

- [RelayINT MVP design](../relayint_mvp_design.md)
- [RelayREF / RelaySLP MVP design](../relayref_relayslp_mvp_design.md)
- [RelayMEM MVP design](../relaymem_mvp_design.md)
- [RelayMEM SLP execution design](../relaymem_slp_execution_design.md)
- [RelayMEM retrieval execution design](../relaymem_retrieval_execution_design.md)
- [RelayEMO return-side style adapter design](../relayemo_return_side_style_adapter_design.md)

## Follow-up cleanup

Future architecture docs should be created directly under `docs/architecture/` when they describe cross-cutting runtime design, pipeline order, responsibility boundaries, or profile-specific pipeline contracts.

Suggested physical move order:

1. Move the three core pipeline files first:
   - `pipeline_implementation_plan.md`
   - `pipeline_responsibility_design.md`
   - `ai_vtuber_pipeline_profile.md`
2. Move runtime and product architecture docs.
3. Move profile-specific architecture docs.
4. Leave contracts, smoke runbooks, and MVP summaries in their own directories.
