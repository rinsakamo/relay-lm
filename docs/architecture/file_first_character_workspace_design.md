---
relaylm_doc_type: stable_architecture
relaylm_authority: file_first_character_workspace_source_tree_and_context_budget
relaylm_status: target
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - character workspace source-tree changes
  - human-editable source naming changes
  - RelayREL boundary changes
  - RelaySLP workspace maintenance policy changes
  - context packing or KV-cache tier changes
relaylm_not_authoritative_for:
  - current runtime implementation status
  - exact parser schemas
  - exact RelayMEM retrieval schemas
  - exact RelaySLP apply schemas
  - UI component implementation details
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - pipeline_responsibility_design.md
  - memory_lifecycle_design.md
  - relayscn_mvp_scene_policy.md
  - ../relayemo_mvp_initial_design.md
  - ../relaysoul/relaysoul_design.md
---
# File-first Character Workspace Design

## Purpose

This document defines the target file-first character workspace model for RelayLM.

RelayLM should feel like a local-LLM character workspace, not like a memory database administration panel. The user-facing source of truth is an editable Markdown source tree. RelayLM compiles that tree into runtime projections, indexes, state, and audit artifacts used by RelaySCN, RelayEMO, RelayREL, RelayMEM, RelayCTX, and RelaySLP.

This is target architecture. It does not claim that the current SOUL Lab UI, RelayMEM store, RelaySOUL patch tooling, RelaySCN runtime order, or RelayEMO artifact shape already implements this source tree.

## Product boundary

The target product boundary is:

```text
RelayLM is a local-LLM character workspace.

Human-editable Markdown files define the character, relationship model,
scene policy, emotion profiles, memory policy, and boundaries.

RelaySLP maintains lower-case scene and memory wiki pages after turns.

.relaylm/** contains generated, runtime, source, state, index, queue,
and audit artifacts that are not edited by hand.
```

The primary local user is a mid-range GPU local-LLM / OpenWebUI / LM Studio / AI companion / VTuber experimenter who wants to grow a character by editing ordinary files. The primary UX should be a Character Workspace UI, not an internal Pin / Unpin / memory-id console.

## Source tree

Target workspace layout:

```text
characters/<character>/
  SOUL.md            # portable identity, name, values, temperament
  STYLE.md           # portable voice, tone, roleplay flavor, output surface
  EMOTION.md         # portable emotion-state response profiles
  SCENE.md           # scene wiki generation, selection, and consolidation policy
  RELATIONSHIP.md    # RelayREL role and parameter definitions
  MEMORY.md          # memory formation, recall, archive, forget, and disclosure policy
  BOUNDARY.md        # character-specific privacy, pressure, intimacy, and disclosure limits
  LORE.md            # optional: world, backstory, factions, setting, proper nouns

  relationships/
    user.md          # target-specific relationship instance
    _inbox/

  scenes/
    default.md
    development_review.md
    casual_chat.md
    _inbox/

  memory/
    core.md
    people/
      user.md
    projects/
    topics/
    episodes/
    inbox/
    forgotten/

  proposals/
    soul/
    style/
    emotion/
    scene/
    relationship/
    memory/
    boundary/

  .relaylm/
    sources/
      conversations/
      corrections/
      imports/
    state/
      scene_state.json
      emotion_state.json
      relationship_state_cache.json
    build/
      character_manifest.json
      style_projection.json
      emotion_projection.json
      scene_units.jsonl
      relationship_projection.json
      memory_units.jsonl
      context_projection.json
      links.jsonl
    indexes/
    projections/
    audit/
    queue/
```

## Naming rule

```text
UPPERCASE.md
  Human-editable character source.
  These files are the stable, deliberate source layer.

lowercase/**/*.md
  RelaySLP-maintained wiki pages, candidates, and target instances.
  Users may inspect and edit them, but the default workflow is SLP/UI-assisted.

.relaylm/**
  Generated source evidence, state, indexes, projections, queue records, and audit artifacts.
  These files are not hand-authored character source.
```

This naming convention is intentionally visible in ordinary editors. A user should be able to infer whether a file is a stable character source, an SLP-maintained wiki page, or an internal runtime artifact without opening RelayLM.

## Source ownership

### SOUL.md

`SOUL.md` is the portable character identity source. It should remain meaningful if copied into another compatible product.

It may include:

```text
name
gender or gender presentation
age presentation / species / role, when character-defining
self-concept
values
temperament
identity invariants
```

`SOUL.md` should not contain target-specific relationship parameters, current scene state, current emotion state, raw memory pages, or runtime state.

### STYLE.md

`STYLE.md` is the portable output-surface source.

It owns:

```text
first-person / second-person usage
base tone
speech style
roleplay flavor
formatting preferences
response density
emoji / marker policy at the character-source level
```

It does not own durable identity, scene selection, target-specific relationship permissions, memory truth, or safety boundaries.

### EMOTION.md

`EMOTION.md` defines emotion-state response profiles, not current emotion.

Example split:

```text
SOUL.md
  The character is quick to anger when important things are treated carelessly.

EMOTION.md
  angry -> shorter, more direct, fewer jokes, lower/firmer TTS hint,
  no threats, no personal attacks, repair path remains available.
```

Current expression state belongs under `.relaylm/state/`, not in `EMOTION.md`.

### SCENE.md and scenes/*.md

`SCENE.md` defines scene-wiki policy: how scenes are generated, selected, merged, archived, and bounded.

`scenes/*.md` are SLP-maintained scene wiki pages. Active scenes should remain few enough for reliable selection, roughly tens rather than hundreds. `scenes/_inbox/` may grow more freely because it is candidate/staging space.

`SCENE.md` should be the human-editable policy source. It should not become a log of current scene state.

### RelayREL: RELATIONSHIP.md and relationships/*.md

RelayREL is the relationship state and interaction policy layer.

`RELATIONSHIP.md` defines the relationship role and parameter vocabulary:

```text
relationship_roles
trust
attachment
respect_for_autonomy
correction_acceptance
direct_disagreement_permission
teasing_permission
bold_inference_permission
personal_memory_reference_permission
public_familiarity_permission
emo_gain
disclosure boundaries
repair style
```

`relationships/<target>.md` is a target-specific relationship instance. It has meaning only with a concrete target such as `relationships/user.md`.

Boundary:

```text
SOUL = the character itself; portable and target-independent.
REL  = the character-and-target relation; target-specific and not portable by itself.
```

### MEMORY.md and memory/**/*.md

`MEMORY.md` defines memory policy:

```text
what should be remembered
what should not be remembered
memory granularity
recall policy
archive / forgotten / deleted semantics
source-reference policy
personal-memory disclosure rules
SLP auto-apply versus proposal rules
```

`memory/**/*.md` are memory pages, not one-file-per-memory records. One Markdown page is a human editing unit. One memory block is a semantic unit. One retrieval chunk is an internal generated unit.

Use stable block IDs for memory units:

```markdown
## Target user direction ^mem-relaylm-target-user

status:: active
importance:: high
tags:: #relaylm #product-direction

RelayLM should target mid-range GPU local LLM hobbyists and character-AI
experimenters rather than DGX-class infrastructure operators.
```

### BOUNDARY.md

`BOUNDARY.md` defines character-specific boundaries that keep the experience enjoyable and non-creepy.

It owns:

```text
privacy and memory-disclosure limits
public-scene familiarity limits
intimacy and pressure limits
prohibited relationship moves
sensitive inference handling
anger / concern / attachment expression limits
```

It does not replace system safety policy. It is a character-source boundary file that should be compiled into the stable context and used by RelaySCN, RelayEMO, RelayREL, and RelayCTX.

### LORE.md

`LORE.md` is optional. Use it only when the character has enough world, backstory, faction, setting, or proper-noun material that `SOUL.md` would become crowded.

Examples that may need `LORE.md`:

```text
medieval knight
vampire aristocrat
shrine fox spirit
spaceship AI
fantasy academy student
VTuber with a persistent fictional world
```

If the character is a modern local AI companion with light setting, keep the identity in `SOUL.md` and omit `LORE.md`.

## RelaySLP workspace maintenance

RelaySLP is the deferred workspace compiler and curator. It does not answer the current turn.

Target out-of-band path:

```text
current response completes
  -> governed source evidence under .relaylm/sources/
  -> RelaySLP
  -> memory inbox/page candidates
  -> scene inbox/page candidates
  -> relationship update candidates
  -> SOUL / STYLE / EMOTION / SCENE / RELATIONSHIP / MEMORY / BOUNDARY proposals
  -> approval or gated apply
  -> compiled .relaylm/build projections and indexes
```

Recommended apply policy:

```text
Auto-apply allowed:
  memory/inbox additions
  scenes/_inbox additions
  source-reference additions
  low-risk episode summaries
  content-free usage metadata

Conditionally auto-apply:
  memory page consolidation
  scene candidate consolidation
  low-risk relationship continuity notes

Proposal / explicit approval required:
  SOUL.md
  STYLE.md
  EMOTION.md
  SCENE.md
  RELATIONSHIP.md
  MEMORY.md
  BOUNDARY.md
  relationships/<target>.md important parameters
  relationship role assignment such as most_important_person
  sensitive memory
  Forget / Delete / physical purge
```

## KV-cache and context update model

The workspace must compile into context tiers that keep the stable prefix stable for local models.

Recommended tiering:

```text
Tier 0: runtime/system/safety wrapper
  Very stable, outside character workspace.

Tier 1: character stable prefix
  SOUL.md
  STYLE.md
  EMOTION.md
  RELATIONSHIP.md
  MEMORY.md
  BOUNDARY.md
  optional LORE.md
  selected compact SCENE.md policy summary

Tier 2: target/session semi-stable prefix
  selected relationships/<target>.md summary
  selected active scene page summary
  selected stable memory summaries or high-importance memory blocks

Tier 3: dynamic suffix
  .relaylm/state scene_state / emotion_state summaries
  retrieved memory blocks
  current short-term CTX
  latest user input
  request-local policy flags
```

Rules:

1. Uppercase source files should be compact, deliberate, and rarely changed. They are the best KV-cache anchors.
2. Lowercase wiki pages may change more often, but only selected summaries or blocks should enter the prompt.
3. `.relaylm/state/**` may change every turn and belongs in the dynamic suffix.
4. `.relaylm/build/**` may be regenerated whenever sources change, but generation should preserve content hashes and stable fragment IDs so unchanged tiers can be reused.
5. Do not inject all memory pages or all scene pages. Compile and select.
6. Prefer replacement/consolidation over append-only growth in uppercase files.
7. SLP must not rewrite uppercase files during the normal response loop.

## Practical update frequency

| Source | Expected update frequency | Default writer | Context tier |
|---|---:|---|---|
| `SOUL.md` | rare | user / approved proposal | Tier 1 |
| `STYLE.md` | rare | user / approved proposal | Tier 1 |
| `EMOTION.md` | rare | user / approved proposal | Tier 1 |
| `SCENE.md` | rare | user / approved proposal | Tier 1 compact policy |
| `RELATIONSHIP.md` | rare | user / approved proposal | Tier 1 |
| `MEMORY.md` | rare | user / approved proposal | Tier 1 |
| `BOUNDARY.md` | rare | user / approved proposal | Tier 1 |
| `LORE.md` | rare/optional | user / approved proposal | Tier 1 when present |
| `relationships/user.md` | slow | user / approved or gated REL proposal | Tier 2 selected target |
| `scenes/_inbox/*.md` | moderate | RelaySLP | not directly injected |
| `scenes/*.md` | occasional | RelaySLP / user | Tier 2 selected scene |
| `memory/inbox/*.md` | frequent | RelaySLP | not directly injected |
| `memory/**/*.md` | moderate | RelaySLP / user | selected blocks only |
| `.relaylm/sources/**` | frequent | runtime / SLP | never prompt source by default |
| `.relaylm/state/**` | per turn/session | runtime | Tier 3 |
| `.relaylm/build/**` | generated | compiler | selected compiled artifacts |

## Runtime composition invariants

When sources conflict, preserve this authority order:

```text
1. runtime/system/safety constraints
2. BOUNDARY.md
3. SOUL.md
4. RELATIONSHIP.md + selected relationships/<target>.md
5. SCENE.md + selected scene policy
6. EMOTION.md + current emotion state
7. STYLE.md
8. MEMORY.md + selected memory evidence
9. current conversation context
```

Expression rendering may combine STYLE, EMOTION, SCENE, and REL, but lower layers must not override higher invariants.

Examples:

```text
SOUL says the character is quick to anger.
EMOTION.md says angry responses become shorter and more direct.
relationships/user.md says the user is a valued co-creator.
SCENE.md says public scenes suppress anger expression.
BOUNDARY.md says anger must not become coercion or personal attack.
```

The result should be a consistent character whose emotion is visible but bounded by relationship, scene, and boundary policy.

## UI target

SOUL Lab should be rebuilt around the Character Workspace model.

Recommended top-level surfaces:

```text
Home
  conversation and recent workspace changes

Character
  SOUL / STYLE / EMOTION / BOUNDARY / optional LORE

Scenes
  SCENE policy, active scenes, scene inbox

Relationships
  RELATIONSHIP vocabulary, relationships/user.md, pending REL proposals

Memory Wiki
  memory pages, blocks, links, archive, forgotten items

Runtime
  latest used scene, emotion, relationship, memory, and context projection

Advanced
  memory_id, revision, pin_state, queue, worker, audit, raw projections
```

Pin / Unpin, revision IDs, queue states, worker records, and apply tokens are advanced diagnostics or internal governance concepts. The default UX should use character/workspace vocabulary such as important, active, archived, forgotten, proposal, and source.

## Migration interpretation

Legacy target names map as follows:

```text
OUTPUT_POLICY.md
  -> STYLE.md for voice/output surface
  -> MEMORY.md / BOUNDARY.md for memory-disclosure and privacy policy when appropriate

RELATIONSHIP_ANCHOR.md
  -> RELATIONSHIP.md for role/parameter definitions
  -> relationships/<target>.md for concrete relationship state

SCENE_STATE.md
  -> .relaylm/state/scene_state.json for current state
  -> SCENE.md / scenes/*.md for scene policy and scene wiki

STABLE_MEMORY_SUMMARY.md
  -> MEMORY.md for policy
  -> memory/**/*.md for human-readable memory pages
  -> .relaylm/build/memory_units.jsonl for compiled units
```

This migration is target architecture. Existing compatibility tooling may continue to accept older filenames until a dedicated implementation PR changes parser allowlists, examples, smoke tests, UI routes, and migration commands atomically.

## Summary

```text
RelayLM character workspace is a Markdown-first character source tree.

Human-editable uppercase files define the character and policy layer.
SLP-maintained lowercase wiki pages grow scene, memory, and relationship instances.
.relaylm generated artifacts compile them into cache-friendly runtime projections.
```
