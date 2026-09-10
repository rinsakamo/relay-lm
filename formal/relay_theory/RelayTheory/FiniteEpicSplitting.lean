import RelayTheory.FiniteMonicSplitting

namespace RelayTheory

namespace FinKernel

/-- Representation-local transpose of an exact finite rational kernel. -/
def transpose {a q : Nat} (k : FinKernel a q) : FinKernel q a :=
  fun y x => k x y

/-- Exact section/right-inverse interface, dual to `HasExactRecovery`. -/
def HasExactSection {a q : Nat} (obs : FinKernel a q) : Prop :=
  ∃ sec : FinKernel q a,
    compose obs sec = identity q

end FinKernel

@[simp] theorem finKernel_transpose_apply
    {a q : Nat} (k : FinKernel a q) (y : Fin q) (x : Fin a) :
    FinKernel.transpose k y x = k x y := by
  rfl

@[simp] theorem finKernel_transpose_transpose
    {a q : Nat} (k : FinKernel a q) :
    FinKernel.transpose (FinKernel.transpose k) = k := by
  rfl

/-- Transpose fixes the exact identity kernel. -/
theorem finKernel_transpose_identity (n : Nat) :
    FinKernel.transpose (FinKernel.identity n) = FinKernel.identity n := by
  funext x y
  simp [FinKernel.transpose, FinKernel.identity, eq_comm]

/-- Exact transpose reverses sequential composition. -/
theorem finKernel_transpose_compose
    {a q r : Nat} (obsA : FinKernel a q) (obsB : FinKernel q r) :
    FinKernel.transpose (FinKernel.compose obsB obsA) =
      FinKernel.compose (FinKernel.transpose obsA) (FinKernel.transpose obsB) := by
  funext z x
  unfold FinKernel.transpose FinKernel.compose
  apply sumFin_congr
  intro y
  grind

/-- Epic cancellation becomes monic cancellation under exact transpose. -/
theorem finKernel_observationEpic_to_transpose_observationMonic
    {a q : Nat} {obs : FinKernel a q}
    (hepic : FinKernel.ObservationEpic obs) :
    FinKernel.ObservationMonic (FinKernel.transpose obs) := by
  intro t h₁ h₂ hEq
  have hEqT := congrArg (fun k => FinKernel.transpose k) hEq
  rw [finKernel_transpose_compose, finKernel_transpose_compose,
    finKernel_transpose_transpose] at hEqT
  have hT : FinKernel.transpose h₁ = FinKernel.transpose h₂ :=
    hepic (FinKernel.transpose h₁) (FinKernel.transpose h₂) hEqT
  have hTT := congrArg (fun k => FinKernel.transpose k) hT
  simpa using hTT

/-- Monic cancellation of the transpose reflects back to epic cancellation. -/
theorem finKernel_transpose_observationMonic_to_observationEpic
    {a q : Nat} {obs : FinKernel a q}
    (hmonic : FinKernel.ObservationMonic (FinKernel.transpose obs)) :
    FinKernel.ObservationEpic obs := by
  intro r h₁ h₂ hEq
  have hEqT := congrArg (fun k => FinKernel.transpose k) hEq
  rw [finKernel_transpose_compose, finKernel_transpose_compose] at hEqT
  have hT : FinKernel.transpose h₁ = FinKernel.transpose h₂ :=
    hmonic (FinKernel.transpose h₁) (FinKernel.transpose h₂) hEqT
  have hTT := congrArg (fun k => FinKernel.transpose k) hT
  simpa using hTT

/-- Exact finite epicity is precisely monicity of the transpose. -/
theorem finKernel_observationEpic_iff_transpose_observationMonic
    {a q : Nat} {obs : FinKernel a q} :
    FinKernel.ObservationEpic obs ↔
      FinKernel.ObservationMonic (FinKernel.transpose obs) := by
  constructor
  · exact finKernel_observationEpic_to_transpose_observationMonic
  · exact finKernel_transpose_observationMonic_to_observationEpic

/-- Exact section of a kernel is exact recovery of its transpose. -/
theorem finKernel_hasExactSection_iff_transpose_hasExactRecovery
    {a q : Nat} {obs : FinKernel a q} :
    FinKernel.HasExactSection obs ↔
      FinKernel.HasExactRecovery (FinKernel.transpose obs) := by
  constructor
  · rintro ⟨sec, hsection⟩
    refine ⟨FinKernel.transpose sec, ?_⟩
    have hT := congrArg (fun k => FinKernel.transpose k) hsection
    rw [finKernel_transpose_compose, finKernel_transpose_identity] at hT
    exact hT
  · rintro ⟨recovery, hrecovery⟩
    refine ⟨FinKernel.transpose recovery, ?_⟩
    have hT := congrArg (fun k => FinKernel.transpose k) hrecovery
    rw [finKernel_transpose_compose, finKernel_transpose_transpose,
      finKernel_transpose_identity] at hT
    exact hT

/-- Any explicit exact section gives universal epic/right cancellation. -/
theorem finKernel_hasExactSection_to_observationEpic
    {a q : Nat} {obs : FinKernel a q}
    (hsection : FinKernel.HasExactSection obs) :
    FinKernel.ObservationEpic obs := by
  rcases hsection with ⟨sec, hright⟩
  intro r h₁ h₂ hEq
  calc
    h₁ = FinKernel.compose h₁ (FinKernel.identity q) :=
      (finKernel_compose_identity_before h₁).symm
    _ = FinKernel.compose h₁ (FinKernel.compose obs sec) := by
      rw [hright]
    _ = FinKernel.compose (FinKernel.compose h₁ obs) sec :=
      finKernel_compose_associative sec obs h₁
    _ = FinKernel.compose (FinKernel.compose h₂ obs) sec := by
      rw [hEq]
    _ = FinKernel.compose h₂ (FinKernel.compose obs sec) :=
      (finKernel_compose_associative sec obs h₂).symm
    _ = FinKernel.compose h₂ (FinKernel.identity q) := by
      rw [hright]
    _ = h₂ := finKernel_compose_identity_before h₂

/--
Finite rational epicity splits exactly: transpose converts epicity to monicity,
#2513 splits the transpose, and transposing the recovery gives a section.
-/
theorem finKernel_observationEpic_to_hasExactSection
    {a q : Nat} (obs : FinKernel a q)
    (hepic : FinKernel.ObservationEpic obs) :
    FinKernel.HasExactSection obs := by
  have hmonicT : FinKernel.ObservationMonic (FinKernel.transpose obs) :=
    finKernel_observationEpic_to_transpose_observationMonic hepic
  have hrecoveryT :
      FinKernel.HasExactRecovery (FinKernel.transpose obs) :=
    finKernel_observationMonic_to_hasExactRecovery q a
      (FinKernel.transpose obs) hmonicT
  exact (finKernel_hasExactSection_iff_transpose_hasExactRecovery).2 hrecoveryT

/-- In the exact finite rational kernel category, epicity is exactly split epicity. -/
theorem finKernel_observationEpic_iff_hasExactSection
    {a q : Nat} {obs : FinKernel a q} :
    FinKernel.ObservationEpic obs ↔ FinKernel.HasExactSection obs := by
  constructor
  · exact finKernel_observationEpic_to_hasExactSection obs
  · exact finKernel_hasExactSection_to_observationEpic

/--
Concrete finite rational balancedness: simultaneous epic and monic cancellation
is exactly existence of a two-sided exact inverse.
-/
theorem finKernel_epic_and_monic_iff_twoSidedExactInverse
    {a q : Nat} {obs : FinKernel a q} :
    (FinKernel.ObservationEpic obs ∧ FinKernel.ObservationMonic obs) ↔
      ∃ inverse : FinKernel q a,
        FinKernel.compose inverse obs = FinKernel.identity a ∧
        FinKernel.compose obs inverse = FinKernel.identity q := by
  constructor
  · rintro ⟨hepic, hmonic⟩
    have hrecovery : FinKernel.HasExactRecovery obs :=
      finKernel_observationMonic_to_hasExactRecovery a q obs hmonic
    exact finKernel_observationEpic_exactRecovery_twoSided hepic hrecovery
  · rintro ⟨inverse, hleft, hright⟩
    constructor
    · exact finKernel_hasExactSection_to_observationEpic ⟨inverse, hright⟩
    · exact finKernel_hasExactRecovery_to_observationMonic ⟨inverse, hleft⟩

/-- Epic binary discard splits exactly despite not being monic/invertible. -/
theorem finKernel_discard_two_hasExactSection :
    FinKernel.HasExactSection (FinKernel.discard 2) :=
  finKernel_observationEpic_to_hasExactSection
    (FinKernel.discard 2) finKernel_discard_two_observationEpic

/-- The fair monic observation has no exact section because it is not epic. -/
theorem finFairKernel_not_hasExactSection :
    ¬ FinKernel.HasExactSection finFairKernel := by
  intro hsection
  exact finFairKernel_not_observationEpic
    (finKernel_hasExactSection_to_observationEpic hsection)

/-- The noisy epic+monic fixture has a two-sided exact inverse. -/
theorem finNoisyEpic2_hasTwoSidedExactInverse :
    ∃ inverse : FinKernel 2 2,
      FinKernel.compose inverse finNoisyEpic2 = FinKernel.identity 2 ∧
      FinKernel.compose finNoisyEpic2 inverse = FinKernel.identity 2 :=
  finKernel_observationEpic_exactRecovery_twoSided
    finNoisyEpic2_observationEpic finNoisyEpic2_hasExactRecovery

/--
Acceptance bundle retaining one-sided and stochastic-valid distinctions while
exposing finite rational epic splitting and balancedness.
-/
theorem finKernel_finite_epic_splitting_balancedness_bundle :
    (∀ {a q : Nat} {obs : FinKernel a q},
      FinKernel.ObservationEpic obs ↔ FinKernel.HasExactSection obs) ∧
    (∀ {a q : Nat} {obs : FinKernel a q},
      (FinKernel.ObservationEpic obs ∧ FinKernel.ObservationMonic obs) ↔
        ∃ inverse : FinKernel q a,
          FinKernel.compose inverse obs = FinKernel.identity a ∧
          FinKernel.compose obs inverse = FinKernel.identity q) ∧
    FinKernel.HasExactSection (FinKernel.discard 2) ∧
    (¬ FinKernel.ObservationMonic (FinKernel.discard 2)) ∧
    FinKernel.ObservationMonic finFairKernel ∧
    (¬ FinKernel.HasExactSection finFairKernel) ∧
    (∃ inverse : FinKernel 2 2,
      FinKernel.compose inverse finNoisyEpic2 = FinKernel.identity 2 ∧
      FinKernel.compose finNoisyEpic2 inverse = FinKernel.identity 2) ∧
    (¬ FinKernel.HasValidStochasticRecovery finNoisyEpic2) ∧
    FinKernel.HasValidStochasticRecovery (FinKernel.dirac finFlip2) := by
  exact ⟨finKernel_observationEpic_iff_hasExactSection,
    finKernel_epic_and_monic_iff_twoSidedExactInverse,
    finKernel_discard_two_hasExactSection,
    finKernel_discard_two_not_observationMonic,
    finFairKernel_observationMonic,
    finFairKernel_not_hasExactSection,
    finNoisyEpic2_hasTwoSidedExactInverse,
    finNoisyEpic2_not_hasValidStochasticRecovery,
    finFlip2_dirac_hasValidStochasticRecovery⟩

end RelayTheory
