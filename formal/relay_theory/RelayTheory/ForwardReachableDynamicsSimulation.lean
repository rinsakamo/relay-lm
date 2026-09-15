import RelayTheory.EmbeddingRightFunctionalityReconstruction
import RelayTheory.LeftFunctionalityBoundary

namespace RelayTheory

namespace FinKernel

/--
One-sided forward reachable dynamics after deleting input injectivity from the
#2930 interface.  The only retained data are a relation, source-side reachable
coverage, and forward source-substitution preservation.
-/
structure ForwardReachableDynamicsSimulation {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop
  total_left : ∀ {s}, ReachableResidualState P K s →
    ∃ t, ReachableResidualState P L t ∧ rel s t
  successor_forward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P K sK tK uK →
    SourceSubstitutionSuccessorRel P L sL tL uL

/-- Existence of a one-sided forward reachable-dynamics simulation. -/
def ForwardReachableDynamicsSimulates {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (ForwardReachableDynamicsSimulation P K L)

end FinKernel

/--
Output-side uniqueness remains reconstructible in the bare one-sided simulation
interface.  The proof uses only a reachable image of the source root and forward
successor preservation; no input injectivity or target surjectivity is needed.
-/
theorem finKernel_forwardSimulation_rightFunctional_on_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ForwardReachableDynamicsSimulation P K L)
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

/-- Forget input injectivity from #2930's reduced embedding interface. -/
def finKernel_forwardSimulation_of_leftFunctionalEmbedding {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.LeftFunctionalReachableDynamicsEmbedding P K L) :
    FinKernel.ForwardReachableDynamicsSimulation P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    successor_forward := h.successor_forward
  }

/-- Forget both explicit functionality fields from #2910's embedding interface. -/
def finKernel_forwardSimulation_of_embedding {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableDynamicsEmbedding P K L) :
    FinKernel.ForwardReachableDynamicsSimulation P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    successor_forward := h.successor_forward
  }

/-- Every injective reachable-dynamics embedding induces a forward simulation. -/
theorem finKernel_reachableDynamicsEmbeds_implies_forwardReachableDynamicsSimulates
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.ReachableDynamicsEmbeds P K L) :
    FinKernel.ForwardReachableDynamicsSimulates P K L := by
  rcases h with ⟨e⟩
  exact ⟨finKernel_forwardSimulation_of_embedding e⟩

/-- Identity is a one-sided forward simulation. -/
def finKernel_forwardReachableDynamicsSimulation_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ForwardReachableDynamicsSimulation P K K := by
  exact {
    rel := fun s t => s = t
    total_left := by
      intro s hs
      exact ⟨s, hs, rfl⟩
    successor_forward := by
      intro sK tK uK sL tL uL hs ht hu hSucc
      subst sL
      subst tL
      subst uL
      exact hSucc
  }

/-- One-sided forward simulations compose by relational composition. -/
def finKernel_forwardReachableDynamicsSimulation_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.ForwardReachableDynamicsSimulation P K L)
    (hLM : FinKernel.ForwardReachableDynamicsSimulation P L M) :
    FinKernel.ForwardReachableDynamicsSimulation P K M := by
  exact {
    rel := fun s u => ∃ t, hKL.rel s t ∧ hLM.rel t u
    total_left := by
      intro s hs
      rcases hKL.total_left hs with ⟨t, ht, hst⟩
      rcases hLM.total_left ht with ⟨u, hu, htu⟩
      exact ⟨u, hu, t, hst, htu⟩
    successor_forward := by
      intro sK tK uK sM tM uM hsRel htRel huRel hSuccK
      rcases hsRel with ⟨sL, hsKL, hsLM⟩
      rcases htRel with ⟨tL, htKL, htLM⟩
      rcases huRel with ⟨uL, huKL, huLM⟩
      have hSuccL := hKL.successor_forward hsKL htKL huKL hSuccK
      exact hLM.successor_forward hsLM htLM huLM hSuccL
  }

/-- Simulation existence is reflexive. -/
theorem finKernel_forwardReachableDynamicsSimulates_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ForwardReachableDynamicsSimulates P K K := by
  exact ⟨finKernel_forwardReachableDynamicsSimulation_refl P K⟩

/-- Simulation existence is transitive. -/
theorem finKernel_forwardReachableDynamicsSimulates_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.ForwardReachableDynamicsSimulates P K L)
    (hLM : FinKernel.ForwardReachableDynamicsSimulates P L M) :
    FinKernel.ForwardReachableDynamicsSimulates P K M := by
  rcases hKL with ⟨sKL⟩
  rcases hLM with ⟨sLM⟩
  exact ⟨finKernel_forwardReachableDynamicsSimulation_trans sKL sLM⟩

/-- Forget target surjectivity from #2927's stronger forward quotient interface. -/
def finKernel_forwardSimulation_of_surjective {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.SurjectiveForwardReachableDynamicsCorrespondence P K L) :
    FinKernel.ForwardReachableDynamicsSimulation P K L := by
  exact {
    rel := h.rel
    total_left := h.total_left
    successor_forward := h.successor_forward
  }

/--
The existing #2927 all-probes safe→empty quotient descends directly to a
one-sided forward simulation.
-/
theorem finKernel_allProbes_safe_empty_forwardReachableDynamicsSimulates :
    FinKernel.ForwardReachableDynamicsSimulates
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact ⟨finKernel_forwardSimulation_of_surjective
    finKernel_allProbes_safeToEmpty_surjectiveForwardCorrespondence⟩

/-- The strict #2910 empty→safe embedding also yields a simulation. -/
theorem finKernel_allProbes_empty_safe_forwardReachableDynamicsSimulates :
    FinKernel.ForwardReachableDynamicsSimulates
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact finKernel_reachableDynamicsEmbeds_implies_forwardReachableDynamicsSimulates
    finKernel_allProbes_empty_safe_reachableDynamicsEmbeds

/--
Input injectivity is not reconstructible at existence level from one-sided
forward simulation.  The safe→empty simulation exists by #2927, while #2910
already proves that no injective reachable-dynamics embedding exists there.
-/
theorem finKernel_forwardReachableDynamicsSimulates_does_not_imply_reachableDynamicsEmbeds :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.ForwardReachableDynamicsSimulates (FinKernel.allProbes 3) K L →
      FinKernel.ReachableDynamicsEmbeds (FinKernel.allProbes 3) K L) := by
  intro hPromote
  exact finKernel_allProbes_safe_empty_not_reachableDynamicsEmbeds
    (hPromote _ _ finKernel_allProbes_safe_empty_forwardReachableDynamicsSimulates)

/--
Concrete strictness witness: a one-sided forward simulation exists from the
safe frame to the empty frame, but no injective embedding does.
-/
theorem finKernel_allProbes_forwardSimulation_strict_embedding_witness :
    FinKernel.ForwardReachableDynamicsSimulates
        (FinKernel.allProbes 3)
        FinKernel.merge01SafeContextFamily3
        (FinKernel.emptyFutureContextFamily 3) ∧
      ¬ FinKernel.ReachableDynamicsEmbeds
        (FinKernel.allProbes 3)
        FinKernel.merge01SafeContextFamily3
        (FinKernel.emptyFutureContextFamily 3) := by
  exact ⟨finKernel_allProbes_safe_empty_forwardReachableDynamicsSimulates,
    finKernel_allProbes_safe_empty_not_reachableDynamicsEmbeds⟩

end RelayTheory
