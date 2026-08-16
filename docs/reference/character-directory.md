# Character Package Directory

The Character Package is portable character-owned data. It is designed to outlive individual RelayLM implementations and model providers.

## MVP layout

```text
<Character>/
├─ SOUL.md
├─ config.yaml
└─ memory/
   ├─ events.jsonl
   └─ state.json
```

## `config.yaml`

Minimal example:

```yaml
format_version: 1
character:
  id: relm
  name: ReLM
```

Default paths are convention-based. Future versions may permit explicit path mapping without changing semantic roles.

`config.yaml` is a package entrypoint, not an all-in-one prompt dump.

## Stable future envelope

When real features require them, the package may grow toward:

```text
<Character>/
├─ SOUL.md
├─ config.yaml
├─ memory/
├─ knowledge/
├─ examples/
├─ settings/
├─ assets/
└─ cache/
```

Meanings:

- `memory/` — lived continuity;
- `knowledge/` — character-associated reference/world knowledge;
- `examples/` — behavioral/calibration examples;
- `settings/` — portable character-specific behavior/presentation configuration;
- `assets/` — portable voice/avatar/image assets;
- `cache/` — disposable, rebuildable derivatives.

Machine-specific provider URLs, API keys, GPU/microphone selection, and secrets do not belong in the Character Package.

Later crystallized memory may add `memory/MEMORY.md` and `memory/notes/*.md` as a Markdown/Obsidian-style readable projection while Canonical State remains machine authority. See #1260.
