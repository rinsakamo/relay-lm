import RelayTheory.RestrictedContexts

namespace RelayTheory

namespace FinKernel

/--
Exact kernel-level observation factorization.  A future kernel `k` respects the
source and target observations when its observed behavior is exactly induced by
some quotient-level kernel `h`.
-/
def KernelFactorsObservation {a b qa qb : Nat}
    (obsA : Fin a → Fin qa) (obsB : Fin b → Fin qb)
    (k : FinKernel a b) : Prop :=
  ∃ h : FinKernel qa qb,
    compose (dirac obsB) k = compose h (dirac obsA)

/--
Stochastic-valid observation factorization.  In addition to the exact commuting
square, both the concrete future kernel and the explicit quotient dynamics must
be stochastic-valid.
-/
def StochasticFactorsObservation {a b qa qb : Nat}
    (obsA : Fin a → Fin qa) (obsB : Fin b → Fin qb)
    (k : FinKernel a b) : Prop :=
  Valid k ∧
    ∃ h : FinKernel qa qb,
      Valid h ∧
        compose (dirac obsB) k = compose h (dirac obsA)

end FinKernel

/-- Deterministic observation factorization is a special case of kernel factorization. -/
theorem finKernel_factorsObservation_to_kernelFactors
    {a b qa qb : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {f : Fin a → Fin b}
    (hf : FinKernel.FactorsObservation obsA obsB f) :
    FinKernel.KernelFactorsObservation obsA obsB (FinKernel.dirac f) := by
  rcases hf with ⟨h, hcomm⟩
  refine ⟨FinKernel.dirac h, ?_⟩
  rw [finKernel_dirac_compose, finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  exact hcomm x

/-- The deterministic bridge also lands in the stochastic-valid policy. -/
theorem finKernel_factorsObservation_to_stochasticFactors
    {a b qa qb : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {f : Fin a → Fin b}
    (hf : FinKernel.FactorsObservation obsA obsB f) :
    FinKernel.StochasticFactorsObservation obsA obsB (FinKernel.dirac f) := by
  rcases hf with ⟨h, hcomm⟩
  refine ⟨finKernel_dirac_valid f, ?_⟩
  refine ⟨FinKernel.dirac h, finKernel_dirac_valid h, ?_⟩
  rw [finKernel_dirac_compose, finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  exact hcomm x

/-- Exact kernel factorization contains identity for every declared observation. -/
theorem finKernel_kernelFactorsObservation_identity {a q : Nat}
    (obs : Fin a → Fin q) :
    FinKernel.KernelFactorsObservation obs obs (FinKernel.identity a) := by
  refine ⟨FinKernel.identity q, ?_⟩
  rw [finKernel_compose_identity_before, finKernel_compose_identity_after]

/-- Exact kernel factorization is closed under generic sequential composition. -/
theorem finKernel_kernelFactorsObservation_compose
    {a b c qa qb qc : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {obsC : Fin c → Fin qc}
    {k : FinKernel a b} {l : FinKernel b c}
    (hk : FinKernel.KernelFactorsObservation obsA obsB k)
    (hl : FinKernel.KernelFactorsObservation obsB obsC l) :
    FinKernel.KernelFactorsObservation obsA obsC (FinKernel.compose l k) := by
  rcases hk with ⟨hAB, hk⟩
  rcases hl with ⟨hBC, hl⟩
  refine ⟨FinKernel.compose hBC hAB, ?_⟩
  calc
    FinKernel.compose (FinKernel.dirac obsC) (FinKernel.compose l k) =
        FinKernel.compose
          (FinKernel.compose (FinKernel.dirac obsC) l) k :=
      finKernel_compose_associative k l (FinKernel.dirac obsC)
    _ = FinKernel.compose
        (FinKernel.compose hBC (FinKernel.dirac obsB)) k := by
          rw [hl]
    _ = FinKernel.compose hBC
        (FinKernel.compose (FinKernel.dirac obsB) k) :=
      (finKernel_compose_associative k (FinKernel.dirac obsB) hBC).symm
    _ = FinKernel.compose hBC
        (FinKernel.compose hAB (FinKernel.dirac obsA)) := by
          rw [hk]
    _ = FinKernel.compose (FinKernel.compose hBC hAB)
        (FinKernel.dirac obsA) :=
      finKernel_compose_associative (FinKernel.dirac obsA) hAB hBC

/-- The stochastic-valid factorization policy contains identity. -/
theorem finKernel_stochasticFactorsObservation_identity {a q : Nat}
    (obs : Fin a → Fin q) :
    FinKernel.StochasticFactorsObservation obs obs (FinKernel.identity a) := by
  refine ⟨finKernel_identity_valid a, ?_⟩
  refine ⟨FinKernel.identity q, finKernel_identity_valid q, ?_⟩
  rw [finKernel_compose_identity_before, finKernel_compose_identity_after]

/-- The stochastic-valid factorization policy is closed under composition. -/
theorem finKernel_stochasticFactorsObservation_compose
    {a b c qa qb qc : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {obsC : Fin c → Fin qc}
    {k : FinKernel a b} {l : FinKernel b c}
    (hk : FinKernel.StochasticFactorsObservation obsA obsB k)
    (hl : FinKernel.StochasticFactorsObservation obsB obsC l) :
    FinKernel.StochasticFactorsObservation obsA obsC (FinKernel.compose l k) := by
  rcases hk with ⟨hkValid, hAB, hABValid, hkEq⟩
  rcases hl with ⟨hlValid, hBC, hBCValid, hlEq⟩
  refine ⟨finKernel_compose_valid hkValid hlValid, ?_⟩
  refine ⟨FinKernel.compose hBC hAB,
    finKernel_compose_valid hABValid hBCValid, ?_⟩
  calc
    FinKernel.compose (FinKernel.dirac obsC) (FinKernel.compose l k) =
        FinKernel.compose
          (FinKernel.compose (FinKernel.dirac obsC) l) k :=
      finKernel_compose_associative k l (FinKernel.dirac obsC)
    _ = FinKernel.compose
        (FinKernel.compose hBC (FinKernel.dirac obsB)) k := by
          rw [hlEq]
    _ = FinKernel.compose hBC
        (FinKernel.compose (FinKernel.dirac obsB) k) :=
      (finKernel_compose_associative k (FinKernel.dirac obsB) hBC).symm
    _ = FinKernel.compose hBC
        (FinKernel.compose hAB (FinKernel.dirac obsA)) := by
          rw [hkEq]
    _ = FinKernel.compose (FinKernel.compose hBC hAB)
        (FinKernel.dirac obsA) :=
      finKernel_compose_associative (FinKernel.dirac obsA) hAB hBC

/--
Exact coarse observational equivalence is preserved by every future stochastic
kernel that factors through the source and target observations.  The commuting
square alone is sufficient; no validity premise is needed for this theorem.
-/
theorem finKernel_observedEq_postcompose_of_kernelFactors
    {m a b qa qb : Nat}
    (obsA : Fin a → Fin qa) (obsB : Fin b → Fin qb)
    (k : FinKernel a b)
    (hk : FinKernel.KernelFactorsObservation obsA obsB k)
    {f g : FinKernel m a}
    (hfg : FinKernel.ObservedEq (FinKernel.dirac obsA) f g) :
    FinKernel.ObservedEq (FinKernel.dirac obsB)
      (FinKernel.compose k f) (FinKernel.compose k g) := by
  rcases hk with ⟨h, hfactor⟩
  unfold FinKernel.ObservedEq at hfg ⊢
  have hbase :
      FinKernel.compose (FinKernel.dirac obsA) f =
        FinKernel.compose (FinKernel.dirac obsA) g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hfg
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose (FinKernel.dirac obsB) (FinKernel.compose k f) =
        FinKernel.compose
          (FinKernel.compose (FinKernel.dirac obsB) k) f :=
      finKernel_compose_associative f k (FinKernel.dirac obsB)
    _ = FinKernel.compose
        (FinKernel.compose h (FinKernel.dirac obsA)) f := by
          rw [hfactor]
    _ = FinKernel.compose h
        (FinKernel.compose (FinKernel.dirac obsA) f) :=
      (finKernel_compose_associative f (FinKernel.dirac obsA) h).symm
    _ = FinKernel.compose h
        (FinKernel.compose (FinKernel.dirac obsA) g) := by
          rw [hbase]
    _ = FinKernel.compose
        (FinKernel.compose h (FinKernel.dirac obsA)) g :=
      finKernel_compose_associative g (FinKernel.dirac obsA) h
    _ = FinKernel.compose
        (FinKernel.compose (FinKernel.dirac obsB) k) g := by
          rw [hfactor]
    _ = FinKernel.compose (FinKernel.dirac obsB) (FinKernel.compose k g) :=
      (finKernel_compose_associative g k (FinKernel.dirac obsB)).symm

/--
Genuinely stochastic hidden-class mixer on the three-state fixture.  Hidden
states 0 and 1 are both replaced by a fair draw over {0,1}; visible state 2 is
preserved exactly.
-/
def finHiddenMix3 : FinKernel 3 3 :=
  fun x y =>
    if x = (2 : Fin 3) then
      if y = (2 : Fin 3) then 1 else 0
    else if y = (2 : Fin 3) then 0 else qHalf

/-- The hidden mixer is an exact stochastic-valid kernel. -/
theorem finHiddenMix3_valid : FinKernel.Valid finHiddenMix3 := by
  constructor
  · intro x y
    by_cases hx : x = (2 : Fin 3)
    · by_cases hy : y = (2 : Fin 3)
      · simpa [finHiddenMix3, hx, hy] using rat_zero_le_one
      · simpa [finHiddenMix3, hx, hy] using
          (show (0 : Rat) ≤ 0 from Rat.le_refl)
    · by_cases hy : y = (2 : Fin 3)
      · simpa [finHiddenMix3, hx, hy] using
          (show (0 : Rat) ≤ 0 from Rat.le_refl)
      · simpa [finHiddenMix3, hx, hy] using Rat.le_of_lt qHalf_pos
  · intro x
    unfold FinKernel.rowSum
    by_cases hx : x = (2 : Fin 3)
    · subst x
      grind [sumFin, finHiddenMix3, qHalf]
    · grind [sumFin, finHiddenMix3, qHalf]

/-- Genuine randomness: the hidden mixer is not any deterministic Dirac kernel. -/
theorem finHiddenMix3_not_dirac :
    ¬ ∃ f : Fin 3 → Fin 3, finHiddenMix3 = FinKernel.dirac f := by
  intro h
  rcases h with ⟨f, hf⟩
  have hv := congrArg
    (fun k => k (0 : Fin 3) (0 : Fin 3)) hf
  have h02 : (0 : Fin 3) ≠ (2 : Fin 3) := by decide
  change
    (if (0 : Fin 3) = (2 : Fin 3) then
      (if (0 : Fin 3) = (2 : Fin 3) then (1 : Rat) else 0)
    else if (0 : Fin 3) = (2 : Fin 3) then 0 else qHalf) =
      (if (0 : Fin 3) = f 0 then 1 else 0) at hv
  rw [if_neg h02, if_neg h02] at hv
  by_cases h0 : (0 : Fin 3) = f 0
  · rw [if_pos h0] at hv
    have hhalf_ne_one : qHalf ≠ 1 := by grind [qHalf]
    exact hhalf_ne_one hv
  · rw [if_neg h0] at hv
    have hhalf_ne_zero : qHalf ≠ 0 := ne_of_gt qHalf_pos
    exact hhalf_ne_zero hv

/-- Observing the hidden mixer through `merge01` leaves the coarse state unchanged. -/
theorem finHiddenMix3_merge01_commutes :
    FinKernel.compose (FinKernel.dirac finMerge01) finHiddenMix3 =
      FinKernel.dirac finMerge01 := by
  funext x z
  unfold FinKernel.compose FinKernel.dirac
  by_cases hx : x = (2 : Fin 3)
  · subst x
    grind [sumFin, finHiddenMix3, finMerge01, qHalf]
  · grind [sumFin, finHiddenMix3, finMerge01, qHalf]

/-- Exact kernel-level factorization of the hidden mixer through `merge01`. -/
theorem finHiddenMix3_kernelFactors_merge01 :
    FinKernel.KernelFactorsObservation
      finMerge01 finMerge01 finHiddenMix3 := by
  refine ⟨FinKernel.identity 2, ?_⟩
  rw [finKernel_compose_identity_after]
  exact finHiddenMix3_merge01_commutes

/-- The hidden mixer belongs to the stronger stochastic-valid factorization policy. -/
theorem finHiddenMix3_stochasticFactors_merge01 :
    FinKernel.StochasticFactorsObservation
      finMerge01 finMerge01 finHiddenMix3 := by
  refine ⟨finHiddenMix3_valid, ?_⟩
  refine ⟨FinKernel.identity 2, finKernel_identity_valid 2, ?_⟩
  rw [finKernel_compose_identity_after]
  exact finHiddenMix3_merge01_commutes

/--
The genuinely stochastic allowed future context preserves the existing
non-trivial `zero3 ~ one3` coarse quotient.
-/
theorem finKernel_merge01_equivalence_survives_hidden_mix :
    FinKernel.ObservedEq (FinKernel.dirac finMerge01)
      (FinKernel.compose finHiddenMix3 finKernelZero3)
      (FinKernel.compose finHiddenMix3 finKernelOne3) := by
  exact finKernel_observedEq_postcompose_of_kernelFactors
    finMerge01 finMerge01 finHiddenMix3
    finHiddenMix3_kernelFactors_merge01
    finKernel_merge01_observes_zero_one_equal

/--
The known distinction-refining deterministic future map is excluded even at the
more general kernel-factorization level; otherwise generic congruence would
contradict the already-earned semantic counterexample.
-/
theorem finKernel_moveOneToTwo_not_kernelFactors_merge01 :
    ¬ FinKernel.KernelFactorsObservation
      finMerge01 finMerge01 finKernelMoveOneToTwo := by
  intro hfac
  have hpreserved := finKernel_observedEq_postcompose_of_kernelFactors
    finMerge01 finMerge01 finKernelMoveOneToTwo hfac
    finKernel_merge01_observes_zero_one_equal
  exact finKernel_fixed_probe_not_postcomposition_stable hpreserved

/--
Acceptance bundle for the finite stochastic quotient-dynamics milestone.
It keeps genuine randomness, non-triviality, factorization, preservation, and
the excluded distinction-refining control visible together.
-/
theorem finKernel_stochastic_quotient_dynamics_bundle :
    FinKernel.Valid finHiddenMix3 ∧
    (¬ ∃ f : Fin 3 → Fin 3, finHiddenMix3 = FinKernel.dirac f) ∧
    FinKernel.StochasticFactorsObservation
      finMerge01 finMerge01 finHiddenMix3 ∧
    finKernelZero3 ≠ finKernelOne3 ∧
    FinKernel.ObservedEq (FinKernel.dirac finMerge01)
      (FinKernel.compose finHiddenMix3 finKernelZero3)
      (FinKernel.compose finHiddenMix3 finKernelOne3) ∧
    ¬ FinKernel.KernelFactorsObservation
      finMerge01 finMerge01 finKernelMoveOneToTwo := by
  exact ⟨finHiddenMix3_valid,
    finHiddenMix3_not_dirac,
    finHiddenMix3_stochasticFactors_merge01,
    finKernel_zero3_ne_one3,
    finKernel_merge01_equivalence_survives_hidden_mix,
    finKernel_moveOneToTwo_not_kernelFactors_merge01⟩

end RelayTheory
