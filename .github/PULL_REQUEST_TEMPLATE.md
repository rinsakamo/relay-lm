## Bounded responsibility

<!-- One PR = one bounded transaction. What is the single responsibility? -->

## Owning Issue

<!-- `Closes #...`, `Refs #...`, or `None`. Reconcile it after merge. -->

## Change type

- [ ] Semantic change
- [ ] Behavior-preserving change
- [ ] Docs / repository-only change

## Meaning / examples

<!-- For semantic work, state the intended meaning and concrete Given / When / Then examples. -->

## Evidence

<!-- Semantic: existing GREEN + new contract RED, then implementation GREEN. Other work: relevant baseline/verification. -->

## Authority impact

- Code:
- Tests:
- Current-authority docs:
- Documentation impact is explicitly none: [ ]

## Non-goals / deferred work

<!-- Keep adjacent work out of this transaction. -->

## Canonical convergence

- [ ] No compatibility shim, bridge, old-path forwarder, dual authority, or deprecated-behavior fallback is introduced or retained.
- [ ] Affected internal consumers converge directly on the current canonical owner.

## Fresh-head completion

- [ ] Cumulative PR diff still matches the bounded responsibility.
- [ ] Current-authority docs match the implementation and keep deferred behavior deferred.
- [ ] Required CI belongs to the exact reviewed PR head and is GREEN.
- [ ] Merge will use expected-head protected squash.
- [ ] Owning Issue will be closed, narrowed, or explicitly superseded after merge.
