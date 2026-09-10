import RelayTheory.QuotientWitnessDeterminacy

namespace RelayTheory

namespace FinKernel

/-- Extract one target coordinate of a downstream kernel as a one-output kernel. -/
def column {q r : Nat} (h : FinKernel q r) (z : Fin r) : FinKernel q 1 :=
  fun y _ => h y z

/-- One-output continuations suffice for the scalar cancellation test. -/
def ScalarObservationEpic {a q : Nat} (obs : FinKernel a q) : Prop :=
  ∀ h₁ h₂ : FinKernel q 1,
    compose h₁ obs = compose h₂ obs → h₁ = h₂

/-- Zero scalar continuation used to expose unreachable observation states. -/
def zeroScalar (q : Nat) : FinKernel q 1 :=
  fun _ _ => 0

/-- Indicator scalar continuation for one selected observation state. -/
def indicatorScalar {q : Nat} (target : Fin q) : FinKernel q 1 :=
  fun y _ => if y = target then 1 else 0

end FinKernel

/-- Column extraction commutes exactly with precomposition by an observation. -/
theorem finKernel_column_compose_eval {a q r : Nat}
    (obs : FinKernel a q) (h : FinKernel q r)
    (z : Fin r) (x : Fin a) (u : Fin 1) :
    FinKernel.compose (FinKernel.column h z) obs x u =
      FinKernel.compose h obs x z := by
  rfl

/-- Full observation epicity immediately implies scalar observation epicity. -/
theorem finKernel_observationEpic_to_scalar {a q : Nat}
    {obs : FinKernel a q}
    (hepic : FinKernel.ObservationEpic obs) :
    FinKernel.ScalarObservationEpic obs := by
  intro h₁ h₂ hEq
  exact hepic h₁ h₂ hEq

/--
Scalar cancellation is complete: arbitrary downstream kernels are recovered one
column at a time, so one-output tests imply full observation epicity.
-/
theorem finKernel_scalar_to_observationEpic {a q : Nat}
    {obs : FinKernel a q}
    (hscalar : FinKernel.ScalarObservationEpic obs) :
    FinKernel.ObservationEpic obs := by
  intro r h₁ h₂ hEq
  funext y z
  have hcolEq :
      FinKernel.compose (FinKernel.column h₁ z) obs =
        FinKernel.compose (FinKernel.column h₂ z) obs := by
    funext x u
    rw [finKernel_column_compose_eval, finKernel_column_compose_eval]
    exact congrFun (congrFun hEq x) z
  have hc := hscalar
    (FinKernel.column h₁ z) (FinKernel.column h₂ z) hcolEq
  have hv := congrFun (congrFun hc y) (0 : Fin 1)
  exact hv

/-- Exact quantifier reduction: scalar and arbitrary downstream cancellation coincide. -/
theorem finKernel_observationEpic_iff_scalar {a q : Nat}
    {obs : FinKernel a q} :
    FinKernel.ObservationEpic obs ↔ FinKernel.ScalarObservationEpic obs := by
  constructor
  · exact finKernel_observationEpic_to_scalar
  · exact finKernel_scalar_to_observationEpic

/-- Exact identity observation is epic. -/
theorem finKernel_identity_observationEpic (n : Nat) :
    FinKernel.ObservationEpic (FinKernel.identity n) := by
  intro r h₁ h₂ hEq
  rw [finKernel_compose_identity_before,
    finKernel_compose_identity_before] at hEq
  exact hEq

/-- Observation epicity is closed under exact sequential composition. -/
theorem finKernel_observationEpic_compose {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hA : FinKernel.ObservationEpic obsA)
    (hB : FinKernel.ObservationEpic obsB) :
    FinKernel.ObservationEpic (FinKernel.compose obsB obsA) := by
  intro t h₁ h₂ hEq
  have hEqA :
      FinKernel.compose (FinKernel.compose h₁ obsB) obsA =
        FinKernel.compose (FinKernel.compose h₂ obsB) obsA := by
    calc
      FinKernel.compose (FinKernel.compose h₁ obsB) obsA =
          FinKernel.compose h₁ (FinKernel.compose obsB obsA) :=
        (finKernel_compose_associative obsA obsB h₁).symm
      _ = FinKernel.compose h₂ (FinKernel.compose obsB obsA) := hEq
      _ = FinKernel.compose (FinKernel.compose h₂ obsB) obsA :=
        finKernel_compose_associative obsA obsB h₂
  have hEqB : FinKernel.compose h₁ obsB = FinKernel.compose h₂ obsB :=
    hA (FinKernel.compose h₁ obsB) (FinKernel.compose h₂ obsB) hEqA
  exact hB h₁ h₂ hEqB

/-- The zero scalar and a selected-state indicator are distinct. -/
theorem finKernel_zeroScalar_ne_indicator {q : Nat} (target : Fin q) :
    FinKernel.zeroScalar q ≠ FinKernel.indicatorScalar target := by
  intro h
  have hv := congrFun (congrFun h target) (0 : Fin 1)
  simp [FinKernel.zeroScalar, FinKernel.indicatorScalar] at hv

/--
If a deterministic observation misses one target state, the zero scalar and that
state's indicator become observationally identical after the Dirac map.
-/
theorem finKernel_missing_state_scalar_collision
    {a q : Nat} (f : Fin a → Fin q) (target : Fin q)
    (hmissing : ¬ ∃ x : Fin a, f x = target) :
    FinKernel.compose (FinKernel.zeroScalar q) (FinKernel.dirac f) =
      FinKernel.compose (FinKernel.indicatorScalar target) (FinKernel.dirac f) := by
  funext x u
  rw [finKernel_compose_after_dirac_eval,
    finKernel_compose_after_dirac_eval]
  have hne : f x ≠ target := by
    intro h
    exact hmissing ⟨x, h⟩
  simp [FinKernel.zeroScalar, FinKernel.indicatorScalar, hne]

/-- Epicity of a deterministic observation forces surjectivity of its map. -/
theorem finKernel_dirac_observationEpic_surjective
    {a q : Nat} (f : Fin a → Fin q)
    (hepic : FinKernel.ObservationEpic (FinKernel.dirac f)) :
    ∀ y : Fin q, ∃ x : Fin a, f x = y := by
  intro y
  apply Classical.byContradiction
  intro hmissing
  have hsame := finKernel_missing_state_scalar_collision f y hmissing
  have heq : FinKernel.zeroScalar q = FinKernel.indicatorScalar y :=
    hepic (FinKernel.zeroScalar q) (FinKernel.indicatorScalar y) hsame
  exact finKernel_zeroScalar_ne_indicator y heq

/--
For deterministic finite observations, exact quotient-witness determinacy is
precisely ordinary surjectivity of the underlying finite map.
-/
theorem finKernel_dirac_observationEpic_iff_surjective
    {a q : Nat} (f : Fin a → Fin q) :
    FinKernel.ObservationEpic (FinKernel.dirac f) ↔
      (∀ y : Fin q, ∃ x : Fin a, f x = y) := by
  constructor
  · exact finKernel_dirac_observationEpic_surjective f
  · exact finKernel_dirac_surjective_observationEpic f

/-- The fair stochastic observation also fails the reduced scalar test. -/
theorem finFairKernel_not_scalarObservationEpic :
    ¬ FinKernel.ScalarObservationEpic finFairKernel := by
  intro hscalar
  exact finFairKernel_not_observationEpic
    (finKernel_scalar_to_observationEpic hscalar)

/-- The genuinely stochastic noisy epic observation passes the reduced scalar test. -/
theorem finNoisyEpic2_scalarObservationEpic :
    FinKernel.ScalarObservationEpic finNoisyEpic2 :=
  finKernel_observationEpic_to_scalar finNoisyEpic2_observationEpic

/-- Acceptance bundle for scalar epicity reduction and deterministic sharpness. -/
theorem finKernel_scalar_epicity_reduction_bundle :
    (∀ {a q : Nat} {obs : FinKernel a q},
      FinKernel.ObservationEpic obs ↔ FinKernel.ScalarObservationEpic obs) ∧
    (∀ {a q : Nat} (f : Fin a → Fin q),
      FinKernel.ObservationEpic (FinKernel.dirac f) ↔
        (∀ y : Fin q, ∃ x : Fin a, f x = y)) ∧
    (¬ FinKernel.ScalarObservationEpic finFairKernel) ∧
    FinKernel.ScalarObservationEpic finNoisyEpic2 := by
  exact ⟨finKernel_observationEpic_iff_scalar,
    finKernel_dirac_observationEpic_iff_surjective,
    finFairKernel_not_scalarObservationEpic,
    finNoisyEpic2_scalarObservationEpic⟩

end RelayTheory
