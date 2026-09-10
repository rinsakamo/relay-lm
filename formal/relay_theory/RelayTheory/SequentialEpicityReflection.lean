import RelayTheory.EpicityReversibility

namespace RelayTheory

/--
Epicity of a sequential composite reflects to its later factor.  No stochastic
validity hypothesis is required: this is pure exact cancellation plus
associativity.
-/
theorem finKernel_observationEpic_compose_reflect_later
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hcomp : FinKernel.ObservationEpic (FinKernel.compose obsB obsA)) :
    FinKernel.ObservationEpic obsB := by
  intro t h₁ h₂ hEq
  apply hcomp h₁ h₂
  calc
    FinKernel.compose h₁ (FinKernel.compose obsB obsA) =
        FinKernel.compose (FinKernel.compose h₁ obsB) obsA :=
      finKernel_compose_associative obsA obsB h₁
    _ = FinKernel.compose (FinKernel.compose h₂ obsB) obsA := by
      rw [hEq]
    _ = FinKernel.compose h₂ (FinKernel.compose obsB obsA) :=
      (finKernel_compose_associative obsA obsB h₂).symm

/-- On the one-point finite interface, structural discard is exactly identity. -/
theorem finKernel_discard_one_eq_identity :
    FinKernel.discard 1 = FinKernel.identity 1 := by
  rw [finKernel_discard_as_dirac 1, finKernel_identity_eq_dirac_id 1]
  apply finKernel_dirac_congr
  intro x
  change (0 : Fin 1) = x
  exact (fin_one_eq_zero x).symm

/-- Discard from the binary interface is epic: the unique target point is reached. -/
theorem finKernel_discard_two_observationEpic :
    FinKernel.ObservationEpic (FinKernel.discard 2) := by
  rw [finKernel_discard_as_dirac 2]
  apply (finKernel_dirac_observationEpic_iff_surjective (@finDiscardFn 2)).2
  intro y
  refine ⟨(0 : Fin 2), ?_⟩
  change (0 : Fin 1) = y
  exact (fin_one_eq_zero y).symm

/--
The valid fair observation followed by discard collapses exactly to the
one-point identity.
-/
theorem finFairKernel_then_discard_eq_identity :
    FinKernel.compose (FinKernel.discard 2) finFairKernel =
      FinKernel.identity 1 := by
  calc
    FinKernel.compose (FinKernel.discard 2) finFairKernel =
        FinKernel.discard 1 :=
      finKernel_discard_causal finFairKernel_valid
    _ = FinKernel.identity 1 := finKernel_discard_one_eq_identity

/-- The fair-then-discard composite is epic. -/
theorem finFairKernel_then_discard_observationEpic :
    FinKernel.ObservationEpic
      (FinKernel.compose (FinKernel.discard 2) finFairKernel) := by
  rw [finFairKernel_then_discard_eq_identity]
  exact finKernel_identity_observationEpic 1

/--
Concrete valid counterexample to reflection toward the earlier factor: the
composite is epic although the fair prefix is not.
-/
theorem finFairKernel_then_discard_non_epic_prefix_bundle :
    FinKernel.Valid finFairKernel ∧
    FinKernel.Valid (FinKernel.discard 2) ∧
    FinKernel.ObservationEpic
      (FinKernel.compose (FinKernel.discard 2) finFairKernel) ∧
    (¬ FinKernel.ObservationEpic finFairKernel) := by
  exact ⟨finFairKernel_valid,
    finKernel_discard_valid 2,
    finFairKernel_then_discard_observationEpic,
    finFairKernel_not_observationEpic⟩

/--
There is no general theorem reflecting composite epicity to the earlier factor.
The fair-then-discard valid witness refutes that universal statement exactly.
-/
theorem finKernel_observationEpic_compose_not_reflect_earlier :
    ¬ (∀ {a q r : Nat}
        (obsA : FinKernel a q) (obsB : FinKernel q r),
        FinKernel.ObservationEpic (FinKernel.compose obsB obsA) →
          FinKernel.ObservationEpic obsA) := by
  intro hreflect
  have hfair : FinKernel.ObservationEpic finFairKernel :=
    hreflect finFairKernel (FinKernel.discard 2)
      finFairKernel_then_discard_observationEpic
  exact finFairKernel_not_observationEpic hfair

/--
Directional sequential epicity calculus: closure holds forward; an epic
composite forces the later factor epic; reflection to the earlier factor fails.
-/
theorem finKernel_sequential_epicity_directional_bundle :
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.ObservationEpic obsA →
      FinKernel.ObservationEpic obsB →
      FinKernel.ObservationEpic (FinKernel.compose obsB obsA)) ∧
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.ObservationEpic (FinKernel.compose obsB obsA) →
      FinKernel.ObservationEpic obsB) ∧
    (¬ (∀ {a q r : Nat}
      (obsA : FinKernel a q) (obsB : FinKernel q r),
      FinKernel.ObservationEpic (FinKernel.compose obsB obsA) →
      FinKernel.ObservationEpic obsA)) := by
  exact ⟨finKernel_observationEpic_compose,
    finKernel_observationEpic_compose_reflect_later,
    finKernel_observationEpic_compose_not_reflect_earlier⟩

end RelayTheory
