# Historical Architecture Design Archive

This directory contains design documents that preserve useful RelayLM design history but no longer define current component ownership or implementation status.

## Status rule

Documents in this directory are **non-canonical historical references**.

Use these documents as the current sources of truth:

1. [Pipeline Responsibilities](../pipeline-responsibilities.md) for component names, pipeline order, and responsibility boundaries.
2. [Pipeline implementation plan](../pipeline_implementation_plan.md) for implementation sequencing and current phase status.
3. Current module and contract documents for schema and behavior details.

Historical documents must not override those sources.

## Compatibility redirect boundary

Short redirect files may remain at former active paths to preserve historical or external links. Those redirects are not active architecture documents. Current documents must link directly to canonical current files rather than through a redirect chain.

The active architecture index lists the retained redirect paths separately from current specifications.

## Archived responsibility-split designs

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

## Archived implementation-history markers

These markers record where append-only design histories were superseded by concise active contracts. The original long-form bodies remain available in Git history.

## Reviewed and retained as active documents

The following documents contain distinct current contracts and remain in the active architecture index:

- `context_packing_design.md`
- `relaymem_mvp_design.md`
- `relaymem_slp_execution_design.md`
- `relaymem_retrieval_execution_design.md`
- `relayemo_return_side_expression_design.md`
- `ai_vtuber_pipeline_profile.md`
- `open_llm_vtuber_integration.md`

The previous consolidation pass did not declare additional archive candidates. Root-level compatibility redirects, newly revised documents, and future additions remain subject to later structure and current-versus-target audits before the archive boundary is considered final.
