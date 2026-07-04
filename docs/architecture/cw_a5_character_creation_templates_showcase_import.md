---
relaylm_doc_type: implementation_handoff
relaylm_authority: character_workspace_creation_templates_import_boundary
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - character creation route behavior changes
  - template validation or manifest behavior changes
  - workspace commit behavior changes
  - active-character selection policy changes
relaylm_not_authoritative_for:
  - repository-wide current status
  - runtime conversation behavior outside creation/import flow
  - remote template registry behavior
  - RelaySLP automatic maintenance beyond CW-A4
  - active character auto-selection
relaylm_related_authority:
  - ../PROJECT_STATUS.md
  - project_execution_plan.md
  - file_first_character_workspace_design.md
  - character_template_creation_flow.md
  - cw_a1_file_first_source_tree_parser_contracts.md
  - cw_a2_workspace_compiler_projections.md
  - cw_a3_character_workspace_ui_rebuild.md
  - cw_a4_slp_workspace_maintenance_candidates.md
---
# CW-A5 Character Creation, Templates, and Showcase Import

Last reviewed: 2026-07-04 JST

## Purpose

CW-A5 adds the bounded character creation path for the file-first Character Workspace reset. It covers bundled official templates, Quick Create, Advanced Create staging, showcase-as-template behavior, local template validation, explicit workspace commit, and local CW-A2 build projection generation.

The target user journey is:

```text
No valid character workspace
  -> Character Creation / Import flow
  -> source files selected or generated
  -> deterministic validation
  -> compiled preview
  -> explicit user approval
  -> workspace commit
  -> .relaylm/build projections generated
  -> active character set only by explicit user action
```

## No auto-created default active character

RelayLM must not create, restore, or activate a default/sample character when no valid Character Workspace exists. CW-A5 exposes creation flow instead. Sample/showcase characters remain templates until explicitly created by the user.

The SOUL Lab UI now routes the zero-character projection to the Create surface rather than falling back to a runtime active character. This is a UI state transition, not active-character mutation.

## Quick Create

Quick Create accepts a bundled template id, character name, tone, and intended use. It performs deterministic template substitution, stages a full source tree, validates it through CW-A1, and returns a content-free compiled preview summary through CW-A2.

Quick Create is not a reduced workspace format. It produces the same required uppercase sources, lowercase workspace directories, relationship pages, scene pages, memory pages, and optional LORE source as the other creation modes.

## Advanced Create

Advanced Create exposes source sections for SOUL, STYLE, EMOTION, RELATIONSHIP, SCENE, MEMORY, BOUNDARY, optional LORE, and Preview. It stages the candidate source tree and keeps it candidate-only until validation and explicit approval.

Advanced Create does not bypass CW-A1 validation, does not write `.relaylm/build/**` from templates, and does not auto-apply SOUL or MEMORY changes.

## Template pack format

Template packs are content-only source packs. The safe format includes:

```text
manifest.json
SOUL.md
STYLE.md
EMOTION.md
SCENE.md
RELATIONSHIP.md
MEMORY.md
BOUNDARY.md
optional LORE.md
relationships/
scenes/
memory/
preview/
assets/
```

Validation rejects scripts, executables, symlinks, absolute paths, path traversal, `.env`, runtime config overrides, credentials, queue/audit/runtime state artifacts, and imported `.relaylm/build/**` artifacts.

## Official bundled templates

CW-A5 registers bundled official templates without network download:

- Friendly Companion
- VTuber / Stream Partner
- Creator Mascot
- Fantasy Roleplay Character
- Calm Assistant Character
- Blank Character
- Showcase Friendly Companion
- Showcase VTuber / Stream Partner
- Showcase Creator Mascot
- Showcase Fantasy Roleplay Character
- Developer Design Partner

Developer Design Partner is an advanced/power-user template and is not part of the primary default shelf.

## Showcase templates

Showcase templates demonstrate a grown-character experience without becoming active workspaces automatically. Example memories are marked as `status:: template_example` and remain clearly separate from real user memory.

CW-A5 supports two showcase staging modes:

```text
use as-is
  -> keeps curated example memories and scenes

use as starter
  -> keeps personality/style/lore and RelayLM onboarding memory,
     but clears demo user-specific example memory
```

## RelayLM onboarding memory

Official starter/showcase templates may include `memory/topics/relaylm.md` as a pinned product-help memory page:

```markdown
status:: template_knowledge
source:: template:relaylm_onboarding
scope:: product_help
pin_state:: pinned
slp_update:: disabled
update_policy:: bundled_template_update_only
```

This is ordinary memory source, not a SOUL trait and not fake user memory. It does not contain current PR status, private roadmap arguments, internal review comments, queue implementation details, memory IDs, revision IDs, or claims about unimplemented features. Third-party/imported templates do not receive this memory automatically.

## Import safety

CW-A5 MVP validates bundled templates and local folder/zip packs. Remote registries and unbounded network downloads are non-goals.

Validation returns content-free reason IDs and does not dump unsafe file content or raw internal paths. A valid user-facing summary can say:

```text
This template was checked.
No scripts or unsafe files were found.
Create character?
```

## Workspace commit flow

The commit flow is staged and explicit:

```text
template selected
  -> candidate staged under final character slug
  -> CW-A1 validation
  -> CW-A2 compiled preview
  -> explicit approval
  -> atomic-ish directory move under characters/<character>/
  -> local .relaylm/build/** generated by CW-A2
  -> active character remains unset until explicit user action
```

Commit rejects invalid character slugs, invalid candidates, existing target workspaces, and unapproved requests. It does not delete or merge existing characters and does not import `.relaylm/**` runtime/build/state artifacts from templates.

## API and CLI surface

Loopback-only SOUL Lab routes:

```text
GET  /lab/api/character-templates
POST /lab/api/character-templates/validate
POST /lab/api/characters/create-from-template
POST /lab/api/characters/import-template
```

CLI entrypoints:

```bash
relaylm-character-create --template friendly-companion --name Koyomi --dry-run
relaylm-character-create --template friendly-companion --name Koyomi --write
relaylm-character-template-validate path/to/template
```

The CLI requires `--write` for persistence and does not auto-activate characters.

## Non-goals

CW-A5 does not implement remote template ecosystems, unbounded downloads, automatic default active character restoration, runtime prompt injection changes, RelayMEM semantic rewrites, RelaySOUL apply/rollback, SLP auto-apply beyond CW-A4, LLM generation on the normal startup/response path, O2/O3 worker services, or media runtime features.

## Validation commands

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_cw_a1_file_first_workspace_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a2_workspace_compiler_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a4_workspace_slp_candidates_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a5_character_creation_templates_smoke.py
cd apps/soul-lab && npm run typecheck
cd apps/soul-lab && npm run smoke:character-workspace
cd apps/soul-lab && npm run smoke:character-creation
cd apps/soul-lab && npm run build
```

Use actual smoke names when a downstream branch has renamed prior CW smokes.

## Completion boundary

CW-A5 is complete when no-character startup routes to creation/import flow, Quick Create / Advanced Create / Showcase / Import share the same file-first source structure, official starter/showcase templates exist, unsafe template packs are rejected fail-closed, workspace commit requires explicit approval, local build projections are generated by CW-A2, and active character selection remains explicit.
