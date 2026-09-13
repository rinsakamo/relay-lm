import RelayTheory.ContextualActionQuotient

namespace RelayTheory

/--
Closure-relative contextual action equivalence is preserved when the same
endomorphic context is placed before both representatives.  The proof uses the
source-polymorphism already built into `ContextActionEq`: the common prefix can
be absorbed into the quantified source kernel.
-/
theorem finKernel_contextualActionEq_precompose {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l d : FinKernel n n}
    (h : FinKernel.ContextualActionEq P K k l) :
    FinKernel.ContextualActionEq P K
      (FinKernel.compose k d)
      (FinKernel.compose l d) := by
  intro c hc
  have hAfter : FinKernel.ContextActionEq P
      (FinKernel.compose c k)
      (FinKernel.compose c l) := h c hc
  intro m f
  have hAtPrefixedSource := hAfter (FinKernel.compose d f)
  simpa only [finKernel_compose_associative] using hAtPrefixedSource

/--
Two-sided representative independence for sequential composition.  Replacing
the earlier representative uses source-polymorphism; replacing the later
representative uses generated-continuation congruence from #2778.
-/
theorem finKernel_contextualActionEq_compose_respects_representatives {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k k' l l' : FinKernel n n}
    (hkk : FinKernel.ContextualActionEq P K k k')
    (hll : FinKernel.ContextualActionEq P K l l')
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.ContextualActionEq P K
      (FinKernel.compose l k)
      (FinKernel.compose l' k') := by
  have hEarlier : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k)
      (FinKernel.compose l k') :=
    finKernel_contextualActionEq_postcompose_generated hkk hl
  have hLater : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k')
      (FinKernel.compose l' k') :=
    finKernel_contextualActionEq_precompose hll
  exact finKernel_contextualActionEq_trans hEarlier hLater

/-- Composition of two generated continuations stays in the generated closure. -/
theorem finKernel_generatedContext_compose {n : Nat}
    {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.GeneratedContext K (FinKernel.compose l k) :=
  FinKernel.GeneratedContext.seq hk hl

/--
Generated representatives can be replaced on both sides of composition without
changing either closure membership or the resulting contextual action class.
This is the direct descent contract needed before introducing any explicit
quotient algebra object.
-/
theorem finKernel_contextualActionEq_generated_composition_descent {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k k' l l' : FinKernel n n}
    (hkk : FinKernel.ContextualActionEq P K k k')
    (hll : FinKernel.ContextualActionEq P K l l')
    (hk : FinKernel.GeneratedContext K k)
    (hk' : FinKernel.GeneratedContext K k')
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l') :
    FinKernel.GeneratedContext K (FinKernel.compose l k) ∧
    FinKernel.GeneratedContext K (FinKernel.compose l' k') ∧
    FinKernel.ContextualActionEq P K
      (FinKernel.compose l k)
      (FinKernel.compose l' k') := by
  exact ⟨finKernel_generatedContext_compose hk hl,
    finKernel_generatedContext_compose hk' hl',
    finKernel_contextualActionEq_compose_respects_representatives hkk hll hl⟩

/-- The safe hidden-state collapse is a generated continuation. -/
theorem finKernel_merge01_collapse_generated_safe :
    FinKernel.GeneratedContext
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3) := by
  exact FinKernel.GeneratedContext.generator rfl

/--
Concrete anti-cheat witness: in the safe `merge01` closure, replacing both
literal collapse representatives by identity representatives inside a two-step
composite preserves the contextual action class and generated-closure status.
-/
theorem finKernel_merge01_safe_composition_representative_substitution :
    FinKernel.GeneratedContext
      FinKernel.merge01SafeContextFamily3
      (FinKernel.compose
        (FinKernel.dirac finCollapseHidden3)
        (FinKernel.dirac finCollapseHidden3)) ∧
    FinKernel.GeneratedContext
      FinKernel.merge01SafeContextFamily3
      (FinKernel.compose (FinKernel.identity 3) (FinKernel.identity 3)) ∧
    FinKernel.ContextualActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.compose
        (FinKernel.dirac finCollapseHidden3)
        (FinKernel.dirac finCollapseHidden3))
      (FinKernel.compose (FinKernel.identity 3) (FinKernel.identity 3)) := by
  exact finKernel_contextualActionEq_generated_composition_descent
    finKernel_merge01_collapse_identity_contextual_action_eq_safe
    finKernel_merge01_collapse_identity_contextual_action_eq_safe
    finKernel_merge01_collapse_generated_safe
    FinKernel.GeneratedContext.identity
    finKernel_merge01_collapse_generated_safe
    FinKernel.GeneratedContext.identity

/--
Acceptance bundle: contextual equivalence supports representative-independent
sequential composition on generated continuations, and the concrete safe fixture
exercises two-sided representative substitution.
-/
theorem finKernel_contextual_action_composition_descent_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K : FinKernel.FutureContextFamily n}
      {k k' l l' : FinKernel n n},
      FinKernel.ContextualActionEq P K k k' →
      FinKernel.ContextualActionEq P K l l' →
      FinKernel.GeneratedContext K k →
      FinKernel.GeneratedContext K k' →
      FinKernel.GeneratedContext K l →
      FinKernel.GeneratedContext K l' →
      FinKernel.GeneratedContext K (FinKernel.compose l k) ∧
      FinKernel.GeneratedContext K (FinKernel.compose l' k') ∧
      FinKernel.ContextualActionEq P K
        (FinKernel.compose l k)
        (FinKernel.compose l' k')) ∧
    FinKernel.ContextualActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.compose
        (FinKernel.dirac finCollapseHidden3)
        (FinKernel.dirac finCollapseHidden3))
      (FinKernel.compose (FinKernel.identity 3) (FinKernel.identity 3)) := by
  constructor
  · intro n P K k k' l l' hkk hll hk hk' hl hl'
    exact finKernel_contextualActionEq_generated_composition_descent
      hkk hll hk hk' hl hl'
  · exact finKernel_merge01_safe_composition_representative_substitution.2.2

end RelayTheory
