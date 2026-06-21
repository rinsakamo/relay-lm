---
relaylm_doc_type: documentation_index
relaylm_authority: repository_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: documentation
relaylm_update_trigger:
  - documentation entry points change
  - canonical authority ordering changes
  - placement rules change
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact schema details
  - implementation phase completion claims
relaylm_current_status_source: PROJECT_STATUS.md
---
# RelayLM Documentation

This page is the entry point for RelayLM documentation.

RelayLM documentation is AI-first: documents should be understandable when retrieved partially by ChatGPT, Codex, or another assistant. Use [Documentation Model](DOCUMENTATION_MODEL.md) for document types, metadata, status labels, and authority rules.

## Start here

- [Current project status](PROJECT_STATUS.md) — concise current boundary and next choices
- [Documentation model](DOCUMENTATION_MODEL.md) — AI-first document types, metadata, and authority labels
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md) — detailed status and sequencing
- [Phase 6 Asynchronous RelaySLP bounded slice](architecture/phase6_async_relayslp_bounded_slice.md) — current Core orchestration track, complete through A2 helpers and B0 design
- [RelayMEM MVP implementation plan](architecture/relaymem_mvp_implementation_plan.md) — independent memory track, complete through M3f preflight
- [SOUL Lab UI-A3 Communication handoff](architecture/soul_lab_ui_a3_communication_handoff.md) — current UI track through browser-local mock Communication
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

Use [Project Status](PROJECT_STATUS.md) for the current developer-facing view and [Pipeline Implementation Plan](architecture/pipeline_implementation_plan.md) for later sequencing.

Phase 5.5 Stream Unpack / TTS handoff preparation is complete for RelayLM Core. Concrete TTS execution, audio queueing, adapter delivery, Live2D/avatar mapping, motion, and lip-sync remain SOUL Lab Runtime MVP responsibilities.

Current work is split across independent tracks. RelayLM Core is complete through Phase 6-A2 helpers and the Phase 6-B0 durable-queue design; B1 is next. RelayMEM has implemented its Primary MEM path through M3f read-only index/log reconciliation planning; M3g apply is next. SOUL Lab UI is implemented through UI-A3; UI-A4 Pod / SOUL Intervention is next. Concrete TTS/audio/avatar execution remains SOUL Lab Runtime work.

Use [Current / Target / Migration Guide](architecture/current_target_migration_guide.md) before treating proposed schemas, future execution gates, or historical compatibility artifacts as current behavior.

Use [Documentation Model](DOCUMENTATION_MODEL.md) before adding new docs or deciding whether a document is status, stable architecture, implementation planning, contract, smoke/how-to, handoff, ADR, or historical evidence.

## Canonical precedence

When documents disagree:

1. `pipeline_responsibility_design.md` owns component names, responsibility, and target order.
2. `pipeline_implementation_plan.md` owns implementation status and sequencing.
3. Dedicated current contracts own implemented schemas and bounded behavior.
4. `current_target_migration_guide.md` owns compatibility/target interpretation.
5. `docs/mvp/` and `docs/architecture/archive/` are historical evidence.

`DOCUMENTATION_MODEL.md` owns document type metadata and AI reading rules; it does not override the content authority list above.

## Primary architecture entry points

- [Architecture docs index](architecture/README.md)
- [Pipeline responsibility design](architecture/pipeline_responsibility_design.md)
- [Pipeline implementation plan](architecture/pipeline_implementation_plan.md)
- [Phase 6 Asynchronous RelaySLP bounded slice](architecture/phase6_async_relayslp_bounded_slice.md)
- [Completed Phase 5.5 Stream Unpack bounded slice](architecture/phase5_5_stream_unpack_bounded_slice.md)
- [Current / Target / Migration Guide](architecture/current_target_migration_guide.md)
- [Client history authority contract](architecture/client_history_authority_contract.md)
- [Client instruction authority contract](architecture/client_instruction_authority_contract.md)
- [Runtime architecture](architecture/runtime_architecture.md)
- [Runtime operational requirements](architecture/runtime_operational_requirements.md)
- [Runtime compile gate design](architecture/runtime_compile_gate_design.md)
- [Managed-route fallback authority contract](architecture/managed_route_fallback_contract.md)
- [RelayRUN runtime checkpoint design](architecture/relayrun_runtime_checkpoint_design.md)
- [Context packing design](architecture/context_packing_design.md)
- [Memory lifecycle design](architecture/memory_lifecycle_design.md)
- [RelayMEM / RelaySLP current / target boundary](architecture/relaymem_slp_current_target.md)
- [RelayMEM MVP implementation plan](architecture/relaymem_mvp_implementation_plan.md)
- [RelayMEM SLP execution design](architecture/relaymem_slp_execution_design.md)
- [RelayMEM-M3d Primary writer handoff](architecture/relaymem_m3d_primary_writer_handoff.md)
- [RelayMEM-M3e Atomic Primary page writer](architecture/relaymem_m3e_atomic_primary_page_writer.md)
- [RelayMEM-M3f Index/log reconciliation preflight](architecture/relaymem_m3f_primary_index_log_reconciliation_preflight.md)
- [Scene lifecycle design](architecture/scene_lifecycle_design.md)
- [AI VTuber pipeline profile](architecture/ai_vtuber_pipeline_profile.md)
- [SOUL Lab UI MVP](architecture/soul_lab_ui_mvp.md)
- [SOUL Lab UI-A0 / UI-A1 handoff](architecture/soul_lab_ui_a0_a1_handoff.md)
- [SOUL Lab UI-A2 Adoption handoff](architecture/soul_lab_ui_a2_adoption_handoff.md)
- [SOUL Lab UI-A3 Communication handoff](architecture/soul_lab_ui_a3_communication_handoff.md)
- [SOUL Lab Runtime MVP](architecture/soul_lab_runtime_mvp.md)
- [RelayINT MVP design](architecture/relayint_mvp_design.md)

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

AI-first maintenance rules:

- add front matter to active current/architecture/plan/contract docs when practical,
- include document type, authority, status, volatility, owner, update trigger, and non-authority fields,
- keep current/target/compatibility/historical/frozen status explicit,
- do not encode source text, prompts, traces, cache bodies, or runtime-private data in metadata.

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
