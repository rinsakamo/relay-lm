# MVP-2 Profile File Loading

This MVP-2 step adds placeholder profile file loading for persona-stable context compilation.

The compiler is still not connected to `/v1/chat/completions`. Pass-through runtime behavior remains unchanged.

## Added pieces

- `relaylm.profile.ProfileFiles`
- `relaylm.profile.ProfileTexts`
- `relaylm.profile.load_profile_texts()`
- `relaylm.profile.build_profile_blocks()`
- example profile files under `examples/profiles/default/`
- server-free profile loading smoke

## Example profile files

```text
examples/profiles/default/common_runtime_policy.md
examples/profiles/default/SOUL.md
examples/profiles/default/style.md
examples/profiles/default/ROOM_ANCHOR.md
```

The `style.md` sample is used as the configured output policy path. RelayLM's internal block type remains `character_output_policy`; the actual file path can be configured freely in later PRs.

## Run

```bash
python -m compileall relaylm scripts/relaylm_profile_loading_smoke.py
python scripts/relaylm_profile_loading_smoke.py
```

Expected output:

```text
ok load profile texts
ok build profile blocks
ok render profile context
```

## Out of scope

This step does not add:

- config schema integration for profile files
- route-to-character profile resolution
- incoming system prompt fallback
- chat completion integration
- memory or RAG
