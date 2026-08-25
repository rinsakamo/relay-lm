# Calibration continuation gate

Status: CAL2 execution/continuation policy for RelayLM v1.

Owning Issue: #1388.

Related owners: #1386 Actual-model Evaluation, #1387 Cognitive Budget, #1533 two-pass cognition semantics.

This contract defines when an actual-model calibration transaction may continue after a generated turn fails a strict model-output boundary. It does **not** relax RelayLM runtime parsing, candidate construction, source validation, State/Continuity validation, or fail-closed commit semantics.

## Principle

> **Strict runtime, tolerant calibration evaluation.**

Calibration measures product behavior under budget pressure. It must preserve strict deterministic authority boundaries, but it must not require a stochastic model to produce perfect wire output on every generated turn before any budget evidence may be collected.

A strict model-output failure is a quality observation. It is not automatically a calibration-transaction blocker.

## Runtime invariants remain strict

During every calibration run:

- provider/output parsing remains strict;
- typed candidate construction remains strict;
- source/provenance validation remains strict;
- State and Continuity validation/lifecycle remain strict;
- malformed or unsupported proposals remain fail-closed;
- no coercion, JSON repair, retry, fallback, parser relaxation, or unsafe partial commit is introduced for calibration;
- an invalid turn must not mutate State/Continuity merely so the experiment can continue.

This contract changes only the **evaluation disposition after the turn has already failed safely**.

## No all-turn perfection gate

CAL2 has no fixed requirement that every generated turn reach strict typed extraction/materialization.

In particular, `6/6` strict Pass 2 completion for a six-turn fixture is **not** a general prerequisite for continuing to the next pressure condition.

Protocol completion/failure rate remains an observed product-quality dimension. A failed turn loses semantic coverage for the channels that did not commit, but valid capacity, token, timing, deterministic-pressure, and successful-turn semantic observations remain evidence.

Calibration must report the exact successful/failed turn set; it must not hide failures by converting them into passes.

## Continue after an isolated fail-closed defect

A calibration transaction may continue after one or more generated-turn failures when all of the following remain true:

1. **Safety holds.** No invalid or unsupported output was committed as State, Continuity, or other authority.
2. **The budget observation is valid.** The runtime/counter/provider observations needed for the pressure question remain attributable to the frozen condition.
3. **The failure does not invalidate the controlled comparison.** Non-budget identity remains fixed, and the failure is not evidence of unrelated runtime drift.
4. **Useful coverage remains.** Enough successful generated turns remain to interpret the quality dimension being compared. Coverage is dimension-specific; a failed Pass 2 turn does not erase valid Pass 1, token, timing, or deterministic budget evidence from other turns.
5. **The failure pattern is still interpretable.** Isolated or occasional fail-closed model-output defects may be carried as quality observations instead of forcing prompt repair before calibration continues.

There is deliberately no universal numeric success-percentage threshold. The question is whether the requested comparison remains interpretable and safe.

## Blocker conditions

CAL2 must stop, reject the condition, or narrow its claimed coverage when any of the following applies:

- invalid/unsupported output is committed or another deterministic authority/provenance invariant is violated;
- provider/runtime/capacity failure makes the measurement itself invalid, except an owner-defined expected fail-before-generation pressure boundary;
- generated failures are systematic, repeated, or pressure-correlated enough that the requested semantic comparison cannot be interpreted;
- successful coverage is insufficient for the quality dimension being claimed;
- non-budget model/provider/tokenizer/prompt/serialization/scenario/Character/runtime drift invalidates a baseline/pressure pair;
- the evidence cannot distinguish ordinary model variance from the budget effect being calibrated.

A pressure-correlated increase in safe protocol failures is itself a legitimate negative pressure observation. It may disqualify that candidate region without requiring the entire calibration lane to restart from an unpressured perfect run.

## Coverage and comparison

For every generated condition, record at least:

- attempted turns;
- successful Pass 1 turns;
- successful strict Pass 2 typed commits;
- failed turns and bounded failure class/boundary;
- whether each failure was fail-closed with no authority mutation;
- which semantic quality dimensions remain covered;
- whether the condition remains usable as a controlled comparator.

A condition with incomplete semantic coverage may still contribute capacity/headroom/timing/deterministic-pressure evidence. It must not be cited for a semantic dimension that the failed turns leave unobserved.

## Baseline and pressure usage

`baseline_fit` means the fixture fits without budget degradation. It does not mean that every stochastic model output must be protocol-perfect.

A baseline can serve as a calibration comparator when it is safe, measurement-valid, and has enough successful semantic coverage for the comparison being made. Protocol defects are retained in the baseline quality record.

Likewise, a pressure condition is not automatically discarded because one turn fails strict Pass 2 parsing. Compare the failure pattern with baseline. If failures materially increase or become systematic under pressure, record that as a quality breakpoint and reject or bound the candidate region as appropriate.

## Prompt/serialization drift and evidence reuse

Recalibration is scoped to what changed.

When prompt or serialization bytes change:

- exact serialized-input token counts, headroom, and derived reserve boundaries that depend on those bytes must be remeasured before canonical numeric use;
- prior exact counts must not be relabeled to the new RelayLM SHA;
- unchanged backend/model capacity, KV-memory observations, and other runtime capability facts may remain reusable when their own identity and host conditions remain materially equivalent;
- historical semantic observations remain historical evidence and do not require a full Stage R requalification merely because CAL2 needs a fresh token baseline;
- a current prompt-dependent `T0` may be acquired as part of the next pressure transaction rather than through a separate all-turn-perfect rerun gate.

An unrelated documentation-only repository change does not invalidate model/runtime/token evidence merely because the Git commit changed; the affected authority must be determined from the changed surfaces.

## Relationship to #1386 qualification

#1386 remains the owner of product-quality methodology and release qualification. A previously qualified two-pass path is not silently re-qualified by this contract.

CAL2 continuation is a narrower question: whether evidence remains safe and interpretable enough to measure budget breakpoints. It must not turn every isolated model-output defect discovered during calibration into a mandatory prompt-tuning transaction.

Recurring material defects may still be handed back to #1386/#1533 as product findings. That handoff does not automatically block unrelated deterministic or capacity calibration evidence.

## Canonical-default gate remains stronger

Tolerant CAL2 continuation does not mean weak default selection.

Before CAL6 canonicalization, #1388 must still have sufficient supported quality coverage, deterministic safety evidence, pressure/breakpoint evidence, applicability limits, and exact provenance to justify the recommended profile. A candidate with unacceptable protocol-failure behavior must not become a default merely because CAL2 was allowed to continue measuring it.

## Example disposition

An isolated Pass 2 enum mistake that is rejected by the strict parser, commits no State/Continuity, and leaves the remaining successful turns usable for comparison is recorded as a protocol-quality defect and CAL2 continues.

By contrast, an invalid candidate that is committed, a pressure condition whose failures become systematic enough to erase the relevant semantic comparison, or a run whose provider/runtime identity drifted is a blocker for that claimed comparison.

Refs #1388 #1386 #1387 #1533
