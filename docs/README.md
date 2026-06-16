# RelayLM Documentation

This page is the entry point for RelayLM documentation.

## Start here

- [Current project status](PROJECT_STATUS.md) — one-page current phase, implemented boundaries, and next work
- [Architecture docs](architecture/README.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [MVP summaries and milestone notes](mvp/README.md)
- [Contract docs](contracts/README.md)
- [Smoke and validation docs](smoke/README.md)
- [RelaySOUL design and gate docs](relaysoul/README.md)
- [Config schema](config_schema.md)
- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)

## Current status

Use [Project Status](PROJECT_STATUS.md) as the concise developer-facing view of:

- the current phase,
- implemented versus dry-run/preflight/read-only/runtime-private boundaries,
- currently usable runtime paths,
- major unimplemented components,
- current defaults and apply posture,
- and the immediate next implementation slice.

`PROJECT_STATUS.md` is a summary view. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) remains authoritative for detailed phase status, dependencies, and sequencing.

Use [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) before treating a proposed v1 schema, target pipeline, future execution gate, or historical compatibility artifact as current behavior.

## Architecture

Use these docs to understand the RelayLM pipeline, responsibility boundaries, runtime reliability, context/memory design, and profile-specific integration.

Canonical precedence and legacy-term handling are defined in the [architecture docs index](architecture/README.md). When documents disagree:

- `pipeline_responsibility_design.md` is the source of truth for component names and ownership,
- `pipeline_implementation_plan.md` is the source of truth for implementation phase status,
- dedicated current contracts are the source of truth for implemented schemas and bounded behavior,
- `current_target_migration_guide.md` defines how target and compatibility material must be read.

Primary architecture entry points:

- [Architecture docs index](architecture/README.md)
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md) — canonical naming and responsibility source
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — implementation order, dependencies, and phase status
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Runtime architecture](architecture/runtime_architecture.md)
- [Runtime operational requirements](architecture/runtime_operational_requirements.md)
- [Runtime compile gate design](architecture/runtime_compile_gate_design.md)
- [Managed-route fallback authority contract](architecture/managed_route_fallback_contract.md)
- [RelayRUN runtime checkpoint design](architecture/relayrun_runtime_checkpoint_design.md)
- [Context packing design](architecture/context_packing_design.md)
- [Safe SOUL / Scene / CTX compile chain](architecture/safe_soul_scene_ctx_compile_chain.md)
- [Scene lifecycle design](architecture/scene_lifecycle_design.md)
- [Scene-aware memory scope current / target boundary](architecture/scene_memory_scope_current_target.md)
- [Scene-aware memory scope detailed design](architecture/scene_memory_scope_design.md)
- [AI character product principles](architecture/ai_character_product_principles.md)
- [AI VTuber pipeline profile](architecture/ai_vtuber_pipeline_profile.md)
- [Open-LLM-VTuber current / target boundary](architecture/open_llm_vtuber_current_target.md)
- [Open-LLM-VTuber detailed integration design](architecture/open_llm_vtuber_integration.md)
- [RelayINT MVP design](architecture/relayint_mvp_design.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM MVP detailed design](architecture/relaymem_mvp_design.md)
- [RelayMEM retrieval execution design](architecture/relaymem_retrieval_execution_design.md)
- [RelayMEM SLP detailed execution design](architecture/relaymem_slp_execution_design.md)
- [RelayEMO return-side expression design](architecture/relayemo_return_side_expression_design.md)
- [Historical architecture design archive](architecture/archive/README.md)

## Contracts and safety gates

Contract, artifact, schema, approval, and gate documents are collected under `docs/contracts/`.

- [Contract docs](contracts/README.md)
- [Runtime compile current / target boundary](contracts/runtime_compile_current_target.md)
- [Runtime compile artifact contract](contracts/runtime_compile_artifact_contract.md)
- [RelayRUN recovery response generator current / target boundary](contracts/relayrun_recovery_response_generator_current_target.md)

Current compile behavior includes both the typed `CompileApplyDecision` and the separate content-free `mvp-ctx-apply-0` diagnostics artifact. Proposed authority-aware v1 projections remain target contracts.

## MVP summaries

MVP summaries and MVP-focused implementation notes are collected under `docs/mvp/`.

- [MVP summaries and milestone notes](mvp/README.md)

MVP summaries are historical implementation snapshots. Later architecture, contract, implementation-plan, and project-status documents may supersede their terminology or current-status statements.

Future MVP summaries should be created directly under `docs/mvp/` and linked from the MVP index.

## Setup, smoke, and validation

- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)
- [Smoke and validation docs](smoke/README.md)

## RelaySOUL design and execution gates

- [RelaySOUL design and gate docs](relaysoul/README.md)

The current `mvp-soul-0` five-file chain is compatibility behavior. The target durable ownership boundary is narrower, and actual apply, rollback, and persistence execution remain disabled.

## Historical material

`docs/mvp/` and `docs/architecture/archive/` preserve implementation snapshots and historical rationale. They do not override current architecture, contracts, project status, or implementation sequencing.

Compatibility redirect files preserve old paths only. Current documents should link directly to canonical files rather than through redirects.

## Documentation maintenance

Run the local Markdown-link audit after moving, renaming, or adding documentation links:

```bash
python scripts/relaylm_docs_link_check.py
```

Placement rules:

- one-page repository-wide current status -> `docs/PROJECT_STATUS.md`
- cross-cutting architecture and pipeline docs -> `docs/architecture/`
- historical architecture rationale -> `docs/architecture/archive/`
- MVP summaries and milestone notes -> `docs/mvp/`
- artifact, schema, approval, and contract docs -> `docs/contracts/`
- manual smoke, results, troubleshooting, and local evaluation docs -> `docs/smoke/`
- RelaySOUL design, chain, persistence architecture, and execution-gate docs -> `docs/relaysoul/`
- setup entry points and repository-wide indexes may remain directly under `docs/`

Before removing detail from an active document, preserve unique design intent in the appropriate current owner document. Current/Target clarification should normally be added as labels or a boundary summary rather than by deleting operational requirements or migration detail.

## Examples

- [OpenWebUI + LM Studio copy-ready config](../examples/config/openwebui_lmstudio.yaml)
- [OpenWebUI example profiles](../examples/profiles/)
