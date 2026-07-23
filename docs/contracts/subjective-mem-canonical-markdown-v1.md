---
relaylm_doc_type: contract
relaylm_authority: subjective_mem_canonical_markdown_v1_physical_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: memory
relaylm_update_trigger:
  - ST-1 page schema, renderer, partition, bounds, or platform revision changes
  - Character Workspace memory-page parsing changes
  - canonical Subjective MEM create or LC-1 lifecycle publication changes
relaylm_not_authoritative_for:
  - ordinary Subjective MEM Retrieval or projection schema
  - lifecycle operations beyond the currently implemented LC-1A Correct slice
  - Primary MEM migration or user-data migration
  - multi-host or non-POSIX publication
relaylm_related_authority:
  - subjective-mem-storage-authority-and-commit-protocol.md
  - ../adr/0005-subjective-mem-storage-authority.md
  - ../architecture/st1_subjective_mem_commit_runtime.md
  - ../architecture/lc1a_subjective_mem_correct.md
  - ../architecture/file_first_character_workspace_design.md
---
# Subjective MEM Canonical Markdown v1 Physical Contract

Last reviewed: 2026-07-23 JST

## Scope

This contract fixes the physical Markdown and single-host publication boundary used by ST-1 and LC-1A. ST-1 supports one SM-1 `create` result at revision 1 with `character_private` / `private` scope, known identity, primary formation, and active lifecycle. LC-1A appends an immutable active-to-active Correct successor while retaining every earlier canonical revision.

It does not define ordinary Retrieval, projection rows, lifecycle operations beyond Correct, migration, backup/restore, distributed writers, or a final long-term organization scheme.

## Canonical domain and placement

Canonical Subjective MEM pages live only under the exact configured character workspace `memory/**/*.md` source domain. `.relaylm/build`, indexes, projections, and immutable transaction artifacts are not canonical semantic authority.

ST-1 v1 uses a deterministic, content-heuristic-free partition:

```text
episodic -> memory/episodes/subjective-mem-v1.md
semantic -> memory/topics/subjective-mem-v1.md
```

Each partition has one stable opaque `page_id` derived from the renderer partition revision, character identity, and partition. The initial two-page rule is a bounded implementation rule, not a claim about final long-term organization.

A page is a human editing unit and may contain several logical memory revision blocks. ST-1 and LC-1A do not create one physical file per revision.

## Page and block identity

The page header records:

- `relaylm.subjective_mem_markdown_page.v1`;
- opaque page ID;
- opaque character ID;
- `episodes` or `topics` partition;
- partition and renderer revisions.

Each immutable revision is a level-two Markdown block with:

- `relaylm.subjective_mem_markdown_block.v1` for the exact legacy ST-1 revision-1 create rendering, or `relaylm.subjective_mem_markdown_block.v2` for a lifecycle successor;
- opaque block ID and stable block anchor;
- memory ID and immutable revision number;
- exact revision, grounded-content, and subjective-meaning digests;
- authorizing formation decision or lifecycle transition and creation time.

The revision-1 block ID and anchor retain the exact ST-1 derivation from memory ID and v1 block schema. A lifecycle successor identity additionally binds the immutable revision number. Neither form depends on file path, filename, page title, heading prose, block order, or mtime. Moving or retitling a valid block therefore does not redefine logical revision identity, although the implemented writer publishes only to the fixed placement above.

## Lossless revision representation

Every block contains:

1. a deterministic UTF-8 JSON representation of the complete `SubjectiveMemRevision`;
2. a separately labeled JSON string for grounded content;
3. a separately labeled JSON string for subjective meaning.

The complete revision preserves memory and character IDs, revision, exact Shared Assessment reference and digest, grounded and subjective fields, memory kind, formation stage, scope, formation snapshot, multidimensional strength, lifecycle, retrieval visibility, predecessor, authorization, and creation time.

The grounded and subjective labels must equal the corresponding fields in the complete revision. All recorded digests and lineage must verify. The page does not embed a self-referential page digest.

Rendering is deterministic UTF-8 with LF newlines and reproducible SHA-256. Render then parse must reproduce the exact revision dictionary without loss.

## Supported create shape

A block accepted by ST-1 v1 must have:

```yaml
memory_revision: 1
formation_stage: primary
lifecycle_state: active
retrieval_visible: true
predecessor_revision_or_null: null
memory_kind: episodic | semantic
scope_kind: character_private
audience_class: private
participant_id_or_null: null
relationship_id_or_null: null
scene_id_or_null: null
identity_status: known
```

`retrieval_visible: true` is the valid semantic state for an active revision. Before ST-1 finalization, safety remains owned by the separate logical selector:

```yaml
mutation_state: prepared
retrieval_eligible: false
```

After exact page and receipt finalization, that selector becomes `none` / `true`. This logical eligibility does not wire ordinary Retrieval; RT-1 owns that later boundary.


## Supported LC-1A Correct successor shape

LC-1A accepts only one exact current active revision selected by the durable singleton selector and appends one immutable successor:

```yaml
operation: correct
from_lifecycle_state: active
to_lifecycle_state: active
memory_revision: previous + 1
predecessor_revision_or_null: previous
character_id: unchanged
scope_binding: unchanged
memory_kind: unchanged
formation_stage: unchanged
formation_snapshot: unchanged
retrieval_visible: true
authorization_ref.authority_kind: lifecycle_transition
```

Corrected grounded content must equal one exact current admitted Shared Assessment revision. Corrected subjective meaning and strength are explicit governed inputs; LC-1A does not generate them. The prior canonical revision remains in the page and exactly one operations selector identifies the logical current revision. During unresolved publication that selector is ineligible; it becomes eligible only after the exact page and lifecycle receipt agree.

Pinned Correct and every other lifecycle operation remain unsupported by this slice.

## Bounds and fail-closed parsing

A canonical v1 page is bounded to:

- at most 128 logical memory blocks;
- at most 512 KiB of UTF-8 bytes.

When the fixed page is full, ST-1 fails closed. It does not choose another filename or infer a semantic folder from content.

Parsing rejects, at minimum:

- invalid UTF-8, missing final newline, oversize pages, or unsupported page schema;
- malformed or unrecognized material between blocks;
- duplicate anchors, block IDs, or logical `(memory_id, memory_revision)` identities;
- wrong character, page ID, partition, revision, kind, scope, lifecycle shape, or broken predecessor chain;
- mismatched revision, grounded-content, subjective-meaning, decision, creation-time, or block digests;
- ambiguous blocks or unsupported metadata.

Character Workspace parsing remains the heading/anchor substrate. Existing CW-A1 behavior outside this strict page schema is unchanged.

## Supported platform and secure replacement

ST-1 apply supports one local POSIX host with evidence-backed directory-file-descriptor primitives. The platform revision is `relaylm.subjective_mem_commit.posix_dirfd.v1`.

Apply requires:

- an existing validated absolute workspace root and character workspace;
- existing canonical parent directories;
- component-by-component traversal with no symlink following;
- an allowlisted Character Workspace memory-page path;
- a page-domain exclusive lock;
- under-lock pre-image state and digest revalidation;
- a private complete staging file, file fsync, atomic rename, exact installed-byte and parsed-lineage verification, then parent-directory fsync;
- receipt/current-state finalization while the same page lock remains held.

Root, character, parent, target, lock, artifact, or staging symlink ambiguity fails closed. Non-regular files, stale pre-images, unsupported primitives, uncertain durability, post-install mismatch, or unknown writer exceptions never produce success.

Windows startup and configuration remain supported, but ST-1 apply fails closed as unsupported until a separate platform contract is accepted and validated.

## Immutable transaction artifact

The rendered post-image may be stored under the private character `.relaylm/state` domain as an immutable content-addressed artifact. It is recovery material only: non-editable, byte-bound to the intent, and never a second live memory or canonical source.
