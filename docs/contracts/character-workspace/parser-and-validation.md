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

This contract owns the exact current read-only Character Workspace Markdown parsing, source-file parse result, workspace validation, and read-only manifest behavior implemented by `relaylm.character_workspace`.

It does not define source path classification; that is owned by [Character Workspace Source Tree Contract](source-tree.md). It does not define deterministic compiler projections or build writes.

The central boundary is:

```text
classified workspace source/path vocabulary
  -> bounded file read
  -> structural Markdown parsing
  -> read-only workspace validation
  -> optional content-free public projection / manifest summary
```

Successful parsing or validation does not approve, compile, or activate content.

## Shared schema version

Current public parser/validation/manifest projections use:

```text
relaylm.character_workspace.v0
```

The identifier is a projection schema version. It does not make all Character Workspace concerns one authority.

## Source-file size limit

The current source-file parse limit is exactly:

```text
MAX_SOURCE_FILE_BYTES = 512 * 1024
```

A source whose filesystem-reported size is greater than this value is rejected by the source-file parser with `source_file_too_large`.

The comparison is strict `>`: a file whose reported size equals the limit is not rejected for size alone.

## Manifest enumeration limit

The current read-only manifest enumeration limit is exactly:

```text
MAX_MANIFEST_ENTRIES = 4096
```

The manifest increments its entry counter for each result yielded by `workspace_root.rglob("*")`. When the counter becomes greater than the configured limit, it appends:

```text
manifest_entry_limit_reached
```

and stops further enumeration.

This reason ID does not independently replace the workspace validation status or change `is_valid`; it is an additional manifest reason.

## Validation status enum

The exact current validation status values are:

```text
valid
missing_required_source
invalid_character_id
invalid_root
path_escape_rejected
reserved_path_conflict
malformed_markdown
```

`path_escape_rejected` is part of the shared enum because path classification also uses that vocabulary. The top-level workspace validator does not currently select that status in its own control flow.

## Character ID contract

When a `character_id` argument is supplied to `validate_character_workspace`, it is accepted only when it matches exactly:

```regex
^[A-Za-z0-9_-]{1,128}$
```

Therefore the current accepted character ID alphabet is ASCII letters, digits, underscore, and hyphen, with length from 1 through 128 characters.

If `character_id` is omitted, validation may continue with `None`.

If a supplied character ID fails the expression, validation returns before root inspection with:

```text
status = invalid_character_id
is_valid = false
character_id = null
reason_ids = ("invalid_character_id",)
```

## Workspace root precondition

After character-ID normalization, the workspace root must both exist and be a directory.

Otherwise validation returns:

```text
status = invalid_root
is_valid = false
reason_ids = ("workspace_root_missing_or_not_directory",)
```

No missing-file creation or root repair is attempted.

## Source kinds accepted by direct parsing

`parse_character_source_file(path, source_kind, public=False)` accepts `source_kind` only when it is one of the lowercase source kinds defined by the current source-tree filename mapping:

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

An unsupported `source_kind` returns a parse-error result with:

```text
status = malformed_markdown
source_kind = unknown
error_ids = ("unknown_source_kind",)
```

The direct parser currently validates the supplied source-kind value, not a filename-to-kind pairing. Workspace validation supplies the canonical filename-derived kind when it calls the parser.

## Source-file read sequence

For a recognized source kind, the current parser performs these checks in order:

1. obtain the source filename from `Path(path).name`;
2. call `stat()` and read `st_size`;
3. if `stat()` raises `OSError`, return `source_file_unreadable`;
4. if size is greater than `MAX_SOURCE_FILE_BYTES`, return `source_file_too_large`;
5. read the file as UTF-8 text;
6. if UTF-8 decoding fails, return `source_file_not_utf8`;
7. if the read raises `OSError`, return `source_file_unreadable`;
8. parse Markdown blocks structurally;
9. return a valid source parse result.

The parser does not retry with another encoding and does not truncate an oversized source.

## Parse-error result

All current direct source-file precondition errors use a `CharacterSourceParseResult` whose status is:

```text
malformed_markdown
```

with:

```text
content_hash = null
line_count = 0
block_count = 0
blocks = ()
```

and one bounded `error_ids` tuple identifying the actual cause.

Current direct source-file error IDs are:

```text
unknown_source_kind
source_file_unreadable
source_file_too_large
source_file_not_utf8
```

The status name does not imply that each failure was caused by Markdown syntax. It is the current shared parse-failure status.

## Successful source parse result

On successful UTF-8 read, the parser returns:

```text
status = valid
filename = source path basename
source_kind = supplied recognized source kind
content_hash = sha256 hash of the complete decoded text
line_count = len(text.splitlines())
block_count = number of parsed Markdown blocks
blocks = parsed block tuple
error_ids = ()
```

`content_hash` has the exact textual form:

```text
sha256:<64 lowercase hexadecimal digits>
```

The hash input is the UTF-8 encoding of the exact decoded Python string, including any trailing newline that remains in the string.

## Heading syntax

`parse_markdown_blocks(text, source_path=None)` recognizes headings with the current expression:

```regex
^(#{1,6})\s+(.+?)\s*$
```

Consequences of current behavior include:

- heading levels 1 through 6 are recognized;
- at least one whitespace character is required after the hash run;
- the heading must occupy the whole line aside from trailing whitespace accepted by the expression;
- non-heading text does not create a heading boundary.

The optional `source_path` argument is currently ignored and does not affect parsing, hashing, or identity.

## Heading anchor syntax

At the end of recognized heading text, the parser may recognize one heading anchor using:

```regex
(?:^|\s)(\^[A-Za-z0-9][A-Za-z0-9_.:-]*)\s*$
```

An accepted anchor:

- begins with `^`;
- has an alphanumeric first character after `^`;
- may then contain alphanumerics, underscore, period, colon, or hyphen;
- must occur at the end of the heading text apart from trailing whitespace.

When an anchor is recognized, the block's `anchor` stores the complete caret-prefixed value and the block's `heading` excludes that terminal anchor and preceding whitespace.

## Metadata syntax

Outside fenced code regions, the parser recognizes metadata lines matching:

```regex
^([A-Za-z][A-Za-z0-9_-]*)::\s*(.*)$
```

The parser first strips surrounding whitespace from the line.

For a recognized metadata line:

- the key must begin with an ASCII letter;
- remaining key characters may be ASCII letters, digits, underscore, or hyphen;
- the stored key is lowercased;
- the stored value is stripped of surrounding whitespace;
- metadata is preserved in encounter order as key/value pairs.

Duplicate keys are not collapsed by the parser; tuple order remains observable in the runtime block object.

## Fenced-code exclusion

Metadata recognition is suspended while the parser is inside a current fenced region.

A stripped line beginning with either:

```text
```
~~~
```

opens a fence when no fence is active. The first three characters become the active fence marker.

While a fence is active, metadata parsing is skipped. A later stripped line beginning with the same three-character marker closes it. A different fence marker does not close the active fence.

The parser does not otherwise interpret the fenced body.

## Block construction with headings

When one or more headings are recognized:

- each recognized heading starts one block;
- `start_line` is the one-based heading line;
- the block extends through the line immediately before the next recognized heading;
- the last block extends through the final input line;
- `heading_level` is the number of heading hashes;
- `heading` and optional `anchor` use the rules above;
- metadata is parsed from all lines in that block, including the heading line;
- the block content hash is computed over `"\n".join(block_lines)`.

Text before the first recognized heading is not represented as a separate block under current behavior.

## Block construction without headings

If no heading is recognized:

- an empty input string returns no blocks;
- a non-empty input returns exactly one synthetic block;
- that block has `heading_level = 0`, `heading = ""`, and `anchor = null`;
- `start_line = 1`;
- `end_line = len(text.splitlines())` or `1` if needed by the current helper;
- metadata is parsed from the input lines;
- the content hash is computed over the original complete text string rather than a reconstructed line join.

This preserves the current trailing-newline hashing distinction for the heading-free case.

## Runtime Markdown block shape

The exact current `CharacterMarkdownBlock` fields are:

```text
heading_level
heading
anchor
metadata
start_line
end_line
content_hash
```

`metadata` is an ordered tuple of `(key, value)` pairs.

`metadata_dict()` is a convenience conversion to a mapping; duplicate keys therefore collapse according to normal dictionary construction only when that method is invoked.

## Public Markdown block projection

`CharacterMarkdownBlock.to_public_dict()` emits:

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

where:

```text
schema_version = "relaylm.character_workspace.v0"
content_free = true
```

It does not emit heading text, anchor text, metadata values, or raw block content.

`metadata_keys` preserves the keys in parsed encounter order and may contain duplicates.

## Public source parse projection

`CharacterSourceParseResult.to_public_dict()` emits exactly:

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

with `content_free = true`.

It does not emit the parsed block bodies or the runtime `blocks` tuple.

## Required-source validation

For an existing directory root, workspace validation computes `missing_required_sources` in the required-source order owned by the source-tree contract.

A required source is missing when `workspace_root / filename` is not a file.

An optional source is never added to `missing_required_sources`.

## Reserved-path conflict construction

The current reserved-directory set is constructed from the source-tree constants as:

```text
LOWERCASE_WORKSPACE_DIRECTORIES
+ "proposals"
+ PROPOSAL_DIRECTORIES
+ ".relaylm"
+ ".relaylm/sources"
+ INTERNAL_DIRECTORIES
```

A reserved conflict is recorded when:

- a required or optional root source path exists but is not a file; or
- one of the reserved directory paths exists but is not a directory.

Conflict values are recorded as workspace-relative names/paths. Validation does not repair them.

## Source parsing during workspace validation

Validation inspects required and optional root source filenames in the exact concatenated source-tree order.

For each path that `is_file()` reports as a file, validation calls the direct source parser with the canonical filename-derived `source_kind` and `public=False`.

Missing optional sources are skipped without error.

A parsed source is considered malformed for workspace validation whenever its result's `is_valid` property is false.

## Validation reason accumulation

After source presence, reserved-conflict, and parse checks, current top-level validation builds `reason_ids` in this order:

```text
missing_required_source     if any required source is missing
reserved_path_conflict      if any reserved conflict exists
malformed_markdown          if any parsed source result is invalid
```

More than one reason may therefore appear in the result.

## Validation status precedence

The single top-level `status` is selected with exact current precedence:

```text
missing required source
  -> missing_required_source
else reserved conflict
  -> reserved_path_conflict
else malformed parsed source
  -> malformed_markdown
else
  -> valid
```

`is_valid` is true if and only if the selected status is `valid`.

Reason accumulation and status precedence are different: lower-precedence reasons may remain present even when a higher-precedence status wins.

## Runtime workspace validation result shape

The exact current `CharacterWorkspaceValidationResult` fields are:

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

The runtime result defaults `content_free` to false unless it is constructed for a public call.

## Public workspace validation projection

`CharacterWorkspaceValidationResult.to_public_dict()` emits exactly:

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

with:

```text
schema_version = "relaylm.character_workspace.v0"
content_free = true
```

`source_results` is the ordered tuple of each source result's public projection.

The public result exposes the count of reserved conflicts, not their path values.

## Character workspace layout result

`character_workspace_layout()` returns a `CharacterWorkspaceLayout` populated from the current source-tree constants.

Its exact fields are:

```text
required_source_filenames
optional_source_filenames
expected_directories
proposal_directories
internal_directories
```

The source-tree contract owns the exact path vocabulary in those fields. This parser/validation contract owns only the fact that the layout result projects those source-tree constants.

## Read-only manifest behavior

`build_character_workspace_manifest(root, public=False)` is a read-only summary helper, not the deterministic compiler.

Current behavior is:

1. convert `root` to `Path`;
2. use the root basename as `character_id` only if it matches the character-ID contract, otherwise use `None`;
3. call workspace validation with that derived character ID and `public=False`;
4. if the root exists and is a directory, enumerate `rglob("*")` up to the manifest-entry boundary;
5. classify each enumerated relative path through the source-tree classifier;
6. count results by classifier `domain` and path-kind value;
7. sort each count mapping by key before storing it;
8. preserve the validation status, validity, source results, and reason IDs, adding `manifest_entry_limit_reached` if enumeration exceeded the configured limit.

The manifest does not write `.relaylm/build/character_manifest.json`.

## Runtime manifest shape

The exact current `CharacterWorkspaceManifest` fields are:

```text
status
is_valid
character_id
source_results
domain_counts
path_kind_counts
reason_ids
```

`domain_counts` and `path_kind_counts` are sorted tuples of `(key, count)` pairs.

## Public manifest projection

`CharacterWorkspaceManifest.to_public_dict()` emits exactly:

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

with `content_free = true` and each source result converted through its public projection.

The manifest projection contains counts and bounded source diagnostics rather than raw Markdown bodies or arbitrary enumerated workspace paths.

## Parser/validation non-authority

These APIs must not be interpreted as authority to:

- create missing workspace files or directories;
- restore a default character;
- approve a character source;
- write compiler build artifacts;
- select active character, relationship, scene, affect, memory, or context;
- apply proposal or inbox material;
- mutate runtime state;
- publish raw source bodies through public diagnostics.

The stable separation remains:

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

This current contract is implemented by:

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

- Source files are read as UTF-8 and bounded by the exact current byte limit.
- Direct parse failures are bounded and expose fixed error IDs rather than raw exceptions.
- Structural Markdown parsing recognizes only the current heading, terminal-anchor, and metadata forms.
- Metadata inside active triple-backtick or triple-tilde fences is ignored.
- Parser content hashes are deterministic SHA-256 strings over the exact current text/block inputs.
- Workspace validation is read-only.
- Invalid supplied character IDs fail before workspace-root inspection.
- Missing required sources, reserved conflicts, and malformed source results preserve exact status precedence and reason accumulation.
- Public block/source/validation/manifest projections are content-free by default and do not expose raw Markdown bodies.
- The manifest is a read-only summary, not the CW-A2 compiler or an activation artifact.
- Manifest enumeration truncation adds a reason but does not independently rewrite validation status.
- Parsing and validation never grant downstream semantic or runtime authority.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- source-tree path-kind values beyond consuming the source-tree contract;
- semantic validity of SOUL/STYLE/EMOTION/SCENE/RELATIONSHIP/MEMORY/BOUNDARY/LORE content;
- compiler artifact schemas or deterministic build serialization;
- compiler dry-run/write gates;
- creation/import commit behavior;
- SLP maintenance candidate behavior;
- runtime activation or context selection;
- source retirement, retirement-manifest entries, or router migration.

## Related architecture and contracts

- [Character Workspace Source Tree Contract](source-tree.md)
- [Character Workspace Source Compiler](../../architecture/character-workspace/source-compiler.md)
- [Character Workspace System](../../architecture/character-workspace/system.md)
- [CW-A1 transitional implementation handoff](../../architecture/cw_a1_file_first_source_tree_parser_contracts.md)
