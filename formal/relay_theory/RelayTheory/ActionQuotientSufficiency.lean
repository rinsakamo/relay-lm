import RelayTheory.OperationalAccessRefinement

namespace RelayTheory

/--
With every exact downstream probe available, contextual action equivalence is
literal kernel equality for every admissibility frame.  The generated future
closure cannot coarsen this relation because identity is always generated.
-/
theorem finKernel_contextualActionEq_allProbes_iff_eq {n : Nat}
    (K : FinKernel.FutureContextFamily n)
    (k l : FinKernel n n) :
    FinKernel.ContextualActionEq (FinKernel.allProbes n) K k l ↔ k = l := by
  constructor
  · intro h
    have hAction : FinKernel.ContextActionEq (FinKernel.allProbes n) k l :=
      finKernel_contextualActionEq_implies_actionEq h
    have hProbe : FinKernel.ProbeEq (FinKernel.allProbes n)
        (FinKernel.compose k (FinKernel.identity n))
        (FinKernel.compose l (FinKernel.identity n)) :=
      hAction (FinKernel.identity n)
    have hEq := (finKernel_probeEq_all_iff_eq
      (FinKernel.compose k (FinKernel.identity n))
      (FinKernel.compose l (FinKernel.identity n))).1 hProbe
    simpa only [finKernel_compose_identity_before] using hEq
  · rintro rfl
    exact finKernel_contextualActionEq_refl (FinKernel.allProbes n) K k

/--
Under all exact probes, every pair of admissibility frames induces the same
contextual-action quotient: literal equality of endomorphic kernels.
-/
theorem finKernel_allProbes_accessActionEq {n : Nat}
    (K L : FinKernel.FutureContextFamily n) :
    FinKernel.AccessActionEq (FinKernel.allProbes n) K L := by
  constructor
  · intro k l hL
    exact (finKernel_contextualActionEq_allProbes_iff_eq K k l).2
      ((finKernel_contextualActionEq_allProbes_iff_eq L k l).1 hL)
  · intro k l hK
    exact (finKernel_contextualActionEq_allProbes_iff_eq L k l).2
      ((finKernel_contextualActionEq_allProbes_iff_eq K k l).1 hK)

/-- The no-generator frame has a singleton reachable response quotient even under all probes. -/
theorem finKernel_allProbes_empty_reachableResponseTrivial {n : Nat} :
    FinKernel.ReachableResponseTrivial
      (FinKernel.allProbes n)
      (FinKernel.emptyFutureContextFamily n) := by
  exact finKernel_reachableResponseTrivial_of_generated_contextual_identity
    (fun hk => finKernel_empty_generated_contextual_identity hk)

/--
The safe collapse-generated frame is not reachable-response-trivial under all
exact probes: hidden collapse is generated and is literally distinct from the
identity action, hence reaches a distinct residual response state.
-/
theorem finKernel_allProbes_safe_not_reachableResponseTrivial :
    ¬ FinKernel.ReachableResponseTrivial
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3 := by
  intro hTrivial
  have hReach : FinKernel.ReachableResidualState
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.IdentityResidualState
        (FinKernel.allProbes 3)
        FinKernel.merge01SafeContextFamily3
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe) :=
    finKernel_generated_identityResidualState_reachable
      finKernel_merge01_collapse_generated_safe
  have hEq := hTrivial _ hReach
  have hResidual : FinKernel.IdentityResidualStateEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity := by
    simpa [FinKernel.ReachableResponseTrivial,
      FinKernel.ResidualIdentityState,
      FinKernel.IdentityResidualStateEq] using hEq
  have hContext : FinKernel.ContextualActionEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity).1 hResidual
  have hLiteral : FinKernel.dirac finCollapseHidden3 = FinKernel.identity 3 :=
    (finKernel_contextualActionEq_allProbes_iff_eq
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)).1 hContext
  exact finKernel_identity3_ne_hidden_collapse hLiteral.symm

/--
Whole reachable-response efficacy equivalence transports singleton-root
triviality.  This uses only the abstract dynamics-equivalence interface, not a
literal context-domain map.
-/
theorem finKernel_reachableResponseTrivial_of_accessEfficacyEq_left {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hK : FinKernel.ReachableResponseTrivial P K)
    (hEff : FinKernel.AccessEfficacyEq P K L) :
    FinKernel.ReachableResponseTrivial P L := by
  rcases hEff with ⟨e⟩
  intro s hs
  have hBack : FinKernel.FullFutureResponseSpaceEq
      (e.backward s)
      (FinKernel.ResidualIdentityState P K) :=
    hK (e.backward s) (e.backward_reachable hs)
  have hBackEq : FinKernel.FullFutureResponseSpaceEq
      (e.backward s)
      (e.backward (FinKernel.ResidualIdentityState P L)) :=
    finKernel_fullFutureResponseSpaceEq_trans hBack
      (finKernel_fullFutureResponseSpaceEq_symm e.root_backward)
  exact e.backward_reflects_eq hs
    finKernel_residualIdentityState_reachable hBackEq

/--
The empty and safe frames have the same all-probes action partition but are not
whole-dynamics efficacy-equivalent, because only the latter realizes the
non-identity hidden-collapse class.
-/
theorem finKernel_allProbes_empty_safe_not_accessEfficacyEq :
    ¬ FinKernel.AccessEfficacyEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  intro hEff
  apply finKernel_allProbes_safe_not_reachableResponseTrivial
  exact finKernel_reachableResponseTrivial_of_accessEfficacyEq_left
    finKernel_allProbes_empty_reachableResponseTrivial hEff

/--
Grand-Null refutation: mutual operational action refinement does not in general
determine whole reachable response/source-substitution dynamics.
-/
theorem finKernel_accessActionEq_does_not_imply_accessEfficacyEq :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.AccessActionEq (FinKernel.allProbes 3) K L →
      FinKernel.AccessEfficacyEq (FinKernel.allProbes 3) K L) := by
  intro hConverse
  exact finKernel_allProbes_empty_safe_not_accessEfficacyEq
    (hConverse _ _ (finKernel_allProbes_accessActionEq _ _))

/--
Acceptance bundle for #2861: identical contextual-action quotient, different
reachable support, and therefore different whole reachable dynamics.
-/
theorem finKernel_action_quotient_sufficiency_counterexample_bundle :
    FinKernel.AccessActionEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    FinKernel.ReachableResponseTrivial
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3) ∧
    ¬ FinKernel.ReachableResponseTrivial
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.AccessEfficacyEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact ⟨finKernel_allProbes_accessActionEq _ _,
    finKernel_allProbes_empty_reachableResponseTrivial,
    finKernel_allProbes_safe_not_reachableResponseTrivial,
    finKernel_allProbes_empty_safe_not_accessEfficacyEq⟩

end RelayTheory
