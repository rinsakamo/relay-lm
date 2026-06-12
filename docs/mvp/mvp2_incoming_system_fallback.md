# MVP-2 Incoming System Prompt Fallback

This step preserves incoming OpenAI-compatible `system` and `developer` messages without letting them remain in the recent-message chain or override RelayLM's configured stable persona prefix.

The historical helper name uses `system` and `fallback` for compatibility, but the current authority meaning is:

```text
client system / developer instruction
  -> dynamic instruction evidence
  -> Input-side RelaySCN classification
  -> scene role / scene context / scene constraints

RelaySOUL
  -> separate durable persona authority
```

See `docs/architecture/client_instruction_authority_contract.md` for the canonical policy.

## Added helpers

- `split_incoming_system_messages()`
- `extract_instruction_text()`
- `build_incoming_system_prompt_block()`
- `append_incoming_system_prompt_block()`
- `compile_profile_messages_with_system_fallback()`

The compatibility helper treats both `system` and `developer` roles as instruction-bearing messages. This prevents `developer` messages from being appended unchanged after RelayLM's compiled system context in managed compilation.

`extract_instruction_text()` supports:

- ordinary string content,
- ordered text-part arrays using `type: text`,
- ordered text-part arrays using `type: input_text`.

Unsupported non-text content parts are ignored rather than stringified into the instruction block. This preserves textual developer instructions without accidentally embedding image URLs or other non-text payloads.

## Authority behavior

Incoming system/developer messages are treated as dynamic evidence, not as authority above RelayLM's stable persona blocks.

The historical compiled order is:

```text
stable profile blocks
incoming_system_prompt dynamic block
recent non-instruction messages
```

The intended pipeline interpretation is:

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

When an approved SOUL exists, the SCN-derived role guides the current situation without replacing or mutating durable identity.

When SOUL is missing, the same client instruction may establish a safe temporary scene role for the first request. RelaySOUL creation is separate: only explicitly identified durable persona evidence may become a proposal, and the raw prompt must never be persisted wholesale as `SOUL.md`.

Repeated frontend instructions should update or confirm the current scene role, not create repeated SOUL proposals.

## Run

```bash
python -m compileall relaylm scripts/relaylm_system_fallback_smoke.py
python scripts/relaylm_system_fallback_smoke.py
```

Expected output:

```text
ok normalize array-valued instruction content
ok split incoming system/developer messages
ok append incoming instruction block
ok compile messages with system/developer fallback
```

The smoke confirms that:

- string and array-valued instruction content are normalized,
- both `system` and `developer` messages are extracted,
- neither remains in the recent-message chain,
- supported text parts are included in the compatibility dynamic evidence block,
- unsupported non-text parts are not stringified into the block,
- current user/assistant messages remain in their original order.

## Out of scope

This step does not add:

- full client-history canonicalization in FastAPI,
- automatic message rewriting in pass-through mode,
- RelaySCN instruction-classification runtime,
- instruction hash/cache persistence,
- `scene_role` runtime schema wiring,
- RelayCTX control-envelope Unpack,
- RelaySOUL proposal generation or activation,
- memory or RAG,
- frontend-specific semantic instruction parsing.
