# Phase 5-D1 CJK-Aware Token Estimation Handoff

## Status

Phase 5-D1 is the next bounded implementation slice after Phase 5-C4a.

## Goal

Replace the single global `len(text) / chars_per_token` approximation with a deterministic, tokenizer-free, conservative estimator that does not systematically undercount Japanese and other CJK-heavy context.

## Required behavior

- preserve the existing public helpers and `chars_per_token` compatibility input,
- classify text deterministically into ASCII word characters, ASCII punctuation, whitespace, CJK/Kana/Hangul/full-width characters, emoji/symbols, and other non-ASCII characters,
- use conservative integer rounding,
- keep empty text at zero tokens,
- avoid model-specific tokenizer dependencies,
- expose content-free estimator diagnostics only,
- use one estimator consistently for memory assembly and message truncation,
- keep token-budget features default-off where they are already default-off,
- preserve system/current-user retention and existing fail-closed truncation behavior.

## Validation matrix

- ASCII prose,
- Japanese prose,
- mixed Japanese/ASCII,
- Markdown punctuation,
- source code,
- emoji and ZWJ sequences,
- combining marks,
- empty/whitespace-only input,
- exact budget boundaries,
- memory candidate inclusion/drop behavior,
- message truncation and preserved-message blocking,
- existing config and token-budget regressions.

## Non-goals

- model-specific exact token counts,
- downloading or loading backend tokenizers,
- changing context ownership or drop order,
- changing token-budget feature defaults,
- Stream Unpack,
- cache-hit RelaySCN projection,
- RelayCTX Compact.

## Rollback conditions

Roll back if the estimator becomes nondeterministic, undercounts CJK compared with the legacy estimate, leaks text through diagnostics, changes pass-through behavior, drops protected system/current-user messages, or silently changes configuration defaults.
