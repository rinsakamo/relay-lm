---
relaylm_doc_type: implementation_handoff
relaylm_authority: cw_a4_slp_workspace_maintenance_candidates
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - CW-A4 candidate/proposal schemas change
  - workspace maintenance apply boundary changes
  - public projection content policy changes
relaylm_not_authoritative_for:
  - CW-A5 character creation, templates, or showcase import
  - runtime prompt injection
  - RelayMEM lifecycle, RelaySCN scene, or RelayREL relationship runtime authority
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - project_execution_plan.md
  - file_first_character_workspace_design.md
  - cw_a1_file_first_source_tree_parser_contracts.md
  - cw_a2_workspace_compiler_projections.md
  - cw_a3_character_workspace_ui_rebuild.md
  - relaymem_slp_current_target.md
---
# CW-A4 SLP Workspace Maintenance Candidates

Last reviewed: 2026-07-04 JST

## Purpose

CW-A4 adds a dry-run-first RelaySLP workspace maintenance planner for File-first Character Workspace MEM / SCENE / REL wiki candidates and proposals. It consumes bounded governed source evidence under `.relaylm/sources/**`, validates the workspace through the CW-A1 source-tree contract, and emits deterministic candidate/proposal schemas plus a content-free public projection.

CW-A4 is complete only for SLP-maintained Memory Wiki, Scene Wiki, and Relationship candidate/proposal planning. It does not implement CW-A5 creation/templates/import.

## Deferred workspace curator boundary

RelaySLP remains a deferred workspace compiler and curator. CW-A4 does not answer the current turn and has no current-turn response effect. The intended out-of-band path remains:

```text
current response completes
  -> governed source evidence under .relaylm/sources/
  -> RelaySLP candidate/proposal planning
  -> memory / scene / relationship inbox candidates
  -> explicit approval or later gated apply
  -> CW-A2 compiler rebuilds .relaylm/build projections
```

The CW-A4 planner does not create queue jobs, start workers, poll, sleep, supervise O2/O3, or mutate runtime state.

## Schemas

CW-A4 uses fixed English schema identifiers:

```text
relaylm.character_workspace_slp_run.v0
relaylm.character_workspace_candidate.v0
relaylm.character_workspace_proposal.v0
relaylm.character_workspace_slp_projection.v0
```

Candidate identifiers and proposal identifiers are stable content-hash-derived IDs. They do not use timestamps, random UUIDs, modification times, or absolute paths.

## Candidate domains

### Memory

Memory candidates target `memory/inbox/*.md` and `proposals/memory/*.json`. The planner treats `memory/**/*.md` as page/block sources, never one-file-per-memory authority. `memory/forgotten/**` remains excluded from ordinary candidate targeting. Sensitive memory candidates remain approval-required and not auto-applied. User-fact candidates require user assertion evidence; assistant-only speculation is blocked and is not promoted to a user fact.

CW-A4 does not replace RelayMEM Primary lifecycle authority and does not run Pin, Unpin, Forget, Delete, physical purge, merge, or supersession apply.

### Scene

Scene candidates target `scenes/_inbox/*.md` and `proposals/scene/*.json`. RelaySCN remains the scene policy owner. RelayEMO does not own scene selection. ACG-6 classifier output, when present in source evidence, can only be treated as a candidate signal and is not runtime authority. `scenes/_inbox/**` is never a direct prompt-injection surface.

CW-A4 does not set active scene state and does not mutate `.relaylm/state/scene_state.json`.

### Relationship

Relationship candidates target `relationships/_inbox/*.md` and `proposals/relationship/*.json`. The planner keeps `RELATIONSHIP.md` vocabulary separate from target-specific relationship instances such as `relationships/<target>.md`. Important relationship parameters and role assignments such as `most_important_person` are explicit-approval proposals only.

CW-A4 does not rewrite RelayREL runtime policy and does not mix relationship candidates into SOUL identity.

## Uppercase source proposal-only rule

CW-A4 never directly writes uppercase source files:

```text
SOUL.md
STYLE.md
EMOTION.md
SCENE.md
RELATIONSHIP.md
MEMORY.md
BOUNDARY.md
LORE.md
```

If a candidate implies an uppercase source change, CW-A4 records approval-required proposal metadata only. It does not perform RelaySOUL apply/rollback and does not auto-rewrite stable character sources.

## Apply policy

Default mode is dry-run. Dry-run writes nothing.

`write-candidates` mode writes only deterministic, allowlisted candidate/proposal artifacts:

```text
memory/inbox/*.md
scenes/_inbox/*.md
relationships/_inbox/*.md
proposals/memory/*.json
proposals/scene/*.json
proposals/relationship/*.json
```

Existing files are never overwritten unless the existing bytes are identical, making repeated writes idempotent. Conflicting files are blocked with deterministic reason IDs. Deletion is not supported.

CW-A4 never directly writes `.relaylm/build/**`, `.relaylm/state/**`, or `.relaylm/queue/**`. If build projections need refresh after an approved change, the operator must run the CW-A2 compiler.

## Public projection

The public projection is content-free. It exposes counts, candidate/proposal IDs, target domains, relative target paths, risk levels, approval flags, and reason IDs. It does not expose raw source bodies, memory text, scene body text, relationship body text, queue payloads, runtime-private identifiers, secrets, or absolute paths.

Example public projection fields:

```json
{
  "schema_version": "relaylm.character_workspace_slp_projection.v0",
  "content_free": true,
  "memory_candidates_count": 2,
  "memory_inbox_additions_count": 1,
  "scene_candidates_count": 1,
  "relationship_candidates_count": 1,
  "sensitive_candidates_count": 0,
  "approval_required_count": 3
}
```

## CLI

```bash
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_candidates.py \
  --workspace-root runtime/characters/koyomi \
  --dry-run

PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_candidates.py \
  --workspace-root runtime/characters/koyomi \
  --write-candidates
```

The CLI prints a content-free projection. `--json-out` can save that projection to an operator-selected path.

## Non-goals

CW-A4 does not implement:

- CW-A5 character creation, templates, or showcase import;
- uppercase source direct writes;
- SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY auto-rewrite;
- RelaySOUL apply or rollback;
- runtime prompt injection;
- `.relaylm/build/**` direct compiler output mutation;
- `.relaylm/state/**` runtime state mutation;
- `.relaylm/queue/**` queue mutation or job creation;
- worker start, O2, O3, polling, sleep, or background loop;
- active scene runtime authority mutation;
- RelayREL runtime rewrite;
- RelayMEM Primary lifecycle replacement;
- Pin / Unpin / Forget / Delete / physical purge;
- sensitive memory auto-apply;
- broad LLM classifier authority;
- TTS/audio/avatar runtime;
- browser-owned trust or source mutation.

## Validation

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_cw_a2_workspace_compiler_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_candidates_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_review_fix_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```

If a CW-A1 parser smoke exists in a checked-out branch, run that equivalent parser smoke as well. If the CW-A3 UI smoke exists, also run the Soul Lab typecheck/smoke/build sequence from `apps/soul-lab`.
