import RelayTheory.ScalarEpicityReduction

namespace RelayTheory

namespace FinKernel

/--
Partially contract a scalar continuation on a product observation target against
one fixed row of the left observation.
-/
def tensorContractLeft {a qa qb : Nat}
    (obsA : FinKernel a qa)
    (h : FinKernel (qa * qb) 1)
    (x : Fin a) : FinKernel qb 1 :=
  fun j _ =>
    sumFin qa (fun i =>
      obsA x i * h (finPairTransport.toFun (i, j)) (0 : Fin 1))

/-- Fix the right product coordinate of a scalar continuation. -/
def tensorFiberRight {qa qb : Nat}
    (h : FinKernel (qa * qb) 1)
    (j : Fin qb) : FinKernel qa 1 :=
  fun i _ => h (finPairTransport.toFun (i, j)) (0 : Fin 1)

end FinKernel

/-- Every point of the singleton finite interface is its canonical zero point. -/
theorem finOne_eq_zero (u : Fin 1) : u = (0 : Fin 1) := by
  apply Fin.ext
  simp

/--
Exact Fubini bridge: a scalar continuation after a tensor observation can be
computed by first contracting the left observation row and then composing
through the right observation.
-/
theorem finKernel_tensor_scalar_contract_eval
    {a b qa qb : Nat}
    (obsA : FinKernel a qa) (obsB : FinKernel b qb)
    (h : FinKernel (qa * qb) 1)
    (x : Fin a) (y : Fin b) (u : Fin 1) :
    FinKernel.compose h (FinKernel.tensor obsA obsB)
        (finPairTransport.toFun (x, y)) u =
      FinKernel.compose (FinKernel.tensorContractLeft obsA h x) obsB y u := by
  have hu := finOne_eq_zero u
  subst u
  unfold FinKernel.compose FinKernel.tensorContractLeft
  calc
    sumFin (qa * qb) (fun w =>
        FinKernel.tensor obsA obsB
          (finPairTransport.toFun (x, y)) w * h w (0 : Fin 1)) =
      sumFin qa (fun i =>
        sumFin qb (fun j =>
          FinKernel.tensor obsA obsB
            (finPairTransport.toFun (x, y))
            (finPairTransport.toFun (i, j)) *
          h (finPairTransport.toFun (i, j)) (0 : Fin 1))) :=
        sumFin_product (qa) (qb) (fun w =>
          FinKernel.tensor obsA obsB
            (finPairTransport.toFun (x, y)) w * h w (0 : Fin 1))
    _ = sumFin qa (fun i =>
        sumFin qb (fun j =>
          (obsA x i * obsB y j) *
            h (finPairTransport.toFun (i, j)) (0 : Fin 1))) := by
          apply sumFin_congr
          intro i
          apply sumFin_congr
          intro j
          rw [finKernel_tensor_encoded]
    _ = sumFin qb (fun j =>
        sumFin qa (fun i =>
          (obsA x i * obsB y j) *
            h (finPairTransport.toFun (i, j)) (0 : Fin 1))) :=
          sumFin_swap qa qb (fun i j =>
            (obsA x i * obsB y j) *
              h (finPairTransport.toFun (i, j)) (0 : Fin 1))
    _ = sumFin qb (fun j =>
        sumFin qa (fun i =>
          obsB y j *
            (obsA x i * h (finPairTransport.toFun (i, j)) (0 : Fin 1)))) := by
          apply sumFin_congr
          intro j
          apply sumFin_congr
          intro i
          grind
    _ = sumFin qb (fun j =>
        obsB y j *
          sumFin qa (fun i =>
            obsA x i * h (finPairTransport.toFun (i, j)) (0 : Fin 1))) := by
          apply sumFin_congr
          intro j
          exact sumFin_mul_left qa (obsB y j)
            (fun i => obsA x i *
              h (finPairTransport.toFun (i, j)) (0 : Fin 1))

/--
Scalar epicity of the right observation cancels the right factor and forces the
left-row contractions of two product continuations to agree.
-/
theorem finKernel_tensorContractLeft_eq_of_scalarEpic_right
    {a b qa qb : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    (hB : FinKernel.ScalarObservationEpic obsB)
    {h₁ h₂ : FinKernel (qa * qb) 1}
    (hEq : FinKernel.compose h₁ (FinKernel.tensor obsA obsB) =
      FinKernel.compose h₂ (FinKernel.tensor obsA obsB))
    (x : Fin a) :
    FinKernel.tensorContractLeft obsA h₁ x =
      FinKernel.tensorContractLeft obsA h₂ x := by
  apply hB
  funext y u
  rw [← finKernel_tensor_scalar_contract_eval,
    ← finKernel_tensor_scalar_contract_eval]
  exact congrFun (congrFun hEq (finPairTransport.toFun (x, y))) u

/-- A fixed right fiber composed through the left observation is one contraction coordinate. -/
theorem finKernel_tensorFiberRight_compose_eval
    {a qa qb : Nat}
    (obsA : FinKernel a qa)
    (h : FinKernel (qa * qb) 1)
    (j : Fin qb) (x : Fin a) (u : Fin 1) :
    FinKernel.compose (FinKernel.tensorFiberRight h j) obsA x u =
      FinKernel.tensorContractLeft obsA h x j u := by
  have hu := finOne_eq_zero u
  subst u
  rfl

/--
After right-factor cancellation, scalar epicity of the left observation cancels
each fixed right fiber.
-/
theorem finKernel_tensorFiberRight_eq_of_scalarEpics
    {a b qa qb : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    (hA : FinKernel.ScalarObservationEpic obsA)
    (hB : FinKernel.ScalarObservationEpic obsB)
    {h₁ h₂ : FinKernel (qa * qb) 1}
    (hEq : FinKernel.compose h₁ (FinKernel.tensor obsA obsB) =
      FinKernel.compose h₂ (FinKernel.tensor obsA obsB))
    (j : Fin qb) :
    FinKernel.tensorFiberRight h₁ j = FinKernel.tensorFiberRight h₂ j := by
  apply hA
  funext x u
  rw [finKernel_tensorFiberRight_compose_eval,
    finKernel_tensorFiberRight_compose_eval]
  have hc := finKernel_tensorContractLeft_eq_of_scalarEpic_right hB hEq x
  exact congrFun (congrFun hc j) u

/-- Exact observation epicity is closed under independent tensor. -/
theorem finKernel_observationEpic_tensor
    {a b qa qb : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    (hA : FinKernel.ObservationEpic obsA)
    (hB : FinKernel.ObservationEpic obsB) :
    FinKernel.ObservationEpic (FinKernel.tensor obsA obsB) := by
  apply finKernel_scalar_to_observationEpic
  have hAs := finKernel_observationEpic_to_scalar hA
  have hBs := finKernel_observationEpic_to_scalar hB
  intro h₁ h₂ hEq
  funext w u
  have hu := finOne_eq_zero u
  subst u
  let j : Fin qb := (finPairTransport.invFun w).2
  have hfiber := finKernel_tensorFiberRight_eq_of_scalarEpics
    hAs hBs hEq j
  have hv := congrFun (congrFun hfiber (finPairTransport.invFun w).1) (0 : Fin 1)
  have hw := finPair_flatten_roundtrip w
  rw [← hw]
  simpa [j, FinKernel.tensorFiberRight] using hv

/-- The noisy epic observation remains stochastic-valid after tensoring with itself. -/
theorem finNoisyEpic2_tensor_valid :
    FinKernel.Valid (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) :=
  finKernel_tensor_valid finNoisyEpic2_valid finNoisyEpic2_valid

/-- The noisy epic observation remains epic after independent tensor. -/
theorem finNoisyEpic2_tensor_observationEpic :
    FinKernel.ObservationEpic (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) :=
  finKernel_observationEpic_tensor
    finNoisyEpic2_observationEpic finNoisyEpic2_observationEpic

/-- The noisy product observation is still genuinely non-deterministic. -/
theorem finNoisyEpic2_tensor_not_deterministic :
    ¬ FinKernel.DeterministicKernel
      (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) := by
  rintro ⟨f, hf⟩
  let x := finPairTransport.toFun ((0 : Fin 2), (0 : Fin 2))
  let y := finPairTransport.toFun ((0 : Fin 2), (0 : Fin 2))
  have hv := congrFun (congrFun hf x) y
  have hleft :
      FinKernel.tensor finNoisyEpic2 finNoisyEpic2 x y =
        qThreeQuarter * qThreeQuarter := by
    simp [x, y, finNoisyEpic2]
  rw [hleft] at hv
  by_cases hy : y = f x
  · simp [FinKernel.dirac, hy] at hv
    grind [qThreeQuarter]
  · simp [FinKernel.dirac, hy] at hv
    grind [qThreeQuarter]

/-- Positive stochastic product control for monoidal witness determinacy. -/
theorem finNoisyEpic2_tensor_epic_bundle :
    FinKernel.Valid (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) ∧
    (¬ FinKernel.DeterministicKernel
      (FinKernel.tensor finNoisyEpic2 finNoisyEpic2)) ∧
    FinKernel.ObservationEpic
      (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) := by
  exact ⟨finNoisyEpic2_tensor_valid,
    finNoisyEpic2_tensor_not_deterministic,
    finNoisyEpic2_tensor_observationEpic⟩

/-- Tensoring the fair non-epic observation with the unit identity remains non-epic. -/
theorem finFairKernel_tensor_identity_not_observationEpic :
    ¬ FinKernel.ObservationEpic
      (FinKernel.tensor finFairKernel (FinKernel.identity 1)) := by
  intro hepic
  let h₁ : FinKernel (2 * 1) (2 * 1) :=
    FinKernel.tensor (FinKernel.identity 2) (FinKernel.identity 1)
  let h₂ : FinKernel (2 * 1) (2 * 1) :=
    FinKernel.tensor (FinKernel.dirac finFlip2) (FinKernel.identity 1)
  have hne : h₁ ≠ h₂ := by
    intro h
    have hv := congrFun (congrFun h
      (finPairTransport.toFun ((0 : Fin 2), (0 : Fin 1))))
      (finPairTransport.toFun ((0 : Fin 2), (0 : Fin 1)))
    simp [h₁, h₂, FinKernel.identity, FinKernel.dirac, finFlip2] at hv
  have hsame :
      FinKernel.compose h₁
          (FinKernel.tensor finFairKernel (FinKernel.identity 1)) =
        FinKernel.compose h₂
          (FinKernel.tensor finFairKernel (FinKernel.identity 1)) := by
    calc
      FinKernel.compose h₁
          (FinKernel.tensor finFairKernel (FinKernel.identity 1)) =
        FinKernel.tensor
          (FinKernel.compose (FinKernel.identity 2) finFairKernel)
          (FinKernel.compose (FinKernel.identity 1) (FinKernel.identity 1)) := by
            exact finKernel_tensor_interchange
              finFairKernel (FinKernel.identity 2)
              (FinKernel.identity 1) (FinKernel.identity 1)
      _ = FinKernel.tensor finFairKernel (FinKernel.identity 1) := by
            rw [finKernel_compose_identity_after,
              finKernel_compose_identity_after]
      _ = FinKernel.tensor
          (FinKernel.compose (FinKernel.dirac finFlip2) finFairKernel)
          (FinKernel.compose (FinKernel.identity 1) (FinKernel.identity 1)) := by
            rw [finKernel_flip_after_fair,
              finKernel_compose_identity_after]
      _ = FinKernel.compose h₂
          (FinKernel.tensor finFairKernel (FinKernel.identity 1)) := by
            exact (finKernel_tensor_interchange
              finFairKernel (FinKernel.dirac finFlip2)
              (FinKernel.identity 1) (FinKernel.identity 1)).symm
  exact hne (hepic h₁ h₂ hsame)

/--
Tensor factorization existence plus epic source observations yields a unique
tensor quotient witness.
-/
theorem finKernel_tensor_factorization_existsUnique_of_epic
    {a b c d qa qb qc qd : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    {obsC : FinKernel c qc} {obsD : FinKernel d qd}
    {k : FinKernel a b} {l : FinKernel c d}
    (hk : FinKernel.KernelObservationFactors obsA obsB k)
    (hl : FinKernel.KernelObservationFactors obsC obsD l)
    (hA : FinKernel.ObservationEpic obsA)
    (hC : FinKernel.ObservationEpic obsC) :
    ∃ h : FinKernel (qa * qc) (qb * qd),
      FinKernel.compose
          (FinKernel.tensor obsB obsD) (FinKernel.tensor k l) =
        FinKernel.compose h (FinKernel.tensor obsA obsC) ∧
      ∀ h' : FinKernel (qa * qc) (qb * qd),
        FinKernel.compose
            (FinKernel.tensor obsB obsD) (FinKernel.tensor k l) =
          FinKernel.compose h' (FinKernel.tensor obsA obsC) → h' = h := by
  have hfactor := finKernel_kernelObservationFactors_tensor hk hl
  have hepic := finKernel_observationEpic_tensor hA hC
  exact finKernel_kernelObservationFactors_existsUnique hepic hfactor

/-- Acceptance bundle for monoidal witness determinacy. -/
theorem finKernel_monoidal_epicity_bundle :
    (∀ {a b qa qb : Nat}
      {obsA : FinKernel a qa} {obsB : FinKernel b qb},
      FinKernel.ObservationEpic obsA →
      FinKernel.ObservationEpic obsB →
      FinKernel.ObservationEpic (FinKernel.tensor obsA obsB)) ∧
    FinKernel.Valid (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) ∧
    (¬ FinKernel.DeterministicKernel
      (FinKernel.tensor finNoisyEpic2 finNoisyEpic2)) ∧
    FinKernel.ObservationEpic
      (FinKernel.tensor finNoisyEpic2 finNoisyEpic2) ∧
    (¬ FinKernel.ObservationEpic
      (FinKernel.tensor finFairKernel (FinKernel.identity 1))) := by
  exact ⟨finKernel_observationEpic_tensor,
    finNoisyEpic2_tensor_valid,
    finNoisyEpic2_tensor_not_deterministic,
    finNoisyEpic2_tensor_observationEpic,
    finFairKernel_tensor_identity_not_observationEpic⟩

end RelayTheory
