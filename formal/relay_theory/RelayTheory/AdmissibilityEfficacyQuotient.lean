import RelayTheory.AdmissibilityDomainIdentifiability

namespace RelayTheory

namespace FinKernel

/--
Two admissibility frames are operationally efficacy-equivalent when their
reachable complete-response/source-substitution dynamics are explicitly
equivalent.  This relation does not assume generated-domain equality.
-/
def AccessEfficacyEq {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  Nonempty (ReachableResponseDynamicsEquiv P K L)

end FinKernel

/-- Identity dynamics equivalence. -/
def finKernel_reachableResponseDynamicsEquiv_refl {n : Nat}
    (P : FinKernel.ProbeFamily n) (K : FinKernel.FutureContextFamily n) :
    FinKernel.ReachableResponseDynamicsEquiv P K K := by
  refine {
    forward := fun s => s
    backward := fun s => s
    forward_reachable := ?_
    backward_reachable := ?_
    roundtrip_K := ?_
    roundtrip_L := ?_
    forward_eq := ?_
    forward_reflects_eq := ?_
    backward_eq := ?_
    backward_reflects_eq := ?_
    root_forward := ?_
    root_backward := ?_
    successor_forward := ?_
    successor_backward := ?_
  }
  · intro s hs
    exact hs
  · intro s hs
    exact hs
  · intro s hs
    exact finKernel_fullFutureResponseSpaceEq_refl s
  · intro s hs
    exact finKernel_fullFutureResponseSpaceEq_refl s
  · intro s t hs ht hst
    exact hst
  · intro s t hs ht hst
    exact hst
  · intro s t hs ht hst
    exact hst
  · intro s t hs ht hst
    exact hst
  · exact finKernel_fullFutureResponseSpaceEq_refl _
  · exact finKernel_fullFutureResponseSpaceEq_refl _
  · intro s t u hs ht hu hrel
    exact hrel
  · intro s t u hs ht hu hrel
    exact hrel

/-- Reverse an explicit reachable-dynamics equivalence. -/
def finKernel_reachableResponseDynamicsEquiv_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (e : FinKernel.ReachableResponseDynamicsEquiv P K L) :
    FinKernel.ReachableResponseDynamicsEquiv P L K := by
  exact {
    forward := e.backward
    backward := e.forward
    forward_reachable := e.backward_reachable
    backward_reachable := e.forward_reachable
    roundtrip_K := e.roundtrip_L
    roundtrip_L := e.roundtrip_K
    forward_eq := e.backward_eq
    forward_reflects_eq := e.backward_reflects_eq
    backward_eq := e.forward_eq
    backward_reflects_eq := e.forward_reflects_eq
    root_forward := e.root_backward
    root_backward := e.root_forward
    successor_forward := e.successor_backward
    successor_backward := e.successor_forward
  }

/-- Compose explicit reachable-dynamics equivalences. -/
def finKernel_reachableResponseDynamicsEquiv_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (eKL : FinKernel.ReachableResponseDynamicsEquiv P K L)
    (eLM : FinKernel.ReachableResponseDynamicsEquiv P L M) :
    FinKernel.ReachableResponseDynamicsEquiv P K M := by
  refine {
    forward := fun s => eLM.forward (eKL.forward s)
    backward := fun s => eKL.backward (eLM.backward s)
    forward_reachable := ?_
    backward_reachable := ?_
    roundtrip_K := ?_
    roundtrip_L := ?_
    forward_eq := ?_
    forward_reflects_eq := ?_
    backward_eq := ?_
    backward_reflects_eq := ?_
    root_forward := ?_
    root_backward := ?_
    successor_forward := ?_
    successor_backward := ?_
  }
  · intro s hs
    exact eLM.forward_reachable (eKL.forward_reachable hs)
  · intro s hs
    exact eKL.backward_reachable (eLM.backward_reachable hs)
  · intro s hs
    have hsL := eKL.forward_reachable hs
    have hsM := eLM.forward_reachable hsL
    have hMiddle := eLM.roundtrip_K hsL
    have hBack := eKL.backward_eq
      (eLM.backward_reachable hsM) hsL hMiddle
    exact finKernel_fullFutureResponseSpaceEq_trans hBack
      (eKL.roundtrip_K hs)
  · intro s hs
    have hsL := eLM.backward_reachable hs
    have hsK := eKL.backward_reachable hsL
    have hMiddle := eKL.roundtrip_L hsL
    have hForward := eLM.forward_eq
      (eKL.forward_reachable hsK) hsL hMiddle
    exact finKernel_fullFutureResponseSpaceEq_trans hForward
      (eLM.roundtrip_L hs)
  · intro s t hs ht hst
    exact eLM.forward_eq
      (eKL.forward_reachable hs)
      (eKL.forward_reachable ht)
      (eKL.forward_eq hs ht hst)
  · intro s t hs ht hst
    exact eKL.forward_reflects_eq hs ht
      (eLM.forward_reflects_eq
        (eKL.forward_reachable hs)
        (eKL.forward_reachable ht) hst)
  · intro s t hs ht hst
    exact eKL.backward_eq
      (eLM.backward_reachable hs)
      (eLM.backward_reachable ht)
      (eLM.backward_eq hs ht hst)
  · intro s t hs ht hst
    exact eLM.backward_reflects_eq hs ht
      (eKL.backward_reflects_eq
        (eLM.backward_reachable hs)
        (eLM.backward_reachable ht) hst)
  · have hRootK : FinKernel.ReachableResidualState P K
        (FinKernel.ResidualIdentityState P K) :=
      finKernel_residualIdentityState_reachable
    have hRootL : FinKernel.ReachableResidualState P L
        (FinKernel.ResidualIdentityState P L) :=
      finKernel_residualIdentityState_reachable
    have hMapped := eLM.forward_eq
      (eKL.forward_reachable hRootK) hRootL eKL.root_forward
    exact finKernel_fullFutureResponseSpaceEq_trans hMapped eLM.root_forward
  · have hRootM : FinKernel.ReachableResidualState P M
        (FinKernel.ResidualIdentityState P M) :=
      finKernel_residualIdentityState_reachable
    have hRootL : FinKernel.ReachableResidualState P L
        (FinKernel.ResidualIdentityState P L) :=
      finKernel_residualIdentityState_reachable
    have hMapped := eKL.backward_eq
      (eLM.backward_reachable hRootM) hRootL eLM.root_backward
    exact finKernel_fullFutureResponseSpaceEq_trans hMapped eKL.root_backward
  · intro s t u hs ht hu hrel
    exact eLM.successor_forward
      (eKL.forward_reachable hs)
      (eKL.forward_reachable ht)
      (eKL.forward_reachable hu)
      (eKL.successor_forward hs ht hu hrel)
  · intro s t u hs ht hu hrel
    exact eKL.successor_backward
      (eLM.backward_reachable hs)
      (eLM.backward_reachable ht)
      (eLM.backward_reachable hu)
      (eLM.successor_backward hs ht hu hrel)

/-- Operational access efficacy equivalence is reflexive. -/
theorem finKernel_accessEfficacyEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n) (K : FinKernel.FutureContextFamily n) :
    FinKernel.AccessEfficacyEq P K K := by
  exact ⟨finKernel_reachableResponseDynamicsEquiv_refl P K⟩

/-- Operational access efficacy equivalence is symmetric. -/
theorem finKernel_accessEfficacyEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.AccessEfficacyEq P K L) :
    FinKernel.AccessEfficacyEq P L K := by
  rcases h with ⟨e⟩
  exact ⟨finKernel_reachableResponseDynamicsEquiv_symm e⟩

/-- Operational access efficacy equivalence is transitive. -/
theorem finKernel_accessEfficacyEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.AccessEfficacyEq P K L)
    (hLM : FinKernel.AccessEfficacyEq P L M) :
    FinKernel.AccessEfficacyEq P K M := by
  rcases hKL with ⟨eKL⟩
  rcases hLM with ⟨eLM⟩
  exact ⟨finKernel_reachableResponseDynamicsEquiv_trans eKL eLM⟩

/-- Generated-domain transport preserves the distinguished residual root. -/
theorem finKernel_transportResponse_residualIdentityState {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L) :
    FinKernel.FullFutureResponseSpaceEq
      (FinKernel.TransportResponse hKL
        (FinKernel.ResidualIdentityState P K))
      (FinKernel.ResidualIdentityState P L) := by
  have hRootK : FinKernel.FullFutureResponseSpaceEq
      (FinKernel.ResidualIdentityState P K)
      (FinKernel.FullFutureResponse P K (FinKernel.identity n)) := by
    change FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState P K (FinKernel.identity n)
        FinKernel.GeneratedContext.identity)
      (FinKernel.FullFutureResponse P K (FinKernel.identity n))
    exact finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) FinKernel.GeneratedContext.identity
  have hTransportRoot :=
    finKernel_transportResponse_respects_response_eq hKL hRootK
  have hSignature := finKernel_transportResponse_fullFutureResponse
    (P := P) hKL (FinKernel.identity n)
  have hRootL : FinKernel.FullFutureResponseSpaceEq
      (FinKernel.ResidualIdentityState P L)
      (FinKernel.FullFutureResponse P L (FinKernel.identity n)) := by
    change FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState P L (FinKernel.identity n)
        FinKernel.GeneratedContext.identity)
      (FinKernel.FullFutureResponse P L (FinKernel.identity n))
    exact finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) FinKernel.GeneratedContext.identity
  exact finKernel_fullFutureResponseSpaceEq_trans hTransportRoot
    (finKernel_fullFutureResponseSpaceEq_trans hSignature
      (finKernel_fullFutureResponseSpaceEq_symm hRootL))

/--
Equal generated admissibility domains induce an explicit reachable-dynamics
equivalence through the already-earned #2838 response transport.
-/
def finKernel_reachableResponseDynamicsEquiv_of_generatedDomainEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L) :
    FinKernel.ReachableResponseDynamicsEquiv P K L := by
  let hLK := finKernel_generatedDomainEq_symm hKL
  refine {
    forward := FinKernel.TransportResponse hKL
    backward := FinKernel.TransportResponse hLK
    forward_reachable := ?_
    backward_reachable := ?_
    roundtrip_K := ?_
    roundtrip_L := ?_
    forward_eq := ?_
    forward_reflects_eq := ?_
    backward_eq := ?_
    backward_reflects_eq := ?_
    root_forward := ?_
    root_backward := ?_
    successor_forward := ?_
    successor_backward := ?_
  }
  · intro s hs
    exact (finKernel_reachableResidualState_transport_iff hKL).1 hs
  · intro s hs
    exact (finKernel_reachableResidualState_transport_iff hLK).1 hs
  · intro s hs
    exact finKernel_transportResponse_roundtrip hKL s
  · intro s hs
    exact finKernel_transportResponse_roundtrip hLK s
  · intro s t hs ht hst
    exact finKernel_transportResponse_respects_response_eq hKL hst
  · intro s t hs ht hst
    exact finKernel_transportResponse_reflects_response_eq hKL hst
  · intro s t hs ht hst
    exact finKernel_transportResponse_respects_response_eq hLK hst
  · intro s t hs ht hst
    exact finKernel_transportResponse_reflects_response_eq hLK hst
  · exact finKernel_transportResponse_residualIdentityState hKL
  · exact finKernel_transportResponse_residualIdentityState hLK
  · intro s t u hs ht hu hrel
    exact (finKernel_sourceSubstitutionSuccessorRel_transport_iff hKL).1 hrel
  · intro s t u hs ht hu hrel
    exact (finKernel_sourceSubstitutionSuccessorRel_transport_iff hLK).1 hrel

/-- Generated-domain equality is sufficient for operational access efficacy equality. -/
theorem finKernel_generatedDomainEq_implies_accessEfficacyEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L) :
    FinKernel.AccessEfficacyEq P K L := by
  exact ⟨finKernel_reachableResponseDynamicsEquiv_of_generatedDomainEq hKL⟩

/-- The #2841 empty-vs-safe pair is efficacy-equivalent despite unequal generated domains. -/
theorem finKernel_merge01_empty_safe_accessEfficacyEq :
    FinKernel.AccessEfficacyEq
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact ⟨finKernel_merge01_empty_safe_responseDynamicsEquiv⟩

/-- Generated-domain equality is strictly finer: efficacy equality does not imply it. -/
theorem finKernel_accessEfficacyEq_does_not_imply_generatedDomainEq :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.AccessEfficacyEq FinKernel.merge01ProbeFamily3 K L →
      FinKernel.GeneratedDomainEq K L) := by
  intro hConverse
  exact finKernel_merge01_empty_safe_not_generatedDomainEq
    (hConverse _ _ finKernel_merge01_empty_safe_accessEfficacyEq)

/-- Safe and expanded merge01 frames are not efficacy-equivalent. -/
theorem finKernel_merge01_safe_expanded_not_accessEfficacyEq :
    ¬ FinKernel.AccessEfficacyEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  intro hEff
  rcases hEff with ⟨e⟩
  apply finKernel_merge01_expanded_not_reachableResponseTrivial
  intro s hs
  have hSafe := finKernel_merge01_safe_reachableResponseTrivial
    (e.backward s) (e.backward_reachable hs)
  have hBackEq : FinKernel.FullFutureResponseSpaceEq
      (e.backward s)
      (e.backward (FinKernel.ResidualIdentityState
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01ExpandedContextFamily3)) :=
    finKernel_fullFutureResponseSpaceEq_trans hSafe
      (finKernel_fullFutureResponseSpaceEq_symm e.root_backward)
  exact e.backward_reflects_eq hs
    finKernel_residualIdentityState_reachable hBackEq

/-- Acceptance bundle: efficacy equivalence is a nontrivial strict quotient of generated-domain equality. -/
theorem finKernel_admissibility_efficacy_quotient_bundle :
    (∀ {n : Nat} (P : FinKernel.ProbeFamily n)
      (K : FinKernel.FutureContextFamily n),
      FinKernel.AccessEfficacyEq P K K) ∧
    (∀ {n : Nat} {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.AccessEfficacyEq P K L →
      FinKernel.AccessEfficacyEq P L K) ∧
    (∀ {n : Nat} {P : FinKernel.ProbeFamily n}
      {K L M : FinKernel.FutureContextFamily n},
      FinKernel.AccessEfficacyEq P K L →
      FinKernel.AccessEfficacyEq P L M →
      FinKernel.AccessEfficacyEq P K M) ∧
    (∀ {n : Nat} {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.GeneratedDomainEq K L →
      FinKernel.AccessEfficacyEq P K L) ∧
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.AccessEfficacyEq FinKernel.merge01ProbeFamily3 K L →
      FinKernel.GeneratedDomainEq K L) ∧
    ¬ FinKernel.AccessEfficacyEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  exact ⟨
    finKernel_accessEfficacyEq_refl,
    (by intro n P K L h; exact finKernel_accessEfficacyEq_symm h),
    (by intro n P K L M hKL hLM; exact finKernel_accessEfficacyEq_trans hKL hLM),
    (by intro n P K L hKL; exact finKernel_generatedDomainEq_implies_accessEfficacyEq hKL),
    finKernel_accessEfficacyEq_does_not_imply_generatedDomainEq,
    finKernel_merge01_safe_expanded_not_accessEfficacyEq
  ⟩

end RelayTheory
