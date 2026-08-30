# Cognitive Package Root and Character Package Directory

A Cognitive Package is portable package-owned semantic data rooted at one filesystem directory. A Character Package remains a supported specialization of this boundary; machine-like or otherwise non-personal packages use the same runtime and persistence boundary without fabricating human persona metadata.

The root is not classified by its parent directory name. Both of these are valid shapes, for example:

```text
characters/relm/
machines/medical-soap/
```

## Current layout

```text
<CognitivePackage>/
├─ SOUL.md
├─ config.yaml
├─ knowledge/         # optional package-authored read-only reference text
└─ memory/
   ├─ events.jsonl
   ├─ state.json
   └─ MEMORY.md        # optional crystallized readable synthesis
```

`memory/MEMORY.md` is materialized only when crystallization produces readable memory. It is not required to open or run a package.

## `config.yaml`

A general non-personal package declares stable package identity without Character persona fields:

```yaml
format_version: 1
package:
  id: medical-soap
```

A Character Package keeps its existing specialization unchanged:

```yaml
format_version: 1
character:
  id: relm
  name: ReLM
```

Exactly one of `package` or `character` is the package identity authority. Defining both, or neither, is invalid. The current package accepts only an explicit integer `format_version: 1`. String/coerced or missing version values are invalid. `package.id` is a required non-empty string for a general Cognitive Package. Character Packages continue to require non-empty `character.id` and `character.name`.

Duplicate YAML mapping keys anywhere in `config.yaml` are malformed persisted authority and fail closed. The general loader consumes the same duplicate-key-rejecting filesystem path as the Character specialization; generalization does not introduce a looser config parser.

Default paths are convention-based. Runtime loading does not require a root to live under `characters/`, `machines/`, or any closed package-kind directory. Public Cognitive Profile routing is owned separately by #1889; this package boundary does not add profile orchestration.

`config.yaml` is a package entrypoint, not an all-in-one prompt dump. Provider URLs, provider model IDs, API keys, host policy, hardware selection, and other runtime secrets/configuration remain outside the portable package.

## Current file behavior

- `SOUL.md` is required by the current runtime and must contain non-empty stable identity or role authority. For a machine-like package this may be role-oriented rather than human-persona-oriented content.
- `knowledge/` is optional package-authored read-only reference material. KNOWLEDGE is distinct from SOUL, State, Event provenance, and lived `memory/MEMORY.md`; supported v0 assets and bounds are defined in `docs/reference/knowledge.md`.
- `memory/events.jsonl` contains RelayLM-owned persisted Events. Missing Event storage is read as an empty journal; malformed non-empty Event lines fail closed. Event IDs must be unique within the journal; a later duplicate ID fails closed with that record's line context.
- once an Event Journal append write and close succeed, failure to refresh the process-local derived file signature does not retroactively fail that durable append; cached Event/discovery data is invalidated and the next read revalidates `memory/events.jsonl`.
- a missing `memory/state.json` file is read as an empty version-1 State;
- an existing `memory/state.json` must explicitly contain integer `format_version: 1` and a `states` array; RelayLM does not infer either field for an existing file;
- duplicate JSON object member names anywhere within `memory/state.json` fail closed rather than selecting one duplicate value;
- each persisted State record explicitly contains `state_id`, `state_class`, `key`, `value`, `status`, and `sources`; `sources` is a non-empty array of non-empty provenance source IDs, while `valid_from` and `valid_to` are optional;
- `memory/state.json` rejects non-finite JSON numbers such as `NaN` and positive or negative infinity on both load and save;
- malformed State, missing required persisted fields, or version type coercion fails closed rather than receiving compatibility defaults;
- `memory/MEMORY.md` is optional readable crystallized synthesis. Missing readable memory is treated as absent rather than as an empty truth source. It does not replace Canonical State or Event provenance.
- State and `MEMORY.md` writes use temporary-file replacement so the visible target is replaced atomically at the filesystem boundary rather than rewritten in place.
- stale State write-back remains guarded by the existing opaque State revision check, and guarded `MEMORY.md` persistence fails closed when current State changed first.
- an unchanged crystallized Markdown body is not rewritten.

State, Event Journal, and `MEMORY.md` paths are always relative to the selected Cognitive Package root. Separate roots therefore keep separate persistence authority even when they share the same physical provider/model configuration.

These behaviors describe the current filesystem adapter. A later storage backend may implement the same current logical contract as an intentional architecture boundary; it must not preserve superseded RelayLM semantics through an internal compatibility bridge.

## Character specialization future envelope

When real Character features require them, a Character Package may grow toward:

```text
<Character>/
├─ SOUL.md
├─ config.yaml
├─ memory/
│  ├─ events.jsonl
│  ├─ state.json
│  ├─ MEMORY.md
│  └─ notes/
├─ knowledge/
├─ examples/
├─ settings/
├─ assets/
└─ cache/
```

Meanings:

- `memory/` — lived continuity and readable crystallized synthesis;
- `knowledge/` — package-authored read-only reference/world knowledge; Core 1.0 v0 supports the bounded text form in `docs/reference/knowledge.md`;
- `examples/` — behavioral/calibration examples;
- `settings/` — portable package-specific behavior/presentation configuration when such semantics are owned;
- `assets/` — portable voice/avatar/image assets when relevant to the package specialization;
- `cache/` — disposable, rebuildable derivatives.

Optional components are materialized only when an owner-defined feature actually requires them. A machine-like package is not required to carry Character-only components such as relationship or emotion material merely to satisfy the runtime loader.

`memory/notes/*.md` remains deferred richer Markdown/Obsidian-style memory organization. Canonical State remains machine authority. See #1260 and `docs/contracts/crystallization.md`.
