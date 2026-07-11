# MVP-2 Config Profile Resolution

This step connects RelayLM config routes to persona profile file paths without changing pass-through runtime behavior.

## Added scope

- `CharacterConfig` in `relaylm.config`
- top-level `common_runtime_policy` path in config
- `characters` map in config
- `resolve_profile_files()` helper
- `ProfileConfigurationError`
- `config.example.yaml` profile path example
- server-free config/profile smoke

## Example config shape

```yaml
common_runtime_policy: examples/profiles/default/common_runtime_policy.md

model_routes:
  relaylm-default:
    character_id: default

characters:
  default:
    soul: examples/profiles/default/SOUL.md
    output_policy: examples/profiles/default/style.md
    room_anchor: examples/profiles/default/ROOM_ANCHOR.md
```

The configured `output_policy` path can point to any file name. The sample uses `style.md`; internally the context compiler still renders it as `character_output_policy`.

## Run

```bash
python -m compileall relaylm scripts/relaylm_config_profile_smoke.py
python scripts/relaylm_config_profile_smoke.py
```

Expected output:

```text
ok resolve profile files
ok build config profile blocks
ok render config profile context
ok missing character error
```

## Out of scope

This step does not add:

- FastAPI integration
- automatic persona compilation in `/v1/chat/completions`
- incoming system prompt fallback
- memory or RAG
