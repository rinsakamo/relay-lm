# MVP-2 Memory-light Apply Helper

This step adds the first payload compilation helper for `memory_light` mode.

It does not connect the helper to `/v1/chat/completions` yet.

## Rule

```text
pass_through -> payload unchanged
memory_light -> replace messages with compiled profile messages when the profile plan is ready
```

## Added pieces

- `CompiledRequest`
- `compile_chat_payload_if_enabled()`
- server-free memory-light apply smoke

## Run

```bash
python -m compileall relaylm scripts/relaylm_memory_light_apply_smoke.py
python scripts/relaylm_memory_light_apply_smoke.py
```

Expected output:

```text
ok pass-through payload unchanged
ok memory-light payload compiled
ok compiled request log payload
```

## Out of scope

This step does not add FastAPI runtime integration. That should be done in a follow-up PR after the helper contract is validated.
