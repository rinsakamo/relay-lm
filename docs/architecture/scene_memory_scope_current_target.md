---
relaylm_doc_type: current_target_migration
relaylm_authority: scene_memory_scope_current_target
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - route character or memory namespace semantics change
  - RelaySCN or RelayINT retrieval-scope inputs change
  - Primary or Subjective retrieval scope validation changes
  - scene/session/room-aware candidate ranking is implemented
  - RT-1D-R5 or R6 retirement disposition changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status or sequencing
  - exact RT-1 reader or writer cutover state
  - target scene-aware ranking semantics
  - lifecycle mutation or memory-write authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - scene_memory_scope_design.md
  - relaymem_retrieval_execution_design.md
  - subjective-mem-retrieval-projection-hard-cutover.md
  - relaymem_slp_current_target.md
  - ../PROJECT_STATUS.md
---
# Scene-aware Memory Scope Current / Target Boundary

Last reviewed: 2026-08-08 JST

## Current implemented

Current ordinary Retrieval has a narrower scope boundary than the full target scene-aware design. The implemented runtime already enforces route, character, namespace, and verified-source boundaries, but it does **not** yet implement the complete character/user/relationship/scene/session/room candidate schema or a general scene-aware ranking policy.

The exact RT-1 reader decision is resolved before any ordinary memory family is touched:

```text
primary_only
  -> retained Primary compatibility retrieval within its existing character/namespace scope

neither
  -> no ordinary durable-memory retrieval

subjective_only
  -> finalized Subjective retrieval bound to its verified character/source/generation scope
  -> no Primary scope discovery or fallback
```

Scene/scope metadata cannot override that reader decision or create a second ordinary reader.

### Character boundary

`ResolvedRoute.character_id` is a live routing boundary for both retained Primary compatibility and finalized Subjective retrieval.

- the Primary branch resolves the character-scoped store root only after exact `primary_only` authorization;
- the Subjective branch acquires and verifies the live projection for the route character before selection;
- character disagreement or unavailable scope fails closed rather than broadening retrieval.

Character identity used for retrieval comes from the resolved route/runtime authority, not from free-text guessing.

### Memory namespace boundary

The retained Primary compatibility branch passes the route `memory_namespace` as `expected_namespace` into canonical Primary recall. Invalid or unavailable namespace state blocks that scoped recall path; it is not permission for a wider scan.

The current Subjective branch is storage-neutral at the RT-1 contract level and binds its request to the verified workspace authority, admitted-scope binding, projection generation, manifest, and route character. It does not infer a broader namespace from query text or from the presence of a Primary store.

### RelaySCN / RelayINT boundary

RelaySCN scene policy and RelayINT intent are current inputs to the Retrieval stage. They may narrow or block retrieval behavior **inside the authority already selected by RT-1**, but neither is reader authority.

```text
exact RT-1 reader decision
  -> selected authority only
  -> RelaySCN / RelayINT scope and request gates
  -> bounded retrieval inside that authority
```

A scene policy, intent artifact, missing candidate, or empty result cannot switch `subjective_only` to Primary, combine families, or make `neither` read memory.

### Current privacy / diagnostic boundary

Request-local retrieval state may contain runtime-private or content-bearing evidence. Generic persisted diagnostics must not expose raw memory text, exact private identifiers, local paths, query bodies, snippets, protected source bodies, or arbitrary nested runtime artifacts.

Content-free projections may expose bounded counts, enum/reason classes, boolean scope/fence facts, and other explicitly allowlisted diagnostics. Exact namespace values and content-bearing evidence remain protected unless an owning developer-only boundary explicitly permits them.

## Current non-capabilities

The current runtime does not establish the full target scene-aware memory model merely because route and scene metadata exist. In particular, this page does not claim current implementation of:

- general relationship-target-aware memory ranking;
- general `scene_id`-aware memory ranking;
- session-memory or room-memory candidate stores;
- scene/session/room promotion or carryover rules;
- a complete `relaymem.memory_scope_projection.v1` producer;
- broad user/relationship identity discovery from free text;
- a unified character/user/relationship/scene/session/room candidate schema;
- memory writes from Retrieval or compile artifacts.

Those remain target or future extensions unless and until their owning runtime authorities land and are validated.

## Target architecture

The detailed target remains [Scene-aware Memory Scope Design](scene_memory_scope_design.md). It defines how these dimensions may eventually influence candidate filtering/ranking without conflating them with write authority:

```text
character_id
user_id / user_type
relationship_target_id
scene_id
session_id
room_id
memory_namespace
```

Target principles remain:

- route/authenticated authority supplies identity and relationship scope rather than free-text guessing;
- `memory_namespace` remains an explicit partitioning boundary;
- scene/session/room metadata may narrow or rank candidates but does not authorize persistence;
- missing optional scene/session/room dimensions should degrade conservatively rather than broaden authority;
- RelayMEM proposes/returns bounded evidence while RelayCTX owns final packing;
- Retrieval remains read-only;
- memory/source mutation remains behind its owning RelaySLP/lifecycle/approval gates.

The target document is authoritative for those future semantics. This current/target page only records which subset is implemented now.

## RT-1D-R5 / R6 boundary

Current Project Status records RT-1D-R4 activation/P8 complete and R5 immediate retirement unstarted. Therefore the current scope picture still includes a retained `primary_only` compatibility reader as well as the finalized `subjective_only` branch.

R5/R6 may remove Primary ordinary-reader/fallback surfaces after exact dependency characterization. That retirement must not be implemented by broadening Subjective scope, weakening exact character/source/generation checks, adding cross-authority fallback, or treating scene/namespace metadata as replacement serving authority.

This document does not authorize Primary deletion or decide which explicitly read-only historical/operational Primary scope consumers survive retirement.

## Validation boundary

Current validation should continue to prove:

- exact RT-1 reader selection before memory-family access;
- no Primary root/scope discovery in `neither` or `subjective_only`;
- exact route character binding for ordinary retrieval;
- exact Primary namespace validation while the `primary_only` branch exists;
- exact Subjective workspace/scope/generation/source binding before release;
- no cross-authority fallback on empty/refused/failed retrieval;
- content-free persisted diagnostics and protected runtime-private evidence;
- no memory mutation from Retrieval/scene-scope metadata.

The workflow/test registry remains the command authority; this page is not a second CI registry.

## Required migration

Remaining migration is intentionally split rather than presented as one broad Retrieval rewrite:

1. RT-1D-R5/R6 retires replaced Primary serving/fallback surfaces under its own authority.
2. Any future scene/relationship/session/room-aware ranking implements the target design through separately reviewed runtime/schema slices.
3. A future typed scope projection, if accepted, must remain content-free and must not become serving or write authority.
4. RelayCTX consumers may evolve with those accepted scope contracts without merging memory families or moving lifecycle authority into context packing.

## Summary

```text
current
  exact RT-1 reader decision first
  -> character-bound ordinary retrieval
  -> Primary compatibility additionally requires exact namespace
  -> Subjective requires verified workspace/scope/generation/source binding
  -> RelaySCN / RelayINT may narrow the selected authority
  -> no dual serving or cross-authority fallback

target
  add explicitly governed relationship/scene/session/room candidate scoping/ranking
  without turning metadata into read/write authority
```

See [Scene-aware Memory Scope Design](scene_memory_scope_design.md) for the target model and [RelayMEM Retrieval Execution Design](relaymem_retrieval_execution_design.md) for the current ordinary routing boundary.
