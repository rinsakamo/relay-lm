# Historical Architecture Design Archive

This directory contains design documents that preserve useful RelayLM design history but no longer define current component ownership or implementation status.

## Status rule

Documents in this directory are **non-canonical historical references**.

Use these documents as the current sources of truth:

1. [Pipeline responsibility design](../pipeline_responsibility_design.md) for component names, pipeline order, and responsibility boundaries.
2. [Pipeline implementation plan](../pipeline_implementation_plan.md) for implementation sequencing and current phase status.
3. Current module and contract documents for schema and behavior details.

Historical documents must not override those sources.

## Archived documents

### [RelayCTX Wake Loop Design](relayctx_wake_loop_design.md)

Date basis: 2026-05-31 JST.

Reason archived:

- predates the RelayINT / RelayREF responsibility split,
- assigns reference resolution and response-mode selection to RelayCTX,
- assigns Wake-time reflection and recovery to RelayREF,
- combines CTX working-memory concepts with semantic decisions now owned by RelayINT, RelaySCN, and RelayRUN.

Still useful for:

- the distinction between RAM-side working state and prompt hints,
- early reference-confidence ideas,
- the two-step memory recall UX,
- the motivation for minimal context repacking.

Current replacements:

- [RelayINT MVP design](../relayint_mvp_design.md)
- [Pipeline responsibility design](../pipeline_responsibility_design.md)
- [Context packing design](../context_packing_design.md)
- [Context compiler contract](../../contracts/context_compiler_contract.md)

### [RelayREF / RelaySLP MVP Design](relayref_relayslp_mvp_design.md)

Date basis: 2026-05-31 JST.

Reason archived:

- defines RelayREF as a Wake-time reflection and recovery layer,
- predates the current rule `RelayINT = before action / RelayREF = after response`,
- places recovery orchestration and handoff repair under RelayREF rather than the current RelaySCN / RelayINT / RelayRUN split,
- contains an early combined REF/SLP artifact model that no longer matches current typed runtime artifacts.

Still useful for:

- recovery UX wording,
- conservative sleep/reflect trigger ideas,
- the rule that repaired context requires user confirmation,
- simulation observations about ambiguity and forced sleep frequency.

Current replacements:

- [Pipeline responsibility design](../pipeline_responsibility_design.md)
- [RelayINT MVP design](../relayint_mvp_design.md)
- [RelaySCN MVP scene policy](../relayscn_mvp_scene_policy.md)
- [RelayRUN runtime checkpoint design](../../relayrun_runtime_checkpoint_design.md)
- [RelayMEM SLP execution design](../relaymem_slp_execution_design.md)

## Reviewed but retained as active documents

The following dated documents still contain a distinct current design contract and remain in the active architecture index:

- `context_packing_design.md`
- `relaymem_mvp_design.md`
- `relaymem_slp_execution_design.md`
- `relaymem_retrieval_execution_design.md`
- `relayemo_return_side_style_adapter_design.md`
- `ai_vtuber_pipeline_profile.md`
- `open_llm_vtuber_integration.md`

## Possible later archive candidates

These documents overlap substantially with newer architecture documents, but still contain unique product rationale that should be migrated before archiving:

- `persona_specialized_proxy_design.md`
  - overlaps `runtime_architecture.md`, `context_packing_design.md`, and RelaySOUL docs,
  - unique material: conversation-stickiness evaluation and persona-product framing.
- `vtuber_memory_proxy_design.md`
  - overlaps `runtime_architecture.md`, `open_llm_vtuber_integration.md`, and `ai_vtuber_pipeline_profile.md`,
  - unique material: concise early product-value and latency-positioning summary.

Do not delete these two until their unique material is either retained intentionally or folded into current product documentation.
