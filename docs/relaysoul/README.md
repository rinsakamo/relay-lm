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

This directory is an empty transitional collection. D6-R29 disposed the remaining RelaySOUL update-cadence and post-MVP experimental SOUL replacement child sources, so no design source remains here and this README only routes readers to their canonical owners.

Durable RelaySOUL portable identity and source-authority architecture is not housed here. It lives at [Character Identity and Source Authority](../architecture/character/identity-and-source-authority.md). Durable personality state and update-speed architecture lives at [Character Personality and Experience](../architecture/character/personality-and-experience.md). Exact execution-gate and artifact-persistence authority lives under `docs/contracts/`.

RelaySOUL artifact schemas and content-free contracts remain under `docs/contracts/`. Implementation evidence remains under `docs/evidence/implementation/`.

## Current and target boundary

Use the [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md) together with the documents below.

Current compatibility behavior is the `mvp-soul-0` dry-run/preflight chain. It retains the older compatibility allowlist and does not perform actual apply, rollback, or persistence execution.

The file-first workspace target supersedes the older three-file persona target. Durable portable RelaySOUL-owned character sources are now `SOUL.md`, `STYLE.md`, `EMOTION.md`, `BOUNDARY.md`, and optional `LORE.md`. `RELATIONSHIP.md` and `relationships/<target>.md` are RelayREL-owned relationship sources; `SCENE.md` and `scenes/*.md` are RelaySCN-owned scene sources; `MEMORY.md` and `memory/**/*.md` are RelayMEM / RelaySLP-owned memory sources.

The target migration must update patch, revision, approval, apply, rollback, storage, examples, and smoke tests atomically. A file-first target statement does not change the current `mvp-soul-0` wire contract by itself.

## Core design

- [Character Identity and Source Authority](../architecture/character/identity-and-source-authority.md) — canonical durable portable identity, source-authority, and calibration boundary
- [Character Personality and Experience](../architecture/character/personality-and-experience.md) — canonical durable personality-state and update-speed boundary, including which state RelaySLP may update automatically

## Execution, gate, and persistence authority

Durable execution-gate and artifact-persistence authority is not housed in this collection.

- [RelaySOUL Execution Gate Contract](../contracts/relaysoul-execution-gates.md) — target gate scopes, decision artifacts, allowed flags, and dependency ordering for apply, rollback, storage writer, and persistence execution
- [RelaySOUL Artifact Persistence Contract](../contracts/relaysoul_persistence_contract.md) — current content-free artifact storage readiness and the target storage model
- [RelaySOUL Explicit Approval Artifact Contract](../contracts/relaysoul_explicit_approval_artifact_contract.md) — exact approval artifact shape and gate-scoped approval checks
- [RelaySOUL Preflight Lineage Freshness Policy](../contracts/relaysoul_preflight_lineage_freshness_policy.md) — exact lineage fields, freshness checks, and stale conditions

No gate decision runtime, gate CLI, or actual apply, rollback, or persistence writer is implemented.

## Showcase character sources and related policy

No showcase source set is published from this collection. A documented source-set candidate is not a registered workspace, an active character, or portable source authority; that rule belongs to the canonical identity authority above.

- [Showcase, Public Starter, and Product Knowledge Ownership](../architecture/character-workspace/showcase-starter-product-knowledge.md) — target ownership split between developer showcase characters, the unnamed public starter, user-authored characters, and versioned RelayLM product-help knowledge.
- [Rin / ReLM Showcase Character Direction](../architecture/character/showcase-character-direction.md) — non-runtime maker-side creative direction for the developer-owned showcase pair; asset and public-lineage ownership remains with the showcase ownership policy.

## Post-MVP experimental design

No post-MVP experimental design source is published from this collection. D6-R29 retired the former experimental SOUL replacement and memory bootstrap source to Git history rather than promoting it to an independent current architecture: its general source, lifecycle, memory-exclusion, and disclosure principles are already owned by the canonical identity, memory-mutation, and privacy authorities, and its unimplemented replacement-branch, virtual-memory bootstrap, and staged planning content is future design with no current owner. Its exact recovery identity is in the central retirement manifest.

## Completed chain and gate review evidence

The RelaySOUL dry-run chain, preflight chain, persistence preflight, and gate design consistency review are completed records. They are retained as frozen bounded evidence under [Implementation Evidence](../evidence/implementation/README.md) and are not current authority. Current gate, persistence, and identity semantics are the canonical owners linked above.

## Related contracts

- [RelayLM contract docs](../contracts/README.md)

## Placement rule

`docs/relaysoul/` is not a permanent destination. Do not create new durable RelaySOUL architecture here: durable portable identity and source-authority content belongs to [Character Identity and Source Authority](../architecture/character/identity-and-source-authority.md), durable personality-state and update-speed content belongs to [Character Personality and Experience](../architecture/character/personality-and-experience.md), schemas and artifact contracts belong under `docs/contracts/`, and implementation evidence belongs under `docs/evidence/implementation/`.

No child design source remains in `docs/relaysoul/`. This README survives only as a transitional router, and D6-R30 owns retiring it and removing the emptied collection.
