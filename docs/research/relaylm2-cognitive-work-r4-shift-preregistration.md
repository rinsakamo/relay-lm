# RelayLM 2.0 Cognitive Work R4 held-out shift preregistration

Owner: #2321  
Parent scientific owner: #2187

## Purpose

R2 heterogeneous (#2308) and R3 uniform retrieval-only (#2320) both left the cheap deterministic heuristic on the same or better capability/resource frontier than the tested adaptive allocator.

R4 does **not** tune either policy. It changes only the relationship between public operation availability and true marginal work value.

> **Shift the cue, not the policy.**

## Frozen predecessor results

```text
R2 heterogeneous:
A0/A1/A2/A3 = 16/40, 33/40, 32/40, 33/40
category = HEURISTIC_SUFFICIENT

R3 uniform retrieval-only:
A0/A1/A2/A3 = 0/16, 16/16, 16/16, 16/16
category = HEURISTIC_SUFFICIENT_UNIFORM
```

These results remain historical and are not reinterpreted by R4.

## Shift construction

R4 keeps the same five semantic regimes used by R2:

```text
EASY_SATURATED
DEPTH_BENEFICIAL
RETRIEVAL_BENEFICIAL
OBSERVATION_BENEFICIAL
UNCERTAINTY_TRAP
```

The balanced suite contains four fresh unseen tasks per regime, twenty tasks total.

Every task now exposes the same public operation surface:

```text
ZERO
THINK
RETRIEVE
OBSERVE
```

so both:

```text
retrieval_available = true
observation_available = true
```

for every task.

Useful packet content remains regime-dependent. Non-useful operations receive deterministic task-scoped auxiliary records/observations that do not reveal the target answer. Hidden regime labels, usefulness labels, expected answers, and evaluator truth never enter the allocator request.

This removes the R2 construction-specific shortcut in which availability flags themselves strongly indicated the useful operation.

## Frozen policies

R4 imports the R2-tested semantics unchanged:

```text
A0 = fixed THINK
A1 = retrieval-first availability heuristic
A2 = model allocator unchanged
A3 = evaluator-only oracle unchanged
```

Because every R4 task exposes retrieval, the unchanged A1 chooses RETRIEVE on all twenty tasks. That behavior is the intended held-out transfer pressure, not a bug or a new heuristic.

The allocator prompt, operation descriptions, parsers, response schemas, paired exact test, bootstrap implementation, resource accounting and thresholds are inherited unchanged.

## Fresh identity

```text
version = relaylm2-cognitive-work-r4-availability-shift-v1
root seed domain = relaylm2-2187-r4-availability-decorrelation-v1
```

The concrete root seed is derived only from the immutable squash-merged preregistration commit. No R2/R3 seed/task instance is reused.

## Exact plan

Each task has one shared bank:

```text
BASE
A2_ALLOCATE
BANK:THINK
BANK:RETRIEVE
BANK:OBSERVE
```

Totals:

```text
20 BASE
20 A2_ALLOCATE
20 BANK:THINK
20 BANK:RETRIEVE
20 BANK:OBSERVE
= 100 physical provider calls
```

Structured-output split:

```text
80 answer-schema
20 operation-schema
```

## Qualified transport

The already-qualified #2302 lineage remains frozen:

```text
qualification = relaylm2-cognitive-work-sopq-v1
answer schema = sha256:d7f69ea25824f613d0b60198abe050adc66a3bf45d9f2045d1997214a55498e5
operation schema = sha256:acabff40467f48996033a4be6ee02dbfa97755bbfaf45ee1dd94cea5afeb720d
answer response_format = sha256:e7a71f6a15e7cc936df664f19e3729cbffce6562dbebcb5e69e8f9cfd070639b
operation response_format = sha256:a41031db0de0e912ded0fae8e8fb9687507debb6bcc86a286cfa0051de8afa76
```

No prompt-only fallback, wrapper stripping, embedded JSON extraction or schema repair is permitted.

## Statistical discipline

Inherited unchanged:

```text
material task gain = 4
heuristic-oracle gap tolerance = 2
alpha = 0.05
paired directional exact test = unchanged
bootstrap = 10,000 / 95%
```

Primary comparison is A2 vs A1. A0 remains the fixed simple baseline and A3 remains the headroom discriminator.

Frozen interpretation order:

```text
INCONCLUSIVE
HEURISTIC_TRANSFER_SUFFICIENT
NO_MATERIAL_SHIFT_HEADROOM
SIMPLE_FIXED_BASELINE_SUFFICIENT
ADAPTIVE_TRANSFER_SIGNAL
SHIFT_HEADROOM_UNCAPTURED
```

`ADAPTIVE_TRANSFER_SIGNAL` requires material oracle headroom over A1 and a material/significant A2>A1 effect. A materially better A0 blocks that interpretation.

## Information boundary

Before purchase, A2 sees only public task information, base answer, legal operation descriptions and the now-common availability surface.

It never sees:

```text
hidden regime
which packet is useful
expected answer
A3 choice
bank answer
post-hoc correctness
```

Only the purchased RETRIEVE or OBSERVE packet enters its corresponding revision request.

## Resource boundary

The shared bank pays once for every non-zero operation so evaluator-side A0/A1/A2/A3 reconstruction does not leak future results into allocation.

Budget identity:

```text
tasks = 20
bank provider calls max = 80
A2 allocator calls max = 20
physical provider calls max = 100
treatment call ceiling per arm = 60
retrieval unit ceiling per arm = 20
observation unit ceiling per arm = 20
context = 8192
retry = false
```

## Physical gate

This preregistration is repository-only. It authorizes no real model call.

After squash merge and post-merge CI:

1. derive and record the concrete root seed and preregistration digest from the merged commit;
2. package a separate hard-bound R4 host;
3. create a separate exactly-once physical execution owner.

Physical execution must use one clean exact checkout, fresh ExecutionBinding, fresh empty external artifact root, real live binding probes, exact 100-call plan, and zero retry/fallback/replay/repair.

## Interpretation boundary

A surviving adaptive result means only that the **already-frozen tested allocator** transferred better than the retrieval-first heuristic under this declared cue/value relationship shift.

A negative result strengthens the evidence that the tested explicit metareasoner does not pay for itself across the current synthetic lineage.

Neither outcome directly authorizes production architecture.

R5 tighter-budget pressure is materially required only if an adaptive effect survives R4. R6 remains the separate held-out generator/template-family test.

## Architecture consequence

**NONE.**

No production scheduler, persistent allocator state, Attention primitive, Intelligence score, v1 mutation or architecture promotion follows from this preregistration.

> **Do not tune the allocator after seeing the race.**

> **A heuristic that wins because the construction tells it what to do has not yet survived transfer.**

> **Shift the cue, not the policy.**

> **Metacognition must pay rent.**
