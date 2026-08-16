# Persistence and Character Portability

RelayLM 1.0 treats the Character Package as a portability contract rather than an incidental filesystem layout.

## MVP package

```text
<Character>/
├─ SOUL.md
├─ config.yaml
└─ memory/
   ├─ events.jsonl
   └─ state.json
```

The package can live under a default data root or any user-selected local directory.

## Semantic ownership

- `SOUL.md` — Identity authority;
- `memory/events.jsonl` — Event persistence;
- `memory/state.json` — accepted current State;
- `config.yaml` — package identity/layout/config entrypoint.

Filesystem format is not semantic architecture. Storage may later use segmentation or a database while preserving these logical roles and migration guarantees.

## Current MVP persistence contract

The current filesystem implementation intentionally keeps a small, strict contract:

- `config.yaml` uses `format_version: 1` and requires non-empty `character.id` and `character.name`;
- `SOUL.md` must exist and contain non-empty Identity content;
- `events.jsonl` stores one Event object per non-empty line and is appended in Event order;
- a missing `events.jsonl` is treated as an empty Event Journal;
- malformed Event JSON, malformed Event shape, malformed config, or malformed State fails closed rather than being silently repaired;
- a missing `state.json` is treated as an empty `CanonicalState(format_version=1)`;
- `state.json` writes use a temporary file followed by atomic filesystem replacement, and a failed write attempts to remove the temporary file;
- State persistence preserves JSON-serializable State values and provenance source IDs.

These are current implementation guarantees, not a claim that the underlying filesystem is the permanent storage architecture. Crash-consistent journaling, multi-process writers, backup/restore, schema migration, package integrity tooling, and broader lifecycle operations remain deferred.

## Event and State durability roles

Event persistence and Canonical State persistence are intentionally different:

```text
Event Journal
  occurrence / provenance history

Canonical State
  accepted current understanding
```

Removing a current State does not delete its source Events. Conversely, the presence of an Event does not make every statement in that Event accepted State.

## Future envelope

Future features may materialize `knowledge/`, `examples/`, `settings/`, `assets/`, and `cache/` only when they contain real data. Their semantics are tracked in #1262.

Crystallized readable memory/graph projection is tracked separately in #1260.
