import RelayTheory.StochasticProbeDichotomy

namespace RelayTheory

namespace FinKernel

/--
A deterministic future context respects two declared coarse observations when
it factors through them by an explicit quotient-level deterministic map.
-/
def FactorsObservation {a b qa qb : Nat}
    (obsA : Fin a → Fin qa) (obsB : Fin b → Fin qb)
    (k : Fin a → Fin b) : Prop :=
  ∃ h : Fin qa → Fin qb, ∀ x, obsB (k x) = h (obsA x)

end FinKernel

/-- Identity is observation-factorizing for every declared deterministic observation. -/
theorem finKernel_factorsObservation_identity {a q : Nat}
    (obs : Fin a → Fin q) :
    FinKernel.FactorsObservation obs obs (fun x => x) := by
  refine ⟨fun y => y, ?_⟩
  intro x
  rfl

/-- Observation-factorizing deterministic contexts are closed under composition. -/
theorem finKernel_factorsObservation_compose
    {a b c qa qb qc : Nat}
    {obsA : Fin a → Fin qa} {obsB : Fin b → Fin qb}
    {obsC : Fin c → Fin qc}
    {k : Fin a → Fin b} {l : Fin b → Fin c}
    (hk : FinKernel.FactorsObservation obsA obsB k)
    (hl : FinKernel.FactorsObservation obsB obsC l) :
    FinKernel.FactorsObservation obsA obsC (fun x => l (k x)) := by
  rcases hk with ⟨hAB, hABcomm⟩
  rcases hl with ⟨hBC, hBCcomm⟩
  refine ⟨fun y => hBC (hAB y), ?_⟩
  intro x
  rw [hBCcomm (k x), hABcomm x]

/--
Exact fixed-observation equivalence is preserved by every deterministic future
context that factors through the source and target observations. No stochastic
validity premise is required.
-/
theorem finKernel_observedEq_postcompose_dirac_of_factors
    {m a b qa qb : Nat}
    (obsA : Fin a → Fin qa) (obsB : Fin b → Fin qb)
    (k : Fin a → Fin b)
    (hk : FinKernel.FactorsObservation obsA obsB k)
    {f g : FinKernel m a}
    (hfg : FinKernel.ObservedEq (FinKernel.dirac obsA) f g) :
    FinKernel.ObservedEq (FinKernel.dirac obsB)
      (FinKernel.compose (FinKernel.dirac k) f)
      (FinKernel.compose (FinKernel.dirac k) g) := by
  rcases hk with ⟨h, hcomm⟩
  unfold FinKernel.ObservedEq at hfg ⊢
  have hbase :
      FinKernel.compose (FinKernel.dirac obsA) f =
        FinKernel.compose (FinKernel.dirac obsA) g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hfg
  have hfactor :
      FinKernel.compose (FinKernel.dirac obsB) (FinKernel.dirac k) =
        FinKernel.compose (FinKernel.dirac h) (FinKernel.dirac obsA) := by
    rw [finKernel_dirac_compose, finKernel_dirac_compose]
    apply finKernel_dirac_congr
    intro x
    exact hcomm x
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose (FinKernel.dirac obsB)
        (FinKernel.compose (FinKernel.dirac k) f) =
      FinKernel.compose
        (FinKernel.compose (FinKernel.dirac obsB) (FinKernel.dirac k)) f :=
          finKernel_compose_associative f (FinKernel.dirac k) (FinKernel.dirac obsB)
    _ = FinKernel.compose
        (FinKernel.compose (FinKernel.dirac h) (FinKernel.dirac obsA)) f := by
          rw [hfactor]
    _ = FinKernel.compose (FinKernel.dirac h)
        (FinKernel.compose (FinKernel.dirac obsA) f) :=
          (finKernel_compose_associative f (FinKernel.dirac obsA) (FinKernel.dirac h)).symm
    _ = FinKernel.compose (FinKernel.dirac h)
        (FinKernel.compose (FinKernel.dirac obsA) g) := by
          rw [hbase]
    _ = FinKernel.compose
        (FinKernel.compose (FinKernel.dirac h) (FinKernel.dirac obsA)) g :=
          finKernel_compose_associative g (FinKernel.dirac obsA) (FinKernel.dirac h)
    _ = FinKernel.compose
        (FinKernel.compose (FinKernel.dirac obsB) (FinKernel.dirac k)) g := by
          rw [hfactor]
    _ = FinKernel.compose (FinKernel.dirac obsB)
        (FinKernel.compose (FinKernel.dirac k) g) :=
          (finKernel_compose_associative g (FinKernel.dirac k) (FinKernel.dirac obsB)).symm

/-- Non-identity future context that collapses hidden state 1 to hidden state 0. -/
def finCollapseHidden3 : Fin 3 → Fin 3 :=
  finSelectorAt (2 : Fin 3) (2 : Fin 3) (0 : Fin 3)

/-- The hidden-state collapse genuinely is not the identity map. -/
theorem finCollapseHidden3_ne_identity :
    finCollapseHidden3 ≠ (fun x : Fin 3 => x) := by
  intro h
  have hv := congrFun h (1 : Fin 3)
  simp [finCollapseHidden3, finSelectorAt] at hv

/-- The hidden-state collapse factors through the coarse merge01 observation. -/
theorem finCollapseHidden3_factors_merge01 :
    FinKernel.FactorsObservation finMerge01 finMerge01 finCollapseHidden3 := by
  refine ⟨fun y => y, ?_⟩
  intro x
  by_cases h2 : x = (2 : Fin 3)
  · subst x
    simp [finCollapseHidden3, finSelectorAt, finMerge01]
  · simp [finCollapseHidden3, finSelectorAt, finMerge01, h2]

/-- The two hidden deterministic source states differ as exact kernels. -/
theorem finKernel_zero3_ne_one3 : finKernelZero3 ≠ finKernelOne3 := by
  intro h
  have hv := congrArg (fun k => k (0 : Fin 1) (0 : Fin 3)) h
  simp [finKernelZero3, finKernelOne3, FinKernel.dirac] at hv

/--
The existing non-trivial coarse equivalence survives the non-identity allowed
future context because that context factors through the observation.
-/
theorem finKernel_merge01_equivalence_survives_hidden_collapse :
    FinKernel.ObservedEq (FinKernel.dirac finMerge01)
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelZero3)
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelOne3) := by
  exact finKernel_observedEq_postcompose_dirac_of_factors
    finMerge01 finMerge01 finCollapseHidden3
    finCollapseHidden3_factors_merge01
    finKernel_merge01_observes_zero_one_equal

/--
The previously used future map that moves hidden state 1 into visible state 2
cannot factor through the merge01 observation.
-/
theorem finMoveOneToTwo_not_factors_merge01 :
    ¬ FinKernel.FactorsObservation finMerge01 finMerge01 finMoveOneToTwo := by
  intro hfac
  rcases hfac with ⟨h, hcomm⟩
  have h0 := hcomm (0 : Fin 3)
  have h1 := hcomm (1 : Fin 3)
  simp [finMerge01, finMoveOneToTwo] at h0 h1
  grind

/--
Policy exclusion and semantic failure coincide for the known negative control:
the disallowed future map breaks the merge01 observational equivalence.
-/
theorem finKernel_excluded_move_breaks_merge01 :
    ¬ FinKernel.ObservedEq (FinKernel.dirac finMerge01)
      (FinKernel.compose (FinKernel.dirac finMoveOneToTwo) finKernelZero3)
      (FinKernel.compose (FinKernel.dirac finMoveOneToTwo) finKernelOne3) := by
  exact finKernel_fixed_probe_not_postcomposition_stable

/--
A concrete non-trivial exact quotient is therefore preserved by a non-identity
restricted context while a context that refines the hidden distinction is both
excluded by the factorization policy and semantically distinguishing.
-/
theorem finKernel_restricted_context_nontriviality_witness :
    finKernelZero3 ≠ finKernelOne3 ∧
    FinKernel.ObservedEq (FinKernel.dirac finMerge01)
      finKernelZero3 finKernelOne3 ∧
    finCollapseHidden3 ≠ (fun x : Fin 3 => x) ∧
    FinKernel.FactorsObservation finMerge01 finMerge01 finCollapseHidden3 ∧
    FinKernel.ObservedEq (FinKernel.dirac finMerge01)
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelZero3)
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelOne3) ∧
    ¬ FinKernel.FactorsObservation finMerge01 finMerge01 finMoveOneToTwo := by
  exact ⟨finKernel_zero3_ne_one3,
    finKernel_merge01_observes_zero_one_equal,
    finCollapseHidden3_ne_identity,
    finCollapseHidden3_factors_merge01,
    finKernel_merge01_equivalence_survives_hidden_collapse,
    finMoveOneToTwo_not_factors_merge01⟩

end RelayTheory
