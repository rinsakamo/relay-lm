import RelayTheory.MonoidalQuotientDynamics

namespace RelayTheory

/--
Tensor equality can be cancelled against a right factor at any source/target
coordinate where that factor has exact mass one.  This gives the parallel
negative control an explicit discriminator instead of assuming component
non-factorization automatically lifts to product non-factorization.
-/
theorem finKernel_tensor_cancel_right_at_one
    {a b c d : Nat}
    {f g : FinKernel a b}
    (r : FinKernel c d) (u : Fin c) (v : Fin d)
    (hr : r u v = 1)
    (h : FinKernel.tensor f r = FinKernel.tensor g r) :
    f = g := by
  funext x y
  have hv := congrArg
    (fun k => k
      (finPairTransport.toFun (x, u))
      (finPairTransport.toFun (y, v))) h
  rw [finKernel_tensor_encoded, finKernel_tensor_encoded, hr,
    Rat.mul_one, Rat.mul_one] at hv
  exact hv

/--
Observe after parallel future dynamics and parallel sources.  The result factors
exactly into the tensor of the two independently observed component chains.
-/
theorem finKernel_observe_tensor_after_tensor
    {m a b n c d qb qd : Nat}
    (obsB : Fin b → Fin qb) (obsD : Fin d → Fin qd)
    (k : FinKernel a b) (l : FinKernel c d)
    (f : FinKernel m a) (p : FinKernel n c) :
    FinKernel.compose
        (FinKernel.dirac (finTensorMap obsB obsD))
        (FinKernel.compose (FinKernel.tensor k l) (FinKernel.tensor f p)) =
      FinKernel.tensor
        (FinKernel.compose (FinKernel.dirac obsB) (FinKernel.compose k f))
        (FinKernel.compose (FinKernel.dirac obsD) (FinKernel.compose l p)) := by
  calc
    FinKernel.compose
        (FinKernel.dirac (finTensorMap obsB obsD))
        (FinKernel.compose (FinKernel.tensor k l) (FinKernel.tensor f p)) =
      FinKernel.compose
        (FinKernel.dirac (finTensorMap obsB obsD))
        (FinKernel.tensor (FinKernel.compose k f) (FinKernel.compose l p)) := by
          rw [finKernel_tensor_interchange]
    _ = FinKernel.compose
        (FinKernel.tensor (FinKernel.dirac obsB) (FinKernel.dirac obsD))
        (FinKernel.tensor (FinKernel.compose k f) (FinKernel.compose l p)) := by
          rw [finKernel_tensor_dirac_finTensorMap]
    _ = FinKernel.tensor
        (FinKernel.compose (FinKernel.dirac obsB) (FinKernel.compose k f))
        (FinKernel.compose (FinKernel.dirac obsD) (FinKernel.compose l p)) :=
          finKernel_tensor_interchange
            (FinKernel.compose k f) (FinKernel.dirac obsB)
            (FinKernel.compose l p) (FinKernel.dirac obsD)

/-- The unchanged second component contributes exact observed mass one at state 0. -/
theorem finKernel_merge01_after_identity_zero_mass_zero :
    FinKernel.compose (FinKernel.dirac finMerge01)
      (FinKernel.compose (FinKernel.identity 3) finKernelZero3)
      (0 : Fin 1) (0 : Fin 2) = 1 := by
  rw [finKernel_compose_identity_after]
  unfold finKernelZero3
  rw [finKernel_dirac_compose]
  simp [FinKernel.dirac, finMerge01]

/--
A product context containing the known distinction-refining map on the first
factor and identity on the second genuinely breaks the product coarse quotient.
-/
theorem finKernel_merge01_product_excluded_move_identity_breaks :
    ¬ FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap finMerge01 finMerge01))
      (FinKernel.compose
        (FinKernel.tensor finKernelMoveOneToTwo (FinKernel.identity 3))
        (FinKernel.tensor finKernelZero3 finKernelZero3))
      (FinKernel.compose
        (FinKernel.tensor finKernelMoveOneToTwo (FinKernel.identity 3))
        (FinKernel.tensor finKernelOne3 finKernelZero3)) := by
  intro h
  unfold FinKernel.ObservedEq at h
  have heq := (finKernel_behaviorEq_iff_eq _ _).1 h
  have hzero := finKernel_observe_tensor_after_tensor
    finMerge01 finMerge01
    finKernelMoveOneToTwo (FinKernel.identity 3)
    finKernelZero3 finKernelZero3
  have hone := finKernel_observe_tensor_after_tensor
    finMerge01 finMerge01
    finKernelMoveOneToTwo (FinKernel.identity 3)
    finKernelOne3 finKernelZero3
  rw [hzero, hone] at heq
  have hcomponent := finKernel_tensor_cancel_right_at_one
    (FinKernel.compose (FinKernel.dirac finMerge01)
      (FinKernel.compose (FinKernel.identity 3) finKernelZero3))
    (0 : Fin 1) (0 : Fin 2)
    finKernel_merge01_after_identity_zero_mass_zero
    heq
  have hbad :
      FinKernel.ObservedEq finKernelMerge01
        (FinKernel.compose finKernelMoveOneToTwo finKernelZero3)
        (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) := by
    unfold FinKernel.ObservedEq
    apply (finKernel_behaviorEq_iff_eq _ _).2
    simpa [finKernelMerge01] using hcomponent
  exact finKernel_fixed_probe_not_postcomposition_stable hbad

/--
The semantically distinguishing parallel context is therefore excluded by the
product kernel-factorization policy itself.
-/
theorem finKernel_move_identity_tensor_not_kernelFactors_merge01_product :
    ¬ FinKernel.KernelFactorsObservation
      (finTensorMap finMerge01 finMerge01)
      (finTensorMap finMerge01 finMerge01)
      (FinKernel.tensor finKernelMoveOneToTwo (FinKernel.identity 3)) := by
  intro hfac
  have hpreserved := finKernel_observedEq_postcompose_of_kernelFactors
    (finTensorMap finMerge01 finMerge01)
    (finTensorMap finMerge01 finMerge01)
    (FinKernel.tensor finKernelMoveOneToTwo (FinKernel.identity 3))
    hfac
    finKernel_merge01_product_observes_zerozero_onezero_equal
  exact finKernel_merge01_product_excluded_move_identity_breaks hpreserved

/-- The excluded parallel context is itself stochastic-valid; exclusion is semantic, not malformedness. -/
theorem finKernel_move_identity_tensor_valid :
    FinKernel.Valid
      (FinKernel.tensor finKernelMoveOneToTwo (FinKernel.identity 3)) :=
  finKernel_tensor_valid finKernel_moveOneToTwo_valid (finKernel_identity_valid 3)

/--
Acceptance bundle: exact non-triviality, product equivalence, random parallel
preservation, and a valid but excluded distinction-refining parallel context.
-/
theorem finKernel_monoidal_quotient_dynamics_bundle :
    FinKernel.tensor finKernelZero3 finKernelZero3 ≠
      FinKernel.tensor finKernelOne3 finKernelZero3 ∧
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap finMerge01 finMerge01))
      (FinKernel.tensor finKernelZero3 finKernelZero3)
      (FinKernel.tensor finKernelOne3 finKernelZero3) ∧
    FinKernel.StochasticFactorsObservation
      (finTensorMap finMerge01 finMerge01)
      (finTensorMap finMerge01 finMerge01)
      (FinKernel.tensor finHiddenMix3 finHiddenMix3) ∧
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap finMerge01 finMerge01))
      (FinKernel.compose
        (FinKernel.tensor finHiddenMix3 finHiddenMix3)
        (FinKernel.tensor finKernelZero3 finKernelZero3))
      (FinKernel.compose
        (FinKernel.tensor finHiddenMix3 finHiddenMix3)
        (FinKernel.tensor finKernelOne3 finKernelZero3)) ∧
    FinKernel.Valid
      (FinKernel.tensor finKernelMoveOneToTwo (FinKernel.identity 3)) ∧
    ¬ FinKernel.KernelFactorsObservation
      (finTensorMap finMerge01 finMerge01)
      (finTensorMap finMerge01 finMerge01)
      (FinKernel.tensor finKernelMoveOneToTwo (FinKernel.identity 3)) := by
  exact ⟨finKernel_zerozero_ne_onezero_product,
    finKernel_merge01_product_observes_zerozero_onezero_equal,
    finHiddenMix3_tensor_stochasticFactors_merge01_product,
    finKernel_merge01_product_equivalence_survives_hidden_mix_tensor,
    finKernel_move_identity_tensor_valid,
    finKernel_move_identity_tensor_not_kernelFactors_merge01_product⟩

end RelayTheory
