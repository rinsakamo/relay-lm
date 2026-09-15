import RelayTheory.SuccessorReflectionReconstruction
import RelayTheory.ActionQuotientSufficiency

namespace RelayTheory

namespace FinKernel

/--
A forward injective embedding of the reachable source-substitution dynamics.
This is exactly `ForwardReachableDynamicsCorrespondence` from #2908 with
`total_right` deleted.  It need not cover every reachable target state.
-/
structure ReachableDynamicsEmbedding {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop
  total_left : ∀ {s}, ReachableResidualState P K s →
    ∃ t, ReachableResidualState P L t ∧ rel s t
  right_functional : ∀ {s t u}, rel s t → rel s u →
    FullFutureResponseSpaceEq t u
  left_functional : ∀ {s u t}, rel s t → rel u t →
    FullFutureResponseSpaceEq s u
  successor_forward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P K sK tK uK →
    SourceSubstitutionSuccessorRel P L sL tL uL

/-- Existence of a forward injective reachable-dynamics embedding. -/
def ReachableDynamicsEmbeds {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (ReachableDynamicsEmbedding P K L)

end FinKernel

/-- Identity is a reachable-dynamics embedding. -/
def finKernel_reachableDynamicsEmbedding_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ReachableDynamicsEmbedding P K K := by
  exact {
    rel := fun s t => s = t
    total_left := by
      intro s hs
      exact ⟨s, hs, rfl⟩
    right_functional := by
      intro s t u hst hsu
      exact (finKernel_fullFutureResponseSpaceEq_iff_eq).2
        (hst.symm.trans hsu)
    left_functional := by
      intro s u t hst hut
      exact (finKernel_fullFutureResponseSpaceEq_iff_eq).2
        (hst.trans hut.symm)
    successor_forward := by
      intro sK tK uK sL tL uL hs ht hu hSucc
      subst sL
      subst tL
      subst uL
      exact hSucc
  }

/-- Reachable-dynamics embeddings compose by relational composition. -/
def finKernel_reachableDynamicsEmbedding_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.ReachableDynamicsEmbedding P K L)
    (hLM : FinKernel.ReachableDynamicsEmbedding P L M) :
    FinKernel.ReachableDynamicsEmbedding P K M := by
  exact {
    rel := fun s u => ∃ t, hKL.rel s t ∧ hLM.rel t u
    total_left := by
      intro s hs
      rcases hKL.total_left hs with ⟨t, ht, hst⟩
      rcases hLM.total_left ht with ⟨u, hu, htu⟩
      exact ⟨u, hu, ⟨t, hst, htu⟩⟩
    right_functional := by
      intro s u v hsu hsv
      rcases hsu with ⟨t, hst, htu⟩
      rcases hsv with ⟨t', hst', ht'v⟩
      have htt' : FinKernel.FullFutureResponseSpaceEq t t' :=
        hKL.right_functional hst hst'
      have httEq : t = t' :=
        (finKernel_fullFutureResponseSpaceEq_iff_eq).1 htt'
      subst t'
      exact hLM.right_functional htu ht'v
    left_functional := by
      intro s v u hsu hvu
      rcases hsu with ⟨t, hst, htu⟩
      rcases hvu with ⟨t', hvt', ht'u⟩
      have htt' : FinKernel.FullFutureResponseSpaceEq t t' :=
        hLM.left_functional htu ht'u
      have httEq : t = t' :=
        (finKernel_fullFutureResponseSpaceEq_iff_eq).1 htt'
      subst t'
      exact hKL.left_functional hst hvt'
    successor_forward := by
      intro sK tK uK sM tM uM hsRel htRel huRel hSuccK
      rcases hsRel with ⟨sL, hsKL, hsLM⟩
      rcases htRel with ⟨tL, htKL, htLM⟩
      rcases huRel with ⟨uL, huKL, huLM⟩
      have hSuccL := hKL.successor_forward hsKL htKL huKL hSuccK
      exact hLM.successor_forward hsLM htLM huLM hSuccL
  }

/-- Embedding existence is reflexive. -/
theorem finKernel_reachableDynamicsEmbeds_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ReachableDynamicsEmbeds P K K := by
  exact ⟨finKernel_reachableDynamicsEmbedding_refl P K⟩

/-- Embedding existence is transitive. -/
theorem finKernel_reachableDynamicsEmbeds_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.ReachableDynamicsEmbeds P K L)
    (hLM : FinKernel.ReachableDynamicsEmbeds P L M) :
    FinKernel.ReachableDynamicsEmbeds P K M := by
  rcases hKL with ⟨eKL⟩
  rcases hLM with ⟨eLM⟩
  exact ⟨finKernel_reachableDynamicsEmbedding_trans eKL eLM⟩

/-- Forget right-totality from the #2908 forward correspondence. -/
def finKernel_reachableDynamicsEmbedding_of_forward {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsCorrespondence P K L) :
    FinKernel.ReachableDynamicsEmbedding P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    right_functional := h.right_functional
    left_functional := h.left_functional
    successor_forward := h.successor_forward
  }

/-- Reachable-dynamics equality therefore always yields an embedding. -/
theorem finKernel_forwardReachableDynamicsEq_implies_reachableDynamicsEmbeds
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsEq P K L) :
    FinKernel.ReachableDynamicsEmbeds P K L := by
  rcases h with ⟨e⟩
  exact ⟨finKernel_reachableDynamicsEmbedding_of_forward e⟩

/-- The #2879 dynamics-equivalence relation also always yields an embedding. -/
theorem finKernel_reachableDynamicsEq_implies_reachableDynamicsEmbeds {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableDynamicsEq P K L) :
    FinKernel.ReachableDynamicsEmbeds P K L := by
  exact finKernel_forwardReachableDynamicsEq_implies_reachableDynamicsEmbeds
    ((finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq).2 h)

/--
Under all exact probes, the singleton reachable dynamics of the empty frame
embeds into the safe collapse-generated frame by mapping its unique reachable
state to the safe root.
-/
def finKernel_allProbes_empty_safe_embedding :
    FinKernel.ReachableDynamicsEmbedding
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  let P := FinKernel.allProbes 3
  let K := FinKernel.emptyFutureContextFamily 3
  let L := FinKernel.merge01SafeContextFamily3
  let rootK := FinKernel.ResidualIdentityState P K
  let rootL := FinKernel.ResidualIdentityState P L
  exact {
    rel := fun s t => s = rootK ∧ t = rootL
    total_left := by
      intro s hs
      have hsRootExt : FinKernel.FullFutureResponseSpaceEq s rootK :=
        finKernel_allProbes_empty_reachableResponseTrivial s hs
      have hsRoot : s = rootK :=
        (finKernel_fullFutureResponseSpaceEq_iff_eq).1 hsRootExt
      have hRootL : FinKernel.ReachableResidualState P L rootL :=
        finKernel_residualIdentityState_reachable
      exact ⟨rootL, hRootL, hsRoot, rfl⟩
    right_functional := by
      intro s t u hst hsu
      exact (finKernel_fullFutureResponseSpaceEq_iff_eq).2
        (hst.2.trans hsu.2.symm)
    left_functional := by
      intro s u t hst hut
      exact (finKernel_fullFutureResponseSpaceEq_iff_eq).2
        (hst.1.trans hut.1.symm)
    successor_forward := by
      intro sK tK uK sL tL uL hsRel htRel huRel hSuccK
      rcases hsRel with ⟨hsK, hsL⟩
      rcases htRel with ⟨htK, htL⟩
      rcases huRel with ⟨huK, huL⟩
      subst sK
      subst tK
      subst uK
      subst sL
      subst tL
      subst uL
      have hUnit := finKernel_residualIdentityState_reachableTwoSidedUnit P L
      exact (hUnit.2 rootL hUnit.1).1
  }

/-- The all-probes empty frame embeds into the safe frame. -/
theorem finKernel_allProbes_empty_safe_reachableDynamicsEmbeds :
    FinKernel.ReachableDynamicsEmbeds
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact ⟨finKernel_allProbes_empty_safe_embedding⟩

/--
There is no embedding in the reverse direction: the safe root and the reachable
hidden-collapse state would both have to inject into the unique reachable empty
state, contradicting their all-probes separation.
-/
theorem finKernel_allProbes_safe_empty_not_reachableDynamicsEmbeds :
    ¬ FinKernel.ReachableDynamicsEmbeds
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  rintro ⟨e⟩
  let P := FinKernel.allProbes 3
  let K := FinKernel.merge01SafeContextFamily3
  let L := FinKernel.emptyFutureContextFamily 3
  let rootK := FinKernel.ResidualIdentityState P K
  let collapseK := FinKernel.IdentityResidualState P K
    (FinKernel.dirac finCollapseHidden3)
    finKernel_merge01_collapse_generated_safe
  have hRootReach : FinKernel.ReachableResidualState P K rootK :=
    finKernel_residualIdentityState_reachable
  have hCollapseReach : FinKernel.ReachableResidualState P K collapseK :=
    finKernel_generated_identityResidualState_reachable
      finKernel_merge01_collapse_generated_safe
  rcases e.total_left hRootReach with ⟨tRoot, htRoot, hRootRel⟩
  rcases e.total_left hCollapseReach with
    ⟨tCollapse, htCollapse, hCollapseRel⟩
  have htRootExt := finKernel_allProbes_empty_reachableResponseTrivial
    tRoot htRoot
  have htCollapseExt := finKernel_allProbes_empty_reachableResponseTrivial
    tCollapse htCollapse
  have htSameExt : FinKernel.FullFutureResponseSpaceEq tRoot tCollapse :=
    finKernel_fullFutureResponseSpaceEq_trans htRootExt
      (finKernel_fullFutureResponseSpaceEq_symm htCollapseExt)
  have htSame : tRoot = tCollapse :=
    (finKernel_fullFutureResponseSpaceEq_iff_eq).1 htSameExt
  subst tCollapse
  have hRootCollapse : FinKernel.FullFutureResponseSpaceEq rootK collapseK :=
    e.left_functional hRootRel hCollapseRel
  have hResidual : FinKernel.IdentityResidualStateEq
      P K
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity := by
    simpa [P, K, rootK, collapseK,
      FinKernel.ResidualIdentityState,
      FinKernel.IdentityResidualStateEq] using
      (finKernel_fullFutureResponseSpaceEq_symm hRootCollapse)
  have hContext : FinKernel.ContextualActionEq
      P K
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity).1 hResidual
  have hLiteral : FinKernel.dirac finCollapseHidden3 = FinKernel.identity 3 :=
    (finKernel_contextualActionEq_allProbes_iff_eq
      K
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)).1 hContext
  exact finKernel_identity3_ne_hidden_collapse hLiteral.symm

/-- Reachable-dynamics embedding is not symmetric. -/
theorem finKernel_reachableDynamicsEmbeds_not_symmetric :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.ReachableDynamicsEmbeds (FinKernel.allProbes 3) K L →
      FinKernel.ReachableDynamicsEmbeds (FinKernel.allProbes 3) L K) := by
  intro hSymm
  exact finKernel_allProbes_safe_empty_not_reachableDynamicsEmbeds
    (hSymm _ _ finKernel_allProbes_empty_safe_reachableDynamicsEmbeds)

/--
Right-totality is not reconstructible from the remaining embedding fields in
general: if every embedding extended to #2908 dynamics equality, the strict
empty-to-safe embedding would imply a reverse embedding by symmetry.
-/
theorem finKernel_reachableDynamicsEmbeds_does_not_imply_forwardReachableDynamicsEq :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.ReachableDynamicsEmbeds (FinKernel.allProbes 3) K L →
      FinKernel.ForwardReachableDynamicsEq (FinKernel.allProbes 3) K L) := by
  intro hPromote
  have hEq : FinKernel.ForwardReachableDynamicsEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 :=
    hPromote _ _ finKernel_allProbes_empty_safe_reachableDynamicsEmbeds
  have hEqRev : FinKernel.ForwardReachableDynamicsEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) :=
    finKernel_forwardReachableDynamicsEq_symm hEq
  exact finKernel_allProbes_safe_empty_not_reachableDynamicsEmbeds
    (finKernel_forwardReachableDynamicsEq_implies_reachableDynamicsEmbeds hEqRev)

/-- Acceptance bundle for #2910. -/
theorem finKernel_reachable_dynamics_embedding_bundle :
    (∀ {n : Nat}
      (P : FinKernel.ProbeFamily n)
      (K : FinKernel.FutureContextFamily n),
      FinKernel.ReachableDynamicsEmbeds P K K) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L M : FinKernel.FutureContextFamily n},
      FinKernel.ReachableDynamicsEmbeds P K L →
      FinKernel.ReachableDynamicsEmbeds P L M →
      FinKernel.ReachableDynamicsEmbeds P K M) ∧
    FinKernel.ReachableDynamicsEmbeds
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.ReachableDynamicsEmbeds
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact ⟨finKernel_reachableDynamicsEmbeds_refl,
    fun hKL hLM => finKernel_reachableDynamicsEmbeds_trans hKL hLM,
    finKernel_allProbes_empty_safe_reachableDynamicsEmbeds,
    finKernel_allProbes_safe_empty_not_reachableDynamicsEmbeds⟩

end RelayTheory
