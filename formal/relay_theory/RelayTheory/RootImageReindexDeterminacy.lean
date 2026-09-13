import RelayTheory.UnaryResidualTransitionReconstruction

namespace RelayTheory

namespace FinKernel

/--
Two arbitrary generated-future index endomaps have the same semantic root
image.  The root is the complete response signature of the literal identity
action.  No action-specific right shift appears in this definition.
-/
def ReindexRootImageEq {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (r q : GeneratedContinuationIndex K → GeneratedContinuationIndex K) : Prop :=
  FullFutureResponseSpaceEq
    (ReindexFullFutureResponse r
      (FullFutureResponse P K (identity n)))
    (ReindexFullFutureResponse q
      (FullFutureResponse P K (identity n)))

/--
Two arbitrary future-index endomaps induce the same extensional action on every
reachable residual-response state.
-/
def ReindexEqOnReachable {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (r q : GeneratedContinuationIndex K → GeneratedContinuationIndex K) : Prop :=
  ∀ s : FullFutureResponseSpace P K,
    ReachableResidualState P K s →
      FullFutureResponseSpaceEq
        (ReindexFullFutureResponse r s)
        (ReindexFullFutureResponse q s)

/--
Intrinsic successor presentation through an arbitrary generated-future index
endomap.  It refers only to a root image and generic reindexing; it does not
mention `GeneratedRightShift`, `CanonicalSuccessorRel`, or `ResidualComposeRel`.
-/
def IntrinsicReindexSuccessorRel {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (s t u : FullFutureResponseSpace P K) : Prop :=
  ∃ r : GeneratedContinuationIndex K → GeneratedContinuationIndex K,
    FullFutureResponseSpaceEq t
      (ReindexFullFutureResponse r
        (FullFutureResponse P K (identity n))) ∧
    FullFutureResponseSpaceEq u (ReindexFullFutureResponse r s)

end FinKernel

/--
Root-image equality already forces two arbitrary index reindexings to agree on
every literal semantic response signature.  Source-polymorphism is the key:
the action `k` can be absorbed into the root signature's source kernel.
-/
theorem finKernel_reindexRootImageEq_implies_semantic_signature_eq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {r q : FinKernel.GeneratedContinuationIndex K →
      FinKernel.GeneratedContinuationIndex K}
    (hRoot : FinKernel.ReindexRootImageEq P K r q)
    (k : FinKernel n n) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.ReindexFullFutureResponse r
        (FinKernel.FullFutureResponse P K k))
      (FinKernel.ReindexFullFutureResponse q
        (FinKernel.FullFutureResponse P K k)) := by
  change FinKernel.FullFutureResponseSpaceEq
    (FinKernel.ReindexFullFutureResponse r
      (FinKernel.FullFutureResponse P K (FinKernel.identity n)))
    (FinKernel.ReindexFullFutureResponse q
      (FinKernel.FullFutureResponse P K (FinKernel.identity n))) at hRoot
  intro c hc m f obs hobs x z
  have hAtRoot := hRoot c hc m (FinKernel.compose k f) obs hobs x z
  simpa [FinKernel.ReindexFullFutureResponse, FinKernel.FullFutureResponse,
    finKernel_compose_identity_before, finKernel_compose_associative] using
    hAtRoot

/--
Main forward determinacy result: equal root images imply equal generic
reindexing action on the entire reachable residual-response carrier.
-/
theorem finKernel_reindexRootImageEq_implies_reindexEqOnReachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {r q : FinKernel.GeneratedContinuationIndex K →
      FinKernel.GeneratedContinuationIndex K}
    (hRoot : FinKernel.ReindexRootImageEq P K r q) :
    FinKernel.ReindexEqOnReachable P K r q := by
  intro s hs
  rcases finKernel_reachableResidualState_has_generated_signature hs with
    ⟨k, hk, hsk⟩
  have hLeft := finKernel_reindexFullFutureResponse_respects_response_eq
    (P := P) (K := K) r hsk
  have hMiddle :=
    finKernel_reindexRootImageEq_implies_semantic_signature_eq
      (P := P) (K := K) hRoot k
  have hRight := finKernel_reindexFullFutureResponse_respects_response_eq
    (P := P) (K := K) q hsk
  exact finKernel_fullFutureResponseSpaceEq_trans hLeft
    (finKernel_fullFutureResponseSpaceEq_trans hMiddle
      (finKernel_fullFutureResponseSpaceEq_symm hRight))

/--
The converse is immediate because the literal identity full-future signature is
itself a reachable residual-response state.
-/
theorem finKernel_reindexEqOnReachable_implies_reindexRootImageEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {r q : FinKernel.GeneratedContinuationIndex K →
      FinKernel.GeneratedContinuationIndex K}
    (hReachable : FinKernel.ReindexEqOnReachable P K r q) :
    FinKernel.ReindexRootImageEq P K r q := by
  have hRootReachable : FinKernel.ReachableResidualState P K
      (FinKernel.FullFutureResponse P K (FinKernel.identity n)) :=
    finKernel_generated_signature_reachableResidualState
      (P := P) (K := K)
      (l := FinKernel.identity n)
      FinKernel.GeneratedContext.identity
  exact hReachable
    (FinKernel.FullFutureResponse P K (FinKernel.identity n))
    hRootReachable

/--
Level-B root-image determinacy: on the reachable semantic carrier, an arbitrary
future-index reindexing operator is completely determined extensionally by its
image of the root identity response.
-/
theorem finKernel_reindexRootImageEq_iff_reindexEqOnReachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {r q : FinKernel.GeneratedContinuationIndex K →
      FinKernel.GeneratedContinuationIndex K} :
    FinKernel.ReindexRootImageEq P K r q ↔
      FinKernel.ReindexEqOnReachable P K r q := by
  constructor
  · exact finKernel_reindexRootImageEq_implies_reindexEqOnReachable
  · exact finKernel_reindexEqOnReachable_implies_reindexRootImageEq

/-- Every action-specific canonical successor is an intrinsic generic-reindex successor. -/
theorem finKernel_canonicalSuccessorRel_implies_intrinsicReindexSuccessorRel
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.CanonicalSuccessorRel P K s t u) :
    FinKernel.IntrinsicReindexSuccessorRel P K s t u := by
  rcases h with ⟨l, hl, ht, hu⟩
  refine ⟨FinKernel.GeneratedRightShift l hl, ?_, hu⟩
  simpa only [FinKernel.IdentityResidualState] using ht

/--
For reachable source and action states, an arbitrary generic-reindex successor
is extensionally realized by any generated right-shift representative of the
action state.  Root-image determinacy supplies the bridge.
-/
theorem finKernel_intrinsicReindexSuccessorRel_implies_canonicalSuccessorRel
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hsReachable : FinKernel.ReachableResidualState P K s)
    (htReachable : FinKernel.ReachableResidualState P K t)
    (h : FinKernel.IntrinsicReindexSuccessorRel P K s t u) :
    FinKernel.CanonicalSuccessorRel P K s t u := by
  rcases htReachable with ⟨l, hl, ht⟩
  rcases h with ⟨r, hRootR, hu⟩
  refine ⟨l, hl, ht, ?_⟩
  have hRootShift : FinKernel.FullFutureResponseSpaceEq t
      (FinKernel.ReindexFullFutureResponse
        (FinKernel.GeneratedRightShift l hl)
        (FinKernel.FullFutureResponse P K (FinKernel.identity n))) := by
    simpa only [FinKernel.IdentityResidualState] using ht
  have hRootEq : FinKernel.ReindexRootImageEq P K r
      (FinKernel.GeneratedRightShift l hl) := by
    change FinKernel.FullFutureResponseSpaceEq
      (FinKernel.ReindexFullFutureResponse r
        (FinKernel.FullFutureResponse P K (FinKernel.identity n)))
      (FinKernel.ReindexFullFutureResponse
        (FinKernel.GeneratedRightShift l hl)
        (FinKernel.FullFutureResponse P K (FinKernel.identity n)))
    exact finKernel_fullFutureResponseSpaceEq_trans
      (finKernel_fullFutureResponseSpaceEq_symm hRootR) hRootShift
  have hActions : FinKernel.ReindexEqOnReachable P K r
      (FinKernel.GeneratedRightShift l hl) :=
    (finKernel_reindexRootImageEq_iff_reindexEqOnReachable).1 hRootEq
  have hAtSource := hActions s hsReachable
  exact finKernel_fullFutureResponseSpaceEq_trans hu hAtSource

/--
Action-specific unary successors and intrinsic root-image successors coincide on
reachable source/action states.
-/
theorem finKernel_canonicalSuccessorRel_iff_intrinsicReindexSuccessorRel
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hsReachable : FinKernel.ReachableResidualState P K s)
    (htReachable : FinKernel.ReachableResidualState P K t) :
    FinKernel.CanonicalSuccessorRel P K s t u ↔
      FinKernel.IntrinsicReindexSuccessorRel P K s t u := by
  constructor
  · exact finKernel_canonicalSuccessorRel_implies_intrinsicReindexSuccessorRel
  · exact finKernel_intrinsicReindexSuccessorRel_implies_canonicalSuccessorRel
      hsReachable htReachable

/--
Corollary: the earlier ternary residual composition relation also reconstructs
from intrinsic root-image reindexing alone, on reachable source/action states.
-/
theorem finKernel_residualComposeRel_iff_intrinsicReindexSuccessorRel
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hsReachable : FinKernel.ReachableResidualState P K s)
    (htReachable : FinKernel.ReachableResidualState P K t) :
    FinKernel.ResidualComposeRel P K s t u ↔
      FinKernel.IntrinsicReindexSuccessorRel P K s t u := by
  exact Iff.trans
    (finKernel_residualComposeRel_iff_canonicalSuccessorRel hsReachable)
    (finKernel_canonicalSuccessorRel_iff_intrinsicReindexSuccessorRel
      hsReachable htReachable)

/-- Safe `merge01`: literal right shifts differ, but their root images agree. -/
theorem finKernel_merge01_safe_rightShift_rootImageEq :
    FinKernel.ReindexRootImageEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe)
      (FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity) := by
  change FinKernel.IdentityResidualStateEq
    FinKernel.merge01ProbeFamily3
    FinKernel.merge01SafeContextFamily3
    (FinKernel.dirac finCollapseHidden3)
    (FinKernel.identity 3)
    finKernel_merge01_collapse_generated_safe
    FinKernel.GeneratedContext.identity
  exact finKernel_merge01_safe_identityResidualStateEq

/-- Safe root-image equality therefore determines equality on every reachable response state. -/
theorem finKernel_merge01_safe_rightShift_reindexEqOnReachable :
    FinKernel.ReindexEqOnReachable
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe)
      (FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity) :=
  (finKernel_reindexRootImageEq_iff_reindexEqOnReachable).1
    finKernel_merge01_safe_rightShift_rootImageEq

/-- Expanded continuation access still separates the two right-shift root images. -/
theorem finKernel_merge01_expanded_not_rightShift_rootImageEq :
    ¬ FinKernel.ReindexRootImageEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_expanded)
      (FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity) := by
  intro hRoot
  apply finKernel_merge01_expanded_not_identityResidualStateEq
  change FinKernel.FullFutureResponseSpaceEq
    (FinKernel.ReindexFullFutureResponse
      (FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_expanded)
      (FinKernel.FullFutureResponse
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01ExpandedContextFamily3
        (FinKernel.identity 3)))
    (FinKernel.ReindexFullFutureResponse
      (FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity)
      (FinKernel.FullFutureResponse
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01ExpandedContextFamily3
        (FinKernel.identity 3)))
  exact hRoot

/-- Acceptance bundle for #2818. -/
theorem finKernel_root_image_reindex_determinacy_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K : FinKernel.FutureContextFamily n}
      {r q : FinKernel.GeneratedContinuationIndex K →
        FinKernel.GeneratedContinuationIndex K},
      FinKernel.ReindexRootImageEq P K r q ↔
        FinKernel.ReindexEqOnReachable P K r q) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K : FinKernel.FutureContextFamily n}
      {s t u : FinKernel.FullFutureResponseSpace P K},
      FinKernel.ReachableResidualState P K s →
      FinKernel.ReachableResidualState P K t →
        (FinKernel.ResidualComposeRel P K s t u ↔
          FinKernel.IntrinsicReindexSuccessorRel P K s t u)) ∧
    FinKernel.ReindexRootImageEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe)
      (FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity) ∧
    FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe ≠
      FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity ∧
    ¬ FinKernel.ReindexRootImageEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_expanded)
      (FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity) := by
  constructor
  · intro n P K r q
    exact finKernel_reindexRootImageEq_iff_reindexEqOnReachable
  · constructor
    · intro n P K s t u hs ht
      exact finKernel_residualComposeRel_iff_intrinsicReindexSuccessorRel hs ht
    · exact ⟨finKernel_merge01_safe_rightShift_rootImageEq,
        finKernel_merge01_safe_literal_rightShift_ne,
        finKernel_merge01_expanded_not_rightShift_rootImageEq⟩

end RelayTheory