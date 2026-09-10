import RelayTheory.KernelObservationMonoidal

namespace RelayTheory

namespace FinKernel

/--
Exact cancellation property of an observation channel: post-observation dynamics
are determined uniquely by their concrete composite through this observation.
-/
def ObservationEpic {a q : Nat} (obs : FinKernel a q) : Prop :=
  ∀ {r : Nat} (h₁ h₂ : FinKernel q r),
    compose h₁ obs = compose h₂ obs → h₁ = h₂

end FinKernel

/-- Epicity makes any two explicit quotient witnesses for one square equal. -/
theorem finKernel_factorWitness_unique_of_observationEpic
    {a b qa qb : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    {k : FinKernel a b}
    (hepic : FinKernel.ObservationEpic obsA)
    {h₁ h₂ : FinKernel qa qb}
    (h₁Eq : FinKernel.compose obsB k = FinKernel.compose h₁ obsA)
    (h₂Eq : FinKernel.compose obsB k = FinKernel.compose h₂ obsA) :
    h₁ = h₂ := by
  apply hepic h₁ h₂
  exact h₁Eq.symm.trans h₂Eq

/--
An existing factorization through an epic source observation upgrades from
existence to a unique quotient witness.  The uniqueness packaging is written
explicitly rather than relying on additional parser/library notation.
-/
theorem finKernel_kernelObservationFactors_existsUnique
    {a b qa qb : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    {k : FinKernel a b}
    (hepic : FinKernel.ObservationEpic obsA)
    (hk : FinKernel.KernelObservationFactors obsA obsB k) :
    ∃ h : FinKernel qa qb,
      FinKernel.compose obsB k = FinKernel.compose h obsA ∧
      ∀ h' : FinKernel qa qb,
        FinKernel.compose obsB k = FinKernel.compose h' obsA → h' = h := by
  rcases hk with ⟨h, hEq⟩
  refine ⟨h, hEq, ?_⟩
  intro h' h'Eq
  exact finKernel_factorWitness_unique_of_observationEpic
    hepic h'Eq hEq

/--
Every surjective deterministic observation is epic for arbitrary exact finite
kernel continuations.
-/
theorem finKernel_dirac_surjective_observationEpic
    {a q : Nat} (f : Fin a → Fin q)
    (hsurj : ∀ y : Fin q, ∃ x : Fin a, f x = y) :
    FinKernel.ObservationEpic (FinKernel.dirac f) := by
  intro r h₁ h₂ hEq
  funext y z
  rcases hsurj y with ⟨x, hx⟩
  have hv := congrFun (congrFun hEq x) z
  rw [finKernel_compose_after_dirac_eval,
    finKernel_compose_after_dirac_eval] at hv
  simpa [hx] using hv

/-- Every point of `Fin 2` is one of the two canonical points. -/
theorem finTwo_zero_or_one (x : Fin 2) :
    x = (0 : Fin 2) ∨ x = (1 : Fin 2) := by
  have hx := x.isLt
  have hv : x.val = 0 ∨ x.val = 1 := by
    grind
  rcases hv with h0 | h1
  · left
    apply Fin.ext
    simpa using h0
  · right
    apply Fin.ext
    simpa using h1

/-- Deterministic flip of the two-point finite interface. -/
def finFlip2 (x : Fin 2) : Fin 2 :=
  if x = (0 : Fin 2) then (1 : Fin 2) else (0 : Fin 2)

/-- Identity and binary flip are genuinely distinct exact kernels. -/
theorem finKernel_identity_two_ne_flip :
    FinKernel.identity 2 ≠ FinKernel.dirac finFlip2 := by
  intro h
  have hv := congrFun (congrFun h (0 : Fin 2)) (0 : Fin 2)
  simp [FinKernel.identity, FinKernel.dirac, finFlip2] at hv

/-- The uniform fair observation is invariant under downstream binary flip. -/
theorem finKernel_flip_after_fair :
    FinKernel.compose (FinKernel.dirac finFlip2) finFairKernel =
      finFairKernel := by
  funext x z
  rcases finTwo_zero_or_one z with hz | hz
  · subst z
    grind [FinKernel.compose, sumFin, FinKernel.dirac,
      finFlip2, finFairKernel, qHalf]
  · subst z
    grind [FinKernel.compose, sumFin, FinKernel.dirac,
      finFlip2, finFairKernel, qHalf]

/--
Two distinct valid downstream kernels are observationally identical after the
fair stochastic observation.
-/
theorem finFairKernel_valid_witness_ambiguity :
    FinKernel.Valid (FinKernel.identity 2) ∧
    FinKernel.Valid (FinKernel.dirac finFlip2) ∧
    FinKernel.identity 2 ≠ FinKernel.dirac finFlip2 ∧
    FinKernel.compose (FinKernel.identity 2) finFairKernel =
      FinKernel.compose (FinKernel.dirac finFlip2) finFairKernel := by
  exact ⟨finKernel_identity_valid 2,
    finKernel_dirac_valid finFlip2,
    finKernel_identity_two_ne_flip,
    by rw [finKernel_compose_identity_after, finKernel_flip_after_fair]⟩

/-- The fair stochastic observation is not epic. -/
theorem finFairKernel_not_observationEpic :
    ¬ FinKernel.ObservationEpic finFairKernel := by
  intro hepic
  rcases finFairKernel_valid_witness_ambiguity with
    ⟨_, _, hne, hsame⟩
  exact hne (hepic (FinKernel.identity 2) (FinKernel.dirac finFlip2) hsame)

/--
The identity factorization through the fair observation has two distinct valid
quotient-level witnesses. This is ambiguity inside the stochastic-valid slice.
-/
theorem finFairKernel_stochastic_factorization_has_two_valid_witnesses :
    ∃ h₁ h₂ : FinKernel 2 2,
      FinKernel.Valid h₁ ∧
      FinKernel.Valid h₂ ∧
      h₁ ≠ h₂ ∧
      FinKernel.compose finFairKernel (FinKernel.identity 1) =
        FinKernel.compose h₁ finFairKernel ∧
      FinKernel.compose finFairKernel (FinKernel.identity 1) =
        FinKernel.compose h₂ finFairKernel := by
  refine ⟨FinKernel.identity 2, FinKernel.dirac finFlip2,
    finKernel_identity_valid 2, finKernel_dirac_valid finFlip2,
    finKernel_identity_two_ne_flip, ?_, ?_⟩
  · rw [finKernel_compose_identity_before, finKernel_compose_identity_after]
  · rw [finKernel_compose_identity_before, finKernel_flip_after_fair]

/--
A genuinely stochastic binary observation with exact invertible mixing.
-/
def finNoisyEpic2 : FinKernel 2 2 :=
  fun x y => if x = y then qThreeQuarter else qQuarter

/-- The noisy binary observation is stochastic-valid. -/
theorem finNoisyEpic2_valid : FinKernel.Valid finNoisyEpic2 := by
  constructor
  · intro x y
    by_cases hxy : x = y
    · simpa [finNoisyEpic2, hxy] using Rat.le_of_lt qThreeQuarter_pos
    · simpa [finNoisyEpic2, hxy] using Rat.le_of_lt qQuarter_pos
  · intro x
    rcases finTwo_zero_or_one x with hx | hx
    · subst x
      grind [FinKernel.rowSum, finNoisyEpic2, sumFin,
        qThreeQuarter, qQuarter]
    · subst x
      grind [FinKernel.rowSum, finNoisyEpic2, sumFin,
        qThreeQuarter, qQuarter]

/-- The noisy binary observation is genuinely non-deterministic. -/
theorem finNoisyEpic2_not_deterministic :
    ¬ FinKernel.DeterministicKernel finNoisyEpic2 := by
  intro hdet
  have hcopy : FinKernel.PreservesCopy finNoisyEpic2 :=
    (finKernel_valid_preservesCopy_iff_deterministic finNoisyEpic2_valid).2 hdet
  have hd := finKernel_preservesCopy_diagonal
    hcopy (0 : Fin 2) (0 : Fin 2)
  have hq : qThreeQuarter = qThreeQuarter * qThreeQuarter := by
    simpa [finNoisyEpic2] using hd
  grind [qThreeQuarter]

/--
Despite being genuinely stochastic, the noisy binary observation is epic: its
two exact row equations determine every downstream coordinate uniquely.
-/
theorem finNoisyEpic2_observationEpic :
    FinKernel.ObservationEpic finNoisyEpic2 := by
  intro r h₁ h₂ hEq
  funext y z
  have h0 := congrFun (congrFun hEq (0 : Fin 2)) z
  have h1 := congrFun (congrFun hEq (1 : Fin 2)) z
  have h0eq :
      qThreeQuarter * h₁ (0 : Fin 2) z + qQuarter * h₁ (1 : Fin 2) z =
        qThreeQuarter * h₂ (0 : Fin 2) z + qQuarter * h₂ (1 : Fin 2) z := by
    simpa [FinKernel.compose, sumFin, finNoisyEpic2,
      Rat.add_zero, Rat.zero_add] using h0
  have h1eq :
      qQuarter * h₁ (0 : Fin 2) z + qThreeQuarter * h₁ (1 : Fin 2) z =
        qQuarter * h₂ (0 : Fin 2) z + qThreeQuarter * h₂ (1 : Fin 2) z := by
    simpa [FinKernel.compose, sumFin, finNoisyEpic2,
      Rat.add_zero, Rat.zero_add] using h1
  rcases finTwo_zero_or_one y with hy | hy
  · subst y
    grind [qThreeQuarter, qQuarter]
  · subst y
    grind [qThreeQuarter, qQuarter]

/--
Positive-control bundle: stochasticity does not preclude exact quotient-witness
determinacy.
-/
theorem finNoisyEpic2_stochastic_epic_bundle :
    FinKernel.Valid finNoisyEpic2 ∧
    (¬ FinKernel.DeterministicKernel finNoisyEpic2) ∧
    FinKernel.ObservationEpic finNoisyEpic2 := by
  exact ⟨finNoisyEpic2_valid,
    finNoisyEpic2_not_deterministic,
    finNoisyEpic2_observationEpic⟩

/--
Acceptance bundle separating factorization existence, witness determinacy, and
Markov-copy determinism.
-/
theorem finKernel_quotient_witness_determinacy_bundle :
    (¬ FinKernel.ObservationEpic finFairKernel) ∧
    FinKernel.Valid finNoisyEpic2 ∧
    (¬ FinKernel.DeterministicKernel finNoisyEpic2) ∧
    FinKernel.ObservationEpic finNoisyEpic2 := by
  exact ⟨finFairKernel_not_observationEpic,
    finNoisyEpic2_valid,
    finNoisyEpic2_not_deterministic,
    finNoisyEpic2_observationEpic⟩

end RelayTheory
