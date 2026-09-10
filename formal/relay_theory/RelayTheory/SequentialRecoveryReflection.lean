import RelayTheory.DiracRecoverySharpness

namespace RelayTheory

/-- Exact recovery of finite kernels is closed under sequential composition. -/
theorem finKernel_hasExactRecovery_compose
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hA : FinKernel.HasExactRecovery obsA)
    (hB : FinKernel.HasExactRecovery obsB) :
    FinKernel.HasExactRecovery (FinKernel.compose obsB obsA) := by
  rcases hA with ⟨recoveryA, hrecA⟩
  rcases hB with ⟨recoveryB, hrecB⟩
  refine ⟨FinKernel.compose recoveryA recoveryB, ?_⟩
  calc
    FinKernel.compose (FinKernel.compose recoveryA recoveryB)
        (FinKernel.compose obsB obsA) =
      FinKernel.compose recoveryA
        (FinKernel.compose recoveryB (FinKernel.compose obsB obsA)) := by
          rw [finKernel_compose_associative obsA obsB recoveryB]
          exact (finKernel_compose_associative
            obsA (FinKernel.compose recoveryB obsB) recoveryA).symm
    _ = FinKernel.compose recoveryA
        (FinKernel.compose (FinKernel.compose recoveryB obsB) obsA) := by
          rw [finKernel_compose_associative obsA obsB recoveryB]
    _ = FinKernel.compose recoveryA
        (FinKernel.compose (FinKernel.identity q) obsA) := by
          rw [hrecB]
    _ = FinKernel.compose recoveryA obsA := by
          rw [finKernel_compose_identity_after obsA]
    _ = FinKernel.identity a := hrecA

/--
Exact recoverability of a composite always reflects to its earlier factor.
No stochastic-validity premise is required.
-/
theorem finKernel_hasExactRecovery_compose_reflect_earlier
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hcomp : FinKernel.HasExactRecovery (FinKernel.compose obsB obsA)) :
    FinKernel.HasExactRecovery obsA := by
  rcases hcomp with ⟨recovery, hrec⟩
  refine ⟨FinKernel.compose recovery obsB, ?_⟩
  calc
    FinKernel.compose (FinKernel.compose recovery obsB) obsA =
        FinKernel.compose recovery (FinKernel.compose obsB obsA) :=
      (finKernel_compose_associative obsA obsB recovery).symm
    _ = FinKernel.identity a := hrec

/-- Every identity kernel has an exact recovery, namely itself. -/
theorem finKernel_identity_hasExactRecovery (n : Nat) :
    FinKernel.HasExactRecovery (FinKernel.identity n) := by
  exact ⟨FinKernel.identity n,
    finKernel_compose_identity_after (FinKernel.identity n)⟩

/-- On the singleton interface, discard is exactly identity. -/
theorem finKernel_discard_one_eq_identity :
    FinKernel.discard 1 = FinKernel.identity 1 := by
  change FinKernel.dirac (@finDiscardFn 1) =
    FinKernel.dirac (fun x : Fin 1 => x)
  apply finKernel_dirac_congr
  intro x
  exact (fin_one_eq_zero x).symm

/--
The injective `Fin 1 -> Fin 2` control followed by binary discard is exactly the
singleton identity.
-/
theorem finInjectOneToTwo_then_discard_eq_identity :
    FinKernel.compose (FinKernel.discard 2)
        (FinKernel.dirac finInjectOneToTwo) =
      FinKernel.identity 1 := by
  calc
    FinKernel.compose (FinKernel.discard 2)
        (FinKernel.dirac finInjectOneToTwo) = FinKernel.discard 1 :=
      finKernel_discard_causal (finKernel_dirac_valid finInjectOneToTwo)
    _ = FinKernel.identity 1 := finKernel_discard_one_eq_identity

/--
A valid deterministic counterexample: the composite is exactly recoverable but
the later binary discard is not.  Thus composite recovery does not in general
reflect to the later factor.
-/
theorem finKernel_recoverable_composite_not_later_recoverable_bundle :
    FinKernel.Valid (FinKernel.dirac finInjectOneToTwo) ∧
    FinKernel.Valid (FinKernel.discard 2) ∧
    FinKernel.HasExactRecovery
      (FinKernel.compose (FinKernel.discard 2)
        (FinKernel.dirac finInjectOneToTwo)) ∧
    (¬ FinKernel.HasExactRecovery (FinKernel.discard 2)) := by
  refine ⟨finKernel_dirac_valid finInjectOneToTwo,
    finKernel_discard_valid 2, ?_, finKernel_discard_two_not_hasExactRecovery⟩
  rw [finInjectOneToTwo_then_discard_eq_identity]
  exact finKernel_identity_hasExactRecovery 1

/--
Earlier-factor epicity restores reflection of exact recoverability to the later
factor.  No validity premise is needed.
-/
theorem finKernel_hasExactRecovery_compose_reflect_later_of_earlier_epic
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hcomp : FinKernel.HasExactRecovery (FinKernel.compose obsB obsA))
    (hepicA : FinKernel.ObservationEpic obsA) :
    FinKernel.HasExactRecovery obsB := by
  rcases hcomp with ⟨recovery, hrec⟩
  refine ⟨FinKernel.compose obsA recovery, ?_⟩
  apply hepicA
    (FinKernel.compose (FinKernel.compose obsA recovery) obsB)
    (FinKernel.identity q)
  calc
    FinKernel.compose
        (FinKernel.compose (FinKernel.compose obsA recovery) obsB) obsA =
      FinKernel.compose obsA
        (FinKernel.compose recovery (FinKernel.compose obsB obsA)) := by
          rw [← finKernel_compose_associative obsA obsB
            (FinKernel.compose obsA recovery)]
          exact (finKernel_compose_associative
            (FinKernel.compose obsB obsA) recovery obsA).symm
    _ = FinKernel.compose obsA (FinKernel.identity a) := by
          rw [hrec]
    _ = obsA := finKernel_compose_identity_before obsA
    _ = FinKernel.compose (FinKernel.identity q) obsA :=
          (finKernel_compose_identity_after obsA).symm

/--
If the earlier factor of a recoverable composite is epic, then it is both
recoverable and epic, so its recovery upgrades to a two-sided exact inverse.
This reuses the generic upgrade theorem from #2503.
-/
theorem finKernel_recoverable_composite_earlier_epic_twoSided
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hcomp : FinKernel.HasExactRecovery (FinKernel.compose obsB obsA))
    (hepicA : FinKernel.ObservationEpic obsA) :
    ∃ recoveryA : FinKernel q a,
      FinKernel.compose recoveryA obsA = FinKernel.identity a ∧
      FinKernel.compose obsA recoveryA = FinKernel.identity q := by
  exact finKernel_observationEpic_exactRecovery_twoSided hepicA
    (finKernel_hasExactRecovery_compose_reflect_earlier hcomp)

/--
Acceptance package for directional sequential exact-recovery reflection.
-/
theorem finKernel_sequential_recovery_reflection_bundle :
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.HasExactRecovery obsA →
      FinKernel.HasExactRecovery obsB →
        FinKernel.HasExactRecovery (FinKernel.compose obsB obsA)) ∧
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.HasExactRecovery (FinKernel.compose obsB obsA) →
        FinKernel.HasExactRecovery obsA) ∧
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.HasExactRecovery (FinKernel.compose obsB obsA) →
      FinKernel.ObservationEpic obsA →
        FinKernel.HasExactRecovery obsB) ∧
    FinKernel.HasExactRecovery
      (FinKernel.compose (FinKernel.discard 2)
        (FinKernel.dirac finInjectOneToTwo)) ∧
    (¬ FinKernel.HasExactRecovery (FinKernel.discard 2)) := by
  exact ⟨finKernel_hasExactRecovery_compose,
    finKernel_hasExactRecovery_compose_reflect_earlier,
    finKernel_hasExactRecovery_compose_reflect_later_of_earlier_epic,
    finKernel_recoverable_composite_not_later_recoverable_bundle.2.2.1,
    finKernel_discard_two_not_hasExactRecovery⟩

end RelayTheory
