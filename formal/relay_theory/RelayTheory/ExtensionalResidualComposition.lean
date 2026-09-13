import RelayTheory.ReachableResidualOrbit

namespace RelayTheory

/-- Full-future response-space equality is reflexive. -/
theorem finKernel_fullFutureResponseSpaceEq_refl {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    (s : FinKernel.FullFutureResponseSpace P K) :
    FinKernel.FullFutureResponseSpaceEq s s := by
  intro c hc m f obs hobs x z
  rfl

/-- Full-future response-space equality is symmetric. -/
theorem finKernel_fullFutureResponseSpaceEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.FullFutureResponseSpaceEq s t) :
    FinKernel.FullFutureResponseSpaceEq t s := by
  intro c hc m f obs hobs x z
  exact (h c hc m f obs hobs x z).symm

/-- Full-future response-space equality is transitive. -/
theorem finKernel_fullFutureResponseSpaceEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (hst : FinKernel.FullFutureResponseSpaceEq s t)
    (htu : FinKernel.FullFutureResponseSpaceEq t u) :
    FinKernel.FullFutureResponseSpaceEq s u := by
  intro c hc m f obs hobs x z
  exact Eq.trans (hst c hc m f obs hobs x z)
    (htu c hc m f obs hobs x z)

namespace FinKernel

/--
Extensional sequential composition on reachable residual response states.
`s` is represented by an earlier generated action `k`, `t` by a later action
`l`, and `u` by the composite `l ∘ k`.  Representatives are existential and
never canonically selected.
-/
def ResidualComposeRel {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (s t u : FullFutureResponseSpace P K) : Prop :=
  ∃ k : FinKernel n n,
    ∃ hk : GeneratedContext K k,
      ∃ l : FinKernel n n,
        ∃ hl : GeneratedContext K l,
          FullFutureResponseSpaceEq s (IdentityResidualState P K k hk) ∧
          FullFutureResponseSpaceEq t (IdentityResidualState P K l hl) ∧
          FullFutureResponseSpaceEq u
            (IdentityResidualState P K (compose l k)
              (finKernel_generatedContext_compose hk hl))

/-- The residual state corresponding to the generated identity action. -/
def ResidualIdentityState {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n) :
    FullFutureResponseSpace P K :=
  IdentityResidualState P K (identity n) GeneratedContext.identity

end FinKernel

/-- Every state appearing in the composition relation is reachable. -/
theorem finKernel_residualComposeRel_implies_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.ResidualComposeRel P K s t u) :
    FinKernel.ReachableResidualState P K s ∧
    FinKernel.ReachableResidualState P K t ∧
    FinKernel.ReachableResidualState P K u := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hu⟩
  exact ⟨⟨k, hk, hs⟩,
    ⟨l, hl, ht⟩,
    ⟨FinKernel.compose l k,
      finKernel_generatedContext_compose hk hl,
      hu⟩⟩

/-- Any pair of reachable residual states has an extensional composite witness. -/
theorem finKernel_reachable_residuals_have_composite {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t : FinKernel.FullFutureResponseSpace P K}
    (hs : FinKernel.ReachableResidualState P K s)
    (ht : FinKernel.ReachableResidualState P K t) :
    ∃ u : FinKernel.FullFutureResponseSpace P K,
      FinKernel.ResidualComposeRel P K s t u ∧
      FinKernel.ReachableResidualState P K u := by
  rcases hs with ⟨k, hk, hsk⟩
  rcases ht with ⟨l, hl, htl⟩
  let hcomp : FinKernel.GeneratedContext K (FinKernel.compose l k) :=
    finKernel_generatedContext_compose hk hl
  let u := FinKernel.IdentityResidualState P K (FinKernel.compose l k) hcomp
  refine ⟨u, ?_, ?_⟩
  · refine ⟨k, hk, l, hl, hsk, htl, ?_⟩
    exact finKernel_fullFutureResponseSpaceEq_refl u
  · exact ⟨FinKernel.compose l k, hcomp,
      finKernel_fullFutureResponseSpaceEq_refl u⟩

/--
Main Level-B result: once the two input residual states are fixed, any two
literal generated representative choices produce extensionally equal outputs.
-/
theorem finKernel_residualComposeRel_functional_up_to_response_eq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u u' : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.ResidualComposeRel P K s t u)
    (h' : FinKernel.ResidualComposeRel P K s t u') :
    FinKernel.FullFutureResponseSpaceEq u u' := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hu⟩
  rcases h' with ⟨k', hk', l', hl', hs', ht', hu'⟩
  have hkkResidual : FinKernel.IdentityResidualStateEq P K k k' hk hk' :=
    finKernel_fullFutureResponseSpaceEq_trans
      (finKernel_fullFutureResponseSpaceEq_symm hs) hs'
  have hllResidual : FinKernel.IdentityResidualStateEq P K l l' hl hl' :=
    finKernel_fullFutureResponseSpaceEq_trans
      (finKernel_fullFutureResponseSpaceEq_symm ht) ht'
  have hkk : FinKernel.ContextualActionEq P K k k' :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq hk hk').1
      hkkResidual
  have hll : FinKernel.ContextualActionEq P K l l' :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq hl hl').1
      hllResidual
  have hcomp : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k) (FinKernel.compose l' k') :=
    finKernel_contextualActionEq_compose_respects_representatives hkk hll hl
  have hcompResidual : FinKernel.IdentityResidualStateEq P K
      (FinKernel.compose l k) (FinKernel.compose l' k')
      (finKernel_generatedContext_compose hk hl)
      (finKernel_generatedContext_compose hk' hl') :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq
      (finKernel_generatedContext_compose hk hl)
      (finKernel_generatedContext_compose hk' hl')).2 hcomp
  exact finKernel_fullFutureResponseSpaceEq_trans hu
    (finKernel_fullFutureResponseSpaceEq_trans hcompResidual
      (finKernel_fullFutureResponseSpaceEq_symm hu'))

/-- A later identity action is a right unit for the extensional relation. -/
theorem finKernel_residualComposeRel_identity_later {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s u : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.ResidualComposeRel P K s
      (FinKernel.ResidualIdentityState P K) u) :
    FinKernel.FullFutureResponseSpaceEq u s := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hu⟩
  have hllResidual : FinKernel.IdentityResidualStateEq P K l
      (FinKernel.identity n) hl FinKernel.GeneratedContext.identity :=
    finKernel_fullFutureResponseSpaceEq_symm ht
  have hll : FinKernel.ContextualActionEq P K l (FinKernel.identity n) :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq
      hl FinKernel.GeneratedContext.identity).1 hllResidual
  have hcompId : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k)
      (FinKernel.compose (FinKernel.identity n) k) :=
    finKernel_contextualActionEq_compose_respects_representatives
      (finKernel_contextualActionEq_refl P K k) hll hl
  have hcompK : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k) k := by
    simpa only [finKernel_compose_identity_after] using hcompId
  have hres : FinKernel.IdentityResidualStateEq P K
      (FinKernel.compose l k) k
      (finKernel_generatedContext_compose hk hl) hk :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq
      (finKernel_generatedContext_compose hk hl) hk).2 hcompK
  exact finKernel_fullFutureResponseSpaceEq_trans hu
    (finKernel_fullFutureResponseSpaceEq_trans hres
      (finKernel_fullFutureResponseSpaceEq_symm hs))

/-- An earlier identity action is a left unit for the extensional relation. -/
theorem finKernel_residualComposeRel_identity_earlier {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s u : FinKernel.FullFutureResponseSpace P K}
    (h : FinKernel.ResidualComposeRel P K
      (FinKernel.ResidualIdentityState P K) s u) :
    FinKernel.FullFutureResponseSpaceEq u s := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hu⟩
  have hkkResidual : FinKernel.IdentityResidualStateEq P K k
      (FinKernel.identity n) hk FinKernel.GeneratedContext.identity :=
    finKernel_fullFutureResponseSpaceEq_symm hs
  have hkk : FinKernel.ContextualActionEq P K k (FinKernel.identity n) :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq
      hk FinKernel.GeneratedContext.identity).1 hkkResidual
  have hcompId : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k)
      (FinKernel.compose l (FinKernel.identity n)) :=
    finKernel_contextualActionEq_compose_respects_representatives
      hkk (finKernel_contextualActionEq_refl P K l) hl
  have hcompL : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k) l := by
    simpa only [finKernel_compose_identity_before] using hcompId
  have hres : FinKernel.IdentityResidualStateEq P K
      (FinKernel.compose l k) l
      (finKernel_generatedContext_compose hk hl) hl :=
    (finKernel_identityResidualStateEq_iff_contextualActionEq
      (finKernel_generatedContext_compose hk hl) hl).2 hcompL
  exact finKernel_fullFutureResponseSpaceEq_trans hu
    (finKernel_fullFutureResponseSpaceEq_trans hres
      (finKernel_fullFutureResponseSpaceEq_symm ht))

/--
Canonical associativity bridge: the two literal bracketings of three generated
continuations yield the same residual response state.  This earns associativity
at the representative bridge without selecting quotient representatives.
-/
theorem finKernel_identityResidualStateEq_associative {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l d : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l)
    (hd : FinKernel.GeneratedContext K d) :
    FinKernel.IdentityResidualStateEq P K
      (FinKernel.compose d (FinKernel.compose l k))
      (FinKernel.compose (FinKernel.compose d l) k)
      (finKernel_generatedContext_compose
        (finKernel_generatedContext_compose hk hl) hd)
      (finKernel_generatedContext_compose hk
        (finKernel_generatedContext_compose hl hd)) := by
  apply (finKernel_identityResidualStateEq_iff_contextualActionEq
    (finKernel_generatedContext_compose
      (finKernel_generatedContext_compose hk hl) hd)
    (finKernel_generatedContext_compose hk
      (finKernel_generatedContext_compose hl hd))).2
  simpa only [finKernel_compose_associative] using
    (finKernel_contextualActionEq_refl P K
      (FinKernel.compose d (FinKernel.compose l k)))

/--
Safe-frame anti-cheat: substituting literal hidden-collapse representatives by
identity representatives on both inputs does not change the residual composite.
-/
theorem finKernel_merge01_safe_residual_composite_representative_gauge :
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
          FinKernel.GeneratedContext.identity)) := by
  let s := FinKernel.IdentityResidualState
    FinKernel.merge01ProbeFamily3
    FinKernel.merge01SafeContextFamily3
    (FinKernel.dirac finCollapseHidden3)
    finKernel_merge01_collapse_generated_safe
  let uCollapse := FinKernel.IdentityResidualState
    FinKernel.merge01ProbeFamily3
    FinKernel.merge01SafeContextFamily3
    (FinKernel.compose
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.dirac finCollapseHidden3))
    (finKernel_generatedContext_compose
      finKernel_merge01_collapse_generated_safe
      finKernel_merge01_collapse_generated_safe)
  let uIdentity := FinKernel.IdentityResidualState
    FinKernel.merge01ProbeFamily3
    FinKernel.merge01SafeContextFamily3
    (FinKernel.compose (FinKernel.identity 3) (FinKernel.identity 3))
    (finKernel_generatedContext_compose
      FinKernel.GeneratedContext.identity
      FinKernel.GeneratedContext.identity)
  have hCollapse : FinKernel.ResidualComposeRel
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3 s s uCollapse := by
    refine ⟨FinKernel.dirac finCollapseHidden3,
      finKernel_merge01_collapse_generated_safe,
      FinKernel.dirac finCollapseHidden3,
      finKernel_merge01_collapse_generated_safe, ?_, ?_, ?_⟩
    · exact finKernel_fullFutureResponseSpaceEq_refl s
    · exact finKernel_fullFutureResponseSpaceEq_refl s
    · exact finKernel_fullFutureResponseSpaceEq_refl uCollapse
  have hIdentity : FinKernel.ResidualComposeRel
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3 s s uIdentity := by
    refine ⟨FinKernel.identity 3, FinKernel.GeneratedContext.identity,
      FinKernel.identity 3, FinKernel.GeneratedContext.identity,
      ?_, ?_, ?_⟩
    · exact finKernel_merge01_safe_identityResidualStateEq
    · exact finKernel_merge01_safe_identityResidualStateEq
    · exact finKernel_fullFutureResponseSpaceEq_refl uIdentity
  exact finKernel_residualComposeRel_functional_up_to_response_eq
    hCollapse hIdentity

/-- Expanded continuation access still distinguishes collapse from identity. -/
theorem finKernel_merge01_expanded_residual_distinction_survives :
    ¬ FinKernel.IdentityResidualStateEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_expanded
      FinKernel.GeneratedContext.identity :=
  finKernel_merge01_expanded_not_identityResidualStateEq

/-- Acceptance bundle for #2810. -/
theorem finKernel_extensional_residual_composition_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K : FinKernel.FutureContextFamily n}
      {s t u u' : FinKernel.FullFutureResponseSpace P K},
      FinKernel.ResidualComposeRel P K s t u →
      FinKernel.ResidualComposeRel P K s t u' →
      FinKernel.FullFutureResponseSpaceEq u u') ∧
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
    fun h h' => finKernel_residualComposeRel_functional_up_to_response_eq h h',
    finKernel_merge01_safe_residual_composite_representative_gauge,
    finKernel_merge01_expanded_residual_distinction_survives⟩

end RelayTheory
