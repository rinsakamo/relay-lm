# RelayLM Documentation

This page is the entry point for RelayLM documentation.

## Start here

- [Current project status](PROJECT_STATUS.md) — current phase, implemented boundaries, and next work
- [Architecture docs](architecture/README.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [MVP summaries and milestone notes](mvp/README.md)
- [Contract docs](contracts/README.md)
- [Smoke and validation docs](smoke/README.md)
- [RelaySOUL design and gate docs](relaysoul/README.md)
- [Config schema](config_schema.md)
- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)

## Current status

Use [Project Status](PROJECT_STATUS.md) for the concise developer-facing view. [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) is authoritative for detailed phase status and sequencing.

## Architecture

Use [Pipeline Responsibility Design](architecture/pipeline_responsibility_design.md) for canonical component ownership and target order.

Use [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) before treating a proposed v1 schema, target pipeline, or future execution gate as current behavior.

Primary entry points:

- [Architecture docs index](architecture/README.md)
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md)
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md)
- [Runtime architecture](architecture/runtime_architecture.md)
- [Runtime operational requirements](architecture/runtime_operational_requirements.md)
- [Context packing design](architecture/context_packing_design.md)
- [Runtime compile gate design](architecture/runtime_compile_gate_design.md)
- [RelayRUN checkpoint design](architecture/relayrun_runtime_checkpoint_design.md)
- [Open-LLM-VTuber integration](architecture/open_llm_vtuber_integration.md)
- [RelayMEM MVP design](architecture/relaymem_mvp_design.md)
- [RelayMEM SLP execution design](architecture/relaymem_slp_execution_design.md)
- [RelayMEM retrieval execution design](architecture/relaymem_retrieval_execution_design.md)

## Historical material

`docs/mvp/` and `docs/architecture/archive/` preserve implementation snapshots and historical rationale. They do not override current architecture, contracts, project status, or implementation sequencing.

## Documentation maintenance

Run after moving or renaming Markdown files:

```bash
python scripts/relaylm_docs_link_check.py
```

Placement:

- current repository status -> `docs/PROJECT_STATUS.md`
- architecture and pipeline design -> `docs/architecture/`
- historical architecture rationale -> `docs/architecture/archive/`
- MVP snapshots -> `docs/mvp/`
- schemas and contracts -> `docs/contracts/`
- validation and manual smoke -> `docs/smoke/`
- RelaySOUL design and execution gates -> `docs/relaysoul/`

## Examples

- [OpenWebUI + LM Studio config](../examples/config/openwebui_lmstudio.yaml)
- [OpenWebUI example profiles](../examples/profiles/)
