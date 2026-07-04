---
relaylm_doc_type: implementation_handoff
relaylm_authority: cw_a1_file_first_source_tree_parser_contracts
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace source tree contract changes
  - Character Workspace parser or validation schema changes
  - public diagnostics for workspace validation change
  - CW-A2 compiler projection boundary changes
relaylm_not_authoritative_for:
  - repository-wide current implementation status
  - CW-A2 compiler or KV-cache projections
  - CW-A3 UI implementation
  - CW-A4 RelaySLP workspace maintenance
  - CW-A5 templates or imports
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - project_execution_plan.md
  - file_first_character_workspace_design.md
  - character_template_creation_flow.md
  - analyzer_candidate_governance.md
  - pipeline_responsibility_design.md
---
# CW-A1 File-first Source Tree and Parser Contracts

Last reviewed: 2026-07-04 JST

## Purpose and authority

This document records the CW-A1 implementation slice for the file-first Character Workspace reset. It owns the exact bounded handoff for the read-only source-tree and parser contract helpers added in this slice.

Read [Project Status](../PROJECT_STATUS.md) for repository-wide current state and [Project Execution Plan](project_execution_plan.md) for roadmap sequencing. Read [File-first Character Workspace Design](file_first_character_workspace_design.md) for the broader target architecture and future compiler/UI direction.

## CW-A1 scope

CW-A1 adds a small deterministic contract layer that can:

```text
describe the target workspace layout;
classify workspace-relative paths;
validate an existing character workspace root read-only;
parse Markdown source files into bounded contract objects;
build content-free public validation and manifest diagnostics;
prove naming, ownership, and public-diagnostic boundaries with smoke coverage.
```

The implementation surface is `relaylm/character_workspace.py`. The smoke entry point is `scripts/relaylm_cw_a1_file_first_workspace_smoke.py`.

## Target workspace layout

CW-A1 recognizes the target root:

```text
characters/<character>/
```

Required human-editable uppercase source files:

```text
SOUL.md
STYLE.md
EMOTION.md
SCENE.md
RELATIONSHIP.md
MEMORY.md
BOUNDARY.md
```

Optional uppercase source file:

```text
LORE.md
```

Lowercase SLP-maintained and user-inspectable workspace domains:

```text
relationships/<target>.md
relationships/_inbox/
scenes/*.md
scenes/_inbox/
memory/core.md
memory/people/
memory/projects/
memory/topics/
memory/episodes/
memory/inbox/
memory/forgotten/
```

Proposal domains:

```text
proposals/soul/
proposals/style/
proposals/emotion/
proposals/scene/
proposals/relationship/
proposals/memory/
proposals/boundary/
```

Internal/generated/runtime domains:

```text
.relaylm/sources/conversations/
.relaylm/sources/corrections/
.relaylm/sources/imports/
.relaylm/state/scene_state.json
.relaylm/state/emotion_state.json
.relaylm/state/relationship_state_cache.json
.relaylm/build/character_manifest.json
.relaylm/build/style_projection.json
.relaylm/build/emotion_projection.json
.relaylm/build/scene_units.jsonl
.relaylm/build/relationship_projection.json
.relaylm/build/memory_units.jsonl
.relaylm/build/context_projection.json
.relaylm/build/links.jsonl
.relaylm/indexes/
.relaylm/projections/
.relaylm/audit/
.relaylm/queue/
```

## Naming and ownership rules

CW-A1 keeps these rules as explicit constants and smoke-tested behavior:

```text
UPPERCASE.md root files are deliberate human-editable character source.
lowercase/**/*.md files are SLP-maintained wiki pages, candidates, or target instances.
.relaylm/** files are generated/runtime/internal artifacts and are not hand-authored character source.
Current scene and emotion state belongs under .relaylm/state/**, not in SCENE.md or EMOTION.md.
memory/**/*.md pages are human editing units, not one-file-per-memory records.
Stable memory block IDs use Markdown heading anchors, such as `## Target user direction ^mem-relaylm-target-user`.
```

## Parser contract summary

The CW-A1 module exposes these contract behaviors:

```text
CharacterWorkspacePathKind
CharacterWorkspaceValidationStatus
CharacterWorkspaceLayout
classify_character_workspace_path(relative_path)
validate_character_workspace(root, character_id=None, public=False)
parse_character_source_file(path, source_kind, public=False)
parse_markdown_blocks(text, source_path=None)
build_character_workspace_manifest(root, public=False)
```

Path classification is deterministic and filesystem-free. It rejects absolute paths and `..` traversal, treats `.relaylm/**` as internal, treats only exact root uppercase source files as source, and classifies lower-case wiki pages by relationship, scene, and memory domains.

Workspace validation is read-only. It does not mutate files, create skeletons, create a default character, restore a default active character, run compiler projections, or wire runtime defaults. Missing required uppercase sources return the fixed status `missing_required_source`.

Markdown parsing identifies headings, optional heading anchors, `key:: value` metadata lines, stable content hashes, and block line ranges. It does not require memory pages to be one-file-per-memory records.

The manifest helper is a read-only contract manifest summary. It is not the CW-A2 compiler and does not write `.relaylm/build/character_manifest.json`.

## Public diagnostic content-free rules

When `public=True` or a `to_public_dict()` projection is used, CW-A1 diagnostics may expose:

```text
schema version;
enum values;
source filename;
source kind;
status;
content hash;
line and block counts;
reason IDs;
domain/path-kind counts.
```

Public diagnostics must not expose:

```text
raw Markdown bodies;
absolute or private filesystem paths;
queue records;
runtime-private payloads;
memory IDs or heading anchors;
internal source evidence bodies.
```

## Non-goals

CW-A1 does not implement CW-A2:

```text
no full context compiler;
no KV-cache tier compiler;
no backend prompt projection;
no source-to-RelayCTX runtime wiring beyond passive imports.
```

CW-A1 does not implement CW-A3:

```text
no Character Workspace UI rebuild;
no new Characters / Scenes / Relationships / Memory Wiki surfaces.
```

CW-A1 does not implement CW-A4:

```text
no RelaySLP automatic workspace maintenance;
no auto-merge of scenes, memory, or relationship candidates;
no uppercase source mutation.
```

CW-A1 does not implement CW-A5:

```text
no Quick Create or Advanced Create UI;
no template shelf;
no showcase import behavior.
```

CW-A1 also does not add broad compatibility shims for legacy source names and does not weaken Analyzer Candidate Governance, P0 ordering, E1-R5 scoped recall, lifecycle exclusions, or content-free public diagnostic guarantees.

## Validation commands

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_cw_a1_file_first_workspace_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
PYTHONPATH=. python scripts/relaylm_analyzer_governance_smoke.py
PYTHONPATH=. python scripts/relaylm_p0_pipeline_ordering_smoke.py
```

## Relationship to broader design

[File-first Character Workspace Design](file_first_character_workspace_design.md) remains the broad target architecture for editable Markdown character sources, generated projections, and KV-cache-friendly runtime tiers. CW-A1 is the first bounded implementation contract under that target. It establishes the path/parser/validation vocabulary needed before CW-A2 can compile workspace sources into runtime projections.

[Project Execution Plan](project_execution_plan.md) owns the CW-A1 -> CW-A2 -> CW-A3 -> CW-A4 -> CW-A5 sequence. This handoff only records the CW-A1 boundary.
