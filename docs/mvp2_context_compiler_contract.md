# MVP-2 Context Compiler Contract

MVP-2 introduces the first code-level contract for persona-stable context compilation.

This PR does not connect the compiler to `/v1/chat/completions` yet. Pass-through runtime behavior remains unchanged.

## Added primitives

- `StabilityClass`
- `BlockType`
- `ContextBlock`
- `render_context_blocks()`
- `validate_block_order()`
- `build_placeholder_persona_blocks()`

## Stability order

MVP-2 preserves this ordering rule:

```text
stable_prefix -> slow_prefix -> dynamic_suffix
```

Stable prefix blocks are intended for persona and prefix-cache stability.

Initial stable prefix block order:

```text
common_runtime_policy
character_soul_anchor
character_output_policy
room_anchor
```

## Smoke check

Run:

```bash
python -m compileall relaylm scripts/relaylm_context_compiler_smoke.py
python scripts/relaylm_context_compiler_smoke.py
```

Expected output:

```text
ok stable prefix blocks
ok render context blocks
ok invalid order error
```

## Out of scope

This MVP-2 entry PR does not implement:

- config file profile loading
- SOUL.md loading from disk
- OUTPUT_POLICY.md loading from disk
- request message compilation
- memory insertion
- RAG
- FastAPI integration

Those should be added after this contract is stable.
