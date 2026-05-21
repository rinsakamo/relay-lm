# MVP-2 Summary

MVP-2 introduces RelayLM's persona-stable context compiler path.

The goal is to make RelayLM able to load character profile files, compile them into a stable OpenAI-compatible system message, preserve incoming frontend system prompts as dynamic context, and apply the compiled payload only in a gated `memory_light` mode.

## Completed scope

MVP-2 currently covers:

- context compiler primitives
- stable prefix block ordering
- profile file loading placeholders
- config-based character/profile resolution
- compiled system message generation
- incoming system prompt fallback
- profile compile dry-run planning
- diagnostics-only dry-run headers
- gated compile decision
- memory-light payload compilation helper
- runtime forwarding connection for memory-light mode
- API smoke visibility for compiler-used state

## Runtime behavior

Default `config.example.yaml` remains `pass_through`.

```text
pass_through -> request payload stays unchanged, diagnostics only
memory_light -> request payload can be rewritten with compiled profile messages
memory_full -> reserved for later memory/RAG work
```

## Stable context layout

The compiled message layout is:

```text
messages[0]: compiled RelayLM system context
messages[1:]: recent non-system messages
```

Inside the compiled RelayLM system context, the current MVP-2 block order is:

```text
common_runtime_policy
character_soul_anchor
character_output_policy
room_anchor
incoming_system_prompt
```

The incoming OpenAI-compatible `system` prompt is preserved as `incoming_system_prompt`, but it is placed after RelayLM's stable persona/profile blocks.

## Main validation commands

Server-free compile contract checks:

```bash
python -m compileall relaylm scripts/relaylm_context_compiler_smoke.py
python scripts/relaylm_context_compiler_smoke.py

python -m compileall relaylm scripts/relaylm_profile_loading_smoke.py
python scripts/relaylm_profile_loading_smoke.py

python -m compileall relaylm scripts/relaylm_config_profile_smoke.py
python scripts/relaylm_config_profile_smoke.py

python -m compileall relaylm scripts/relaylm_compiled_message_smoke.py
python scripts/relaylm_compiled_message_smoke.py

python -m compileall relaylm scripts/relaylm_system_fallback_smoke.py
python scripts/relaylm_system_fallback_smoke.py

python -m compileall relaylm scripts/relaylm_profile_compile_dry_run_smoke.py
python scripts/relaylm_profile_compile_dry_run_smoke.py

python -m compileall relaylm scripts/relaylm_compile_gate_smoke.py
python scripts/relaylm_compile_gate_smoke.py

python -m compileall relaylm scripts/relaylm_memory_light_apply_smoke.py
python scripts/relaylm_memory_light_apply_smoke.py
```

API smoke with default pass-through config:

```bash
cp -f config.example.yaml config.yaml
python -m relaylm.app --config config.yaml
```

In another terminal:

```bash
python scripts/relaylm_api_smoke.py \
  --base-url http://127.0.0.1:8090 \
  --model relaylm-default \
  --expected-mode pass_through \
  --expected-profile-compile-dry-run true \
  --expected-compiler-used false
```

API smoke with temporary memory-light config:

```bash
cp -f config.example.yaml config.memory_light.yaml
python - <<'PY'
from pathlib import Path
path = Path('config.memory_light.yaml')
text = path.read_text()
text = text.replace('mode: pass_through', 'mode: memory_light', 1)
text = text.replace('    mode: pass_through', '    mode: memory_light', 1)
path.write_text(text)
PY
python -m relaylm.app --config config.memory_light.yaml
```

In another terminal:

```bash
python scripts/relaylm_api_smoke.py \
  --base-url http://127.0.0.1:8090 \
  --model relaylm-default \
  --expected-mode memory_light \
  --expected-profile-compile-dry-run true \
  --expected-compiler-used true
```

A `502` chat status is acceptable when the configured backend is not running. The smoke checks RelayLM's routing, diagnostics, and compilation path before backend availability.

## Out of scope

MVP-2 does not implement:

- memory retrieval
- RAG
- vector stores
- automatic memory writes
- conversation persistence
- token counting or budget trimming
- TTS/Live2D-specific output post-processing
- backend KV-cache mutation

## Next phase: MVP-3

MVP-3 should focus on a small practical memory layer.

Recommended first MVP-3 scope:

- local JSONL conversation trace
- explicit memory candidate records
- manual memory seed file
- memory block insertion after stable persona blocks
- memory-light smoke with fixed memory snippets
- no embeddings/vector DB at first

MVP-3 should preserve the MVP-2 safety boundary: `pass_through` remains unchanged and `memory_light` is the first apply path.
