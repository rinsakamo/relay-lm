# Protected workload calibration contract

Status: companion contract for RelayLM v1 calibration.

Owning Issue: #1388.

Bounded refinement Issue: #1879.

Parent contracts:
- `docs/contracts/calibration-evidence.md` (`calibration-contract-v1`)
- `docs/contracts/calibration-candidate-sweep.md` (CAL2 candidate derivation)

Related semantic owners: #1387 Cognitive Budget, #1386 Actual-model Evaluation, #1533 cognition execution.

This contract defines how calibration treats protected Identity/SOUL payload variation. It does not add a runtime budget control and does not select a numeric default.

## Protected workload boundary

Identity/SOUL and other payload already owned by RelayLM Identity are part of the protected workload presented to the model. Under #1387, Identity and Current Event are Tier 0 anchors: global budget pressure must not silently truncate, summarize, replace, or evict them.

Therefore protected Identity payload size is a **workload axis**, not a `BudgetPlan` envelope, not a degradation target, and not a calibration-owned semantic selection rule.

Calibration may observe how different protected workloads consume the truthful backend/model capacity, but it must preserve #1387 fail-before-generation behavior when required framing + protected Identity + Current Event + reserved output cannot fit.

## Truthful capacity stays fixed

For one frozen provider/model/runtime condition, the effective model context window remains the truthful backend capability recorded by #1386.

Calibration must not simulate a larger or smaller Identity/SOUL by changing `model_context_window` while claiming the same runtime identity. Pressure from a larger protected payload is represented by the larger protected workload itself while the runtime capacity remains fixed.

The observed live maximum is capability evidence. It is not a release recommendation by itself.

## Protected-footprint regions

Calibration may measure more than one representative protected-footprint region when supported by actual fixtures/evidence.

Region names and numeric boundaries are evidence outputs, not preselected defaults. Calibration must not assume arbitrary `small`, `medium`, or `large` token cutoffs before observing the workload distribution and fit/quality boundaries.

A region may later be described by an evidence-backed token/count range or other current approved content-free footprint observation. Such a region expresses where a candidate budget profile has support; it does not authorize truncating an Identity that exceeds the region.

## Comparison rules

A budget-effect comparison keeps the Character/Identity fixture fixed, as required by `calibration-contract-v1`. Within that fixed workload, only the declared budget condition may vary.

Runs using materially different Character/Identity payloads are not causal budget-effect pairs. They may be used to establish **profile applicability/support regions**: whether the same candidate budget policy still fits and preserves required quality under different protected workloads.

Cross-Identity results must keep their distinct #1386 fixture/revision identities and must not be collapsed into one scalar quality delta.

## Relationship to recommended layer budgets

Recommended/canonical budget profiles are conditional policies, not claims that every turn has the same prompt size.

A later profile may recommend values for existing legal controls such as:
- reserved output tokens;
- Canonical State envelope/floor;
- Working Context envelope/floor;
- Retrieved MEMORY envelope/floor;
- Event Evidence envelope/floor;
- deterministic degradation steps already legal under #1387.

Every profile proposed for canonicalization must also state the protected-workload region for which those recommendations have evidence.

The same layer-budget values may be valid across multiple protected-workload regions if evidence shows sufficient headroom and quality. If not, #1388 may define a small number of evidence-backed capability/workload profiles rather than one misleading universal number.

## Unsupported protected workload

If required framing + Identity + Current Event + output reserve cannot fit under the truthful runtime capacity, the result is the existing #1387 bounded pre-generation failure.

Calibration must not make an unsupported protected workload fit by:
- truncating or summarizing Identity/SOUL;
- silently dropping Identity material;
- reducing Current Event authority;
- inventing a second semantic selector;
- falsifying the model context window;
- weakening protected-floor enforcement.

Any future Identity compression/summarization mechanism requires its own semantic owner and evidence; it is not implied by calibration.

## Numeric-default prohibition

This companion contract selects no numeric Identity cap, protected-footprint boundary, model context default, output reserve, layer envelope, or degradation magnitude.

Numbers become recommendations only after #1386 actual-model evidence, #1387 deterministic safety evidence, CAL2/CAL3 breakpoint analysis, applicability evidence across the claimed protected-workload region, and normal #1388 provenance requirements are satisfied.

## Recalibration trigger

A material change to Identity/SOUL projection, provider framing, tokenizer/model artifact, two-pass prompt/wire, or runtime capacity may invalidate protected-workload applicability evidence even when the numeric layer-budget policy did not change.

Refs #1388 #1387 #1386 #1533 #1879
