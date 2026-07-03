---
relaylm_doc_type: documentation_index
relaylm_authority: relaysoul_documentation_entrypoint
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: relaysoul
relaylm_update_trigger:
  - RelaySOUL documentation entry points change
  - RelaySOUL current or target boundary changes
  - experimental RelaySOUL work is added or removed
relaylm_not_authoritative_for:
  - current runtime behavior
  - exact schema details
  - implementation phase completion claims
relaylm_current_status_source: ../PROJECT_STATUS.md
---
# RelaySOUL Design and Gate Docs

This directory indexes RelaySOUL persona-source calibration, update cadence, dry-run/preflight chains, persistence design, execution-gate documentation, and explicitly post-MVP experimental SOUL replacement work.

RelaySOUL artifact schemas and content-free contracts remain under `docs/contracts/`. MVP milestone summaries remain under `docs/mvp/`.

The RelaySOUL design, cadence, chain, persistence architecture, execution-gate, and experimental replacement documents tracked by this index are housed in this directory.

## Current and target boundary

Use the [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md) together with the documents below.

Current compatibility behavior is the `mvp-soul-0` dry-run/preflight chain. It retains the older compatibility allowlist and does not perform actual apply, rollback, or persistence execution.

The file-first workspace target supersedes the older three-file persona target. Durable portable RelaySOUL-owned character sources are now `SOUL.md`, `STYLE.md`, `EMOTION.md`, `BOUNDARY.md`, and optional `LORE.md`. `RELATIONSHIP.md` and `relationships/<target>.md` are RelayREL-owned relationship sources; `SCENE.md` and `scenes/*.md` are RelaySCN-owned scene sources; `MEMORY.md` and `memory/**/*.md` are RelayMEM / RelaySLP-owned memory sources.

The target migration must update patch, revision, approval, apply, rollback, storage, examples, and smoke tests atomically. A file-first target statement does not change the current `mvp-soul-0` wire contract by itself.

## Core design

- [RelaySOUL persona source calibration design](relaysoul_design.md)
- [RelaySOUL persona update cadence design](persona_update_cadence_design.md)
- [RelaySOUL persistence storage design](relaysoul_persistence_storage_design.md)

## Post-MVP experimental design

- [Experimental SOUL Replacement and Memory Bootstrap Design](experimental_soul_replacement_memory_bootstrap_design.md) — future high-risk non-destructive SOUL fork, SLP-governed memory inheritance, optional provisional virtual memory from conversation history, fresh relationship state, and explicit rollback. This is not part of the MVP or ordinary same-character SOUL revision.

## Chain summaries

- [RelaySOUL dry-run chain summary](relaysoul_dry_run_chain_summary.md)
- [RelaySOUL preflight chain summary](relaysoul_preflight_chain_summary.md)
- [RelaySOUL persistence preflight summary](relaysoul_persistence_preflight_summary.md)

## Execution gate designs

- [RelaySOUL apply execution gate design](relaysoul_apply_execution_gate_design.md)
- [RelaySOUL rollback execution gate design](relaysoul_rollback_execution_gate_design.md)
- [RelaySOUL storage writer gate design](relaysoul_storage_writer_gate_design.md)
- [RelaySOUL persistence execution gate design](relaysoul_persistence_execution_gate_design.md)
- [RelaySOUL gate design consistency review](relaysoul_gate_design_consistency_review.md)
- [RelaySOUL gate dry-run CLI design](relaysoul_gate_dry_run_cli_design.md)

## Related contracts

- [RelayLM contract docs](../contracts/README.md)

## Placement rule

Create RelaySOUL design, cadence, chain, persistence architecture, execution-gate, and experimental replacement docs directly under `docs/relaysoul/`. Keep schemas and artifact contracts under `docs/contracts/`.
