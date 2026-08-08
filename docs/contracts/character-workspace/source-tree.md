---
relaylm_doc_type: contract
relaylm_authority: character_workspace_source_tree_path_classification_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace root source filenames change
  - workspace-relative path classification changes
  - generated/internal workspace domains change
  - public path-classification projection changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - Markdown parsing, source validation, or compiler projection schemas
  - character creation, import, approval, or activation
  - RelayREL, RelaySCN, RelayEMO, RelayMEM, RelayCTX, or RelaySLP semantics
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - ../../architecture/character-workspace/source-compiler.md
  - ../../architecture/character-workspace/system.md
  - ../../architecture/cw_a1_file_first_source_tree_parser_contracts.md
relaylm_verified_by:
  - ../../../scripts/relaylm_cw_a1_file_first_workspace_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace path/parser/compiler maintainers
  - workspace UI, creation, import, and maintenance integrations
  - documentation and security reviewers
relaylm_authority_level: exact_contract
---
# Character Workspace Source Tree Contract

## Authority summary

This contract owns the exact current Character Workspace source-tree vocabulary and workspace-relative path-classification behavior implemented by `relaylm.character_workspace`.

It formalizes only the source-tree boundary. Markdown parsing/validation and deterministic compiler projections are separate contract responsibilities.

The classifier is filesystem-free and read-only. Classification never creates, edits, validates, compiles, approves, or activates workspace content.

## Workspace root

All paths governed by this contract are interpreted relative to one character workspace root:

```text
characters/<character>/
```

The path-classification API receives a workspace-relative path. The character root itself is outside the relative-path value.

## Contract schema version

Current public path-classification projections use:

```text
relaylm.character_workspace.v0
```

This schema identifier does not imply that every Character Workspace API shares the same lifecycle or that a classified path is valid/active content.

## Required human-editable root sources

The exact required root source filenames are, in this order:

```text
SOUL.md
STYLE.md
EMOTION.md
SCENE.md
RELATIONSHIP.md
MEMORY.md
BOUNDARY.md
```

A required source is recognized only when the normalized path consists of exactly that one root filename.

## Optional human-editable root sources

The exact optional root source filename set is:

```text
LORE.md
```

An optional source is recognized only when the normalized path consists of exactly that one root filename.

## Source-kind mapping

For required and optional root source filenames, `source_kind` is the lowercase filename stem:

| Filename | `source_kind` |
|---|---|
| `SOUL.md` | `soul` |
| `STYLE.md` | `style` |
| `EMOTION.md` | `emotion` |
| `SCENE.md` | `scene` |
| `RELATIONSHIP.md` | `relationship` |
| `MEMORY.md` | `memory` |
| `BOUNDARY.md` | `boundary` |
| `LORE.md` | `lore` |

No other path receives a source kind from this mapping.

## Expected lowercase workspace directories

The current layout vocabulary exposes these lowercase user-inspectable workspace directories:

```text
relationships
relationships/_inbox
scenes
scenes/_inbox
memory
memory/people
memory/projects
memory/topics
memory/episodes
memory/inbox
memory/forgotten
```

These directory names describe current workspace layout. Their presence does not by itself make every descendant an active runtime input.

## Proposal directories

The current proposal directory vocabulary is:

```text
proposals/soul
proposals/style
proposals/emotion
proposals/scene
proposals/relationship
proposals/memory
proposals/boundary
```

The allowed proposal domain identifiers are exactly:

```text
soul
style
emotion
scene
relationship
memory
boundary
```

Any normalized path beginning with `proposals/<allowed-domain>/...` or equal to the allowed domain path is classified as proposal material by the path classifier. Classification does not approve or apply the proposal.

## Internal directories

The current internal/generated directory vocabulary is:

```text
.relaylm/sources/conversations
.relaylm/sources/corrections
.relaylm/sources/imports
.relaylm/state
.relaylm/build
.relaylm/indexes
.relaylm/projections
.relaylm/audit
.relaylm/queue
```

Everything whose normalized first component is `.relaylm` is internal to the Character Workspace rather than hand-authored root source.

Within `.relaylm/**`:

- `.relaylm/sources/**` is `internal_source_evidence`;
- `.relaylm/state/**` is `internal_state`;
- every other `.relaylm` path is `internal_generated`.

The bare `.relaylm` path and unrecognized `.relaylm/<domain>/**` descendants therefore classify as `internal_generated` under current behavior.

## Current internal state files

The layout vocabulary identifies these current internal state files:

```text
.relaylm/state/scene_state.json
.relaylm/state/emotion_state.json
.relaylm/state/relationship_state_cache.json
```

Their listing here does not transfer semantic ownership of scene, emotion, or relationship state to the source-tree classifier.

## Current build-file vocabulary

The layout vocabulary identifies these current generated build files:

```text
.relaylm/build/character_manifest.json
.relaylm/build/style_projection.json
.relaylm/build/emotion_projection.json
.relaylm/build/scene_units.jsonl
.relaylm/build/relationship_projection.json
.relaylm/build/memory_units.jsonl
.relaylm/build/context_projection.json
.relaylm/build/links.jsonl
```

The path classifier treats these as `internal_generated`. Exact compiler artifact contents and write semantics belong to the compiler contract, not this source-tree contract.

## Path-kind enum

The exact current path-kind values are:

```text
required_source
optional_source
relationship_page
scene_page
memory_page
proposal
internal_generated
internal_state
internal_source_evidence
unknown
```

No additional path kind is inferred from prose, file contents, runtime state, or downstream semantic ownership.

## Path normalization

`classify_character_workspace_path(relative_path)` first normalizes the supplied value without filesystem access.

Current normalization rules are:

1. convert the input to text;
2. replace backslashes with `/`;
3. reject the empty string and `.` with reason ID `empty_path`;
4. reject a leading `/`, a leading `//`, or a Windows drive-form prefix matching `<letter>:/` or `<letter>:` with reason ID `path_escape_rejected`;
5. split on `/` and reject any empty component, `.` component, or `..` component with reason ID `path_escape_rejected`;
6. parse the remaining path as POSIX-relative syntax;
7. reject if that normalized path is absolute;
8. otherwise use its POSIX form as the normalized path.

A normalization failure returns `unknown` classification and does not attempt a filesystem lookup or path repair.

## Classification order

After successful normalization, current classification is deterministic and ordered:

1. exact one-component required root source filename -> `required_source`;
2. exact one-component optional root source filename -> `optional_source`;
3. first component `.relaylm` -> internal classification;
4. first component `relationships` plus a qualifying Markdown filename -> `relationship_page`;
5. first component `scenes` plus a qualifying Markdown filename -> `scene_page`;
6. first component `memory` plus a qualifying Markdown filename -> `memory_page`;
7. first component `proposals` plus an allowed second-component proposal domain -> `proposal`;
8. otherwise -> `unknown` with reason ID `unrecognized_workspace_path`.

This order is normative for current behavior because the same normalized path must not be reinterpreted differently by callers.

## Lowercase Markdown-page qualification

Relationship, scene, and memory page classification requires:

- at least two path components;
- a final filename ending in `.md`;
- the final filename to equal its own lowercase form.

The current classifier applies this lowercase check to the final Markdown filename. It does not inspect file contents and does not use filesystem metadata.

Examples:

```text
relationships/rin.md       -> relationship_page
scenes/home.md             -> scene_page
memory/topics/relaylm.md   -> memory_page
relationships/Rin.md       -> unknown
scenes/HOME.md             -> unknown
memory/NOTE.md             -> unknown
```

These examples describe classifier results only. They do not establish activation, lifecycle, or semantic validity.

## Domain values

The exact current `domain` values emitted by classification are:

| Path kind | `domain` |
|---|---|
| `required_source` | `source` |
| `optional_source` | `source` |
| `relationship_page` | `relationship` |
| `scene_page` | `scene` |
| `memory_page` | `memory` |
| `proposal` | the allowed proposal domain |
| `internal_source_evidence` | `internal_source_evidence` |
| `internal_state` | `internal_state` |
| `internal_generated` | `internal_generated` |
| `unknown` | `unknown` |

Domain is a classifier output. It is not a capability, disclosure grant, lifecycle state, or runtime activation decision.

## Classification result shape

The current runtime classification object carries:

```text
kind
normalized_path
domain
source_kind
reason_ids
```

`source_kind` is present only where the classifier assigns the root-source filename mapping. `reason_ids` is a tuple of bounded reason identifiers.

The runtime object may carry the normalized path, but public projection is more restrictive.

## Public classification projection

`CharacterWorkspacePathClassification.to_public_dict()` emits exactly these common keys:

```text
schema_version
kind
domain
source_kind
reason_ids
content_free
```

with:

```text
schema_version = "relaylm.character_workspace.v0"
content_free = true
```

For `required_source` and `optional_source` only, the projection additionally emits:

```text
filename
```

The public projection does not emit `normalized_path` for relationship, scene, memory, proposal, internal, or unknown paths.

This prevents the general classifier diagnostic from becoming a public filesystem/path inventory.

## Reason IDs owned by path classification

The exact reason IDs produced directly by current path normalization/classification are:

```text
empty_path
path_escape_rejected
unrecognized_workspace_path
```

Other Character Workspace validation or parser error IDs are not owned by this contract.

## Filesystem non-authority

Path classification must not:

- read whether a path exists;
- resolve symlinks;
- create directories or files;
- validate Markdown contents;
- infer current character activation;
- compile generated projections;
- mutate `.relaylm/**` state;
- repair rejected paths.

A caller that needs any of those effects must use the separately owned validation/compiler/runtime boundary.

## Classification is not validation

A path can classify into a known kind while the containing workspace or file remains invalid, missing, malformed, stale, unapproved, hidden, or otherwise ineligible for downstream use.

The invariant is:

```text
classified
  != exists
  != validates
  != parses
  != compiles
  != approved
  != activated
```

This contract therefore cannot be used as a runtime activation gate by itself.

## Classification is not semantic ownership

The names `relationship`, `scene`, `memory`, `state`, and `source` identify workspace path domains only.

They do not grant the source-tree layer authority to:

- resolve current relationship identity;
- classify current scene;
- estimate current affect;
- select or mutate memory;
- choose context packing;
- approve proposals;
- disclose protected material.

Those semantics remain with their owning architecture/contracts.

## Failure behavior

Current path-classification failures are content-free and fail closed:

```text
empty / dot path
  -> unknown
  -> normalized_path = ""
  -> reason_ids = ("empty_path",)

absolute / drive / empty-segment / dot-segment / parent-traversal path
  -> unknown
  -> normalized_path = ""
  -> reason_ids = ("path_escape_rejected",)

recognized-safe syntax but unsupported workspace path
  -> unknown
  -> normalized_path = normalized safe path
  -> reason_ids = ("unrecognized_workspace_path",)
```

No failure path guesses the intended source domain.

## Current implementation anchors

This current contract is implemented by:

```text
relaylm/character_workspace/_constants.py
relaylm/character_workspace/_pathing.py
relaylm/character_workspace/_types.py
```

The current focused smoke is:

```text
scripts/relaylm_cw_a1_file_first_workspace_smoke.py
```

The older CW-A1 implementation handoff remains a transitional source until a later reviewed retirement transaction accounts for all of its parser/validation normative content and incoming references. This contract does not retire that source.

## Stable invariants

- Source-tree paths are workspace-relative and normalized without filesystem access.
- Empty, absolute, drive-form, empty-segment, dot-segment, and parent-traversal paths fail closed.
- Required and optional root sources are exact one-component filename matches.
- Relationship, scene, and memory pages require a lowercase `.md` final filename.
- `.relaylm/**` is always internal rather than hand-authored root source.
- Proposal classification is limited to the exact allowed proposal domains.
- Path-kind, domain, source-kind, and reason IDs are deterministic for the same input.
- Classification performs no file I/O and no mutation.
- Public classification diagnostics omit general normalized workspace paths and remain content-free.
- Path classification does not imply validation, compilation, approval, activation, disclosure, or semantic authority.
- Current behavior is defined by the exact contract and current implementation anchors; Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- Markdown block parsing or metadata syntax;
- workspace validation status precedence;
- reserved-path conflict validation;
- source size limits;
- manifest enumeration limits;
- compiler artifact schemas or deterministic serialization details;
- build write/apply behavior;
- creation/import commit behavior;
- SLP maintenance candidates;
- current relationship, scene, affect, memory, or context semantics;
- source retirement or router migration.

## Related architecture

- [Character Workspace Source Compiler](../../architecture/character-workspace/source-compiler.md)
- [Character Workspace System](../../architecture/character-workspace/system.md)
- [CW-A1 transitional implementation handoff](../../architecture/cw_a1_file_first_source_tree_parser_contracts.md)
