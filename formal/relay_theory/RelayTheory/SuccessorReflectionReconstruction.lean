import RelayTheory.RootReconstruction

namespace RelayTheory

namespace FinKernel

/--
A raw forward-only reachable-dynamics correspondence.  This is exactly the
#2885 unpointed interface with `successor_backward` omitted.  Its relation still
lives on the whole raw response-function carrier, so a relation witness alone
does not assert reachability.
-/
structure ForwardReachableDynamicsCorrespondence {n : Nat}
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

/-- Existence of a raw forward-only reachable-dynamics correspondence. -/
def ForwardReachableDynamicsEq {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (ForwardReachableDynamicsCorrespondence P K L)

/--
The extra condition that a raw relation contains no pairs outside the reachable
carriers.  #2908 uses this only to state when the original raw relation itself
can be promoted without normalization.
-/
def RelatesOnlyReachable {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n)
    (rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop) : Prop :=
  ∀ {s t}, rel s t → ReachableResidualState P K s ∧ ReachableResidualState P L t

end FinKernel

/--
Core reachable-carrier reflection theorem.  For reachable source/action pairs,
a bi-functional relation that is total on reachable states and preserves the
successor operation forward already reflects it.  No inverse function or choice
is selected.
-/
theorem finKernel_forwardCorrespondence_reflects_successor_on_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsCorrespondence P K L)
    {sK tK uK : FinKernel.FullFutureResponseSpace P K}
    {sL tL uL : FinKernel.FullFutureResponseSpace P L}
    (hsK : FinKernel.ReachableResidualState P K sK)
    (htK : FinKernel.ReachableResidualState P K tK)
    (hsL : FinKernel.ReachableResidualState P L sL)
    (htL : FinKernel.ReachableResidualState P L tL)
    (hsRel : h.rel sK sL)
    (htRel : h.rel tK tL)
    (huRel : h.rel uK uL)
    (hSuccL : FinKernel.SourceSubstitutionSuccessorRel P L sL tL uL) :
    FinKernel.SourceSubstitutionSuccessorRel P K sK tK uK := by
  let lawsK := finKernel_sourceSubstitutionSuccessorRel_laws P K
  let lawsL := finKernel_sourceSubstitutionSuccessorRel_laws P L
  rcases lawsK.total hsK htK with ⟨vK, hSuccK, hvK⟩
  rcases h.total_left hvK with ⟨vL, hvL, hvRel⟩
  have hSuccLv : FinKernel.SourceSubstitutionSuccessorRel P L sL tL vL :=
    h.successor_forward hsRel htRel hvRel hSuccK
  have hvLuL : FinKernel.FullFutureResponseSpaceEq vL uL :=
    lawsL.functional hsL htL hSuccLv hSuccL
  have hvLuLEq : vL = uL :=
    (finKernel_fullFutureResponseSpaceEq_iff_eq).1 hvLuL
  have hvRelU : h.rel vK uL := by
    simpa only [hvLuLEq] using hvRel
  have hvKuK : FinKernel.FullFutureResponseSpaceEq vK uK :=
    h.left_functional hvRelU huRel
  have hvKuKEq : vK = uK :=
    (finKernel_fullFutureResponseSpaceEq_iff_eq).1 hvKuK
  simpa only [hvKuKEq] using hSuccK

/--
If the raw forward relation is already closed on reachable pairs, reflection can
be added while retaining exactly the same relation.  This exposes the missing
hypothesis in the raw #2885 interface rather than silently assuming it.
-/
def finKernel_unpointedCorrespondence_of_forward_sameRel {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsCorrespondence P K L)
    (hReach : FinKernel.RelatesOnlyReachable P K L h.rel) :
    FinKernel.UnpointedReachableDynamicsCorrespondence P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    total_right := h.total_right
    right_functional := h.right_functional
    left_functional := h.left_functional
    successor_forward := h.successor_forward
    successor_backward := by
      intro sK tK uK sL tL uL hsRel htRel huRel hSuccL
      have hsReach := hReach hsRel
      have htReach := hReach htRel
      exact finKernel_forwardCorrespondence_reflects_successor_on_reachable
        h hsReach.1 htReach.1 hsReach.2 htReach.2
        hsRel htRel huRel hSuccL
  }

/-- Forget backward preservation from an existing unpointed correspondence. -/
def finKernel_forwardCorrespondence_of_unpointed {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.UnpointedReachableDynamicsCorrespondence P K L) :
    FinKernel.ForwardReachableDynamicsCorrespondence P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    total_right := h.total_right
    right_functional := h.right_functional
    left_functional := h.left_functional
    successor_forward := h.successor_forward
  }

/--
Normalize a raw forward-only correspondence by discarding relation pairs whose
endpoints are not both reachable.  On this normalized relation, the reachable
reflection theorem reconstructs `successor_backward`.
-/
def finKernel_unpointedCorrespondence_of_forward_normalized {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsCorrespondence P K L) :
    FinKernel.UnpointedReachableDynamicsCorrespondence P K L := by
  let relR : FinKernel.FullFutureResponseSpace P K →
      FinKernel.FullFutureResponseSpace P L → Prop :=
    fun s t =>
      FinKernel.ReachableResidualState P K s ∧
      FinKernel.ReachableResidualState P L t ∧
      h.rel s t
  exact {
    rel := relR
    total_left := by
      intro s hs
      rcases h.total_left hs with ⟨t, ht, hst⟩
      exact ⟨t, ht, hs, ht, hst⟩
    total_right := by
      intro t ht
      rcases h.total_right ht with ⟨s, hs, hst⟩
      exact ⟨s, hs, hs, ht, hst⟩
    right_functional := by
      intro s t u hst hsu
      exact h.right_functional hst.2.2 hsu.2.2
    left_functional := by
      intro s u t hst hut
      exact h.left_functional hst.2.2 hut.2.2
    successor_forward := by
      intro sK tK uK sL tL uL hsRel htRel huRel hSuccK
      exact h.successor_forward hsRel.2.2 htRel.2.2 huRel.2.2 hSuccK
    successor_backward := by
      intro sK tK uK sL tL uL hsRel htRel huRel hSuccL
      exact finKernel_forwardCorrespondence_reflects_successor_on_reachable
        h hsRel.1 htRel.1 hsRel.2.1 htRel.2.1
        hsRel.2.2 htRel.2.2 huRel.2.2 hSuccL
  }

/--
Existence of a forward-only raw correspondence is exactly existence of the
#2885 unpointed bidirectional correspondence.  The forward-to-unpointed
conversion is allowed to discard unreachable relation garbage but changes no
reachable state or successor fact.
-/
theorem finKernel_forwardReachableDynamicsEq_iff_unpointedReachableDynamicsEq
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    FinKernel.ForwardReachableDynamicsEq P K L ↔
      FinKernel.UnpointedReachableDynamicsEq P K L := by
  constructor
  · rintro ⟨h⟩
    exact ⟨finKernel_unpointedCorrespondence_of_forward_normalized h⟩
  · rintro ⟨h⟩
    exact ⟨finKernel_forwardCorrespondence_of_unpointed h⟩

/-- Forward-only existence therefore also exactly matches #2879 reachable dynamics. -/
theorem finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    FinKernel.ForwardReachableDynamicsEq P K L ↔
      FinKernel.ReachableDynamicsEq P K L := by
  exact Iff.trans
    finKernel_forwardReachableDynamicsEq_iff_unpointedReachableDynamicsEq
    finKernel_unpointedReachableDynamicsEq_iff_reachableDynamicsEq

/-- Forward-only reachable-dynamics equality is reflexive. -/
theorem finKernel_forwardReachableDynamicsEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ForwardReachableDynamicsEq P K K :=
  (finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq).2
    (finKernel_reachableDynamicsEq_refl P K)

/-- Forward-only reachable-dynamics equality is symmetric at the existence level. -/
theorem finKernel_forwardReachableDynamicsEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsEq P K L) :
    FinKernel.ForwardReachableDynamicsEq P L K := by
  apply (finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq).2
  exact finKernel_reachableDynamicsEq_symm
    ((finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq).1 h)

/-- Forward-only reachable-dynamics equality is transitive at the existence level. -/
theorem finKernel_forwardReachableDynamicsEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.ForwardReachableDynamicsEq P K L)
    (hLM : FinKernel.ForwardReachableDynamicsEq P L M) :
    FinKernel.ForwardReachableDynamicsEq P K M := by
  apply (finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq).2
  exact finKernel_reachableDynamicsEq_trans
    ((finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq).1 hKL)
    ((finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq).1 hLM)

/-- Standard equivalence packaging for the forward-only existence relation. -/
theorem finKernel_forwardReachableDynamicsEq_equivalence {n : Nat}
    (P : FinKernel.ProbeFamily n) :
    Equivalence (FinKernel.ForwardReachableDynamicsEq P) := by
  exact ⟨finKernel_forwardReachableDynamicsEq_refl P,
    fun {_ _} h => finKernel_forwardReachableDynamicsEq_symm h,
    fun {_ _ _} hKL hLM => finKernel_forwardReachableDynamicsEq_trans hKL hLM⟩

/-- Acceptance bundle for #2908. -/
theorem finKernel_successor_reflection_reconstruction_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.ForwardReachableDynamicsEq P K L ↔
        FinKernel.UnpointedReachableDynamicsEq P K L) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.ForwardReachableDynamicsEq P K L ↔
        FinKernel.ReachableDynamicsEq P K L) := by
  exact ⟨finKernel_forwardReachableDynamicsEq_iff_unpointedReachableDynamicsEq,
    finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq⟩

end RelayTheory
