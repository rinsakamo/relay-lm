---
relaylm_doc_type: subsystem_architecture
relaylm_authority: character_workspace_source_parser_validation_and_compiler_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace source-tree classification or validation responsibility changes
  - Markdown parser ownership or source-domain naming changes
  - deterministic compiler projection or build-domain responsibility changes
  - workspace cache-tier or source-to-projection boundary changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact parser dataclasses, validation enums, compiler artifact schemas, or CLI flags
  - exact runtime activation, RelayCTX selection, RelayREL, RelaySCN, RelayEMO, or RelayMEM semantics
  - character creation/import, SLP maintenance apply, UI editing, or active-character selection
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - system.md
  - ../../contracts/character-workspace/source-tree.md
  - ../../contracts/character-workspace/parser-and-validation.md
  - ../../contracts/character-workspace/compiled-projections.md
  - ../file_first_character_workspace_design.md
  - ../context/context-assembly.md
  - ../relationship/relationship-state.md
  - ../scene/scene-model.md
  - ../memory/system.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace parser/compiler maintainers
  - RelayCTX, RelayREL, RelaySCN, RelayMEM, and workspace integration maintainers
  - character creation, maintenance, UI, migration, and documentation reviewers
relaylm_authority_level: subsystem
---
# Character Workspace Source Compiler

## Purpose

This page is the canonical subsystem architecture for the Character Workspace source-tree boundary, read-only parsing and validation, and deterministic source-to-projection compilation.

It combines the stable responsibilities established by CW-A1 and CW-A2 without turning parser or compiler success into runtime activation.

The permanent boundary is:

```text
workspace source tree
  -> classify paths and source domains
  -> validate read-only
  -> parse bounded Markdown structure
  -> compile deterministic derived projections
  -> explicit downstream selection / activation by owning components
```

The editable source tree remains authoritative for character/workspace content. `.relaylm/build/**` is derived build output. Current runtime state and activation remain separately owned.

## Source compiler boundary

The source compiler owns four durable responsibilities:

1. classify workspace-relative paths into accepted source/generated domains;
2. validate an existing workspace without mutating it;
3. parse Markdown sources into bounded deterministic source/fragment representations;
4. compile accepted sources into deterministic generated projections under the build domain.

It does not own:

- active-character selection;
- current relationship target identity;
- current scene selection;
- current affect state;
- ordinary-memory reader selection;
- runtime prompt inclusion;
- SLP candidate approval/apply;
- source editing or creation approval.

## Three authority classes

The compiler preserves the parent Character Workspace distinction among three classes.

### Human-editable uppercase source

Root uppercase Markdown sources are deliberate character/workspace policy:

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

These files are source inputs, not generated projections and not current runtime state.

### Lowercase wiki and target-instance material

Lowercase workspace paths may contain relationship instances, scene pages, memory pages, inbox/staging material, and proposals under their owning contracts.

Examples include:

```text
relationships/<target>.md
relationships/_inbox/**
scenes/*.md
scenes/_inbox/**
memory/**/*.md
proposals/**
```

Path classification does not grant activation or prompt authority to these files.

### Generated/internal `.relaylm/**`

`.relaylm/**` contains generated or operational material such as sources, state, build artifacts, indexes, projections, audit, and queue content.

Only the accepted build subdomain is writable by the deterministic compiler described here. Other `.relaylm/**` domains remain owned by their runtime/deferred systems.

## Path classification is deterministic

Workspace path classification is a pure responsibility boundary.

Stable rules include:

- only workspace-relative paths are accepted;
- absolute paths are not source paths;
- parent traversal is rejected;
- exact root uppercase filenames map to durable-source classes;
- lowercase relationship/scene/memory domains are classified distinctly;
- `.relaylm/**` is internal/generated rather than hand-authored character source;
- ambiguous or unsupported paths fail closed rather than being silently reinterpreted.

Classification is not filesystem discovery authority and does not modify the tree.

## Validation is read-only

Workspace validation inspects an existing source tree and reports whether required source structure satisfies the accepted contract.

Validation does not:

- create missing source files;
- create directory skeletons;
- restore sample content;
- choose or activate a default character;
- write build projections;
- mutate lowercase wiki pages;
- repair malformed source automatically.

A missing or invalid required source produces a bounded validation failure. The safe outcome is no compile/activation rather than guessing source content.

## Required and optional durable sources

The accepted root source family includes required durable sources for identity/style/emotion/scene/relationship/memory/boundary policy and an optional lore source.

Exact source-body schemas are outside this page.

The source compiler verifies source presence/classification and parses bounded structure. It does not decide the semantic truth or runtime meaning of every source field.

Those semantics remain with RelaySOUL/STYLE, RelayREL, RelaySCN, RelayEMO, RelayMEM, BOUNDARY/privacy, and downstream component architecture.

## Markdown parsing boundary

The parser converts accepted Markdown source text into deterministic structural material suitable for validation and compilation.

Stable capabilities include recognizing:

- headings;
- optional stable heading anchors;
- bounded metadata lines where supported by the source contract;
- content hashes;
- deterministic block/source order;
- source-relative location and line/block ranges needed by the compiler.

The parser does not promote prose into runtime truth merely because it can parse it.

## Page, semantic unit, and generated fragment are different

A human Markdown page is an editing unit.

A semantic block may be a bounded unit within that page.

A generated compiler fragment or retrieval unit is a derived internal unit.

The permanent distinction is:

```text
Markdown page
  != semantic block
  != generated fragment
  != runtime-selected memory/retrieval chunk
```

This is especially important for memory and scene pages, which must not be forced into one-file-per-record models simply for compiler convenience.

## Stable identifiers and hashes

Deterministic source/fragment identity exists to make generated projections reproducible and traceable to source.

Where accepted source anchors exist, unchanged anchored fragments should retain stable identity across rebuilds.

Where anchors are absent, deterministic source-relative structure may be used by the implementation to derive stable generated identity.

Exact identifier formats remain contract details.

Generated identity does not become a public memory ID, relationship ID, or runtime capability token.

## Compiler input gate

The deterministic compiler consumes only an accepted workspace source tree that has passed the applicable read-only validation boundary.

Invalid or blocked source does not produce a guessed successful build.

The stable flow is:

```text
source tree
  -> validation
  -> parse / normalized source fragments
  -> deterministic compiler
  -> build artifacts
```

A successful parser object alone is not sufficient proof that the whole workspace is valid.

## Compiler output is derived projection

CW-A2 establishes `.relaylm/build/**` as deterministic derived output.

The compiler may emit bounded projections such as workspace manifests, style/emotion projections, scene units, relationship projections, memory units, context-tier projections, and source-to-fragment links under the accepted build contract.

The exact artifact set and schema versions remain implementation-contract details.

The architecture invariant is:

> Generated build artifacts are reproducible projections of source, not a second human-editable authority.

## Build write domain is narrow

The compiler writes only its accepted build output domain.

Compilation must not write or mutate:

- uppercase durable Markdown sources;
- lowercase relationship/scene/memory pages;
- proposal/inbox material;
- `.relaylm/state/**`;
- `.relaylm/sources/**`;
- `.relaylm/audit/**`;
- `.relaylm/queue/**`;
- RelayMEM stores or lifecycle records;
- runtime request payloads.

This keeps source compilation separate from runtime/deferred mutation.

## Dry-run and explicit write

The compiler is dry-run-first under the current bounded implementation.

Dry-run computes the same deterministic build result in memory without writing the build tree.

An explicit write action is required to materialize generated projections.

This distinction protects source inspection/preview workflows from accidental filesystem mutation.

Dry-run success is not runtime activation.

## Deterministic byte output

For the same accepted source tree and compiler contract, generated artifacts should be byte-stable.

Stable requirements include:

- deterministic key/order serialization;
- deterministic JSONL ordering where applicable;
- fixed newline behavior;
- stable source/fragment ordering;
- no random UUIDs in deterministic identity;
- no current timestamps or generated-at fields that make unchanged builds differ;
- no host-specific absolute paths or temporary paths;
- no file mtime as semantic source authority.

Determinism is a reproducibility property, not an activation or trust signal.

## Manifest responsibility

A compiled manifest may summarize source-family presence, source hashes, fragment counts, validation status, build artifact classes, tier summaries, and blocking reason classes.

A manifest is not a substitute for source content and does not become the editable source of truth.

A manifest declaring a source present does not prove that the corresponding runtime component selected it for the current request.

## Style and emotion projection boundaries

Durable STYLE and EMOTION source material may produce deterministic Tier-1 projections for downstream context compilation.

The source compiler does not:

- choose final response style for the current request;
- estimate current affect;
- create current emotion state;
- override scene/relationship/boundary policy;
- write portable character source from runtime affect.

Current affect/expression remains RelayEMO-owned runtime state.

## Scene projection boundary

SCENE policy and accepted active scene pages may produce deterministic scene-related source units/candidate summaries under the compiler contract.

Inbox/staging scene material remains non-active candidate material.

The compiler does not:

- run the scene classifier as current request authority;
- select the active scene for the current request;
- create normalized current `scene_state`;
- write `.relaylm/state/scene_state.json`;
- promote scene inbox material into prompt authority.

RelaySCN remains the runtime scene owner.

## Relationship projection boundary

RELATIONSHIP policy and accepted target relationship pages may produce deterministic vocabulary/projection material.

Relationship inbox/proposal material remains non-active candidate material.

The compiler does not:

- resolve current target identity;
- choose the current relationship instance;
- assign important roles automatically;
- merge relationship state into SOUL;
- apply relationship updates.

RelayREL remains the runtime relationship owner.

## Memory projection boundary

MEMORY policy and accepted memory pages may produce deterministic policy/unit projections.

Memory pages remain human editing units, and blocks may become generated internal units according to the accepted compiler contract.

The compiler does not:

- select the ordinary-memory reader family;
- execute retrieval;
- decide current ranking;
- mutate memory lifecycle;
- restore forgotten material to ordinary candidates;
- run Correct, Forget, Pin/Unpin, Consolidate, or other memory mutation.

RT-1 and RelayMEM runtime/mutation architecture remain authoritative for those decisions.

## Forgotten and inbox material

Candidate/staging and forgotten material retain their owning lifecycle meaning during compilation.

Compilation must not erase lifecycle distinctions simply to produce a uniform unit list.

In particular:

- inbox/candidate material is not automatically stable prompt content;
- forgotten/hidden material is not ordinary active candidate material merely because it remains on disk;
- a generated projection cannot bypass the owning memory/scene/relationship lifecycle.

## Context tier projection

The source compiler may describe deterministic source placement classes used by RelayCTX and backend cache strategy.

At responsibility level:

```text
Tier 0
  runtime/system/safety wrapper outside workspace source authority

Tier 1
  stable approved character/workspace policy

Tier 2
  selected target/session semi-stable relationship/scene/memory material

Tier 3
  current runtime state, retrieval, CTX, and current input
```

CW-A2 can compile source-side tier projections. It does not inject current Tier-3 runtime content itself.

## Cache stability is subordinate to source authority

Stable source-derived prefixes are valuable for local-model prefix/KV reuse.

Cache reuse cannot override a changed source hash, changed target/scene selection, invalid validation state, or newer runtime authority.

A byte-stable old projection is stale when its accepted source revision is no longer current.

## RelayCTX consumption boundary

RelayCTX may consume selected approved compiled projections according to current request authority.

The source compiler does not decide what every request receives.

The stable separation is:

```text
source compiler
  builds deterministic source-derived projections

RelayCTX and upstream semantic owners
  decide request-local eligible context
```

Compilation of memory/relationship/scene material therefore does not imply automatic prompt inclusion.

## Source versus projection versus activation

This is a core invariant:

```text
source exists
  != source validates
  != source parses
  != build compiles
  != build is approved/current
  != runtime activates or selects it
```

Likewise:

```text
build artifact exists
  != current component authority
  != current request consumption
```

Each transition belongs to an explicit owner.

## Rebuild and deletion semantics

Generated projections are reproducible derived state.

Deleting and rebuilding the build domain must not delete accepted source files or invent source replacements.

A failed rebuild preserves the fact that source remains source; it must not silently fall back to an unrelated stale build without an explicitly accepted runtime contract.

Exact transactional build/recovery behavior remains implementation-contract territory.

## Public diagnostics are content-free

Validation/compiler public projections may expose bounded metadata such as:

- workspace/source validation status;
- source family/file class;
- content hashes;
- line/block/fragment counts;
- artifact names/classes;
- artifact hashes;
- tier counts;
- blocking/reason IDs;
- deterministic status booleans.

They do not expose by default:

- raw Markdown bodies;
- memory prose;
- relationship notes;
- scene bodies;
- private filesystem roots;
- protected source evidence;
- queue/runtime payloads;
- runtime-private identifiers;
- unrestricted generated internals.

Content-free diagnostics do not make the underlying source/build artifacts public.

## Failure behavior

The source compiler fails closed toward no build/no activation rather than source invention.

```text
invalid path
  -> reject classification/use

missing required source
  -> validation failure
  -> no successful compile

malformed source
  -> bounded parse/validation failure
  -> no guessed source meaning

compiler failure
  -> no fabricated successful projection
  -> source remains authoritative

build exists but is stale/invalid
  -> downstream owner must not treat it as newer authority

public projection requested
  -> emit only allowlisted content-free diagnostics
```

## Current versus target

This page is current as the canonical responsibility map for the source parser/validator/compiler boundary.

Current CW-A1 provides the bounded read-only source-tree/path/parser/validation contract. Current CW-A2 provides the bounded deterministic build projection compiler.

Richer source schemas, compiler artifacts, transactional rebuild mechanics, source editing APIs, deeper runtime integration, and future cache optimizations may remain target or separately evolving implementation details.

Project Status remains authoritative for exact implementation completion.

## Stable invariants

- Workspace path classification is deterministic and rejects unsafe/ambiguous source paths.
- Workspace validation is read-only and never creates or restores a character source tree.
- Markdown parsing yields bounded deterministic structure; parsing does not make prose runtime truth.
- Human pages, semantic blocks, generated fragments, and runtime-selected chunks remain distinct.
- Build artifacts are deterministic derived projections, not editable source authority.
- Compiler writes are restricted to the accepted build domain.
- Dry-run does not mutate the workspace.
- Deterministic output excludes incidental time/host/randomness sources.
- Scene/relationship/memory compilation does not take current runtime semantic authority.
- Inbox/proposal/forgotten lifecycle distinctions are not erased by compilation.
- Cache-friendly tiers remain subordinate to source/runtime authority.
- Compile success does not imply runtime activation or prompt inclusion.
- Public diagnostics remain content-free by default.
- Failure closes toward no build/no activation, not guessed source or broader authority.

## Non-goals

This architecture does not define:

- exact parser classes or field schemas;
- exact compiler JSON/JSONL schemas or schema versions;
- exact CLI syntax;
- current target identity or scene selection;
- current affect inference;
- ordinary-memory reader selection, retrieval, ranking, or mutation;
- RelayCTX request-local selection algorithm;
- character creation/import/activation workflow;
- SLP maintenance apply behavior;
- UI editor behavior;
- repository-level project sequencing.

## Related architecture

- [Character Workspace Architecture](system.md)
- [Character Workspace Source Tree Contract](../../contracts/character-workspace/source-tree.md)
- [Character Workspace Parser and Validation Contract](../../contracts/character-workspace/parser-and-validation.md)
- [Character Workspace Compiled Projections Contract](../../contracts/character-workspace/compiled-projections.md)
- [File-first Character Workspace Design](../file_first_character_workspace_design.md)
- [RelayCTX Context Assembly](../context/context-assembly.md)
- [RelayREL Relationship State](../relationship/relationship-state.md)
- [RelaySCN Scene Model](../scene/scene-model.md)
- [RelayMEM System](../memory/system.md)
