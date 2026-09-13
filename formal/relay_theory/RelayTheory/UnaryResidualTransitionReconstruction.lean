import RelayTheory.WitnessFreeResidualAssociativity

namespace RelayTheory

namespace FinKernel

/--
Two independently defined canonical residual reindexing operators agree on the
reachable residual-response carrier.  This definition does not mention the
ternary residual composition relation.
-/
def UnaryResidualEqOnReachable {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (l l' : FinKernel n n)
    (hl : GeneratedContext K l) (hl' : GeneratedContext K l') : Prop :=
  ∀ s : FullFutureResponseSpace P K,
    ReachableResidualState P K s →
      FullFutureResponseSpaceEq
        (ReindexFullFutureResponse (GeneratedRightShift l hl) s)
        (ReindexFullFutureResponse (GeneratedRightShift l' hl') s)

/--
An independently defined unary-successor presentation of sequential residual
dynamics.  The later residual state `t` is represented existentially by a
generated continuation, and `u` is obtained by canonical future reindexing of
`s`.  `ResidualComposeRel` is intentionally absent from this definition.
-/
def CanonicalSuccessorRel {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (s t u : FullFutureResponseSpace P K) : Prop :=
  ∃ l : FinKernel n n,
    ∃ hl : GeneratedContext K l,
      FullFutureResponseSpaceEq t (IdentityResidualState P K l hl) ∧
      FullFutureResponseSpaceEq u
        (ReindexFullFutureResponse (GeneratedRightShift l hl) s)

end FinKernel

/-- Canonical reindexing preserves extensional equality of response states. -/
theorem finKernel_reindexFullFutureResponse_respects_response_eq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    (r : FinKernel.GeneratedContinuationIndex K →
      FinKernel.GeneratedContinuationIndex K)
    {s t : FinKernel.FullFutureResponseSpace P K}
    (hst : FinKernel.FullFutureResponseSpaceEq s t) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.ReindexFullFutureResponse r s)
      (FinKernel.ReindexFullFutureResponse r t) := by
  intro c hc m f obs hobs x z
  exact hst
    (r { kernel := c, generated := hc }).kernel
    (r { kernel := c, generated := hc }).generated
    m f obs hobs x z

/--
Residual-state-equivalent generated continuations induce the same independently
defined unary canonical transition on every reachable residual input.
-/
theorem finKernel_identityResidualStateEq_implies_unaryResidualEqOnReachable
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l')
    (hResidual : FinKernel.IdentityResidualStateEq P K l l' hl hl') :
    FinKernel.UnaryResidualEqOnReachable P K l l' hl hl' := by
  have hContext : FinKernel.ContextualActionEq P K l l' :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq hl hl').1
      hResidual
  have hDerivative : FinKernel.DerivativeEqOnSemanticSignatures
      P K l l' hl hl' :=
    (finKernel_contextualActionEq_iff_derivativeEqOnSemanticSignatures
      hl hl').1 hContext
  have hCanonical : FinKernel.CanonicalResidualEqOnSemanticSignatures
      P K l l' hl hl' :=
    (finKernel_derivativeEq_iff_canonicalResidualEqOnSemanticSignatures
      hl hl').1 hDerivative
  intro s hs
  rcases finKernel_reachableResidualState_has_generated_signature hs with
    ⟨k, hk, hsk⟩
  have hLeft := finKernel_reindexFullFutureResponse_respects_response_eq
    (P := P) (K := K)
    (FinKernel.GeneratedRightShift l hl) hsk
  have hMiddle := hCanonical k
  have hRight := finKernel_reindexFullFutureResponse_respects_response_eq
    (P := P) (K := K)
    (FinKernel.GeneratedRightShift l' hl') hsk
  exact finKernel_fullFutureResponseSpaceEq_trans hLeft
    (finKernel_fullFutureResponseSpaceEq_trans hMiddle
      (finKernel_fullFutureResponseSpaceEq_symm hRight))

/--
Faithfulness of the unary presentation: equality of canonical unary transitions
on every reachable input already recovers equality of the generated residual
action states.  The literal identity signature is itself reachable and suffices
as the separating input.
-/
theorem finKernel_unaryResidualEqOnReachable_implies_identityResidualStateEq
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l')
    (hUnary : FinKernel.UnaryResidualEqOnReachable P K l l' hl hl') :
    FinKernel.IdentityResidualStateEq P K l l' hl hl' := by
  have hIdentityReachable : FinKernel.ReachableResidualState P K
      (FinKernel.FullFutureResponse P K (FinKernel.identity n)) :=
    finKernel_generated_signature_reachableResidualState
      (P := P) (K := K)
      (l := FinKernel.identity n)
      FinKernel.GeneratedContext.identity
  have hAtIdentity := hUnary
    (FinKernel.FullFutureResponse P K (FinKernel.identity n))
    hIdentityReachable
  change FinKernel.FullFutureResponseSpaceEq
    (FinKernel.IdentityResidualState P K l hl)
    (FinKernel.IdentityResidualState P K l' hl')
  simpa only [FinKernel.IdentityResidualState] using hAtIdentity

/--
Generated residual action states and their unary canonical transitions on the
reachable carrier carry exactly the same extensional distinctions.
-/
theorem finKernel_identityResidualStateEq_iff_unaryResidualEqOnReachable
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l') :
    FinKernel.IdentityResidualStateEq P K l l' hl hl' ↔
      FinKernel.UnaryResidualEqOnReachable P K l l' hl hl' := by
  constructor
  · exact finKernel_identityResidualStateEq_implies_unaryResidualEqOnReachable
      hl hl'
  · exact finKernel_unaryResidualEqOnReachable_implies_identityResidualStateEq
      hl hl'

/--
Applying the independently defined unary transition for a generated later action
`l` to the residual state of an earlier generated action `k` yields the residual
state of the literal composite `l ∘ k`.
-/
theorem finKernel_canonicalSuccessor_generated_step {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.ReindexFullFutureResponse
        (FinKernel.GeneratedRightShift l hl)
        (FinKernel.IdentityResidualState P K k hk))
      (FinKernel.IdentityResidualState P K (FinKernel.compose l k)
        (finKernel_generatedContext_compose hk hl)) := by
  have hComposition :=
    finKernel_canonicalResidual_composition (P := P) (K := K) hk hl
      (FinKernel.FullFutureResponse P K (FinKernel.identity n))
  have hSymm := finKernel_fullFutureResponseSpaceEq_symm hComposition
  simpa only [FinKernel.IdentityResidualState] using hSymm

/-- Every ternary residual-composition witness gives an independent unary successor witness. -/
theorem finKernel_residualComposeRel_implies_canonicalSuccessorRel {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.ResidualComposeRel P K s t u) :
    FinKernel.CanonicalSuccessorRel P K s t u := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hu⟩
  refine ⟨l, hl, ht, ?_⟩
  have hSource := finKernel_reindexFullFutureResponse_respects_response_eq
    (P := P) (K := K)
    (FinKernel.GeneratedRightShift l hl) hs
  have hGenerated := finKernel_canonicalSuccessor_generated_step
    (P := P) (K := K) hk hl
  have hFromSource := finKernel_fullFutureResponseSpaceEq_trans
    hSource hGenerated
  exact finKernel_fullFutureResponseSpaceEq_trans hu
    (finKernel_fullFutureResponseSpaceEq_symm hFromSource)

/--
On a reachable source state, every independently defined canonical unary
successor witness reconstructs a ternary residual-composition witness.
-/
theorem finKernel_canonicalSuccessorRel_implies_residualComposeRel {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hsReachable : FinKernel.ReachableResidualState P K s)
    (h : FinKernel.CanonicalSuccessorRel P K s t u) :
    FinKernel.ResidualComposeRel P K s t u := by
  rcases hsReachable with ⟨k, hk, hs⟩
  rcases h with ⟨l, hl, ht, hu⟩
  refine ⟨k, hk, l, hl, hs, ht, ?_⟩
  have hSource := finKernel_reindexFullFutureResponse_respects_response_eq
    (P := P) (K := K)
    (FinKernel.GeneratedRightShift l hl) hs
  have hGenerated := finKernel_canonicalSuccessor_generated_step
    (P := P) (K := K) hk hl
  exact finKernel_fullFutureResponseSpaceEq_trans hu
    (finKernel_fullFutureResponseSpaceEq_trans hSource hGenerated)

/--
Main reconstruction theorem: on reachable sources, the witness-free ternary
composition relation is exactly the independently defined unary canonical
successor relation.
-/
theorem finKernel_residualComposeRel_iff_canonicalSuccessorRel {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hsReachable : FinKernel.ReachableResidualState P K s) :
    FinKernel.ResidualComposeRel P K s t u ↔
      FinKernel.CanonicalSuccessorRel P K s t u := by
  constructor
  · exact finKernel_residualComposeRel_implies_canonicalSuccessorRel
  · exact finKernel_canonicalSuccessorRel_implies_residualComposeRel hsReachable

/--
Unary residual transitions inherit their composition law directly from the
canonical future-index reindexing algebra of #2801.
-/
theorem finKernel_unaryResidualTransition_composition {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseOperatorEq (P := P) (K := K)
      (FinKernel.ReindexFullFutureResponse (P := P) (K := K)
        (FinKernel.GeneratedRightShift (FinKernel.compose l k)
          (FinKernel.GeneratedContext.seq hk hl)))
      (fun s : FinKernel.FullFutureResponseSpace P K =>
        FinKernel.ReindexFullFutureResponse (P := P) (K := K)
          (FinKernel.GeneratedRightShift l hl)
          (FinKernel.ReindexFullFutureResponse (P := P) (K := K)
            (FinKernel.GeneratedRightShift k hk) s)) := by
  exact finKernel_canonicalResidual_composition hk hl

/-- Safe `merge01`: equivalent residual action states induce equal unary transitions on all reachable inputs. -/
theorem finKernel_merge01_safe_unaryResidualEqOnReachable :
    FinKernel.UnaryResidualEqOnReachable
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity := by
  exact (finKernel_identityResidualStateEq_iff_unaryResidualEqOnReachable
    finKernel_merge01_collapse_generated_safe
    FinKernel.GeneratedContext.identity).1
    finKernel_merge01_safe_identityResidualStateEq

/-- Expanded `merge01` still separates the unary residual-transition semantics. -/
theorem finKernel_merge01_expanded_not_unaryResidualEqOnReachable :
    ¬ FinKernel.UnaryResidualEqOnReachable
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_expanded
      FinKernel.GeneratedContext.identity := by
  intro hUnary
  exact finKernel_merge01_expanded_not_identityResidualStateEq
    ((finKernel_identityResidualStateEq_iff_unaryResidualEqOnReachable
      finKernel_merge01_collapse_generated_expanded
      FinKernel.GeneratedContext.identity).2 hUnary)

/-- Acceptance bundle for #2816. -/
theorem finKernel_unary_residual_transition_reconstruction_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K : FinKernel.FutureContextFamily n}
      {l l' : FinKernel n n}
      (hl : FinKernel.GeneratedContext K l)
      (hl' : FinKernel.GeneratedContext K l'),
      FinKernel.IdentityResidualStateEq P K l l' hl hl' ↔
        FinKernel.UnaryResidualEqOnReachable P K l l' hl hl') ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K : FinKernel.FutureContextFamily n}
      {s t u : FinKernel.FullFutureResponseSpace P K},
      FinKernel.ReachableResidualState P K s →
        (FinKernel.ResidualComposeRel P K s t u ↔
          FinKernel.CanonicalSuccessorRel P K s t u)) ∧
    FinKernel.UnaryResidualEqOnReachable
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity ∧
    ¬ FinKernel.UnaryResidualEqOnReachable
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_expanded
      FinKernel.GeneratedContext.identity ∧
    FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe ≠
      FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity := by
  constructor
  · intro n P K l l' hl hl'
    exact finKernel_identityResidualStateEq_iff_unaryResidualEqOnReachable
      hl hl'
  · constructor
    · intro n P K s t u hs
      exact finKernel_residualComposeRel_iff_canonicalSuccessorRel hs
    · exact ⟨finKernel_merge01_safe_unaryResidualEqOnReachable,
        finKernel_merge01_expanded_not_unaryResidualEqOnReachable,
        finKernel_merge01_safe_literal_rightShift_ne⟩

end RelayTheory