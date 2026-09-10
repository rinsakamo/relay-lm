import RelayTheory.StochasticQuotientDynamics

namespace RelayTheory

/--
The tensor of two deterministic observation kernels is exactly the Dirac kernel
of the transport-aware product observation.  This bridge keeps the explicit
`Fin a × Fin c <-> Fin (a*c)` representation visible.
-/
theorem finKernel_tensor_dirac_finTensorMap
    {a b c d : Nat}
    (f : Fin a → Fin b) (g : Fin c → Fin d) :
    FinKernel.tensor (FinKernel.dirac f) (FinKernel.dirac g) =
      FinKernel.dirac (finTensorMap f g) := by
  simpa [finTensorMap] using finKernel_tensor_dirac f g

/--
Exact kernel-level observation factorization is closed under independent tensor.
The quotient witness is the independent tensor of the two component witnesses.
-/
theorem finKernel_kernelFactorsObservation_tensor
    {a b c d qa qb qc qd : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {obsC : Fin c → Fin qc} {obsD : Fin d → Fin qd}
    {k : FinKernel a b} {l : FinKernel c d}
    (hk : FinKernel.KernelFactorsObservation obsA obsB k)
    (hl : FinKernel.KernelFactorsObservation obsC obsD l) :
    FinKernel.KernelFactorsObservation
      (finTensorMap obsA obsC)
      (finTensorMap obsB obsD)
      (FinKernel.tensor k l) := by
  rcases hk with ⟨hAB, hkEq⟩
  rcases hl with ⟨hCD, hlEq⟩
  refine ⟨FinKernel.tensor hAB hCD, ?_⟩
  calc
    FinKernel.compose
        (FinKernel.dirac (finTensorMap obsB obsD))
        (FinKernel.tensor k l) =
      FinKernel.compose
        (FinKernel.tensor (FinKernel.dirac obsB) (FinKernel.dirac obsD))
        (FinKernel.tensor k l) := by
          rw [finKernel_tensor_dirac_finTensorMap]
    _ = FinKernel.tensor
        (FinKernel.compose (FinKernel.dirac obsB) k)
        (FinKernel.compose (FinKernel.dirac obsD) l) :=
          finKernel_tensor_interchange k (FinKernel.dirac obsB)
            l (FinKernel.dirac obsD)
    _ = FinKernel.tensor
        (FinKernel.compose hAB (FinKernel.dirac obsA))
        (FinKernel.compose hCD (FinKernel.dirac obsC)) := by
          rw [hkEq, hlEq]
    _ = FinKernel.compose
        (FinKernel.tensor hAB hCD)
        (FinKernel.tensor (FinKernel.dirac obsA) (FinKernel.dirac obsC)) :=
          (finKernel_tensor_interchange
            (FinKernel.dirac obsA) hAB
            (FinKernel.dirac obsC) hCD).symm
    _ = FinKernel.compose
        (FinKernel.tensor hAB hCD)
        (FinKernel.dirac (finTensorMap obsA obsC)) := by
          rw [finKernel_tensor_dirac_finTensorMap]

/--
The stochastic-valid factorization policy is closed under independent tensor.
Validity of both the concrete context and quotient witness follows from the
generic tensor-validity theorem.
-/
theorem finKernel_stochasticFactorsObservation_tensor
    {a b c d qa qb qc qd : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {obsC : Fin c → Fin qc} {obsD : Fin d → Fin qd}
    {k : FinKernel a b} {l : FinKernel c d}
    (hk : FinKernel.StochasticFactorsObservation obsA obsB k)
    (hl : FinKernel.StochasticFactorsObservation obsC obsD l) :
    FinKernel.StochasticFactorsObservation
      (finTensorMap obsA obsC)
      (finTensorMap obsB obsD)
      (FinKernel.tensor k l) := by
  rcases hk with ⟨hkValid, hAB, hABValid, hkEq⟩
  rcases hl with ⟨hlValid, hCD, hCDValid, hlEq⟩
  refine ⟨finKernel_tensor_valid hkValid hlValid, ?_⟩
  refine ⟨FinKernel.tensor hAB hCD,
    finKernel_tensor_valid hABValid hCDValid, ?_⟩
  exact (finKernel_kernelFactorsObservation_tensor
    (show FinKernel.KernelFactorsObservation obsA obsB k from ⟨hAB, hkEq⟩)
    (show FinKernel.KernelFactorsObservation obsC obsD l from ⟨hCD, hlEq⟩)).choose_spec

/--
Independent exact observational equivalences tensor to an exact product
observational equivalence under the transport-aware product observation.
No stochastic validity premise is required.
-/
theorem finKernel_observedEq_tensor_product
    {m a n c qa qc : Nat}
    (obsA : Fin a → Fin qa) (obsC : Fin c → Fin qc)
    {f g : FinKernel m a} {p q : FinKernel n c}
    (hfg : FinKernel.ObservedEq (FinKernel.dirac obsA) f g)
    (hpq : FinKernel.ObservedEq (FinKernel.dirac obsC) p q) :
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap obsA obsC))
      (FinKernel.tensor f p)
      (FinKernel.tensor g q) := by
  unfold FinKernel.ObservedEq at hfg hpq ⊢
  have hfeq :
      FinKernel.compose (FinKernel.dirac obsA) f =
        FinKernel.compose (FinKernel.dirac obsA) g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hfg
  have hpeq :
      FinKernel.compose (FinKernel.dirac obsC) p =
        FinKernel.compose (FinKernel.dirac obsC) q :=
    (finKernel_behaviorEq_iff_eq _ _).1 hpq
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose
        (FinKernel.dirac (finTensorMap obsA obsC))
        (FinKernel.tensor f p) =
      FinKernel.compose
        (FinKernel.tensor (FinKernel.dirac obsA) (FinKernel.dirac obsC))
        (FinKernel.tensor f p) := by
          rw [finKernel_tensor_dirac_finTensorMap]
    _ = FinKernel.tensor
        (FinKernel.compose (FinKernel.dirac obsA) f)
        (FinKernel.compose (FinKernel.dirac obsC) p) :=
          finKernel_tensor_interchange f (FinKernel.dirac obsA)
            p (FinKernel.dirac obsC)
    _ = FinKernel.tensor
        (FinKernel.compose (FinKernel.dirac obsA) g)
        (FinKernel.compose (FinKernel.dirac obsC) q) := by
          rw [hfeq, hpeq]
    _ = FinKernel.compose
        (FinKernel.tensor (FinKernel.dirac obsA) (FinKernel.dirac obsC))
        (FinKernel.tensor g q) :=
          (finKernel_tensor_interchange g (FinKernel.dirac obsA)
            q (FinKernel.dirac obsC)).symm
    _ = FinKernel.compose
        (FinKernel.dirac (finTensorMap obsA obsC))
        (FinKernel.tensor g q) := by
          rw [finKernel_tensor_dirac_finTensorMap]

/-- The random hidden mixer tensors with itself inside the stochastic factorization policy. -/
theorem finHiddenMix3_tensor_stochasticFactors_merge01_product :
    FinKernel.StochasticFactorsObservation
      (finTensorMap finMerge01 finMerge01)
      (finTensorMap finMerge01 finMerge01)
      (FinKernel.tensor finHiddenMix3 finHiddenMix3) := by
  exact finKernel_stochasticFactorsObservation_tensor
    finHiddenMix3_stochasticFactors_merge01
    finHiddenMix3_stochasticFactors_merge01

/-- A product source differing only in the first hidden state is still exactly distinct. -/
theorem finKernel_zerozero_ne_onezero_product :
    FinKernel.tensor finKernelZero3 finKernelZero3 ≠
      FinKernel.tensor finKernelOne3 finKernelZero3 := by
  intro h
  have hv := congrArg
    (fun k => k
      (finPairTransport.toFun ((0 : Fin 1), (0 : Fin 1)))
      (finPairTransport.toFun ((0 : Fin 3), (0 : Fin 3)))) h
  rw [finKernel_tensor_encoded, finKernel_tensor_encoded] at hv
  simp [finKernelZero3, finKernelOne3, FinKernel.dirac] at hv

/-- The product merge observation identifies the distinct product sources. -/
theorem finKernel_merge01_product_observes_zerozero_onezero_equal :
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap finMerge01 finMerge01))
      (FinKernel.tensor finKernelZero3 finKernelZero3)
      (FinKernel.tensor finKernelOne3 finKernelZero3) := by
  apply finKernel_observedEq_tensor_product finMerge01 finMerge01
  · exact finKernel_merge01_observes_zero_one_equal
  · unfold FinKernel.ObservedEq
    intro x z
    rfl

/--
The non-trivial product quotient survives genuinely random parallel future
dynamics on both factors.
-/
theorem finKernel_merge01_product_equivalence_survives_hidden_mix_tensor :
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap finMerge01 finMerge01))
      (FinKernel.compose
        (FinKernel.tensor finHiddenMix3 finHiddenMix3)
        (FinKernel.tensor finKernelZero3 finKernelZero3))
      (FinKernel.compose
        (FinKernel.tensor finHiddenMix3 finHiddenMix3)
        (FinKernel.tensor finKernelOne3 finKernelZero3)) := by
  exact finKernel_observedEq_postcompose_of_kernelFactors
    (finTensorMap finMerge01 finMerge01)
    (finTensorMap finMerge01 finMerge01)
    (FinKernel.tensor finHiddenMix3 finHiddenMix3)
    (finKernel_stochasticFactorsObservation_tensor
      finHiddenMix3_stochasticFactors_merge01
      finHiddenMix3_stochasticFactors_merge01).2.choose_spec.2
    finKernel_merge01_product_observes_zerozero_onezero_equal

end RelayTheory
