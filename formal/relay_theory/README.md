# Relay Theory 0.1 — bounded Lean core

This directory is an isolated Lean 4 formalization lane for Relay Theory.
It is **not** a RelayLM runtime dependency and does not authorize changes to `v1` or `v2`.

The formalization intentionally follows already-earned finite Grand Null results. It does not
claim a universal probability ontology, a universal minimal axiom system, a global-world ontology,
or a category-theoretic foundation.

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
| `EXPLICIT_ALIGNMENT_INPUT` | `JointLaw`, `TripleLaw`, exact marginal projections |
| `REALIZABILITY_DOMAIN_CERTIFICATE` | `RealizabilityCertificate.Valid`, `PairContextFamily.RealizedBy` |
| derived finite stochastic slice | `BinaryKernel`, `PairKernel`, exact `Rat` composition/tensor/copy/discard |
| `EXACT_EQUALITY_BOUNDARY` | Lean propositional equality over the exact finite structures |

The first countermodel layers use exact quarter units because those witness families only need
masses in `{0, 1/4, 1/2, 3/4, 1}`. The derived stochastic-composition layer uses Lean core exact
`Rat`, because sequential composition and independent tensor need exact products such as `1/16`.
Neither representation is claimed fundamental.

## First formal milestone — #2403 / PR #2404

`RelayTheory.Countermodels.finiteCore_countermodel_bundle` mechanically checks that:

1. equal support does not imply equal exact law;
2. an unresolved selectable response family is not one resolved law;
3. visible information changes transform admissibility;
4. behavioral equivalence is derived from exact public signature;
5. pure observational forgetting composes;
6. equal one-context marginals do not determine the exact 2x2 joint alignment;
7. realizability certificate validation is exact and fail-closed.

## Higher-order alignment and gluing — #2413 / PR #2415

`RelayTheory.HigherOrder` ports the already-earned finite Grand Null results from #2374 and #2379
into the theorem surface.

The non-uniqueness witness uses exact even/odd parity triple laws. They have identical exact
marginals on all three binary pairs but unequal full triple joints, and a triple parity probe
separates them. Therefore pairwise alignment does not determine one unique higher-order joint.

The non-existence witness uses fair anti-correlation on all three local contexts `AB`, `BC`, and
`AC`. Each local pair law is valid and all singleton overlaps agree exactly, yet no binary triple
can realize all three pair laws simultaneously. Matched positive controls prove that the fair
equality triangle has an explicit global witness and that deleting one anti-correlation edge
restores an explicit global completion.

The bounded conclusions are only:

```text
same all pairwise data
  != unique global joint

locally valid + overlap-consistent pairwise data
  != guaranteed global joint existence
```

This does not solve the general marginal polytope, assume a sheaf/presheaf, or establish an
arbitrary `n`-world hierarchy.

## Earned finite stochastic slice — #2416

`RelayTheory.Stochastic` reconstructs the already-earned #2384 fully resolved stochastic slice
without importing category theory as a premise.

The module uses exact Lean `Rat` masses and mechanically defines/evaluates:

- binary stochastic kernels and exact sequential composition;
- exact identity and deterministic/Dirac kernels;
- bounded discard;
- deterministic classical-data copy, including coassociativity, cocommutativity, counit, and
  deterministic copy preservation;
- exact state-level shared-randomness copy versus independent tensor;
- exact independent tensor of binary kernels and bounded interchange with sequential composition.

The required negative control remains explicit:

```text
copy one fair random result
  !=
make two independent fair draws
```

while both resulting coordinate marginals are exactly fair.

The module also imports the already-formalized outer boundaries rather than hiding them inside a
stochastic arrow:

```text
unresolved selectable family != one resolved law
locally valid overlap-consistent pieces may have no global realization
```

The bounded result is therefore only a reconstructed **derived finite stochastic / Markov-like
slice**. It is not a theorem that Relay Theory itself is a Markov category.

## Proof / CI authority

The dedicated CI lane does not relax this repository's full-SHA action policy. It:

- installs `elan` from the official v4.2.4 Linux release asset and verifies its published SHA256;
- installs the toolchain declared by `lean-toolchain` (`leanprover/lean4:v4.33.1`);
- runs `lake build` only in this isolated project;
- runs the bundled `leanchecker` over `RelayTheory`;
- clones `leanprover-community/axiom-audit` v0.1.2, verifies exact commit
  `46024e005996495c65ef609368e11ab39c4222e3`, builds it with the project toolchain,
  and audits the compiled `RelayTheory` kernel environment.

Accepted theorem surfaces must not depend on `sorry`, `admit`, `native_decide`, or home-grown
substantive axioms. Universal FinStoch/category reconstruction, general symmetric-monoidal
coherence, arbitrary finite indexing, intervention/substitution algebra, and general gluing remain
downstream. No Mathlib, SCM, MDP, game, contextuality, sheaf, or product-runtime dependency is
imported here.
