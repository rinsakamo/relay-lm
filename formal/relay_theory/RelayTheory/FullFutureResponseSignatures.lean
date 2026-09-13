import RelayTheory.ContextualActionCompositionDescent

namespace RelayTheory

namespace FinKernel

/--
The exact scalar-response carrier for every generated future continuation,
every compatible source, and every admitted downstream observation.  This is
an extensional response object; it does not mention contextual action classes
or any quotient algebra.
-/
abbrev FullFutureResponseSpace {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n) :=
  (c : FinKernel n n) →
  GeneratedContext K c →
  (m : Nat) →
  (f : FinKernel m n) →
  (obs : Observation n) →
  P obs →
  Fin m →
  Fin obs.1 →
  Rat

/--
Full admissible-future response signature of one endomorphic action.  The value
at an index is the exact scalar response of `obs ∘ c ∘ k ∘ f`.
-/
def FullFutureResponse {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (k : FinKernel n n) : FullFutureResponseSpace P K :=
  fun c _ m f obs _ x z =>
    compose obs.2 (compose (compose c k) f) x z

/-- Pointwise extensional equality on the full-future response carrier. -/
def FullFutureResponseSpaceEq {n : Nat}
    {P : ProbeFamily n} {K : FutureContextFamily n}
    (s t : FullFutureResponseSpace P K) : Prop :=
  ∀ c (hc : GeneratedContext K c) m f obs (hobs : P obs) x z,
    s c hc m f obs hobs x z = t c hc m f obs hobs x z

/-- Two actions have the same complete response signature. -/
def FullFutureResponseEq {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (k l : FinKernel n n) : Prop :=
  FullFutureResponseSpaceEq
    (FullFutureResponse P K k)
    (FullFutureResponse P K l)

/--
Residual / derivative action generated directly by reindexing the future
continuation coordinate.  No quotient transport is used.
-/
def FutureDerivative {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (l : FinKernel n n) (hl : GeneratedContext K l)
    (s : FullFutureResponseSpace P K) : FullFutureResponseSpace P K :=
  fun c hc m f obs hobs x z =>
    s (compose c l) (GeneratedContext.seq hl hc)
      m f obs hobs x z

/--
Two generated actions induce the same derivative on every semantic response
signature arising from a literal action.
-/
def DerivativeEqOnSemanticSignatures {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (l l' : FinKernel n n)
    (hl : GeneratedContext K l) (hl' : GeneratedContext K l') : Prop :=
  ∀ k : FinKernel n n,
    FullFutureResponseSpaceEq
      (FutureDerivative P K l hl (FullFutureResponse P K k))
      (FutureDerivative P K l' hl' (FullFutureResponse P K k))

end FinKernel

/-- Full-future response equality is reflexive. -/
theorem finKernel_fullFutureResponseSpaceEq_refl {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    (s : FinKernel.FullFutureResponseSpace P K) :
    FinKernel.FullFutureResponseSpaceEq s s := by
  intro c hc m f obs hobs x z
  rfl

/-- Full-future response equality is symmetric. -/
theorem finKernel_fullFutureResponseSpaceEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.FullFutureResponseSpaceEq s t) :
    FinKernel.FullFutureResponseSpaceEq t s := by
  intro c hc m f obs hobs x z
  exact (h c hc m f obs hobs x z).symm

/-- Full-future response equality is transitive. -/
theorem finKernel_fullFutureResponseSpaceEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hst : FinKernel.FullFutureResponseSpaceEq s t)
    (htu : FinKernel.FullFutureResponseSpaceEq t u) :
    FinKernel.FullFutureResponseSpaceEq s u := by
  intro c hc m f obs hobs x z
  exact Eq.trans (hst c hc m f obs hobs x z)
    (htu c hc m f obs hobs x z)

/--
Normalization only: closure-relative contextual action equivalence is exactly
pointwise equality of the independently defined full-future response signature.
-/
theorem finKernel_contextualActionEq_iff_fullFutureResponseEq {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n} :
    FinKernel.ContextualActionEq P K k l ↔
      FinKernel.FullFutureResponseEq P K k l := by
  constructor
  · intro h c hc m f obs hobs x z
    simpa [FinKernel.FullFutureResponse] using
      h c hc f obs hobs x z
  · intro h c hc m f obs hobs x z
    simpa [FinKernel.FullFutureResponse] using
      h c hc m f obs hobs x z

/--
Composition with a generated later action is reconstructed by derivative
reindexing of the earlier action's response signature.
-/
theorem finKernel_fullFutureResponse_compose_as_derivative {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.FullFutureResponse P K (FinKernel.compose l k))
      (FinKernel.FutureDerivative P K l hl
        (FinKernel.FullFutureResponse P K k)) := by
  intro c hc m f obs hobs x z
  simp only [FinKernel.FullFutureResponse, FinKernel.FutureDerivative]
  rw [finKernel_compose_associative k l c]

/--
Residual composition law on the semantic response-signature image.  The law is
proved directly from future-index reindexing and ordinary associativity.
-/
theorem finKernel_futureDerivative_composition_on_signature {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {k l r : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.FutureDerivative P K (FinKernel.compose l k)
        (FinKernel.GeneratedContext.seq hk hl)
        (FinKernel.FullFutureResponse P K r))
      (FinKernel.FutureDerivative P K l hl
        (FinKernel.FutureDerivative P K k hk
          (FinKernel.FullFutureResponse P K r))) := by
  intro c hc m f obs hobs x z
  simp only [FinKernel.FutureDerivative, FinKernel.FullFutureResponse]
  rw [finKernel_compose_associative k l c]

/--
Contextually equivalent generated representatives induce the same derivative on
every semantic response signature.
-/
theorem finKernel_contextualActionEq_implies_derivativeEqOnSemanticSignatures
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l')
    (hll : FinKernel.ContextualActionEq P K l l') :
    FinKernel.DerivativeEqOnSemanticSignatures P K l l' hl hl' := by
  intro k c hc m f obs hobs x z
  have hComposed : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k) (FinKernel.compose l' k) :=
    finKernel_contextualActionEq_precompose hll
  have hResponse : FinKernel.FullFutureResponseEq P K
      (FinKernel.compose l k) (FinKernel.compose l' k) :=
    (finKernel_contextualActionEq_iff_fullFutureResponseEq).1 hComposed
  have hv := hResponse c hc m f obs hobs x z
  simpa only [FinKernel.FutureDerivative, FinKernel.FullFutureResponse,
    finKernel_compose_associative] using hv

/--
Faithfulness: equality of derivatives on semantic signatures already recovers
contextual action equivalence.  The identity action signature is sufficient to
reconstruct the action response signature.
-/
theorem finKernel_derivativeEqOnSemanticSignatures_implies_contextualActionEq
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l')
    (hD : FinKernel.DerivativeEqOnSemanticSignatures P K l l' hl hl') :
    FinKernel.ContextualActionEq P K l l' := by
  apply (finKernel_contextualActionEq_iff_fullFutureResponseEq).2
  intro c hc m f obs hobs x z
  have hId := hD (FinKernel.identity n) c hc m f obs hobs x z
  simpa only [FinKernel.FutureDerivative, FinKernel.FullFutureResponse,
    finKernel_compose_identity_before] using hId

/--
Generated contextual action classes and derivative actions on the semantic
response image carry exactly the same extensional distinction.
-/
theorem finKernel_contextualActionEq_iff_derivativeEqOnSemanticSignatures
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l') :
    FinKernel.ContextualActionEq P K l l' ↔
      FinKernel.DerivativeEqOnSemanticSignatures P K l l' hl hl' := by
  constructor
  · exact finKernel_contextualActionEq_implies_derivativeEqOnSemanticSignatures
      hl hl'
  · exact finKernel_derivativeEqOnSemanticSignatures_implies_contextualActionEq
      hl hl'

/-- Safe `merge01`: collapse and identity have the same complete response signature. -/
theorem finKernel_merge01_safe_collapse_identity_fullFutureResponseEq :
    FinKernel.FullFutureResponseEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) := by
  exact (finKernel_contextualActionEq_iff_fullFutureResponseEq).1
    finKernel_merge01_collapse_identity_contextual_action_eq_safe

/--
Safe `merge01`: literal collapse and identity also induce the same derivative on
every semantic response signature.
-/
theorem finKernel_merge01_safe_collapse_identity_derivativeEq :
    FinKernel.DerivativeEqOnSemanticSignatures
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity := by
  exact (finKernel_contextualActionEq_iff_derivativeEqOnSemanticSignatures
    finKernel_merge01_collapse_generated_safe
    FinKernel.GeneratedContext.identity).1
    finKernel_merge01_collapse_identity_contextual_action_eq_safe

/--
Expanded `merge01` remains a negative control: the previously merged action
signatures split once `moveOneToTwo` is admitted.
-/
theorem finKernel_merge01_expanded_collapse_identity_not_fullFutureResponseEq :
    ¬ FinKernel.FullFutureResponseEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) := by
  intro hResponse
  exact finKernel_merge01_collapse_identity_not_contextual_action_eq_expanded
    ((finKernel_contextualActionEq_iff_fullFutureResponseEq).2 hResponse)

/--
Acceptance bundle for #2794: response signatures normalize contextual action
equivalence, composition reconstructs through derivative reindexing, the
representation is faithful on generated actions, and the safe/expanded fixtures
retain their positive/negative distinction.
-/
theorem finKernel_full_future_response_signature_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
      {k l : FinKernel n n},
      FinKernel.GeneratedContext K l →
      FinKernel.FullFutureResponseSpaceEq
        (FinKernel.FullFutureResponse P K (FinKernel.compose l k))
        (FinKernel.FutureDerivative P K l ‹FinKernel.GeneratedContext K l›
          (FinKernel.FullFutureResponse P K k))) ∧
    FinKernel.identity 3 ≠ FinKernel.dirac finCollapseHidden3 ∧
    FinKernel.FullFutureResponseEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) ∧
    FinKernel.DerivativeEqOnSemanticSignatures
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity ∧
    ¬ FinKernel.FullFutureResponseEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) := by
  constructor
  · intro n P K k l hl
    exact finKernel_fullFutureResponse_compose_as_derivative hl
  · exact ⟨finKernel_identity3_ne_hidden_collapse,
      finKernel_merge01_safe_collapse_identity_fullFutureResponseEq,
      finKernel_merge01_safe_collapse_identity_derivativeEq,
      finKernel_merge01_expanded_collapse_identity_not_fullFutureResponseEq⟩

end RelayTheory
