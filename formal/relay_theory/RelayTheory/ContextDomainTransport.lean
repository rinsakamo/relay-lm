import RelayTheory.SourceSubstitutionCharacterization

namespace RelayTheory

namespace FinKernel

/--
Two declared future-context families have the same generated admissibility
domain when they admit exactly the same finite sequential contexts after closure.
This compares the generated predicate, not the literal generator enumeration.
-/
def GeneratedDomainEq {n : Nat}
    (K L : FutureContextFamily n) : Prop :=
  ∀ c : FinKernel n n, GeneratedContext K c ↔ GeneratedContext L c

/--
Transport a complete response function across extensionally equal generated
context domains.  Only the admissibility proof is translated; response values,
context kernels, source kernels, and observations are unchanged.
-/
def TransportResponse {n : Nat}
    {P : ProbeFamily n} {K L : FutureContextFamily n}
    (hKL : GeneratedDomainEq K L)
    (s : FullFutureResponseSpace P K) :
    FullFutureResponseSpace P L :=
  fun c hc m f obs hobs x z =>
    s c ((hKL c).2 hc) m f obs hobs x z

end FinKernel

/-- Generated-domain equivalence is reflexive. -/
theorem finKernel_generatedDomainEq_refl {n : Nat}
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.GeneratedDomainEq K K := by
  intro c
  rfl

/-- Generated-domain equivalence is symmetric. -/
theorem finKernel_generatedDomainEq_symm {n : Nat}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L) :
    FinKernel.GeneratedDomainEq L K := by
  intro c
  exact (hKL c).symm

/-- Generated-domain equivalence is transitive. -/
theorem finKernel_generatedDomainEq_trans {n : Nat}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    (hLM : FinKernel.GeneratedDomainEq L M) :
    FinKernel.GeneratedDomainEq K M := by
  intro c
  exact Iff.trans (hKL c) (hLM c)

/-- Response transport preserves extensional response equality. -/
theorem finKernel_transportResponse_respects_response_eq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    {s t : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.FullFutureResponseSpaceEq s t) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.TransportResponse hKL s)
      (FinKernel.TransportResponse hKL t) := by
  intro c hc m f obs hobs x z
  exact h c ((hKL c).2 hc) m f obs hobs x z

/-- Response transport reflects extensional response equality. -/
theorem finKernel_transportResponse_reflects_response_eq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    {s t : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.FullFutureResponseSpaceEq
      (FinKernel.TransportResponse hKL s)
      (FinKernel.TransportResponse hKL t)) :
    FinKernel.FullFutureResponseSpaceEq s t := by
  intro c hc m f obs hobs x z
  have hAt := h c ((hKL c).1 hc) m f obs hobs x z
  simpa only [FinKernel.TransportResponse] using hAt

/-- Forward then reverse domain transport is extensionally the identity. -/
theorem finKernel_transportResponse_roundtrip {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    (s : FinKernel.FullFutureResponseSpace P K) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.TransportResponse (finKernel_generatedDomainEq_symm hKL)
        (FinKernel.TransportResponse hKL s))
      s := by
  intro c hc m f obs hobs x z
  rfl

/-- Reverse then forward domain transport is extensionally the identity. -/
theorem finKernel_transportResponse_roundtrip_reverse {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    (s : FinKernel.FullFutureResponseSpace P L) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.TransportResponse hKL
        (FinKernel.TransportResponse (finKernel_generatedDomainEq_symm hKL) s))
      s := by
  exact finKernel_transportResponse_roundtrip
    (P := P) (K := L) (L := K)
    (finKernel_generatedDomainEq_symm hKL) s

/-- Literal semantic signatures are unchanged by generated-domain transport. -/
theorem finKernel_transportResponse_fullFutureResponse {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    (k : FinKernel n n) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.TransportResponse hKL
        (FinKernel.FullFutureResponse P K k))
      (FinKernel.FullFutureResponse P L k) := by
  intro c hc m f obs hobs x z
  rfl

/--
Source substitution is natural under generated-domain transport: changing the
admissibility presentation commutes with substituting an earlier source action.
-/
theorem finKernel_transportResponse_sourceSubstitute_natural {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    (k : FinKernel n n)
    (s : FinKernel.FullFutureResponseSpace P K) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.TransportResponse hKL
        (FinKernel.SourceSubstituteResponse k s))
      (FinKernel.SourceSubstituteResponse k
        (FinKernel.TransportResponse hKL s)) := by
  intro c hc m f obs hobs x z
  rfl

/-- Source realization is preserved and reflected by generated-domain transport. -/
theorem finKernel_sourceRealizes_transport_iff {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    {s : FinKernel.FullFutureResponseSpace P K}
    (k : FinKernel n n) :
    FinKernel.SourceRealizes P K s k ↔
      FinKernel.SourceRealizes P L
        (FinKernel.TransportResponse hKL s) k := by
  constructor
  · rintro ⟨hk, hsk⟩
    refine ⟨(hKL k).1 hk, ?_⟩
    exact finKernel_fullFutureResponseSpaceEq_trans
      (finKernel_transportResponse_respects_response_eq hKL hsk)
      (finKernel_transportResponse_fullFutureResponse hKL k)
  · rintro ⟨hl, hsl⟩
    refine ⟨(hKL k).2 hl, ?_⟩
    have hSig := finKernel_transportResponse_fullFutureResponse
      (P := P) hKL k
    have hBoth : FinKernel.FullFutureResponseSpaceEq
        (FinKernel.TransportResponse hKL s)
        (FinKernel.TransportResponse hKL
          (FinKernel.FullFutureResponse P K k)) :=
      finKernel_fullFutureResponseSpaceEq_trans hsl
        (finKernel_fullFutureResponseSpaceEq_symm hSig)
    exact finKernel_transportResponse_reflects_response_eq hKL hBoth

/-- Reachability is exactly existence of a generated source realization. -/
theorem finKernel_reachableResidualState_iff_exists_sourceRealizes {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s : FinKernel.FullFutureResponseSpace P K} :
    FinKernel.ReachableResidualState P K s ↔
      ∃ k : FinKernel n n, FinKernel.SourceRealizes P K s k := by
  constructor
  · exact finKernel_reachableResidualState_has_sourceRealization
  · rintro ⟨k, hk, hsk⟩
    refine ⟨k, hk, ?_⟩
    exact finKernel_fullFutureResponseSpaceEq_trans hsk
      (finKernel_fullFutureResponseSpaceEq_symm
        (finKernel_identityResidualState_eq_fullFutureResponse
          (P := P) hk))

/-- Reachable residual-state membership transports across equal generated domains. -/
theorem finKernel_reachableResidualState_transport_iff {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    {s : FinKernel.FullFutureResponseSpace P K} :
    FinKernel.ReachableResidualState P K s ↔
      FinKernel.ReachableResidualState P L
        (FinKernel.TransportResponse hKL s) := by
  rw [finKernel_reachableResidualState_iff_exists_sourceRealizes,
    finKernel_reachableResidualState_iff_exists_sourceRealizes]
  constructor
  · rintro ⟨k, hk⟩
    exact ⟨k, (finKernel_sourceRealizes_transport_iff hKL k).1 hk⟩
  · rintro ⟨k, hk⟩
    exact ⟨k, (finKernel_sourceRealizes_transport_iff hKL k).2 hk⟩

/--
The complete source-substitution successor relation is preserved and reflected
across extensionally equal generated context domains.  This is the main
Level-B transport theorem; no reachability premise is needed because source
realizations themselves transport exactly.
-/
theorem finKernel_sourceSubstitutionSuccessorRel_transport_iff {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L)
    {s t u : FinKernel.FullFutureResponseSpace P K} :
    FinKernel.SourceSubstitutionSuccessorRel P K s t u ↔
      FinKernel.SourceSubstitutionSuccessorRel P L
        (FinKernel.TransportResponse hKL s)
        (FinKernel.TransportResponse hKL t)
        (FinKernel.TransportResponse hKL u) := by
  constructor
  · intro hSource k hkL
    have hkK := (finKernel_sourceRealizes_transport_iff hKL k).2 hkL
    have hOutK := hSource k hkK
    have hTransport :=
      finKernel_transportResponse_respects_response_eq hKL hOutK
    exact finKernel_fullFutureResponseSpaceEq_trans hTransport
      (finKernel_transportResponse_sourceSubstitute_natural hKL k t)
  · intro hSource k hkK
    have hkL := (finKernel_sourceRealizes_transport_iff hKL k).1 hkK
    have hOutL := hSource k hkL
    have hNatural :=
      finKernel_transportResponse_sourceSubstitute_natural hKL k t
    have hBoth : FinKernel.FullFutureResponseSpaceEq
        (FinKernel.TransportResponse hKL u)
        (FinKernel.TransportResponse hKL
          (FinKernel.SourceSubstituteResponse k t)) :=
      finKernel_fullFutureResponseSpaceEq_trans hOutL
        (finKernel_fullFutureResponseSpaceEq_symm hNatural)
    exact finKernel_transportResponse_reflects_response_eq hKL hBoth

/--
The historical #2776 generator-list gauge pair has exactly the same generated
admissibility domain.
-/
theorem finKernel_merge01_collapse_generator_generatedDomainEq :
    FinKernel.GeneratedDomainEq
      FinKernel.merge01CollapseOnlyContextFamily3
      FinKernel.merge01CollapseIdentityContextFamily3 := by
  intro c
  exact finKernel_merge01_generated_context_policy_iff c

/--
Concrete positive witness: the #2829 source-substitution dynamics transports
exactly between two literally different generator families with the same
sequential closure.
-/
theorem finKernel_merge01_generator_gauge_preserves_sourceSubstitution
    {s t u : FinKernel.FullFutureResponseSpace
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01CollapseOnlyContextFamily3} :
    FinKernel.SourceSubstitutionSuccessorRel
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01CollapseOnlyContextFamily3 s t u ↔
      FinKernel.SourceSubstitutionSuccessorRel
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01CollapseIdentityContextFamily3
        (FinKernel.TransportResponse
          finKernel_merge01_collapse_generator_generatedDomainEq s)
        (FinKernel.TransportResponse
          finKernel_merge01_collapse_generator_generatedDomainEq t)
        (FinKernel.TransportResponse
          finKernel_merge01_collapse_generator_generatedDomainEq u) := by
  exact finKernel_sourceSubstitutionSuccessorRel_transport_iff
    finKernel_merge01_collapse_generator_generatedDomainEq

/--
The safe and expanded context families do not have the same generated domain:
the expanded family's distinguishing move would contradict the already-earned
safe generated-context congruence if it belonged to the safe closure.
-/
theorem finKernel_merge01_safe_expanded_not_generatedDomainEq :
    ¬ FinKernel.GeneratedDomainEq
      FinKernel.merge01SafeContextFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  intro hEq
  have hMoveSafe : FinKernel.GeneratedContext
      FinKernel.merge01SafeContextFamily3 finKernelMoveOneToTwo :=
    (hEq finKernelMoveOneToTwo).2
      finKernel_merge01_move_generated_by_expanded_policy
  have hAfter :=
    finKernel_merge01_contextActionEq_stable_under_safe_generated
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_identity_action_eq
      finKernelMoveOneToTwo hMoveSafe
  exact finKernel_merge01_collapse_identity_break_after_move hAfter

/-- Acceptance bundle for the #2838 first transaction. -/
theorem finKernel_context_domain_transport_bundle :
    FinKernel.merge01CollapseOnlyContextFamily3 ≠
      FinKernel.merge01CollapseIdentityContextFamily3 ∧
    FinKernel.GeneratedDomainEq
      FinKernel.merge01CollapseOnlyContextFamily3
      FinKernel.merge01CollapseIdentityContextFamily3 ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n}
      (hKL : FinKernel.GeneratedDomainEq K L)
      {s t u : FinKernel.FullFutureResponseSpace P K},
      FinKernel.SourceSubstitutionSuccessorRel P K s t u ↔
        FinKernel.SourceSubstitutionSuccessorRel P L
          (FinKernel.TransportResponse hKL s)
          (FinKernel.TransportResponse hKL t)
          (FinKernel.TransportResponse hKL u)) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n}
      (hKL : FinKernel.GeneratedDomainEq K L)
      {s : FinKernel.FullFutureResponseSpace P K},
      FinKernel.ReachableResidualState P K s ↔
        FinKernel.ReachableResidualState P L
          (FinKernel.TransportResponse hKL s)) ∧
    ¬ FinKernel.GeneratedDomainEq
      FinKernel.merge01SafeContextFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  exact ⟨finKernel_merge01_context_policy_families_differ,
    finKernel_merge01_collapse_generator_generatedDomainEq,
    (by
      intro n P K L hKL s t u
      exact finKernel_sourceSubstitutionSuccessorRel_transport_iff hKL),
    (by
      intro n P K L hKL s
      exact finKernel_reachableResidualState_transport_iff hKL),
    finKernel_merge01_safe_expanded_not_generatedDomainEq⟩

end RelayTheory
