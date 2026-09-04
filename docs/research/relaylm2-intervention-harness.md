# RelayLM 2.0 Clean Intervention Harness

Status: **Post-1.0 deterministic research harness for Issue #2155.**

This surface exists to test whether transfer, resource allocation, and correction
can be expressed as clean causal interventions over the RelayLM 2.0 minimal
semantic basis before any LLM or GPU experiment is attempted.

It does not define intelligence, does not authorize production scheduling, and
does not change RelayLM 1.x semantics.

## Prerequisite

Issue #2135 / PR #2137 established the current deterministic semantic basis:

```text
Cognitive semantic / Crystal substrate
+ governed Evidence / provenance substrate
+ one canonical transaction writer
+ external governance
```

The present harness does not add a third persistent cognitive substrate.

## Principle

> **Keep the substrate fixed. Vary one cognition condition. Measure the consequence.**

A nominal A/B comparison is not causal evidence when an arm also receives more
Evidence, more context, more compute, stronger authority, or a different
canonical ontology.

The harness therefore makes those surfaces explicit and diffable.

## Canonical versus ephemeral

Canonical cognition remains owned by `relaylm.v2_semantics`.

This harness introduces only ephemeral/control-plane apparatus:

```text
ProjectionPolicy
ProjectionResult
RevisionPolicy
ResourceVector
ResourceLedger
Operation
OperationPolicy
MeasurementTrace
ArmSnapshot
InterventionSpec
ArmDiff
```

None of these are serialized into `SemanticTransactionStore` by the harness.

Forbidden interpretations include:

```text
ProjectionPolicy != Attention State
ResourceLedger   != cognitive memory
MeasurementTrace != Evidence
ArmDiff          != semantic truth
policy id        != authority
```

## Projection eligibility

`project_scope()` reads the current active Crystal roots and an explicitly named
set of observed Evidence packets.

It may include:

```text
local roots
+ optionally eligible cross-task roots
+ explicitly supplied observed Evidence packets
```

It may not:

- delete or rewrite canonical roots to create a baseline;
- inject an inactive root;
- treat endogenous Trace as observed Evidence;
- persist the selected scope.

This allows the transfer arms to differ only in whether already-present reusable
Structure is eligible for target cognition.

## Transfer arms

```text
T0 no cross-task reuse
  source Structure remains canonical but is not projected

T1 reusable Structure
  the same source Structure is projectable

T2 reusable + revisable/suppressible Structure
  same target Evidence as T1;
  a supported ordinary revision may commit through the one writer
```

The baseline must not be weakened by deleting source Structure or Evidence.

## Revision and correction

`commit_supported_revision()` accepts only an existing observed provenance record
as the correction support. When revision is disabled, the helper performs no
canonical write. When enabled, it uses the ordinary #2135 transaction writer and
normal revision/deactivation lineage.

This permits the temporal-correction distinction:

```text
one-shot Evidence
  usable in one projected scope
  != durable semantic correction

durable correction
  observed support
  + governed revision
  + later projection of revised Crystal
```

Observed Evidence may remain auditable even when it was not committed as active
semantic correction.

## Resource allocation

The deterministic resource ledger uses an explicit synthetic vector:

```text
calls
input_tokens
output_tokens
latency_units
observation_units
retrieval_units
memory_units
```

These units are not claims about physical hardware cost. They exist to prove
that a later experiment can account for different resource currencies and
prevent hidden free work.

`run_operation_plan()` executes only a synthetic plan over one declared operation
registry. It refuses undeclared operations, charges every selected operation,
and verifies that policy execution did not mutate canonical cognition.

A privileged oracle policy/operation is quarantined unless a test explicitly
enables it as a synthetic upper bound.

## Instrumentation boundary

`MeasurementTrace` records experiment metadata only. It cannot create Evidence,
Crystal roots, or authority.

Examples:

```text
threshold crossed
operation selected
regret estimate
latency surrogate
fixture verdict
```

remain outside canonical persistence.

## Matched-arm diff

`ArmSnapshot` exposes the experimentally relevant surfaces:

```text
canonical digest
active roots
provenance ids
projection eligibility
projected roots
Evidence packet ids
policy id
resource total
commit decisions
measurement events
```

`InterventionSpec` declares which surfaces are allowed to differ for a given
causal arm. `compare_arms()` reports all differences and the undeclared subset;
`assert_clean_intervention()` fails on any undeclared difference.

This is intentionally strict. For example, a transfer projection experiment may
allow only:

```text
projection_eligibility
projected_roots
```

If one arm also has extra provenance, a changed canonical digest, or hidden
resource work, the comparison fails.

## Deterministic fixture gate

`tests/unit/test_v2_interventions.py` freezes these requirements:

- **D1 projection eligibility ablation** — same Crystal/Evidence; only target
  projection eligibility differs;
- **D2 revision Evidence equivalence** — sticky/revisable arms receive the exact
  same observed correction before commit behavior diverges;
- **D3 allocator policy substitution** — one operation surface, explicit resource
  ledger, quarantined oracle;
- **D4 one-shot non-propagation** — transient Evidence does not silently become
  durable semantic correction;
- **D5 durable propagation** — supported revision affects later projection while
  preserving historical/auditable meaning;
- **D6 instrumentation non-authority** — metrics and resource accounting leave the
  canonical snapshot unchanged;
- **D7 arm-diff contamination attack** — an undeclared extra Evidence record is
  detected as a failed causal comparison.

Additional negative fixtures reject endogenous Trace as an Evidence packet and
show that one resource dimension cannot substitute for another merely because a
scalar total might look similar.

## Kill criteria

The harness fails the current #2132 minimal-basis hypothesis if a clean experiment
materially requires any of:

1. a third persistent cognitive substrate;
2. a transfer/generality/attention/correction/intelligence state object;
3. a privileged semantic writer for one experimental arm;
4. hidden Evidence or context differences;
5. free allocator observation or computation;
6. instrumentation promoted to semantic authority;
7. destructive baseline manipulation instead of projection control;
8. undeclared differences that the harness cannot expose.

A failure should return to #2132 rather than be hidden by a benchmark-specific
exception.

## Promotion gate

Passing this deterministic harness does not establish transfer, adaptive
metareasoning, correction capability, or intelligence in an LLM.

It only earns the right to create separate same-model physical experiment owners
for the constituent hypotheses:

```text
#2145 transfer / reorganization
#2143 resource allocation
#2121 correction / propagation
```

Those campaigns must remain separate until their constituent evidence exists.
Only later may #2153 ask whether a compact Intelligence macro-property earns
predictive use.

> **Instrumentation observes cognition; it does not become cognition.**
