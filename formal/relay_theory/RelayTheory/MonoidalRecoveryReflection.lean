import RelayTheory.FiniteEpicSplitting

namespace RelayTheory

/--
Tensoring on the right with an inhabited identity kernel is injective on exact
finite kernels.  This is the extraction step used for factor reflection.
-/
theorem finKernel_tensor_right_identity_cancel
    {a b c : Nat} (u : Fin c)
    {h₁ h₂ : FinKernel a b}
    (hEq :
      FinKernel.tensor h₁ (FinKernel.identity c) =
        FinKernel.tensor h₂ (FinKernel.identity c)) :
    h₁ = h₂ := by
  funext x y
  have hcoord := congrFun
    (congrFun hEq (finPairTransport.toFun (x, u)))
    (finPairTransport.toFun (y, u))
  simpa [FinKernel.identity, finPair_transport_roundtrip] using hcoord

/-- Left-hand version of identity-tensor cancellation. -/
theorem finKernel_tensor_left_identity_cancel
    {a b c : Nat} (u : Fin c)
    {h₁ h₂ : FinKernel a b}
    (hEq :
      FinKernel.tensor (FinKernel.identity c) h₁ =
        FinKernel.tensor (FinKernel.identity c) h₂) :
    h₁ = h₂ := by
  funext x y
  have hcoord := congrFun
    (congrFun hEq (finPairTransport.toFun (u, x)))
    (finPairTransport.toFun (u, y))
  simpa [FinKernel.identity, finPair_transport_roundtrip] using hcoord

/-- Exact one-sided recoverability is closed under independent tensor. -/
theorem finKernel_hasExactRecovery_tensor
    {a b c d : Nat}
    {obsA : FinKernel a b} {obsB : FinKernel c d}
    (hA : FinKernel.HasExactRecovery obsA)
    (hB : FinKernel.HasExactRecovery obsB) :
    FinKernel.HasExactRecovery (FinKernel.tensor obsA obsB) := by
  rcases hA with ⟨recoveryA, hrecA⟩
  rcases hB with ⟨recoveryB, hrecB⟩
  refine ⟨FinKernel.tensor recoveryA recoveryB, ?_⟩
  calc
    FinKernel.compose
        (FinKernel.tensor recoveryA recoveryB)
        (FinKernel.tensor obsA obsB) =
      FinKernel.tensor
        (FinKernel.compose recoveryA obsA)
        (FinKernel.compose recoveryB obsB) :=
          finKernel_tensor_interchange obsA recoveryA obsB recoveryB
    _ = FinKernel.tensor (FinKernel.identity a) (FinKernel.identity c) := by
      rw [hrecA, hrecB]
    _ = FinKernel.identity (a * c) := finKernel_tensor_identity a c

/-- Finite rational observation monicity is closed under independent tensor. -/
theorem finKernel_observationMonic_tensor
    {a b c d : Nat}
    {obsA : FinKernel a b} {obsB : FinKernel c d}
    (hA : FinKernel.ObservationMonic obsA)
    (hB : FinKernel.ObservationMonic obsB) :
    FinKernel.ObservationMonic (FinKernel.tensor obsA obsB) := by
  apply finKernel_hasExactRecovery_to_observationMonic
  exact finKernel_hasExactRecovery_tensor
    (finKernel_observationMonic_to_hasExactRecovery a b obsA hA)
    (finKernel_observationMonic_to_hasExactRecovery c d obsB hB)

/--
If the right source factor is inhabited, monicity of a tensor reflects to the
left factor.  A collision is lifted by tensoring it with the right identity.
-/
theorem finKernel_observationMonic_tensor_reflect_left
    {a b c d : Nat}
    {obsA : FinKernel a b} {obsB : FinKernel c d}
    (u : Fin c)
    (hTensor : FinKernel.ObservationMonic (FinKernel.tensor obsA obsB)) :
    FinKernel.ObservationMonic obsA := by
  intro t h₁ h₂ hEq
  have hLift :
      FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor h₁ (FinKernel.identity c)) =
        FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor h₂ (FinKernel.identity c)) := by
    calc
      FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor h₁ (FinKernel.identity c)) =
        FinKernel.tensor
          (FinKernel.compose obsA h₁)
          (FinKernel.compose obsB (FinKernel.identity c)) :=
            finKernel_tensor_interchange h₁ obsA (FinKernel.identity c) obsB
      _ = FinKernel.tensor
          (FinKernel.compose obsA h₂)
          (FinKernel.compose obsB (FinKernel.identity c)) := by
            rw [hEq]
      _ = FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor h₂ (FinKernel.identity c)) :=
            (finKernel_tensor_interchange h₂ obsA
              (FinKernel.identity c) obsB).symm
  have hTensorInputs :
      FinKernel.tensor h₁ (FinKernel.identity c) =
        FinKernel.tensor h₂ (FinKernel.identity c) :=
    hTensor
      (FinKernel.tensor h₁ (FinKernel.identity c))
      (FinKernel.tensor h₂ (FinKernel.identity c))
      hLift
  exact finKernel_tensor_right_identity_cancel u hTensorInputs

/-- Symmetric factor reflection when the left source factor is inhabited. -/
theorem finKernel_observationMonic_tensor_reflect_right
    {a b c d : Nat}
    {obsA : FinKernel a b} {obsB : FinKernel c d}
    (x : Fin a)
    (hTensor : FinKernel.ObservationMonic (FinKernel.tensor obsA obsB)) :
    FinKernel.ObservationMonic obsB := by
  intro t h₁ h₂ hEq
  have hLift :
      FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor (FinKernel.identity a) h₁) =
        FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor (FinKernel.identity a) h₂) := by
    calc
      FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor (FinKernel.identity a) h₁) =
        FinKernel.tensor
          (FinKernel.compose obsA (FinKernel.identity a))
          (FinKernel.compose obsB h₁) :=
            finKernel_tensor_interchange (FinKernel.identity a) obsA h₁ obsB
      _ = FinKernel.tensor
          (FinKernel.compose obsA (FinKernel.identity a))
          (FinKernel.compose obsB h₂) := by
            rw [hEq]
      _ = FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor (FinKernel.identity a) h₂) :=
            (finKernel_tensor_interchange (FinKernel.identity a) obsA
              h₂ obsB).symm
  have hTensorInputs :
      FinKernel.tensor (FinKernel.identity a) h₁ =
        FinKernel.tensor (FinKernel.identity a) h₂ :=
    hTensor
      (FinKernel.tensor (FinKernel.identity a) h₁)
      (FinKernel.tensor (FinKernel.identity a) h₂)
      hLift
  exact finKernel_tensor_left_identity_cancel x hTensorInputs

/--
With both source factors inhabited, exact recovery of a tensor is equivalent to
exact recovery of each factor.
-/
theorem finKernel_hasExactRecovery_tensor_iff_factors
    {a b c d : Nat}
    {obsA : FinKernel a b} {obsB : FinKernel c d}
    (x : Fin a) (u : Fin c) :
    FinKernel.HasExactRecovery (FinKernel.tensor obsA obsB) ↔
      (FinKernel.HasExactRecovery obsA ∧ FinKernel.HasExactRecovery obsB) := by
  constructor
  · intro hTensorRecovery
    have hTensorMonic :
        FinKernel.ObservationMonic (FinKernel.tensor obsA obsB) :=
      finKernel_hasExactRecovery_to_observationMonic hTensorRecovery
    have hAMonic : FinKernel.ObservationMonic obsA :=
      finKernel_observationMonic_tensor_reflect_left u hTensorMonic
    have hBMonic : FinKernel.ObservationMonic obsB :=
      finKernel_observationMonic_tensor_reflect_right x hTensorMonic
    exact ⟨finKernel_observationMonic_to_hasExactRecovery a b obsA hAMonic,
      finKernel_observationMonic_to_hasExactRecovery c d obsB hBMonic⟩
  · rintro ⟨hA, hB⟩
    exact finKernel_hasExactRecovery_tensor hA hB

/--
Equivalent inhabited-source characterization stated directly at the cancellation
interface.
-/
theorem finKernel_observationMonic_tensor_iff_factors
    {a b c d : Nat}
    {obsA : FinKernel a b} {obsB : FinKernel c d}
    (x : Fin a) (u : Fin c) :
    FinKernel.ObservationMonic (FinKernel.tensor obsA obsB) ↔
      (FinKernel.ObservationMonic obsA ∧ FinKernel.ObservationMonic obsB) := by
  constructor
  · intro hTensor
    exact ⟨finKernel_observationMonic_tensor_reflect_left u hTensor,
      finKernel_observationMonic_tensor_reflect_right x hTensor⟩
  · rintro ⟨hA, hB⟩
    exact finKernel_observationMonic_tensor hA hB

/-- Every exact kernel with empty source is monic, vacuously. -/
theorem finKernel_emptySource_observationMonic
    {q : Nat} (obs : FinKernel 0 q) :
    FinKernel.ObservationMonic obs := by
  intro t h₁ h₂ _
  funext x y
  exact Fin.elim0 y

/--
An empty right source factor erases a non-monic left factor.  This is an exact
counterexample to unrestricted tensor-monicity reflection.
-/
theorem finKernel_tensor_empty_right_reflection_counterexample :
    FinKernel.ObservationMonic
      (FinKernel.tensor (FinKernel.discard 2) (FinKernel.identity 0)) ∧
    (¬ FinKernel.ObservationMonic (FinKernel.discard 2)) := by
  constructor
  · exact finKernel_emptySource_observationMonic _
  · exact finKernel_discard_two_not_observationMonic

/-- Symmetric empty-left counterexample to unrestricted right reflection. -/
theorem finKernel_tensor_empty_left_reflection_counterexample :
    FinKernel.ObservationMonic
      (FinKernel.tensor (FinKernel.identity 0) (FinKernel.discard 2)) ∧
    (¬ FinKernel.ObservationMonic (FinKernel.discard 2)) := by
  constructor
  · exact finKernel_emptySource_observationMonic _
  · exact finKernel_discard_two_not_observationMonic

/-- The empty-factor counterexample also exists at the exact-recovery interface. -/
theorem finKernel_tensor_empty_right_recovery_counterexample :
    FinKernel.HasExactRecovery
      (FinKernel.tensor (FinKernel.discard 2) (FinKernel.identity 0)) ∧
    (¬ FinKernel.HasExactRecovery (FinKernel.discard 2)) := by
  constructor
  · exact (finKernel_observationMonic_iff_hasExactRecovery).1
      finKernel_tensor_empty_right_reflection_counterexample.1
  · intro hrecover
    exact finKernel_tensor_empty_right_reflection_counterexample.2
      (finKernel_hasExactRecovery_to_observationMonic hrecover)

/-- Two-sided exact invertibility is closed under independent tensor. -/
theorem finKernel_twoSidedExactInverse_tensor
    {a b c d : Nat}
    {obsA : FinKernel a b} {obsB : FinKernel c d}
    (hA : ∃ inverseA : FinKernel b a,
      FinKernel.compose inverseA obsA = FinKernel.identity a ∧
      FinKernel.compose obsA inverseA = FinKernel.identity b)
    (hB : ∃ inverseB : FinKernel d c,
      FinKernel.compose inverseB obsB = FinKernel.identity c ∧
      FinKernel.compose obsB inverseB = FinKernel.identity d) :
    ∃ inverse : FinKernel (b * d) (a * c),
      FinKernel.compose inverse (FinKernel.tensor obsA obsB) =
        FinKernel.identity (a * c) ∧
      FinKernel.compose (FinKernel.tensor obsA obsB) inverse =
        FinKernel.identity (b * d) := by
  rcases hA with ⟨inverseA, hAleft, hAright⟩
  rcases hB with ⟨inverseB, hBleft, hBright⟩
  refine ⟨FinKernel.tensor inverseA inverseB, ?_, ?_⟩
  · calc
      FinKernel.compose
          (FinKernel.tensor inverseA inverseB)
          (FinKernel.tensor obsA obsB) =
        FinKernel.tensor
          (FinKernel.compose inverseA obsA)
          (FinKernel.compose inverseB obsB) :=
            finKernel_tensor_interchange obsA inverseA obsB inverseB
      _ = FinKernel.tensor (FinKernel.identity a) (FinKernel.identity c) := by
        rw [hAleft, hBleft]
      _ = FinKernel.identity (a * c) := finKernel_tensor_identity a c
  · calc
      FinKernel.compose
          (FinKernel.tensor obsA obsB)
          (FinKernel.tensor inverseA inverseB) =
        FinKernel.tensor
          (FinKernel.compose obsA inverseA)
          (FinKernel.compose obsB inverseB) :=
            finKernel_tensor_interchange inverseA obsA inverseB obsB
      _ = FinKernel.tensor (FinKernel.identity b) (FinKernel.identity d) := by
        rw [hAright, hBright]
      _ = FinKernel.identity (b * d) := finKernel_tensor_identity b d

/-- Noisy exact isomorphisms remain tensor-closed algebraically. -/
theorem finNoisyEpic2_tensor_self_hasTwoSidedExactInverse :
    ∃ inverse : FinKernel 4 4,
      FinKernel.compose inverse
          (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) = FinKernel.identity 4 ∧
      FinKernel.compose
          (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) inverse =
        FinKernel.identity 4 := by
  simpa using finKernel_twoSidedExactInverse_tensor
    finNoisyEpic2_hasTwoSidedExactInverse
    finNoisyEpic2_hasTwoSidedExactInverse

/--
Tensoring the deterministic binary flip with itself retains a stochastic-valid
two-sided inverse.
-/
theorem finFlip2_dirac_tensor_self_hasValidStochasticTwoSidedInverse :
    ∃ inverse : FinKernel 4 4,
      FinKernel.Valid inverse ∧
      FinKernel.compose inverse
          (FinKernel.tensor (FinKernel.dirac finFlip2) (FinKernel.dirac finFlip2)) =
        FinKernel.identity 4 ∧
      FinKernel.compose
          (FinKernel.tensor (FinKernel.dirac finFlip2) (FinKernel.dirac finFlip2))
          inverse = FinKernel.identity 4 := by
  rcases finFlip2_dirac_hasValidStochasticTwoSidedInverse with
    ⟨inverseA, hvalidA, hAleft, hAright⟩
  refine ⟨FinKernel.tensor inverseA inverseA,
    finKernel_tensor_valid hvalidA hvalidA, ?_, ?_⟩
  · calc
      FinKernel.compose
          (FinKernel.tensor inverseA inverseA)
          (FinKernel.tensor (FinKernel.dirac finFlip2) (FinKernel.dirac finFlip2)) =
        FinKernel.tensor
          (FinKernel.compose inverseA (FinKernel.dirac finFlip2))
          (FinKernel.compose inverseA (FinKernel.dirac finFlip2)) :=
            finKernel_tensor_interchange
              (FinKernel.dirac finFlip2) inverseA
              (FinKernel.dirac finFlip2) inverseA
      _ = FinKernel.tensor (FinKernel.identity 2) (FinKernel.identity 2) := by
        rw [hAleft]
      _ = FinKernel.identity 4 := by
        simpa using finKernel_tensor_identity 2 2
  · calc
      FinKernel.compose
          (FinKernel.tensor (FinKernel.dirac finFlip2) (FinKernel.dirac finFlip2))
          (FinKernel.tensor inverseA inverseA) =
        FinKernel.tensor
          (FinKernel.compose (FinKernel.dirac finFlip2) inverseA)
          (FinKernel.compose (FinKernel.dirac finFlip2) inverseA) :=
            finKernel_tensor_interchange
              inverseA (FinKernel.dirac finFlip2)
              inverseA (FinKernel.dirac finFlip2)
      _ = FinKernel.tensor (FinKernel.identity 2) (FinKernel.identity 2) := by
        rw [hAright]
      _ = FinKernel.identity 4 := by
        simpa using finKernel_tensor_identity 2 2

/-- Acceptance bundle for tensor closure, inhabited reflection, and empty-factor failure. -/
theorem finKernel_monoidal_recovery_reflection_bundle :
    (∀ {a b c d : Nat} {obsA : FinKernel a b} {obsB : FinKernel c d},
      FinKernel.HasExactRecovery obsA →
      FinKernel.HasExactRecovery obsB →
      FinKernel.HasExactRecovery (FinKernel.tensor obsA obsB)) ∧
    (∀ {a b c d : Nat} {obsA : FinKernel a b} {obsB : FinKernel c d},
      FinKernel.ObservationMonic obsA →
      FinKernel.ObservationMonic obsB →
      FinKernel.ObservationMonic (FinKernel.tensor obsA obsB)) ∧
    (∀ {a b c d : Nat} {obsA : FinKernel a b} {obsB : FinKernel c d},
      Fin a → Fin c →
      (FinKernel.ObservationMonic (FinKernel.tensor obsA obsB) ↔
        (FinKernel.ObservationMonic obsA ∧ FinKernel.ObservationMonic obsB))) ∧
    FinKernel.ObservationMonic
      (FinKernel.tensor (FinKernel.discard 2) (FinKernel.identity 0)) ∧
    (¬ FinKernel.ObservationMonic (FinKernel.discard 2)) ∧
    FinKernel.HasExactRecovery
      (FinKernel.tensor (FinKernel.discard 2) (FinKernel.identity 0)) ∧
    (¬ FinKernel.HasExactRecovery (FinKernel.discard 2)) ∧
    (∃ inverse : FinKernel 4 4,
      FinKernel.compose inverse
          (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) = FinKernel.identity 4 ∧
      FinKernel.compose
          (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) inverse =
        FinKernel.identity 4) ∧
    (∃ inverse : FinKernel 4 4,
      FinKernel.Valid inverse ∧
      FinKernel.compose inverse
          (FinKernel.tensor (FinKernel.dirac finFlip2) (FinKernel.dirac finFlip2)) =
        FinKernel.identity 4 ∧
      FinKernel.compose
          (FinKernel.tensor (FinKernel.dirac finFlip2) (FinKernel.dirac finFlip2))
          inverse = FinKernel.identity 4) := by
  exact ⟨finKernel_hasExactRecovery_tensor,
    finKernel_observationMonic_tensor,
    fun x u => finKernel_observationMonic_tensor_iff_factors x u,
    finKernel_tensor_empty_right_reflection_counterexample.1,
    finKernel_tensor_empty_right_reflection_counterexample.2,
    finKernel_tensor_empty_right_recovery_counterexample.1,
    finKernel_tensor_empty_right_recovery_counterexample.2,
    finNoisyEpic2_tensor_self_hasTwoSidedExactInverse,
    finFlip2_dirac_tensor_self_hasValidStochasticTwoSidedInverse⟩

end RelayTheory
