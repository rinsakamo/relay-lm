# Character Package Directory

The Character Package is portable character-owned data. It is designed to outlive individual RelayLM implementations and model providers.

## Current layout

```text
<Character>/
├─ SOUL.md
├─ config.yaml
└─ memory/
   ├─ events.jsonl
   ├─ state.json
   └─ MEMORY.md        # optional crystallized readable synthesis
```

`memory/MEMORY.md` is materialized only when crystallization produces readable memory. It is not required to open or run a character.

## `config.yaml`

Minimal example:

```yaml
format_version: 1
character:
  id: relm
  name: ReLM
```

The current package accepts only an explicit integer `format_version: 1`. String/coerced or missing version values are invalid. `character.id` and `character.name` are required non-empty strings. Invalid or malformed package metadata fails closed.

Default paths are convention-based. Future versions may permit explicit path mapping without changing semantic roles.

`config.yaml` is a package entrypoint, not an all-in-one prompt dump.

## Current file behavior

- `SOUL.md` is required and must contain non-empty Identity content.
- `memory/events.jsonl` contains RelayLM-owned persisted Events. Missing Event storage is read as an empty journal; malformed non-empty Event lines fail closed. Event IDs must be unique within the journal; a later duplicate ID fails closed with that record's line context.
- once an Event Journal append write and close succeed, failure to refresh the process-local derived file signature does not retroactively fail that durable append; cached Event/discovery data is invalidated and the next read revalidates `memory/events.jsonl`.
- a missing `memory/state.json` file is read as an empty version-1 State;
- an existing `memory/state.json` must explicitly contain integer `format_version: 1` and a `states` array; RelayLM does not infer either field for an existing file;
- each persisted State record explicitly contains `state_id`, `state_class`, `key`, `value`, `status`, and `sources`; `sources` is a non-empty array of non-empty provenance source IDs, while `valid_from` and `valid_to` are optional;
- `memory/state.json` rejects non-finite JSON numbers such as `NaN` and positive or negative infinity on both load and save;
- malformed State, missing required persisted fields, or version type coercion fails closed rather than receiving compatibility defaults;
- `memory/MEMORY.md` is optional readable crystallized synthesis. Missing readable memory is treated as absent rather than as an empty truth source. It does not replace Canonical State or Event provenance.
- State and `MEMORY.md` writes use temporary-file replacement so the visible target is replaced atomically at the filesystem boundary rather than rewritten in place.
- An unchanged crystallized Markdown body is not rewritten.

These behaviors describe the current filesystem adapter. A later storage backend may implement the same current logical contract as an intentional architecture boundary; it must not preserve superseded RelayLM semantics through an internal compatibility bridge.

## Stable future envelope

When real features require them, the package may grow toward:

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
- `knowledge/` — character-associated reference/world knowledge;
- `examples/` — behavioral/calibration examples;
- `settings/` — portable character-specific behavior/presentation configuration;
- `assets/` — portable voice/avatar/image assets;
- `cache/` — disposable, rebuildable derivatives.

Machine-specific provider URLs, API keys, GPU/microphone selection, and secrets do not belong in the Character Package.

`memory/notes/*.md` remains deferred richer Markdown/Obsidian-style memory organization. Canonical State remains machine authority. See #1260 and `docs/contracts/crystallization.md`.
