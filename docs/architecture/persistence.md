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

## Future envelope

Future features may materialize `knowledge/`, `examples/`, `settings/`, `assets/`, and `cache/` only when they contain real data. Their semantics are tracked in #1262.

Crystallized readable memory/graph projection is tracked separately in #1260.
