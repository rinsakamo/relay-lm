import RelayTheory.ContextDomainTransport

namespace RelayTheory

namespace FinKernel

/-- A context family with no declared generators. Its generated closure still contains identity. -/
def emptyFutureContextFamily (n : Nat) : FutureContextFamily n :=
  fun _ => False

/--
The reachable response dynamics is extensionally trivial when every reachable
state equals the distinguished residual identity state.
-/
def ReachableResponseTrivial {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n) : Prop :=
  ∀ s : FullFutureResponseSpace P K,
    ReachableResidualState P K s →
      FullFutureResponseSpaceEq s (ResidualIdentityState P K)

/--
A non-circular equivalence interface for reachable complete-response dynamics.
The maps need not know a `GeneratedDomainEq`; they must instead preserve and
reflect reachable extensional state identity, the distinguished root, and the
intrinsic source-substitution successor relation.
-/
structure ReachableResponseDynamicsEquiv {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  forward : FullFutureResponseSpace P K → FullFutureResponseSpace P L
  backward : FullFutureResponseSpace P L → FullFutureResponseSpace P K
  forward_reachable : ∀ {s}, ReachableResidualState P K s →
    ReachableResidualState P L (forward s)
  backward_reachable : ∀ {s}, ReachableResidualState P L s →
    ReachableResidualState P K (backward s)
  roundtrip_K : ∀ {s}, ReachableResidualState P K s →
    FullFutureResponseSpaceEq (backward (forward s)) s
  roundtrip_L : ∀ {s}, ReachableResidualState P L s →
    FullFutureResponseSpaceEq (forward (backward s)) s
  forward_eq : ∀ {s t}, ReachableResidualState P K s →
    ReachableResidualState P K t →
    FullFutureResponseSpaceEq s t →
    FullFutureResponseSpaceEq (forward s) (forward t)
  forward_reflects_eq : ∀ {s t}, ReachableResidualState P K s →
    ReachableResidualState P K t →
    FullFutureResponseSpaceEq (forward s) (forward t) →
    FullFutureResponseSpaceEq s t
  backward_eq : ∀ {s t}, ReachableResidualState P L s →
    ReachableResidualState P L t →
    FullFutureResponseSpaceEq s t →
    FullFutureResponseSpaceEq (backward s) (backward t)
  backward_reflects_eq : ∀ {s t}, ReachableResidualState P L s →
    ReachableResidualState P L t →
    FullFutureResponseSpaceEq (backward s) (backward t) →
    FullFutureResponseSpaceEq s t
  root_forward : FullFutureResponseSpaceEq
    (forward (ResidualIdentityState P K))
    (ResidualIdentityState P L)
  root_backward : FullFutureResponseSpaceEq
    (backward (ResidualIdentityState P L))
    (ResidualIdentityState P K)
  successor_forward : ∀ {s t u},
    ReachableResidualState P K s →
    ReachableResidualState P K t →
    ReachableResidualState P K u →
    SourceSubstitutionSuccessorRel P K s t u →
    SourceSubstitutionSuccessorRel P L (forward s) (forward t) (forward u)
  successor_backward : ∀ {s t u},
    ReachableResidualState P L s →
    ReachableResidualState P L t →
    ReachableResidualState P L u →
    SourceSubstitutionSuccessorRel P L s t u →
    SourceSubstitutionSuccessorRel P K (backward s) (backward t) (backward u)

end FinKernel

/-- Replacing the output by an extensionally equal response preserves the successor relation. -/
theorem finKernel_sourceSubstitutionSuccessorRel_output_congr {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {s t u u' : FinKernel.FullFutureResponseSpace P K}
    (huu' : FinKernel.FullFutureResponseSpaceEq u u')
    (h : FinKernel.SourceSubstitutionSuccessorRel P K s t u) :
    FinKernel.SourceSubstitutionSuccessorRel P K s t u' := by
  intro k hk
  exact finKernel_fullFutureResponseSpaceEq_trans
    (finKernel_fullFutureResponseSpaceEq_symm huu')
    (h k hk)

/-- If all reachable states collapse to root, root composed with root yields root extensionally. -/
theorem finKernel_root_sourceSubstitutionSuccessorRel_of_trivial {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    (htrivial : FinKernel.ReachableResponseTrivial P K) :
    FinKernel.SourceSubstitutionSuccessorRel P K
      (FinKernel.ResidualIdentityState P K)
      (FinKernel.ResidualIdentityState P K)
      (FinKernel.ResidualIdentityState P K) := by
  rcases (finKernel_sourceSubstitutionSuccessorRel_laws P K).total
      finKernel_residualIdentityState_reachable
      finKernel_residualIdentityState_reachable with
    ⟨u, hrel, hu⟩
  exact finKernel_sourceSubstitutionSuccessorRel_output_congr
    (htrivial u hu) hrel

/--
Any two response systems whose reachable quotients are both singleton-root
systems are equivalent under the abstract reachable-dynamics interface.
-/
def finKernel_reachableResponseDynamicsEquiv_of_trivial {n : Nat}
    {P : FinKernel.ProbeFamily n} {K L : FinKernel.FutureContextFamily n}
    (hK : FinKernel.ReachableResponseTrivial P K)
    (hL : FinKernel.ReachableResponseTrivial P L) :
    FinKernel.ReachableResponseDynamicsEquiv P K L := by
  refine {
    forward := fun _ => FinKernel.ResidualIdentityState P L
    backward := fun _ => FinKernel.ResidualIdentityState P K
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
    exact finKernel_residualIdentityState_reachable
  · intro s hs
    exact finKernel_residualIdentityState_reachable
  · intro s hs
    exact finKernel_fullFutureResponseSpaceEq_symm (hK s hs)
  · intro s hs
    exact finKernel_fullFutureResponseSpaceEq_symm (hL s hs)
  · intro s t hs ht hst
    exact finKernel_fullFutureResponseSpaceEq_refl _
  · intro s t hs ht hst
    exact finKernel_fullFutureResponseSpaceEq_trans (hK s hs)
      (finKernel_fullFutureResponseSpaceEq_symm (hK t ht))
  · intro s t hs ht hst
    exact finKernel_fullFutureResponseSpaceEq_refl _
  · intro s t hs ht hst
    exact finKernel_fullFutureResponseSpaceEq_trans (hL s hs)
      (finKernel_fullFutureResponseSpaceEq_symm (hL t ht))
  · exact finKernel_fullFutureResponseSpaceEq_refl _
  · exact finKernel_fullFutureResponseSpaceEq_refl _
  · intro s t u hs ht hu hrel
    exact finKernel_root_sourceSubstitutionSuccessorRel_of_trivial hL
  · intro s t u hs ht hu hrel
    exact finKernel_root_sourceSubstitutionSuccessorRel_of_trivial hK

/-- The generated closure of the no-generator family contains only identity. -/
theorem finKernel_generatedContext_empty_iff_identity {n : Nat}
    {c : FinKernel n n} :
    FinKernel.GeneratedContext (FinKernel.emptyFutureContextFamily n) c ↔
      c = FinKernel.identity n := by
  constructor
  · intro hc
    induction hc with
    | identity => rfl
    | generator h => exact False.elim h
    | seq hk hl ihk ihl =>
        rw [ihk, ihl]
        simp only [finKernel_compose_identity_after]
  · intro h
    subst c
    exact FinKernel.GeneratedContext.identity

/-- Hidden collapse is idempotent as an exact deterministic kernel. -/
theorem finKernel_hiddenCollapse_idempotent :
    FinKernel.compose
        (FinKernel.dirac finCollapseHidden3)
        (FinKernel.dirac finCollapseHidden3) =
      FinKernel.dirac finCollapseHidden3 := by
  rw [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  by_cases h2 : x = (2 : Fin 3)
  · subst x
    simp [finCollapseHidden3, finSelectorAt]
  · simp [finCollapseHidden3, finSelectorAt, h2]

/-- The safe collapse-generated closure contains only identity or hidden collapse. -/
theorem finKernel_merge01_safe_generated_eq_identity_or_collapse
    {c : FinKernel 3 3}
    (hc : FinKernel.GeneratedContext FinKernel.merge01SafeContextFamily3 c) :
    c = FinKernel.identity 3 ∨
      c = FinKernel.dirac finCollapseHidden3 := by
  induction hc with
  | identity => exact Or.inl rfl
  | generator hk => exact Or.inr hk
  | seq hk hl ihk ihl =>
      rcases ihk with hik | hck
      · rcases ihl with hil | hcl
        · left
          rw [hik, hil]
          simp only [finKernel_compose_identity_after]
        · right
          rw [hik, hcl]
          simp only [finKernel_compose_identity_before]
      · rcases ihl with hil | hcl
        · right
          rw [hck, hil]
          simp only [finKernel_compose_identity_after]
        · right
          rw [hck, hcl]
          exact finKernel_hiddenCollapse_idempotent

/-- Every generated no-generator action is contextually the identity action. -/
theorem finKernel_empty_generated_contextual_identity {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {k : FinKernel n n}
    (hk : FinKernel.GeneratedContext (FinKernel.emptyFutureContextFamily n) k) :
    FinKernel.ContextualActionEq P (FinKernel.emptyFutureContextFamily n)
      k (FinKernel.identity n) := by
  have hEq := (finKernel_generatedContext_empty_iff_identity).1 hk
  subst k
  exact finKernel_contextualActionEq_refl P _ _

/-- Every generated safe merge01 action is contextually equal to identity. -/
theorem finKernel_merge01_safe_generated_contextual_identity
    {k : FinKernel 3 3}
    (hk : FinKernel.GeneratedContext FinKernel.merge01SafeContextFamily3 k) :
    FinKernel.ContextualActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      k (FinKernel.identity 3) := by
  rcases finKernel_merge01_safe_generated_eq_identity_or_collapse hk with h | h
  · subst k
    exact finKernel_contextualActionEq_refl _ _ _
  · subst k
    exact finKernel_merge01_collapse_identity_contextual_action_eq_safe

/--
If every generated action is contextually identity, every reachable response
state is extensionally the root response state.
-/
theorem finKernel_reachableResponseTrivial_of_generated_contextual_identity
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    (hAll : ∀ {k : FinKernel n n}, FinKernel.GeneratedContext K k →
      FinKernel.ContextualActionEq P K k (FinKernel.identity n)) :
    FinKernel.ReachableResponseTrivial P K := by
  intro s hs
  rcases finKernel_reachableResidualState_has_generated_signature hs with
    ⟨k, hk, hsk⟩
  have hkId : FinKernel.FullFutureResponseEq P K k (FinKernel.identity n) :=
    (finKernel_contextualActionEq_iff_fullFutureResponseEq).1 (hAll hk)
  have hRoot : FinKernel.FullFutureResponseSpaceEq
      (FinKernel.ResidualIdentityState P K)
      (FinKernel.FullFutureResponse P K (FinKernel.identity n)) := by
    change FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState P K (FinKernel.identity n)
        FinKernel.GeneratedContext.identity)
      (FinKernel.FullFutureResponse P K (FinKernel.identity n))
    exact finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) FinKernel.GeneratedContext.identity
  exact finKernel_fullFutureResponseSpaceEq_trans hsk
    (finKernel_fullFutureResponseSpaceEq_trans hkId
      (finKernel_fullFutureResponseSpaceEq_symm hRoot))

/-- The no-generator merge01 response system has a singleton reachable quotient. -/
theorem finKernel_merge01_empty_reachableResponseTrivial :
    FinKernel.ReachableResponseTrivial
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact finKernel_reachableResponseTrivial_of_generated_contextual_identity
    (fun hk => finKernel_empty_generated_contextual_identity hk)

/-- The safe collapse-generated merge01 response system also has a singleton reachable quotient. -/
theorem finKernel_merge01_safe_reachableResponseTrivial :
    FinKernel.ReachableResponseTrivial
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3 := by
  exact finKernel_reachableResponseTrivial_of_generated_contextual_identity
    (fun hk => finKernel_merge01_safe_generated_contextual_identity hk)

/--
The no-generator and safe-collapse generated domains are genuinely different:
collapse is generated only in the latter.
-/
theorem finKernel_merge01_empty_safe_not_generatedDomainEq :
    ¬ FinKernel.GeneratedDomainEq
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  intro hEq
  have hCollapseEmpty : FinKernel.GeneratedContext
      (FinKernel.emptyFutureContextFamily 3)
      (FinKernel.dirac finCollapseHidden3) :=
    (hEq (FinKernel.dirac finCollapseHidden3)).2
      finKernel_merge01_collapse_generated_safe
  have hLiteral := (finKernel_generatedContext_empty_iff_identity).1 hCollapseEmpty
  exact finKernel_identity3_ne_hidden_collapse hLiteral.symm

/--
Despite the genuinely different generated domains, the reachable complete-
response/source-substitution dynamics are explicitly equivalent.
-/
def finKernel_merge01_empty_safe_responseDynamicsEquiv :
    FinKernel.ReachableResponseDynamicsEquiv
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact finKernel_reachableResponseDynamicsEquiv_of_trivial
    finKernel_merge01_empty_reachableResponseTrivial
    finKernel_merge01_safe_reachableResponseTrivial

/--
Main negative identifiability result: abstract reachable response dynamics does
not in general reconstruct the generated admissibility domain.
-/
theorem finKernel_reachableResponseDynamicsEquiv_does_not_imply_generatedDomainEq :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.ReachableResponseDynamicsEquiv FinKernel.merge01ProbeFamily3 K L →
      FinKernel.GeneratedDomainEq K L) := by
  intro hReconstruct
  exact finKernel_merge01_empty_safe_not_generatedDomainEq
    (hReconstruct _ _ finKernel_merge01_empty_safe_responseDynamicsEquiv)

/-- Expanded access is not response-trivial: it splits collapse from identity. -/
theorem finKernel_merge01_expanded_not_reachableResponseTrivial :
    ¬ FinKernel.ReachableResponseTrivial
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  intro hTrivial
  have hReach : FinKernel.ReachableResidualState
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.IdentityResidualState
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01ExpandedContextFamily3
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_expanded_collapse_generated) :=
    finKernel_generated_identityResidualState_reachable
      finKernel_merge01_expanded_collapse_generated
  have hEq := hTrivial _ hReach
  apply finKernel_merge01_expanded_not_identityResidualStateEq
  simpa [FinKernel.ReachableResponseTrivial,
    FinKernel.ResidualIdentityState,
    FinKernel.IdentityResidualStateEq] using hEq

/-- Acceptance bundle for the #2841 first transaction. -/
theorem finKernel_admissibility_domain_identifiability_bundle :
    ¬ FinKernel.GeneratedDomainEq
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    Nonempty (FinKernel.ReachableResponseDynamicsEquiv
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3) ∧
    FinKernel.ReachableResponseTrivial
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3) ∧
    FinKernel.ReachableResponseTrivial
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.ReachableResponseTrivial
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  exact ⟨finKernel_merge01_empty_safe_not_generatedDomainEq,
    ⟨finKernel_merge01_empty_safe_responseDynamicsEquiv⟩,
    finKernel_merge01_empty_reachableResponseTrivial,
    finKernel_merge01_safe_reachableResponseTrivial,
    finKernel_merge01_expanded_not_reachableResponseTrivial⟩

end RelayTheory
