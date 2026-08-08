---
relaylm_doc_type: contract
relaylm_authority: character_workspace_markdown_parser_validation_and_manifest_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace Markdown parser syntax changes
  - source-file parse limits or error identifiers change
  - workspace validation precedence or reserved-path checks change
  - validation/manifest public projection changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - workspace path classification vocabulary owned by the source-tree contract
  - compiler artifacts, build writes, approval, or runtime activation
  - semantic schemas for SOUL, STYLE, EMOTION, SCENE, RELATIONSHIP, MEMORY, BOUNDARY, or LORE
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - source-tree.md
  - ../../architecture/character-workspace/source-compiler.md
  - ../../architecture/character-workspace/system.md
  - ../../architecture/cw_a1_file_first_source_tree_parser_contracts.md
relaylm_verified_by:
  - ../../../scripts/relaylm_cw_a1_file_first_workspace_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace parser/compiler maintainers
  - workspace validation, UI, creation, import, and maintenance integrations
  - documentation and security reviewers
relaylm_authority_level: exact_contract
---
# Character Workspace Parser and Validation Contract

## Authority summary

This contract owns the exact current read-only Character Workspace Markdown parser, source-file parse results, workspace validation, layout projection, and read-only manifest behavior implemented by `relaylm.character_workspace`.

Path vocabulary and path classification are owned by [Character Workspace Source Tree Contract](source-tree.md). Deterministic compiler projections and build writes are separate responsibilities.

The current boundary is:

```text
classified workspace vocabulary
  -> bounded UTF-8 source read
  -> structural Markdown parse
  -> read-only workspace validation
  -> optional content-free projection / manifest summary
```

Parsing or validation success does not compile, approve, select, or activate source content.

## Shared projection schema

Current public parser, validation, and manifest projections use:

```text
relaylm.character_workspace.v0
```

The exact current file bounds are:

```text
MAX_SOURCE_FILE_BYTES = 512 * 1024
MAX_MANIFEST_ENTRIES = 4096
```

A source is rejected for size only when filesystem-reported `st_size` is strictly greater than `MAX_SOURCE_FILE_BYTES`.

The manifest counts each `workspace_root.rglob("*")` result. When the counter becomes greater than `MAX_MANIFEST_ENTRIES`, enumeration stops and `manifest_entry_limit_reached` is appended to the manifest reason IDs. That reason does not independently change workspace validation status or `is_valid`.

## Validation status enum

The exact current values are:

```text
valid
missing_required_source
invalid_character_id
invalid_root
path_escape_rejected
reserved_path_conflict
malformed_markdown
```

`path_escape_rejected` is part of the shared enum but is not currently selected by the top-level `validate_character_workspace` control flow.

## Character ID

A supplied `character_id` is valid only when it matches:

```regex
^[A-Za-z0-9_-]{1,128}$
```

If `character_id` is omitted, validation may continue with `None`.

An invalid supplied character ID returns before root inspection with:

```text
status = invalid_character_id
is_valid = false
character_id = null
reason_ids = ("invalid_character_id",)
```

## Workspace-root precondition

After character-ID normalization, the root must exist and be a directory. Otherwise validation returns:

```text
status = invalid_root
is_valid = false
reason_ids = ("workspace_root_missing_or_not_directory",)
```

No repair or skeleton creation occurs.

## Direct source parsing

`parse_character_source_file(path, source_kind, public=False)` accepts only the current source kinds defined by the source-tree filename map:

```text
soul
style
emotion
scene
relationship
memory
boundary
lore
```

An unsupported kind returns:

```text
status = malformed_markdown
source_kind = unknown
error_ids = ("unknown_source_kind",)
```

The direct parser validates the supplied source-kind value. It does not independently require that the filename correspond to that kind. Workspace validation supplies the canonical filename-derived kind.

For a recognized kind, the exact read sequence is:

1. derive `filename` from `Path(path).name`;
2. call `stat()` and read `st_size`;
3. `OSError` from `stat()` -> `source_file_unreadable`;
4. size greater than the limit -> `source_file_too_large`;
5. read as UTF-8 text;
6. decoding failure -> `source_file_not_utf8`;
7. `OSError` while reading -> `source_file_unreadable`;
8. parse Markdown blocks;
9. construct a valid parse result.

The parser does not retry another encoding and does not truncate an oversized source.

## Parse-error result

All current direct source-file precondition failures use `CharacterWorkspaceValidationStatus.MALFORMED_MARKDOWN` and return:

```text
content_hash = null
line_count = 0
block_count = 0
blocks = ()
```

with one of these current direct-parser error IDs:

```text
unknown_source_kind
source_file_unreadable
source_file_too_large
source_file_not_utf8
```

The shared status name does not imply that every such failure is a Markdown-syntax error.

## Successful source result

A successful source read returns:

```text
status = valid
filename = source path basename
source_kind = supplied recognized source kind
content_hash = sha256 hash of complete decoded text
line_count = len(text.splitlines())
block_count = parsed block count
blocks = parsed block tuple
error_ids = ()
```

Content hashes use:

```text
sha256:<64 lowercase hexadecimal digits>
```

and are SHA-256 over the UTF-8 encoding of the exact string supplied to the hashing helper.

## Heading parsing

`parse_markdown_blocks(text, source_path=None)` recognizes headings with:

```regex
^(#{1,6})\s+(.+?)\s*$
```

Current consequences:

- heading levels 1 through 6 are recognized;
- whitespace is required after the hash run;
- the recognized heading occupies the whole line apart from accepted trailing whitespace;
- text that does not match this expression does not start a heading block;
- `source_path` is currently ignored and has no hashing or identity effect.

## Heading anchors

A terminal heading anchor is recognized with:

```regex
(?:^|\s)(\^[A-Za-z0-9][A-Za-z0-9_.:-]*)\s*$
```

An accepted anchor begins with `^`, has an alphanumeric first character after the caret, may continue with alphanumerics, underscore, period, colon, or hyphen, and occurs at the end of heading text apart from trailing whitespace.

When present, the runtime `anchor` stores the caret-prefixed value and `heading` excludes that terminal anchor and its preceding whitespace.

## Metadata parsing

Outside an active code fence, a stripped line is metadata when it matches:

```regex
^([A-Za-z][A-Za-z0-9_-]*)::\s*(.*)$
```

The stored key is lowercased, the stored value is stripped, and pairs remain in encounter order. Duplicate keys are preserved in the runtime tuple.

Metadata parsing is suspended inside fences that start with either of these three-character markers:

- three backticks: `` ` ` ` ``
- three tildes: `~~~`

The first three characters of the opening fence become the active marker. Only a later stripped line beginning with the same marker closes it. A different marker does not close the active fence.

The parser does not otherwise interpret fenced content.

## Blocks when headings exist

When at least one heading is recognized:

- every recognized heading starts one block;
- `start_line` is the one-based heading line;
- the block ends immediately before the next recognized heading, or at the final input line;
- `heading_level` is the number of heading hashes;
- heading and optional anchor use the rules above;
- metadata is parsed from all block lines, including the heading line;
- block hash input is `"\n".join(block_lines)`.

Text before the first recognized heading is not represented as a separate block in current behavior.

## Blocks when no heading exists

If no heading is recognized:

- empty text returns `[]`;
- non-empty text returns exactly one synthetic block;
- `heading_level = 0`;
- `heading = ""`;
- `anchor = null`;
- `start_line = 1`;
- `end_line = len(text.splitlines())`, with the helper's `or 1` fallback;
- metadata is parsed from the input lines;
- block hash input is the original complete text string, not a reconstructed line join.

This preserves current trailing-newline hashing behavior for heading-free text.

## Runtime Markdown block shape

`CharacterMarkdownBlock` carries exactly:

```text
heading_level
heading
anchor
metadata
start_line
end_line
content_hash
```

`metadata` is an ordered tuple of `(key, value)` pairs. `metadata_dict()` converts that tuple to a normal mapping; duplicate keys collapse only at that conversion step.

Its public projection emits:

```text
schema_version
heading_level
has_anchor
metadata_keys
start_line
end_line
content_hash
content_free
```

with `content_free = true`. It omits heading text, anchor text, metadata values, and raw block content. `metadata_keys` preserves encounter order and may contain duplicates.

## Runtime source result and public projection

`CharacterSourceParseResult` carries:

```text
status
filename
source_kind
content_hash
line_count
block_count
blocks
error_ids
```

Its public projection emits exactly:

```text
schema_version
filename
source_kind
status
content_hash
line_count
block_count
error_ids
content_free
```

with `content_free = true`. It does not emit the runtime `blocks` tuple or raw source text.

## Required-source validation

For an existing root, `missing_required_sources` is computed in the required-source order owned by the source-tree contract.

A required source is missing when `workspace_root / filename` is not a file. Optional sources are never added to `missing_required_sources`.

## Reserved-path conflicts

The exact reserved-directory set is constructed from source-tree constants as:

```text
LOWERCASE_WORKSPACE_DIRECTORIES
+ ("proposals",)
+ PROPOSAL_DIRECTORIES
+ (".relaylm", ".relaylm/sources")
+ INTERNAL_DIRECTORIES
```

A conflict is recorded when:

- a required or optional root source path exists but is not a file; or
- a reserved directory path exists but is not a directory.

Conflict values are workspace-relative names/paths. Validation does not repair them.

## Source parsing during validation

Validation checks required plus optional root source filenames in their current concatenated source-tree order. For every path that is a file, it calls the direct parser with the canonical filename-derived source kind and `public=False`.

Missing optional sources are skipped. Any source result whose `is_valid` property is false contributes to the malformed-source condition.

## Reason accumulation and status precedence

After presence, conflict, and parse checks, reason IDs are appended in this exact order when applicable:

```text
missing_required_source
reserved_path_conflict
malformed_markdown
```

The single top-level status uses this precedence:

```text
missing required source -> missing_required_source
else reserved conflict -> reserved_path_conflict
else malformed source -> malformed_markdown
else -> valid
```

`is_valid` is true only for `valid`.

Reason accumulation and status selection are intentionally distinct: lower-precedence reasons may remain visible even when a higher-precedence status wins.

## Workspace validation result

`CharacterWorkspaceValidationResult` carries exactly:

```text
status
is_valid
character_id
missing_required_sources
reason_ids
reserved_conflicts
source_results
content_free
```

Its public projection emits:

```text
schema_version
status
is_valid
character_id
missing_required_sources
reason_ids
reserved_conflict_count
source_results
content_free
```

with `content_free = true` and each source result converted through its public projection. Public validation exposes only the count of reserved conflicts, not their path values.

## Layout projection

`character_workspace_layout()` returns `CharacterWorkspaceLayout` populated from current source-tree constants with exactly these fields:

```text
required_source_filenames
optional_source_filenames
expected_directories
proposal_directories
internal_directories
```

The source-tree contract owns the exact path values. This contract owns only this layout-result projection behavior.

## Read-only manifest

`build_character_workspace_manifest(root, public=False)` is not the CW-A2 compiler and does not write `.relaylm/build/character_manifest.json`.

Current behavior is:

1. convert `root` to `Path`;
2. derive `character_id` from the root basename only when that basename matches the character-ID expression, otherwise use `None`;
3. call workspace validation with that derived ID and `public=False`;
4. if the root exists and is a directory, enumerate `rglob("*")` until the manifest-entry boundary;
5. classify each enumerated relative path through the source-tree classifier;
6. count by classifier domain and path-kind value;
7. store both mappings as key-sorted tuples;
8. preserve validation status, validity, source results, and reason IDs, plus `manifest_entry_limit_reached` if enumeration crossed the limit.

`CharacterWorkspaceManifest` carries exactly:

```text
status
is_valid
character_id
source_results
domain_counts
path_kind_counts
reason_ids
```

Its public projection emits:

```text
schema_version
status
is_valid
character_id
source_results
domain_counts
path_kind_counts
reason_ids
content_free
```

with `content_free = true` and public source-result projections.

## Content-free boundary

Public block, source, validation, and manifest projections may expose bounded structure, hashes, counts, fixed identifiers, filenames for root sources, and the validated character ID.

They do not expose raw Markdown bodies, heading text, anchor values, metadata values, reserved-conflict paths, arbitrary enumerated workspace paths, runtime-private payloads, or semantic activation state.

A hash or count is diagnostic structure; it is not semantic approval or disclosure authority.

## Read-only and semantic non-authority

Parser/validation APIs do not:

- create missing workspace files or directories;
- restore a default character;
- approve character source;
- write compiler build artifacts;
- select the active character, relationship, scene, affect, memory, or context;
- apply proposal or inbox material;
- mutate runtime state;
- publish raw source bodies through public diagnostics.

The invariant remains:

```text
path classified
  != file readable
  != source parsed
  != workspace valid
  != manifest summarized
  != compiler build succeeds
  != approved/current
  != runtime activated
```

## Current implementation anchors

This contract is implemented by:

```text
relaylm/character_workspace/_parser.py
relaylm/character_workspace/_validation.py
relaylm/character_workspace/_types.py
relaylm/character_workspace/_constants.py
```

and consumes path classification from:

```text
relaylm/character_workspace/_pathing.py
```

The focused current smoke is:

```text
scripts/relaylm_cw_a1_file_first_workspace_smoke.py
```

The older CW-A1 handoff remains a transitional source until a later reviewed retirement transaction accounts for remaining consumers and normative disposition. This contract does not retire it.

## Stable invariants

- Source reads are UTF-8 and bounded by the exact current byte limit.
- Direct parse failures use bounded fixed error IDs rather than raw exceptions.
- Structural parsing recognizes only the current heading, terminal-anchor, and metadata forms.
- Metadata inside an active backtick or tilde fence is ignored.
- Content hashes are deterministic SHA-256 strings over the exact current text/block inputs.
- Workspace validation is read-only.
- Invalid supplied character IDs fail before root inspection.
- Missing required sources, reserved conflicts, and malformed results preserve exact status precedence and reason accumulation.
- Public block/source/validation/manifest projections remain content-free and omit raw Markdown bodies.
- Manifest enumeration truncation adds a reason without independently rewriting validation status.
- The manifest is a read-only summary, not a compiler or activation artifact.
- Parsing/validation never grants downstream semantic or runtime authority.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- source-tree path-kind values beyond consuming the source-tree contract;
- semantic schemas for the uppercase source families;
- compiler artifact schemas or deterministic build serialization;
- compiler dry-run/write gates;
- creation/import commit behavior;
- SLP maintenance candidates;
- runtime activation or context selection;
- source retirement, retirement-manifest entries, or router migration.

## Related architecture and contracts

- [Character Workspace Source Tree Contract](source-tree.md)
- [Character Workspace Source Compiler](../../architecture/character-workspace/source-compiler.md)
- [Character Workspace System](../../architecture/character-workspace/system.md)
- [CW-A1 transitional implementation handoff](../../architecture/cw_a1_file_first_source_tree_parser_contracts.md)
