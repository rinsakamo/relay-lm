import RelayTheory.CanonicalResidualReindexing

namespace RelayTheory

namespace FinKernel

/--
The residual response state reached from the identity response signature by one
generated continuation.  This is defined through the canonical reindexing from
#2801 rather than by naming the action's own signature.
-/
def IdentityResidualState {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (l : FinKernel n n) (hl : GeneratedContext K l) :
    FullFutureResponseSpace P K :=
  ReindexFullFutureResponse (GeneratedRightShift l hl)
    (FullFutureResponse P K (identity n))

/-- Extensional equality of two generated identity-residual states. -/
def IdentityResidualStateEq {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (l l' : FinKernel n n)
    (hl : GeneratedContext K l) (hl' : GeneratedContext K l') : Prop :=
  FullFutureResponseSpaceEq
    (IdentityResidualState P K l hl)
    (IdentityResidualState P K l' hl')

/--
Extensional reachable-residual orbit predicate.  The carrier is a response
function; literal action labels are existential witnesses only.
-/
def ReachableResidualState {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (s : FullFutureResponseSpace P K) : Prop :=
  ∃ l : FinKernel n n, ∃ hl : GeneratedContext K l,
    FullFutureResponseSpaceEq s (IdentityResidualState P K l hl)

end FinKernel

/--
A generated identity-residual state reconstructs the complete response signature
of the generating action.
-/
theorem finKernel_identityResidualState_eq_fullFutureResponse {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState P K l hl)
      (FinKernel.FullFutureResponse P K l) := by
  intro c hc m f obs hobs x z
  simp only [FinKernel.IdentityResidualState,
    FinKernel.ReindexFullFutureResponse,
    FinKernel.GeneratedRightShift,
    FinKernel.FullFutureResponse]
  rw [finKernel_compose_identity_before]

/--
Kernel theorem: two generated actions reach the same identity-residual state
exactly when they are contextually action-equivalent.
-/
theorem finKernel_identityResidualStateEq_iff_contextualActionEq {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l') :
    FinKernel.IdentityResidualStateEq P K l l' hl hl' ↔
      FinKernel.ContextualActionEq P K l l' := by
  constructor
  · intro hResidual
    apply (finKernel_contextualActionEq_iff_fullFutureResponseEq).2
    intro c hc m f obs hobs x z
    have hLeft := finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) hl c hc m f obs hobs x z
    have hRight := finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) hl' c hc m f obs hobs x z
    have hMiddle := hResidual c hc m f obs hobs x z
    exact hLeft.symm.trans (hMiddle.trans hRight)
  · intro hContext
    have hSignature : FinKernel.FullFutureResponseEq P K l l' :=
      (finKernel_contextualActionEq_iff_fullFutureResponseEq).1 hContext
    intro c hc m f obs hobs x z
    have hLeft := finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) hl c hc m f obs hobs x z
    have hRight := finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) hl' c hc m f obs hobs x z
    have hMiddle := hSignature c hc m f obs hobs x z
    exact hLeft.trans (hMiddle.trans hRight.symm)

/-- Every generated continuation contributes a state to the residual orbit. -/
theorem finKernel_generated_identityResidualState_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.ReachableResidualState P K
      (FinKernel.IdentityResidualState P K l hl) := by
  refine ⟨l, hl, ?_⟩
  intro c hc m f obs hobs x z
  rfl

/--
Every state in the residual orbit is extensionally the action signature of some
generated continuation.
-/
theorem finKernel_reachableResidualState_has_generated_signature {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s : FinKernel.FullFutureResponseSpace P K}
    (hs : FinKernel.ReachableResidualState P K s) :
    ∃ l : FinKernel n n, ∃ hl : FinKernel.GeneratedContext K l,
      FinKernel.FullFutureResponseSpaceEq s
        (FinKernel.FullFutureResponse P K l) := by
  rcases hs with ⟨l, hl, hs⟩
  refine ⟨l, hl, ?_⟩
  intro c hc m f obs hobs x z
  exact (hs c hc m f obs hobs x z).trans
    (finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) hl c hc m f obs hobs x z)

/--
Conversely, every generated action signature belongs extensionally to the
reachable residual orbit.
-/
theorem finKernel_generated_signature_reachableResidualState {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.ReachableResidualState P K
      (FinKernel.FullFutureResponse P K l) := by
  refine ⟨l, hl, ?_⟩
  intro c hc m f obs hobs x z
  exact (finKernel_identityResidualState_eq_fullFutureResponse
    (P := P) hl c hc m f obs hobs x z).symm

/--
Safe `merge01`: literal right-shift maps remain distinct while collapse and
identity reach the same residual response state.
-/
theorem finKernel_merge01_safe_identityResidualStateEq :
    FinKernel.IdentityResidualStateEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity := by
  exact (finKernel_identityResidualStateEq_iff_contextualActionEq
    finKernel_merge01_collapse_generated_safe
    FinKernel.GeneratedContext.identity).2
    finKernel_merge01_collapse_identity_contextual_action_eq_safe

/-- Expanded `merge01` splits the previously merged residual response states. -/
theorem finKernel_merge01_expanded_not_identityResidualStateEq :
    ¬ FinKernel.IdentityResidualStateEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity := by
  intro hResidual
  exact finKernel_merge01_collapse_identity_not_contextual_action_eq_expanded
    ((finKernel_identityResidualStateEq_iff_contextualActionEq
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity).1 hResidual)

/--
Acceptance bundle for #2804.  It proves action-identity representation by
reachable residual states while intentionally making no claim that an unlabeled
orbit carrier determines transition/composition structure.
-/
theorem finKernel_reachable_residual_orbit_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
      {l l' : FinKernel n n}
      (hl : FinKernel.GeneratedContext K l)
      (hl' : FinKernel.GeneratedContext K l'),
      FinKernel.IdentityResidualStateEq P K l l' hl hl' ↔
        FinKernel.ContextualActionEq P K l l') ∧
    FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe ≠
      FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity ∧
    FinKernel.IdentityResidualStateEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity ∧
    ¬ FinKernel.IdentityResidualStateEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity := by
  constructor
  · intro n P K l l' hl hl'
    exact finKernel_identityResidualStateEq_iff_contextualActionEq hl hl'
  · exact ⟨finKernel_merge01_safe_literal_rightShift_ne,
      finKernel_merge01_safe_identityResidualStateEq,
      finKernel_merge01_expanded_not_identityResidualStateEq⟩

end RelayTheory
