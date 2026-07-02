---
relaylm_doc_type: implementation_report
relaylm_authority: p0_relayrel_relayscn_relayemo_ordering_fix
relaylm_status: draft
relaylm_volatility: high
relaylm_owner: implementation
relaylm_update_trigger:
  - RelayREL / RelaySCN / RelayEMO runtime ordering changes
  - scene_state ownership changes
  - PipelineContext node ordering changes
relaylm_not_authoritative_for:
  - exact runtime schemas outside the P0 ordering boundary
  - Character Workspace parser/compiler/UI implementation
  - full RelayREL relationship Markdown parsing
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project_execution_plan.md
  - pipeline_responsibility_design.md
  - relayscn_mvp_scene_policy.md
  - ../relayemo_mvp_initial_design.md
---
# P0 RelayREL / RelaySCN / RelayEMO Ordering Fix

## Purpose

This document records the draft P0 implementation boundary after the file-first Character Workspace design reset.

Before implementing Character Workspace parser/compiler/UI slices, RelayLM needs to remove the legacy scene ownership path where RelayEMO ran before RelaySCN and RelaySCN could fall back to `RelayEMO` artifact `scene_state` as normalized scene state.

## Current draft status

This PR is complete only after the FastAPI request path is actually rewired and the local validation commands pass; helper/projection changes alone are not sufficient.

Implemented in this draft:

```text
RelaySCN no longer accepts RelayEMO artifact scene_state as normalized fallback.
RelayREL has a content-free placeholder/projection for request-path ordering.
Pipeline order projection proves RelayREL -> RelaySCN -> RelayEMO -> RelayINT -> RelayMEM -> RelayCTX.
RelayMEM retrieval smoke coverage consumes RelaySCN policy.
Public diagnostics/projections remain content-free.
```

Still required before this PR can be marked ready:

```text
app.py request path calls RelayREL / RelaySCN before input-side RelayEMO.
app.py no longer passes relayemo_artifact into build_relayscn_scene_policy_artifact.
project_execution_plan.md moves PM-D3/P0 to complete only because app.py is wired and validation passed.
validation passes locally or in CI before ready-for-review.
```

## Target order

The target request path remains:

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

The bounded runtime/helper order used for current P0 smoke evidence is:

```text
relayrel_relationship_projection
  -> relayscn_scene_policy
  -> relayemo_input
  -> relayint
  -> relaymem_retrieval
  -> relayctx_repack
```

## Removed legacy helper fallback

The removed RelaySCN compatibility path was close to:

```text
RelayEMO
  -> RelaySCN v0
  -> RelaySCN may use RelayEMO artifact scene_state as fallback
```

RelaySCN now uses only:

```text
1. explicit RelaySCN/request metadata scene state
2. deterministic lightweight message heuristic
3. fail-closed unknown scene through the heuristic source
```

RelaySCN must not emit `scene_state_source == "relayemo_artifact"`.

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

## What this does not implement

This slice does not implement:

```text
full RelayREL markdown relationship parsing
Character Workspace parser/compiler/UI
Quick Create / Advanced Create UI
one-file-per-memory behavior
Primary MEM lifecycle changes unrelated to pipeline ordering
runtime support for Character Workspace source files
```

The RelayREL implementation in this draft is a content-free placeholder/projection. It exposes only presence/status flags and must not expose raw messages, relationship bodies, memory bodies, scene bodies, private state, or assistant output.

## Validation

Expected validation for this slice:

```text
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_p0_pipeline_ordering_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

The dedicated smoke proves:

```text
build_relayscn_scene_policy_artifact has no public relayemo_artifact parameter
RelaySCN no longer keeps _extract_relayemo_scene_state
RelaySCN rejects relayemo_artifact as an unexpected keyword and does not emit scene_state_source=relayemo_artifact
explicit request metadata still wins
missing metadata uses heuristic/fail-closed behavior
RelayREL precedes RelaySCN in the order projection
RelaySCN precedes input RelayEMO in the order projection
RelayMEM retrieval consumes RelaySCN policy
public order diagnostics remain content-free
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

Therefore this ordering fix is the required predecessor to CW-A1 file-first parser/compiler implementation.
