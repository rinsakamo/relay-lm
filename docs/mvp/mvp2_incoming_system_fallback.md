# MVP-2 Incoming System Prompt Fallback

This step preserves incoming OpenAI-compatible `system` messages without letting them override RelayLM's configured stable persona prefix.

The compiler is still not connected to `/v1/chat/completions`. Pass-through runtime behavior remains unchanged.

## Added helpers

- `split_incoming_system_messages()`
- `build_incoming_system_prompt_block()`
- `append_incoming_system_prompt_block()`
- `compile_profile_messages_with_system_fallback()`

## Authority behavior

Incoming system messages are treated as dynamic evidence, not as authority above RelayLM's stable persona blocks.

The compiled order is:

```text
stable profile blocks
incoming_system_prompt dynamic block
recent non-system messages
```

This preserves OpenAI-compatible frontend instructions while keeping `SOUL`, output style, and room anchor earlier in the compiled context.

## Run

```bash
python -m compileall relaylm scripts/relaylm_system_fallback_smoke.py
python scripts/relaylm_system_fallback_smoke.py
```

Expected output:

```text
ok split incoming system messages
ok append incoming system block
ok compile messages with system fallback
```

## Out of scope

This step does not add:

- FastAPI integration
- automatic message rewriting in pass-through mode
- memory or RAG
- frontend-specific system prompt parsing
