# RelayLM 2.0 — #2211 R5 precursor: F_SHARED canonical target-range calibration

Status: repository binding for #2600 via #2601. This document defines a
**non-citable protocol calibration only**. It does not establish representation
efficacy, Memory/Structure typing, Crystallization efficacy, or architecture
authority.

## Why this gate exists

The completed S3-R4 campaign (#2596) and deterministic analysis (#2598) passed
the semantic-invariance discriminator but left the positive canonical workload
near floor:

- P3/P4: 1/12 pooled, 1/3 on `F_SHARED`;
- P0/P1/P2/P5/P6: 0/12 pooled;
- surface effect: 0.041666666666666664;
- semantic intervention effect: 0.25;
- semantic-minus-surface gap: 0.20833333333333334.

At the same time the option-value panel was not at floor. The smallest next
gate is therefore to calibrate **only the positive `F_SHARED` canonical task**
into a measurable range before any new citable R5 campaign. `F_NULL`,
`F_MISMATCH`, and `F_SHIFT` remain attack/negative-transfer strata and do not
select task difficulty.

## Frozen identity

```text
label = relaylm2-cognitive-ir-shared-floor-calibration-v1
claim = NON_CITABLE_SHARED_TARGET_RANGE_CALIBRATION
citable = false
architecture_consequence = NONE

seeds =
  824131651
  727517075
  1455229498
  691488953
  1485742517
  411743139
```

The seeds are SHA-256 derived from the label and index and must remain disjoint
from prior calibration/S2/S3/P2 evidence.

## One-knob difficulty ladder

All candidates keep:

```text
width = 4
modulus = 10
source examples = 4
target examples visible = 0
permutation = identity
source rule = target rule
no wrap
```

Only the number of non-zero source offsets changes:

```text
K4_CURRENT_CLASS   = 4 active coordinates
K3_THREE_ACTIVE    = 3 active coordinates
K2_TWO_ACTIVE      = 2 active coordinates
K1_ONE_ACTIVE      = 1 active coordinate
```

Every active offset is in `{1,2,3}`. There is no `K0`.

The coordinate ranking and each coordinate's non-zero value are fixed from
`(label, seed, coordinate)` hashes. Moving down the ladder only changes active
coordinates to zero; it does not change public source/query inputs, prompt
semantics, vector width, modulus, or representation contracts.

## Outcome-blind semantic call plan

Per seed, exactly nine calls are legal:

```text
1  A0_EXPLICIT_APPLICATION
2  FORM_P2
3  FORM_P3
4  FORM_P4
5  TARGET_P0
6  TARGET_P1
7  TARGET_P2
8  TARGET_P3
9  TARGET_P6
```

`TARGET_P4` and `TARGET_P5` are deliberately absent. Calibration cannot select
a difficulty by observing the typed arm's target outcome.

Also absent:

- surface perturbation panels;
- semantic intervention panels;
- option-value panels;
- null/mismatch/shift panels.

The one P4 formation is needed to instantiate the already-frozen
P4/P5/P6 lineage and derive the generic equal-information P6 control. P4
formation correctness is a diagnostic; P4 target behavior is not observed.

Accounting is frozen before physical execution:

```text
semantic calls / seed = 9
seeds / candidate = 6
semantic calls / fully evaluated candidate = 54
maximum semantic calls = 216

exact llama.cpp /input_tokens requests / semantic call = 2
/input_tokens requests / candidate = 108
maximum /input_tokens requests = 432
```

Planned hardest-first early stop is not a retry.

## Representation invariants

The calibration reuses the R4 representation path:

- P0 raw history;
- P1 retrieval only;
- qualified bounded P2 ordinary summary;
- P3 semantic cache;
- P4 Memory+Structure formation;
- P5 deterministic structure-only derivative;
- P6 deterministic generic equal-information derivative.

P4/P5/P6 share one exact P4 formation completion. P4/P6 canonical semantic
digest equality is mandatory. The R4 qualified P2 hard envelope remains
unchanged.

The A0 application diagnostic may contain evaluator-known exact rule semantics,
but only in the A0 prompt. Those semantics must not enter any P0-P6
representation or target message.

## Admission and selection

A completed candidate is admitted only when all gates hold:

```text
A0 exact application = 6/6
P4 formation exact-rule recovery >= 3/6
P2 hard admission = 6/6
0.20 <= neutral_control_mean <= 0.80
at least 2 neutral arms are individually in [1/6, 5/6]
```

The neutral selector arms are exactly:

```text
P0 P1 P2 P3 P6
```

and

```text
neutral_control_mean =
  total correct across 5 neutral arms x 6 seeds / 30
```

Evaluate in fixed order:

```text
K4 -> K3 -> K2 -> K1
```

Select the first/hardest admitted candidate and do not execute easier
candidates. If all four complete without admission, return
`NO_SHARED_TARGET_RANGE_FOUND`.

Allowed terminal classifications are:

```text
SHARED_TARGET_RANGE_QUALIFIED
NO_SHARED_TARGET_RANGE_FOUND
CALIBRATION_INCOMPLETE
```

All remain non-citable with architecture consequence `NONE`.

## Physical boundary

#2601 binds repository code and CI only. It does not run the model.

A later dedicated physical owner must reacquire fresh repository, llama.cpp,
GGUF, tokenizer/chat-template, hardware, lifecycle-lock, listener, and artifact
authority under the current physical-execution procedure before invoking:

```text
python3 -m tools.v2_cognitive_ir_shared_floor_calibration_llama_cpp_wsl
```

No semantic retry, replay, reseed, fallback, LM Studio substitution, treatment
repair, or second invocation is authorized by this document.

If calibration qualifies one difficulty, a later R5 preregistration must use
fresh disjoint scientific seeds and preserve the S3 representation semantics,
surface/semantic interventions and thresholds, option-value attack,
null/mismatch/shift pressure, observable Cognitive Work accounting, Grand Null,
and `architecture_consequence = NONE`.

Refs: #2211 #2600 #2601 #2598 #2596 #2577 #2363 #2188 #2132.
