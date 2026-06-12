# MVP-2 Incoming System Prompt Fallback

This step preserves incoming OpenAI-compatible `system` messages without letting them override RelayLM's configured stable persona prefix.

The compiler is still not connected to `/v1/chat/completions`. Pass-through runtime behavior remains unchanged.

The historical helper name uses `fallback`, but the current authority meaning is:

```text
client system prompt
  -> dynamic instruction evidence
  -> Input-side RelaySCN classification
  -> scene role / scene context / scene constraints

RelaySOUL
  -> separate durable persona authority
```

See `docs/architecture/client_instruction_authority_contract.md` for the canonical policy.

## Added helpers

- `split_incoming_system_messages()`
- `build_incoming_system_prompt_block()`
- `append_incoming_system_prompt_block()`
- `compile_profile_messages_with_system_fallback()`

## Authority behavior

Incoming system messages are treated as dynamic evidence, not as authority above RelayLM's stable persona blocks.

The historical compiled order is:

```text
stable profile blocks
incoming_system_prompt dynamic block
recent non-system messages
```

The intended pipeline interpretation is now:

```text
incoming_system_prompt dynamic evidence
  -> RelaySCN
  -> normalized scene_state
     - scene_type
     - scene_role
     - scene_context
     - scene_constraints / scene_policy
  -> RelayCTX dynamic suffix
```

When an approved SOUL exists, the SCN-derived role guides the current situation without replacing or mutating the durable identity.

When SOUL is missing, the same client instruction may still establish a safe temporary scene role for the first request. RelaySOUL creation is a separate process: only explicitly identified durable persona evidence may become a proposal, and the raw prompt must never be persisted wholesale as `SOUL.md`.

Repeated frontend system prompts should update or confirm the current scene role, not create repeated SOUL proposals.

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
- RelaySCN instruction classification runtime
- `scene_role` runtime schema wiring
- RelaySOUL proposal generation or activation
- memory or RAG
- frontend-specific system prompt parsing
