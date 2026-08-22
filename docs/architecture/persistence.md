# Persistence and Character Portability

RelayLM 1.0 treats the Character Package as a portability contract rather than an incidental filesystem layout.

## Current package

```text
<Character>/
├─ SOUL.md
├─ config.yaml
└─ memory/
   ├─ events.jsonl
   ├─ state.json
   └─ MEMORY.md        # optional crystallized readable synthesis
```

The package can live under a default data root or any user-selected local directory.

## Semantic ownership

- `SOUL.md` — Identity authority;
- `memory/events.jsonl` — Event persistence and occurrence/provenance history;
- `memory/state.json` — accepted current State;
- `memory/MEMORY.md` — optional readable crystallized semantic synthesis, not current-State authority;
- `config.yaml` — package identity/layout/config entrypoint.

Filesystem format is not semantic architecture. Storage may later use segmentation or a database while preserving these logical roles and migration guarantees.

## Current filesystem persistence contract

The current filesystem implementation intentionally keeps a small, strict contract:

- `config.yaml` explicitly contains integer `format_version: 1` and requires non-empty `character.id` and `character.name`; version values are not string-coerced or defaulted;
- `SOUL.md` must exist and contain non-empty Identity content;
- `events.jsonl` stores one Event object per non-empty line and is appended in Event order;
- Event IDs are unique within one `events.jsonl`; a later record that repeats an earlier Event ID is malformed persisted authority and loading fails closed at that duplicate line;
- a missing `events.jsonl` is treated as an empty Event Journal;
- malformed Event JSON, malformed Event shape, malformed config, or malformed State fails closed rather than being silently repaired;
- within one `CharacterDirectory` process, a successfully validated Event Journal snapshot may be reused while the authoritative file signature is unchanged;
- RelayLM-owned successful `append_event` calls incrementally extend an already-valid process-local snapshot, while detected external file changes invalidate the snapshot and force authoritative JSONL revalidation;
- the Event snapshot is derived, non-persistent, and never replaces `events.jsonl` as occurrence/provenance authority; malformed external edits remain fail-closed rather than being masked by stale cached Events;
- a missing `state.json` file is treated as an empty `CanonicalState(format_version=1)`;
- an existing `state.json` must explicitly contain integer `format_version: 1` and a `states` array; missing fields and version type coercion are rejected rather than interpreted as an older/looser format;
- every persisted State record explicitly contains `state_id`, `state_class`, `key`, `value`, `status`, and `sources`; `sources` is a non-empty array of non-empty provenance source IDs, and only `valid_from` and `valid_to` are optional in the current record representation;
- `state.json` writes use a temporary file followed by atomic filesystem replacement, and a failed write attempts to remove the temporary file;
- State persistence preserves JSON-serializable State values and provenance source IDs;
- a missing `MEMORY.md` means no prior crystallized readable memory and does not block ordinary character operation;
- `MEMORY.md` writes also use temporary-file replacement;
- byte-for-byte unchanged crystallized Markdown is not rewritten.

File absence and malformed existing content are deliberately different: an unmaterialized optional persistence file may have a defined empty/absent meaning, while an existing versioned file is never repaired through compatibility defaults.

The process-local Event snapshot only removes repeated disk parsing of an unchanged journal within one live `CharacterDirectory`. It is not a persistent search index and does not make targeted retrieval asymptotically independent of Event count. Persistent/segmented indexing, if later justified, must remain derived from the Event Journal rather than becoming a second Event authority.

These are current implementation guarantees, not a claim that the underlying filesystem is the permanent storage architecture. Crash-consistent multi-file transactions, multi-process writers, backup/restore, schema migration, package integrity tooling, and broader lifecycle operations remain deferred.

## Event, State, and crystallized-memory durability roles

The durable layers are intentionally different:

```text
Event Journal
  occurrence / provenance history

Canonical State
  accepted current understanding

MEMORY.md
  readable long-term semantic synthesis
```

Removing a current State does not delete its source Events. Conversely, the presence of an Event does not make every statement in that Event accepted State. `MEMORY.md` may summarize durable meaning but does not override State for current truth or Events for what occurred.

Crystallization write-back into current State is governed through the existing StateCandidate + Validator path; writing Markdown alone never promotes prose into accepted State. See `docs/contracts/crystallization.md`.

## Future envelope

Future features may materialize `knowledge/`, `examples/`, `settings/`, `assets/`, and `cache/` only when they contain real data. Their semantics are tracked in #1262.

Richer `memory/notes/*.md` wiki organization and actual crystallizer-provider behavior remain tracked in #1260. Retrieval of crystallized memory into bounded ordinary-turn Context remains tracked in #1267.
