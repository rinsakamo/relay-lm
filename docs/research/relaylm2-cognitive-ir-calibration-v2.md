# RelayLM 2.0 — #2211 factorized pre-S2 calibration v2

This document preregisters a replacement calibration design after the completed v1 calibration selected no difficulty and its two zero-provider forensics exposed non-monotone and mixed failure geometry.

This is a **new calibration on fresh deterministic cases**. It does not retune the completed v1 matrix, reinterpret its result, authorize S2, or create architecture authority.

```text
claim_status = NON_CITABLE_S2_CALIBRATION_V2
citable      = false
```

## Why a v2 calibration is justified

The completed v1 matrix observed, descriptively:

- `D0_OFFSET_ONLY_RANDOM`: application `3/6`, formation `0/6`, end-to-end `0/6`;
- `D1_PERMUTATION_ONLY_RANDOM`: application `5/6`, formation `2/6`, end-to-end `3/6`;
- `D2_FULL_DIAGNOSTIC`: `0/6` on all three probes, with a repeated identity-permutation output pattern despite exact offsets in formation;
- `D3_FULL_RANDOM`: `0/6` on all three probes with mixed permutation/offset error.

The post-#2274 forensic showed that the old one-dimensional difficulty ordering was not monotone for application. The post-#2275 operator-convention forensic found a few exact bounded alternative-operator matches but did not explain most failures. In particular, the D2 identity-collapse pattern remained systematic and the D0 wrong C0 answers were not reproduced by the bounded operator candidates.

Those observations justify **factorizing the next calibration axes**. They do not prove a model-internal cause.

## Anti-overfit boundary

Calibration v2 changes the generated case family but preserves the original admission thresholds. It uses a new seed label and cannot reuse v1 calibration cells as empirical evidence.

Forbidden after v2 results are observed:

- replacing failed seeds;
- weakening application/formation/end-to-end thresholds;
- changing regime priority;
- changing operator wording;
- adding retries or reasoning rescue;
- selecting a regime that failed admission;
- using v1 or v2 calibration cases as P0–P6 comparison evidence.

## Fresh seed rule

Six seeds are frozen from:

```text
sha256("relaylm2-cognitive-ir-calibration-v2-factorized|seed|<index>")
```

The seed set is disjoint from calibration v1 and excludes historical S2 seed `2211`.

## Fixed 72-call matrix

The matrix remains exactly:

```text
6 fresh seeds
× 4 factorized regimes
× 3 probes
= 72 provider calls
```

The four regimes are:

```text
V2_SINGLE_SWAP_ZERO_OFFSET
  exactly one transposition
  zero offsets
  wrap arithmetic absent

V2_IDENTITY_OFFSET_NO_WRAP
  identity permutation
  four small nonzero offsets in {1,2,3}
  every example and query is generated so addition does not wrap modulo 10

V2_IDENTITY_OFFSET_WRAP
  identity permutation
  four small nonzero offsets in {1,2,3}
  query has at least two coordinates that wrap modulo 10

V2_SINGLE_SWAP_OFFSET_NO_WRAP
  exactly one transposition
  four small nonzero offsets in {1,2,3}
  every example and query is generated so addition does not wrap modulo 10
```

This is not declared as a single easy-to-hard scale. It separates reordering, offset arithmetic, wrap load, and their modest composition.

## Full-class public identifiability

Every C1/C2 public example packet must identify exactly one legal `VectorRule` across the **full model-visible rule class**:

```text
all 4! permutations
× offsets inferred modulo 10
```

Generation fails closed unless exactly one rule fits every public example. This is stronger than relying on a hidden difficulty-specific prior.

The target model is not required to know an unspoken restriction such as “identity permutation only” or “offsets are zero” in order for the packet to be identifiable.

## Operator contract v2

All three probes share one frozen task-level operator statement:

```text
for every output position i:
output[i] = (input[permutation[i]] + offsets[i]) mod modulus

permutation=[p0,p1,p2,p3]
means outputs 0..3 read inputs p0,p1,p2,p3 respectively.
```

The prompt also says not to assume identity mapping and to check the rule against all supplied examples.

This is a protocol-legibility repair motivated by the bounded forensic, not a semantic hint about any case. C1/C2 still receive no evaluator-known permutation or offset values.

A later S2 preregistration may use this operator contract only if it applies the same public task semantics fairly across all P0–P6 arms.

## Probes

The probe decomposition remains unchanged.

### C0 — application only

Exact rule + query are supplied. Return only the answer.

### C1 — formation only

Public modulus + examples are supplied. Return the exact permutation, offsets, and modulus.

### C2 — end to end

Public modulus + examples + query are supplied. Return the inferred rule and answer. Joint success requires both exact rule and exact answer.

All output remains strict JSON Schema structured output.

## Admission thresholds — unchanged from v1

Each regime uses six seeds and is admitted only when:

```text
C0 application rate          >= 0.90
C1 exact formation rate       0.40 .. 0.90
C2 joint end-to-end rate      0.20 .. 0.80
```

Therefore, with six seeds:

```text
C0 = 6/6
C1 = 3..5/6
C2 = 2..4/6
```

No threshold is relaxed because D1 v1 missed by one case.

## Selection is priority, not claimed difficulty order

If multiple regimes are admitted, selection uses this frozen priority:

```text
1. V2_SINGLE_SWAP_OFFSET_NO_WRAP
2. V2_SINGLE_SWAP_ZERO_OFFSET
3. V2_IDENTITY_OFFSET_NO_WRAP
4. V2_IDENTITY_OFFSET_WRAP
```

Rationale:

1. prefer a modest composition of reusable reordering + arithmetic when viable without wrap nuisance;
2. otherwise preserve nontrivial reordering;
3. otherwise preserve nontrivial offset transformation without wrap;
4. use wrap-specific offset transformation only if it independently lands in the admission band.

This priority is a task-coverage preference, **not evidence that the list is ordered by cognitive difficulty**.

If no regime is admitted, `selected_regime=null` and S2 remains blocked.

## Transport and reasoning boundary

Calibration v2 is intended to inherit the already-qualified transport only in a later physical-host transaction:

```text
OpenAI-compatible /v1/chat/completions
strict response_format JSON Schema
temperature = 0
max_tokens = 128
timeout = 300
request-level reasoning override = none
```

The loaded LM Studio instance must again be fail-closed verified as effective reasoning-off on every completed provider call (`reasoning_tokens=0`, no reasoning payload).

This preregistration transaction performs **no model call** and does not yet create or run the physical v2 host.

## Scientific boundary

Calibration v2 may only select a task regime for a later fresh S2 preregistration. It cannot:

- choose a representation arm;
- prove Memory/Structure/Crystallization efficacy;
- establish that an operator convention caused the old failures;
- establish a model capability ordering;
- authorize S3;
- mutate #2132 architecture authority.

```text
P0-P6                    = NOT RUN
S2                       = BLOCKED until a separate v2 physical calibration completes and selects
S3                       = BLOCKED
architecture consequence = NONE
```
