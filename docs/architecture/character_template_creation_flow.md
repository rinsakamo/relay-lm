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
  natural guidance for using RelayLM itself
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

## RelayLM onboarding knowledge memory

Official default starter and showcase characters should include a small RelayLM onboarding knowledge memory.

This is a normal memory page from the retrieval/compiler point of view. It should live under the same `memory/**/*.md` tree as other character memories so it can be selected, chunked, and injected by the ordinary memory pipeline when the user asks about RelayLM.

It is not a SOUL trait and must not turn the character into a RelayLM development-review partner. The character may be a companion, VTuber partner, mascot, or roleplay character, while still having one protected memory page that explains RelayLM basics.

Recommended placement:

```text
memory/topics/relaylm.md
  protected template-scoped product-help memory page

scenes/relaylm_onboarding.md
  optional onboarding/help scene that selects that memory when appropriate

preview/sample_responses.md
  examples of the character explaining RelayLM in its own voice
```

Recommended metadata:

```markdown
status:: template_knowledge
source:: template:relaylm_onboarding
scope:: product_help
mutable:: false
slp_update:: disabled
update_policy:: bundled_template_update_only
```

Meaning:

```text
normal memory page
  -> searchable and injectable when relevant

protected from ordinary SLP mutation
  -> RelaySLP must not rewrite, merge, summarize away, or supersede this page during normal memory maintenance

not fake user memory
  -> not treated as something the character learned about the real user

not source identity
  -> not placed in SOUL.md and not used as character identity
```

Official default characters should include this page. Self-authored characters, imported characters, and third-party templates should not receive RelayLM onboarding knowledge automatically.

If a user wants the same help behavior in a custom or imported character, they can copy `memory/topics/relaylm.md` into that character workspace. Once copied, it is ordinary character memory for that workspace and should work through the same retrieval path. RelayLM should not special-case the character type beyond honoring the page metadata.

Manual edits are allowed because the workspace is file-first. However, RelaySLP should still treat the page as protected from automatic mutation while `slp_update:: disabled` is present. If the user removes that metadata, the page becomes an ordinary editable memory page under normal memory policy.

Purpose:

```text
help first-time users understand what RelayLM is
explain the Character Workspace model in character voice
answer basic questions about SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY
explain that Markdown source files are editable source of truth
explain that .relaylm/** is generated/runtime/internal material
explain how to create, import, edit, and grow characters
explain public/private scene and memory-disclosure behavior
suggest safe next steps when the user is confused
```

The onboarding knowledge memory should be factual, compact, and user-facing. It should not include internal PR history, private implementation notes, queue records, memory IDs, unreleased claims, or hidden diagnostics.

Good default knowledge:

```text
RelayLM is a local-LLM character workspace.
Characters are stored as editable Markdown files.
Uppercase files are stable human-edited character sources.
Lowercase pages are SLP-maintained wiki/work pages.
.relaylm contains generated/runtime artifacts.
RelayLM compiles the workspace into backend-bound prompt projections.
Memory and scene updates can be proposed or maintained after turns.
Private memory should not be exposed in public/stream scenes.
```

Not default knowledge:

```text
current PR status
private roadmap arguments
internal review comments
queue implementation details
memory IDs or revision IDs
claims that a feature is implemented when it is only target architecture
```

The default behavior should be:

```text
character first
  -> keep the chosen character voice and use case

RelayLM-aware
  -> can explain how this workspace works when asked

not developer-default
  -> does not turn every character into a technical project reviewer
```

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
  protected RelayLM onboarding memory, private-scene familiarity limits,
  and natural memory use without fake intimacy.

Showcase VTuber / Stream Partner
  A stream-friendly character with public/private scene differences,
  protected RelayLM help memory, expression profiles, audience-safe memory disclosure,
  and chat-ready style.

Showcase Creator Mascot
  A memorable mascot-style character for creators who want a consistent local AI
  persona for brainstorming, streaming, short clips, casual interaction,
  and light RelayLM guidance.

Showcase Fantasy Roleplay Character
  A lore-heavy character with SOUL, STYLE, EMOTION, SCENE, BOUNDARY, LORE,
  roleplay-oriented scene pages, and optional out-of-character RelayLM help scene.
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
  protected RelayLM onboarding memory
  intended for customization

Showcase template
  richer memory/core examples
  multiple active scenes
  tuned relationship instance
  protected RelayLM onboarding memory
  optional onboarding/help scene
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
  keep curated example memories, scenes, and protected RelayLM onboarding memory

Use as starter
  keep personality/style/lore and protected RelayLM onboarding memory,
  but clear example user-specific memory
```

For AI companion templates, the default should avoid importing fake user-specific intimacy. It is acceptable to include template-scoped examples such as favorite topics, prior scene examples, creator workflow examples, demo-user memories, and protected RelayLM onboarding memory when clearly marked as template examples or template knowledge.

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
  relaylm_onboarding.md optional
  optional showcase scenes
memory/
  core.md
  topics/
    relaylm.md optional
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
  relationship to user, tone, forbidden behaviors, and optional RelayLM help behavior
  -> drafts SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY / LORE
  -> for official default templates, includes protected RelayLM onboarding memory
  -> for custom/imported templates, does not auto-inject RelayLM onboarding memory
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
Official default starter/showcase characters include a protected normal memory page
for RelayLM onboarding knowledge.
Self-authored and imported characters do not receive RelayLM onboarding knowledge automatically.
Users may copy the onboarding memory page into a custom workspace when desired.
Showcase characters demonstrate the grown-character experience for AI companion,
VTuber / stream, mascot, and roleplay users.
Design-review characters are secondary power-user templates, not the default shelf.
External imports are validated content-only packs.
All modes produce the same file-first Character Workspace.
```
