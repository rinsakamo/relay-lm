import RelayTheory.SuccessorReflectionReconstruction

namespace RelayTheory

namespace FinKernel

/--
Forward reachable-dynamics correspondence retaining only input-side
(`left_functional`) uniqueness. Output-side uniqueness is deliberately omitted
and will be reconstructed on the reachable carrier.
-/
structure LeftFunctionalForwardReachableDynamicsCorrespondence {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop
  total_left : ∀ {s}, ReachableResidualState P K s →
    ∃ t, ReachableResidualState P L t ∧ rel s t
  total_right : ∀ {t}, ReachableResidualState P L t →
    ∃ s, ReachableResidualState P K s ∧ rel s t
  left_functional : ∀ {s u t}, rel s t → rel u t →
    FullFutureResponseSpaceEq s u
  successor_forward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P K sK tK uK →
    SourceSubstitutionSuccessorRel P L sL tL uL

/-- Existence of a left-functional forward correspondence. -/
def LeftFunctionalForwardReachableDynamicsEq {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (LeftFunctionalForwardReachableDynamicsCorrespondence P K L)

end FinKernel

/--
The left root is forced to relate to the right root even without any
correspondence functionality assumption. Totality and forward preservation make
any reachable image of the left root a two-sided unit, and the target unit is
unique.
-/
theorem finKernel_leftFunctionalForward_root {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.LeftFunctionalForwardReachableDynamicsCorrespondence P K L) :
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
On reachable relation pairs, output-side functionality is forced by the target
left-unit law. The same left state cannot have two distinct reachable right
images while forward successor preservation is maintained.
-/
theorem finKernel_leftFunctionalForward_rightFunctional_on_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.LeftFunctionalForwardReachableDynamicsCorrespondence P K L)
    {sK : FinKernel.FullFutureResponseSpace P K}
    {tL uL : FinKernel.FullFutureResponseSpace P L}
    (hsK : FinKernel.ReachableResidualState P K sK)
    (htL : FinKernel.ReachableResidualState P L tL)
    (hst : h.rel sK tL)
    (hsu : h.rel sK uL) :
    FinKernel.FullFutureResponseSpaceEq tL uL := by
  have hRootRel := finKernel_leftFunctionalForward_root h
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

/-- Forget only output-side functionality from the #2908 forward interface. -/
def finKernel_leftFunctionalForward_of_forward {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsCorrespondence P K L) :
    FinKernel.LeftFunctionalForwardReachableDynamicsCorrespondence P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    total_right := h.total_right
    left_functional := h.left_functional
    successor_forward := h.successor_forward
  }

/--
Reachability-normalize a left-functional forward correspondence and reconstruct
its missing output-side functionality. Raw unrelated pairs are discarded exactly
as in #2908; no reachable state or successor fact is removed.
-/
def finKernel_forwardCorrespondence_of_leftFunctional_normalized {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.LeftFunctionalForwardReachableDynamicsCorrespondence P K L) :
    FinKernel.ForwardReachableDynamicsCorrespondence P K L := by
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
      exact finKernel_leftFunctionalForward_rightFunctional_on_reachable
        h hst.1 hst.2.1 hst.2.2 hsu.2.2
    left_functional := by
      intro s u t hst hut
      exact h.left_functional hst.2.2 hut.2.2
    successor_forward := by
      intro sK tK uK sL tL uL hsRel htRel huRel hSuccK
      exact h.successor_forward
        hsRel.2.2 htRel.2.2 huRel.2.2 hSuccK
  }

/--
Deleting `right_functional` does not change existence-level forward reachable
dynamics once the relation is honestly restricted to reachable pairs.
-/
theorem finKernel_leftFunctionalForwardReachableDynamicsEq_iff_forwardReachableDynamicsEq
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    FinKernel.LeftFunctionalForwardReachableDynamicsEq P K L ↔
      FinKernel.ForwardReachableDynamicsEq P K L := by
  constructor
  · rintro ⟨h⟩
    exact ⟨finKernel_forwardCorrespondence_of_leftFunctional_normalized h⟩
  · rintro ⟨h⟩
    exact ⟨finKernel_leftFunctionalForward_of_forward h⟩

/-- The one-sided-functional interface therefore determines exactly #2879 dynamics equality. -/
theorem finKernel_leftFunctionalForwardReachableDynamicsEq_iff_reachableDynamicsEq
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    FinKernel.LeftFunctionalForwardReachableDynamicsEq P K L ↔
      FinKernel.ReachableDynamicsEq P K L := by
  exact Iff.trans
    finKernel_leftFunctionalForwardReachableDynamicsEq_iff_forwardReachableDynamicsEq
    finKernel_forwardReachableDynamicsEq_iff_reachableDynamicsEq

/-- Acceptance bundle for #2925. -/
theorem finKernel_right_functionality_reconstruction_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.LeftFunctionalForwardReachableDynamicsEq P K L ↔
        FinKernel.ForwardReachableDynamicsEq P K L) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.LeftFunctionalForwardReachableDynamicsEq P K L ↔
        FinKernel.ReachableDynamicsEq P K L) := by
  exact ⟨
    finKernel_leftFunctionalForwardReachableDynamicsEq_iff_forwardReachableDynamicsEq,
    finKernel_leftFunctionalForwardReachableDynamicsEq_iff_reachableDynamicsEq⟩

end RelayTheory
