# RelayLM 2.0 — P2 ordinary-summary termination qualification

Authority: #2211 scientific owner, #2530 protocol-repair freeze, #2533 repository implementation. Physical procedure remains #2363.

## Why this gate exists

S3-R2 and S3-R3 independently stopped on `P2_ORDINARY_SUMMARY` formation with `finish_reason=length`, first at a 512-token hard ceiling and later at a 1024-token hard ceiling. Both results remain immutable, non-citable S3 incompletes. The repeated mechanical failure is sufficient to reject another blind output-ceiling increase before repairing P2 termination.

This gate does not test representation efficacy. It tests only whether the ordinary-summary control can terminate predictably under an explicit finite visible-content contract.

## Frozen bounded P2 contract

The historical P2 instruction remains unchanged under ordinary imports. Qualification and a future R4 campaign add the following scoped instruction to the same P2 source packet and the same one-call formation semantics:

```text
Return one plain-text recap paragraph only.
Use no more than 120 words and no more than 800 Unicode characters.
Preserve supported conditions, recurring patterns, exceptions, and outcomes.
You may infer/generalize regularities when supported by the observations.
Do not include a heading, bullet list, special schema, or step-by-step derivation.
Stop after the recap paragraph.
```

P2 remains ordinary plain text, may infer supported regularities, and receives no Memory/Structure/Crystal schema or evaluator-hidden rule. The provider hard ceiling remains 1024 tokens only as a fail-safe. `finish_reason != stop` remains terminal.

## Non-citable qualification

Identity label:

```text
relaylm2-cognitive-ir-p2-termination-qual-v1
```

Seed derivation is SHA-256 of `<label>|<regime>|seed|<index>`, taking the first 32 bits and masking to a positive 31-bit integer. The frozen seeds are repository constants and are disjoint from prior S3/S2/calibration evidence and from the separately precommitted future R4 seeds.

Execution order is `shared -> null -> mismatch -> shift`, three families per regime, P2 formation only. This is exactly 12 semantic calls and 24 exact `/input_tokens` requests under one managed llama-server lifetime.

Every call must mechanically satisfy:

- `finish_reason == stop`;
- non-empty visible content;
- at most 800 Unicode characters;
- at most 120 whitespace-delimited words;
- reasoning absent or empty where exposed;
- exact provider and input-token accounting.

Only content length, digest, token counts, reasoning-field status, and admission state are persisted. No correctness score, latent-rule decoding, cross-arm comparison, or efficacy metric is produced. The terminal result is always non-citable and has `architecture_consequence=NONE`.

## Physical boundary

After #2533 is merged and post-merge CI is green, a separate exactly-once physical owner may run:

```text
python3 -m tools.v2_cognitive_ir_p2_termination_qual_wsl
```

That owner must use the current #2363 Full Access/local-binding preflight and the canonical WSL llama.cpp/GGUF/GPU runtime. The wrapper owns exactly one child transaction and one server lifetime. No retry, replay, reseed, fallback, LM Studio contact, S3 replay, or R4 execution is authorized.

A qualification PASS only permits a later owner to bind the already precommitted R4 identity. It is not evidence that P2 is better or worse than any other representation and does not authorize #2188 or #2132 changes.
