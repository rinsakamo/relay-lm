---
relaylm_doc_type: contract
relaylm_authority: character_workspace_creation_staging_template_validation_and_commit_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace creation candidate or commit result changes
  - explicit approval or target-conflict behavior changes
  - bundled template registry or local template validation changes
  - external import gains a durable commit path
  - creation CLI or loopback management write boundary changes
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - source-tree, parser/validation, or compiler internals owned by adjacent contracts
  - active-character selection or runtime conversation semantics
  - RelaySLP maintenance apply, RelayMEM lifecycle, RelayREL, RelaySCN, RelayEMO, or RelayCTX behavior
  - source retirement or documentation migration disposition
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - source-tree.md
  - parser-and-validation.md
  - compiled-projections.md
  - ../../architecture/character-workspace/creation-and-import.md
  - ../../architecture/character-workspace/system.md
  - ../../architecture/character-workspace/showcase-starter-product-knowledge.md
relaylm_verified_by:
  - ../../../scripts/relaylm_cw_a5_character_creation_templates_smoke.py
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace creation and template maintainers
  - SOUL Lab and CLI integration maintainers
  - source compiler, import, migration, privacy, and security reviewers
relaylm_authority_level: exact_contract
---
# Character Workspace Creation and Commit Contract

## Authority summary

This contract owns the exact current Character Workspace creation candidate, bundled-template staging, local template validation, explicit new-workspace commit boundary, and their content-free public projections.

It consumes the separately owned source-tree, parser/validation, and compiled-projection contracts.

The current durable creation path is:

```text
bundled template or advanced source sections
  -> stage complete candidate in temporary storage
  -> validate workspace
  -> compile dry-run preview
  -> explicit approval
  -> stage source tree under characters-root temporary directory
  -> revalidate staged tree
  -> compile and write derived .relaylm/build/** inside staging
  -> os.replace staging workspace into the final target
  -> committed workspace remains inactive
```

The normal creation flow checks that the final target does not exist before staging. This is the current `Path.exists()` gate, not a general filesystem compare-and-swap or replacement protocol.

Local external folder/ZIP import is currently **validation-only**. No current external-import API extracts or commits a third-party pack into `characters/<character>/`.

## Current schema identifiers

The exact current public schema identifiers are:

```text
TEMPLATE_REGISTRY_SCHEMA_VERSION = relaylm.character_templates.registry.v0
TEMPLATE_VALIDATION_SCHEMA_VERSION = relaylm.character_template.validation.v0
CHARACTER_CREATION_SCHEMA_VERSION = relaylm.character_creation.result.v0
```

The no-character startup projection uses:

```text
relaylm.character_creation.no_character_startup.v0
```

## Character identifier contract

A commit-eligible candidate character ID must match:

```regex
^[A-Za-z0-9_-]{1,128}$
```

The current Quick/Advanced staging helper `safe_character_slug(name)` performs:

1. `strip()` and lowercase the supplied name;
2. replace every run outside `[a-z0-9_-]` with `-`;
3. collapse repeated hyphens to one;
4. strip leading/trailing hyphen and underscore;
5. if empty, use `character-` plus the first 12 SHA-256 hex characters of the original UTF-8 name;
6. truncate to 80 characters.

The staging helper's result is therefore within the 128-character commit regex limit.

A slug is a workspace identifier, not active-character state, persona authority, or a RelayMEM identifier.

## Quick Create choices

The exact current accepted tone values are:

```text
friendly
polite
calm
energetic
cool
playful
slightly sharp
```

The exact current accepted intended-use values are:

```text
casual chat
AI companion
livestream / VTuber chat
roleplay
learning support
creative brainstorming
```

The current normalizer strips surrounding whitespace. Unknown tone falls back to `friendly`; unknown intended use falls back to `casual chat`.

These choices affect bundled source staging only.

## Current bundled template registry

The current local-only template IDs are:

```text
friendly-companion
vtuber-stream-partner
creator-mascot
fantasy-roleplay-character
calm-assistant-character
blank-character
showcase-friendly-companion
showcase-vtuber-stream-partner
showcase-creator-mascot
showcase-fantasy-roleplay-character
developer-design-partner
```

The first six are starter records, the next four are showcase records, and `developer-design-partner` is an advanced record with `primary_default = false`.

Registry membership does not imply that a workspace exists or is active.

## Template record shape

`CharacterTemplateRecord` carries exactly:

```text
template_id
title
shelf
summary
intended_uses
tone_options
official
showcase
primary_default
advanced
relaylm_onboarding_memory
```

Its public projection adds:

```text
content_only_source_pack = true
runtime_authority = false
```

`get_character_template(template_id)` returns the matching record or raises `ValueError("template_not_found")`.

## Registry public projection

`list_character_templates()` emits:

```text
schema_version
content_free
remote_registry_supported
network_download_performed
templates
starter
showcase
advanced
safety
```

with:

```text
schema_version = relaylm.character_templates.registry.v0
content_free = true
remote_registry_supported = false
network_download_performed = false
```

Its current safety projection is:

```text
templates_are_active_characters = false
auto_create_default_character = false
auto_restore_sample_character = false
explicit_approval_required = true
imports_runtime_state = false
```

Registry access performs no network download.

## No-character startup projection

`validate_no_character_startup(characters_root)` is read-only.

If the root exists and is a directory, it scans direct children in name-sorted order. A child is considered only when `child.is_dir()` is true and `child.is_symlink()` is false. Each remaining child is validated with its child name as `character_id`.

The result contains:

```text
schema_version = relaylm.character_creation.no_character_startup.v0
valid_character_count
creation_flow_required
auto_created_default_character = false
auto_restored_sample_character = false
active_character_restored = false
content_free = true
source_content_included = false
```

`creation_flow_required` is exactly `not valid_character_ids`.

This helper does not create, restore, select, or activate a default character.

## Quick Create staging

`stage_quick_character(...)` accepts:

```text
template_id
name
tone = friendly
intended_use = casual chat
showcase_mode = starter
```

Current behavior is:

1. resolve the bundled template record;
2. normalize tone and intended use;
3. compute `use_as_starter = (showcase_mode == "starter")`;
4. build the bundled source mapping;
5. derive `character_id` with `safe_character_slug(name)`;
6. call the shared candidate-staging helper.

Candidate `mode` is `quick_create` for non-showcase records and `showcase_<showcase_mode>` for showcase records.

The core function itself accepts any string for `showcase_mode`. Current SOUL Lab and CLI surfaces restrict that input to `starter` or `as_is`.

## Showcase staging

For current showcase records, bundled staging may add:

```text
memory/people/demo_user.md
scenes/showcase.md
```

When `showcase_mode == "starter"`, `memory/people/demo_user.md` is removed. In `as_is` mode it remains marked as template-example material.

Staged example material is not live evidence or active memory merely because candidate validation succeeds.

## Advanced Create staging

`stage_advanced_character(name, source_sections=None)`:

1. uppercases supplied section keys;
2. starts from the current complete base workspace source mapping using `polite`, `creative brainstorming`, and `advanced custom character`;
3. considers only required and optional root source families for override;
4. replaces a root source only when the supplied value is non-empty after stripping;
5. writes a replacement as stripped text plus one newline;
6. stages through the same shared candidate path.

Its candidate has:

```text
template_id = null
mode = advanced_create
relaylm_onboarding_memory_included = false
```

Advanced Create is not permission to write arbitrary `.relaylm/**` state.

## Candidate completion

Before validation, `_complete_workspace_files` supplies these files when absent:

```text
relationships/_template.md
relationships/user.md
scenes/default.md
memory/core.md
```

It also supplies a current default source for every missing required uppercase source filename.

This completion is creation staging behavior; it is not a repair API for an existing committed workspace.

## Candidate staging is temporary

`_candidate_from_files` uses `tempfile.TemporaryDirectory(prefix="relaylm-cw-a5-")`.

Inside that temporary root it:

```text
writes the completed source mapping
  -> validate_character_workspace(..., public=False)
  -> compile_character_workspace(..., write=False)
  -> retain compiler public projection
```

The temporary directory is discarded when candidate construction ends.

Candidate preview therefore does not write to the user's characters root and does not write compiler build artifacts there.

## Candidate object

`CharacterWorkspaceCandidate` carries exactly:

```text
character_id
template_id
mode
source_files
source_directories
validation
compile_projection
relaylm_onboarding_memory_included
content_free
```

The runtime object carries content-bearing `source_files` for later commit. That mapping is not emitted by the public projection.

## Candidate public projection

`CharacterWorkspaceCandidate.to_public_dict()` emits:

```text
schema_version
status
is_valid
character_id
template_id
mode
required_source_presence
optional_source_presence
source_file_count
workspace_directories_present
relaylm_onboarding_memory_included
validation
compile_projection
content_free
source_content_included
active_character_set
requires_explicit_approval
```

with:

```text
schema_version = relaylm.character_creation.result.v0
status = staged if validation.is_valid else invalid
is_valid = bool(validation.is_valid)
content_free = true
source_content_included = false
active_character_set = false
requires_explicit_approval = true
```

## Candidate directory projection

`source_directories` is the sorted, de-duplicated union of the source-tree contract's current lowercase directories and the creation module's additional workspace-file directories:

```text
relationships
scenes
memory
memory/topics
proposals
```

This projection does not mean all directories contain active semantic content.

## Safe creation-source write

`_write_workspace_files` creates the candidate root and expected directory union, then writes every source as UTF-8 after `_assert_safe_workspace_relative_path` accepts the supplied relative path.

The current helper constructs `PurePosixPath(relative_path)` and rejects when:

- `pure.is_absolute()` is true;
- one of the components that remains in `pure.parts` is `""`, `"."`, or `".."`;
- the normalized POSIX string begins with `.relaylm/`;
- the suffix is not one of the current safe text suffixes.

The exact safe text suffix set is:

```text
.md
.txt
.json
```

The current `ValueError` identifiers are:

```text
unsafe_workspace_relative_path
template_must_not_write_relaylm_internal_artifacts
workspace_source_must_be_text
```

`PurePosixPath` normalizes some redundant separators and `.` components before exposing `.parts`. This contract therefore does not claim that the helper preserves/rejects every raw spelling distinction before that normalization. It does preserve `..` components for the current traversal check.

Bundled/current candidate paths are generated by trusted local creation code and are still revalidated through the Character Workspace validator before publish.

## Bundled template manifest and preview files

Current bundled generation adds:

```text
manifest.json
preview/sample_prompt.txt
preview/sample_responses.md
```

The manifest uses:

```text
schema = relaylm.character_template.manifest.v0
content_only_source_pack = true
imports_runtime_state = false
```

plus the template ID, title, shelf, and onboarding-memory flag.

These are template/source-pack files, not active runtime state or imported `.relaylm/build/**` authority.

## Product-help onboarding source

Current bundled templates may opt into:

```text
memory/topics/relaylm.md
scenes/relaylm_onboarding.md
```

The onboarding memory contains current source markers including:

```text
status:: template_knowledge
source:: template:relaylm_onboarding
scope:: product_help
pin_state:: pinned
slp_update:: disabled
update_policy:: bundled_template_update_only
```

Third-party validation only observes whether the exact normalized path `memory/topics/relaylm.md` is present. It does not add that file to an external pack.

## Commit result object

`WorkspaceCommitResult` carries exactly:

```text
status
character_id
committed
active_character_set
reason_ids
written_build_artifacts
content_free
```

Its public projection emits:

```text
schema_version
status
character_id
committed
active_character_set
reason_ids
written_build_artifacts
content_free
source_content_included
absolute_paths_included
```

with:

```text
schema_version = relaylm.character_creation.result.v0
content_free = true
source_content_included = false
absolute_paths_included = false
```

## Explicit approval gate

`commit_character_workspace_candidate(..., approval=False)` returns before characters-root creation or target write:

```text
status = approval_required
committed = false
active_character_set = false
reason_ids = ("approval_required",)
```

Validation or preview success is not approval.

## Candidate-ID gate

After approval, the commit path rechecks the candidate ID against the exact character-ID regex.

Failure returns:

```text
status = invalid_character_id
committed = false
active_character_set = false
reason_ids = ("invalid_character_id",)
```

## Retained candidate-validation gate

If `candidate.validation.is_valid` is false, commit returns:

```text
status = invalid_candidate
committed = false
active_character_set = false
```

with the retained validation reason IDs, falling back to `invalid_candidate`.

The retained-result gate is followed by fresh materialized-tree revalidation before publish.

## Existing-target gate

The final target is:

```text
<characters_root>/<candidate.character_id>
```

Current code tests:

```text
target.exists()
```

If true, commit returns:

```text
status = target_exists
committed = false
active_character_set = false
reason_ids = ("target_character_exists",)
```

The current gate is exactly `Path.exists()`: it is not documented here as `lexists()`, an inode reservation, a lock, or a race-free compare-and-swap.

Creation does not intentionally merge with or overwrite a target that passes this existing-target check.

## Commit staging directory

After the non-write gates pass, the characters root is created with `parents=True, exist_ok=True` if necessary.

Current temporary paths are:

```text
<characters_root>/_relaylm_create_<character_id>_tmp/
<characters_root>/_relaylm_create_<character_id>_tmp/<character_id>/
```

If the temporary parent already exists, current code removes that temporary parent recursively before creating the new staging tree.

This reserved temporary directory is implementation staging, not durable character identity.

## Fresh revalidation before publish

The candidate's current `source_files` mapping is materialized into the staging workspace through the creation source-write helper.

The materialized tree is then validated with:

```text
validate_character_workspace(
    staging_root,
    character_id=candidate.character_id,
    public=False,
)
```

Failure returns:

```text
status = validation_failed
committed = false
active_character_set = false
```

with validation reason IDs, falling back to `validation_failed`.

No final target is published on this result.

## Compiler/build gate before publish

After successful revalidation, current commit code calls:

```text
compile_character_workspace(staging_root, write=True)
```

The exact current order is therefore:

```text
materialize source in staging
  -> fresh validate staging
  -> compile staging
  -> write derived .relaylm/build/** inside staging
  -> publish staging workspace
```

Build artifacts are generated before final directory publish, but only inside the not-yet-published staging workspace.

If compiler validation fails, commit returns:

```text
status = compile_failed
committed = false
active_character_set = false
```

with compiler blocking reasons, falling back to `compile_failed`.

This exact order supersedes any loose transitional prose that describes build generation as occurring after the final directory move.

## Final publish

After successful revalidation and compiler write, current code calls:

```text
os.replace(staging_root, target)
```

On normal success:

```text
status = committed
committed = true
active_character_set = false
reason_ids = ()
written_build_artifacts = tuple(.relaylm/build/<EXPECTED_ARTIFACT>)
```

Artifact order is the current `EXPECTED_ARTIFACTS` order owned by `compiled-projections.md`.

`os.replace` is the exact current publish operation. This contract does not inflate it into a stronger cross-platform transaction/locking guarantee than the implementation provides.

## Temporary cleanup

The staging body is covered by a `finally` cleanup. If the temporary parent still exists, current code removes it recursively.

On normal successful publish, the staging workspace has moved into the target and the remaining temporary parent is removed.

On a pre-publish failure reached inside the staging body, the temporary staging parent is removed. The characters root itself may remain after it was created; the guarantee is no successful final workspace publication, not literal zero filesystem metadata change after every late failure.

## Convenience bundled-template commit

`commit_character_from_template(...)` performs:

```text
stage_quick_character(...)
  -> commit_character_workspace_candidate(...)
```

It is not a second write implementation and uses the same explicit approval gate.

## CLI persistence gate

The current creation CLI requires exactly one of:

```text
--dry-run
--write
```

Both or neither is an argument error.

`--dry-run` returns the candidate public projection. `--write` calls the bundled-template commit path with `approval=True`.

The CLI does not auto-activate the committed character.

The separate template-validation CLI validates a local folder/ZIP and prints the template validation public projection only.

## SOUL Lab management boundary

Current Character Creation HTTP routes are under the loopback-only SOUL Lab management surface and call the owning loopback management guard:

```text
GET  /lab/api/character-templates
POST /lab/api/character-templates/validate
POST /lab/api/characters/create-from-template
POST /lab/api/characters/import-template
```

The create-from-template route calls the same bundled-template commit core. A missing template is projected as `template_not_found` with HTTP 404.

The import-template route does not call a commit function.

## Local import root gate

SOUL Lab local import validation first rejects an absolute request `import_path` with:

```text
absolute_import_path_rejected
```

Local import validation is disabled unless:

```text
RELAYLM_CHARACTER_TEMPLATE_IMPORT_ROOT
```

is configured. Absence returns `local_import_disabled`.

When configured, the import root and requested candidate are resolved. A resolved candidate that is not relative to the resolved import root is rejected with:

```text
path_traversal_rejected
```

Only then is the local candidate passed to `validate_template_path`.

This environment setting grants a local validation root, not external-template commit authority.

## External import is validation-only

The current SOUL Lab import endpoint returns the local template validation public projection, then adds:

```text
workspace_commit_supported = false
```

and appends:

```text
external_import_commit_pending
```

to the returned `reason_ids`.

The endpoint does not change the underlying `status` or `is_valid` returned by template validation. A structurally valid pack can therefore remain `status=valid` / `is_valid=true` while also reporting that external workspace commit is pending/unsupported.

The lifecycle is exactly:

```text
local folder/ZIP reference
  -> bounded validation
  -> content-free result
  -> no extraction
  -> no external-file candidate construction
  -> no workspace commit
  -> no activation
```

Any future external-import commit requires a separate implementation and contract update.

## Template path dispatch

`validate_template_path(path)` currently dispatches:

```text
path.is_dir() == true
  -> validate_template_directory

else path.is_file() == true and suffix.lower() == ".zip"
  -> validate_template_zip

else
  -> invalid / template_path_not_supported
```

This API does not commit the validated path.

## Template validation result

`TemplateValidationResult` carries exactly:

```text
status
is_valid
reason_ids
checked_entry_count
rejected_entry_count
relaylm_onboarding_memory_included
content_free
```

Its public projection emits:

```text
schema_version
status
is_valid
reason_ids
checked_entry_count
rejected_entry_count
relaylm_onboarding_memory_included
content_free
source_content_included
raw_paths_included
```

with:

```text
schema_version = relaylm.character_template.validation.v0
content_free = true
source_content_included = false
raw_paths_included = false
```

## Template-directory validation

`validate_template_directory(root)` returns `template_root_missing_or_not_directory` when the path does not exist or is not a directory.

For an accepted directory path, current code recursively enumerates `root_path.rglob("*")`, increments a checked count, derives each entry relative to the root, and records:

```text
relative path
lstat().st_mode
path.is_dir()
path.is_symlink()
```

An unexpected `relative_to` failure returns `path_escape_rejected` with the current checked count and one rejected entry.

Directory validation does not copy the directory into `characters/**`.

## Template-ZIP validation

`validate_template_zip(path)` returns:

```text
template_zip_missing
```

when the path does not exist or is not a file, and:

```text
template_zip_invalid
```

for `zipfile.BadZipFile`.

For a readable ZIP, current code records each `ZipInfo` filename, Unix external mode, `is_dir()` result, and symlink bit derived from the mode.

It does not extract the archive.

## Shared template entry normalization

Before common safety checks, each raw entry name is normalized by:

```text
raw_path.replace("\\", "/").strip("/")
```

Empty normalized strings are skipped.

The normalized string is then parsed as `PurePosixPath`.

Because outer slashes are stripped before the shared helper and `PurePosixPath` normalizes some path spellings, this contract does **not** claim that every raw archive absolute-path spelling is independently preserved and rejected by the inner helper. The current external archive path is validation-only and performs no extraction/commit.

The source-writing commit path does not consume these external archive entries at all.

## Current safe template suffixes

Safe inert asset suffixes are:

```text
.png
.jpg
.jpeg
.webp
.gif
.svg
```

Safe text suffixes are:

```text
.md
.txt
.json
```

A non-directory entry with a non-empty suffix outside both sets receives:

```text
non_content_file_rejected
```

This allowlist is validation metadata, not execution permission.

## Script/executable rejection

The exact current script suffixes are:

```text
.bat
.cmd
.com
.exe
.js
.mjs
.ps1
.py
.rb
.sh
.ts
```

A non-directory entry using one receives `script_or_executable_rejected`. A non-directory entry whose inspected mode contains an executable bit receives the same reason.

Reason IDs are de-duplicated preserving first occurrence.

## Reserved runtime/config rejection

Current reserved template prefixes are:

```text
.relaylm/build/
.relaylm/state/
.relaylm/sources/
.relaylm/audit/
.relaylm/queue/
.relaylm/indexes/
.relaylm/projections/
```

An entry equal to a prefix root or beginning with one receives:

```text
relaylm_runtime_artifact_rejected
```

Current reserved basenames are:

```text
.env
config.yaml
config.yml
relaylm.yaml
relaylm.yml
runtime.yaml
runtime.yml
secrets.json
```

A current basename match receives:

```text
runtime_config_or_env_rejected
```

The helper includes a lowercase basename comparison against this lowercase set.

## Traversal and symlink checks

The common helper checks the `PurePosixPath.parts` it receives for `""`, `"."`, and `".."`; a surviving matching part produces:

```text
path_traversal_rejected
```

In current `PurePosixPath` behavior, redundant separators and `.` segments may already have normalized away before `.parts` is inspected, while `..` is preserved. The contract therefore states the implementation check rather than a stronger raw-spelling guarantee.

An entry identified as a symlink receives:

```text
symlink_rejected
```

Folder validation gets this state from the filesystem path; ZIP validation derives it from the archive mode.

## Template required entries

After entry-level checks, the shared validator requires exact normalized presence of:

```text
manifest.json
```

and every required uppercase source filename owned by `source-tree.md`.

Missing manifest adds `missing_manifest`. Missing one or more required uppercase sources adds `missing_required_template_source`.

The final reason tuple is de-duplicated preserving first occurrence. Template validation is `valid` exactly when that tuple is empty.

## Onboarding-memory presence

Template validation reports `relaylm_onboarding_memory_included = true` exactly when the normalized entry set contains:

```text
memory/topics/relaylm.md
```

This is presence only. It does not grant official/bundled provenance and does not commit the file.

## Current external trust boundary

Current external template validation does not:

- extract ZIP content;
- copy a validated folder into `characters/**`;
- construct a commit candidate from external file bodies;
- write `.relaylm/build/**` from the external pack;
- import `.relaylm/state/**`, queue, audit, indexes, projections, or source-evidence records;
- execute scripts/assets;
- contact a remote registry;
- download template content;
- set active character;
- apply memory, relationship, scene, emotion, or context state.

A successful validation is therefore a safety/structure observation, not durable import.

## New-workspace creation only

`commit_character_workspace_candidate` is not a generic import, merge, update, rename, replace, restore, or migration API.

It attempts to publish one staged candidate at a target that passed the current `target.exists()` precheck.

A future replacement or external-import commit path needs separately governed conflict, provenance, staging-revision, rollback, and activation semantics.

## Active-character separation

Current candidate and commit projections keep:

```text
active_character_set = false
```

The current creation core does not persist active-character selection as part of commit.

The lifecycle remains:

```text
candidate staged
  != candidate valid
  != compiled preview valid
  != approval granted
  != workspace committed
  != derived build present
  != active character selected
```

## Runtime semantic non-authority

Creation and template validation do not directly mutate:

- RelaySOUL runtime selection;
- RelayREL current target/state;
- RelaySCN current scene state;
- RelayEMO current affect state;
- RelayMEM stores or retrieval results;
- RelayCTX current request state;
- RelaySLP maintenance queues/apply decisions;
- current conversation output.

A committed source tree becomes available for later explicit selection. Creation commit does not execute the workspace's semantic content immediately.

## Content-free public boundary

Current public projections may expose bounded template product metadata, validation status/reasons/counts, character IDs, source-family presence, directory names, compiler public summaries, commit status, and relative generated artifact names.

They do not expose:

- candidate raw source bodies;
- rejected template file bodies;
- arbitrary raw template path inventories;
- absolute characters-root paths;
- credentials or runtime configuration content;
- `.relaylm/state/**`, queue, audit, or source-evidence payloads.

## Failure behavior

Current behavior closes toward no successful final workspace publication and no activation:

```text
approval absent
  -> approval_required

candidate ID invalid
  -> invalid_character_id

retained candidate invalid
  -> invalid_candidate

current target.exists() true
  -> target_exists

fresh staging validation fails
  -> validation_failed

staging compiler fails
  -> compile_failed

external template validates
  -> validation result only
  -> workspace_commit_supported = false
  -> external_import_commit_pending

creation publish succeeds
  -> committed = true
  -> active_character_set = false
```

Late failures after characters-root creation may leave the characters root itself present, while the staging `finally` removes the reserved temporary parent. This contract does not overstate failure as literal zero filesystem metadata change.

## Current implementation anchors

This contract is implemented by:

```text
relaylm/character_creation.py
relaylm/soul_lab_character_creation.py
relaylm/cli/character_creation.py
```

and consumes `relaylm/character_workspace/**` under the adjacent exact contracts.

The focused current smoke is:

```text
scripts/relaylm_cw_a5_character_creation_templates_smoke.py
```

The smoke verifies current registry/no-default behavior, Quick/Advanced staging, showcase starter/as-is distinction, approval gate, successful build-containing commit with no activation, duplicate-target rejection, safe third-party validation, unsafe runtime/script/config/symlink/traversal rejection, and content-free public validation output.

The transitional CW-A5 implementation handoff was retired in D6-R35-K after this contract, the Character Workspace creation/import architecture, and the showcase/starter/product-knowledge policy already owned its current semantics. Its exact text remains Git-recoverable through the central retirement manifest.

## Stable invariants

- No-character startup does not auto-create, restore, or activate a default/sample character.
- Bundled template registry access is local and performs no network download.
- Quick/Advanced/Showcase staging produces a full candidate and reuses current validation/compiler boundaries.
- Candidate preview uses compiler dry-run and is not durable commit.
- Candidate public projection omits raw source bodies.
- Durable current bundled/new-workspace creation requires explicit approval.
- Commit rechecks candidate ID and retained validation, applies the current target-exists precheck, then freshly revalidates the materialized staging tree.
- Current commit writes derived build artifacts inside staging before final publish.
- Current publish operation is `os.replace(staging_root, target)`; no stronger locking/transaction guarantee is implied.
- Staging cleanup removes the reserved temporary parent on normal success and handled pre-publish returns.
- Successful creation still reports `active_character_set = false`.
- Current external folder/ZIP import is validation-only.
- SOUL Lab external import explicitly reports `workspace_commit_supported = false` and `external_import_commit_pending`.
- SOUL Lab external path validation is confined to the configured resolved local import root.
- External validation does not extract archives, import runtime state, or trust foreign `.relaylm/**` as source authority.
- Creation-source staging rejects the current `.relaylm/` prefix and non-text source suffixes after its current `PurePosixPath` normalization.
- Public validation/creation diagnostics remain content-free.
- Creation/import does not mutate current REL/SCN/EMO/MEM/CTX/SLP runtime state.
- Validation, preview compilation, approval, commit, derived build presence, and activation remain separate lifecycle states.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- source-tree classification owned by `source-tree.md`;
- Markdown/workspace validation internals owned by `parser-and-validation.md`;
- compiler artifact schemas/write mechanics owned by `compiled-projections.md`;
- external template extraction or commit, which is not currently implemented;
- remote registry, marketplace, download, signature, or update-channel behavior;
- existing-workspace merge/replacement/migration;
- active-character selection or persistence;
- semantic source schemas;
- RelaySLP maintenance apply;
- runtime conversation/request-context behavior;
- UI component layout;
- source retirement or router migration;
- repository-level project sequencing.

## Related architecture and contracts

- [Character Workspace Source Tree Contract](source-tree.md)
- [Character Workspace Parser and Validation Contract](parser-and-validation.md)
- [Character Workspace Compiled Projections Contract](compiled-projections.md)
- [Character Workspace Creation and Import](../../architecture/character-workspace/creation-and-import.md)
- [Character Workspace System](../../architecture/character-workspace/system.md)
- [Showcase, Public Starter, and Product Knowledge Ownership](../../architecture/character-workspace/showcase-starter-product-knowledge.md)
