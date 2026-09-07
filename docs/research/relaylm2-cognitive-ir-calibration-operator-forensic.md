# RelayLM 2.0 — #2211 calibration operator-convention forensic

This surface defines a second, narrower **zero-provider forensic** over the output of the merged post-#2274 calibration forensic.

It asks only:

> When the model produced a wrong permutation or wrong answer, does that already-observed output exactly match one of a small set of predeclared alternative operator interpretations?

This is descriptive hypothesis matching. It does not prove why the model failed and it does not rerun the model.

## Input

The forensic consumes one `NON_CITABLE_S2_CALIBRATION_FORENSIC` JSON report produced by `tools/v2_cognitive_ir_calibration_forensic.py`.

Before analysis it fails closed unless the source report remains:

```text
claim_status             = NON_CITABLE_S2_CALIBRATION_FORENSIC
citable                  = false
provider_calls_added     = 0
causal_effect_claims     = false
S2 authorization         = false
architecture consequence = NONE
```

It also regenerates every frozen seed/difficulty case from `src/relaylm/v2_cognitive_ir_calibration.py` and requires the stored true rule, query, and expected answer to match the current deterministic generator exactly.

No provider, LM Studio, Native API, GPU, or network call is performed.

## Permutation relations

For the C1 and C2 reported rules, the observed permutation is compared with the frozen true permutation using only the following descriptive relations:

- `EXACT`;
- `IDENTITY_COLLAPSE_CANDIDATE` — the observed permutation is identity while the true permutation is not;
- `INVERSE_MAPPING_CANDIDATE` — the observed permutation equals the mathematical inverse of the true permutation;
- `SINGLE_POSITION_SWAP_CANDIDATE` — swapping exactly two positions of the true permutation reproduces the observed permutation;
- `CYCLIC_SHIFT_CANDIDATE` — rotating the permutation vector by a nonzero amount reproduces the observed permutation;
- `OTHER`.

These labels may overlap. For example an inverse permutation can also happen to be a single-position swap for a particular four-element permutation. They are matching relations, not mutually exclusive diagnoses.

`INVERSE_MAPPING_CANDIDATE` is the bounded proxy for a possible input/output mapping-convention reversal. It does **not** establish that such a reversal caused the model output.

## Answer hypotheses

For wrong C0 and C2 answers, the observed answer is tested against a small frozen family of deterministic alternatives:

- `TRUE_RULE` — the declared operator itself;
- `INVERSE_MAPPING_CONVENTION` — treat `permutation[i]` as the destination of input `i`, with offsets reindexed with that input;
- `INVERSE_PERM_KEEP_OUTPUT_OFFSETS` — inverse the permutation but keep offsets attached to output positions;
- `NEGATIVE_OFFSETS` — use the true permutation but subtract offsets modulo the frozen modulus;
- `ZERO_OFFSETS` — omit offsets;
- for C2 only, `REPORTED_RULE` — apply the rule that the same C2 response reported;
- for C2 only, `REPORTED_RULE_INVERSE_MAPPING` — apply that reported rule under the inverse-mapping convention.

The forensic separately checks alternative integer moduli from 2 through 16, excluding the frozen modulus 10, and records any exact matches as `wrong_modulus_matches`.

Multiple candidates may reproduce the same four-value answer. A match therefore narrows possible interpretations but does not identify a unique cognitive mechanism.

## C2 self-consistency

A particularly important descriptive distinction is:

```text
reported C2 rule is wrong
+ observed C2 answer == reported_rule(query)
```

This is reported as `reported_rule_self_consistent=true`.

It means only that the answer is mechanically consistent with the wrong rule emitted in that same response. Conversely, a wrong answer that is inconsistent even with the response's own reported rule shows an additional application mismatch. Neither case proves an internal reasoning path.

The report also counts `C2_exact_rule_but_wrong_answer`, which isolates cells where formation output is exact but application still fails.

## Output and interpretation boundary

Every report is forced to:

```text
claim_status                 = NON_CITABLE_S2_CALIBRATION_OPERATOR_FORENSIC
citable                      = false
provider_calls_added         = 0
descriptive matching only   = true
operator error cause proven = false
model capability ordering   = not proven
threshold retuning          = unauthorized
S2 authorization            = false
architecture consequence    = NONE
```

This forensic cannot:

- relax the v1 calibration thresholds;
- adopt D1 after the observed near miss;
- declare permutation intrinsically easier or harder than offset arithmetic;
- conclude that inverse mapping, wrap-around, wrong sign, or wrong modulus caused an error;
- unblock P0-P6 / S2 / S3;
- create architecture authority.

Its legitimate use is to decide whether a future separately preregistered calibration-v2 should change the **interface used to express an operator** or factor difficulty into separate independent axes.

## Invocation

Run against the historical forensic report read-only and write the new report elsewhere:

```bash
python -m tools.v2_cognitive_ir_calibration_operator_forensic \
  --forensic /tmp/<calibration-forensic-v1.json> \
  --output /tmp/<operator-forensic.json>
```

Omit `--output` to print canonical JSON to stdout. The output path is created exclusively and cannot overwrite an existing file.
