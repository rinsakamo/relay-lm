---
relaylm_doc_type: contract
relaylm_authority: character_workspace_compiler_projection_and_build_write_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace compiler result or artifact schema changes
  - deterministic fragment/unit identity or serialization changes
  - build write-domain or path-safety behavior changes
  - compiler tier projection or public diagnostics changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - source-tree classification or Markdown parser/validation behavior
  - runtime RelayCTX selection or prompt injection
  - RelayREL, RelaySCN, RelayEMO, RelayMEM, or RelaySLP semantic decisions
  - character creation/import, approval, activation, or source retirement
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - source-tree.md
  - parser-and-validation.md
  - ../../architecture/character-workspace/source-compiler.md
  - ../../architecture/character-workspace/system.md
  - ../../architecture/cw_a2_workspace_compiler_projections.md
relaylm_verified_by:
  - ../../../scripts/relaylm_cw_a2_workspace_compiler_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace compiler maintainers
  - RelayCTX and workspace integration maintainers
  - UI, maintenance, migration, performance, and security reviewers
relaylm_authority_level: exact_contract
---
# Character Workspace Compiled Projections Contract

## Authority summary

This contract owns the exact current deterministic Character Workspace compiler result, generated artifact set, source-derived fragment/unit projection behavior, and explicit `.relaylm/build/**` write boundary implemented by `relaylm.character_workspace`.

It consumes the separately owned source-tree and parser/validation contracts.

The current lifecycle is:

```text
workspace source tree
  -> compiler preflight
  -> read-only workspace validation
  -> in-memory deterministic compile
  -> compiler result
  -> optional explicit build write
```

The editable source tree remains source authority. Generated artifacts are derived projections. Compile success does not approve or activate a character and does not inject the projection into a request.

## Compiler identity

The exact current compiler identity is:

```text
COMPILER_NAME = relaylm.character_workspace_compiler
COMPILER_SCHEMA_VERSION = relaylm.character_workspace.compiler_result.v0
```

The compiler consumes the workspace schema version owned by the source/parser layer:

```text
relaylm.character_workspace.v0
```

## Expected artifact set and order

The exact current artifact sequence is:

```text
character_manifest.json
style_projection.json
emotion_projection.json
scene_units.jsonl
relationship_projection.json
memory_units.jsonl
context_projection.json
links.jsonl
```

`EXPECTED_ARTIFACTS` preserves this order.

Every materialized artifact path is exactly:

```text
.relaylm/build/<artifact-name>
```

The compiler does not add arbitrary artifact names to this set.

## Artifact schema versions

The exact current artifact schema mapping is:

| Artifact | Schema version |
|---|---|
| `character_manifest.json` | `relaylm.character_workspace.character_manifest.v0` |
| `style_projection.json` | `relaylm.character_workspace.style_projection.v0` |
| `emotion_projection.json` | `relaylm.character_workspace.emotion_projection.v0` |
| `scene_units.jsonl` | `relaylm.character_workspace.scene_units.v0` |
| `relationship_projection.json` | `relaylm.character_workspace.relationship_projection.v0` |
| `memory_units.jsonl` | `relaylm.character_workspace.memory_units.v0` |
| `context_projection.json` | `relaylm.character_workspace.context_projection.v0` |
| `links.jsonl` | `relaylm.character_workspace.links.v0` |

## Compile entry point

The exact current core entry point is:

```text
compile_character_workspace(root, *, write=False)
```

`write=False` is the default.

The default path computes artifacts in memory and performs no build-file write.

`write=True` uses the same in-memory compile result and then calls the explicit build-write boundary after successful compilation.

The invariant is:

```text
dry-run artifact bytes == write-mode pre-write artifact bytes
```

for the same accepted source tree and compiler implementation.

## Compiler result shape

`CharacterWorkspaceCompileResult` carries exactly:

```text
schema_version
generated_by
status
is_valid
character_id
artifacts
reason_ids
blocking_reason_ids
content_free
```

For a successful current compile:

```text
schema_version = relaylm.character_workspace.compiler_result.v0
generated_by = relaylm.character_workspace_compiler
status = valid
is_valid = true
reason_ids = ()
blocking_reason_ids = ()
content_free = true
```

`artifacts` contains the eight generated artifact objects in `EXPECTED_ARTIFACTS` order.

## Blocked result

A blocked compile result contains no artifacts.

Current `_blocked_result(...)` behavior is:

```text
is_valid = false
artifacts = ()
reason_ids = de-duplicated input reasons preserving first occurrence
blocking_reason_ids = the same reason tuple
content_free = true
```

The default blocked status is:

```text
invalid_workspace
```

Callers may receive a more specific current status such as a validation status or `path_escape_rejected` where the current implementation supplies one.

## Compiler preflight

Before workspace validation, current compiler preflight checks the root argument itself.

If the text form of the root contains a path component equal to `..`, compilation is blocked with:

```text
path_traversal_rejected
```

If the root does not exist or is not a directory, compilation is blocked with:

```text
workspace_root_missing_or_not_directory
```

The compiler then checks symlinks under the workspace root before validating source contents.

## Symlink escape preflight

The compiler resolves the workspace root and inspects every symlink found by `root.rglob("*")`.

If resolving a symlink fails, or if the resolved symlink target is outside the resolved workspace root, compilation is blocked with:

```text
symlink_escape_rejected
```

This check occurs before the parser/validation result is used for a successful compile.

An escaping uppercase source symlink therefore fails for symlink escape rather than being followed and interpreted as ordinary source content.

## Validation gate

After root and symlink preflight, the compiler calls:

```text
validate_character_workspace(root, character_id=root.name, public=False)
```

A validation result with `is_valid = false` blocks compilation before artifact construction.

The compiler carries validation reason IDs into the blocked result; when validation reason IDs are empty it falls back to the validation status value.

A source parse object by itself is not sufficient to authorize a successful workspace compile.

## Build artifact object

Each `CharacterWorkspaceBuildArtifact` carries exactly:

```text
name
relative_path
schema_version
content
content_hash
```

`content` is the exact UTF-8 artifact bytes.

`content_hash` is:

```text
sha256:<64 lowercase hexadecimal digits>
```

computed over those exact artifact bytes.

`text()` decodes `content` as UTF-8.

## Public artifact projection

`CharacterWorkspaceBuildArtifact.to_public_dict()` emits exactly:

```text
name
relative_path
schema_version
content_hash
byte_count
content_free
```

with `content_free = true`.

It does not emit artifact bytes or raw source bodies.

## Public compiler projection

`build_character_workspace_compiler_projection(root, *, write=False)` returns `compile_character_workspace(...).to_public_dict()`.

The public compile projection emits:

```text
schema_version
generated_by
status
is_valid
character_id
artifact_names
artifact_count
artifact_summaries
tier_counts
reason_ids
blocking_reason_ids
content_free
```

with `content_free = true`.

The public helper inherits the same default dry-run behavior. Passing `write=True` explicitly requests the same write behavior as the core compiler.

## Deterministic JSON bytes

Current JSON artifacts use exactly the equivalent of:

```text
json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
```

encoded as UTF-8.

Consequences:

- object keys are sorted;
- compact separators are used;
- non-ASCII text is not ASCII-escaped by serialization;
- every serialized JSON object ends with one newline.

## Deterministic JSONL bytes

Current JSONL artifacts serialize each row through the same deterministic JSON serializer and concatenate those newline-terminated row bytes.

An empty row sequence therefore produces empty bytes. Non-empty JSONL contains exactly one deterministic newline per row.

## Incidental-state exclusion

Current deterministic artifacts intentionally exclude incidental host/runtime inputs such as:

- current timestamps or generated-at values;
- file modification times;
- random UUIDs;
- host temp paths;
- absolute workspace paths;
- runtime queue records;
- runtime-private payloads;
- raw full source bodies.

Byte stability is a build reproducibility property, not proof that an artifact is current or activated.

## Stable hash helpers

Current text and byte hash forms are:

```text
_content_hash(text) = sha256 UTF-8 text
_bytes_hash(content) = sha256 exact bytes
```

Both are exposed in textual `sha256:<hex>` form inside generated structures where used.

`_stable_hash(*values)` hashes the deterministic JSON serialization of the supplied values.

`_hash_many(values)` sorts the supplied hash strings, replacing a false/null value with an empty string, then stable-hashes that tuple.

## Stable generated identifiers

Current source fragments and page units use deterministic IDs derived from:

- domain;
- workspace-relative source path;
- accepted block anchor or heading-derived identity;
- per-source occurrence count.

The current ID builder also includes a 12-hex SHA-256 prefix of the relative path so distinct relative paths that normalize similarly do not silently collide.

For anchored blocks it includes an 8-hex SHA-256 prefix of the anchor text plus the anchor value. For unanchored blocks it includes a 12-hex SHA-256 prefix of heading/root text and the literal fragment label `heading`.

The assembled identifier is normalized by the current safe-ID helper to lowercase characters drawn from its accepted alphanumeric/period/underscore/colon/hyphen surface.

Duplicate anchors within one source are distinguished by occurrence count.

Generated fragment/unit IDs are internal deterministic projection identities. They are not RelayMEM public memory IDs, runtime capabilities, or source approval tokens.

## Heading and metadata privacy in generated units

Current generated uppercase fragments and page units do not store raw heading text in their `heading` field; that field is `null` under current construction.

Where a heading exists, a deterministic `heading_hash` may be present.

Generated units expose metadata keys and a content-free metadata map only for allowlisted metadata keys:

```text
status
importance
priority
scope
```

The generated metadata map records the presence of an allowlisted key as `true`; it does not copy the metadata value.

Raw body content is marked absent with:

```text
raw_body_included = false
```

## Uppercase Tier-1 source set

Current `UPPERCASE_TIER1_SOURCES` is:

```text
SOUL.md
STYLE.md
EMOTION.md
RELATIONSHIP.md
MEMORY.md
BOUNDARY.md
LORE.md
```

`SCENE.md` is also treated as a Tier-1 prompt candidate by current compiler logic even though it is handled separately for scene policy-unit construction.

The compiler does not make runtime prompt inclusion decisions merely by emitting a Tier-1 projection.

## Tier order

The exact current tier order is:

```text
tier0
tier1
tier2
tier3
```

Current meanings in `context_projection.json` are:

- `tier0`: runtime/system/safety wrapper, runtime-owned, compiler does not own its fragments;
- `tier1`: character stable prefix, Character Workspace-owned source projection;
- `tier2`: target/session semi-stable prefix, selected later by a selector or RelayCTX; compiler owns candidate metadata only;
- `tier3`: dynamic suffix, runtime-request-path-owned and required to belong last; compiler does not generate its runtime fragments.

## Tier-3 placeholders

The exact current dynamic-suffix placeholder vocabulary is:

```text
.relaylm/state/scene_state.json
.relaylm/state/emotion_state.json
retrieved_memory_blocks
current_short_term_ctx
latest_user_input
request_local_policy_flags
```

The compiler records these placeholders. It does not inject their current runtime values.

## Uppercase fragments

Uppercase source results are processed in filename-sorted order and each source's parsed blocks are processed in parser order.

Each generated fragment includes current fields such as:

```text
fragment_id
source_path
source_kind
heading
heading_hash
heading_level
has_anchor
metadata
metadata_keys
content_hash
source_content_hash
tier
prompt_candidate
```

with `heading = null` and content-free metadata behavior as defined above.

## Lowercase page enumeration

Scene, relationship, and memory page collection recursively enumerates `.md` files in the relevant domain using deterministic path sort.

If the domain root does not exist, the collector returns no units.

If the domain root exists but is not a directory, compilation is blocked as an invalid workspace with `reserved_path_conflict`.

Every page is read as UTF-8. Decode failure blocks with `malformed_markdown` plus `source_file_not_utf8`; read failure blocks with `invalid_workspace` plus `source_file_unreadable`.

The page's workspace-relative path is reclassified through the source-tree classifier. A classifier reason blocks with `path_escape_rejected`.

## Common page-unit shape

Current generated page units include:

```text
unit_id
fragment_id
unit_domain
unit_kind
source_path
source_stage
artifact_name
heading
heading_hash
heading_level
has_anchor
metadata
metadata_keys
content_hash
source_content_hash
tier
prompt_candidate
candidate_only
raw_body_included
```

For current generated page units:

```text
fragment_id = unit_id
heading = null
raw_body_included = false
candidate_only = not prompt_candidate
```

## Scene page units

Current scene page behavior is:

```text
scenes/_inbox/** -> source_stage = staging_candidate
                    prompt_candidate = false
                    tier = staging

other scenes/**/*.md -> source_stage = active
                        prompt_candidate = true
                        tier = tier2
```

Scene page units use:

```text
unit_domain = scene
unit_kind = scene_page
artifact_name = scene_units.jsonl
```

`SCENE.md` policy fragments are separately converted to Tier-1 `scene_policy` units and combined with scene-page units in `scene_units.jsonl`.

## Relationship page units

Current relationship page behavior is:

```text
relationships/_inbox/** -> source_stage = proposal_candidate
                           prompt_candidate = false
                           tier = staging

other relationships/**/*.md -> source_stage = active
                                prompt_candidate = true
                                tier = tier2
```

Relationship page units use:

```text
unit_domain = relationship
unit_kind = relationship_page
artifact_name = relationship_projection.json
```

`RELATIONSHIP.md` policy fragments are projected as Tier-1 policy fragments and combined with target relationship units inside `relationship_projection.json`.

## Memory page stages

Current memory stage mapping uses the first domain component after `memory`:

```text
memory/forgotten/** -> forgotten_excluded
memory/inbox/**     -> staging_candidate
other memory/**    -> active
```

Initial tier/candidate behavior is:

```text
forgotten_excluded -> tier = excluded, prompt_candidate = false
staging_candidate  -> tier = staging, prompt_candidate = false
active             -> candidate evaluated per block
```

## Memory block prompt-candidate filter

For an active memory page, a block is a prompt candidate only when either:

```text
status:: active
status:: stable
importance:: high
importance:: critical
```

is present under current case-insensitive value comparison.

If none of those conditions is true, the active block is emitted as staging/candidate-only rather than as a Tier-2 prompt candidate.

Forgotten blocks stay excluded regardless of metadata. Inbox blocks stay staging regardless of metadata.

Memory page units use:

```text
unit_domain = memory
unit_kind = memory_block
artifact_name = memory_units.jsonl
```

This compiler classification does not restore, retrieve, rank, or mutate RelayMEM memory.

## Policy units

Current scene and memory policy units derived from uppercase policy fragments use:

```text
source_stage = policy
tier = tier1
prompt_candidate = true
candidate_only = false
raw_body_included = false
```

They inherit deterministic fragment ID, source path/kind, heading hash, metadata-key structure, and content hashes from the source fragment.

## `character_manifest.json`

The current generated manifest includes the common artifact envelope plus current workspace/build summary fields including:

```text
character_id
workspace_schema_version
workspace_format
required_source_presence
optional_lore_presence
lowercase_wiki_domain_presence
build_artifact_schema_versions
source_file_hashes
fragment_count
tier_summary
validation_status
is_valid
blocking_reason_ids
content_policy
```

Its `content_policy` records false for current prohibited/incidental fields including absolute paths, raw full source bodies, memory IDs, queue records, runtime-private payloads, and timestamps.

This generated manifest is different from the read-only validation manifest owned by `parser-and-validation.md`.

## `style_projection.json`

Current style projection is derived from `STYLE.md` fragments at Tier 1.

It includes `projection_owner = STYLE.md`, a fixed current scope describing style/output-surface ownership and non-ownership, and `surface_fragments`.

It does not own SOUL identity, memory truth, relationship permission, scene selection, or runtime state.

## `emotion_projection.json`

Current emotion projection is derived from `EMOTION.md` fragments at Tier 1.

It includes `projection_owner = EMOTION.md`, a fixed current scope, `emotion_profile_fragments`, and a state-write policy declaring:

```text
writes_relaylm_state = false
current_emotion_state_saved = false
```

Compilation does not write current affect state.

## `scene_units.jsonl`

Current scene units are the concatenation of Tier-1 SCENE policy units and generated scene-page units, then sorted by the current unit sort key:

```text
source_path
unit_id
content_hash
```

Inbox scene units remain staging/non-prompt candidates.

## `relationship_projection.json`

Current relationship projection combines:

- Tier-1 `RELATIONSHIP.md` policy fragments;
- deterministically sorted relationship-page target units.

It declares Tier 1 for policy and Tier 2 for target-summary candidates while retaining the individual unit's actual staging/prompt flags for inbox material.

It does not rewrite RelayREL policy or auto-apply important relationship parameters.

## `memory_units.jsonl`

Current memory units combine Tier-1 MEMORY policy units and lowercase memory-page block units, then sort by the current unit sort key.

Forgotten units remain `tier = excluded` and `prompt_candidate = false`.

Inbox units remain staging/candidate-only.

Active units become Tier-2 prompt candidates only under the current block metadata filter.

## `context_projection.json`

Current context projection includes:

- exact `tier_order`;
- the four tier descriptions;
- Tier-1 stable-prefix fragment list;
- Tier-2 semi-stable candidate fragment list;
- Tier-3 dynamic-suffix contract and placeholders;
- byte-stability indicators;
- content-hash summary;
- content-free public-safe projection summary.

The Tier-2 list contains only generated units whose current tier is `tier2` and whose `prompt_candidate` is true.

The compiler records:

```text
runtime_prompt_injection = false
```

inside the public-safe summary.

## `links.jsonl`

Current links include two relations for each uppercase fragment:

```text
source_file_to_fragment
fragment_to_projection_artifact
```

and two relations for each generated scene/relationship/memory page unit:

```text
page_to_unit
unit_to_projection_artifact
```

Links are sorted by:

```text
link_type
from
to
```

Each row carries the links artifact schema version, compiler identity, deterministic link ID, relation endpoints, content hash, `contains_absolute_path = false`, and `content_free = true`.

## Common artifact envelope

Current JSON-object artifacts use a shared base containing:

```text
schema_version
generated_by
diagnostics_only
workspace_format
content_hash
source_fragments
```

with:

```text
generated_by = relaylm.character_workspace_compiler
diagnostics_only = false
workspace_format = relaylm.character_workspace.v0
```

Artifact-specific fields are then added.

JSONL unit rows use their own exact row shapes rather than this object envelope.

## Source-to-artifact mapping

For current uppercase fragments, link projection maps source files as follows:

```text
STYLE.md        -> style_projection.json
EMOTION.md      -> emotion_projection.json
SCENE.md        -> scene_units.jsonl
RELATIONSHIP.md -> relationship_projection.json
MEMORY.md       -> memory_units.jsonl
other uppercase source -> context_projection.json
```

This mapping controls generated link metadata only. It does not mean the compiler owns the runtime semantics of each source family.

## Tier counts in public projection

When `context_projection.json` exists and parses as JSON, public compiler tier counts are derived as:

```text
tier0 = 1
tier1 = len(stable_prefix_fragment_list)
tier2_candidates = len(semi_stable_candidate_fragment_list)
tier3_placeholders = len(dynamic_suffix_contract.placeholders)
```

If no artifacts or no context projection exist, tier counts are empty. If context JSON cannot be parsed, tier counts are empty.

## Explicit write boundary

`write_character_workspace_build_artifacts(root, result)` rejects an invalid compile result with `ValueError`.

For a valid result, it obtains the safe build root and writes only expected artifact names beneath `.relaylm/build`.

The write boundary does not modify uppercase source files, lowercase wiki pages, `.relaylm/state/**`, `.relaylm/sources/**`, `.relaylm/audit/**`, or `.relaylm/queue/**`.

## Safe build-root rules

Before writing, current code rejects a `.relaylm` symlink or `.relaylm/build` symlink.

The resolved build root must remain inside the resolved workspace root.

An escaped build directory raises `ValueError` rather than writing outside the workspace.

## Per-artifact write rules

For each artifact:

- artifact name must equal the target basename;
- artifact name must be in `EXPECTED_ARTIFACTS`;
- a target symlink is rejected;
- resolved target must remain under the workspace root;
- an existing target directory is rejected;
- an existing ordinary file/hardlink path is unlinked before the new bytes are written;
- exact in-memory artifact bytes are then written;
- the returned tuple records `.relaylm/build/<artifact-name>` in artifact order.

Unlink-before-write prevents an existing hardlink at the artifact path from mutating its other inode alias, including a source file alias.

## Build write return value

A successful explicit write returns the tuple of written workspace-relative artifact paths in the same order as `result.artifacts`.

The write function does not return approval or runtime activation state.

## Source mutation non-authority

Compilation and build writing do not mutate:

- required or optional uppercase sources;
- lowercase scene pages;
- lowercase relationship pages;
- lowercase memory pages;
- proposal/inbox source material;
- `.relaylm/state/**`;
- `.relaylm/sources/**`;
- `.relaylm/audit/**`;
- `.relaylm/queue/**`;
- RelayMEM stores;
- request/runtime state.

A generated artifact can be deleted and rebuilt from source without becoming source authority.

## Runtime semantic non-authority

Compiler output does not itself:

- select the active character;
- decide current relationship target;
- classify the current scene;
- estimate current affect;
- select ordinary memory reader family;
- retrieve/rank memory;
- choose current request context;
- inject Tier-3 runtime content;
- apply SLP proposals;
- authorize protected disclosure.

The invariant remains:

```text
source exists
  != source validates
  != compile succeeds
  != artifact is current/approved
  != runtime selects or activates artifact
```

## Content-free diagnostic boundary

Compiler public projections expose bounded names, schema versions, hashes, byte counts, tier counts, fixed statuses, and reason IDs.

Generated artifact contents themselves are derived runtime/build data and are not made public merely because the public summary is content-free.

Current compiler smoke additionally verifies that generated artifacts avoid fixture raw memory, relationship, scene, queue, runtime-private, and private-heading values used to probe leakage.

## Current implementation anchors

This contract is implemented by:

```text
relaylm/character_workspace/_compiler.py
```

and consumes:

```text
relaylm/character_workspace/_constants.py
relaylm/character_workspace/_pathing.py
relaylm/character_workspace/_parser.py
relaylm/character_workspace/_validation.py
relaylm/character_workspace/_types.py
```

The focused current smoke is:

```text
scripts/relaylm_cw_a2_workspace_compiler_smoke.py
```

The older CW-A2 implementation handoff remains transitional until a later reviewed retirement transaction accounts for incoming references and complete normative disposition. This contract does not retire it.

## Stable invariants

- Default compilation is dry-run and performs no build write.
- Invalid root, traversal, symlink escape, or workspace validation blocks a successful build.
- A blocked compile result contains no artifacts.
- Successful compiles emit exactly the eight expected artifacts in deterministic order.
- JSON/JSONL serialization is deterministic for the same accepted source state.
- Generated artifacts exclude incidental timestamps, mtimes, absolute paths, random UUIDs, raw full source bodies, queue records, and runtime-private payloads.
- Stable fragment/unit identity derives from workspace-relative source structure and deterministic occurrence handling.
- Generated heading text and metadata values are not copied into current content-free fragment/unit structures.
- Scene/relationship inbox material remains staging/non-prompt candidate material.
- Forgotten memory material remains excluded from ordinary prompt candidates.
- Active memory blocks become Tier-2 prompt candidates only under the current metadata filter.
- Tier 0 and Tier 3 remain runtime-owned; Tier 2 remains candidate metadata pending downstream selection.
- Compiler success does not perform RelayCTX runtime prompt injection.
- Explicit write is restricted to expected `.relaylm/build/**` artifacts and rejects symlink/path escape.
- Existing artifact paths are unlinked before replacement, preventing hardlink writes through to source aliases.
- Compilation does not mutate source, current state, queues, RelayMEM stores, or runtime semantic authority.
- Public compiler diagnostics are content-free.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- source-tree path classification already owned by `source-tree.md`;
- Markdown parsing/validation already owned by `parser-and-validation.md`;
- semantic schemas for uppercase source bodies;
- runtime RelayCTX selection or Tier-3 injection;
- current scene/relationship/affect/memory decisions;
- creation/import or current-character activation;
- SLP maintenance apply behavior;
- UI editing behavior;
- source retirement or documentation migration;
- repository-level project sequencing.

## Related architecture and contracts

- [Character Workspace Source Tree Contract](source-tree.md)
- [Character Workspace Parser and Validation Contract](parser-and-validation.md)
- [Character Workspace Source Compiler](../../architecture/character-workspace/source-compiler.md)
- [Character Workspace System](../../architecture/character-workspace/system.md)
- [CW-A2 transitional implementation handoff](../../architecture/cw_a2_workspace_compiler_projections.md)
