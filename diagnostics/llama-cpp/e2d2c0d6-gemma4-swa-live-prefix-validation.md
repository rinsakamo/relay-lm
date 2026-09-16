# #2947 follow-up discriminator (diagnostic only)

Target llama.cpp revision: `e2d2c0d6aa9b996d5d3a3c1d5e24c8c19728bb3d`

## Frozen observed facts

Unpatched buffered Pass2 (g2):

- exact input tokens: 2927
- true LCP: 865 (`865/2927` in `llama-server.log`)
- `n_swa`: 1024
- live `pos_min`: 0
- `pos_min_thold`: 0
- restored checkpoint: `[0,366]`, `n_tokens=367`
- resulting `n_past/cache_n`: 366
- prompt-eval tokens: 2561
- completion tokens: 256
- finish reason: `length`

Immutable cache-off control (#2934) for the exact same serialized buffered Pass2 request:

- prompt tokens: 2927
- completion tokens: 96
- finish reason: `stop`

## Patch hypothesis

When `has_new_tokens && n_swa > 0 && pos_min_thold == 0 && pos_min == 0`, the entire SWA history required by the next prompt token is still resident in live KV. Restoring an older checkpoint is unnecessary and rolls `n_past` backward.

The diagnostic patch skips only that restore case.

## Hard predictions

For the same treatment topology, if no other path intervenes:

- g2 `cache_n/n_past`: **865** (not 366)
- g2 prompt-eval tokens: **2062** (= 2927 - 865)
- g3 `cache_n/n_past`: **865** (not 366)
- g3 prompt-eval tokens: **18** (= 883 - 865)
- g4 `cache_n/n_past`: **865** (not 366)
- g4 prompt-eval tokens: **2062**

The semantic discriminator is buffered Pass2:

- if it returns ~96 tokens / `finish_reason=stop` with valid structured output, unnecessary checkpoint rollback is strongly implicated;
- if it still diverges or reaches `length`, residual cache/prefill numerical non-equivalence (e.g. llama.cpp #28368 class) remains.

## Scope discipline

This patch is a diagnostic discriminator, not a production RelayLM change and not yet an upstream-general fix. Do not modify RelayLM production cache policy based on the patch alone. Run it under a new separately-owned physical experiment; #2947 remains consumed exactly once and immutable.
