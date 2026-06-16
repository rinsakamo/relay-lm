# RelayLM Architecture Docs

This is the active architecture index.

## Canonical precedence

When documents disagree:

1. [Pipeline Responsibility Design](pipeline_responsibility_design.md) — component names, ownership, and canonical target order.
2. [Pipeline Implementation Plan](pipeline_implementation_plan.md) — current phase status and sequencing.
3. Dedicated current module/contract documents — implemented schemas and bounded behavior.
4. [Current / Target / Migration Guide](current_target_migration_guide.md) — interpretation of compatibility and target material.
5. Archived and dated MVP documents — historical rationale only.

Standard labels:

```text
Current implemented
Current compatibility
Target architecture
Required migration
Historical only
```

A v1 example is not a current wire contract unless an implemented producer, consumer, runtime position, and schema are named.

## Canonical terminology

```text
RelaySCN = scene and persistence policy
RelayEMO = request/session-local affect and transient expression hints
RelayINT = input-side intent, ambiguity, clarification, retrieval decision
RelayMEM Retrieval = synchronous read-only memory evidence
RelayCTX Repack = backend input construction and token-budget application
RelayCTX Unpack = visible/internal output separation
RelayREF = post-generation diagnostics-only observer
RelayRUN = orchestration, fallback/recovery, checkpoint, trace, lineage
RelaySLP = deferred memory/SOUL candidate compiler
```

## Pipeline architecture

- [Pipeline responsibility design](pipeline_responsibility_design.md)
- [Pipeline implementation plan](pipeline_implementation_plan.md)
- [Current / Target / Migration Guide](current_target_migration_guide.md)
- [Client history authority contract](client_history_authority_contract.md)
- [Client instruction authority contract](client_instruction_authority_contract.md)
- [Runtime architecture](runtime_architecture.md)
- [Runtime compile gate design](runtime_compile_gate_design.md)
- [Runtime operational requirements](runtime_operational_requirements.md)
- [AI character product principles](ai_character_product_principles.md)

Managed-route authority target:

```text
client messages = request evidence
validated current turn + bounded instruction evidence
  -> RelayLM-owned backend context
```

Current implementation includes a narrow default-off no-instruction apply slice. Instruction-bearing managed apply remains incomplete; see [Project Status](../PROJECT_STATUS.md).

## Runtime orchestration

- [Client History Exclusion Apply Forward Gate](client_history_exclusion_apply_forward_gate.md)
- [Managed-route fallback authority contract](managed_route_fallback_contract.md)
- [RelayRUN runtime checkpoint design](relayrun_runtime_checkpoint_design.md)
- [Runtime compile gate design](runtime_compile_gate_design.md)

`pass_through` is an explicit delegated route, not the generic terminal fallback for managed compilation.

## Context and scene

- [Context packing design](context_packing_design.md)
- [Safe SOUL / Scene / CTX compile chain](safe_soul_scene_ctx_compile_chain.md)
- [Scene lifecycle design](scene_lifecycle_design.md)
- [Scene-aware memory scope current / target boundary](scene_memory_scope_current_target.md)
- [Scene-aware memory scope detailed design](scene_memory_scope_design.md)
- [RelaySCN MVP scene policy](relayscn_mvp_scene_policy.md)

General v1 scene examples are target schemas. Current RelaySCN uses v0 shapes and the current EMO-to-SCN compatibility order.

## Memory and interpretation modules

- [RelayINT MVP design](relayint_mvp_design.md)
- [RelayMEM / RelaySLP current / target boundary](relaymem_slp_current_target.md)
- [RelayMEM MVP detailed design](relaymem_mvp_design.md)
- [RelayMEM retrieval execution design](relaymem_retrieval_execution_design.md)
- [RelayMEM SLP detailed execution design](relaymem_slp_execution_design.md)
- [RelayEMO return-side expression design](relayemo_return_side_expression_design.md)

Current Retrieval v0 and dry-run/preflight SLP foundations must not be read as complete target memory apply.

## Profile-specific architecture

- [AI VTuber pipeline profile](ai_vtuber_pipeline_profile.md)
- [Open-LLM-VTuber current / target boundary](open_llm_vtuber_current_target.md)
- [Open-LLM-VTuber detailed integration design](open_llm_vtuber_integration.md)

Open-LLM-VTuber is optional. Current streaming is primarily backend forwarding; the target Stream Unpack/output pipeline is planned.

## Legacy compatibility redirects

These files preserve old links and are not active specifications:

- `relayctx_wake_loop_design.md`
- `relayref_relayslp_mvp_design.md`
- `persona_specialized_proxy_design.md`
- `vtuber_memory_proxy_design.md`
- `product_runtime_hardening.md`
- `relayemo_return_side_style_adapter_design.md`
- `../relayrun_runtime_checkpoint_design.md`
- `../runtime_compile_gate_design.md`

Current documents link directly to canonical files rather than through redirects.

## Historical archive

- [Archive index](archive/README.md)

## Maintenance rule

- Keep transient status in `PROJECT_STATUS.md` and the implementation plan.
- Label current, compatibility, target, and migration sections explicitly.
- Name current schema and producer when a target schema is also shown.
- Identify migration consumers and smoke coverage.
- Preserve detailed target design when adding concise current/target boundary summaries.
- Move superseded rationale to the archive only after unique intent is preserved.
