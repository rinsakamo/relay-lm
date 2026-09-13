import RelayTheory.RelationalReachableDynamicsEquivalence

namespace RelayTheory

namespace FinKernel

/--
A reachable state is an operational two-sided unit when composing it with any
reachable state, on either side, returns that state under the intrinsic
source-substitution successor relation.
-/
def ReachableTwoSidedUnit {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (e : FullFutureResponseSpace P K) : Prop :=
  ReachableResidualState P K e ∧
    ∀ s : FullFutureResponseSpace P K,
      ReachableResidualState P K s →
        SourceSubstitutionSuccessorRel P K e s s ∧
        SourceSubstitutionSuccessorRel P K s e s

/--
Reachable-dynamics correspondence with no separately declared distinguished
root.  This is a proof interface only; it retains the full reachable carrier,
functionality, totality, and successor preservation/reflection.
-/
structure UnpointedReachableDynamicsCorrespondence {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop
  total_left : ∀ {s}, ReachableResidualState P K s →
    ∃ t, ReachableResidualState P L t ∧ rel s t
  total_right : ∀ {t}, ReachableResidualState P L t →
    ∃ s, ReachableResidualState P K s ∧ rel s t
  right_functional : ∀ {s t u}, rel s t → rel s u →
    FullFutureResponseSpaceEq t u
  left_functional : ∀ {s u t}, rel s t → rel u t →
    FullFutureResponseSpaceEq s u
  successor_forward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P K sK tK uK →
    SourceSubstitutionSuccessorRel P L sL tL uL
  successor_backward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P L sL tL uL →
    SourceSubstitutionSuccessorRel P K sK tK uK

/-- Existence of an unpointed reachable-dynamics correspondence. -/
def UnpointedReachableDynamicsEq {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (UnpointedReachableDynamicsCorrespondence P K L)

end FinKernel

/-- The existing residual root is an operational reachable two-sided unit. -/
theorem finKernel_residualIdentityState_reachableTwoSidedUnit {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ReachableTwoSidedUnit P K
      (FinKernel.ResidualIdentityState P K) := by
  have hRoot : FinKernel.ReachableResidualState P K
      (FinKernel.ResidualIdentityState P K) :=
    finKernel_residualIdentityState_reachable
  let laws := finKernel_sourceSubstitutionSuccessorRel_laws P K
  refine ⟨hRoot, ?_⟩
  intro s hs
  constructor
  · rcases laws.total hRoot hs with ⟨u, hSucc, hu⟩
    have huEq : FinKernel.FullFutureResponseSpaceEq u s :=
      laws.identity_earlier hs hSucc
    have hNative : u = s :=
      (finKernel_fullFutureResponseSpaceEq_iff_eq).1 huEq
    rw [hNative] at hSucc
    exact hSucc
  · rcases laws.total hs hRoot with ⟨u, hSucc, hu⟩
    have huEq : FinKernel.FullFutureResponseSpaceEq u s :=
      laws.identity_later hs hSucc
    have hNative : u = s :=
      (finKernel_fullFutureResponseSpaceEq_iff_eq).1 huEq
    rw [hNative] at hSucc
    exact hSucc

/-- Reachable two-sided units are unique up to extensional response equality. -/
theorem finKernel_reachableTwoSidedUnit_unique {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {e q : FinKernel.FullFutureResponseSpace P K}
    (he : FinKernel.ReachableTwoSidedUnit P K e)
    (hq : FinKernel.ReachableTwoSidedUnit P K q) :
    FinKernel.FullFutureResponseSpaceEq e q := by
  let laws := finKernel_sourceSubstitutionSuccessorRel_laws P K
  have hToQ : FinKernel.SourceSubstitutionSuccessorRel P K e q q :=
    (he.2 q hq.1).1
  have hToE : FinKernel.SourceSubstitutionSuccessorRel P K e q e :=
    (hq.2 e he.1).2
  have hQE : FinKernel.FullFutureResponseSpaceEq q e :=
    laws.functional he.1 hq.1 hToQ hToE
  exact finKernel_fullFutureResponseSpaceEq_symm hQE

/-- Reachable two-sided units are literally equal on the current function carrier. -/
theorem finKernel_reachableTwoSidedUnit_eq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {e q : FinKernel.FullFutureResponseSpace P K}
    (he : FinKernel.ReachableTwoSidedUnit P K e)
    (hq : FinKernel.ReachableTwoSidedUnit P K q) :
    e = q :=
  (finKernel_fullFutureResponseSpaceEq_iff_eq).1
    (finKernel_reachableTwoSidedUnit_unique he hq)

/-- Forget only the explicit root witness from a pointed correspondence. -/
def finKernel_unpointedReachableDynamicsCorrespondence_of_pointed {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableClassDynamicsCorrespondence P K L) :
    FinKernel.UnpointedReachableDynamicsCorrespondence P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    total_right := h.total_right
    right_functional := h.right_functional
    left_functional := h.left_functional
    successor_forward := h.successor_forward
    successor_backward := h.successor_backward
  }

/--
The image of the left root under any unpointed total successor correspondence
is itself a reachable two-sided unit on the right.
-/
theorem finKernel_unpointed_root_image_is_reachableTwoSidedUnit {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.UnpointedReachableDynamicsCorrespondence P K L)
    {tL : FinKernel.FullFutureResponseSpace P L}
    (htL : FinKernel.ReachableResidualState P L tL)
    (hRootRel : h.rel (FinKernel.ResidualIdentityState P K) tL) :
    FinKernel.ReachableTwoSidedUnit P L tL := by
  have hRootK := finKernel_residualIdentityState_reachableTwoSidedUnit P K
  refine ⟨htL, ?_⟩
  intro sL hsL
  rcases h.total_right hsL with ⟨sK, hsK, hRel⟩
  have hUnitsK := hRootK.2 sK hsK
  exact ⟨
    h.successor_forward hRootRel hRel hRel hUnitsK.1,
    h.successor_forward hRel hRootRel hRel hUnitsK.2⟩

/--
Any unpointed reachable-dynamics correspondence reconstructs the explicit root
relation because the reachable two-sided unit is unique.
-/
def finKernel_reachableClassDynamicsCorrespondence_of_unpointed {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.UnpointedReachableDynamicsCorrespondence P K L) :
    FinKernel.ReachableClassDynamicsCorrespondence P K L := by
  have hRootK : FinKernel.ReachableResidualState P K
      (FinKernel.ResidualIdentityState P K) :=
    finKernel_residualIdentityState_reachable
  rcases h.total_left hRootK with ⟨tL, htL, hRootRel⟩
  have htUnit : FinKernel.ReachableTwoSidedUnit P L tL :=
    finKernel_unpointed_root_image_is_reachableTwoSidedUnit h htL hRootRel
  have hRootL : FinKernel.ReachableTwoSidedUnit P L
      (FinKernel.ResidualIdentityState P L) :=
    finKernel_residualIdentityState_reachableTwoSidedUnit P L
  have htRoot : tL = FinKernel.ResidualIdentityState P L :=
    finKernel_reachableTwoSidedUnit_eq htUnit hRootL
  have hRoot : h.rel
      (FinKernel.ResidualIdentityState P K)
      (FinKernel.ResidualIdentityState P L) := by
    simpa only [htRoot] using hRootRel
  exact {
    rel := h.rel
    total_left := h.total_left
    total_right := h.total_right
    right_functional := h.right_functional
    left_functional := h.left_functional
    root := hRoot
    successor_forward := h.successor_forward
    successor_backward := h.successor_backward
  }

/-- Root designation adds no existence-level correspondence information. -/
theorem finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    FinKernel.UnpointedReachableDynamicsEq P K L ↔
      FinKernel.ReachableDynamicsEq P K L := by
  constructor
  · rintro ⟨h⟩
    exact ⟨finKernel_reachableClassDynamicsCorrespondence_of_unpointed h⟩
  · rintro ⟨h⟩
    exact ⟨finKernel_unpointedReachableDynamicsCorrespondence_of_pointed h⟩

/-- Unpointed reachable-dynamics equality is reflexive by the #2879 equivalence. -/
theorem finKernel_unpointedReachableDynamicsEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.UnpointedReachableDynamicsEq P K K :=
  (finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq).2
    (finKernel_reachableDynamicsEq_refl P K)

/-- Unpointed reachable-dynamics equality is symmetric. -/
theorem finKernel_unpointedReachableDynamicsEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.UnpointedReachableDynamicsEq P K L) :
    FinKernel.UnpointedReachableDynamicsEq P L K := by
  apply (finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq).2
  exact finKernel_reachableDynamicsEq_symm
    ((finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq).1 h)

/-- Unpointed reachable-dynamics equality is transitive. -/
theorem finKernel_unpointedReachableDynamicsEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.UnpointedReachableDynamicsEq P K L)
    (hLM : FinKernel.UnpointedReachableDynamicsEq P L M) :
    FinKernel.UnpointedReachableDynamicsEq P K M := by
  apply (finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq).2
  exact finKernel_reachableDynamicsEq_trans
    ((finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq).1 hKL)
    ((finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq).1 hLM)

/-- Standard equivalence packaging for the root-free interface. -/
theorem finKernel_unpointedReachableDynamicsEq_equivalence {n : Nat}
    (P : FinKernel.ProbeFamily n) :
    Equivalence (FinKernel.UnpointedReachableDynamicsEq P) := by
  exact ⟨finKernel_unpointedReachableDynamicsEq_refl P,
    fun {_ _} h => finKernel_unpointedReachableDynamicsEq_symm h,
    fun {_ _ _} hKL hLM =>
      finKernel_unpointedReachableDynamicsEq_trans hKL hLM⟩

/-- Acceptance bundle for #2885. -/
theorem finKernel_root_reconstruction_bundle :
    (∀ {n : Nat}
      (P : FinKernel.ProbeFamily n)
      (K : FinKernel.FutureContextFamily n),
      FinKernel.ReachableTwoSidedUnit P K
        (FinKernel.ResidualIdentityState P K)) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K : FinKernel.FutureContextFamily n}
      {e q : FinKernel.FullFutureResponseSpace P K},
      FinKernel.ReachableTwoSidedUnit P K e →
      FinKernel.ReachableTwoSidedUnit P K q →
      e = q) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.UnpointedReachableDynamicsEq P K L ↔
        FinKernel.ReachableDynamicsEq P K L) := by
  exact ⟨finKernel_residualIdentityState_reachableTwoSidedUnit,
    fun he hq => finKernel_reachableTwoSidedUnit_eq he hq,
    finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq⟩

end RelayTheory
