# RelayLM 2.0 Cognitive Work allocation experiment — R0 integrity

This document is the current repository authority for the deterministic admission surface owned by #2187.

R0 is model-free. It proves only that allocation arms can be assembled without granting adaptive metareasoning free hidden information or allowing experiment instrumentation to become cognition. It does not prove an adaptive policy improves capability.

## R0 question

> **Can fixed, cheap-heuristic, adaptive, and privileged-oracle allocation arms share one public task, operation surface, canonical cognition, and hard resource envelope while adaptive meta-information is available only after its declared cost is actually charged for that case?**

## Public task versus evaluator case

R0 separates the model/deployable-policy surface from evaluator-only work-value labels.

```text
AllocationTask
  seed
  visible complexity
  visible uncertainty
  public values

AllocationCase
  public AllocationTask
  evaluator-only case identity
  evaluator-only sealed regime
```

`AllocationTask` has no `regime` field. For one seed, all evaluator regimes produce byte-identical public task packets.

Evaluator regimes are:

```text
saturated
  extra work has no intended marginal value

depth_beneficial
  another reasoning operation is evaluator-side useful

retrieval_beneficial
  retrieval is evaluator-side useful

observation_beneficial
  a paid observation is evaluator-side useful

trap
  additional work should stop
```

The regime and case identity are experiment apparatus. They are not Evidence, State, Structure, model prompt fields, or deployable routing labels.

## Operation surface and hard envelope

All deployable arms receive the same deterministic operation definitions:

```text
stop
think
retrieve
observe
meta_probe
```

and the same synthetic hard resource envelope.

R0 reuses #2155 `Operation`, `OperationPolicy`, `ResourceVector`, `ResourceLedger`, `MeasurementTrace`, and matched-arm diffing. Synthetic costs are mechanism checks only; they are not physical latency/token claims.

## Arms

### A0 — fixed

The fixed policy performs one `think` operation and is regime-blind.

### A1 — cheap heuristic

The heuristic sees only `AllocationTask` public fields. For the same seed its plan is therefore identical across every evaluator regime.

### A2 — adaptive paid-information path

A2 is intentionally two-stage.

```text
public task
  -> adaptive pre-probe policy
       plan = meta_probe only
       + explicit allocator decision cost
  -> run_paid_meta_probe
       -> run_operation_plan charges decision + meta_probe
       -> only after successful charge, read this case's sealed evaluator regime
       -> emit PaidMetaProbeReceipt bound to this case_id
  -> selected work operation executes under the same ledger
```

Before the paid boundary, A2 cannot select the hidden ideal operation because its pre-probe policy receives no regime and contains only `meta_probe`.

A probe attempt that cannot fit within the resource envelope fails before returning any hidden result. A successful `PaidMetaProbeReceipt` records the exact evaluator case identity for which the probe was purchased, so one case's paid result is not a generic reusable ticket for another case.

The only non-oracle code path that reads the sealed evaluator regime is after the probe run has recorded both:

```text
policy:adaptive:decision
policy:adaptive:operation:meta_probe
```

and the corresponding resource spend.

This remains a synthetic R0 mechanism. R1 must replace the evaluator-provided probe result with a real bounded inference/observation path and charge its measured physical cost.

### A3 — oracle

The oracle directly reads evaluator-only regime and selects its ideal operation. It is explicitly privileged and fails closed in the ordinary operation runner unless privileged admission is enabled.

A3 is an evaluator upper bound only.

## Matched-arm contract

A0/A1/A2 must match on:

```text
public task digest
operation-surface digest
hard resource envelope
starting/final canonical digest
provenance identities
projection surface
```

Allowed differences are limited to allocation-control instrumentation:

```text
policy_id
resource_total
measurement_events
```

An undeclared Evidence occurrence or canonical mutation in one arm fails the intervention comparison.

## Instrumentation boundary

These are experiment apparatus only:

```text
evaluator case identity
evaluator regime
paid probe receipt / result
ideal operation
policy identity
selected operations
resource ledger
measurement trace
oracle admission
future quality / regret metrics
```

None has semantic authority.

```text
allocator estimate != Evidence
probe result in R0 != WORLD observation
oracle choice != cognition
metric success != Outcome Evidence
```

## R0 acceptance

R0 is repository-PASS only when deterministic tests prove:

1. same seed yields byte-identical public task packets across regimes;
2. public `AllocationTask` contains no regime;
3. A0/A1 are regime-blind;
4. A2 pre-probe policy contains only `meta_probe` and is regime-blind;
5. an unpaid probe cannot return hidden evaluator result;
6. a valid paid probe charges decision and meta-probe resources before regime revelation;
7. the paid receipt is bound to the exact evaluator case identity;
8. selected adaptive work occurs after that paid boundary under the same ledger;
9. A0/A1/A2 share task, operation surface, hard envelope, canonical cognition and provenance;
10. A3 privilege fails closed without explicit privileged admission;
11. policy/resource/measurement instrumentation does not mutate canonical cognition;
12. hidden Evidence contamination fails the matched-arm diff.

## What R0 does not establish

Repository GREEN does not prove:

- adaptive allocation improves model quality;
- the synthetic meta-probe is physically realizable;
- the hidden evaluator regime can be inferred by a real model;
- any operation has the synthetic marginal value assigned here;
- heterogeneous workloads contain useful physical allocation headroom;
- A2 beats A1 or A0;
- an Intelligence property.

## Next physical stages

#2187 remains the physical experiment owner.

```text
R1 bounded non-citable physical smoke
R2 preregistered heterogeneous campaign
R3 uniform-workload null
R4 task-family shift
R5 tighter physical budget
R6 held-out generator/template family
```

R1 must freeze a real model/runtime/hardware identity, replace the synthetic paid result with an actual bounded path, and expose all allocator overhead.

> **Metacognition must pay rent.**

> **Do not give the adaptive arm the answer and charge it afterward.**

> **A paid observation is episode-local evidence for allocation, not a reusable oracle coupon.**

> **Oracle headroom tells us whether allocation matters; A2 tells us whether our allocator matters.**
