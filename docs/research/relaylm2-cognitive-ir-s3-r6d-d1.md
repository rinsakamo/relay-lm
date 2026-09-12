# RelayLM 2.0 Cognitive IR — S3-R6D D1 shared discriminator

Owner: #2670  
Preregistration: #2666  
Scientific owner: #2211

## Purpose

D1 is the prospective citable shared-regime discriminator after R5 remained
`UNDERDETERMINED`. It asks whether explicit `P4_MEMORY_PLUS_STRUCTURE`
outperforms both the independently formed `P3_SEMANTIC_CACHE` Grand Null and
the same-payload neutralized `P6_GENERIC_EQUAL_INFORMATION` control.

No R5 completions, learned payloads, or target outcomes are reused as D1
evidence.

## Frozen identity

```text
schema = relaylm2-cognitive-ir-s3-r6d-d1-prereg-v1
label = relaylm2-cognitive-ir-s3-r6d-shared-discriminator-v1
claim = CITABLE_D1_WITHIN_DECLARED_SCOPE
regime = shared only
difficulty = K3_THREE_ACTIVE
families = 24
semantic calls/family = 41
semantic calls total = 984
/input_tokens total = 1968
architecture_consequence = NONE
```

The frozen preregistration identity digest is:

```text
b3709c57d7c421060d3776932442ef1e06ea808be1abfb3833d7992c5cf5f1b4
```

Exact seed derivation, collision fences, and the 24 seed values live in
`relaylm.v2_cognitive_ir_s3_r6d_d1`.

## Representation and formation invariants

D1 inherits the R5 shared-family contract:

- vector width 4, modulus 10, identity permutation;
- exactly three active offsets;
- four source examples and four target steps;
- zero target examples visible on the canonical probe;
- the qualified bounded P2 builder;
- independent P3 formation from the same source packet;
- one P4 formation completion shared by P4/P5/P6;
- deterministic meaning-preserving P6 neutralization;
- P4/P6 semantic equality on every family;
- no evaluator target truth in learned representations.

The R5 surface and semantic intervention definitions and thresholds are
re-executed prospectively over all 24 fresh families.

## Primary contrasts

The repository analysis surface computes exact paired one-sided tests:

```text
C1: P4 > P3
C2: P4 > P6
```

The dedicated type gate is a conjunction. `IR TYPE EARNED WITHIN DECLARED
SCOPE` is possible only when both exact directional tests pass at `p <= 0.05`,
semantic invariance passes, P4 strictly exceeds the preregistered control arms
on canonical F_SHARED capability, P4 is not Pareto-dominated at equal-or-better
capability, and all lineage/provenance invariants hold.

Non-significance is never interpreted as equivalence.

The same analysis surface also computes:

```text
P3 > P2
P3 > P1
```

for the prospective `SEMANTIC CACHE USEFUL` Grand Null.

## NATURAL_COST scope

`canonical_natural_cost_vectors` reports counterfactual per-arm
formation-plus-canonical Cognitive Work without scalarization. P4/P5/P6 each
carry the shared P4 formation cost in their per-arm capability cost vector,
while the physical campaign still executes that formation only once per
family.

Option-value correctness is reported separately for all P0-P6 arms.

## Physical route

Repository binding exposes:

```bash
python3 -m tools.v2_cognitive_ir_s3_r6d_d1_llama_cpp_wsl
```

The inner transaction activates D1 before importing the generic S3 campaign
transaction, reducing it to one `shared` shard. Therefore a successful
physical campaign owns exactly one llama-server lifetime and executes exactly
984 semantic calls. The listener-safe lifecycle wrapper remains in force.

This repository-binding owner performs no provider/model/GPU/server execution
and does not authorize physical execution. A separate exactly-once physical
owner is required after fresh authority.

## Failure discipline

There is no retry, replay, reseed, fallback, optional extension beyond 24
families, or continuation from a partial campaign. Any partial campaign is
incomplete and non-citable. No architecture mutation follows directly from
D1; `architecture_consequence` remains `NONE`.
