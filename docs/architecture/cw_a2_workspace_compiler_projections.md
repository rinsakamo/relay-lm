---
relaylm_doc_type: implementation_handoff
relaylm_authority: cw_a2_workspace_compiler_projection_contract
relaylm_status: current
relaylm_volatility: medium
relaylm_owner: architecture
relaylm_update_trigger:
  - Character Workspace compiler artifact schemas change
  - KV-cache tier projection contract changes
  - compiler public diagnostics boundary changes
  - runtime RelayCTX injection begins consuming CW-A2 artifacts
relaylm_not_authoritative_for:
  - current runtime prompt injection behavior
  - CW-A3 UI implementation
  - CW-A4 RelaySLP workspace maintenance behavior
  - RelayMEM Primary lifecycle authority
relaylm_current_status_source: ../PROJECT_STATUS.md
relaylm_related_authority:
  - file_first_character_workspace_design.md
  - cw_a1_file_first_source_tree_parser_contracts.md
  - project_execution_plan.md
  - pipeline_responsibility_design.md
---
# CW-A2 Workspace Compiler Projections and KV-cache Tiers

## Purpose

CW-A2 adds the first implementation slice for compiling a file-first Character Workspace into deterministic generated artifacts.

The compiler consumes the CW-A1 source tree and parser contract and emits `.relaylm/build/**` artifacts. The Markdown source tree remains the editable source of truth. Runtime RelayCTX prompt injection, CW-A3 UI rebuild, CW-A4 RelaySLP workspace maintenance, and CW-A5 character creation/template flows remain out of scope.

## Current implementation boundary

CW-A2 is explicit and caller-invoked:

```bash
PYTHONPATH=. python scripts/relaylm_character_workspace_compile.py \
  --workspace-root runtime/characters/koyomi \
  --dry-run

PYTHONPATH=. python scripts/relaylm_character_workspace_compile.py \
  --workspace-root runtime/characters/koyomi \
  --write
```

Default behavior is dry-run. Dry-run generates the same artifact bytes in memory and prints a content-free public projection. `--write` is required before files are written.

The compiler writes only the following files under `.relaylm/build/`:

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

It does not write `.relaylm/state/**`, `.relaylm/sources/**`, `.relaylm/audit/**`, `.relaylm/queue/**`, uppercase Markdown source files, lowercase wiki pages, RelayMEM stores, queue records, or runtime request payloads.

## Artifact contract

All generated artifacts are deterministic and byte-stable for the same source tree:

- JSON is serialized with stable key order.
- JSONL rows are emitted in stable source/unit order.
- Every artifact has a fixed trailing newline.
- Artifact payloads do not include file mtimes, host temp paths, absolute paths, current timestamps, generated-at fields, random UUIDs, queue records, memory IDs, or runtime-private payloads.
- Generated artifacts include source content hashes and stable fragment or unit IDs.
- Unchanged anchored fragments keep stable IDs. For Markdown blocks without anchors, deterministic path/heading/ordinal IDs are used.

The common artifact envelope includes:

```json
{
  "schema_version": "relaylm.character_workspace.<artifact>.v0",
  "generated_by": "relaylm.character_workspace_compiler",
  "diagnostics_only": false,
  "workspace_format": "relaylm.character_workspace.v0",
  "content_hash": "sha256:...",
  "source_fragments": []
}
```

## Artifact responsibilities

### `character_manifest.json`

The manifest summarizes the workspace and build boundary. It includes required uppercase source presence, optional `LORE.md` presence, lowercase wiki domain presence, build artifact schema versions, source file hashes, fragment counts, tier summary, validation status, and blocking reason IDs.

It does not include absolute paths, raw full Markdown bodies, memory IDs, queue records, timestamps, or private runtime payloads.

### `style_projection.json`

`STYLE.md` produces Tier 1 output-surface projection metadata for voice, tone, roleplay flavor, formatting, response density, and output surface hints.

It does not own SOUL identity, memory truth, relationship permission, scene selection, or runtime state.

### `emotion_projection.json`

`EMOTION.md` produces Tier 1 emotion profile projection metadata for emotion definitions, expression modulation hints, and boundary-compatible metadata.

It does not save current emotion state and does not write `.relaylm/state/emotion_state.json`.

### `scene_units.jsonl`

`SCENE.md` produces Tier 1 scene policy units. Active `scenes/**/*.md` pages produce Tier 2 candidate units. `scenes/_inbox/**` stays candidate/staging and is not marked as stable prompt content.

CW-A2 does not implement the ACG-6 scene-wiki classifier, does not select all scenes for prompting, and does not change RelaySCN runtime order.

### `relationship_projection.json`

`RELATIONSHIP.md` produces Tier 1 relationship role and parameter vocabulary projection metadata. Active `relationships/<target>.md` pages produce Tier 2 candidate summaries. `relationships/_inbox/**` remains proposal/candidate content.

CW-A2 does not rewrite RelayREL policy, auto-apply important relationship parameters, or merge relationship state into SOUL identity.

### `memory_units.jsonl`

`MEMORY.md` produces Tier 1 memory policy units. Lowercase memory pages are treated as human-editable pages, not one-file-per-memory records. Markdown blocks become internal units.

`memory/inbox/**` is candidate/staging and not stable prompt content. `memory/forgotten/**` is excluded from ordinary prompt candidate units. Stable/high-importance active blocks are emitted as Tier 2 candidates. Retrieved memory blocks remain Tier 3 runtime-side content and are represented only by the context projection contract in this PR.

CW-A2 does not replace RelayMEM Primary lifecycle authority, mutate memory, or run SLP auto-merge/auto-apply.

### `context_projection.json`

`context_projection.json` records the minimum KV-cache tier contract:

```text
Tier 0: runtime/system/safety wrapper
  outside character workspace; compiler references but does not own it

Tier 1: character stable prefix
  SOUL.md
  STYLE.md
  EMOTION.md
  RELATIONSHIP.md
  MEMORY.md
  BOUNDARY.md
  optional LORE.md
  selected compact SCENE.md policy summary

Tier 2: target/session semi-stable prefix
  selected relationships/<target>.md summary
  selected active scene page summary
  selected stable memory summaries or high-importance memory blocks

Tier 3: dynamic suffix
  .relaylm/state scene_state / emotion_state summaries
  retrieved memory blocks
  current short-term CTX
  latest user input
  request-local policy flags
```

CW-A2 does not inject Tier 3 runtime content. The projection only states that Tier 3 belongs last and remains runtime-owned.

### `links.jsonl`

`links.jsonl` records deterministic source-to-fragment, fragment-to-artifact, page-to-unit, and unit-to-artifact references. Links use workspace-relative paths only and avoid runtime private identifiers.

## Content-free public projection

`build_character_workspace_compiler_projection(...)` returns a public diagnostics projection with:

```text
content_free: true
artifact names
artifact hashes
artifact counts
tier counts
blocking reason IDs
```

It does not include raw Markdown, memory text, relationship bodies, scene bodies, absolute paths, runtime private IDs, queue records, or private payloads.

## Non-goals

CW-A2 does not implement:

- CW-A3 Character Workspace UI rebuild
- CW-A4 RelaySLP workspace maintenance, proposals, or auto-apply
- CW-A5 character creation, templates, or showcase import
- ACG-6 scene classifier execution
- runtime RelayCTX injection
- RelayMEM Primary lifecycle replacement
- O2/O3 worker service or always-on operation
- TTS, avatar, Live2D, or ASR
- uppercase source mutation
- `.relaylm/state/**` updates
- public exposure of raw source bodies or runtime-private evidence

## Validation

Use:

```bash
python -m compileall -q relaylm scripts
PYTHONPATH=. python scripts/relaylm_cw_a1_file_first_workspace_smoke.py
PYTHONPATH=. python scripts/relaylm_cw_a2_workspace_compiler_smoke.py
PYTHONPATH=. python scripts/relaylm_docs_link_check.py
PYTHONPATH=. python scripts/relaylm_documentation_current_boundary_smoke.py
```
