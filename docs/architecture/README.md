# RelayLM Architecture Docs

This directory indexes RelayLM architecture and pipeline design documents.

The main architecture, profile-specific architecture, context/scene architecture, and module-responsibility architecture documents are housed here.

## Canonical precedence

When architecture documents disagree, use this order:

1. [Pipeline responsibility design](pipeline_responsibility_design.md) for canonical component names, pipeline order, and responsibility ownership.
2. [Pipeline implementation plan](pipeline_implementation_plan.md) for current phase status and implementation sequencing.
3. Dedicated current module or contract documents for schema and module-specific details.
4. Dated MVP and pre-split design documents as historical rationale only.

In particular, current terminology fixes these boundaries:

```text
RelayINT = input-side intent / ambiguity / clarification gate
RelayREF = output-side diagnostics-only observer
RelaySCN = scene and persistence policy
RelayCTX Repack = backend input construction and token-budget application
RelayRUN = runtime orchestration, fallback/recovery, checkpoints, trace, and lineage
RelaySLP = out-of-band memory / SOUL compilation path
```

Documents dated before the RelayINT / RelayREF split may use `RelayREF` for Wake-time context repair. That usage is historical and maps primarily to RelayINT, RelaySCN recovery policy, and RelayRUN recovery orchestration in the current architecture.

## Pipeline architecture

- [Pipeline responsibility design](pipeline_responsibility_design.md) — canonical responsibility and naming source
- [Pipeline implementation plan](pipeline_implementation_plan.md) — implementation order and current phase status
- [Client history authority contract](client_history_authority_contract.md)
- [Client instruction authority contract](client_instruction_authority_contract.md)
- [Runtime architecture](runtime_architecture.md)
- [Product runtime hardening](product_runtime_hardening.md)

The two client-authority contracts share one external boundary:

```text
Client-provided messages are request evidence, not backend context.
RelayLM extracts the current turn and current instruction evidence,
then reconstructs the backend payload from RelayLM-owned state.
```

## Profile-specific architecture

- [AI VTuber pipeline profile](ai_vtuber_pipeline_profile.md)
- [VTuber memory proxy design](vtuber_memory_proxy_design.md)
- [Persona-specialized proxy design](persona_specialized_proxy_design.md)
- [Open-LLM-VTuber integration](open_llm_vtuber_integration.md)

## Context and scene architecture

- [Context packing design](context_packing_design.md)
- [Safe SOUL / Scene / CTX compile chain](safe_soul_scene_ctx_compile_chain.md)
- [RelayCTX Wake loop design](relayctx_wake_loop_design.md) — historical pre-RelayINT responsibility split; use for rationale, not canonical ownership
- [Scene lifecycle design](scene_lifecycle_design.md)
- [Scene-aware memory scope design](scene_memory_scope_design.md)
- [RelaySCN MVP scene policy](relayscn_mvp_scene_policy.md)

## Module responsibility docs

- [RelayINT MVP design](relayint_mvp_design.md)
- [RelayREF / RelaySLP MVP design](relayref_relayslp_mvp_design.md) — historical pre-split terminology; current RelayREF is output-side only
- [RelayMEM MVP design](relaymem_mvp_design.md)
- [RelayMEM SLP execution design](relaymem_slp_execution_design.md)
- [RelayMEM retrieval execution design](relaymem_retrieval_execution_design.md)
- [RelayEMO return-side style adapter design](relayemo_return_side_style_adapter_design.md)

## Follow-up cleanup

Architecture consolidation is still in progress for dated pre-RelayINT documents and implementation-status notes. New architecture docs should be created directly under `docs/architecture/` when they describe cross-cutting runtime design, pipeline order, responsibility boundaries, or profile-specific pipeline contracts.

Contracts, smoke runbooks, and MVP summaries remain in their own directories. Historical MVP summaries should remain immutable snapshots unless a broken link or explicit factual correction requires an annotation.
