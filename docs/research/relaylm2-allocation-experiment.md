# RelayLM 2.0 Cognitive Work allocation experiment — R0 integrity

This document is the current repository authority for the allocation experiment surface owned by #2187.

It records deterministic repository-side experiment mechanics only. It does **not** record actual-model evidence, does not define Intelligence, and does not authorize physical execution from repository state alone.

The allocation hypothesis remains owned by #2187 and #2143. The clean matched-intervention substrate remains owned by #2155. Downstream Intelligence macro-property evaluation remains owned by #2153.

## R0 question

R0 asks only:

> **Can fixed, cheap-heuristic, adaptive, and privileged-oracle allocation arms be assembled over the same task, operation surface, canonical cognition, and hard resource envelope while charging adaptive meta-work and quarantining evaluator privilege?**

R0 is deliberately model-free. It cannot establish that adaptive metareasoning improves capability or that any real model can infer which operation is valuable.

## Deterministic workload identity

R0 defines five evaluator-side work-value regimes:

```text
saturated
  extra work has no intended marginal value

depth_beneficial
  another reasoning operation is the evaluator-side useful action

retrieval_beneficial
  retrieval is the evaluator-side useful action

observation_beneficial
  a paid observation is the evaluator-side useful action

trap
  extra work should stop rather than be amplified
```

The public task packet is generated deterministically from `seed` only. For one fixed seed, changing the hidden regime leaves the public packet byte-identical.

The packet exposes only ordinary synthetic surface signals:

```text
visible complexity bucket
visible uncertainty bucket
public value vector
```

It does not expose:

```text
regime identity
ideal operation
arm identity
oracle result
expected utility / regret
```

The hidden regime is evaluator apparatus, not canonical cognition or model-facing Evidence.

## One operation surface

Every deployable arm receives the same operation definitions:

```text
stop
think
retrieve
observe
meta_probe
```

with one common synthetic hard resource envelope.

R0 consumes #2155 `Operation`, `OperationPolicy`, `ResourceVector`, `ResourceLedger`, `MeasurementTrace`, and matched-arm diffing. Synthetic costs are mechanism tests only; they are not physical latency/token claims.

Changing the allocation policy must not mutate canonical cognition.

## Arms

### A0 — fixed

```text
policy = always think once
```

The fixed policy is regime-blind.

### A1 — cheap heuristic

A low-cost deterministic policy uses only public surface signals.

It does not inspect the hidden regime. For the same seed, its plan is therefore identical across all five evaluator regimes.

### A2 — adaptive

R0 represents the adaptive information boundary mechanically:

```text
policy decision cost
  -> paid meta_probe
  -> evaluator-side synthetic probe result
  -> selected work operation
```

The R0 implementation uses the hidden regime only as the synthetic result that becomes available **after** the declared `meta_probe` operation is included and charged.

This is not evidence that a real model can obtain such a signal cheaply. R1 must replace this synthetic meta-result with an actual bounded inference/observation path.

The adaptive arm therefore receives no claimable capability advantage from R0. R0 proves only that the accounting boundary can represent bought meta-information without silently making it free.

### A3 — oracle

The oracle selects the evaluator-side ideal operation without paying the adaptive meta-probe.

It is explicitly `privileged=True` and fails closed when passed through the deployable #2155 operation runner without privileged admission.

A3 is an evaluator upper bound only. Its policy identity, selected operation, and hidden regime must never become canonical State, Structure, or Evidence.

## Matched-arm contract

For A0/A1/A2, require equality of:

```text
public task digest
operation-surface digest
hard resource envelope
starting canonical digest
provenance identities
projection surface
```

Allowed differences are only the declared allocation-control surfaces:

```text
policy_id
resource_total
measurement_events
```

`policy_id` must differ. Resource or measurement differences may differ according to the chosen plan and charged meta-work.

An extra observation or semantic mutation in only one arm changes canonical/provenance identity and must fail matched-arm validation.

## Instrumentation boundary

The following are experiment instrumentation only:

```text
hidden regime
ideal operation
policy identity
selected operations
resource ledger
measurement trace
oracle admission
future quality / regret metrics
```

They have no semantic authority.

```text
allocator says high value
  != Evidence

oracle says operation X is ideal
  != WORLD observation

metric success
  != Outcome Evidence
```

## R0 acceptance

R0 is repository-PASS only when deterministic tests prove:

1. same seed generates the same public packet;
2. changing hidden regime for one seed leaves the public packet unchanged;
3. different seeds change the public packet;
4. evaluator regimes map to the declared ideal operations;
5. A0/A1/A2 share one public task, operation surface, hard envelope, canonical snapshot, and provenance set;
6. A1 depends only on public task surface;
7. A2 pays both explicit decision cost and `meta_probe` cost before its evaluator-side selected work;
8. A3 is rejected by the deployable runner unless privileged execution is explicitly admitted;
9. policy/resource/measurement instrumentation does not mutate canonical cognition;
10. a hidden extra Evidence occurrence in one arm fails the matched-arm diff.

A failure is experiment-design evidence. Do not weaken the matched-arm rules merely to reach R1.

## What R0 does not establish

Repository GREEN does not prove:

- adaptive allocation improves model quality;
- the synthetic meta-probe is physically realizable;
- any selected operation has the claimed marginal value for a real model;
- heterogeneous workloads have useful allocation headroom;
- a cheap heuristic is worse than explicit metareasoning;
- a real oracle upper bound is large;
- any Intelligence claim.

R1 must bind one frozen physical model/runtime/hardware identity and replace synthetic utility/meta-signal assumptions with measured actual-model behavior.

## Next physical stages

The owning Issue #2187 defines the later gates:

```text
R1 bounded non-citable physical smoke
R2 preregistered heterogeneous campaign
R3 uniform-workload null
R4 task-family shift
R5 tighter physical budget
R6 held-out generator/template family
```

No physical stage is authorized merely because R0 repository tests pass.

> **Metacognition must pay rent.**

> **Oracle headroom tells us whether allocation matters; A2 tells us whether our allocator matters.**

> **Keep the task and operation surface fixed. Change only the allocation policy, and charge every extra look.**
