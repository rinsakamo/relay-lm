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

## Primary user fit

The primary template experience should fit local-LLM character users: AI companion builders, VTuber / livestream experimenters, roleplay users, and hobbyists running mid-range GPU stacks through tools such as OpenWebUI and LM Studio.

The default template shelf must not be shaped around RelayLM development work. A design-review partner can exist as an advanced or developer-oriented template, but it should not be the primary default character experience.

Primary showcase goal:

```text
Show the user why a grown local AI character feels different from a blank chatbot:
  stable identity
  recognizable voice
  scene-aware behavior
  public/private expression difference
  bounded memory use
  relationship continuity without fake intimacy
```

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

Default template choices should be character-first:

```text
Template:
  Friendly Companion
  VTuber / Stream Partner
  Creator Mascot
  Fantasy Roleplay Character
  Calm Assistant Character
  Blank Character

Tone:
  friendly
  polite
  calm
  energetic
  cool
  playful
  slightly sharp

Use:
  casual chat
  AI companion
  livestream / VTuber chat
  roleplay
  learning support
  creative brainstorming
```

Secondary or advanced templates may include:

```text
Developer Design Partner
  useful for RelayLM development and technical review,
  but not a default showcase for the primary user.
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

Finished showcase characters are important because a blank or newly generated character does not demonstrate long-term memory, scene tuning, relationship style, public/private scene handling, or mature character consistency. A showcase character should demonstrate the end-state character experience that RelayLM is aiming for.

Primary showcase examples:

```text
Showcase Friendly Companion
  A warm but bounded companion with recognizable voice, gentle continuity,
  private-scene familiarity limits, and natural memory use without fake intimacy.

Showcase VTuber / Stream Partner
  A stream-friendly character with public/private scene differences,
  expression profiles, audience-safe memory disclosure, and chat-ready style.

Showcase Creator Mascot
  A memorable mascot-style character for creators who want a consistent local AI
  persona for brainstorming, streaming, short clips, and casual interaction.

Showcase Fantasy Roleplay Character
  A lore-heavy character with SOUL, STYLE, EMOTION, SCENE, BOUNDARY, LORE,
  and roleplay-oriented scene pages.
```

Secondary showcase examples:

```text
Developer Design Partner
  A technical/project-review companion for advanced users.
  This may be useful as a power-user template but should not define the default shelf.
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

Showcase templates must clearly mark example memories as template memories. They must not imply that the system personally knows the real user before the user creates or imports the workspace.

Recommended marker:

```markdown
status:: template_example
source:: template:showcase_friendly_companion
```

On creation from a showcase template, RelayLM should offer a light reset option:

```text
Use showcase as-is
  keep curated example memories and scenes

Use as starter
  keep personality/style/lore, but clear example user-specific memory
```

For AI companion templates, the default should avoid importing fake user-specific intimacy. It is acceptable to include template-scoped examples such as favorite topics, prior scene examples, creator workflow examples, or demo-user memories when clearly marked as template examples.

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
Fantasy Roleplay generator
  asks for name, gender/presentation, world, role, oath or motivation,
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
  Friendly Companion
  VTuber / Stream Partner
  Creator Mascot
  Fantasy Roleplay Character
  Calm Assistant Character

Showcase:
  Showcase Friendly Companion
  Showcase VTuber / Stream Partner
  Showcase Creator Mascot
  Showcase Fantasy Roleplay Character

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
Try a showcase character
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
Showcase characters demonstrate the grown-character experience for AI companion,
VTuber / stream, mascot, and roleplay users.
Design-review characters are secondary power-user templates, not the default shelf.
External imports are validated content-only packs.
All modes produce the same file-first Character Workspace.
```
