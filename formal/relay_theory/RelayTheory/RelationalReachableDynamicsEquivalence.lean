import RelayTheory.ReachableDynamicsSupportIdentifiability

namespace RelayTheory

namespace FinKernel

/--
Two future-context frames have the same intrinsic rooted reachable dynamics when
there exists a relation-level correspondence preserving and reflecting the
source-substitution successor relation.
-/
def ReachableDynamicsEq {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (ReachableClassDynamicsCorrespondence P K L)

end FinKernel

/--
Pointwise equality on the current full-future response carrier is exactly native
function equality.  No additional quotient or saturation layer is hidden here.
-/
theorem finKernel_fullFutureResponseSpaceEq_iff_eq {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t : FinKernel.FullFutureResponseSpace P K} :
    FinKernel.FullFutureResponseSpaceEq s t ↔ s = t := by
  constructor
  · intro h
    funext c hc m f obs hobs x z
    exact h c hc m f obs hobs x z
  · intro h
    subst t
    exact finKernel_fullFutureResponseSpaceEq_refl s

/-- Identity correspondence on one reachable-dynamics frame. -/
def finKernel_reachableClassDynamicsCorrespondence_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ReachableClassDynamicsCorrespondence P K K := by
  exact {
    rel := fun s t => s = t
    total_left := by
      intro s hs
      exact ⟨s, hs, rfl⟩
    total_right := by
      intro t ht
      exact ⟨t, ht, rfl⟩
    right_functional := by
      intro s t u hst hsu
      have htu : t = u := hst.symm.trans hsu
      exact (finKernel_fullFutureResponseSpaceEq_iff_eq).2 htu
    left_functional := by
      intro s u t hst hut
      have hsu : s = u := hst.trans hut.symm
      exact (finKernel_fullFutureResponseSpaceEq_iff_eq).2 hsu
    root := rfl
    successor_forward := by
      intro sK tK uK sL tL uL hs ht hu hSucc
      subst sL
      subst tL
      subst uL
      exact hSucc
    successor_backward := by
      intro sK tK uK sL tL uL hs ht hu hSucc
      subst sL
      subst tL
      subst uL
      exact hSucc
  }

/-- Reverse any relation-level reachable-dynamics correspondence. -/
def finKernel_reachableClassDynamicsCorrespondence_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableClassDynamicsCorrespondence P K L) :
    FinKernel.ReachableClassDynamicsCorrespondence P L K := by
  exact {
    rel := fun t s => h.rel s t
    total_left := h.total_right
    total_right := h.total_left
    right_functional := h.left_functional
    left_functional := h.right_functional
    root := h.root
    successor_forward := h.successor_backward
    successor_backward := h.successor_forward
  }

/-- Compose two relation-level reachable-dynamics correspondences. -/
def finKernel_reachableClassDynamicsCorrespondence_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.ReachableClassDynamicsCorrespondence P K L)
    (hLM : FinKernel.ReachableClassDynamicsCorrespondence P L M) :
    FinKernel.ReachableClassDynamicsCorrespondence P K M := by
  exact {
    rel := fun s u => ∃ t, hKL.rel s t ∧ hLM.rel t u
    total_left := by
      intro s hs
      rcases hKL.total_left hs with ⟨t, ht, hst⟩
      rcases hLM.total_left ht with ⟨u, hu, htu⟩
      exact ⟨u, hu, ⟨t, hst, htu⟩⟩
    total_right := by
      intro u hu
      rcases hLM.total_right hu with ⟨t, ht, htu⟩
      rcases hKL.total_right ht with ⟨s, hs, hst⟩
      exact ⟨s, hs, ⟨t, hst, htu⟩⟩
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
    root := ⟨FinKernel.ResidualIdentityState P L, hKL.root, hLM.root⟩
    successor_forward := by
      intro sK tK uK sM tM uM hsRel htRel huRel hSuccK
      rcases hsRel with ⟨sL, hsKL, hsLM⟩
      rcases htRel with ⟨tL, htKL, htLM⟩
      rcases huRel with ⟨uL, huKL, huLM⟩
      have hSuccL := hKL.successor_forward hsKL htKL huKL hSuccK
      exact hLM.successor_forward hsLM htLM huLM hSuccL
    successor_backward := by
      intro sK tK uK sM tM uM hsRel htRel huRel hSuccM
      rcases hsRel with ⟨sL, hsKL, hsLM⟩
      rcases htRel with ⟨tL, htKL, htLM⟩
      rcases huRel with ⟨uL, huKL, huLM⟩
      have hSuccL := hLM.successor_backward hsLM htLM huLM hSuccM
      exact hKL.successor_backward hsKL htKL huKL hSuccL
  }

/-- Reachable-dynamics equality is reflexive. -/
theorem finKernel_reachableDynamicsEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ReachableDynamicsEq P K K := by
  exact ⟨finKernel_reachableClassDynamicsCorrespondence_refl P K⟩

/-- Reachable-dynamics equality is symmetric. -/
theorem finKernel_reachableDynamicsEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableDynamicsEq P K L) :
    FinKernel.ReachableDynamicsEq P L K := by
  rcases h with ⟨hKL⟩
  exact ⟨finKernel_reachableClassDynamicsCorrespondence_symm hKL⟩

/-- Reachable-dynamics equality is transitive. -/
theorem finKernel_reachableDynamicsEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.ReachableDynamicsEq P K L)
    (hLM : FinKernel.ReachableDynamicsEq P L M) :
    FinKernel.ReachableDynamicsEq P K M := by
  rcases hKL with ⟨cKL⟩
  rcases hLM with ⟨cLM⟩
  exact ⟨finKernel_reachableClassDynamicsCorrespondence_trans cKL cLM⟩

/-- Standard equivalence packaging for fixed probes. -/
theorem finKernel_reachableDynamicsEq_equivalence {n : Nat}
    (P : FinKernel.ProbeFamily n) :
    Equivalence (FinKernel.ReachableDynamicsEq P) := by
  refine ⟨?_, ?_, ?_⟩
  · intro K
    exact finKernel_reachableDynamicsEq_refl P K
  · intro K L hKL
    exact finKernel_reachableDynamicsEq_symm hKL
  · intro K L M hKL hLM
    exact finKernel_reachableDynamicsEq_trans hKL hLM

/-- Common realized contextual-class support implies intrinsic dynamics equality. -/
theorem finKernel_accessClassSupportEq_implies_reachableDynamicsEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.AccessClassSupportEq P K L) :
    FinKernel.ReachableDynamicsEq P K L := by
  exact ⟨finKernel_reachableClassDynamicsCorrespondence_of_accessClassSupportEq h⟩

/-- The #2877 relabeling fixture is dynamics-equal despite different support. -/
theorem finKernel_allProbes_safe_other_reachableDynamicsEq :
    FinKernel.ReachableDynamicsEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      FinKernel.otherCollapseContextFamily3 := by
  exact ⟨finKernel_safe_other_relabeledDynamicsCorrespondence⟩

/-- The converse from intrinsic dynamics equality to support equality fails. -/
theorem finKernel_reachableDynamicsEq_does_not_imply_accessClassSupportEq :
    ¬ (∀ (P : FinKernel.ProbeFamily 3)
        (K L : FinKernel.FutureContextFamily 3),
      FinKernel.ReachableDynamicsEq P K L →
      FinKernel.AccessClassSupportEq P K L) := by
  intro h
  exact finKernel_allProbes_safe_other_not_accessClassSupportEq
    (h (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      FinKernel.otherCollapseContextFamily3
      finKernel_allProbes_safe_other_reachableDynamicsEq)

/-- Acceptance bundle for #2879. -/
theorem finKernel_relational_reachable_dynamics_equivalence_bundle :
    (∀ {n : Nat}
      (P : FinKernel.ProbeFamily n)
      (K : FinKernel.FutureContextFamily n),
      FinKernel.ReachableDynamicsEq P K K) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.ReachableDynamicsEq P K L →
      FinKernel.ReachableDynamicsEq P L K) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L M : FinKernel.FutureContextFamily n},
      FinKernel.ReachableDynamicsEq P K L →
      FinKernel.ReachableDynamicsEq P L M →
      FinKernel.ReachableDynamicsEq P K M) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.AccessClassSupportEq P K L →
      FinKernel.ReachableDynamicsEq P K L) ∧
    FinKernel.ReachableDynamicsEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      FinKernel.otherCollapseContextFamily3 ∧
    ¬ FinKernel.AccessClassSupportEq
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      FinKernel.otherCollapseContextFamily3 := by
  exact ⟨finKernel_reachableDynamicsEq_refl,
    fun h => finKernel_reachableDynamicsEq_symm h,
    fun hKL hLM => finKernel_reachableDynamicsEq_trans hKL hLM,
    fun h => finKernel_accessClassSupportEq_implies_reachableDynamicsEq h,
    finKernel_allProbes_safe_other_reachableDynamicsEq,
    finKernel_allProbes_safe_other_not_accessClassSupportEq⟩

end RelayTheory
