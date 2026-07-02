---
relaylm_doc_type: implementation_plan
relaylm_authority: p0_relayrel_relayscn_relayemo_ordering_fix
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: implementation
relaylm_update_trigger:
  - RelayREL / RelaySCN / RelayEMO runtime ordering changes
  - scene_state ownership changes
  - PipelineContext node ordering changes
relaylm_not_authoritative_for:
  - current implementation status
  - exact runtime schemas
  - exact smoke implementation details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project_execution_plan.md
  - pipeline_responsibility_design.md
  - relayscn_mvp_scene_policy.md
  - ../relayemo_mvp_initial_design.md
---
# P0 RelayREL / RelaySCN / RelayEMO Ordering Fix

## Purpose

This document records the first implementation priority after the file-first Character Workspace design reset.

Before implementing Character Workspace parser/compiler/UI slices, RelayLM must remove the legacy scene ownership path where RelayEMO runs before RelaySCN and RelaySCN falls back to `RelayEMO` artifact `scene_state` as normalized scene state.

## Target order

The target request path is:

```text
RelayREL
  -> input-side RelaySCN
  -> input-side RelayEMO
  -> RelayINT
  -> RelayMEM Retrieval
  -> RelayCTX Repack
  -> backend LLM
  -> RelayCTX Unpack
  -> RelayREF
  -> return-side RelayEMO
  -> output-side RelaySCN
```

## Current legacy to remove

The current compatibility path is close to:

```text
RelayEMO
  -> RelaySCN v0
  -> RelaySCN may use RelayEMO artifact scene_state as fallback
```

That compatibility path must be removed from the target implementation.

## Ownership correction

```text
RelayREL
  owns target relationship selection and relationship-conditioned interaction policy.

RelaySCN
  owns normalized scene_state and scene_policy.

RelayEMO
  owns affect estimates, expression pressure, assistant expression state, and return-side expression hints.
```

RelayEMO may provide bounded affect-related evidence hints for later scene classification cycles, but it must not provide normalized `scene_state` for same-turn policy ownership.

## Implementation scope

```text
1. Add or update PipelineContext node ordering so RelayREL runs before input-side RelaySCN.
2. Run input-side RelaySCN before input-side RelayEMO.
3. Remove RelaySCN fallback to RelayEMO artifact scene_state for normalized scene ownership.
4. Replace any required dependency with bounded RelayEMO affect evidence hints for later/future cycles only.
5. Ensure RelayINT, RelayMEM Retrieval, and RelayCTX consume RelaySCN scene_policy, not RelayEMO scene fallback.
6. Keep content-free projections typed and bounded.
7. Update RelaySCN, RelayEMO, RelayMEM retrieval, RelayCTX, and integration smokes.
```

## Done when

```text
RelayEMO no longer owns normalized scene_state.
RelaySCN no longer accepts RelayEMO artifact scene_state as normalized fallback.
RelayREL precedes RelaySCN in the request path.
RelaySCN precedes RelayEMO in the request path.
RelayMEM retrieval gates use RelaySCN policy.
RelayCTX receives scene state/policy from RelaySCN and expression hints from RelayEMO.
Public diagnostics remain content-free.
Smokes prove the corrected order and the absence of the legacy fallback.
```

## Why this is P0

Character Workspace implementation depends on stable ownership boundaries:

```text
SCENE.md / scenes/*.md
  require RelaySCN to own scene policy.

EMOTION.md / .relaylm/state/emotion_state
  require RelayEMO to own expression state, not scene ownership.

RELATIONSHIP.md / relationships/<target>.md
  require RelayREL to condition scene, expression, memory, and CTX before scene selection.

memory/**/*.md / RelayMEM Retrieval
  require retrieval gates from RelaySCN policy, not RelayEMO compatibility artifacts.

RelayCTX
  requires a single canonical source for scene policy before backend-bound context assembly.
```

Therefore this ordering fix must be scheduled before CW-A1 file-first parser/compiler implementation.
