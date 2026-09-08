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

This is a real interface defect for interpreting source exact-match failures. A wrong exact source hypothesis must therefore be separated from a semantically equivalent inverse-permutation convention before it is called an induction error.

It does **not**, however, explain the target endpoint floor, because target probes return transformed vectors rather than the latent factorization and all 16 target rules are uniquely determined at three examples.

## Offline raw-response classification

The forensic tool can inspect an already-existing `request-evidence.jsonl` without invoking a provider or changing the frozen scientific result:

```bash
python -m tools.v2_transfer_r2_source_learning_forensic raw \
  --request-evidence /path/to/request-evidence.jsonl \
  --expected-sha256 sha256:<producer-reported-digest>
```

The SHA-256 check binds the analysis to the immutable evidence named by its producer. The tool requires exactly one source-learning `model_exchange` for each of the 16 frozen families and ignores target exchanges for this classification.

Each structurally valid source response is evaluated under three semantics:

```text
canonical
  y[i] = x[permutation[i]] + offsets[i]

reverse permutation, output-indexed offsets
  permutation[input] = output
  offset remains indexed by output

reverse permutation, input-indexed offsets
  permutation[input] = output
  offset is indexed alongside the input entry
```

It reports one of:

```text
EXACT_CANONICAL
SEMANTICALLY_EXACT_REVERSE_PERMUTATION_OUTPUT_OFFSETS
SEMANTICALLY_EXACT_REVERSE_PERMUTATION_INPUT_OFFSETS
OTHER_VALID_HYPOTHESIS
```

The two reverse categories mean the response reproduces all four observed source transformations under a natural inverse convention that the frozen prompt failed to disambiguate. `OTHER_VALID_HYPOTHESIS` means the response was structurally valid but does not reproduce all four observations under any of those three declared interpretations.

This is post-hoc diagnosis only. It never changes #2355's exact-match score or category.

## Current forensic interpretation

Before raw-response classification, the deterministic evidence supports:

```text
GENERATOR_UNDERDETERMINED        = rejected for the four-example source packets
REPRESENTATION_CONVENTION_BURDEN = present
TARGET_TASK_FLOOR                = present at the three-example endpoint
MODEL_INDUCTION_FLOOR            = plausible; source near-miss classification remains evidence-dependent
PROTOCOL_OR_SCORING_DEFECT       = no parser/transport defect demonstrated; source semantic scoring contract is under-explained to the model
```

Accordingly, #2355 remains a valid complete transaction and retains its frozen `NO_SOURCE_LEARNING` category, but it does not provide a clean test of cross-task reuse. The learned object to be reused was never acquired under the frozen exact representation contract, while the target task itself was also below the tested model's demonstrated capability.

## Consequence

Do not proceed directly to R3 mismatch or R4 shift under this realization. Those stages presuppose an operational reusable Structure signal and would spend additional model calls without repairing the construct validity exposed here.

Any successor must be a **new preregistered claim**, not a retry of #2355. At minimum it must separate:

1. source acquisition / exact latent-factorization capability;
2. target transformation capability;
3. transfer/reuse effect conditional on those capabilities.

A mechanism upper-bound using evaluator-provided/oracle Structure may be scientifically useful only if explicitly named as a different experiment. It cannot be substituted for learned Structure inside the completed R2 claim.

## Raw-response boundary

If immutable #2355 request/response evidence is available, classify it with the offline procedure above and reconcile the resulting counts on #2376. If it is unavailable or its producer-reported digest does not match, stop rather than asking the model to reproduce the responses.
