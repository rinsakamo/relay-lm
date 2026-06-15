# RelayLM Architecture Docs

This directory indexes RelayLM architecture and pipeline design documents.

The main architecture, profile-specific architecture, context/scene architecture, and module-responsibility architecture documents are housed here.

## Canonical precedence

When architecture documents disagree, use this order:

1. [Pipeline responsibility design](pipeline_responsibility_design.md) for canonical component names, pipeline order, and responsibility ownership.
2. [Pipeline implementation plan](pipeline_implementation_plan.md) for current phase status and implementation sequencing.
3. Dedicated current module or contract documents for schema and module-specific details.
4. Dated MVP and archived design documents as historical rationale only.

In particular, current terminology fixes these boundaries:

```text
RelayINT = input-side intent / ambiguity / clarification gate
RelayREF = output-side diagnostics-only observer
RelaySCN = scene and persistence policy
RelayCTX Repack = backend input construction and token-budget application
RelayRUN = runtime orchestration, fallback/recovery, checkpoints, trace, and lineage
RelaySLP = out-of-band memory / SOUL compilation path
```

Historical and superseded documents are collected under [`archive/`](archive/README.md). They preserve design rationale but do not define current ownership or implementation status.

## Pipeline architecture

- [Pipeline responsibility design](pipeline_responsibility_design.md) — canonical responsibility and naming source
- [Pipeline implementation plan](pipeline_implementation_plan.md) — implementation order and current phase status
- [Client history authority contract](client_history_authority_contract.md)
- [Client instruction authority contract](client_instruction_authority_contract.md)
- [Runtime architecture](runtime_architecture.md)
- [Runtime operational requirements](runtime_operational_requirements.md)
- [AI character product principles](ai_character_product_principles.md)

The two client-authority contracts share one external boundary:

```text
Client-provided messages are request evidence, not backend context.
RelayLM extracts the current turn and current instruction evidence,
then reconstructs the backend payload from RelayLM-owned state.
```

## Profile-specific architecture

- [AI VTuber pipeline profile](ai_vtuber_pipeline_profile.md)
- [Open-LLM-VTuber integration](open_llm_vtuber_integration.md)

## Context and scene architecture

- [Context packing design](context_packing_design.md)
- [Safe SOUL / Scene / CTX compile chain](safe_soul_scene_ctx_compile_chain.md)
- [Scene lifecycle design](scene_lifecycle_design.md)
- [Scene-aware memory scope design](scene_memory_scope_design.md)
- [RelaySCN MVP scene policy](relayscn_mvp_scene_policy.md)

## Module responsibility docs

- [RelayINT MVP design](relayint_mvp_design.md)
- [RelayMEM MVP design](relaymem_mvp_design.md)
- [RelayMEM SLP execution design](relaymem_slp_execution_design.md)
- [RelayMEM retrieval execution design](relaymem_retrieval_execution_design.md)
- [RelayEMO return-side style adapter design](relayemo_return_side_style_adapter_design.md)

## Historical design archive

- [Archive index](archive/README.md)
- [RelayCTX Wake Loop Design](archive/relayctx_wake_loop_design.md) — pre-RelayINT responsibility split
- [RelayREF / RelaySLP MVP Design](archive/relayref_relayslp_mvp_design.md) — pre-RelayINT RelayREF definition
- [Persona-Specialized Proxy Design](archive/persona_specialized_proxy_design.md) — early product and persona-proxy direction
- [RelayLM VTuber Memory Proxy Design](archive/vtuber_memory_proxy_design.md) — early VTuber product-target direction
- [Product Runtime Hardening](archive/product_runtime_hardening.md) — early cross-cutting MVP/runtime planning

## Follow-up cleanup

Architecture consolidation is still in progress for implementation-status notes and any future overlapping design documents. New current architecture docs should be created directly under `docs/architecture/`; superseded design rationale should move to `docs/architecture/archive/` only after unique principles are migrated.

Contracts, smoke runbooks, and MVP summaries remain in their own directories. Historical MVP summaries should remain immutable snapshots unless a broken link or explicit factual correction requires an annotation.
