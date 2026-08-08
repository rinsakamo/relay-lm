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
  - ../../architecture/cw_a5_character_creation_templates_showcase_import.md
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
  -> os.replace staging workspace into a previously absent target
  -> committed workspace remains inactive
```

Local external folder/zip import is currently **validation-only**. No current external-import API extracts or commits a third-party pack into `characters/<character>/`.

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

The current helper used by Quick/Advanced staging is:

```text
safe_character_slug(name)
```

Its exact transformation is:

1. `strip()` and lowercase the supplied name;
2. replace every run of characters outside `[a-z0-9_-]` with `-`;
3. collapse repeated hyphens to one hyphen;
4. strip leading/trailing hyphen and underscore;
5. if the result is empty, use `character-` plus the first 12 hex characters of SHA-256 over the original UTF-8 name;
6. truncate the result to 80 characters.

The staging helper's 80-character output is therefore within the 128-character commit regex limit.

A generated slug is a local workspace identifier. It is not active-character state, persona identity authority, or a RelayMEM identifier.

## Allowed Quick Create choice values

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

The current normalizer strips surrounding whitespace and preserves a value only when it is exactly in the owning set.

Unknown tone falls back to:

```text
friendly
```

Unknown intended use falls back to:

```text
casual chat
```

These values affect bundled source staging only. They do not bypass source validation or activate runtime state.

## Current bundled template registry

The current local-only registry contains these template IDs:

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

The first six are current starter records, the next four are showcase records, and `developer-design-partner` is an advanced record with `primary_default = false`.

Registry membership is product/template metadata. It does not mean a workspace exists or is active.

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

`get_character_template(template_id)` returns the matching current record or raises:

```text
template_not_found
```

## Template registry public projection

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

The exact current `safety` values are:

```text
templates_are_active_characters = false
auto_create_default_character = false
auto_restore_sample_character = false
explicit_approval_required = true
imports_runtime_state = false
```

The registry performs no network access.

## No-character startup projection

`validate_no_character_startup(characters_root)` is read-only.

When the root exists and is a directory, it examines direct children in filename-sorted order. It skips a child unless that child is a directory and not a symlink. Remaining children are validated as Character Workspaces using the child name as `character_id`.

Its public result contains:

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

`creation_flow_required` is true exactly when no valid child workspace was found.

This helper never creates, restores, chooses, or activates a default character.

## Quick Create staging

`stage_quick_character(...)` takes:

```text
template_id
name
tone = friendly
intended_use = casual chat
showcase_mode = starter
```

Current behavior is:

1. resolve the bundled template record;
2. normalize tone and intended use through the current choice sets;
3. set `use_as_starter = (showcase_mode == "starter")`;
4. deterministically build the bundled source-file mapping;
5. derive `character_id` through `safe_character_slug(name)`;
6. stage and validate the complete candidate through `_candidate_from_files`.

Candidate mode is:

```text
quick_create
```

for a non-showcase record, and:

```text
showcase_<showcase_mode>
```

for a showcase record.

The core staging function does not itself restrict `showcase_mode` to a fixed enum. The SOUL Lab and CLI surfaces currently restrict it to `starter` or `as_is`.

## Showcase staging distinction

For a showcase record, current bundled generation may include:

```text
memory/people/demo_user.md
scenes/showcase.md
```

When `showcase_mode == "starter"`, the demo-user memory is removed from the staged file set.

For current `as_is` staging, that demo-user example remains and is marked as template example content by the bundled source text.

This example content is still staged source material and does not become live evidence or active runtime memory merely because the candidate validates.

## Advanced Create staging

`stage_advanced_character(name, source_sections=None)`:

1. uppercases supplied section-map keys;
2. begins from the current complete base workspace template using `polite`, `creative brainstorming`, and the `advanced custom character` archetype;
3. considers only required plus optional root source filenames for direct section override;
4. replaces a root source only when the corresponding supplied section is non-empty after stripping;
5. stores an override as stripped text plus one newline;
6. stages through the same `_candidate_from_files` validation/preview path.

Its candidate has:

```text
template_id = null
mode = advanced_create
relaylm_onboarding_memory_included = false
```

Advanced staging is not permission to write arbitrary `.relaylm/**` content.

## Candidate completion

Before candidate validation, `_complete_workspace_files` ensures the following files exist in the in-memory source mapping if they were absent:

```text
relationships/_template.md
relationships/user.md
scenes/default.md
memory/core.md
```

It also ensures every required uppercase source filename owned by the source-tree contract exists by supplying the current default source text where necessary.

This completion step applies to creation staging. It does not repair arbitrary already-committed workspaces.

## Candidate staging is temporary

`_candidate_from_files` uses a temporary directory whose current prefix is:

```text
relaylm-cw-a5-
```

Inside it, the candidate is written under the derived character ID, validated with `public=False`, and compiled with:

```text
write = false
```

The compiler result is converted to its content-free public projection and retained as the candidate preview.

The temporary staging directory is discarded after candidate construction.

Candidate preview therefore performs no durable Character Workspace commit and no build-file write to the user's characters root.

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

The runtime object intentionally carries content-bearing `source_files` because the commit boundary needs the staged source material.

That runtime-private content is not emitted in the public candidate projection.

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

No raw source body is included in this public projection.

## Candidate directory projection

The candidate's `source_directories` is the sorted de-duplicated union of:

- the current Character Workspace lowercase directory vocabulary; and
- the creation module's additional workspace file directories:

```text
relationships
scenes
memory
memory/topics
proposals
```

Directory projection does not mean all directories contain active semantic content.

## Safe creation-source write

`_write_workspace_files` creates the candidate root, creates the expected directory union, and writes each candidate source as UTF-8 only after `_assert_safe_workspace_relative_path` accepts the path.

The current path assertion rejects:

- an absolute path;
- a path with an empty, `.` or `..` component;
- a path whose POSIX string starts with `.relaylm/`;
- a path whose suffix is not one of the current safe text suffixes.

The exact current safe text suffix set is:

```text
.md
.txt
.json
```

Rejected creation-source paths raise one of the current `ValueError` identifiers:

```text
unsafe_workspace_relative_path
template_must_not_write_relaylm_internal_artifacts
workspace_source_must_be_text
```

This check prevents template-generated source staging from directly supplying `.relaylm/**` runtime/build material.

## Bundled template manifest and preview files

Current bundled template generation adds:

```text
manifest.json
preview/sample_prompt.txt
preview/sample_responses.md
```

The generated manifest uses:

```text
schema = relaylm.character_template.manifest.v0
content_only_source_pack = true
imports_runtime_state = false
```

plus the template's current ID/title/shelf and onboarding-memory flag.

These files are creation/template source-pack material. They are not active-character state and are not foreign `.relaylm/build/**` artifacts.

## Product-help onboarding source

Current bundled records may opt into generated:

```text
memory/topics/relaylm.md
scenes/relaylm_onboarding.md
```

The onboarding memory is template/product-help source with current markers including:

```text
status:: template_knowledge
source:: template:relaylm_onboarding
scope:: product_help
pin_state:: pinned
slp_update:: disabled
update_policy:: bundled_template_update_only
```

Its presence is reported through the candidate/template projections.

Third-party template validation only reports whether the exact path `memory/topics/relaylm.md` is present. Validation does not add this file to an external pack.

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

`commit_character_workspace_candidate(..., approval=False)` fails before any characters-root creation or target write.

The exact current result is:

```text
status = approval_required
committed = false
active_character_set = false
reason_ids = ("approval_required",)
```

Candidate validation or preview success is not implicit approval.

## Candidate ID gate

After approval, the commit path rechecks `candidate.character_id` against the exact character-ID regex.

Failure returns:

```text
status = invalid_character_id
committed = false
active_character_set = false
reason_ids = ("invalid_character_id",)
```

No target workspace is written.

## Candidate validation gate

If the staged candidate's retained validation result is not valid, commit returns:

```text
status = invalid_candidate
committed = false
active_character_set = false
```

and uses the candidate validation reason IDs, falling back to:

```text
invalid_candidate
```

when none are available.

This gate does not replace the later revalidation of the materialized staging tree.

## Existing-target gate

The exact commit target is:

```text
<characters_root>/<candidate.character_id>
```

If that target already exists in any form, creation returns:

```text
status = target_exists
committed = false
active_character_set = false
reason_ids = ("target_character_exists",)
```

Creation does not merge with, delete, rename, or overwrite an existing target.

## Commit staging directory

After the non-write gates pass, the characters root is created with `parents=True, exist_ok=True` if needed.

Current temporary commit paths are:

```text
<characters_root>/_relaylm_create_<character_id>_tmp/
<characters_root>/_relaylm_create_<character_id>_tmp/<character_id>/
```

If the temporary parent already exists, current code removes it recursively before writing the new staged candidate.

The temporary path is implementation-local staging, not a durable character identity.

## Revalidation before publish

The candidate's source mapping is materialized into the staging workspace through the safe source-write helper.

The materialized staging workspace is then validated again using:

```text
validate_character_workspace(
    staging_root,
    character_id=candidate.character_id,
    public=False,
)
```

If revalidation fails, commit returns:

```text
status = validation_failed
committed = false
active_character_set = false
```

with validation reason IDs, falling back to `validation_failed`.

The staging directory is cleaned by the surrounding `finally` block.

## Compiler/build gate before publish

After successful revalidation, current commit code calls:

```text
compile_character_workspace(staging_root, write=True)
```

Thus the exact current order is:

```text
materialize source in staging
  -> revalidate staging
  -> compile staging
  -> write derived .relaylm/build/** inside staging
  -> publish whole staging workspace to final target
```

Build artifacts are generated **before** the final directory publish, but only inside the not-yet-published staging workspace.

This exact current order differs from a loose prose description that says build generation occurs after final commit. The durable result is still one newly published workspace containing both accepted source and locally generated derived build artifacts.

If the compiler result is invalid, commit returns:

```text
status = compile_failed
committed = false
active_character_set = false
```

with compiler blocking reason IDs, falling back to `compile_failed`.

No final target is published.

## Final publish operation

After successful revalidation and compiler write, current code publishes with:

```text
os.replace(staging_root, target)
```

The target was already required not to exist before staging began.

On success, the result is:

```text
status = committed
committed = true
active_character_set = false
reason_ids = ()
written_build_artifacts = tuple(.relaylm/build/<EXPECTED_ARTIFACT>)
```

Artifact names and order come from the compiled-projections contract's current `EXPECTED_ARTIFACTS` sequence.

The creation commit result does not claim that the active character changed.

## Temporary cleanup

The commit body is enclosed by a `finally` cleanup.

If the temporary parent still exists after success or failure, current code removes it recursively.

On a normal successful `os.replace`, the staging workspace has moved to the final target, leaving only the temporary parent for cleanup.

This cleanup does not delete an existing final target because existing targets are rejected before staging.

## Convenience bundled-template commit

`commit_character_from_template(...)` performs exactly:

```text
stage_quick_character(...)
  -> commit_character_workspace_candidate(...)
```

It does not create an alternative write path.

The same explicit `approval` gate applies.

## CLI persistence gate

The current character-creation CLI requires exactly one of:

```text
--dry-run
--write
```

Selecting both or neither is an argument error.

`--dry-run` returns the staged candidate public projection and performs no user characters-root write.

`--write` calls bundled-template commit with:

```text
approval = true
```

The CLI does not auto-activate the committed character.

The separate template-validation CLI validates a local folder/zip and prints only the template validation public projection.

## SOUL Lab management boundary

Current Character Creation HTTP routes are installed under the loopback-only SOUL Lab management surface and call the owning loopback-management guard before processing.

Current routes are:

```text
GET  /lab/api/character-templates
POST /lab/api/character-templates/validate
POST /lab/api/characters/create-from-template
POST /lab/api/characters/import-template
```

The create-from-template route calls the same core bundled-template commit path. A missing template ID is projected as `template_not_found` with HTTP 404.

The import-template route does **not** call a commit function.

## Local import root gate

SOUL Lab local import validation first rejects an absolute request `import_path` with:

```text
absolute_import_path_rejected
```

Local import validation is disabled unless this environment variable is present:

```text
RELAYLM_CHARACTER_TEMPLATE_IMPORT_ROOT
```

When absent, the result is:

```text
local_import_disabled
```

When configured, the import root is resolved, the requested path is resolved underneath it, and a candidate that does not remain relative to the resolved import root is rejected with:

```text
path_traversal_rejected
```

Only then is the resulting local path passed to template folder/zip validation.

This environment setting grants a validation root, not external-template commit authority.

## External import is validation-only

The current SOUL Lab import route returns the local template validation public projection, then adds:

```text
workspace_commit_supported = false
```

and appends:

```text
external_import_commit_pending
```

to the returned `reason_ids`.

Therefore current external import lifecycle is:

```text
local folder/zip reference
  -> bounded validation
  -> content-free result
  -> no extraction
  -> no candidate construction from external files
  -> no workspace commit
  -> no activation
```

A valid external pack is not commit-eligible merely because validation succeeded.

Any future external-import commit path requires a separately reviewed implementation and contract update.

## Template path dispatch

`validate_template_path(path)` currently dispatches as follows:

```text
existing directory
  -> validate_template_directory

existing file with suffix .zip (case-insensitive)
  -> validate_template_zip

otherwise
  -> invalid / template_path_not_supported
```

This API is validation-only.

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

Validation does not include rejected file bodies or raw path inventories in its public result.

## Template-directory validation

`validate_template_directory(root)` rejects a missing/non-directory root with:

```text
template_root_missing_or_not_directory
```

For an existing directory, it recursively enumerates entries, counts every enumerated item, computes each path relative to the validation root, records `lstat().st_mode`, directory state, and symlink state, then passes the entry metadata to the shared safety validator.

If relative-path derivation unexpectedly fails, it returns:

```text
path_escape_rejected
```

with the current checked count and one rejected entry.

Directory validation reads entry metadata for trust checks; it does not import or execute file content.

## Template-zip validation

`validate_template_zip(path)` rejects a missing/non-file path with:

```text
template_zip_missing
```

A malformed ZIP container is rejected with:

```text
template_zip_invalid
```

For a readable archive, current validation inspects each `ZipInfo` filename, external mode, directory state, and Unix symlink bit and passes those metadata to the shared validator.

It does not extract the ZIP.

## Shared template entry normalization

For common template validation, each raw entry path is currently normalized by:

```text
raw_path.replace("\\", "/").strip("/")
```

Empty normalized entries are skipped.

The normalized value is then interpreted as `PurePosixPath` and checked for unsafe classes.

Because leading/trailing slashes are stripped before the shared unsafe-entry helper runs, callers must not infer a stronger raw-archive absolute-path guarantee than this exact current normalization provides. Current external archives remain validation-only and are never extracted/committed by this path.

## Current safe template suffixes

The current safe inert asset suffixes are:

```text
.png
.jpg
.jpeg
.webp
.gif
.svg
```

The current safe text suffixes are:

```text
.md
.txt
.json
```

A non-directory entry with another non-empty suffix is rejected with:

```text
non_content_file_rejected
```

The suffix allowlist is a validation rule, not authorization to execute or automatically publish assets.

## Rejected script/executable classes

The exact current script suffix set is:

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

A non-directory entry using one of those suffixes is rejected with:

```text
script_or_executable_rejected
```

A non-directory entry whose inspected mode has an executable bit also receives the same reason ID.

Reason IDs are de-duplicated preserving first occurrence.

## Reserved runtime/config classes

The current reserved template prefixes are:

```text
.relaylm/build/
.relaylm/state/
.relaylm/sources/
.relaylm/audit/
.relaylm/queue/
.relaylm/indexes/
.relaylm/projections/
```

A normalized entry equal to a prefix root or beginning with one of these prefixes is rejected with:

```text
relaylm_runtime_artifact_rejected
```

The current reserved filenames are:

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

A matching basename is rejected with:

```text
runtime_config_or_env_rejected
```

The current check is case-insensitive through the lowercase basename comparison where applicable.

## Traversal and symlink template checks

A normalized path whose parsed components include an empty component, `.`, or `..` receives:

```text
path_traversal_rejected
```

An entry identified as a symlink receives:

```text
symlink_rejected
```

Folder validation derives symlink state from the filesystem entry. ZIP validation derives it from the archive external mode.

Template validation does not follow a symlink as trusted source merely because its target is local.

## Template required entries

After entry-level checks, the shared validator requires exact path presence for:

```text
manifest.json
```

and every required uppercase source filename owned by the source-tree contract.

Missing manifest adds:

```text
missing_manifest
```

Missing one or more required source filenames adds:

```text
missing_required_template_source
```

Validation reason IDs are de-duplicated preserving first occurrence.

The template is valid only when the final reason tuple is empty.

## Onboarding-memory detection in imports

Template validation sets `relaylm_onboarding_memory_included = true` only when the exact normalized path:

```text
memory/topics/relaylm.md
```

is present.

This is a presence observation. It does not grant bundled/official status to a third-party file and does not commit it.

## Current validation-only trust boundary

The external validator intentionally checks pack structure and unsafe metadata classes without creating a Character Workspace from the pack.

It does not:

- extract a ZIP;
- copy a folder into `characters/**`;
- write `.relaylm/build/**`;
- trust imported generated/runtime state;
- set the active character;
- contact a remote registry;
- download template content;
- execute scripts/assets;
- apply memory, relationship, scene, emotion, or context state.

This distinction is normative current behavior.

## Commit is new-workspace creation only

The current commit function is not a generic import, merge, update, rename, replace, restore, or migration API.

It publishes exactly one previously absent target workspace after the candidate's creation-stage checks succeed.

If replacement or external-import commit is later implemented, that work must define conflict, provenance, staging revision, rollback, and activation behavior separately rather than inheriting them implicitly from this contract.

## Active-character separation

All current candidate and commit projections keep:

```text
active_character_set = false
```

The current creation core does not persist active-character selection as part of commit.

The stable lifecycle remains:

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
- RelaySLP maintenance queues or apply decisions;
- current conversation output.

Committing human-editable source files makes a workspace available for later explicit selection. It does not execute their semantics immediately.

## Public diagnostics remain content-free

Current public projections expose bounded template IDs/product metadata, validation statuses/reasons/counts, character IDs, source-family presence, directory names, compiler public summaries, commit status, and relative generated artifact names.

They do not expose:

- raw source bodies from a candidate;
- rejected template file bodies;
- raw template path inventories;
- absolute characters-root paths;
- credentials or runtime config contents;
- `.relaylm/state/**`, queue, audit, or source-evidence payloads;
- active-character mutation state beyond the explicit false flag.

## Failure behavior

Current creation/import behavior closes toward no final workspace publication and no activation:

```text
approval absent
  -> approval_required
  -> no commit

candidate ID invalid
  -> invalid_character_id
  -> no commit

candidate validation invalid
  -> invalid_candidate
  -> no commit

final target exists
  -> target_exists
  -> no overwrite/merge

materialized staging validation fails
  -> validation_failed
  -> no publish

staging compiler fails
  -> compile_failed
  -> no publish

external import validation succeeds
  -> validation result only
  -> workspace_commit_supported = false
  -> external_import_commit_pending

commit succeeds
  -> new workspace published
  -> active_character_set = false
```

The contract does not turn a validation-only external pack into a write candidate.

## Current implementation anchors

This current contract is implemented by:

```text
relaylm/character_creation.py
relaylm/soul_lab_character_creation.py
relaylm/cli/character_creation.py
```

and consumes the Character Workspace implementation behind:

```text
relaylm/character_workspace/**
```

The focused current smoke is:

```text
scripts/relaylm_cw_a5_character_creation_templates_smoke.py
```

That smoke verifies, among other things:

- registry is local/content-free and no default auto-create occurs;
- Quick and Advanced candidates validate;
- showcase starter removes demo-user example memory while as-is retains it;
- approval is required before commit;
- successful bundled-template commit creates all expected build artifacts and does not set active character;
- duplicate target commit fails;
- external folder validation can succeed without adding bundled onboarding memory;
- reserved runtime artifacts, scripts, config/env files, symlinks, and traversal ZIP entries are rejected;
- rejected source content is not copied into the public validation result.

The older CW-A5 handoff remains a transitional source until a later reviewed retirement transaction accounts for incoming references and normative disposition. This contract does not retire it.

## Stable invariants

- No-character startup never auto-creates, auto-restores, or auto-activates a default/sample character.
- Bundled template registry access is local and performs no network download.
- Quick/Advanced/Showcase staging produces a full source-tree candidate and reuses current validation/compiler boundaries.
- Candidate preview uses compiler dry-run and is not a durable commit.
- Candidate public projections do not expose raw source bodies.
- Durable bundled-template/workspace creation requires explicit approval.
- Commit rechecks candidate ID and retained validity, rejects an existing target, then revalidates the materialized staging tree.
- Current commit writes derived build artifacts inside staging before final workspace publish.
- Successful publish uses `os.replace` from staging to a previously absent final target.
- Commit cleanup removes the temporary parent on normal success/failure paths.
- Creation does not merge or overwrite an existing workspace.
- Successful creation still reports `active_character_set = false`.
- Template folders/ZIPs are validation-only under current external import support.
- The current SOUL Lab external-import route explicitly reports `workspace_commit_supported = false` and `external_import_commit_pending`.
- External import validation is confined to a configured local import root at the SOUL Lab boundary.
- Template validation does not extract ZIPs, execute files, import runtime state, or trust foreign `.relaylm/**` artifacts.
- Safe creation-source staging rejects `.relaylm/**` paths and non-text source suffixes.
- Public validation/creation diagnostics remain content-free.
- Creation/import does not mutate current REL/SCN/EMO/MEM/CTX/SLP runtime state.
- Source validation, compile success, commit, and runtime activation remain separate lifecycle states.
- Project Status remains repository-wide implementation authority.

## Non-goals

This contract does not define:

- source-tree classification already owned by `source-tree.md`;
- Markdown parsing/workspace validation internals already owned by `parser-and-validation.md`;
- compiled artifact schemas/write mechanics already owned by `compiled-projections.md`;
- external template extraction or commit, which is not currently implemented;
- remote registry, marketplace, download, signature, or update-channel behavior;
- existing-workspace merge/replacement/migration;
- active-character selection or persistence;
- semantic source schemas;
- RelaySLP maintenance candidate apply;
- runtime conversation or request-context behavior;
- UI component layout;
- source retirement or router migration;
- repository-level project sequencing.

## Related architecture and contracts

- [Character Workspace Source Tree Contract](source-tree.md)
- [Character Workspace Parser and Validation Contract](parser-and-validation.md)
- [Character Workspace Compiled Projections Contract](compiled-projections.md)
- [Character Workspace Creation and Import](../../architecture/character-workspace/creation-and-import.md)
- [Character Workspace System](../../architecture/character-workspace/system.md)
- [CW-A5 transitional implementation handoff](../../architecture/cw_a5_character_creation_templates_showcase_import.md)
