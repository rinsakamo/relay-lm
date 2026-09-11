# RelayLM 2.0 — P2 boundedness qualification v2

Authority: #2211 scientific owner, #2571 protocol-repair freeze, #2572 repository implementation. Physical procedure remains #2363.

## Why this second gate exists

The first bounded P2 qualification (#2538) showed that the 1024-token ceiling was no longer the active failure. The model returned `finish_reason=stop`, but one completion still exceeded the hard visible envelope at 870 Unicode characters / 161 whitespace-delimited words. That result remains immutable and non-citable.

This second gate tests only whether ordinary plain-text P2 can satisfy the **same hard 120-word / 800-character admission** when the prompt aims materially below the hard edge. It does not test representation efficacy.

## Frozen target margin

Historical P2 builders remain unchanged. The new scoped builder preserves the same source packet and ordinary-summary semantics and adds exactly:

```text
Return one plain-text recap paragraph only.
Keep it deliberately short: aim for 60 to 80 words and no more than 550 Unicode characters.
Preserve supported conditions, recurring patterns, exceptions, and outcomes.
You may infer/generalize regularities when supported by the observations.
Do not include a heading, bullet list, special schema, or step-by-step derivation.
Do not fill the available output budget; stop after the recap paragraph.
```

The target margin is not the mechanical verdict boundary. A response above 80 words or 550 characters still passes if it remains within the unchanged hard envelope:

```text
finish_reason == stop
non-empty visible content
words <= 120
Unicode characters <= 800
reasoning absent/empty where exposed
```

No grammar, JSON schema, deterministic truncation, post-hoc repair, retry, or larger output ceiling is introduced. `max_output_tokens` remains 1024.

## Fresh non-citable qualification

Label:

```text
relaylm2-cognitive-ir-p2-boundedness-qual-v2
```

Seeds are deterministically derived from SHA-256(`<label>|<regime>|seed|<index>`) and frozen by #2571. They are disjoint from the consumed #2538 qualification, S3-v1/R2/R3, S2/calibration evidence, and the precommitted but inactive S3-R4 seed set.

Execution order is `shared -> null -> mismatch -> shift`, three families per regime, P2 formation only: 12 semantic calls, 24 exact `/input_tokens` requests, one managed llama-server lifetime. The first mechanical failure stops the qualification; no retry/replay/reseed/skip-forward is allowed.

Only mechanical metadata is retained: call identity, finish reason, input/output token counts, visible character/word/byte counts, content digest, reasoning-field status, admission/failure reason, runtime/material identity, exact request counts, cleanup and log hashes. No correctness score, latent-rule decoding, cross-arm comparison or efficacy metric is produced.

The terminal result is always non-citable and has `architecture_consequence=NONE`.

## R4 boundary

The S3-R4 identity/seeds precommitted before #2538 remain unspent and unchanged. This qualification does not activate or execute R4. A PASS only permits #2211 to create a later repository owner that explicitly binds the complete R4 campaign to this repaired P2 contract.

## Physical boundary

After #2572 merges and post-merge v2 CI is green, a separate exactly-once physical owner may run:

```text
python3 -m tools.v2_cognitive_ir_p2_boundedness_qual_v2_wsl
```

That owner must use the current #2363 Full Access/local-binding preflight and canonical WSL llama.cpp/GGUF/GPU runtime. No LM Studio fallback, S3 replay, R4 execution, #2188 routing or #2132 mutation is authorized by this gate.
