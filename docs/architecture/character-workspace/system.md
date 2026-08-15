---
relaylm_doc_type: subsystem_architecture
relaylm_authority: file_first_character_workspace_system_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace editable-source or generated-artifact boundary changes
  - source parser/compiler, workspace UI, maintenance, or creation/import responsibility changes
  - activation/approval or runtime projection ownership changes
  - relationship, scene, memory, context, or SLP workspace integration changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact Markdown, parser, compiler, manifest, projection, candidate, proposal, UI, or API schemas
  - exact RelayMEM, RelayREL, RelaySCN, RelayEMO, RelayCTX, or RelaySLP runtime semantics
  - exact filesystem transaction, template-registry, or remote-import implementation
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../file_first_character_workspace_design.md
  - ../../contracts/character-workspace/source-tree.md
  - ../../contracts/character-workspace/parser-and-validation.md
  - ../../contracts/character-workspace/compiled-projections.md
  - ../ui/soul-lab.md
  - ../cw_a4_slp_workspace_maintenance_candidates.md
  - creation-and-import.md
  - ../pipeline-responsibilities.md
  - ../context/context-assembly.md
  - ../relationship/relationship-state.md
  - ../scene/scene-model.md
  - ../memory/system.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace and SOUL Lab maintainers
  - RelaySLP, RelayCTX, RelayREL, RelaySCN, RelayMEM, and compiler maintainers
  - character creation, template, migration, and documentation reviewers
relaylm_authority_level: subsystem
---
# Character Workspace Architecture

## Purpose

This page is the canonical parent architecture for RelayLM's file-first Character Workspace.

The workspace presents a local, human-editable character source tree while compiling deterministic generated artifacts for runtime and deferred maintenance consumers.

The stable responsibility model is:

```text
human-editable character sources
  -> read-only parser / validation
  -> deterministic compiled projections
  -> explicitly selected runtime/deferred consumers

runtime/deferred evidence
  -> bounded maintenance candidates/proposals
  -> approval/gated apply
  -> source/wiki update
  -> deterministic rebuild
```

The workspace is not an internal memory-database administration panel. Human-editable sources remain ordinary files, while generated runtime state, indexes, queues, projections, and audit material remain clearly separated.

## Three source classes

The permanent workspace distinguishes three visible authority classes.

### Uppercase durable sources

Uppercase Markdown files are deliberate human-editable character policy and identity sources:

```text
SOUL.md
STYLE.md
EMOTION.md
SCENE.md
RELATIONSHIP.md
MEMORY.md
BOUNDARY.md
optional LORE.md
```

They are intended to be compact, reviewable, comparatively stable, and suitable for explicit user editing.

They do not become current runtime state merely because the files exist.

### Lowercase wiki / target-instance sources

Lowercase workspace content carries SLP-maintained or user-inspectable material such as:

```text
relationships/<target>.md
relationships/_inbox/**
scenes/*.md
scenes/_inbox/**
memory/**/*.md
proposals/**
```

These are not all equivalent authority classes. A current target relationship page, an inbox candidate, an approved memory page, and a proposal have different owners and activation rules.

Lowercase naming means workspace-maintained/instance material, not automatic prompt inclusion.

### `.relaylm/**` generated/runtime material

`.relaylm/**` contains generated or operational artifacts such as:

- governed source evidence;
- current transient state;
- deterministic build projections;
- indexes;
- queues;
- audit/diagnostic artifacts;
- other runtime-private generated state.

These artifacts are not ordinary hand-authored character source.

Persistence inside `.relaylm/**` does not by itself make an artifact character identity, memory truth, relationship truth, or active scene authority.

## Portable character identity

`SOUL.md` owns portable character identity and durable invariants.

`STYLE.md`, `EMOTION.md`, `BOUNDARY.md`, and optional `LORE.md` provide adjacent durable policy while retaining their own responsibility.

Portable sources must not absorb:

- target-specific relationship instances;
- current scene state;
- current affect state;
- current conversation working state;
- raw memory pages;
- queue/worker state;
- arbitrary client instruction history.

A strong target relationship or repeated current scene does not automatically mutate portable character identity.

## Relationship workspace boundary

`RELATIONSHIP.md` defines the relationship vocabulary/policy available to RelayREL.

`relationships/<target>.md` contains target-specific relationship state.

The stable split is:

```text
portable character
  != relationship vocabulary
  != target-specific relationship instance
```

The workspace supplies source material; RelayREL remains the semantic runtime owner of target-specific relationship policy.

Changing or creating a relationship source does not make a browser-selected target or guessed display name authoritative identity.

## Scene workspace boundary

`SCENE.md` defines scene-wiki generation/selection/consolidation policy.

`scenes/*.md` may contain reusable scene material; `scenes/_inbox/**` is candidate/staging space.

RelaySCN remains the current scene-policy owner.

A scene page, classifier match, or scene candidate is not automatically active scene state.

Current request-local scene state requires the owning RelaySCN authority and source-precedence/activation rules.

## Memory workspace boundary

`MEMORY.md` defines durable memory policy such as what to remember, recall/archive/disclosure policy, and SLP apply/proposal boundaries.

`memory/**/*.md` provides human-scale memory pages under the owning memory contracts.

A Markdown page is an editing unit, not necessarily a one-record database row or one retrieval chunk.

The workspace does not select ordinary-memory reader authority. RT-1 and RelayMEM Retrieval remain responsible for current ordinary reader selection and retrieval eligibility.

A memory file existing in the workspace does not bypass lifecycle, scope, reader, privacy, or disclosure gates.

Workspace memory representation follows the [Memory Subsystem stable design principles](../memory/system.md#stable-design-principles). Governed Evidence is not collapsed into SLP-curated wiki pages, and Markdown layout, filesystem taxonomy, indexes, embeddings, or compiled retrieval projections remain representation/discovery mechanisms rather than semantic memory authority.

## Boundary source

`BOUNDARY.md` contains character-specific expression/privacy/intimacy/pressure/disclosure limits.

It supplements but never replaces system/runtime safety policy.

Compiled boundary policy may constrain RelayREL, RelaySCN, RelayEMO, RelayCTX, and social expression while remaining an approved durable character source rather than a transient runtime result.

## Read-only source parsing

The current CW-A1 boundary provides deterministic read-only classification, validation, and Markdown parsing for an existing workspace.

Stable principles are:

- parsing does not mutate the source tree;
- workspace-relative paths are classified into explicit source domains;
- naming and ownership are validated before generated consumers rely on them;
- malformed or ambiguous source fails closed rather than being silently reclassified;
- public validation/manifest diagnostics remain content-free;
- parser success does not mean runtime activation.

Exact parser objects, error IDs, bounds, and schemas remain implementation details.

## Deterministic compiler

CW-A2 compiles accepted workspace sources into deterministic `.relaylm/build/**` artifacts.

The source tree remains the editable source of truth.

Compiler output is derived projection, not a second editable authority.

Stable compiler properties include:

- deterministic bytes for the same source tree;
- stable ordering and fragment/unit identity where the source is unchanged;
- no incidental host path, mtime, random UUID, or current-time pollution of deterministic artifacts;
- dry-run before explicit write by default;
- build output restricted to the accepted generated domain;
- generated artifacts do not mutate uppercase/lowercase source files merely by compilation.

Deleting/rebuilding generated projections must not erase accepted source authority.

## Cache and context tiers

Workspace sources compile into stability tiers that support local-model prefix/KV reuse while preserving authority.

Conceptually:

```text
Tier 0
  runtime/system/safety wrapper

Tier 1
  stable approved character sources

Tier 2
  target/session semi-stable relationship, scene, and selected memory summaries

Tier 3
  current scene/affect/retrieval/CTX/input state
```

The exact compiled block selection remains owned by RelayCTX and the applicable subsystem owners.

Cache stability never overrides a newer source revision or current relationship/scene/privacy decision.

## Character Workspace UI

CW-A3 reorganizes the SOUL Lab product surface around the workspace model.

Canonical user-facing areas may expose responsibilities such as:

- Home/conversation;
- Character;
- Scenes;
- Relationships;
- Memory Wiki;
- Runtime;
- Advanced/governance surfaces.

UI visibility is not source authority.

A browser card, local preview, cached source projection, stale request, or selected tab cannot activate a source or commit a mutation by itself.

Server-side authority and explicit write/apply boundaries remain required for durable changes.

## Deferred workspace maintenance

RelaySLP owns deferred candidate/proposal planning for workspace maintenance under its accepted contracts.

CW-A4 currently provides a dry-run-first planner for bounded Memory Wiki, Scene Wiki, and Relationship candidates/proposals.

The stable path is:

```text
completed governed evidence
  -> deferred candidate/proposal planning
  -> hold/review/approval/gated apply
  -> source/wiki change under owning authority
  -> rebuild generated projections
```

The maintenance planner does not answer the current conversation turn and does not gain current RelayMEM/RelaySCN/RelayREL authority merely because it proposes workspace changes.

Inbox/candidate content is not direct prompt-injection authority.

## Maintenance safety classes

The workspace distinguishes low-risk generated/wiki maintenance from durable character-policy changes.

Bounded low-risk additions may be eligible for more automatic handling under their exact contracts.

High-impact sources remain proposal/review-oriented, especially changes to:

- SOUL;
- STYLE;
- EMOTION policy;
- SCENE policy;
- RELATIONSHIP vocabulary/important target parameters;
- MEMORY policy;
- BOUNDARY;
- sensitive memory/lifecycle actions;
- destructive Forget/Delete/Purge semantics.

This parent page does not define exact auto-apply policy; it preserves the principle that current-turn runtime observation does not silently rewrite high-authority character sources.

## Character creation and import

CW-A5 provides bounded character creation, templates, and import flows.

The stable creation model is:

```text
no valid workspace
  -> creation/import surface
  -> candidate source tree
  -> deterministic validation
  -> compiled preview
  -> explicit approval/commit
  -> deterministic build projections
  -> active character only through explicit accepted activation
```

No valid workspace does not justify silently creating/restoring/activating a default sample character.

Templates/showcase packs remain source candidates until explicit creation/commit.

## Quick and Advanced creation

Quick Create and Advanced Create are different authoring experiences over the same full source model, not separate reduced/full character formats.

Both remain subject to validation and explicit commit.

Advanced editing does not bypass source ownership; Quick Create does not bypass required source families merely because the UI is simpler.

## Template boundary

Template packs provide content, not executable trust.

A safe template/import flow validates manifests and paths, rejects unsafe path traversal/symlink/executable behavior according to its owning contract, and never activates a character merely because template files were discovered.

Remote registries, if introduced, require separately governed provenance/trust behavior; they are not implied by local template support.

## Activation is separate from source existence

This is a core invariant.

```text
source exists
  != source validated
  != source compiled
  != source approved
  != source activated for current runtime
```

Likewise:

```text
candidate exists
  != proposal approved
  != source committed
  != build regenerated
  != current request consumes it
```

Each transition belongs to an explicit owner.

## Runtime consumption boundary

RelayCTX consumes selected compiled/approved projections rather than pasting the entire workspace tree into every prompt.

RelayREL, RelaySCN, RelayEMO, RelayMEM, and RelayCTX retain their semantic runtime ownership.

The workspace provides sources/projections and maintenance flows; it is not a universal runtime decision owner.

## Source versus projection versus state

The architecture preserves three distinct concepts:

```text
source
  human/SLP-maintained durable input under explicit ownership

projection
  deterministic derived artifact rebuilt from sources

runtime state
  request/session/process operational state under its component owner
```

A current runtime state is not written back to a durable source merely because it persisted long enough to be useful.

A projection is not hand-edited source merely because it is readable JSON/JSONL.

## Privacy and diagnostics

Workspace content is potentially sensitive.

Generic/public diagnostics remain content-free by default.

They may expose bounded values such as:

- source-family presence;
- validation status;
- build/projection presence;
- counts;
- source classes;
- candidate/proposal classes;
- approval-required booleans;
- reason/error IDs;
- active-character availability status.

They do not expose by default:

- source bodies;
- memory prose;
- relationship notes;
- scene bodies;
- private paths;
- raw prompts;
- protected source evidence;
- unrestricted manifest internals.

A content-bearing editor/management surface requires explicit access authority and is not made public merely because it lives in the workspace UI.

## Fail-closed behavior

Workspace flows close toward no activation/no mutation when authority is incomplete.

```text
invalid source tree
  -> validation failure
  -> no compile/activation

compile failure
  -> source remains authoritative
  -> no guessed generated projection

candidate/proposal invalid
  -> hold/reject
  -> no source mutation

creation/import invalid
  -> no workspace commit
  -> no active-character mutation

stale UI state
  -> reject/discard stale result
  -> do not apply under a different character/source scope
```

## Current versus target

This page is current as the canonical Character Workspace responsibility map.

The bounded CW-A1 through CW-A5 implementation slices establish source parsing, deterministic compilation, workspace-oriented UI, deferred maintenance candidate planning, and explicit creation/import boundaries.

The broader file-first design may still contain target capabilities beyond those bounded slices, including richer source-editing APIs, more complete maintenance apply flows, remote template/registry behavior, or deeper runtime integration.

Project Status remains authoritative for exact implementation completion.

## Stable invariants

- Human-editable sources, lowercase workspace/wiki material, and `.relaylm/**` generated/runtime artifacts remain distinct classes.
- Portable character identity does not absorb target relationship, current scene, current affect, current CTX, or raw memory/runtime state.
- Source parsing/validation is read-only.
- Deterministic build output is derived projection, not a second editable authority.
- Compile success is not runtime activation.
- RelaySLP maintenance is deferred and candidate/proposal driven; it does not answer the current turn.
- Inbox/candidate/proposal content is not direct prompt authority.
- Memory workspace curation does not replace governed Evidence; derived summaries or subjective wiki pages cannot rewrite the Evidence authority they reference.
- Filesystem organization, indexes, embeddings, and retrieval projections are representation/discovery mechanisms, not canonical memory truth or semantic mutation authority.
- High-impact character policy changes require their owning review/apply boundary.
- Creation/import commits a validated workspace only after explicit approval.
- No valid workspace does not cause automatic sample/default character activation.
- Runtime components retain REL/SCN/EMO/MEM/CTX semantic authority.
- Context assembly consumes selected projections rather than the entire workspace tree.
- Generic diagnostics remain content-free by default.
- Missing/invalid/stale workspace authority fails closed toward no activation/no mutation.

## Non-goals

This parent architecture does not define:

- exact Markdown/source schemas;
- exact parser/compiler/build schemas;
- exact UI route/component behavior;
- exact candidate/proposal/apply schemas;
- exact character creation/template/import fields;
- automatic active-character selection;
- remote registry trust policy;
- runtime memory/relationship/scene/affect/context semantics;
- project-level implementation sequencing.

## Related architecture

- [File-first Character Workspace Design](../file_first_character_workspace_design.md)
- [Character Workspace Source Tree Contract](../../contracts/character-workspace/source-tree.md)
- [Character Workspace Parser and Validation Contract](../../contracts/character-workspace/parser-and-validation.md)
- [Character Workspace Compiled Projections Contract](../../contracts/character-workspace/compiled-projections.md)
- [SOUL Lab UI Architecture](../ui/soul-lab.md)
- [CW-A4 Workspace Maintenance Candidates](../cw_a4_slp_workspace_maintenance_candidates.md)
- [Character Workspace Creation and Import](creation-and-import.md)
- [RelayCTX Context Assembly](../context/context-assembly.md)
- [RelayREL Relationship State](../relationship/relationship-state.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [Memory Subsystem Architecture](../memory/system.md)
