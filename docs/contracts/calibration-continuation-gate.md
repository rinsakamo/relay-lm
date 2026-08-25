# Calibration continuation gate

Status: CAL2 execution/continuation policy for RelayLM v1.

Owning Issue: #1388.

Related owners: #1386 Actual-model Evaluation, #1387 Cognitive Budget, #1533 two-pass cognition semantics.

## Principle

> **Strict runtime, tolerant calibration evaluation.**

This contract changes only how CAL2 interprets a safely failed generated turn. It does not relax provider parsing, typed candidate construction, source validation, State/Continuity validation, or fail-closed commit semantics.

Calibration must not add coercion, JSON repair, retry, fallback, parser relaxation, or partial authority commit merely to keep an experiment running.

## No all-turn perfection gate

CAL2 does not require every generated turn to reach strict typed extraction/materialization before later pressure conditions may run.

`6/6` strict Pass 2 completion for a six-turn fixture is therefore **not** a general CAL2 continuation prerequisite.

A safely rejected model output remains a protocol-quality observation. The affected turn loses semantic coverage for channels that did not commit, while valid capacity, token, timing, deterministic-pressure, Pass 1, and other successful-turn observations remain evidence.

There is no universal success-percentage threshold. The question is whether the requested comparison remains safe and interpretable.

## Continue when

CAL2 may continue after isolated or occasional fail-closed generated-turn defects when all of these remain true:

1. no invalid or unsupported output was committed as authority;
2. the budget/capacity/token observation itself remains valid for the frozen condition;
3. non-budget identity remains fixed so the controlled comparison is valid;
4. enough successful coverage remains for the quality dimension being compared;
5. the failure pattern remains interpretable rather than systematic.

Record exact successful and failed turns plus the bounded failure class/boundary. Do not relabel failures as passes.

A condition with incomplete semantic coverage may still contribute capacity/headroom/timing/deterministic-pressure evidence, but it must not support a semantic claim that the failed turns leave unobserved.

## Stop, reject, or narrow coverage when

CAL2 must stop the claimed comparison, reject the candidate region, or explicitly narrow coverage when:

- invalid output is committed or an authority/provenance invariant is violated;
- provider/runtime/capacity failure makes the measurement itself invalid, except an owner-defined expected fail-before-generation pressure boundary;
- failures become systematic, repeated, or pressure-correlated enough that the semantic comparison cannot be interpreted;
- successful coverage is insufficient for the quality dimension being claimed;
- non-budget model/provider/tokenizer/prompt/serialization/scenario/Character/runtime drift invalidates the comparison.

A pressure-correlated increase in safe protocol failures is itself a negative pressure observation. It may disqualify that candidate region without restarting CAL2 from an all-turn-perfect baseline.

## Baseline and pressure conditions

`baseline_fit` means the fixture fits without budget degradation. It does not mean every stochastic model output is protocol-perfect.

A baseline may serve as a comparator when it is safe, measurement-valid, and has enough successful semantic coverage for the comparison. Pressure conditions use the same rule.

Protocol-failure rate remains a quality dimension and must be compared between baseline and pressure conditions.

## Prompt/serialization drift

Recalibration is scoped to what changed.

When prompt or serialization bytes change:

- exact serialized-input counts, headroom, and derived reserve boundaries that depend on those bytes must be remeasured before canonical numeric use;
- prior counts must not be relabeled to a new RelayLM SHA;
- unchanged backend/model capacity and KV-memory observations may remain reusable when their own runtime/host identity is materially equivalent;
- historical semantic observations remain historical evidence;
- a current prompt-dependent `T0` may be acquired as part of the next pressure transaction instead of through a separate all-turn-perfect rerun gate.

An unrelated documentation-only commit does not by itself invalidate runtime/model evidence.

## Qualification and defaults

#1386 remains the product-quality/qualification owner. CAL2 continuation is only the narrower decision that evidence remains safe and interpretable enough to measure budget breakpoints.

Recurring material defects may be handed back to #1386/#1533 without automatically blocking unrelated capacity or deterministic calibration evidence.

CAL6 canonicalization remains stricter than CAL2 continuation: a recommended profile still needs sufficient quality coverage, deterministic safety evidence, pressure/breakpoint evidence, applicability limits, and exact provenance. A candidate with unacceptable protocol-failure behavior must not become a default merely because CAL2 continued measuring it.

Refs #1388 #1386 #1387 #1533
