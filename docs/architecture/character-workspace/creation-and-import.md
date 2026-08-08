---
relaylm_doc_type: subsystem_architecture
relaylm_authority: character_workspace_creation_template_import_and_commit_architecture
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: character_workspace
relaylm_update_trigger:
  - Character Workspace creation or import responsibility changes
  - template trust/validation boundary changes
  - workspace commit or explicit activation boundary changes
  - Quick Create, Advanced Create, Showcase, or local import semantics change
relaylm_not_authoritative_for:
  - repository-wide implementation completion or sequencing
  - exact HTTP/CLI schemas, template manifest fields, slugs, UI controls, or filesystem transaction implementation
  - remote template registry, network provenance, or marketplace behavior not separately governed
  - runtime conversation semantics, RelaySLP maintenance apply, RelayMEM lifecycle, or active-character selection internals
relaylm_current_status_source: ../../PROJECT_STATUS.md
relaylm_related_authority:
  - system.md
  - source-compiler.md
  - ../cw_a5_character_creation_templates_showcase_import.md
  - ../character_template_creation_flow.md
  - ../cw_a1_file_first_source_tree_parser_contracts.md
  - ../cw_a2_workspace_compiler_projections.md
  - ../cw_a3_character_workspace_ui_rebuild.md
  - ../../planning/documentation-target-architecture-graph.md
relaylm_lifecycle: stable
relaylm_primary_consumers:
  - Character Workspace and SOUL Lab maintainers
  - character creation, template, import, and migration maintainers
  - source compiler, activation, privacy, and documentation reviewers
relaylm_authority_level: subsystem
---
# Character Workspace Creation and Import

## Purpose

This page is the canonical subsystem architecture for creating a new file-first Character Workspace from bounded local templates, staged source input, or validated local imports.

The stable creation boundary is:

```text
no selected valid workspace or explicit create/import action
  -> stage candidate source tree
  -> validate source structure and import safety
  -> compile deterministic preview
  -> explicit user approval
  -> commit new workspace
  -> generate local build projections
  -> active character selected only through a separate explicit action
```

Creation/import produces a workspace candidate and, after approval, a committed source tree. It does not make source discovery, preview, or commit equivalent to runtime activation.

## One full workspace model

Quick Create, Advanced Create, Showcase, and local Import are different authoring/staging experiences over one Character Workspace source model.

They do not create incompatible reduced/full workspace formats.

The accepted durable source family and lowercase/generated domains remain defined by the Character Workspace parent and Source Compiler architecture.

A simpler UI may ask for fewer inputs, but the committed result must still satisfy the accepted workspace validation contract.

## Creation modes

### Quick Create

Quick Create offers a bounded convenience path that starts from an accepted local/bundled template and a small set of user inputs.

It may deterministically substitute bounded values such as character name, tone, or intended use into the staged template source tree.

Quick Create does not bypass:

- full source-tree validation;
- source/compiler ownership;
- explicit approval;
- workspace commit checks;
- separate active-character selection.

### Advanced Create

Advanced Create exposes more of the durable source families for direct staged editing before commit.

The staged tree remains a candidate until validation and explicit approval succeed.

Advanced Create does not acquire permission to write arbitrary `.relaylm/**` runtime state, bypass source validation, or auto-apply unrelated SOUL/MEM/REL/SCN changes.

### Showcase

Showcase templates demonstrate a mature character/workspace experience but remain templates until explicitly used to create a workspace.

Showcase content does not become active user memory or active character state simply because it can be previewed.

The creation flow may distinguish curated demonstration content from a starter form that removes or resets demo user-specific material according to the accepted template contract.

### Local import

Local import accepts a bounded local folder/archive/template pack only after validation.

Import is not arbitrary filesystem trust. Imported content must satisfy the same source-tree and template-safety boundaries as local creation.

## No automatic default character

A missing valid character workspace is a creation/import state, not permission to silently synthesize or restore a default active character.

The stable rule is:

```text
no valid workspace
  -> show creation/import choice
  -> no hidden source write
  -> no sample/default auto-activation
```

A sample, bundled template, or showcase remains inert until explicit user creation/commit.

## Candidate staging

Creation/import first produces a staged candidate tree separate from an existing committed workspace.

Staging exists so validation and preview can run before durable source changes.

The candidate is not:

- a committed character workspace;
- active runtime character state;
- a current prompt source;
- a RelaySLP maintenance apply result;
- permission to overwrite an existing character.

## Template packs are content, not executable trust

A template pack is a bounded source-content package.

It may contain accepted Markdown source files, lowercase workspace material, preview metadata, and inert assets according to the owning template contract.

It must not be treated as executable code or configuration authority.

The stable trust boundary rejects or excludes unsafe material such as:

- scripts or executables;
- path traversal;
- absolute-path writes;
- unsafe symlink behavior;
- credentials/secrets;
- environment overrides;
- runtime configuration injection;
- imported queue/audit/state records;
- imported generated `.relaylm/build/**` artifacts as source authority.

Exact allowlists and manifest fields remain implementation-contract details.

## Import does not trust generated artifacts

Imported generated/runtime artifacts are not accepted as a shortcut around local validation/compilation.

The durable local source tree is validated first and local deterministic build projections are generated by the current Source Compiler after commit/approval as required.

This prevents a foreign or stale generated projection from becoming local source authority merely because it arrived inside an archive.

## Source Compiler dependency

Creation/import depends on the canonical Source Compiler boundary for:

- source/path classification;
- read-only workspace validation;
- bounded Markdown parsing;
- deterministic compiled preview/build projections;
- content-free public validation/compiler summaries.

Creation/import does not duplicate parser/compiler semantics or relax their failures.

A creation candidate that does not validate through the accepted source contract is not commit-eligible.

## Compiled preview is not activation

The staged candidate may be compiled in dry-run/preview mode before commit.

A compiled preview can demonstrate source completeness, build determinism, tier/fragment summary, and bounded UI information.

It does not mean:

- the workspace has been committed;
- the user approved it;
- the build tree has been durably written;
- the character is active;
- runtime requests may consume it.

## Explicit approval boundary

Durable workspace creation requires explicit user approval after candidate validation/preview.

The permanent transition is:

```text
candidate staged
  + validation accepted
  + preview available where applicable
  + explicit approval
  -> commit eligible
```

A browser preview, selected template card, validation success, or generated summary is not implicit approval.

## Commit boundary

Commit creates a new accepted workspace under the local character root according to the filesystem transaction contract.

The commit boundary must reject rather than silently merge/overwrite when:

- the character identifier/slug is invalid;
- validation failed;
- approval is absent;
- the target workspace already exists;
- the candidate/import violates trust constraints;
- the operation no longer matches the staged candidate/source revision.

Exact atomicity/rollback mechanics remain implementation details.

## Existing workspaces are not overwritten by creation

Creation/import is not a general workspace merge or replacement API.

It must not delete, partially merge into, or overwrite an existing character simply to make a requested name available.

Replacement/migration behavior, if introduced, requires separately governed authority and conflict handling.

## Build generation after commit

After accepted source commit, local deterministic `.relaylm/build/**` projections may be generated through the Source Compiler.

Generated build files remain derived artifacts and do not replace the committed source tree.

Compiler failure does not authorize invented generated content or automatic source rewriting.

## Activation remains separate

Workspace commit and active-character selection are distinct operations.

The stable invariant is:

```text
candidate selected
  != validated
  != previewed
  != approved
  != committed
  != compiled build written
  != active character
```

Creation/import may return a committed character that is available for later selection without activating it.

## UI zero-character behavior

When no valid workspace is available, the product UI may route the user to the creation/import surface.

That routing is presentation/control flow, not a durable active-character mutation.

The UI does not create a hidden default character to preserve a previous conversation surface.

## Server authority over writes

Browser state is not durable source authority.

Creation/import write operations remain server-side and must validate the staged candidate, source scope, request authority, and approval at the write boundary.

Stale browser state or a preview prepared for a different candidate must not be committed under a new scope.

## Template identity and provenance

Bundled/local template identity should be explicit enough for validation and user-facing provenance.

A template identifier, manifest, or display name is metadata for staging; it does not become the durable character identity unless the resulting committed source says so under its source contract.

Third-party/local imports do not automatically inherit bundled official knowledge, private state, or privileged policy merely because they resemble an official template.

## Official bundled templates

The current implementation may ship bounded local official templates for common use cases.

Their exact names and shelf ordering are product details, not permanent architecture.

The stable architectural property is that bundled templates are local content packs validated/staged through the same creation boundary and are not auto-activated.

## Showcase example memory boundary

Showcase material may include clearly marked example/template knowledge to demonstrate continuity.

Example/template memory must remain distinguishable from real user-origin durable memory.

A showcase should not fabricate personal user history or cause demo-specific observations to be treated as live user evidence after creation unless the chosen staging mode explicitly retains acceptable inert/template knowledge under the memory source contract.

## Product-help template knowledge

Bundled templates may contain bounded product-help knowledge where explicitly accepted.

Such knowledge remains ordinary source material subject to the memory source/retrieval contract.

It does not become SOUL identity, project-status authority, internal governance disclosure, or a privileged cross-reader fallback.

## Local import only by default

The bounded current architecture covers local/bundled creation and import.

Remote template registries, unbounded downloads, package ecosystems, marketplace trust, signed remote provenance, and update channels require separately governed architecture.

Local import support does not imply network trust.

## Content-free validation diagnostics

Public validation/import diagnostics remain content-free by default.

They may expose bounded classes such as:

- template/candidate validity;
- source-family presence;
- unsafe-file class/reason IDs;
- file/source counts;
- preview/build availability;
- commit eligibility;
- target-exists conflict class;
- approval-required status.

They do not expose by default:

- raw source bodies;
- memory/relationship/scene prose;
- private filesystem roots;
- credentials or rejected secret content;
- archive internals beyond bounded allowlisted metadata;
- runtime queue/state/audit payloads.

## Fail-closed behavior

Creation/import closes toward no write/no activation.

```text
candidate invalid
  -> no commit

unsafe import member
  -> reject import
  -> do not partially extract as trusted source

preview/compiler fails
  -> no fabricated successful preview
  -> no implicit approval

approval missing/stale
  -> no workspace commit

workspace target already exists
  -> reject conflict
  -> do not overwrite/merge

commit succeeds but activation not requested
  -> workspace remains available but inactive
```

## Creation does not mutate runtime subsystems

Creating a workspace does not directly set:

- current relationship target/state;
- current scene state;
- current affect state;
- ordinary-memory reader authority;
- current memory retrieval result;
- current RelayCTX request context;
- current conversation response.

Those remain request/runtime responsibilities after an explicit active character is selected.

## Creation and maintenance are separate

Character creation/import initializes a candidate/committed workspace.

RelaySLP maintenance candidates operate later on governed evidence under their own deferred maintenance architecture.

Creation/import does not borrow maintenance auto-apply authority, and maintenance does not become a second hidden character-creation path.

## Current versus target

This page is current as the canonical responsibility map for bounded Character Workspace creation and local import.

Current CW-A5 establishes bundled/local template staging, Quick/Advanced/Showcase creation, local import validation, explicit approval/commit, local deterministic build generation, and explicit active-character selection separation.

Remote registries, richer migration/merge flows, broader source-editing APIs, network provenance, or future template update channels may remain target or separately governed work.

Project Status remains authoritative for exact implementation completion.

## Stable invariants

- Quick, Advanced, Showcase, and Import produce the same accepted workspace model.
- No valid workspace does not cause automatic sample/default character creation or activation.
- Templates are content packs, not executable/configuration trust.
- Imports are validated before any durable workspace commit.
- Foreign/stale `.relaylm/**` generated/runtime artifacts do not become imported source authority.
- Source Compiler validation/preview is reused rather than bypassed.
- Compiled preview is not user approval, durable commit, or runtime activation.
- Durable commit requires explicit approval and rejects existing-target overwrite/merge.
- Build projections are generated locally as derived artifacts.
- Workspace commit and active-character selection remain separate.
- UI routing to Create is not active-character mutation.
- Browser/stale preview state cannot commit a different candidate/scope.
- Local import support does not imply remote registry/network trust.
- Creation/import does not set current REL/SCN/EMO/MEM/CTX runtime state.
- Public diagnostics remain content-free.
- Failure closes toward no write/no activation.

## Non-goals

This architecture does not define:

- exact UI component layout;
- exact HTTP or CLI fields;
- exact template manifest schema;
- exact filesystem transaction/rollback mechanism;
- remote template marketplace/registry behavior;
- automatic active-character selection;
- arbitrary existing-workspace merge/overwrite;
- RelaySLP maintenance apply policy;
- current runtime conversation semantics;
- repository-level project sequencing.

## Related architecture

- [Character Workspace Architecture](system.md)
- [Character Workspace Source Compiler](source-compiler.md)
- [CW-A5 Character Creation, Templates, and Showcase Import](../cw_a5_character_creation_templates_showcase_import.md)
- [Character Template / Creation Flow](../character_template_creation_flow.md)
- [CW-A1 File-first Source Tree and Parser Contracts](../cw_a1_file_first_source_tree_parser_contracts.md)
- [CW-A2 Workspace Compiler Projections and KV-cache Tiers](../cw_a2_workspace_compiler_projections.md)
- [CW-A3 Character Workspace UI Rebuild](../cw_a3_character_workspace_ui_rebuild.md)
