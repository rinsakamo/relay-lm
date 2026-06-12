# MVP-2 Incoming System Prompt Fallback

This step preserves incoming OpenAI-compatible `system` messages without letting them override RelayLM's configured stable persona prefix.

The compiler is still not connected to `/v1/chat/completions`. Pass-through runtime behavior remains unchanged.

The historical helper name uses `fallback`, but the current authority meaning is narrower:

```text
existing SOUL:
  incoming system prompt is non-authoritative dynamic evidence

missing SOUL on the first managed request:
  the first eligible system prompt may be bootstrap evidence
  for creating the initial RelaySOUL persona-source revision
```

See `docs/architecture/client_instruction_authority_contract.md` for the canonical policy.

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

When an approved SOUL exists, the dynamic block must not replace or mutate it.

When SOUL is missing and the route explicitly enables bootstrap, the first valid incoming system prompt may temporarily preserve frontend persona behavior for the first request and seed RelaySOUL persona-source creation. The raw prompt must not be persisted wholesale as `SOUL.md`; RelaySOUL should classify durable identity, output policy, relationship state, and temporary scene material into the correct source files.

After a valid RelaySOUL revision is activated, later client system prompts return to non-authoritative evidence and cannot silently replace the active persona.

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
- RelaySOUL bootstrap persistence or activation
- memory or RAG
- frontend-specific system prompt parsing
