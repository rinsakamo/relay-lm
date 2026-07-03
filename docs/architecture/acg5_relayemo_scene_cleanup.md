---
relaylm_doc_type: implementation_report
relaylm_authority: acg5_relayemo_scene_cleanup
relaylm_status: current
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - RelayEMO scene hint ownership changes
  - RelaySCN scene policy ownership changes
  - analyzer candidate governance authority changes
relaylm_not_authoritative_for:
  - ACG-6 SCN scene-wiki classifier implementation
  - RelayMEM retrieval query normalization
  - Grounded Recall detail migration
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - analyzer_candidate_governance.md
  - project_execution_plan.md
  - pipeline_responsibility_design.md
  - p0_relayrel_relayscn_relayemo_ordering_fix.md
---
# ACG-5 RelayEMO Scene Ownership Cleanup

Last reviewed: 2026-07-03 JST

## Purpose

ACG-5 removes the remaining ambiguity that RelayEMO owns same-turn scene state. RelayEMO owns affect estimates, assistant expression state, and expression modulation hints only.

RelaySCN remains the sole owner of normalized `scene_state` and `scene_policy` in the request path. RelayMEM policy is derived from RelaySCN policy, not RelayEMO output.

## Implemented boundary

RelayEMO may expose a `scene_hint_candidate` for expression gating and diagnostics. This candidate is content-free and non-authoritative:

```text
source_authoritative = false
policy_authority = none
restrictive_only = true
candidate_applied = false
can_open_runtime_policy = false
content_free = true
```

The candidate is represented with the shared ACG governance helper as a non-authoritative `scene_policy_candidate` source. It is a hint candidate only, not RelaySCN policy input.

A deprecated internal `scene_state` compatibility field may remain while existing RelayEMO marker preview and smoke coverage still read it. That field is explicitly marked deprecated, non-authoritative, restrictive-only, content-free, and policy-authority `none`. It must not be consumed by RelaySCN or RelayMEM as scene policy.

## Ownership invariants

```text
RelaySCN:
  owns normalized scene_state and scene_policy
  may provide policy constraints to RelayEMO, RelayMEM, RelayCTX, RelayINT, RelayREL, and RelaySLP

RelayEMO:
  owns user_affect_estimate, assistant_emotion_state, affect probe candidates, and expression hints
  may emit non-authoritative scene_hint_candidate for expression gating only
  must not open RelayMEM retrieval/update policy
  must not feed RelaySCN scene policy input
```

## Public diagnostics

Public RelayEMO projections must remain content-free. They may expose fixed values such as candidate presence, source class, source authority, policy authority, restrictive-only status, reason IDs, validation IDs, and confidence/stability buckets. They must not expose raw user text, assistant text, scene bodies, relationship bodies, memory text, protected source bodies, filesystem paths, queue payloads, or free-form rationale.

## Non-goals

ACG-5 does not implement:

- ACG-6 SCN structured classifier or scene-wiki integration;
- RelayMEM retrieval query rewrite;
- Grounded Recall detail migration;
- RelayREF / RelayINT consolidation;
- broad retrieval or memory update authority from RelayEMO hints;
- RelayEMO to RelaySCN scene fallback restoration.

## Validation

Expected validation:

```text
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_analyzer_governance_smoke.py
PYTHONPATH=. python scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
PYTHONPATH=. python scripts/relaylm_p0_pipeline_ordering_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```
