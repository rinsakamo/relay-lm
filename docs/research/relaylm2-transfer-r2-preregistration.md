# RelayLM 2.0 — transfer R2 shared/null preregistration

Owner: #2341  
Parent actual-model experiment: #2157  
Theory owner: #2145

This note freezes the first citable shared/null transfer campaign after the non-citable R1 physical smoke in #2338.

It is a preregistration and repository-mechanics document. It is not physical evidence and does not authorize architecture changes.

## R1 boundary

#2338 established only that the bounded physical path could complete:

```text
source-learning -> T0 -> T1 -> T2
4/4 provider calls
qualified JSON-Schema transport
no retry/fallback/replay/repair
NON_CITABLE_R1_SMOKE
```

The frozen R1 fixture was floor-like at `examples_visible=1`. R2 does not repair that point by selecting another favorable evidence level or replacement seed.

Instead, every R2 family measures the full target-evidence curve:

```text
examples_visible = 0,1,2,3
```

## Scientific contrast

R2 asks whether a learned reusable Structure produces a source-relation-specific effect:

```text
D_f = AUC(T1) - AUC(T0)

I = mean(D_f | shared) - mean(D_f | null)
```

A generic extra-context benefit that appears equally on `shared` and `null` does not count as transfer.

## Generator and seeds

The current deterministic formal vector generator is retained unchanged:

```text
modulus = 10
vector width = 4
source examples = 4
target steps = 4
target examples per step = 3
```

Only `shared` and `null` regimes enter R2.

The R1 seed `2157001` is excluded permanently.

R2 uses eight fresh seeds per regime. Concrete seeds derive deterministically from:

```text
relaylm2-transfer-r2-shared-null-v1
+ final merged preregistration commit
+ regime
+ within-regime index
+ collision counter
```

The generated family order interleaves `shared,null` to reduce monotonic runtime-order confounding.

No family may be replaced after source learning or target outputs are seen.

## Source-learning boundary

Each family performs one physical source-learning call from the four source examples.

The model-authored hypothesis is committed through the existing #2157 governance path. R2 records whether it exactly equals the evaluator-side source rule.

Primary results remain unconditional over all 16 preregistered families. A `source_hypothesis_correct` subset is diagnostic only and may not replace the primary analysis.

If fewer than half of the preregistered families learn the source rule exactly, the frozen interpretation is `NO_SOURCE_LEARNING`.

## Arms

```text
T0
  same learned source Structure remains canonical
  cross-task projection disabled

T1
  same learned source Structure
  cross-task projection enabled

T2
  same treatment meaning as T1 in R2
  no revision/suppression intervention yet
```

T2 is an integrity treatment-equivalence arm at R2. Mismatch and revision belong to later gates.

## Exact call plan

Per family:

```text
1 source-learning
4 T0 target probes at evidence levels 0,1,2,3
4 T1 target probes at evidence levels 0,1,2,3
4 T2 target probes at evidence levels 0,1,2,3
= 13 calls
```

Across 16 families:

```text
16 source-learning
64 T0
64 T1
64 T2
= 208 provider calls
```

The call plan is generated from the merged preregistration identity and content-digested. A later host must follow it exactly and fail closed on mismatch.

## Structured transport

The R1 four-call adapter remains unchanged.

R2 adds a separate plan-aware adapter that delegates provider I/O to the already qualified #2302 structured client and reuses the #2335 source/target JSON Schemas:

```text
source-learning -> source Structure schema
target probe    -> target integer-array schema
```

The R2 adapter selects schema only from the frozen call-plan index. It does not inspect prompt text or recover embedded JSON.

The 209th call is rejected.

## Outcome vector

Each family/arm preserves the complete correctness curve:

```text
C0,C1,C2,C3
```

and derives:

```text
AUC = mean(C0,C1,C2,C3)
first competence level when present
natural input/output token cost
```

Physical packaging must additionally preserve projected-Structure bytes/hash, target packet identity, canonical/provenance snapshots, binding identity and protocol state.

## Primary statistics

Family-level treatment effect:

```text
D_f = AUC(T1) - AUC(T0)
```

Primary interaction:

```text
I = mean(D_f | shared) - mean(D_f | null)
```

Frozen statistical procedure:

```text
balanced 8 shared + 8 null
two-sided exact regime-label permutation test
alpha = 0.05
10,000 deterministic stratified bootstrap resamples
95% bootstrap interval
material positive interaction = 0.25
```

A positive transfer signal requires all of:

```text
I >= 0.25
exact p <= 0.05
bootstrap lower bound > 0
```

P-value alone is insufficient.

## Frozen interpretation

```text
INCONCLUSIVE
NO_SOURCE_LEARNING
GENERIC_CONTEXT_EFFECT
TRANSFER_SIGNAL
TRANSFER_EFFECT_UNCAPTURED_OR_UNSTABLE
```

There is deliberately no post-hoc `NO_SHARED_HEADROOM` category because this preregistration does not add a separate oracle diagnostic.

Ordering:

1. incomplete or protocol-invalid -> `INCONCLUSIVE`;
2. exact source-rule learning rate below 50% -> `NO_SOURCE_LEARNING`;
3. shared gain at least 0.25 but shared-minus-null interaction below 0.25 -> `GENERIC_CONTEXT_EFFECT`;
4. positive material/significant/bootstrap-clean interaction -> `TRANSFER_SIGNAL`;
5. otherwise -> `TRANSFER_EFFECT_UNCAPTURED_OR_UNSTABLE`.

## Saturation

Saturated families are never replaced:

```text
all target arm/levels false -> floor-saturated
all target arm/levels true  -> ceiling-saturated
otherwise                   -> informative/non-uniform
```

They remain in the unconditional primary analysis.

## Anti-leakage

Before physical execution the later host/package must preserve the existing #2157 invariants:

```text
regime label not model-visible
hidden rules not model-visible
expected output not model-visible
arm label not semantic prompt content
matched target packet/examples across arms
T0 differs only by projection eligibility
T1/T2 reusable Structure meaning equal in R2
model output and verifier result remain instrumentation, not Evidence
```

## Resource boundary

Natural treatment cost is primary. Projected reusable Structure may add prompt tokens and must pay those tokens visibly.

R2 does not truncate T1 to force artificial token equality. A later finite-resource gate owns tighter matched-budget pressure if a transfer interaction survives.

## Next gate

After this preregistration is squash-merged and post-merge CI is green:

1. compute the concrete family seeds, call-plan digest and preregistration digest from the merged commit;
2. terminalize #2341 as the scientific preregistration owner;
3. create a separate repository-only R2 host-packaging owner;
4. fake-qualify the exact 208-call campaign and durability/binding/accounting contract;
5. only after that host merges may a separate exactly-once physical owner spend the R2 seed set.

No provider/model calls belong to #2341.

> **Measure the adaptation curve, not the convenient point on it.**

> **A wrong learned prior is part of the mechanism, not a seed to discard.**

> **Shared minus null is the transfer question.**
