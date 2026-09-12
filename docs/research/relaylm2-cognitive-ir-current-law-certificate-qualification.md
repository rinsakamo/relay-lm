# RelayLM 2.0 S3-R6D G1 — current-law certificate usability qualification

Owner chain: #2211 -> #2711 -> #2712 -> #2713.

## Purpose

G1 is a NON_CITABLE protocol qualification. It follows the terminal
`NO_OBSERVABLE_ATTACK_TARGET_RANGE` result from #2703.

The old D2 prompt asked the model to infer a current target law from visible
input/output examples and then apply that law. In the current task class the
law is already mechanically identifiable from one target observation:

```text
identity permutation
additive coordinate offsets
modulus 10
no wrap

offset[i] = (output[i] - input[i]) mod 10
```

G1 removes example-decoding/rule-induction from the model-facing task. It asks
only whether the frozen model can apply a deterministic current-law certificate
to the current target query.

This qualification is not representation efficacy evidence.

## Frozen identity

```text
schema = relaylm2-cognitive-ir-s3-r6d-g1-certificate-usability-prereg-v1
label  = relaylm2-cognitive-ir-s3-r6d-g1-current-law-certificate-usability-v1
claim  = NON_CITABLE_CURRENT_LAW_CERTIFICATE_USABILITY_QUALIFICATION
regimes = null -> mismatch -> shift-post
difficulty = K3_THREE_ACTIVE
semantic calls = 18
/input_tokens = 36
citable = false
architecture_consequence = NONE
```

The exact 18 seeds are owned by #2712 and mechanically validated by the
repository implementation.

## Current-law certificate

For the attack probe step, use target example index 0 as the sole provenance
root. Let the example be `(x, y)`. Derive:

```text
permutation = [0,1,2,3]
offsets[i] = (y[i] - x[i]) mod 10
modulus = 10
```

The implementation must prove that this reconstructed rule equals the
generated current target rule for every G1 family.

The certificate is a deterministic projection of visible target evidence. It
is not evaluator-hidden truth, is not model-authored, and does not create new
Evidence/Grounding.

## Model-facing payload

`A_CERTIFICATE_ONLY` receives only:

```text
formal instruction
current_law_certificate:
  permutation
  offsets
  modulus
current target query
```

It receives no source history, source examples, raw target example pair,
P0-P6 representation, learned formation output, old D2 completion, D1 result,
or hidden evaluator rule object.

The response is exactly one JSON integer array of length 4.

## Qualification gate

Run one fixed panel:

```text
null       6
mismatch   6
shift-post 6
```

Qualification requires `>=5/6` correct in every regime, 18/18 clean semantic
calls, stable parser/verifier, valid runtime/material binding, and 18/18
mechanical certificate reconstruction.

There is no visibility ladder, early-stop alternative, retry, replay, reseed,
fallback, or post-result rescue.

Allowed terminal results:

```text
CURRENT_LAW_CERTIFICATE_USABILITY_QUALIFIED
CURRENT_LAW_CERTIFICATE_USABILITY_FAILED
QUALIFICATION_INCOMPLETE
PRE_WRAPPER_MECHANICAL_BLOCKED
```

Every result remains non-citable and has `architecture_consequence=NONE`.

## Runtime / operator surface

The frozen runtime class remains local llama.cpp + canonical Gemma-4 12B
Q4_K_M, context 8192, parallel 1, context shift disabled,
`reasoning_effort=none`, temperature 0, request seed null, max output 1024.

LocalCodex must use the shared physical runner target:

```text
v2:current-law-certificate-usability
```

The shared runner owns persistent Python, queue/lease/wait, and final fresh
preflight. The G1 target wrapper owns qualification/runtime semantics.

No physical execution is authorized by #2713 itself.

## Downstream

A positive G1 result only qualifies the certificate interface. It does not
authorize a citable negative-transfer campaign. A later G2 preregistration,
with fresh disjoint scientific seeds, may compare certificate-only against
certificate + P0-P6 stale/source representations.

A failed G1 returns to #2711/#2211 for task/application-surface redesign.
Do not add examples, weaken K3 post hoc, or expose evaluator answers.

Refs #2211 #2711 #2712 #2713 #2703 #2188.
