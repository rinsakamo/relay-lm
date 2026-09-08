# RelayLM 2.0 Cognitive Work R3 uniform-task preregistration

Owner: #2312  
Parent experiment: #2187

## Purpose

This preregistration freezes the R3 uniform-task null after the completed heterogeneous R2 result #2308 (`HEURISTIC_SUFFICIENT`). It asks whether the already-tested adaptive allocator gains material accuracy over the already-tested cheap heuristic when the workload no longer requires routing across heterogeneous marginal-work regimes.

The R2 result is historical evidence and is not rewritten here. R3 does not tune A2 after observing R2.

## Frozen policy semantics

R3 imports the accepted R2 structured-output policy and message functions directly:

- A0: fixed `THINK`;
- A1: deterministic `RETRIEVE` whenever retrieval is publicly available;
- A2: the same model allocator and allocator prompt used in R2;
- A3: the same evaluator-only oracle;
- the same answer/revision/allocator messages;
- the same strict structured parsers;
- the same paired exact-test and bootstrap implementations.

No allocator prompt, A1 rule, operation description, resource accounting rule, threshold, or statistic is redesigned for R3.

## Fresh uniform workload

The only task regime is the pre-existing R2 `RETRIEVAL_BENEFICIAL` generator lineage. The suite contains exactly 16 fresh unseen tasks derived from a new commit-bound seed domain:

```text
relaylm2-2187-r3-uniform-retrieval-v1
```

The concrete root seed is intentionally not committed before merge. It is derived from the final squash-merge commit and is therefore immutable only after merged authority exists.

Every R3 task has:

```text
retrieval_available = true
observation_available = false
legal operations = ZERO / THINK / RETRIEVE
```

The hidden regime label, expected answer, retrieval packet, oracle choice, and post-hoc correctness remain evaluator-side. The retrieval packet enters model-facing context only in the purchased `RETRIEVE` bank call.

## Exact physical call plan

For each of 16 tasks:

```text
BASE
A2_ALLOCATE
BANK:THINK
BANK:RETRIEVE
```

Therefore the frozen physical plan is:

```text
16 BASE
16 A2_ALLOCATE
16 BANK:THINK
16 BANK:RETRIEVE
= 64 provider calls
```

No `OBSERVE` bank call is legal.

Structured-output split:

```text
48 answer-schema calls
16 operation-schema calls
```

## Budget

The plan-derived budget is:

```text
task_count = 16
bank_provider_call_max = 48
a2_allocator_call_max = 16
physical_provider_call_max = 64
treatment_call_ceiling_per_arm = 48
retrieval_unit_ceiling_per_arm = 16
observation_unit_ceiling_per_arm = 0
context_limit = 8192
aggregate token ceilings = none
automatic_retry = false
semantic_retry = false
```

## Structured-output transport

R3 reuses the exact physically qualified #2302 lineage already frozen by the structured R2 preregistration:

```text
qualification version = relaylm2-cognitive-work-sopq-v1
answer schema = sha256:d7f69ea25824f613d0b60198abe050adc66a3bf45d9f2045d1997214a55498e5
operation schema = sha256:acabff40467f48996033a4be6ee02dbfa97755bbfaf45ee1dd94cea5afeb720d
answer response_format = sha256:e7a71f6a15e7cc936df664f19e3729cbffce6562dbebcb5e69e8f9cfd070639b
operation response_format = sha256:a41031db0de0e912ded0fae8e8fb9687507debb6bcc86a286cfa0051de8afa76
```

No plain-chat fallback, fence stripping, embedded-object recovery, parser relaxation, or schema rewrite is part of R3.

## Frozen decision discipline

R3 preserves the R2 thresholds:

```text
material adaptive gain = 4 tasks
heuristic-oracle gap maximum = 2 tasks
alpha = 0.05
bootstrap = 10,000 resamples / 95%
```

The preregistered interpretation order is:

1. `INCONCLUSIVE` if accounting, hard constraints, or protocol validity fail;
2. `NO_USEFUL_WORK_HEADROOM` if `A3 - A0 < 4`;
3. `UNIFORM_NULL_VIOLATION` if `A2 - A1 >= 4` and the one-sided paired exact test is `p <= 0.05`;
4. `HEURISTIC_SUFFICIENT_UNIFORM` if `A3 - A1 <= 2`;
5. otherwise `UNIFORM_NULL_CONSISTENT`.

Sixteen tasks are sufficient for this decision rule to be discriminating: for example, five A2-only wins and zero A1-only wins yield a one-sided exact binomial p-value below 0.05. The sample count is frozen before model output and must not be expanded after seeing physical results.

## Scientific interpretation boundary

R3 is a null/control stage, not an allocator rescue stage. A null-consistent result supports the claim that heterogeneous routing headroom is absent when all tasks share the same work-value class. A `HEURISTIC_SUFFICIENT_UNIFORM` result additionally shows the cheap heuristic remains near the evaluator oracle under this uniform regime.

A `UNIFORM_NULL_VIOLATION` is not automatically a general adaptive-metareasoning win. It first triggers investigation of information leakage or an invalid null construction after preserving the frozen run.

No R3 result by itself authorizes a production scheduler, persistent allocator state, an Attention primitive, an Intelligence score, RelayLM 1.0 mutation, or architecture promotion.

## Next gate

Repository preregistration does not authorize physical execution. A separate hard-bound host/execution gate must freeze the merged R3 commit/root seed/digest and run at most one fresh physical transaction under the qualified structured-output transport.

If R3 is null-consistent, the next scientific pressure is R4 task-family shift with the R2-tested policies still frozen.

> If a cheap heuristic wins, keep the heuristic.

> A null control should be cheaper than the treatment campaign it audits.

> Do not tune the allocator after seeing the race.

> Metacognition must pay rent.
