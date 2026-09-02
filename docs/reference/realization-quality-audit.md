# Realization Quality Audit

This reference defines the admission and exit gate for bounded **Realization Quality Audit** work on RelayLM `v1`.

It is development-workflow authority only. It does not redefine Runtime, Context, State, Continuity, Evaluation, Product/Operator, Provider, Persistence, or release semantics.

## Purpose

Realization audit verifies that current RelayLM contracts are actually realized on supported production, operator, persistence, and evaluation paths.

The audit is not an unlimited defensive-hardening exercise.

> **Repair material realization defects. Record speculative hardening. Converge and stop.**

## Material-finding admission gate

A newly discovered finding may open a repair transaction only when at least one of these conditions is true.

### 1. Production or operator reachability

The defect is reproducible through a supported production execution, persistence, configuration, API, CLI, or operator path and can materially affect at least one of:

- user-visible or client-visible response behavior;
- State or Continuity authority;
- persisted authority or reload behavior;
- success / failure classification;
- supported startup or release operability.

### 2. Current contract violation

The defect directly violates a current documented contract on which a supported caller, operator, runtime path, or persisted authority consumer can rely.

A theoretical inconsistency is not sufficient by itself; the violated guarantee must be part of current authority rather than a possible future hardening rule.

### 3. False-GREEN evaluation risk

The defect can make a current required test, evaluation, scenario, trace, acceptance, or release-evidence surface report success while a material product/runtime contract is broken.

This includes citable evidence that can be produced or consumed through a supported evaluation boundary while misrepresenting the behavior it claims to prove.

## Findings that normally do not open repair transactions

Unless one of the material criteria above is also satisfied, record the finding and stop rather than adding code for:

- multi-step manual artifact forgery outside supported input, persistence, or evidence boundaries;
- states that current production producers cannot create and current supported consumers cannot receive;
- hypothetical corruption for which an existing lower boundary already owns rejection;
- duplicate validation added only for defense in depth with no current contract or supported-path consequence;
- speculative cleanup, abstraction, normalization, or generalized hardening discovered while auditing a narrower responsibility.

A finding may be promoted later if fresh authority shows that it became production-reachable, contract-required, or capable of creating false-GREEN evidence.

## Existing in-flight work

When this gate is introduced, already-open bounded audit transactions may complete under the workflow and scope they were admitted with.

The gate applies to **new findings and follow-up transactions**. It must not be used to retroactively invalidate a transaction merely because its RED or implementation already exists.

## Bounded audit pass

A clean-pass claim must come from a fresh-authority review of one declared lane responsibility. The pass must:

1. re-fetch current `v1` and relevant open competing work;
2. inspect the supported realization path owned by the lane, not only declarations or schemas;
3. inspect materially equivalent sibling supported paths far enough to test the lane's claimed invariant for material counterexamples;
4. apply the material-finding admission gate above;
5. either admit one material finding as a bounded transaction or record that no new material finding was found;
6. avoid expanding mutation into another semantic owner merely to keep the audit active.

Sibling-path discovery is not mutation-scope expansion. A material finding owned outside the current lane is routed to its current owner rather than ignored or repaired opportunistically by the auditing lane.

A repair transaction resets the lane's clean-pass count. After the repair merges and authority is reconstructed, clean-pass counting begins again from zero.

## Lane exit gate

After transactions that were already in flight are resolved, a Realization Quality Audit lane may declare its audit complete after **two consecutive bounded fresh-authority passes find no new material finding**.

```text
material finding
  -> bounded repair transaction
  -> merge / authority reconstruction
  -> clean pass 1
  -> clean pass 2
  -> lane audit complete
```

The two passes must be distinct fresh-authority reviews. Re-reading the same unchanged observation twice in one review does not count as two passes.

A lane that reaches this gate stops generating additional audit work unless:

- current `v1` later changes a relevant owned contract or realization path;
- a new externally reported failure supplies material production evidence;
- a cross-owner Issue explicitly returns bounded work to the lane.

## Cross-owner and integration work

Existing cross-owner findings remain tracked by their owning Issues. Their existence does not require a component lane to keep searching for unrelated defects after its own exit gate is satisfied.

Likewise, lane audit completion does not imply release or integration completion. Genuine cross-owner integration and release-readiness gates remain independently governed by their current owners.

## Transaction discipline remains unchanged

Once a finding passes this admission gate, the normal development workflow still applies:

- one bounded responsibility;
- test-first RED for semantic behavior changes;
- minimal implementation;
- code / tests / owner-local authority convergence;
- fresh-head semantic review;
- exact-head required CI;
- exact reviewed-head merge;
- owning-Issue reconciliation.

This gate narrows **which new audit findings become repair work**. It does not weaken verification for admitted work.

## Non-goals

This reference does not:

- weaken product or release contracts;
- suppress supported-path failures;
- close existing component or integration Issues automatically;
- redefine severity or release-blocker policy outside Realization Quality Audit;
- require audit notes to become permanent repository authority;
- modify frozen 0.x `main`.
