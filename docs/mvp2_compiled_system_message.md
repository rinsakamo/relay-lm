# MVP-2 Compiled System Message

This step adds the first OpenAI-compatible message packing helper for persona-stable context compilation.

The compiler is still not connected to `/v1/chat/completions`. Pass-through runtime behavior remains unchanged.

## Added helpers

- `compile_profile_system_message()`
- `compile_profile_messages()`

## Message layout

MVP-2 uses the initial layout documented in the context compiler contract:

```text
messages[0]: compiled RelayLM context as a system message
messages[1:]: recent messages preserved after the compiled context
```

This keeps stable persona context before dynamic recent conversation while keeping latest user input near the end when recent messages are supplied.

## Run

```bash
python -m compileall relaylm scripts/relaylm_compiled_message_smoke.py
python scripts/relaylm_compiled_message_smoke.py
```

Expected output:

```text
ok compile profile system message
ok compile profile messages
ok recent messages preserved
```

## Out of scope

This step does not add:

- FastAPI integration
- automatic message rewriting in pass-through mode
- incoming system prompt fallback
- memory or RAG
