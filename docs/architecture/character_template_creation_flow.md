---
relaylm_doc_type: stable_architecture
relaylm_authority: character_template_creation_and_showcase_flow
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - character creation UX changes
  - template registry changes
  - template import safety changes
  - showcase character policy changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact template manifest schema
  - exact UI component implementation
  - exact download transport implementation
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - file_first_character_workspace_design.md
  - project_execution_plan.md
  - pipeline_responsibility_design.md
---
# Character Template and Creation Flow

## Purpose

This document defines the target character creation and template import flow for the file-first Character Workspace.

It complements [File-first Character Workspace Design](file_first_character_workspace_design.md). It does not claim that the current SOUL Lab UI already implements these flows.

## Core rule

RelayLM must not auto-create or auto-restore a default active character when no valid character workspace exists.

```text
valid character exists
  -> normal startup / character selection

no valid character exists
  -> Character Creation / Import flow

sample or showcase characters
  -> templates only until explicitly selected by the user
```

A sample character may be bundled or downloadable, but it is not an active workspace until the user explicitly creates a character from it.

## Creation modes

Character creation has two primary modes:

```text
Quick Create
  Low-friction path for starting immediately.

Advanced Create
  Detailed path that exposes the source model.
```

Both modes produce the same final workspace structure:

```text
characters/<character>/
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
  proposals/
  .relaylm/
```

Quick Create is not a lesser character format. It is a lower-friction way to generate the same complete workspace from safe defaults and templates.

## Quick Create

Quick Create should ask for only a few choices:

```text
template
name
tone
intended use
```

Example choices:

```text
Template:
  Friendly Companion
  Design Partner
  VTuber Chat
  Fantasy Knight
  Quiet Assistant
  Blank

Tone:
  friendly
  polite
  calm
  energetic
  cool
  slightly sharp

Use:
  casual chat
  development / design review
  livestream / VTuber chat
  learning support
  roleplay
```

User-facing flow:

```text
select template
  -> enter name
  -> choose tone / use
  -> create
```

Internal flow:

```text
select template
  -> stage template
  -> fill safe defaults
  -> optionally run LLM generator for candidate source text
  -> deterministic validation
  -> compile stable prompt preview
  -> create workspace
```

The UI should not force the user to inspect every source file during Quick Create. Details remain editable after creation.

## Advanced Create

Advanced Create exposes the underlying source model:

```text
Identity      -> SOUL.md
Style         -> STYLE.md
Emotion       -> EMOTION.md
Relationship  -> RELATIONSHIP.md / relationships/user.md
Scene         -> SCENE.md / scenes/default.md
Memory        -> MEMORY.md / memory/core.md
Boundary      -> BOUNDARY.md
Lore          -> optional LORE.md
Preview       -> compiled prompt preview and sample responses
Create        -> approved workspace commit
```

Advanced Create may use an LLM generator to draft candidate sources, but generated content remains a candidate until validation and user approval.

## Finished character templates

Templates should include not only blank or lightly configured starters, but also finished showcase characters.

Purpose:

```text
starter templates
  -> help the user create their own character quickly

finished showcase characters
  -> let the user immediately experience what a grown character feels like
```

Finished showcase characters are important because a blank or newly generated character does not demonstrate long-term memory, scene tuning, relationship style, or mature character consistency. A showcase character should demonstrate the end-state experience that RelayLM is aiming for.

Examples:

```text
Showcase Design Partner
  Mature project-review companion with established scene pages, memory examples,
  relationship policy, and direct-but-safe disagreement style.

Showcase VTuber Chat Character
  Stream-friendly character with public/private scene differences, expression profiles,
  and safe memory-disclosure behavior.

Showcase Fantasy Knight
  Lore-heavy character with SOUL, STYLE, EMOTION, SCENE, BOUNDARY, LORE,
  and roleplay-oriented scene pages.
```

Showcase characters may include curated example memory pages and scene pages, but they must still be content-only templates.

## Starter versus showcase policy

```text
Starter template
  minimal memory
  small scene set
  broad defaults
  intended for customization

Showcase template
  richer memory/core examples
  multiple active scenes
  tuned relationship instance
  optional LORE
  sample prompts/responses
  demonstrates growth and maturity
```

Showcase templates must clearly mark example memories as template memories. They must not imply that the system personally knows the user before the user creates or imports the workspace.

Recommended marker:

```markdown
status:: template_example
source:: template:showcase_design_partner
```

On creation from a showcase template, RelayLM should offer a light reset option:

```text
Use showcase as-is
  keep curated example memories and scenes

Use as starter
  keep personality/style/lore, but clear example user-specific memory
```

For AI companion templates, the default should avoid importing fake user-specific intimacy. Project/product example memories are acceptable when clearly template-scoped.

## Template sources

Supported target sources:

```text
bundled official templates
  available without network

official remote registry
  curated template packs, optionally downloaded from GitHub releases

custom GitHub URL
  advanced import path with validation and warning

local zip/folder
  advanced import path with validation
```

The MVP may start with bundled official templates and add remote registry later.

## Template pack format

A template pack is a content-only source pack.

Recommended structure:

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
  _template.md
  user.md optional
scenes/
  default.md
  optional showcase scenes
memory/
  core.md
  optional showcase pages
preview/
  sample_prompt.txt
  sample_responses.md
assets/
  icon.png optional
```

Template packs should not include `.relaylm/build/**`; generated projections are created locally after validation.

## Import safety

Official bundled templates should feel one-click. Safety checks run silently unless something is wrong.

External templates require stricter validation, but the UX should still remain light:

```text
This template was checked.
No scripts or unsafe files were found.
Create character?
```

Hard rules for all template packs:

```text
No scripts.
No executables.
No symlinks.
No absolute paths.
No path traversal.
No .env files.
No runtime config override.
No hidden auto-activation.
No queue, audit, or runtime state artifacts.
No generated .relaylm/build artifacts.
```

Allowed content should be limited to Markdown, manifest, preview text, and safe assets.

## AI-generated templates

Some templates may be generator templates rather than static templates.

Example:

```text
Fantasy Knight generator
  asks for name, gender/presentation, kingdom, knight order, oath,
  relationship to user, tone, and forbidden behaviors
  -> drafts SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY / LORE
```

Generated files are candidates until user approval. After approval, Markdown source files become the source of truth and RelayLM uses deterministic compilation and cached projections.

Normal startup and normal response paths must not call an LLM to re-summarize character sources.

## No-character startup flow

Target startup flow:

```text
scan characters/
  -> at least one valid workspace
       -> open last active character or character selection
  -> none
       -> Character Creation
```

Recommended zero-character UI:

```text
No character found.

Quick start:
  Design Partner
  Friendly Companion
  VTuber Chat
  Fantasy Knight
  Showcase Design Partner

Create:
  Quick Create
  Advanced Create

Import:
  Official templates
  GitHub template
  Local zip/folder
```

MVP can simplify this to:

```text
Create quickly
Create in detail
Start from showcase
Import
```

## Completion criteria

Character creation is complete only after:

```text
source files generated or selected
source files validated
compiled prompt preview generated
sample response preview generated when available
user approved
workspace revision committed
local .relaylm/build projections generated
active character set by explicit user action
```

For Quick Create from official templates, most of these steps may happen behind the Create button. For Advanced Create or external import, the UI may expose more detail.

## Summary

```text
Default active characters are not auto-restored.
Templates are explicit creation sources.
Quick Create is light.
Advanced Create is detailed.
Showcase characters demonstrate the grown-character experience.
External imports are validated content-only packs.
All modes produce the same file-first Character Workspace.
```
