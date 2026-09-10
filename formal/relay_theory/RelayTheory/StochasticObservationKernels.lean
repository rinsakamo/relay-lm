import RelayTheory.StructuralQuotientDescent

namespace RelayTheory

namespace FinKernel

/--
Exact quotient-dynamics factorization with observation channels represented by
arbitrary finite kernels rather than only deterministic/Dirac maps.
-/
def KernelObservationFactors {a b qa qb : Nat}
    (obsA : FinKernel a qa) (obsB : FinKernel b qb)
    (k : FinKernel a b) : Prop :=
  ∃ h : FinKernel qa qb,
    compose obsB k = compose h obsA

/--
Stochastic-valid specialization of kernel-observation factorization.  Both
observation channels, the concrete future kernel, and the quotient witness must
be stochastic-valid.
-/
def StochasticKernelObservationFactors {a b qa qb : Nat}
    (obsA : FinKernel a qa) (obsB : FinKernel b qb)
    (k : FinKernel a b) : Prop :=
  Valid obsA ∧ Valid obsB ∧ Valid k ∧
    ∃ h : FinKernel qa qb,
      Valid h ∧ compose obsB k = compose h obsA

/-- Classical copy-preservation contract for an arbitrary exact finite kernel. -/
def PreservesCopy {m n : Nat} (k : FinKernel m n) : Prop :=
  compose (copy n) k =
    compose (tensor k k) (copy m)

end FinKernel

/-- Existing deterministic-observation factorization is a strict special case. -/
theorem finKernel_deterministicObservation_to_kernelObservation
    {a b qa qb : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {k : FinKernel a b}
    (hk : FinKernel.KernelFactorsObservation obsA obsB k) :
    FinKernel.KernelObservationFactors
      (FinKernel.dirac obsA) (FinKernel.dirac obsB) k := by
  exact hk

/-- The stochastic-valid deterministic-observation interface also embeds exactly. -/
theorem finKernel_deterministicObservation_to_stochasticKernelObservation
    {a b qa qb : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {k : FinKernel a b}
    (hk : FinKernel.StochasticFactorsObservation obsA obsB k) :
    FinKernel.StochasticKernelObservationFactors
      (FinKernel.dirac obsA) (FinKernel.dirac obsB) k := by
  rcases hk with ⟨hkValid, h, hhValid, hEq⟩
  exact ⟨finKernel_dirac_valid obsA,
    finKernel_dirac_valid obsB,
    hkValid,
    h,
    hhValid,
    hEq⟩

/-- Every kernel observation admits the identity future context. -/
theorem finKernel_kernelObservationFactors_identity
    {a q : Nat} (obs : FinKernel a q) :
    FinKernel.KernelObservationFactors obs obs (FinKernel.identity a) := by
  refine ⟨FinKernel.identity q, ?_⟩
  rw [finKernel_compose_identity_before, finKernel_compose_identity_after]

/-- Kernel-observation factorization is closed under sequential composition. -/
theorem finKernel_kernelObservationFactors_compose
    {a b c qa qb qc : Nat}
    {obsA : FinKernel a qa} {obsB : FinKernel b qb}
    {obsC : FinKernel c qc}
    {k : FinKernel a b} {l : FinKernel b c}
    (hk : FinKernel.KernelObservationFactors obsA obsB k)
    (hl : FinKernel.KernelObservationFactors obsB obsC l) :
    FinKernel.KernelObservationFactors obsA obsC (FinKernel.compose l k) := by
  rcases hk with ⟨hAB, hkEq⟩
  rcases hl with ⟨hBC, hlEq⟩
  refine ⟨FinKernel.compose hBC hAB, ?_⟩
  calc
    FinKernel.compose obsC (FinKernel.compose l k) =
        FinKernel.compose (FinKernel.compose obsC l) k :=
      finKernel_compose_associative k l obsC
    _ = FinKernel.compose (FinKernel.compose hBC obsB) k := by
      rw [hlEq]
    _ = FinKernel.compose hBC (FinKernel.compose obsB k) :=
      (finKernel_compose_associative k obsB hBC).symm
    _ = FinKernel.compose hBC (FinKernel.compose hAB obsA) := by
      rw [hkEq]
    _ = FinKernel.compose (FinKernel.compose hBC hAB) obsA :=
      finKernel_compose_associative obsA hAB hBC

/--
Sequential observational congruence needs only the exact commuting square;
observation channels themselves need not be deterministic.
-/
theorem finKernel_observedEq_postcompose_of_kernelObservationFactors
    {m a b qa qb : Nat}
    (obsA : FinKernel a qa) (obsB : FinKernel b qb)
    (k : FinKernel a b)
    (hk : FinKernel.KernelObservationFactors obsA obsB k)
    {f g : FinKernel m a}
    (hfg : FinKernel.ObservedEq obsA f g) :
    FinKernel.ObservedEq obsB
      (FinKernel.compose k f) (FinKernel.compose k g) := by
  rcases hk with ⟨h, hfactor⟩
  unfold FinKernel.ObservedEq at hfg ⊢
  have hbase :
      FinKernel.compose obsA f = FinKernel.compose obsA g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hfg
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose obsB (FinKernel.compose k f) =
        FinKernel.compose (FinKernel.compose obsB k) f :=
      finKernel_compose_associative f k obsB
    _ = FinKernel.compose (FinKernel.compose h obsA) f := by
      rw [hfactor]
    _ = FinKernel.compose h (FinKernel.compose obsA f) :=
      (finKernel_compose_associative f obsA h).symm
    _ = FinKernel.compose h (FinKernel.compose obsA g) := by
      rw [hbase]
    _ = FinKernel.compose (FinKernel.compose h obsA) g :=
      finKernel_compose_associative g obsA h
    _ = FinKernel.compose (FinKernel.compose obsB k) g := by
      rw [hfactor]
    _ = FinKernel.compose obsB (FinKernel.compose k g) :=
      (finKernel_compose_associative g k obsB).symm

/--
Every valid stochastic observation channel admits canonical structural discard
descent to the monoidal unit.
-/
theorem finKernel_validObservation_discard_factor_square
    {a q : Nat} {obs : FinKernel a q} (hobs : FinKernel.Valid obs) :
    FinKernel.compose (FinKernel.identity 1) (FinKernel.discard a) =
      FinKernel.compose (FinKernel.discard q) obs := by
  calc
    FinKernel.compose (FinKernel.identity 1) (FinKernel.discard a) =
        FinKernel.discard a :=
      finKernel_compose_identity_after (FinKernel.discard a)
    _ = FinKernel.compose (FinKernel.discard q) obs :=
      (finKernel_discard_causal hobs).symm

/-- Exact factorization package for discard under a valid stochastic observation. -/
theorem finKernel_validObservation_discard_kernelFactors
    {a q : Nat} {obs : FinKernel a q} (hobs : FinKernel.Valid obs) :
    FinKernel.KernelObservationFactors
      obs (FinKernel.identity 1) (FinKernel.discard a) := by
  exact ⟨FinKernel.discard q,
    finKernel_validObservation_discard_factor_square hobs⟩

/-- Stochastic-valid factorization package for discard under a valid observation. -/
theorem finKernel_validObservation_discard_stochasticFactors
    {a q : Nat} {obs : FinKernel a q} (hobs : FinKernel.Valid obs) :
    FinKernel.StochasticKernelObservationFactors
      obs (FinKernel.identity 1) (FinKernel.discard a) := by
  exact ⟨hobs,
    finKernel_identity_valid 1,
    finKernel_discard_valid a,
    FinKernel.discard q,
    finKernel_discard_valid q,
    finKernel_validObservation_discard_factor_square hobs⟩

/-- Every deterministic finite map preserves classical copy. -/
theorem finKernel_dirac_preservesCopy
    {m n : Nat} (f : Fin m → Fin n) :
    FinKernel.PreservesCopy (FinKernel.dirac f) := by
  exact finKernel_deterministic_preserves_copy f

/--
A copy-preserving stochastic observation has the canonical copy commuting square
with quotient witness `copy q` and product observation `obs tensor obs`.
-/
theorem finKernel_preservesCopy_factor_square
    {a q : Nat} {obs : FinKernel a q}
    (hcopy : FinKernel.PreservesCopy obs) :
    FinKernel.compose (FinKernel.tensor obs obs) (FinKernel.copy a) =
      FinKernel.compose (FinKernel.copy q) obs := by
  exact hcopy.symm

/-- Canonical copy descent is exactly the copy-preservation contract. -/
theorem finKernel_copy_factor_square_iff_preservesCopy
    {a q : Nat} {obs : FinKernel a q} :
    FinKernel.compose (FinKernel.tensor obs obs) (FinKernel.copy a) =
        FinKernel.compose (FinKernel.copy q) obs ↔
      FinKernel.PreservesCopy obs := by
  constructor
  · intro h
    exact h.symm
  · intro h
    exact h.symm

/-- Exact kernel-observation factorization of copy under a copy-preserving observation. -/
theorem finKernel_copyPreservingObservation_copy_kernelFactors
    {a q : Nat} {obs : FinKernel a q}
    (hcopy : FinKernel.PreservesCopy obs) :
    FinKernel.KernelObservationFactors
      obs (FinKernel.tensor obs obs) (FinKernel.copy a) := by
  exact ⟨FinKernel.copy q, finKernel_preservesCopy_factor_square hcopy⟩

/-- Stochastic-valid copy factorization requires validity plus copy preservation. -/
theorem finKernel_copyPreservingObservation_copy_stochasticFactors
    {a q : Nat} {obs : FinKernel a q}
    (hobs : FinKernel.Valid obs)
    (hcopy : FinKernel.PreservesCopy obs) :
    FinKernel.StochasticKernelObservationFactors
      obs (FinKernel.tensor obs obs) (FinKernel.copy a) := by
  exact ⟨hobs,
    finKernel_tensor_valid hobs hobs,
    finKernel_copy_valid a,
    FinKernel.copy q,
    finKernel_copy_valid q,
    finKernel_preservesCopy_factor_square hcopy⟩

/-- On the one-point interface classical copy is exactly identity. -/
theorem finKernel_copy_one_eq_identity :
    FinKernel.copy 1 = FinKernel.identity 1 := by
  rw [finKernel_copy_as_dirac 1, finKernel_identity_eq_dirac_id 1]
  apply finKernel_dirac_congr
  intro x
  have hx : x = (0 : Fin 1) := fin_one_eq_zero x
  have hc : finCopyFn x = (0 : Fin 1) := fin_one_eq_zero (finCopyFn x)
  exact hc.trans hx.symm

/-- The fair stochastic observation remains causal for discard. -/
theorem finFairObservation_discard_descends :
    FinKernel.KernelObservationFactors
      finFairKernel (FinKernel.identity 1) (FinKernel.discard 1) := by
  exact finKernel_validObservation_discard_kernelFactors finFairKernel_valid

/-- The same valid fair observation does not preserve classical copy. -/
theorem finFairObservation_not_preservesCopy :
    ¬ FinKernel.PreservesCopy finFairKernel := by
  intro hcopy
  unfold FinKernel.PreservesCopy at hcopy
  rw [finKernel_copy_one_eq_identity,
    finKernel_compose_identity_before] at hcopy
  exact finKernel_fair_copy_ne_independent hcopy

/-- Therefore canonical copy descent fails for the fair stochastic observation. -/
theorem finFairObservation_copy_descent_fails :
    ¬ (FinKernel.compose
          (FinKernel.tensor finFairKernel finFairKernel)
          (FinKernel.copy 1) =
        FinKernel.compose (FinKernel.copy 2) finFairKernel) := by
  intro h
  exact finFairObservation_not_preservesCopy
    ((finKernel_copy_factor_square_iff_preservesCopy).1 h)

/--
Acceptance bundle for stochastic observation channels: sequential quotient
factorization survives, discard needs only validity, while copy requires the
stronger copy-preservation contract.
-/
theorem finKernel_stochastic_observation_bundle :
    FinKernel.Valid finFairKernel ∧
    FinKernel.KernelObservationFactors
      finFairKernel (FinKernel.identity 1) (FinKernel.discard 1) ∧
    (¬ FinKernel.PreservesCopy finFairKernel) ∧
    (∀ {m n : Nat} (f : Fin m → Fin n),
      FinKernel.PreservesCopy (FinKernel.dirac f)) := by
  exact ⟨finFairKernel_valid,
    finFairObservation_discard_descends,
    finFairObservation_not_preservesCopy,
    fun f => finKernel_dirac_preservesCopy f⟩

end RelayTheory
