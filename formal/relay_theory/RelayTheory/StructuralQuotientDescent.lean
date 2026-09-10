import RelayTheory.MonoidalQuotientDynamics

namespace RelayTheory

/--
Discard factors through every deterministic coarse observation.  The quotient
witness is discard on the quotient object, and the target observation is the
identity of the monoidal unit.
-/
theorem finKernel_discard_factor_square
    {a q : Nat} (obs : Fin a → Fin q) :
    FinKernel.compose
        (FinKernel.dirac (fun z : Fin 1 => z))
        (FinKernel.discard a) =
      FinKernel.compose
        (FinKernel.discard q)
        (FinKernel.dirac obs) := by
  have hleft :
      FinKernel.compose
          (FinKernel.dirac (fun z : Fin 1 => z))
          (FinKernel.discard a) =
        FinKernel.discard a := by
    rw [finKernel_discard_as_dirac a, finKernel_dirac_compose]
  calc
    FinKernel.compose
        (FinKernel.dirac (fun z : Fin 1 => z))
        (FinKernel.discard a) =
      FinKernel.discard a := hleft
    _ = FinKernel.compose
        (FinKernel.discard q)
        (FinKernel.dirac obs) :=
      (finKernel_discard_causal (finKernel_dirac_valid obs)).symm

/-- Exact quotient factorization of structural discard. -/
theorem finKernel_discard_kernelFactorsObservation
    {a q : Nat} (obs : Fin a → Fin q) :
    FinKernel.KernelFactorsObservation
      obs (fun z : Fin 1 => z) (FinKernel.discard a) := by
  exact ⟨FinKernel.discard q, finKernel_discard_factor_square obs⟩

/-- Stochastic-valid quotient factorization of structural discard. -/
theorem finKernel_discard_stochasticFactorsObservation
    {a q : Nat} (obs : Fin a → Fin q) :
    FinKernel.StochasticFactorsObservation
      obs (fun z : Fin 1 => z) (FinKernel.discard a) := by
  exact ⟨finKernel_discard_valid a,
    FinKernel.discard q,
    finKernel_discard_valid q,
    finKernel_discard_factor_square obs⟩

/--
Copy factors through every deterministic coarse observation.  The quotient
witness is copy on the quotient object and the target observation is the
transport-aware product observation.
-/
theorem finKernel_copy_factor_square
    {a q : Nat} (obs : Fin a → Fin q) :
    FinKernel.compose
        (FinKernel.dirac (finTensorMap obs obs))
        (FinKernel.copy a) =
      FinKernel.compose
        (FinKernel.copy q)
        (FinKernel.dirac obs) := by
  calc
    FinKernel.compose
        (FinKernel.dirac (finTensorMap obs obs))
        (FinKernel.copy a) =
      FinKernel.compose
        (FinKernel.tensor (FinKernel.dirac obs) (FinKernel.dirac obs))
        (FinKernel.copy a) := by
          rw [finKernel_tensor_dirac_finTensorMap]
    _ = FinKernel.compose
        (FinKernel.copy q)
        (FinKernel.dirac obs) :=
      (finKernel_deterministic_preserves_copy obs).symm

/-- Exact quotient factorization of structural copy. -/
theorem finKernel_copy_kernelFactorsObservation
    {a q : Nat} (obs : Fin a → Fin q) :
    FinKernel.KernelFactorsObservation
      obs (finTensorMap obs obs) (FinKernel.copy a) := by
  exact ⟨FinKernel.copy q, finKernel_copy_factor_square obs⟩

/-- Stochastic-valid quotient factorization of structural copy. -/
theorem finKernel_copy_stochasticFactorsObservation
    {a q : Nat} (obs : Fin a → Fin q) :
    FinKernel.StochasticFactorsObservation
      obs (finTensorMap obs obs) (FinKernel.copy a) := by
  exact ⟨finKernel_copy_valid a,
    FinKernel.copy q,
    finKernel_copy_valid q,
    finKernel_copy_factor_square obs⟩

/--
Any exact processes already equivalent under a deterministic coarse observation
remain equivalent after structural copy under the corresponding product
observation.
-/
theorem finKernel_observedEq_after_copy
    {m a q : Nat} (obs : Fin a → Fin q)
    {f g : FinKernel m a}
    (hfg : FinKernel.ObservedEq (FinKernel.dirac obs) f g) :
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap obs obs))
      (FinKernel.compose (FinKernel.copy a) f)
      (FinKernel.compose (FinKernel.copy a) g) := by
  exact finKernel_observedEq_postcompose_of_kernelFactors
    obs (finTensorMap obs obs) (FinKernel.copy a)
    (finKernel_copy_kernelFactorsObservation obs) hfg

/--
The same generic quotient congruence carries equivalent processes through
structural discard to the unit interface.
-/
theorem finKernel_observedEq_after_discard
    {m a q : Nat} (obs : Fin a → Fin q)
    {f g : FinKernel m a}
    (hfg : FinKernel.ObservedEq (FinKernel.dirac obs) f g) :
    FinKernel.ObservedEq
      (FinKernel.dirac (fun z : Fin 1 => z))
      (FinKernel.compose (FinKernel.discard a) f)
      (FinKernel.compose (FinKernel.discard a) g) := by
  exact finKernel_observedEq_postcompose_of_kernelFactors
    obs (fun z : Fin 1 => z) (FinKernel.discard a)
    (finKernel_discard_kernelFactorsObservation obs) hfg

/-- Non-trivial `merge01` quotient admits structural copy. -/
theorem finKernel_merge01_copy_stochasticFactors :
    FinKernel.StochasticFactorsObservation
      finMerge01 (finTensorMap finMerge01 finMerge01) (FinKernel.copy 3) := by
  exact finKernel_copy_stochasticFactorsObservation finMerge01

/-- Non-trivial `merge01` quotient admits structural discard. -/
theorem finKernel_merge01_discard_stochasticFactors :
    FinKernel.StochasticFactorsObservation
      finMerge01 (fun z : Fin 1 => z) (FinKernel.discard 3) := by
  exact finKernel_discard_stochasticFactorsObservation finMerge01

/--
The distinct hidden source states remain product-coarse-equivalent after copy,
showing that copy descends without trivializing the existing quotient.
-/
theorem finKernel_merge01_equivalence_survives_copy :
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap finMerge01 finMerge01))
      (FinKernel.compose (FinKernel.copy 3) finKernelZero3)
      (FinKernel.compose (FinKernel.copy 3) finKernelOne3) := by
  exact finKernel_observedEq_after_copy finMerge01
    finKernel_merge01_observes_zero_one_equal

/-- Every valid stochastic kernel retains discard naturality. -/
theorem finKernel_valid_preserves_discard {m n : Nat}
    {k : FinKernel m n} (hk : FinKernel.Valid k) :
    FinKernel.compose (FinKernel.discard n) k = FinKernel.discard m :=
  finKernel_discard_causal hk

/-- The exact fair stochastic kernel therefore preserves discard. -/
theorem finFairKernel_preserves_discard :
    FinKernel.compose (FinKernel.discard 2) finFairKernel =
      FinKernel.discard 1 :=
  finKernel_discard_causal finFairKernel_valid

/--
But the same valid genuinely stochastic fair kernel fails classical copy
naturality: one draw followed by copy is not two independent draws.
-/
theorem finFairKernel_rejects_copy_naturality :
    FinKernel.compose (FinKernel.copy 2) finFairKernel ≠
      FinKernel.tensor finFairKernel finFairKernel :=
  finKernel_fair_copy_ne_independent

/--
Acceptance bundle: both structural operations descend through the non-trivial
deterministic quotient, while the generic stochastic boundary remains visible.
-/
theorem finKernel_structural_quotient_descent_bundle :
    FinKernel.StochasticFactorsObservation
      finMerge01 (finTensorMap finMerge01 finMerge01) (FinKernel.copy 3) ∧
    FinKernel.StochasticFactorsObservation
      finMerge01 (fun z : Fin 1 => z) (FinKernel.discard 3) ∧
    finKernelZero3 ≠ finKernelOne3 ∧
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap finMerge01 finMerge01))
      (FinKernel.compose (FinKernel.copy 3) finKernelZero3)
      (FinKernel.compose (FinKernel.copy 3) finKernelOne3) ∧
    FinKernel.compose (FinKernel.discard 2) finFairKernel =
      FinKernel.discard 1 ∧
    FinKernel.compose (FinKernel.copy 2) finFairKernel ≠
      FinKernel.tensor finFairKernel finFairKernel := by
  exact ⟨finKernel_merge01_copy_stochasticFactors,
    finKernel_merge01_discard_stochasticFactors,
    finKernel_zero3_ne_one3,
    finKernel_merge01_equivalence_survives_copy,
    finFairKernel_preserves_discard,
    finFairKernel_rejects_copy_naturality⟩

end RelayTheory
