# Relay Theory 0.1 — bounded Lean core

This directory is an isolated Lean 4 formalization lane for Relay Theory issue #2403.
It is **not** a RelayLM runtime dependency and does not authorize changes to `v1` or `v2`.

The first milestone intentionally formalizes only the smallest finite witness surface
extracted by #2396 / PR #2400. It does not claim a universal probability ontology,
a universal minimal axiom system, or a category-theoretic foundation.

## Python ↔ Lean semantic correspondence

The executable synthesis apparatus remains:

- `tools/relay_theory_axiom_extraction.py`
- `tests/unit/test_relay_theory_axiom_extraction.py`

The bounded Lean roles correspond as follows:

| Extracted role | Lean surface |
| --- | --- |
| `EXACT_RESOLVED_BEHAVIOR` | `BinaryLaw`, `BinaryLaw.Valid`, `ExactEquivalent` |
| `ACCESS_SPECIFICATION` | `AccessSpec`, `PureForgetting` |
| `EXPERIMENT_TRANSFORMATION` | `TransformCommand`, `AccessSpec.admits`, `ResponseTable` |
| derived behavioral quotient/equivalence | `OperationalSignature`, `BehaviorEquivalent` |
| `EXPLICIT_ALIGNMENT_INPUT` | `JointLaw`, `JointLaw.marginalA`, `JointLaw.marginalB` |
| `REALIZABILITY_DOMAIN_CERTIFICATE` | `RealizabilityCertificate.Valid` |
| `EXACT_EQUALITY_BOUNDARY` | Lean propositional equality over the exact finite structures |

The current probability representation uses exact quarter units because every first
formal milestone countermodel only needs masses in `{0, 1/4, 1/2, 3/4, 1}`. This is a
bounded theorem model, not a claim that quarter-valued probability is fundamental.

## Mechanically checked first milestone

`RelayTheory.Countermodels.finiteCore_countermodel_bundle` checks together that:

1. equal support does not imply equal exact law;
2. an unresolved selectable response family is not one resolved law;
3. visible information changes transform admissibility;
4. behavioral equivalence is derived from exact public signature;
5. pure observational forgetting composes;
6. equal one-context marginals do not determine the exact joint alignment;
7. realizability certificate validation is exact and fail-closed.

The CI lane builds only this Lake project, runs Lean's environment checker through
`lean-action`, and runs `axiom-audit`. Accepted theorem surface must not depend on
`sorry`, `native_decide`, or home-grown axioms.

Markov / FinStoch reconstruction is intentionally downstream. No Mathlib, category,
MDP, SCM, game, or product-runtime dependency is imported here.
