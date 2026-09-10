import RelayTheory.CopyPreservingCharacterization

namespace RelayTheory

/--
Arbitrary exact kernel-observation commuting squares tensor by pure interchange.
No deterministic/Dirac observation representation is used in this theorem.
-/
theorem finKernel_kernelObservation_tensor_factor_square
    {a b c d qa qb qc qd : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    {obsC : FinKernel c qc} {obsD : FinKernel d qd}
    {k : FinKernel a b} {l : FinKernel c d}
    {hAB : FinKernel qa qb} {hCD : FinKernel qc qd}
    (hkEq : FinKernel.compose obsB k = FinKernel.compose hAB obsA)
    (hlEq : FinKernel.compose obsD l = FinKernel.compose hCD obsC) :
    FinKernel.compose
        (FinKernel.tensor obsB obsD)
        (FinKernel.tensor k l) =
      FinKernel.compose
        (FinKernel.tensor hAB hCD)
        (FinKernel.tensor obsA obsC) := by
  calc
    FinKernel.compose
        (FinKernel.tensor obsB obsD)
        (FinKernel.tensor k l) =
      FinKernel.tensor
        (FinKernel.compose obsB k)
        (FinKernel.compose obsD l) :=
      finKernel_tensor_interchange k obsB l obsD
    _ = FinKernel.tensor
        (FinKernel.compose hAB obsA)
        (FinKernel.compose hCD obsC) := by
      rw [hkEq, hlEq]
    _ = FinKernel.compose
        (FinKernel.tensor hAB hCD)
        (FinKernel.tensor obsA obsC) :=
      (finKernel_tensor_interchange obsA hAB obsC hCD).symm

/-- Exact arbitrary-kernel observation factorization is closed under tensor. -/
theorem finKernel_kernelObservationFactors_tensor
    {a b c d qa qb qc qd : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    {obsC : FinKernel c qc} {obsD : FinKernel d qd}
    {k : FinKernel a b} {l : FinKernel c d}
    (hk : FinKernel.KernelObservationFactors obsA obsB k)
    (hl : FinKernel.KernelObservationFactors obsC obsD l) :
    FinKernel.KernelObservationFactors
      (FinKernel.tensor obsA obsC)
      (FinKernel.tensor obsB obsD)
      (FinKernel.tensor k l) := by
  rcases hk with ⟨hAB, hkEq⟩
  rcases hl with ⟨hCD, hlEq⟩
  exact ⟨FinKernel.tensor hAB hCD,
    finKernel_kernelObservation_tensor_factor_square hkEq hlEq⟩

/--
The stochastic-valid arbitrary-kernel observation policy is also closed under
tensor. Validity of observations, contexts, and quotient witnesses all tensors.
-/
theorem finKernel_stochasticKernelObservationFactors_tensor
    {a b c d qa qb qc qd : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    {obsC : FinKernel c qc} {obsD : FinKernel d qd}
    {k : FinKernel a b} {l : FinKernel c d}
    (hk : FinKernel.StochasticKernelObservationFactors obsA obsB k)
    (hl : FinKernel.StochasticKernelObservationFactors obsC obsD l) :
    FinKernel.StochasticKernelObservationFactors
      (FinKernel.tensor obsA obsC)
      (FinKernel.tensor obsB obsD)
      (FinKernel.tensor k l) := by
  rcases hk with ⟨hobsA, hobsB, hkValid, hAB, hABValid, hkEq⟩
  rcases hl with ⟨hobsC, hobsD, hlValid, hCD, hCDValid, hlEq⟩
  exact ⟨finKernel_tensor_valid hobsA hobsC,
    finKernel_tensor_valid hobsB hobsD,
    finKernel_tensor_valid hkValid hlValid,
    FinKernel.tensor hAB hCD,
    finKernel_tensor_valid hABValid hCDValid,
    finKernel_kernelObservation_tensor_factor_square hkEq hlEq⟩

/--
Independent observational equivalences tensor under arbitrary exact observation
channels. Determinism and stochastic validity are not required.
-/
theorem finKernel_kernelObservedEq_tensor_product
    {m a n c qa qc : Nat}
    (obsA : FinKernel a qa) (obsC : FinKernel c qc)
    {f g : FinKernel m a} {p q : FinKernel n c}
    (hfg : FinKernel.ObservedEq obsA f g)
    (hpq : FinKernel.ObservedEq obsC p q) :
    FinKernel.ObservedEq
      (FinKernel.tensor obsA obsC)
      (FinKernel.tensor f p)
      (FinKernel.tensor g q) := by
  unfold FinKernel.ObservedEq at hfg hpq ⊢
  have hfeq :
      FinKernel.compose obsA f = FinKernel.compose obsA g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hfg
  have hpeq :
      FinKernel.compose obsC p = FinKernel.compose obsC q :=
    (finKernel_behaviorEq_iff_eq _ _).1 hpq
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose
        (FinKernel.tensor obsA obsC)
        (FinKernel.tensor f p) =
      FinKernel.tensor
        (FinKernel.compose obsA f)
        (FinKernel.compose obsC p) :=
      finKernel_tensor_interchange f obsA p obsC
    _ = FinKernel.tensor
        (FinKernel.compose obsA g)
        (FinKernel.compose obsC q) := by
      rw [hfeq, hpeq]
    _ = FinKernel.compose
        (FinKernel.tensor obsA obsC)
        (FinKernel.tensor g q) :=
      (finKernel_tensor_interchange g obsA q obsC).symm

/--
The new arbitrary-kernel product theorem mechanically specializes to the prior
deterministic transport-aware product observation theorem.
-/
theorem finKernel_kernelObservedEq_tensor_recovers_deterministic
    {m a n c qa qc : Nat}
    (obsA : Fin a → Fin qa) (obsC : Fin c → Fin qc)
    {f g : FinKernel m a} {p q : FinKernel n c}
    (hfg : FinKernel.ObservedEq (FinKernel.dirac obsA) f g)
    (hpq : FinKernel.ObservedEq (FinKernel.dirac obsC) p q) :
    FinKernel.ObservedEq
      (FinKernel.dirac (finTensorMap obsA obsC))
      (FinKernel.tensor f p)
      (FinKernel.tensor g q) := by
  have h := finKernel_kernelObservedEq_tensor_product
    (FinKernel.dirac obsA) (FinKernel.dirac obsC) hfg hpq
  rw [finKernel_tensor_dirac_finTensorMap] at h
  exact h

/-- The fair stochastic observation admits its identity factorization square. -/
theorem finFairKernel_identity_stochasticKernelObservationFactors :
    FinKernel.StochasticKernelObservationFactors
      finFairKernel finFairKernel (FinKernel.identity 1) := by
  exact ⟨finFairKernel_valid,
    finFairKernel_valid,
    finKernel_identity_valid 1,
    FinKernel.identity 2,
    finKernel_identity_valid 2,
    by rw [finKernel_compose_identity_before, finKernel_compose_identity_after]⟩

/--
Tensoring the fair observation identity square with itself remains inside the
stochastic-valid kernel-observation policy, despite the component observation
being genuinely stochastic/non-deterministic.
-/
theorem finFairKernel_tensor_identity_stochasticKernelObservationFactors :
    FinKernel.StochasticKernelObservationFactors
      (FinKernel.tensor finFairKernel finFairKernel)
      (FinKernel.tensor finFairKernel finFairKernel)
      (FinKernel.tensor (FinKernel.identity 1) (FinKernel.identity 1)) := by
  exact finKernel_stochasticKernelObservationFactors_tensor
    finFairKernel_identity_stochasticKernelObservationFactors
    finFairKernel_identity_stochasticKernelObservationFactors

/--
Separation witness: a valid non-deterministic observation can still participate
compositionally in the monoidal observation policy. This earns no copy descent.
-/
theorem finKernel_stochastic_observation_monoidal_separation_bundle :
    FinKernel.Valid finFairKernel ∧
    (¬ FinKernel.DeterministicKernel finFairKernel) ∧
    FinKernel.StochasticKernelObservationFactors
      (FinKernel.tensor finFairKernel finFairKernel)
      (FinKernel.tensor finFairKernel finFairKernel)
      (FinKernel.tensor (FinKernel.identity 1) (FinKernel.identity 1)) := by
  exact ⟨finFairKernel_valid,
    finFairKernel_not_deterministic,
    finFairKernel_tensor_identity_stochasticKernelObservationFactors⟩

end RelayTheory
