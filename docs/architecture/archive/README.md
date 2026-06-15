# Historical Architecture Design Archive

This directory contains design documents that preserve useful RelayLM design history but no longer define current component ownership or implementation status.

## Status rule

Documents in this directory are **non-canonical historical references**.

Use these documents as the current sources of truth:

1. [Pipeline responsibility design](../pipeline_responsibility_design.md) for component names, pipeline order, and responsibility boundaries.
2. [Pipeline implementation plan](../pipeline_implementation_plan.md) for implementation sequencing and current phase status.
3. Current module and contract documents for schema and behavior details.

Historical documents must not override those sources.

## Archived responsibility-split designs

### [RelayCTX Wake Loop Design](relayctx_wake_loop_design.md)

Date basis: 2026-05-31 JST.

Reason archived:

- predates the RelayINT / RelayREF responsibility split,
- assigns reference resolution and response-mode selection to RelayCTX,
- assigns Wake-time reflection and recovery to RelayREF,
- combines CTX working-memory concepts with semantic decisions now owned by RelayINT, RelaySCN, and RelayRUN.

Useful principles migrated into current documents:

- RAM-side working state remains separate from prompt-selected hints -> [Context packing design](../context_packing_design.md),
- prompt packing selects only what the current turn needs rather than filling the available budget -> [Context packing design](../context_packing_design.md),
- reference resolution prefers current CTX working state before long-term memory -> [RelayINT MVP design](../relayint_mvp_design.md),
- ambiguous references require clarification before memory retrieval -> [RelayINT MVP design](../relayint_mvp_design.md),
- explicit or confirmed long-term recall may use a clarification-gated two-step interaction -> [RelayINT MVP design](../relayint_mvp_design.md).

### [RelayREF / RelaySLP MVP Design](relayref_relayslp_mvp_design.md)

Date basis: 2026-05-31 JST.

Reason archived:

- defines RelayREF as a Wake-time reflection and recovery layer,
- predates the current rule `RelayINT = before action / RelayREF = after response`,
- places recovery orchestration and handoff repair under RelayREF rather than the current RelaySCN / RelayINT / RelayRUN split,
- contains an early combined REF/SLP artifact model that no longer matches current typed runtime artifacts.

Useful principles migrated or already represented in current documents:

- repaired context is a confirmation candidate, not trusted context -> [RelayRUN recovery response generator contract](../../contracts/relayrun_recovery_response_generator_contract.md),
- recovery must not auto-resume before user confirmation -> [RelayRUN recovery response generator contract](../../contracts/relayrun_recovery_response_generator_contract.md),
- recovery blocks MEM/SOUL persistence and limits retrieval scope -> [RelaySCN MVP scene policy](../relayscn_mvp_scene_policy.md),
- ordinary ambiguity should use RelayINT clarification rather than SLP -> [RelayINT MVP design](../relayint_mvp_design.md),
- forced sleep/reset should remain rare and fail-closed -> [RelayMEM SLP execution design](../relaymem_slp_execution_design.md),
- no extra Wake-time LLM output should be generated solely to run SLP -> [RelayMEM SLP execution design](../relaymem_slp_execution_design.md).

## Archived product-origin designs

### [Persona-Specialized Proxy Design](persona_specialized_proxy_design.md)

Reason archived:

- its proxy role, context hierarchy, adapter model, agent boundary, and scope identity are covered by current architecture and contracts,
- its implementation-boundary notes describe an early post-MVP-12 state,
- it mixes durable product principles with superseded implementation status.

Useful principles migrated into current documents:

- RelayLM is evaluated on whether persona and relationship continuity make conversation comfortable, not task success alone -> [AI character product principles](../ai_character_product_principles.md),
- conversation stickiness must come from coherence and comfort rather than manipulative engagement -> [AI character product principles](../ai_character_product_principles.md),
- memory warmth, non-creepiness, and growth feeling are explicit product-quality axes -> [AI character product principles](../ai_character_product_principles.md),
- persona layers update at different speeds -> [RelaySOUL persona update cadence design](../../relaysoul/persona_update_cadence_design.md),
- `persona_plasticity` changes proposal thresholds, not mutation authority -> [RelaySOUL persona update cadence design](../../relaysoul/persona_update_cadence_design.md).

Current replacements:

- [Runtime architecture](../runtime_architecture.md)
- [Context packing design](../context_packing_design.md)
- [AI character product principles](../ai_character_product_principles.md)
- [RelaySOUL design](../../relaysoul/relaysoul_design.md)
- [RelaySOUL persona update cadence design](../../relaysoul/persona_update_cadence_design.md)

### [RelayLM VTuber Memory Proxy Design](vtuber_memory_proxy_design.md)

Reason archived:

- topology, modes, backend stance, routing, and compatibility behavior are covered by current runtime and integration documents,
- its first-product implementation notes are historical,
- its distinct remaining value is product positioning and realtime latency posture.

Useful principles migrated into current documents:

- AI character memory should improve continuity without replacing frontend ownership -> [AI character product principles](../ai_character_product_principles.md),
- fast first speech takes priority over maximum retrieval depth -> [AI character product principles](../ai_character_product_principles.md),
- heavy memory extraction and indexing belong outside the synchronous speech path -> [AI character product principles](../ai_character_product_principles.md),
- ASR-prefetch and speculative repacking remain optional, discardable, non-mutating optimizations -> [AI character product principles](../ai_character_product_principles.md).

Current replacements:

- [Runtime architecture](../runtime_architecture.md)
- [Open-LLM-VTuber integration design](../open_llm_vtuber_integration.md)
- [AI VTuber pipeline profile](../ai_vtuber_pipeline_profile.md)
- [AI character product principles](../ai_character_product_principles.md)
- [Runtime operational requirements](../runtime_operational_requirements.md)

## Archived cross-cutting planning documents

### [Product Runtime Hardening](product_runtime_hardening.md)

Reason archived:

- combines an obsolete MVP-0 through MVP-5 roadmap with durable runtime requirements,
- duplicates current runtime, context, memory, integration, and product documents,
- mixes current acceptance/operations ideas with early implementation assumptions.

Useful principles migrated into current documents:

- fallback is normal product behavior but must remain policy- and compatibility-gated -> [Runtime operational requirements](../runtime_operational_requirements.md),
- audit/trace diagnostics should use typed content-free projections -> [Runtime operational requirements](../runtime_operational_requirements.md),
- local-first storage, namespace isolation, visible backend configuration, and no hidden telemetry are explicit privacy requirements -> [Runtime operational requirements](../runtime_operational_requirements.md),
- compatibility, persona/context, memory, latency, recovery, and idempotency need product-level acceptance criteria -> [Runtime operational requirements](../runtime_operational_requirements.md),
- product experience hierarchy remains separate from operational requirements -> [AI character product principles](../ai_character_product_principles.md).

Current replacements:

- [Pipeline implementation plan](../pipeline_implementation_plan.md)
- [Runtime architecture](../runtime_architecture.md)
- [Runtime operational requirements](../runtime_operational_requirements.md)
- [AI character product principles](../ai_character_product_principles.md)
- [Context packing design](../context_packing_design.md)
- [RelayMEM retrieval execution design](../relaymem_retrieval_execution_design.md)
- [RelayMEM SLP execution design](../relaymem_slp_execution_design.md)
- [Open-LLM-VTuber integration design](../open_llm_vtuber_integration.md)

## Reviewed and retained as active documents

The following dated documents still contain a distinct current design contract and remain in the active architecture index:

- `context_packing_design.md`
- `runtime_operational_requirements.md`
- `relaymem_mvp_design.md`
- `relaymem_slp_execution_design.md`
- `relaymem_retrieval_execution_design.md`
- `relayemo_return_side_style_adapter_design.md`
- `ai_vtuber_pipeline_profile.md`
- `open_llm_vtuber_integration.md`

No remaining archive candidates are declared by this index. Future candidates should be archived only after their unique principles are mapped to current owner documents.
