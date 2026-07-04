---
relaylm_doc_type: architecture_report
relaylm_authority: acg6_scene_wiki_classifier_boundary
relaylm_status: current
relaylm_volatility: high
relaylm_owner: architecture
relaylm_update_trigger:
  - RelaySCN scene classifier candidate schema changes
  - scene-wiki matching boundary changes
  - scene policy authority gate changes
  - public scene diagnostics changes
relaylm_not_authoritative_for:
  - full Character Workspace parser/compiler/UI behavior
  - scene-wiki page generation or mutation behavior
  - RelayEMO affect/expression ownership
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - ../DOCUMENTATION_MODEL.md
  - analyzer_candidate_governance.md
  - p0_relayrel_relayscn_relayemo_ordering_fix.md
  - acg5_relayemo_scene_cleanup.md
  - project_execution_plan.md
---
# ACG-6 Scene-Wiki Classifier Boundary

Last reviewed: 2026-07-03 JST

## Purpose

ACG-6 implements the first bounded RelaySCN structured scene classifier candidate and scene-wiki matching boundary.

The implemented flow is:

```text
request context / route / tool signals / optional structured scene-wiki definitions
  -> RelaySCN structured scene classifier candidate
  -> Analyzer Candidate Governance authority/confidence/stability validation
  -> RelaySCN scene policy compiler
  -> downstream RelayMEM / RelayCTX behavior
```

The classifier is a candidate producer. It is not a scene authority by default.

## Implemented modules

```text
relaylm/scene_classifier.py
relaylm/scene_wiki_matcher.py
scripts/relaylm_acg6_scene_wiki_classifier_smoke.py
```

`relaylm/scene_classifier.py` emits a fixed English structured artifact for `scene_policy_candidate` and uses `relaylm/analyzer_governance.py` to normalize authority. `relaylm/scene_wiki_matcher.py` accepts already-structured scene definitions and returns content-free match diagnostics.

RelaySCN now includes classifier and scene-wiki diagnostics in `build_relayscn_scene_policy_artifact(...)` while preserving the existing explicit scene-state authority boundary.

## Fixed scene type enum

The initial classifier enum is fixed English-only:

```text
unknown
casual_chat
implementation_work
review_work
design_talk
formal_document
medical_or_safety
system_ops
recovery
vtuber_roleplay
memory_management
character_workspace
```

Free-form classifier labels do not become enum values. Unknown or unrecognized labels normalize to `unknown` with content-free validation evidence. Raw labels are not exposed in public diagnostics.

## Authority rule

Classifier, LLM, heuristic, and scene-wiki match outputs are candidates.

They may:

- provide candidate scene labels;
- improve diagnostics;
- match known structured scene-wiki entries;
- strengthen safety, formal-document, or recovery restrictions;
- fail closed;
- recommend a scene for confirmation.

They must not, by themselves:

- open broad RelayMEM retrieval;
- open memory update gates;
- create trusted scene admission;
- mutate scene-wiki pages;
- mutate uppercase character source files;
- override explicit trusted route metadata;
- override user-confirmed scene selection;
- restore RelayEMO scene ownership.

Only trusted, explicit, or confirmed sources may authorize permissive RelaySCN scene policy, and only when the Analyzer Candidate Governance gate reports that the candidate can open bounded runtime policy.

## RelaySCN precedence

RelaySCN keeps the precedence order:

```text
trusted explicit scene metadata / route-owned trusted scene
  > confirmed scene selection
  > trusted scene-wiki definition selected by route/context
  > structured classifier candidate
  > lexical fallback
  > unknown / fail-closed
```

Existing request metadata remains preferred. A classifier candidate cannot override explicit RelaySCN `scene_state` metadata.

## Scene-wiki matching boundary

The matcher intentionally accepts only structured scene definition records such as:

```python
{
    "scene_id": "repo_review",
    "scene_type": "review_work",
    "scene_family": "implementation",
    "aliases": ["pull_request_review", "code_review"],
    "authority": "explicit_scene_definition",
    "enabled": True,
}
```

The matcher:

- matches only safe fixed IDs, scene types, families, and aliases;
- returns safe IDs, match strength buckets, and counts;
- does not expose scene body text;
- does not mutate the passed definitions;
- does not create or update scene-wiki pages;
- does not parse Character Workspace Markdown.

Full Character Workspace parser/compiler/UI behavior remains a separate implementation lane.

## Public diagnostics

ACG-6 public projections are content-free. They may include only fixed keys such as:

```text
candidate_present
candidate_scene_type
candidate_scene_family
matched_scene_wiki_id
match_strength
confidence_bucket
stability_bucket
source_class
source_authoritative
policy_authority
restrictive_only
candidate_applied
can_open_runtime_policy
reason_ids
validation_error_ids
content_free
```

They must not include raw user text, raw assistant text, scene Markdown, scene-wiki body text, relationship body text, memory text, free-form classifier rationale, LLM raw output, filesystem paths, queue payloads, protected source bodies, or unvalidated external signal bodies.

## Validation

The ACG-6 smoke covers:

- fixed English enum emission;
- free-form scene labels normalizing to `unknown` without raw leakage;
- heuristic/LLM candidates failing to open broad policy;
- safety/formal/recovery candidates restricting or failing closed only;
- trusted explicit scene metadata remaining preferred;
- scene-wiki match output staying content-free and non-mutating;
- RelaySCN keeping non-authoritative candidates fail-closed;
- confirmed/trusted bounded candidates opening only through the governance gate;
- P0 ordering preservation.

Expected validation commands:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_analyzer_governance_smoke.py
PYTHONPATH=. python scripts/relaylm_acg6_scene_wiki_classifier_smoke.py
PYTHONPATH=. python scripts/relaylm_p0_pipeline_ordering_smoke.py
PYTHONPATH=. python scripts/relaylm_acg5_relayemo_scene_cleanup_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

## Non-goals

ACG-6 does not implement:

- Character Workspace parser/compiler/UI;
- scene-wiki page mutation or auto-generation;
- live LLM classifier calls;
- broad retrieval or memory update authority from classifier output;
- SOUL or uppercase source mutation authority;
- RelayEMO scene ownership restoration.
