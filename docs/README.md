# RelayLM Documentation

This page is the entry point for RelayLM documentation.

## Start here

- [Architecture docs](architecture/README.md)
- [MVP summaries and milestone notes](mvp/README.md)
- [Contract docs](contracts/README.md)
- [Smoke and validation docs](smoke/README.md)
- [RelaySOUL design and gate docs](relaysoul/README.md)
- [Config schema](config_schema.md)
- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)

## Architecture

Use these docs to understand the RelayLM pipeline, responsibility boundaries, and profile-specific runtime design.

Canonical precedence and legacy-term handling are defined in the [architecture docs index](architecture/README.md). When documents disagree, `pipeline_responsibility_design.md` is the source of truth for component names and ownership, while `pipeline_implementation_plan.md` is the source of truth for phase status.

- [Architecture docs index](architecture/README.md)
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md) — canonical naming and responsibility source
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — implementation order and phase status
- [Runtime architecture](architecture/runtime_architecture.md)
- [Runtime operational requirements](architecture/runtime_operational_requirements.md)
- [AI character product principles](architecture/ai_character_product_principles.md)
- [AI VTuber pipeline profile](architecture/ai_vtuber_pipeline_profile.md)
- [Open-LLM-VTuber integration](architecture/open_llm_vtuber_integration.md)
- [RelayINT MVP design](architecture/relayint_mvp_design.md)
- [RelayMEM MVP design](architecture/relaymem_mvp_design.md)
- [RelayMEM SLP execution design](architecture/relaymem_slp_execution_design.md)
- [RelayMEM retrieval execution design](architecture/relaymem_retrieval_execution_design.md)
- [RelayEMO return-side style adapter design](architecture/relayemo_return_side_style_adapter_design.md)
- [Historical architecture design archive](architecture/archive/README.md)

## MVP summaries

MVP summaries and MVP-focused implementation notes are collected under `docs/mvp/`.

- [MVP summaries and milestone notes](mvp/README.md)

MVP summaries are historical implementation snapshots. Later architecture and implementation-plan documents may supersede their terminology or current-status statements.

Future MVP summaries should be created directly under `docs/mvp/` and linked from the MVP index.

## Contracts and safety gates

Contract, artifact, schema, approval, and gate docs are collected under `docs/contracts/`.

- [Contract docs](contracts/README.md)

## Setup, smoke, and validation

- [OpenWebUI + LM Studio MVP](openwebui_lmstudio_mvp.md)
- [Smoke and validation docs](smoke/README.md)

## RelaySOUL design and execution gates

- [RelaySOUL design and gate docs](relaysoul/README.md)

## Documentation maintenance

Run the local Markdown-link audit after moving or renaming documentation:

```bash
python scripts/relaylm_docs_link_check.py
```

Placement rules:

- cross-cutting architecture and pipeline docs -> `docs/architecture/`
- historical architecture rationale -> `docs/architecture/archive/`
- MVP summaries and milestone notes -> `docs/mvp/`
- artifact, schema, approval, and contract docs -> `docs/contracts/`
- manual smoke, results, troubleshooting, and local evaluation docs -> `docs/smoke/`
- RelaySOUL design, chain, persistence architecture, and execution-gate docs -> `docs/relaysoul/`
- setup entry points and repository-wide indexes may remain directly under `docs/`

## Examples

- [OpenWebUI + LM Studio copy-ready config](../examples/config/openwebui_lmstudio.yaml)
- [OpenWebUI example profiles](../examples/profiles/)
