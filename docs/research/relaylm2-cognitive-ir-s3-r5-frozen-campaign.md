# RelayLM 2.0 Cognitive IR — S3-R5 frozen campaign

Owner: #2635  
Scientific preregistration: #2634  
Scientific owner: #2211

## Status

This document freezes the repository-facing realization of the next citable-candidate Cognitive IR campaign. It authorizes **no physical execution by itself**.

The only input imported from the NON_CITABLE calibration #2628 is:

```text
selected difficulty = K3_THREE_ACTIVE
```

No #2628 completion, learned representation, generated family, task output, correctness result, or calibration artifact is scientific R5 evidence.

Architecture consequence remains `NONE`.

## Identity

```text
schema = relaylm2-cognitive-ir-s3-prereg-v5
label = relaylm2-cognitive-ir-s3-semantic-invariance-v5-k3
preregistration SHA256 = 2f2dc45283af1ce2e4c921d483d16ea2908151ae7e55c50378ee92eecda15d65
difficulty = K3_THREE_ACTIVE
families per regime = 6
regime order = shared -> null -> mismatch -> shift
```

Fresh scientific seeds are derived by:

```text
int.from_bytes(SHA256(label + "|" + regime + "|seed|" + index)[0:4], "big") & 0x7fffffff
```

for `index = 0..5`.

```text
shared:
  745453345 1549669517 1235625757 193010981 1451955535 1138886096
null:
  2038910999 558665687 1363041899 1756158445 1783331388 2105217087
mismatch:
  804612455 196630042 742511018 1859640844 767626048 668367038
shift:
  1182307820 1332196726 131208839 814841957 1532205196 1600142459
```

The repository binding rejects any derivation mismatch, duplicate, or historical collision. There is no result-exposed reseed path.

## K3 family geometry

Every rule has:

```text
vector width = 4
permutation = identity
modulus = 10
active nonzero offsets = exactly 3
each active offset in {1,2,3}
source examples = 4
target steps = 4
canonical examples_visible = 0
no-wrap discipline = required
```

Regimes:

```text
F_SHARED:
  target rule == source rule

F_NULL:
  target is a deterministic distinct K3 rule, constant across target steps

F_MISMATCH:
  exactly one active source offset value is deterministically rotated to a
  different value in {1,2,3}; active support remains K3

F_SHIFT:
  steps 0-1 use source rule
  steps 2-3 use one deterministic distinct K3 post-shift rule
  shift_index = 2
```

Difficulty changes task geometry only. It does not change representation semantics or expose evaluator truth.

## Representation inheritance

R5 retains the S3-R4 treatment meanings unchanged:

```text
P0 RAW_HISTORY
P1 RETRIEVAL_ONLY
P2 ORDINARY_SUMMARY
P3 SEMANTIC_CACHE
P4 MEMORY_PLUS_STRUCTURE
P5 STRUCTURE_ONLY_RECONSTRUCTABLE
P6 GENERIC_EQUAL_INFORMATION
```

P2 uses the previously qualified bounded-summary builder from R4. P3/P4 use the inherited formation semantics. P4/P5/P6 share one P4 formation lineage. P6 is deterministic meaning-preserving neutralization of P4 and must retain canonical semantic equality with P4. Model-authored semantics are not Evidence or Grounding.

The four R4 surface perturbations, four semantic interventions, option-value/query-family-shift attack, and shift anchor are inherited without treatment changes.

Semantic-invariance gate:

```text
surface_effect <= 0.15
semantic_effect >= 0.20
semantic_effect - surface_effect >= 0.15
```

## Exact call ledger

Inherited per-family shape is unchanged. Only family count doubles from three to six.

```text
shared    6 * 41 = 246
null      6 * 41 = 246
mismatch  6 * 41 = 246
shift     6 * 43 = 258
--------------------------------
semantic calls      = 996
/input_tokens       = 1992
```

No semantic retry, replay, reseed, or fallback is legal. A partial campaign is incomplete/non-citable and is not resumed.

## Confirmatory analysis

The primary dedicated-type contrast is the six paired F_SHARED canonical P4 vs P6 outcomes. Record P4-only, P6-only, both-correct, and both-wrong cells. Use the exact one-sided binomial/sign test over discordant pairs for `P4 > P6`.

`IR TYPE EARNED WITHIN DECLARED SCOPE` is legal only if all preregistered #2634 gates hold: semantic invariance; paired exact `p <= 0.05`; P4 strictly exceeds P0/P1/P2/P3/P6 on F_SHARED canonical capability; P4 is not Pareto-dominated by equal-or-better-capability alternatives; pooled mismatch+shift P4 correctness is not below P6; and every semantic-equality/lineage check passes.

Generic compilation uses paired F_SHARED P6>P2 and P6>P1 exact tests. Absence of superiority is not equivalence. Generic-sufficiency or reduction verdicts additionally require their preregistered capability and Pareto conditions. Otherwise the scientific verdict remains `UNDERDETERMINED`.

F_NULL, F_MISMATCH, F_SHIFT, option value, shift anchors, and the observable Cognitive Work vector remain separate scope/negative-transfer attacks. No post-hoc scalar cost score is introduced.

## Runtime class

A later physical owner must freshly validate the current physical authority and retain:

```text
local llama.cpp
canonical Gemma-4 12B Q4_K_M GGUF
context = 8192
parallel = 1
context shift = disabled
reasoning_effort = none
temperature = 0
request seed = null
max output tokens = 1024
```

No LM Studio/model/quant/backend/prompt/schema/parser/treatment rescue is allowed.

The transaction remains four ordered shard lifetimes: one managed llama-server lifetime for each of `shared`, `null`, `mismatch`, and `shift`. The dedicated route is:

```bash
python3 -m tools.v2_cognitive_ir_s3_r5_llama_cpp_wsl
```

Physical execution requires a separate fresh owner under the current #2363 preflight authority. This repository-binding owner does not create or consume that execution opportunity.

## Downstream boundary

Even a positive R5 result has `architecture_consequence = NONE`. Any surviving durable semantic candidate still requires the #2188 correction/invalidation handoff before architecture consumption.
