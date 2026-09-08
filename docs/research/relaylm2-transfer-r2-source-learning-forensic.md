# RelayLM 2.0 — R2 source-learning floor forensic

Owner: #2376  
Parent experiment: #2157  
Frozen physical result: #2355  
Frozen preregistration: #2341

## Question

The completed R2 transaction classified as `NO_SOURCE_LEARNING`. This forensic asks whether that outcome can be explained by an underdetermined generator, by an ambiguous model-facing representation contract, or by failure of the model to perform the underlying induction task.

This document does not reclassify #2355 and does not authorize another physical run.

## Frozen transformation

The generator uses width-four vectors modulo 10. The canonical evaluator convention is:

```text
y[i] = (x[permutation[i]] + offsets[i]) mod modulus
```

A source packet contains four exact input/output examples. The source-learning response is a strict JSON object containing `permutation`, `offsets`, and `modulus`.

## Deterministic identifiability proof

`tools/v2_transfer_r2_source_learning_forensic.py` reconstructs the exact 16-family seed set from the frozen preregistration and enumerates all 24 width-four permutations. Once a candidate permutation is chosen, the first visible example uniquely determines its four offsets; later examples accept or reject that candidate.

For the frozen 16 source packets, the numbers of formally consistent rules after 1/2/3/4 examples are:

```text
family 00 shared  24 4 1 1
family 01 null    24 1 1 1
family 02 shared  24 1 1 1
family 03 null    24 1 1 1
family 04 shared  24 1 1 1
family 05 null    24 1 1 1
family 06 shared  24 1 1 1
family 07 null    24 2 1 1
family 08 shared  24 2 1 1
family 09 null    24 1 1 1
family 10 shared  24 1 1 1
family 11 null    24 1 1 1
family 12 shared  24 2 1 1
family 13 null    24 2 1 1
family 14 shared  24 6 2 1
family 15 null    24 2 1 1
```

Therefore all 16 source rules are uniquely identifiable from the four examples actually shown. Information-theoretic underdetermination does not explain source correctness `0/16`.

## Target-side identifiability

The R2 target curve exposes 0, 1, 2, or 3 examples. Before any example there are `4! * 10^4 = 240000` possible rules. One example leaves all 24 permutations possible because offsets can absorb the observation. For the frozen families the candidate counts at 0/1/2/3 visible examples are:

```text
family 00 shared  240000 24 2 1
family 01 null    240000 24 1 1
family 02 shared  240000 24 1 1
family 03 null    240000 24 2 1
family 04 shared  240000 24 1 1
family 05 null    240000 24 2 1
family 06 shared  240000 24 1 1
family 07 null    240000 24 2 1
family 08 shared  240000 24 2 1
family 09 null    240000 24 2 1
family 10 shared  240000 24 1 1
family 11 null    240000 24 1 1
family 12 shared  240000 24 2 1
family 13 null    240000 24 1 1
family 14 shared  240000 24 2 1
family 15 null    240000 24 1 1
```

Thus every target rule is uniquely identifiable by the three-example endpoint. The observed all-false target curves cannot be explained solely by ambiguity in the source Structure encoding.

The 0-example and 1-example points are intentionally information-poor and must not be read as model failures. At two examples, some frozen families are already unique and some retain two candidates. At three examples, all are unique.

## Representation-contract finding

The frozen source-learning system prompt names the required fields and their lengths, but it does **not** state the evaluator equation or the direction of the permutation mapping.

Both of these conventions are natural descriptions of a permutation:

```text
output index -> source input index
input index  -> destination output index
```

They are inverses for a general permutation. The JSON schema constrains array shape/range but cannot communicate which convention is intended. Exact equality against the generator's canonical `permutation` therefore imposes a representation convention that was not explicitly exposed to the model.

This is a real interface defect for interpreting source exact-match failures. Without the immutable raw responses, a wrong source hypothesis cannot be distinguished post hoc between an induction error and a conventionally inverted/otherwise near-equivalent representation.

It does **not**, however, explain the target endpoint floor, because target probes return transformed vectors rather than the latent factorization and all 16 target rules are uniquely determined at three examples.

## Current forensic interpretation

The available evidence supports a combined diagnosis:

```text
GENERATOR_UNDERDETERMINED       = rejected for the four-example source packets
REPRESENTATION_CONVENTION_BURDEN = present
TARGET_TASK_FLOOR              = present at the three-example endpoint
MODEL_INDUCTION_FLOOR          = plausible, but raw source responses are needed to distinguish source near-misses
PROTOCOL_OR_SCORING_DEFECT      = no parser/transport defect demonstrated; source semantic scoring contract is under-explained to the model
```

Accordingly, #2355 remains a valid complete transaction and retains its frozen `NO_SOURCE_LEARNING` category, but it does not provide a clean test of cross-task reuse. The learned object to be reused was never acquired, while the target task itself was also below the tested model's demonstrated capability.

## Consequence

Do not proceed directly to R3 mismatch or R4 shift under this realization. Those stages presuppose an operational reusable Structure signal and would spend additional model calls without repairing the construct validity exposed here.

Any successor must be a **new preregistered claim**, not a retry of #2355. At minimum it must separate:

1. source acquisition / exact latent-factorization capability;
2. target transformation capability;
3. transfer/reuse effect conditional on those capabilities.

A mechanism upper-bound using evaluator-provided/oracle Structure may be scientifically useful only if explicitly named as a different experiment. It cannot be substituted for learned Structure inside the completed R2 claim.

## Raw-response boundary

If immutable #2355 request/response evidence becomes available, it may be classified without any new provider call to test inverse-permutation, offset, or other near-miss hypotheses. If those raw responses are not preserved, this forensic stops at the deterministic conclusions above rather than asking the model to reproduce them.
