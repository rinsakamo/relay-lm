import RelayTheory.RightFunctionalityReconstruction

namespace RelayTheory

namespace FinKernel

/--
Reachable forward dynamics with total coverage in both directions but no
correspondence-functionality fields.  This is intentionally directional: it is
a candidate quotient/simulation preorder, not an equivalence interface.
-/
structure SurjectiveForwardReachableDynamicsCorrespondence {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop
  total_left : ∀ {s}, ReachableResidualState P K s →
    ∃ t, ReachableResidualState P L t ∧ rel s t
  total_right : ∀ {t}, ReachableResidualState P L t →
    ∃ s, ReachableResidualState P K s ∧ rel s t
  successor_forward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P K sK tK uK →
    SourceSubstitutionSuccessorRel P L sL tL uL

/-- Existence of a total surjective forward reachable-dynamics correspondence. -/
def SurjectiveForwardReachableDynamicsLe {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (SurjectiveForwardReachableDynamicsCorrespondence P K L)

end FinKernel

/--
Root preservation still reconstructs without either correspondence-functionality
field.  Totality and forward preservation make any reachable image of the source
root a two-sided target unit; target-unit uniqueness identifies it with the
semantic root.
-/
theorem finKernel_surjectiveForward_root {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.SurjectiveForwardReachableDynamicsCorrespondence P K L) :
    h.rel (FinKernel.ResidualIdentityState P K)
      (FinKernel.ResidualIdentityState P L) := by
  have hRootKReach : FinKernel.ReachableResidualState P K
      (FinKernel.ResidualIdentityState P K) :=
    finKernel_residualIdentityState_reachable
  rcases h.total_left hRootKReach with ⟨tL, htL, hRootRel⟩
  have hRootKUnit := finKernel_residualIdentityState_reachableTwoSidedUnit P K
  have htUnit : FinKernel.ReachableTwoSidedUnit P L tL := by
    refine ⟨htL, ?_⟩
    intro sL hsL
    rcases h.total_right hsL with ⟨sK, hsK, hsRel⟩
    have hUnitsK := hRootKUnit.2 sK hsK
    exact ⟨
      h.successor_forward hRootRel hsRel hsRel hUnitsK.1,
      h.successor_forward hsRel hRootRel hsRel hUnitsK.2⟩
  have hRootLUnit := finKernel_residualIdentityState_reachableTwoSidedUnit P L
  have htRoot : tL = FinKernel.ResidualIdentityState P L :=
    finKernel_reachableTwoSidedUnit_eq htUnit hRootLUnit
  simpa only [htRoot] using hRootRel

/--
Output-side uniqueness is structural even in the bare total forward interface.
No correspondence functionality assumption is used: the target left-unit law
forces any two reachable right images of one source state to agree extensionally.
-/
theorem finKernel_surjectiveForward_rightFunctional_on_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.SurjectiveForwardReachableDynamicsCorrespondence P K L)
    {sK : FinKernel.FullFutureResponseSpace P K}
    {tL uL : FinKernel.FullFutureResponseSpace P L}
    (hsK : FinKernel.ReachableResidualState P K sK)
    (htL : FinKernel.ReachableResidualState P L tL)
    (hst : h.rel sK tL)
    (hsu : h.rel sK uL) :
    FinKernel.FullFutureResponseSpaceEq tL uL := by
  have hRootRel := finKernel_surjectiveForward_root h
  have hRootKUnit := finKernel_residualIdentityState_reachableTwoSidedUnit P K
  have hSuccK : FinKernel.SourceSubstitutionSuccessorRel P K
      (FinKernel.ResidualIdentityState P K) sK sK :=
    (hRootKUnit.2 sK hsK).1
  have hSuccL : FinKernel.SourceSubstitutionSuccessorRel P L
      (FinKernel.ResidualIdentityState P L) tL uL :=
    h.successor_forward hRootRel hst hsu hSuccK
  let lawsL := finKernel_sourceSubstitutionSuccessorRel_laws P L
  have huLtL : FinKernel.FullFutureResponseSpaceEq uL tL :=
    lawsL.identity_earlier htL hSuccL
  exact finKernel_fullFutureResponseSpaceEq_symm huLtL

/-- Forget input injectivity from the #2925 interface. -/
def finKernel_surjectiveForward_of_leftFunctional {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.LeftFunctionalForwardReachableDynamicsCorrespondence P K L) :
    FinKernel.SurjectiveForwardReachableDynamicsCorrespondence P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    total_right := h.total_right
    successor_forward := h.successor_forward
  }

/-- Every reachable-dynamics equivalence induces the weaker forward quotient relation. -/
theorem finKernel_reachableDynamicsEq_implies_surjectiveForwardReachableDynamicsLe
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableDynamicsEq P K L) :
    FinKernel.SurjectiveForwardReachableDynamicsLe P K L := by
  have hLeft : FinKernel.LeftFunctionalForwardReachableDynamicsEq P K L :=
    (finKernel_leftFunctionalForwardReachableDynamicsEq_iff_reachableDynamicsEq).2 h
  rcases hLeft with ⟨c⟩
  exact ⟨finKernel_surjectiveForward_of_leftFunctional c⟩

/-- The weakened forward relation is reflexive. -/
theorem finKernel_surjectiveForwardReachableDynamicsLe_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.SurjectiveForwardReachableDynamicsLe P K K := by
  refine ⟨{
    rel := fun s t => s = t
    total_left := ?_
    total_right := ?_
    successor_forward := ?_
  }⟩
  · intro s hs
    exact ⟨s, hs, rfl⟩
  · intro t ht
    exact ⟨t, ht, rfl⟩
  · intro sK tK uK sL tL uL hs ht hu hSucc
    subst sL
    subst tL
    subst uL
    exact hSucc

/-- The weakened forward relation composes, hence forms a preorder candidate. -/
theorem finKernel_surjectiveForwardReachableDynamicsLe_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.SurjectiveForwardReachableDynamicsLe P K L)
    (hLM : FinKernel.SurjectiveForwardReachableDynamicsLe P L M) :
    FinKernel.SurjectiveForwardReachableDynamicsLe P K M := by
  rcases hKL with ⟨cKL⟩
  rcases hLM with ⟨cLM⟩
  refine ⟨{
    rel := fun s u => ∃ t, cKL.rel s t ∧ cLM.rel t u
    total_left := ?_
    total_right := ?_
    successor_forward := ?_
  }⟩
  · intro s hs
    rcases cKL.total_left hs with ⟨t, ht, hst⟩
    rcases cLM.total_left ht with ⟨u, hu, htu⟩
    exact ⟨u, hu, t, hst, htu⟩
  · intro u hu
    rcases cLM.total_right hu with ⟨t, ht, htu⟩
    rcases cKL.total_right ht with ⟨s, hs, hst⟩
    exact ⟨s, hs, t, hst, htu⟩
  · intro sK tK uK sM tM uM hsRel htRel huRel hSuccK
    rcases hsRel with ⟨sL, hsKL, hsLM⟩
    rcases htRel with ⟨tL, htKL, htLM⟩
    rcases huRel with ⟨uL, huKL, huLM⟩
    have hSuccL := cKL.successor_forward hsKL htKL huKL hSuccK
    exact cLM.successor_forward hsLM htLM huLM hSuccL

namespace FinKernel

/--
The concrete many-to-one quotient relation for #2927.  Every reachable all-probes
safe state is sent to the literal root of the all-probes empty frame.
-/
def safeToEmptyForwardRel
    (s : FullFutureResponseSpace (allProbes 3) merge01SafeContextFamily3)
    (t : FullFutureResponseSpace (allProbes 3) (emptyFutureContextFamily 3)) : Prop :=
  ReachableResidualState (allProbes 3) merge01SafeContextFamily3 s ∧
  t = ResidualIdentityState (allProbes 3) (emptyFutureContextFamily 3)

end FinKernel

/-- The safe→empty one-point quotient is a total surjective forward correspondence. -/
def finKernel_allProbes_safeToEmpty_surjectiveForwardCorrespondence :
    FinKernel.SurjectiveForwardReachableDynamicsCorrespondence
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact {
    rel := FinKernel.safeToEmptyForwardRel
    total_left := by
      intro s hs
      exact ⟨FinKernel.ResidualIdentityState
          (FinKernel.allProbes 3) (FinKernel.emptyFutureContextFamily 3),
        finKernel_residualIdentityState_reachable, hs, rfl⟩
    total_right := by
      intro t ht
      have htRoot : FinKernel.FullFutureResponseSpaceEq t
          (FinKernel.ResidualIdentityState
            (FinKernel.allProbes 3) (FinKernel.emptyFutureContextFamily 3)) :=
        finKernel_allProbes_empty_reachableResponseTrivial t ht
      have htEq : t = FinKernel.ResidualIdentityState
          (FinKernel.allProbes 3) (FinKernel.emptyFutureContextFamily 3) :=
        (finKernel_fullFutureResponseSpaceEq_iff_eq).1 htRoot
      exact ⟨FinKernel.ResidualIdentityState
          (FinKernel.allProbes 3) FinKernel.merge01SafeContextFamily3,
        finKernel_residualIdentityState_reachable,
        finKernel_residualIdentityState_reachable,
        htEq⟩
    successor_forward := by
      intro sK tK uK sL tL uL hsRel htRel huRel hSuccK
      rcases hsRel with ⟨_, rfl⟩
      rcases htRel with ⟨_, rfl⟩
      rcases huRel with ⟨_, rfl⟩
      have hRootReach : FinKernel.ReachableResidualState
          (FinKernel.allProbes 3) (FinKernel.emptyFutureContextFamily 3)
          (FinKernel.ResidualIdentityState
            (FinKernel.allProbes 3) (FinKernel.emptyFutureContextFamily 3)) :=
        finKernel_residualIdentityState_reachable
      have hRootUnit := finKernel_residualIdentityState_reachableTwoSidedUnit
        (FinKernel.allProbes 3) (FinKernel.emptyFutureContextFamily 3)
      exact (hRootUnit.2 _ hRootReach).1
  }

/-- Existence of the explicit safe→empty forward quotient. -/
theorem finKernel_allProbes_safe_empty_surjectiveForwardReachableDynamicsLe :
    FinKernel.SurjectiveForwardReachableDynamicsLe
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact ⟨finKernel_allProbes_safeToEmpty_surjectiveForwardCorrespondence⟩

/-- The hidden-collapse safe response is extensionally distinct from the safe root. -/
theorem finKernel_allProbes_safe_collapse_not_root_responseEq :
    ¬ FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState
        (FinKernel.allProbes 3)
        FinKernel.merge01SafeContextFamily3
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe)
      (FinKernel.ResidualIdentityState
        (FinKernel.allProbes 3)
        FinKernel.merge01SafeContextFamily3) := by
  intro hEq
  have hResidual : FinKernel.IdentityResidualStateEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity := by
    simpa [FinKernel.ResidualIdentityState,
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

/-- The explicit safe→empty quotient is genuinely non-injective. -/
theorem finKernel_allProbes_safeToEmpty_not_leftFunctional :
    ¬ (∀ {s u t},
      FinKernel.safeToEmptyForwardRel s t →
      FinKernel.safeToEmptyForwardRel u t →
      FinKernel.FullFutureResponseSpaceEq s u) := by
  intro hLeft
  let rootSafe := FinKernel.ResidualIdentityState
    (FinKernel.allProbes 3) FinKernel.merge01SafeContextFamily3
  let collapseSafe := FinKernel.IdentityResidualState
    (FinKernel.allProbes 3)
    FinKernel.merge01SafeContextFamily3
    (FinKernel.dirac finCollapseHidden3)
    finKernel_merge01_collapse_generated_safe
  let rootEmpty := FinKernel.ResidualIdentityState
    (FinKernel.allProbes 3) (FinKernel.emptyFutureContextFamily 3)
  have hRootReach : FinKernel.ReachableResidualState
      (FinKernel.allProbes 3) FinKernel.merge01SafeContextFamily3 rootSafe :=
    finKernel_residualIdentityState_reachable
  have hCollapseReach : FinKernel.ReachableResidualState
      (FinKernel.allProbes 3) FinKernel.merge01SafeContextFamily3 collapseSafe :=
    finKernel_generated_identityResidualState_reachable
      finKernel_merge01_collapse_generated_safe
  have hRootRel : FinKernel.safeToEmptyForwardRel rootSafe rootEmpty :=
    ⟨hRootReach, rfl⟩
  have hCollapseRel : FinKernel.safeToEmptyForwardRel collapseSafe rootEmpty :=
    ⟨hCollapseReach, rfl⟩
  have hEq : FinKernel.FullFutureResponseSpaceEq collapseSafe rootSafe :=
    hLeft hCollapseRel hRootRel
  exact finKernel_allProbes_safe_collapse_not_root_responseEq hEq

/--
Any reachable-dynamics equivalence into a reachable-response-trivial target
would make the source reachable-response-trivial as well.  This is a direct
bi-functional-carrier argument.
-/
theorem finKernel_reachableResponseTrivial_of_reachableDynamicsEq_target {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hL : FinKernel.ReachableResponseTrivial P L)
    (hDyn : FinKernel.ReachableDynamicsEq P K L) :
    FinKernel.ReachableResponseTrivial P K := by
  rcases hDyn with ⟨c⟩
  intro s hs
  rcases c.total_left hs with ⟨t, ht, hst⟩
  have hRootKReach : FinKernel.ReachableResidualState P K
      (FinKernel.ResidualIdentityState P K) :=
    finKernel_residualIdentityState_reachable
  rcases c.total_left hRootKReach with ⟨r, hr, hroot⟩
  have htr : FinKernel.FullFutureResponseSpaceEq t r :=
    finKernel_fullFutureResponseSpaceEq_trans (hL t ht)
      (finKernel_fullFutureResponseSpaceEq_symm (hL r hr))
  have htrEq : t = r := (finKernel_fullFutureResponseSpaceEq_iff_eq).1 htr
  subst r
  exact c.left_functional hst hroot

/-- Safe and empty are not equivalent reachable dynamics: the target is singleton, the source is not. -/
theorem finKernel_allProbes_safe_empty_not_reachableDynamicsEq :
    ¬ FinKernel.ReachableDynamicsEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  intro hDyn
  apply finKernel_allProbes_safe_not_reachableResponseTrivial
  exact finKernel_reachableResponseTrivial_of_reachableDynamicsEq_target
    finKernel_allProbes_empty_reachableResponseTrivial hDyn

/-- Strictness: total surjective forward dynamics is strictly coarser than dynamics equivalence. -/
theorem finKernel_surjectiveForwardReachableDynamicsLe_strict_counterexample :
    FinKernel.SurjectiveForwardReachableDynamicsLe
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) ∧
    ¬ FinKernel.ReachableDynamicsEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact ⟨finKernel_allProbes_safe_empty_surjectiveForwardReachableDynamicsLe,
    finKernel_allProbes_safe_empty_not_reachableDynamicsEq⟩

/-- Acceptance bundle for #2927. -/
theorem finKernel_left_functionality_boundary_bundle :
    (∀ {n : Nat}
      (P : FinKernel.ProbeFamily n)
      (K : FinKernel.FutureContextFamily n),
      FinKernel.SurjectiveForwardReachableDynamicsLe P K K) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L M : FinKernel.FutureContextFamily n},
      FinKernel.SurjectiveForwardReachableDynamicsLe P K L →
      FinKernel.SurjectiveForwardReachableDynamicsLe P L M →
      FinKernel.SurjectiveForwardReachableDynamicsLe P K M) ∧
    FinKernel.SurjectiveForwardReachableDynamicsLe
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) ∧
    ¬ FinKernel.ReachableDynamicsEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact ⟨finKernel_surjectiveForwardReachableDynamicsLe_refl,
    fun hKL hLM => finKernel_surjectiveForwardReachableDynamicsLe_trans hKL hLM,
    finKernel_allProbes_safe_empty_surjectiveForwardReachableDynamicsLe,
    finKernel_allProbes_safe_empty_not_reachableDynamicsEq⟩

end RelayTheory
