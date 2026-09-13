import RelayTheory.ResidualLawNonCharacterization

namespace RelayTheory

namespace FinKernel

/--
Substitute an earlier endomorphic source action into the source coordinate of a
complete future-response function.  This operation is intrinsic to the source
argument of the response function: it does not mention future-index maps,
`GeneratedRightShift`, generic reindexing, derivatives, or residual composition.
-/
def SourceSubstituteResponse {n : Nat}
    {P : ProbeFamily n} {K : FutureContextFamily n}
    (k : FinKernel n n) (s : FullFutureResponseSpace P K) :
    FullFutureResponseSpace P K :=
  fun c hc m f obs hobs x z =>
    s c hc m (compose k f) obs hobs x z

/-- A generated kernel realizes a response state by its complete response signature. -/
def SourceRealizes {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (s : FullFutureResponseSpace P K) (k : FinKernel n n) : Prop :=
  ∃ hk : GeneratedContext K k,
    FullFutureResponseSpaceEq s (FullFutureResponse P K k)

/--
Witness-free successor presentation by universal source substitution.  No
future-index endomap and no representative of the later/action state appears in
the definition.  On a reachable source state the quantification is non-vacuous.
-/
def SourceSubstitutionSuccessorRel {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (s t u : FullFutureResponseSpace P K) : Prop :=
  ∀ k : FinKernel n n,
    SourceRealizes P K s k →
      FullFutureResponseSpaceEq u (SourceSubstituteResponse k t)

end FinKernel

/-- Source substitution respects extensional response equality. -/
theorem finKernel_sourceSubstituteResponse_respects_response_eq {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t : FinKernel.FullFutureResponseSpace P K}
    (k : FinKernel n n)
    (h : FinKernel.FullFutureResponseSpaceEq s t) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.SourceSubstituteResponse k s)
      (FinKernel.SourceSubstituteResponse k t) := by
  intro c hc m f obs hobs x z
  exact h c hc m (FinKernel.compose k f) obs hobs x z

/-- Identity source substitution is extensionally the identity operation. -/
theorem finKernel_sourceSubstituteResponse_identity {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    (s : FinKernel.FullFutureResponseSpace P K) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.SourceSubstituteResponse (FinKernel.identity n) s) s := by
  intro c hc m f obs hobs x z
  simp only [FinKernel.SourceSubstituteResponse,
    finKernel_compose_identity_after]

/-- Source substitutions compose with the project's sequential orientation. -/
theorem finKernel_sourceSubstituteResponse_composition {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    (k l : FinKernel n n) (s : FinKernel.FullFutureResponseSpace P K) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.SourceSubstituteResponse k
        (FinKernel.SourceSubstituteResponse l s))
      (FinKernel.SourceSubstituteResponse (FinKernel.compose l k) s) := by
  intro c hc m f obs hobs x z
  simp only [FinKernel.SourceSubstituteResponse]
  rw [finKernel_compose_associative]

/--
On a literal semantic signature, source substitution is exactly sequential
composition of the represented actions.
-/
theorem finKernel_sourceSubstituteResponse_fullFutureResponse {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    (k l : FinKernel n n) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.SourceSubstituteResponse k
        (FinKernel.FullFutureResponse P K l))
      (FinKernel.FullFutureResponse P K (FinKernel.compose l k)) := by
  intro c hc m f obs hobs x z
  simp only [FinKernel.SourceSubstituteResponse, FinKernel.FullFutureResponse]
  simp only [finKernel_compose_associative]

/-- Reachability provides a source-realization witness without selecting one canonically. -/
theorem finKernel_reachableResidualState_has_sourceRealization {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s : FinKernel.FullFutureResponseSpace P K}
    (hs : FinKernel.ReachableResidualState P K s) :
    ∃ k : FinKernel n n, FinKernel.SourceRealizes P K s k := by
  rcases finKernel_reachableResidualState_has_generated_signature hs with
    ⟨k, hk, hsk⟩
  exact ⟨k, hk, hsk⟩

/--
Every extensional residual composition satisfies the universal source-
substitution successor law.  Functionality of the previously earned residual
relation supplies representative independence for every source realization.
-/
theorem finKernel_residualComposeRel_implies_sourceSubstitutionSuccessorRel
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (htReachable : FinKernel.ReachableResidualState P K t)
    (hComp : FinKernel.ResidualComposeRel P K s t u) :
    FinKernel.SourceSubstitutionSuccessorRel P K s t u := by
  rcases htReachable with ⟨l, hl, htlId⟩
  intro k hkRealizes
  rcases hkRealizes with ⟨hk, hskSig⟩
  have hskId : FinKernel.FullFutureResponseSpaceEq s
      (FinKernel.IdentityResidualState P K k hk) :=
    finKernel_fullFutureResponseSpaceEq_trans hskSig
      (finKernel_fullFutureResponseSpaceEq_symm
        (finKernel_identityResidualState_eq_fullFutureResponse
          (P := P) hk))
  have htlSig : FinKernel.FullFutureResponseSpaceEq t
      (FinKernel.FullFutureResponse P K l) :=
    finKernel_fullFutureResponseSpaceEq_trans htlId
      (finKernel_identityResidualState_eq_fullFutureResponse
        (P := P) hl)
  have hSubT := finKernel_sourceSubstituteResponse_respects_response_eq
    (P := P) (K := K) k htlSig
  have hSubSignature := finKernel_sourceSubstituteResponse_fullFutureResponse
    (P := P) (K := K) k l
  let hcomp : FinKernel.GeneratedContext K (FinKernel.compose l k) :=
    finKernel_generatedContext_compose hk hl
  have hSignatureResidual : FinKernel.FullFutureResponseSpaceEq
      (FinKernel.FullFutureResponse P K (FinKernel.compose l k))
      (FinKernel.IdentityResidualState P K (FinKernel.compose l k) hcomp) :=
    finKernel_fullFutureResponseSpaceEq_symm
      (finKernel_identityResidualState_eq_fullFutureResponse
        (P := P) hcomp)
  have hOut : FinKernel.FullFutureResponseSpaceEq
      (FinKernel.SourceSubstituteResponse k t)
      (FinKernel.IdentityResidualState P K (FinKernel.compose l k) hcomp) :=
    finKernel_fullFutureResponseSpaceEq_trans hSubT
      (finKernel_fullFutureResponseSpaceEq_trans hSubSignature
        hSignatureResidual)
  have hCandidate : FinKernel.ResidualComposeRel P K s t
      (FinKernel.SourceSubstituteResponse k t) := by
    exact ⟨k, hk, l, hl, hskId, htlId, hOut⟩
  exact finKernel_residualComposeRel_functional_up_to_response_eq
    hComp hCandidate

/--
Conversely, on reachable source/action states the universal source-substitution
law reconstructs the existing residual composition relation.
-/
theorem finKernel_sourceSubstitutionSuccessorRel_implies_residualComposeRel
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hsReachable : FinKernel.ReachableResidualState P K s)
    (htReachable : FinKernel.ReachableResidualState P K t)
    (hSource : FinKernel.SourceSubstitutionSuccessorRel P K s t u) :
    FinKernel.ResidualComposeRel P K s t u := by
  rcases hsReachable with ⟨k, hk, hskId⟩
  rcases htReachable with ⟨l, hl, htlId⟩
  have hskSig : FinKernel.FullFutureResponseSpaceEq s
      (FinKernel.FullFutureResponse P K k) :=
    finKernel_fullFutureResponseSpaceEq_trans hskId
      (finKernel_identityResidualState_eq_fullFutureResponse
        (P := P) hk)
  have htlSig : FinKernel.FullFutureResponseSpaceEq t
      (FinKernel.FullFutureResponse P K l) :=
    finKernel_fullFutureResponseSpaceEq_trans htlId
      (finKernel_identityResidualState_eq_fullFutureResponse
        (P := P) hl)
  have hAtSource := hSource k ⟨hk, hskSig⟩
  have hSubT := finKernel_sourceSubstituteResponse_respects_response_eq
    (P := P) (K := K) k htlSig
  have hSubSignature := finKernel_sourceSubstituteResponse_fullFutureResponse
    (P := P) (K := K) k l
  let hcomp : FinKernel.GeneratedContext K (FinKernel.compose l k) :=
    finKernel_generatedContext_compose hk hl
  have hSignatureResidual : FinKernel.FullFutureResponseSpaceEq
      (FinKernel.FullFutureResponse P K (FinKernel.compose l k))
      (FinKernel.IdentityResidualState P K (FinKernel.compose l k) hcomp) :=
    finKernel_fullFutureResponseSpaceEq_symm
      (finKernel_identityResidualState_eq_fullFutureResponse
        (P := P) hcomp)
  have hu : FinKernel.FullFutureResponseSpaceEq u
      (FinKernel.IdentityResidualState P K (FinKernel.compose l k) hcomp) :=
    finKernel_fullFutureResponseSpaceEq_trans hAtSource
      (finKernel_fullFutureResponseSpaceEq_trans hSubT
        (finKernel_fullFutureResponseSpaceEq_trans hSubSignature
          hSignatureResidual))
  exact ⟨k, hk, l, hl, hskId, htlId, hu⟩

/--
Main Level-B characterization: on reachable source/action states, the previously
earned residual composition relation is exactly intrinsic source substitution.
The theorem statement exposes no future-index map, derivative, or right shift.
-/
theorem finKernel_residualComposeRel_iff_sourceSubstitutionSuccessorRel
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hsReachable : FinKernel.ReachableResidualState P K s)
    (htReachable : FinKernel.ReachableResidualState P K t) :
    FinKernel.ResidualComposeRel P K s t u ↔
      FinKernel.SourceSubstitutionSuccessorRel P K s t u := by
  constructor
  · exact finKernel_residualComposeRel_implies_sourceSubstitutionSuccessorRel
      htReachable
  · exact finKernel_sourceSubstitutionSuccessorRel_implies_residualComposeRel
      hsReachable htReachable

/-- Totality transports from the earned residual relation to source substitution. -/
theorem finKernel_sourceSubstitutionSuccessorRel_total_on_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t : FinKernel.FullFutureResponseSpace P K}
    (hs : FinKernel.ReachableResidualState P K s)
    (ht : FinKernel.ReachableResidualState P K t) :
    ∃ u : FinKernel.FullFutureResponseSpace P K,
      FinKernel.SourceSubstitutionSuccessorRel P K s t u ∧
      FinKernel.ReachableResidualState P K u := by
  rcases finKernel_reachable_residuals_have_composite hs ht with ⟨u, hComp, hu⟩
  exact ⟨u,
    (finKernel_residualComposeRel_iff_sourceSubstitutionSuccessorRel hs ht).1 hComp,
    hu⟩

/-- Functionality transports to the source-substitution presentation on reachable inputs. -/
theorem finKernel_sourceSubstitutionSuccessorRel_functional_on_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t u u' : FinKernel.FullFutureResponseSpace P K}
    (hs : FinKernel.ReachableResidualState P K s)
    (ht : FinKernel.ReachableResidualState P K t)
    (h : FinKernel.SourceSubstitutionSuccessorRel P K s t u)
    (h' : FinKernel.SourceSubstitutionSuccessorRel P K s t u') :
    FinKernel.FullFutureResponseSpaceEq u u' := by
  exact finKernel_residualComposeRel_functional_up_to_response_eq
    ((finKernel_residualComposeRel_iff_sourceSubstitutionSuccessorRel hs ht).2 h)
    ((finKernel_residualComposeRel_iff_sourceSubstitutionSuccessorRel hs ht).2 h')

/--
Safe `merge01`: source-substitution presentation preserves the existing
representative-gauge equality of the composite outputs.
-/
theorem finKernel_merge01_safe_sourceSubstitution_composite_gauge :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01SafeContextFamily3
        (FinKernel.compose
          (FinKernel.dirac finCollapseHidden3)
          (FinKernel.dirac finCollapseHidden3))
        (finKernel_generatedContext_compose
          finKernel_merge01_collapse_generated_safe
          finKernel_merge01_collapse_generated_safe))
      (FinKernel.IdentityResidualState
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01SafeContextFamily3
        (FinKernel.compose (FinKernel.identity 3) (FinKernel.identity 3))
        (finKernel_generatedContext_compose
          FinKernel.GeneratedContext.identity
          FinKernel.GeneratedContext.identity)) :=
  finKernel_merge01_safe_residual_composite_representative_gauge

/-- Expanded access still preserves the previously earned residual distinction. -/
theorem finKernel_merge01_expanded_sourceSubstitution_distinction_survives :
    ¬ FinKernel.IdentityResidualStateEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity :=
  finKernel_merge01_expanded_residual_distinction_survives

/-- Acceptance bundle for the #2829 first transaction. -/
theorem finKernel_source_substitution_characterization_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
      {s t u : FinKernel.FullFutureResponseSpace P K},
      FinKernel.ReachableResidualState P K s →
      FinKernel.ReachableResidualState P K t →
        (FinKernel.ResidualComposeRel P K s t u ↔
          FinKernel.SourceSubstitutionSuccessorRel P K s t u)) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
      {s t : FinKernel.FullFutureResponseSpace P K},
      FinKernel.ReachableResidualState P K s →
      FinKernel.ReachableResidualState P K t →
        ∃ u : FinKernel.FullFutureResponseSpace P K,
          FinKernel.SourceSubstitutionSuccessorRel P K s t u ∧
          FinKernel.ReachableResidualState P K u) ∧
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01SafeContextFamily3
        (FinKernel.compose
          (FinKernel.dirac finCollapseHidden3)
          (FinKernel.dirac finCollapseHidden3))
        (finKernel_generatedContext_compose
          finKernel_merge01_collapse_generated_safe
          finKernel_merge01_collapse_generated_safe))
      (FinKernel.IdentityResidualState
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01SafeContextFamily3
        (FinKernel.compose (FinKernel.identity 3) (FinKernel.identity 3))
        (finKernel_generatedContext_compose
          FinKernel.GeneratedContext.identity
          FinKernel.GeneratedContext.identity)) ∧
    ¬ FinKernel.IdentityResidualStateEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity := by
  constructor
  · intro n P K s t u hs ht
    exact finKernel_residualComposeRel_iff_sourceSubstitutionSuccessorRel hs ht
  · constructor
    · intro n P K s t hs ht
      exact finKernel_sourceSubstitutionSuccessorRel_total_on_reachable hs ht
    · exact ⟨finKernel_merge01_safe_sourceSubstitution_composite_gauge,
        finKernel_merge01_expanded_sourceSubstitution_distinction_survives⟩

end RelayTheory
