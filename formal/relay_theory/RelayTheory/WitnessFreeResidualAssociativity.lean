import RelayTheory.ExtensionalResidualComposition

namespace RelayTheory

/--
The extensional laws carried by `ResidualComposeRel` at the residual-state
boundary.  This is a theory-local interface bundle, not an ontology claim and
not a Mathlib algebra instance.
-/
structure FinKernel.ResidualComposeRelLaws {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) where
  total : ∀ {s t : FinKernel.FullFutureResponseSpace P K},
    FinKernel.ReachableResidualState P K s →
    FinKernel.ReachableResidualState P K t →
    ∃ u : FinKernel.FullFutureResponseSpace P K,
      FinKernel.ResidualComposeRel P K s t u ∧
      FinKernel.ReachableResidualState P K u
  functional : ∀ {s t u u' : FinKernel.FullFutureResponseSpace P K},
    FinKernel.ResidualComposeRel P K s t u →
    FinKernel.ResidualComposeRel P K s t u' →
    FinKernel.FullFutureResponseSpaceEq u u'
  identity_later : ∀ {s u : FinKernel.FullFutureResponseSpace P K},
    FinKernel.ResidualComposeRel P K s
      (FinKernel.ResidualIdentityState P K) u →
    FinKernel.FullFutureResponseSpaceEq u s
  identity_earlier : ∀ {s u : FinKernel.FullFutureResponseSpace P K},
    FinKernel.ResidualComposeRel P K
      (FinKernel.ResidualIdentityState P K) s u →
    FinKernel.FullFutureResponseSpaceEq u s
  associative : ∀ {a b c ab bc out₁ out₂ :
      FinKernel.FullFutureResponseSpace P K},
    FinKernel.ResidualComposeRel P K a b ab →
    FinKernel.ResidualComposeRel P K ab c out₁ →
    FinKernel.ResidualComposeRel P K b c bc →
    FinKernel.ResidualComposeRel P K a bc out₂ →
    FinKernel.FullFutureResponseSpaceEq out₁ out₂

/--
Level-B result for #2813: `ResidualComposeRel` is associative entirely at the
external residual-state relation.  The theorem statement exposes no generated
kernel representatives or intermediate proof witnesses.
-/
theorem finKernel_residualComposeRel_associative_up_to_response_eq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {a b c ab bc out₁ out₂ : FinKernel.FullFutureResponseSpace P K}
    (hAB : FinKernel.ResidualComposeRel P K a b ab)
    (hLeft : FinKernel.ResidualComposeRel P K ab c out₁)
    (hBC : FinKernel.ResidualComposeRel P K b c bc)
    (hRight : FinKernel.ResidualComposeRel P K a bc out₂) :
    FinKernel.FullFutureResponseSpaceEq out₁ out₂ := by
  have hBCOriginal := hBC
  rcases hAB with ⟨k, hk, l, hl, ha, hb, hab⟩
  rcases hBC with ⟨l₂, hl₂, d, hd, hb₂, hc, hbc⟩

  let bcCanonical := FinKernel.IdentityResidualState P K
    (FinKernel.compose d l)
    (finKernel_generatedContext_compose hl hd)
  have hBCCanonical : FinKernel.ResidualComposeRel P K b c bcCanonical := by
    refine ⟨l, hl, d, hd, hb, hc, ?_⟩
    exact finKernel_fullFutureResponseSpaceEq_refl bcCanonical
  have hbcCanonical : FinKernel.FullFutureResponseSpaceEq bc bcCanonical :=
    finKernel_residualComposeRel_functional_up_to_response_eq
      hBCOriginal hBCCanonical

  let leftCanonical := FinKernel.IdentityResidualState P K
    (FinKernel.compose d (FinKernel.compose l k))
    (finKernel_generatedContext_compose
      (finKernel_generatedContext_compose hk hl) hd)
  have hLeftCanonical :
      FinKernel.ResidualComposeRel P K ab c leftCanonical := by
    refine ⟨FinKernel.compose l k,
      finKernel_generatedContext_compose hk hl,
      d, hd, hab, hc, ?_⟩
    exact finKernel_fullFutureResponseSpaceEq_refl leftCanonical
  have houtLeft : FinKernel.FullFutureResponseSpaceEq out₁ leftCanonical :=
    finKernel_residualComposeRel_functional_up_to_response_eq
      hLeft hLeftCanonical

  let rightCanonical := FinKernel.IdentityResidualState P K
    (FinKernel.compose (FinKernel.compose d l) k)
    (finKernel_generatedContext_compose hk
      (finKernel_generatedContext_compose hl hd))
  have hRightCanonical :
      FinKernel.ResidualComposeRel P K a bc rightCanonical := by
    refine ⟨k, hk,
      FinKernel.compose d l,
      finKernel_generatedContext_compose hl hd,
      ha, hbcCanonical, ?_⟩
    exact finKernel_fullFutureResponseSpaceEq_refl rightCanonical
  have houtRight : FinKernel.FullFutureResponseSpaceEq out₂ rightCanonical :=
    finKernel_residualComposeRel_functional_up_to_response_eq
      hRight hRightCanonical

  have hAssoc : FinKernel.FullFutureResponseSpaceEq
      leftCanonical rightCanonical := by
    simpa only [leftCanonical, rightCanonical] using
      (finKernel_identityResidualStateEq_associative
        (P := P) (K := K) hk hl hd)

  exact finKernel_fullFutureResponseSpaceEq_trans houtLeft
    (finKernel_fullFutureResponseSpaceEq_trans hAssoc
      (finKernel_fullFutureResponseSpaceEq_symm houtRight))

/--
All currently earned sequential laws packaged at the witness-free relation
boundary.  No representative-selection operation is introduced.
-/
theorem finKernel_residualComposeRel_laws {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.ResidualComposeRelLaws P K := by
  refine {
    total := ?_,
    functional := ?_,
    identity_later := ?_,
    identity_earlier := ?_,
    associative := ?_
  }
  · intro s t hs ht
    exact finKernel_reachable_residuals_have_composite hs ht
  · intro s t u u' h h'
    exact finKernel_residualComposeRel_functional_up_to_response_eq h h'
  · intro s u h
    exact finKernel_residualComposeRel_identity_later h
  · intro s u h
    exact finKernel_residualComposeRel_identity_earlier h
  · intro a b c ab bc out₁ out₂ hAB hLeft hBC hRight
    exact finKernel_residualComposeRel_associative_up_to_response_eq
      hAB hLeft hBC hRight

/--
The witness-free law strengthening preserves the existing safe/expanded
anti-cheat boundary: safe representative substitution remains invisible, while
expanded continuation access still splits collapse from identity.
-/
theorem finKernel_witness_free_residual_associativity_preserves_merge01_boundary :
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
      finKernel_merge01_collapse_generated_expanded
      FinKernel.GeneratedContext.identity := by
  exact ⟨
    finKernel_merge01_safe_residual_composite_representative_gauge,
    finKernel_merge01_expanded_residual_distinction_survives⟩

end RelayTheory
