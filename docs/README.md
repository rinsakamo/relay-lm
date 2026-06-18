# RelayLM Documentation

This page is the entry point for RelayLM documentation.

## Start here

- [Current project status](PROJECT_STATUS.md) — concise current boundary and next choices
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — detailed status and sequencing
- [Phase 5-C4a completed handoff](architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Architecture docs](architecture/README.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Contract docs](contracts/README.md)
- [Smoke and validation docs](smoke/README.md)
- [MVP summaries and milestone notes](mvp/README.md)
- [RelaySOUL design and gate docs](relaysoul/README.md)
- [Config schema](config_schema.md)
- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)

## Current status

The repository-wide documentation audit, audit Phases 1–8, is complete as of 2026-06-17 JST. That numbering is independent of runtime implementation phases.

Phase 5-C4a instruction-bearing managed apply is implemented. Current instruction evidence for v1 actual apply is selected through explicit `client_instruction_source.v1` provenance; frontend summaries and memory notes are not inferred as instruction merely from role or position.

Use [Project Status](PROJECT_STATUS.md) for the current developer-facing view and [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) for later sequencing. The Phase 5-C4a handoff is now a completed implementation record, not the one active slice.

Use [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) before treating proposed schemas, future execution gates, or historical compatibility artifacts as current behavior.

## Canonical precedence

When documents disagree:

1. `pipeline_responsibility_design.md` owns component names, responsibility, and target order.
2. `pipeline_implementation_plan.md` owns implementation status and sequencing.
3. Dedicated current contracts own implemented schemas and bounded behavior.
4. `current_target_migration_guide.md` owns compatibility/target interpretation.
5. `docs/mvp/` and `docs/architecture/archive/` are historical evidence.

## Primary architecture entry points

- [Architecture docs index](architecture/README.md)
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md)
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md)
- [Phase 5-C4a completed handoff](architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client history authority contract](architecture/client_history_authority_contract.md)
- [Client instruction authority contract](architecture/client_instruction_authority_contract.md)
- [Runtime architecture](architecture/runtime_architecture.md)
- [Runtime operational requirements](architecture/runtime_operational_requirements.md)
- [Runtime compile gate design](architecture/runtime_compile_gate_design.md)
- [Managed-route fallback authority contract](architecture/managed_route_fallback_contract.md)
- [RelayRUN runtime checkpoint design](architecture/relayrun_runtime_checkpoint_design.md)
- [Context packing design](architecture/context_packing_design.md)
- [Scene lifecycle design](architecture/scene_lifecycle_design.md)
- [AI VTuber pipeline profile](architecture/ai_vtuber_pipeline_profile.md)
- [RelayINT MVP design](architecture/relayint_mvp_design.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)

## Contracts and safety gates

Contract, artifact, schema, approval, and gate documents are collected under `docs/contracts/`.

Current compile behavior includes the typed `CompileApplyDecision`, the content-free `mvp-ctx-apply-0` diagnostics artifact, and bounded history-exclusion apply contracts v0/v1. Complete Runtime Compile Gate v1 remains target work.

## MVP and historical material

`docs/mvp/` contains historical implementation snapshots. `docs/architecture/archive/` preserves superseded architecture rationale. Neither overrides current architecture, contracts, project status, or implementation sequencing.

## Setup, smoke, and validation

- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)
- [Smoke and validation docs](smoke/README.md)
- [OpenWebUI + RelayLM troubleshooting](smoke/openwebui_lmstudio_troubleshooting.md)

## Documentation maintenance

Run the Markdown-link audit after moving, renaming, or adding links:

```bash
python scripts/relaylm_docs_link_check.py
```

Placement rules:

- repository-wide current status -> `docs/PROJECT_STATUS.md`
- completed or active bounded implementation handoffs -> `docs/architecture/`
- cross-cutting architecture and pipeline docs -> `docs/architecture/`
- historical architecture rationale -> `docs/architecture/archive/`
- MVP snapshots -> `docs/mvp/`
- schemas and contracts -> `docs/contracts/`
- smoke, troubleshooting, and evaluation docs -> `docs/smoke/`
- RelaySOUL governance docs -> `docs/relaysoul/`

Before removing detail from an active document, preserve unique design intent in the appropriate current owner.
