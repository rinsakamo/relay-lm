import RelayTheory.ReachableDynamicsEmbedding

namespace RelayTheory

namespace FinKernel

/--
A one-sided forward reachable-dynamics embedding with only source-side
(`left_functional`) uniqueness retained. This is exactly #2910's
`ReachableDynamicsEmbedding` with `right_functional` deleted.
-/
structure LeftFunctionalReachableDynamicsEmbedding {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop
  total_left : ∀ {s}, ReachableResidualState P K s →
    ∃ t, ReachableResidualState P L t ∧ rel s t
  left_functional : ∀ {s u t}, rel s t → rel u t →
    FullFutureResponseSpaceEq s u
  successor_forward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P K sK tK uK →
    SourceSubstitutionSuccessorRel P L sL tL uL

/-- Existence of the reduced one-sided left-functional embedding. -/
def LeftFunctionalReachableDynamicsEmbeds {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (LeftFunctionalReachableDynamicsEmbedding P K L)

end FinKernel

/--
Output-side uniqueness is forced on reachable relation pairs without target
surjectivity. A reachable image of the source root is enough: transport the
source left-unit edge twice and use intrinsic successor output functionality in
the target. The proof does not use `left_functional`.
-/
theorem finKernel_leftFunctionalEmbedding_rightFunctional_on_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.LeftFunctionalReachableDynamicsEmbedding P K L)
    {sK : FinKernel.FullFutureResponseSpace P K}
    {tL uL : FinKernel.FullFutureResponseSpace P L}
    (hsK : FinKernel.ReachableResidualState P K sK)
    (htL : FinKernel.ReachableResidualState P L tL)
    (hst : h.rel sK tL)
    (hsu : h.rel sK uL) :
    FinKernel.FullFutureResponseSpaceEq tL uL := by
  have hRootKReach : FinKernel.ReachableResidualState P K
      (FinKernel.ResidualIdentityState P K) :=
    finKernel_residualIdentityState_reachable
  rcases h.total_left hRootKReach with ⟨rL, hrL, hRootRel⟩
  have hRootKUnit := finKernel_residualIdentityState_reachableTwoSidedUnit P K
  have hSuccK : FinKernel.SourceSubstitutionSuccessorRel P K
      (FinKernel.ResidualIdentityState P K) sK sK :=
    (hRootKUnit.2 sK hsK).1
  have hSuccLt : FinKernel.SourceSubstitutionSuccessorRel P L rL tL tL :=
    h.successor_forward hRootRel hst hst hSuccK
  have hSuccLu : FinKernel.SourceSubstitutionSuccessorRel P L rL tL uL :=
    h.successor_forward hRootRel hst hsu hSuccK
  exact finKernel_sourceSubstitutionSuccessorRel_functional_on_reachable
    hrL htL hSuccLt hSuccLu

/-- Forget only output-side functionality from #2910's embedding interface. -/
def finKernel_leftFunctionalEmbedding_of_embedding {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableDynamicsEmbedding P K L) :
    FinKernel.LeftFunctionalReachableDynamicsEmbedding P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    left_functional := h.left_functional
    successor_forward := h.successor_forward
  }

/--
Normalize to reachable relation pairs and reconstruct #2910's explicit
`right_functional` field. Raw unrelated pairs are discarded; no reachable pair
or reachable successor fact is lost.
-/
def finKernel_embedding_of_leftFunctional_normalized {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.LeftFunctionalReachableDynamicsEmbedding P K L) :
    FinKernel.ReachableDynamicsEmbedding P K L := by
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
    right_functional := by
      intro s t u hst hsu
      exact finKernel_leftFunctionalEmbedding_rightFunctional_on_reachable
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
Deleting `right_functional` does not change existence-level one-sided reachable
dynamics embeddings once relations are normalized to reachable pairs.
-/
theorem finKernel_leftFunctionalReachableDynamicsEmbeds_iff_reachableDynamicsEmbeds
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    FinKernel.LeftFunctionalReachableDynamicsEmbeds P K L ↔
      FinKernel.ReachableDynamicsEmbeds P K L := by
  constructor
  · rintro ⟨h⟩
    exact ⟨finKernel_embedding_of_leftFunctional_normalized h⟩
  · rintro ⟨h⟩
    exact ⟨finKernel_leftFunctionalEmbedding_of_embedding h⟩

/-- The #2910 strict empty-to-safe embedding remains after deleting output uniqueness. -/
theorem finKernel_allProbes_empty_safe_leftFunctionalReachableDynamicsEmbeds :
    FinKernel.LeftFunctionalReachableDynamicsEmbeds
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact (finKernel_leftFunctionalReachableDynamicsEmbeds_iff_reachableDynamicsEmbeds).2
    finKernel_allProbes_empty_safe_reachableDynamicsEmbeds

/-- Target right-totality remains absent: the reduced embedding still does not imply dynamics equality. -/
theorem finKernel_leftFunctionalReachableDynamicsEmbeds_does_not_imply_forwardReachableDynamicsEq :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.LeftFunctionalReachableDynamicsEmbeds (FinKernel.allProbes 3) K L →
      FinKernel.ForwardReachableDynamicsEq (FinKernel.allProbes 3) K L) := by
  intro hPromote
  apply finKernel_reachableDynamicsEmbeds_does_not_imply_forwardReachableDynamicsEq
  intro K L hEmbed
  exact hPromote K L
    ((finKernel_leftFunctionalReachableDynamicsEmbeds_iff_reachableDynamicsEmbeds).2 hEmbed)

/-- Acceptance bundle for #2930. -/
theorem finKernel_embedding_right_functionality_reconstruction_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.LeftFunctionalReachableDynamicsEmbeds P K L ↔
        FinKernel.ReachableDynamicsEmbeds P K L) ∧
    FinKernel.LeftFunctionalReachableDynamicsEmbeds
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.ForwardReachableDynamicsEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  refine ⟨finKernel_leftFunctionalReachableDynamicsEmbeds_iff_reachableDynamicsEmbeds,
    finKernel_allProbes_empty_safe_leftFunctionalReachableDynamicsEmbeds, ?_⟩
  intro hEq
  have hRev := finKernel_forwardReachableDynamicsEq_symm hEq
  exact finKernel_allProbes_safe_empty_not_reachableDynamicsEmbeds
    (finKernel_forwardReachableDynamicsEq_implies_reachableDynamicsEmbeds hRev)

end RelayTheory
