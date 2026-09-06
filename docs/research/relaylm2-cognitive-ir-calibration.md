# RelayLM 2.0 — Cognitive IR S2 calibration

This document defines the bounded pre-S2 calibration owned by #2211.

The calibration exists because the first completed Gemma 4 12B S2 transaction failed in two
places at once: the learned reusable rule was wrong before target use, and the target application
was also wrong. The historical smoke remains `NON_CITABLE_S2_SMOKE`; this calibration does not
reinterpret that run and does not open S3.

The calibration answers a narrower question:

> Before comparing P0–P6, which generated rule family is neither a model floor nor a ceiling for
> the selected model/runtime?

It deliberately excludes representation arms. No Memory/Structure/generic representation result is
observed while choosing the later S2 difficulty.

## API boundary

Environment construction and live model authority remain provider-native concerns. For LM Studio,
the physical runner should use the native model-listing/runtime surfaces to establish the unique
loaded model instance, context and any environment-level reasoning setting.

Calibration inference requests use an OpenAI-compatible Chat Completions endpoint with native JSON
Schema structured output. The physical run must freshly verify that the selected provider supports
the declared `response_format.type=json_schema` contract before the first calibration request.

The repository-side calibration transport freezes:

```text
api               = openai-chat-completions-json-schema-v1
structured_output = true
temperature       = 0.0
max_tokens        = 128
seed              = null by default
timeout_seconds   = 300
```

No per-request reasoning field is added by the calibration client. If a provider requires an
explicit reasoning policy, that policy belongs to the freshly attested environment/runtime contract,
not an undocumented OpenAI-compatible extension.

## Independent seed rule

Calibration seeds are generated before any calibration result from:

```text
sha256("relaylm2-cognitive-ir-calibration-v1|seed|<index>")
```

using the first four digest bytes masked to a positive 31-bit integer. Six seeds are used. The
historical failed S2 seed `2211` is not one of them.

The calibration is non-adaptive: every declared seed, difficulty and probe is executed even if an
earlier cell already looks usable.

## Difficulty cells

The fixed matrix uses four generated rule/observation cells:

```text
D0_OFFSET_ONLY_RANDOM
  identity permutation
  four independent offsets
  four deterministic random examples

D1_PERMUTATION_ONLY_RANDOM
  non-identity permutation
  zero offsets
  four deterministic random examples

D2_FULL_DIAGNOSTIC
  non-identity permutation
  four independent offsets
  zero vector plus four deterministic scaled basis probes

D3_FULL_RANDOM
  non-identity permutation
  four independent offsets
  four deterministic random examples
```

Every generated source packet must identify exactly one legal rule inside its declared rule class.
Case generation fails closed if it cannot establish uniqueness.

`D2_FULL_DIAGNOSTIC` and `D3_FULL_RANDOM` have the same rule complexity but different observation
legibility. This is intentional: calibration needs to distinguish difficulty caused by the rule from
difficulty caused by the examples used to expose it.

## Three probes

Every seed × difficulty cell runs exactly three independent structured requests.

### C0 — APPLICATION_ONLY

The exact rule and a fresh query are supplied. The model returns only:

```json
{"answer": [0, 0, 0, 0]}
```

The actual values are determined by the generated case.

This is an oracle mechanism control. It measures whether explicit rule application is viable; it is
not a representation arm and is never exposed to P0–P6 comparison.

### C1 — FORMATION_ONLY

Only the public modulus and source examples are supplied. The model must return:

```json
{
  "permutation": [0, 1, 2, 3],
  "offsets": [0, 0, 0, 0],
  "modulus": 10
}
```

The schema fixes shape/range only. It does not expose evaluator-known permutation or offset values.
The probe is correct only when the returned rule exactly equals the generated rule.

### C2 — END_TO_END

The public modulus, source examples and a query are supplied in one request. The model returns both
its inferred rule and answer:

```json
{
  "permutation": [0, 1, 2, 3],
  "offsets": [0, 0, 0, 0],
  "modulus": 10,
  "answer": [0, 0, 0, 0]
}
```

End-to-end success requires both the exact rule and the exact answer. Returning the right answer with
a wrong rule does not count as joint success.

## Bounded work

The matrix is:

```text
6 seeds
× 4 difficulties
× 3 probes
= 72 provider calls
```

There is no early stopping, result-dependent seed replacement, prompt repair, parser rescue or
retry-until-success inside this matrix.

All three probes use JSON Schema structured output, so formatting skill is intentionally removed as
a calibration variable. Parsing still fails closed on unexpected values after provider-level schema
constraining.

## Admission rule

Each difficulty is summarized across its six seeds.

A difficulty is admitted only when all three conditions hold:

```text
C0 application rate          >= 0.90
C1 exact formation rate       0.40 .. 0.90
C2 joint end-to-end rate      0.20 .. 0.80
```

With six seeds, the discrete consequences are intentionally strict: C0 must succeed on all six
cases, while C1 and C2 must avoid both obvious floor and ceiling.

If more than one difficulty is admitted, the last difficulty in the predeclared order is selected.
If none is admitted, `selected_difficulty = null` and no new S2 is authorized. The matrix must not be
retuned after observing results simply to manufacture an admissible cell.

An all-correct matrix is a calibration ceiling and therefore selects nothing.

## Claim boundary

Every run is:

```text
claim_status = NON_CITABLE_S2_CALIBRATION
citable      = false
```

Calibration may select a candidate difficulty for a new, separate S2 preregistration transaction.
It does not:

- choose a winning P0–P6 representation;
- prove Memory, Structure or Crystallization efficacy;
- establish Model Legibility;
- support an architecture change;
- open S3;
- rewrite the historical seed-2211 smoke.

A later S2 must use a newly frozen generator/seed rule based on the selected difficulty without
reusing the calibration cases as empirical comparison evidence.

## Physical-run discipline

Before physical execution, acquire fresh repository and provider authority. For LM Studio, the
intended split is:

```text
native API
  -> loaded-instance/runtime/context authority

OpenAI-compatible /v1/chat/completions
  -> actual structured calibration requests
```

The physical runner must persist the exact model/runtime/transport identity, truthful provider
attempt/completion counts, token totals, per-difficulty summaries and selected difficulty. A failed
provider request counts as attempted work and terminates the bounded calibration unless a separate
future contract explicitly declares otherwise.

Physical execution is not performed by the repository-side implementation transaction.

## Next gate

```text
calibration selects one difficulty
  -> separate fresh S2 preregistration
  -> fresh P0–P6 smoke on new non-calibration cases

calibration selects none
  -> S2 remains blocked
  -> redesign must be justified before any new physical comparison
```

S3 remains blocked until a later completed S2 is mechanically discriminating under its own frozen
contract.
