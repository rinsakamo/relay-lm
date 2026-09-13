import RelayTheory.AccessRefinementMonotonicity

namespace RelayTheory

namespace FinKernel

/--
Probe-relative operational refinement of admissibility frames at the contextual
action quotient.  `K <=op L` means every action equivalence that survives the
`L` frame already survives the `K` frame, so `L` is at least as distinguishing
as `K`.  No generated-domain inclusion is assumed by this definition.
-/
def AccessActionRefines {n : Nat}
    (P : ProbeFamily n)
    (K L : FutureContextFamily n) : Prop :=
  ∀ k l : FinKernel n n,
    ContextualActionEq P L k l → ContextualActionEq P K k l

/-- Mutual operational refinement: the two frames induce the same action quotient. -/
def AccessActionEq {n : Nat}
    (P : ProbeFamily n)
    (K L : FutureContextFamily n) : Prop :=
  AccessActionRefines P K L ∧ AccessActionRefines P L K

/-- Strict operational refinement: `L` distinguishes strictly more than `K`. -/
def AccessActionStrictRefines {n : Nat}
    (P : ProbeFamily n)
    (K L : FutureContextFamily n) : Prop :=
  AccessActionRefines P K L ∧ ¬ AccessActionRefines P L K

end FinKernel

/-- Operational access refinement is reflexive. -/
theorem finKernel_accessActionRefines_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.AccessActionRefines P K K := by
  intro k l h
  exact h

/-- Operational access refinement is transitive. -/
theorem finKernel_accessActionRefines_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.AccessActionRefines P K L)
    (hLM : FinKernel.AccessActionRefines P L M) :
    FinKernel.AccessActionRefines P K M := by
  intro k l hM
  exact hKL k l (hLM k l hM)

/-- Mutual operational refinement is reflexive. -/
theorem finKernel_accessActionEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.AccessActionEq P K K := by
  exact ⟨finKernel_accessActionRefines_refl P K,
    finKernel_accessActionRefines_refl P K⟩

/-- Mutual operational refinement is symmetric. -/
theorem finKernel_accessActionEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.AccessActionEq P K L) :
    FinKernel.AccessActionEq P L K := by
  exact ⟨h.2, h.1⟩

/-- Mutual operational refinement is transitive. -/
theorem finKernel_accessActionEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.AccessActionEq P K L)
    (hLM : FinKernel.AccessActionEq P L M) :
    FinKernel.AccessActionEq P K M := by
  exact ⟨finKernel_accessActionRefines_trans hKL.1 hLM.1,
    finKernel_accessActionRefines_trans hLM.2 hKL.2⟩

/-- Generated-domain inclusion is sufficient for operational action refinement. -/
theorem finKernel_generatedDomainLe_implies_accessActionRefines {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainLe K L) :
    FinKernel.AccessActionRefines P K L := by
  intro k l hEq
  exact finKernel_contextualActionEq_restrict_generatedDomain hKL hEq

/-- The empty merge01 frame is operationally no more distinguishing than safe. -/
theorem finKernel_merge01_empty_refines_safe :
    FinKernel.AccessActionRefines
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact finKernel_generatedDomainLe_implies_accessActionRefines
    finKernel_merge01_empty_lt_safe_generatedDomain.1

/--
Conversely, safe merge01 is also no more distinguishing than the empty frame:
equivalence under the empty closure gives current one-step action equivalence,
and every safe generated continuation preserves that equivalence.
-/
theorem finKernel_merge01_safe_refines_empty :
    FinKernel.AccessActionRefines
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  intro k l hEmpty
  have hAction : FinKernel.ContextActionEq FinKernel.merge01ProbeFamily3 k l :=
    finKernel_contextualActionEq_implies_actionEq hEmpty
  intro c hc
  exact finKernel_contextActionEq_preserved_by_generated
    finKernel_merge01_contextActionEq_stable_under_safe_policy
    hc hAction

/-- Empty and safe merge01 have the same operational contextual-action quotient. -/
theorem finKernel_merge01_empty_safe_accessActionEq :
    FinKernel.AccessActionEq
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact ⟨finKernel_merge01_empty_refines_safe,
    finKernel_merge01_safe_refines_empty⟩

/--
Operational action refinement does not reconstruct generated-domain inclusion.
The safe frame refines the empty frame operationally even though its generated
closure is not included in the empty closure.
-/
theorem finKernel_accessActionRefines_does_not_imply_generatedDomainLe :
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.AccessActionRefines FinKernel.merge01ProbeFamily3 K L →
      FinKernel.GeneratedDomainLe K L) := by
  intro hConverse
  exact finKernel_merge01_empty_lt_safe_generatedDomain.2
    (hConverse _ _ finKernel_merge01_safe_refines_empty)

/-- Safe merge01 is operationally below expanded merge01. -/
theorem finKernel_merge01_safe_refines_expanded :
    FinKernel.AccessActionRefines
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  exact finKernel_generatedDomainLe_implies_accessActionRefines
    finKernel_merge01_safe_le_expanded_generatedDomain

/-- Expanded merge01 is not operationally below safe merge01. -/
theorem finKernel_merge01_expanded_not_refines_safe :
    ¬ FinKernel.AccessActionRefines
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      FinKernel.merge01SafeContextFamily3 := by
  intro hReverse
  have hExpanded := hReverse
    (FinKernel.dirac finCollapseHidden3)
    (FinKernel.identity 3)
    finKernel_merge01_collapse_identity_contextual_action_eq_safe
  exact finKernel_merge01_collapse_identity_not_contextual_action_eq_expanded
    hExpanded

/-- Safe-to-expanded is a strict operational access refinement. -/
theorem finKernel_merge01_safe_strictly_refines_expanded :
    FinKernel.AccessActionStrictRefines
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  exact ⟨finKernel_merge01_safe_refines_expanded,
    finKernel_merge01_expanded_not_refines_safe⟩

/-- Acceptance bundle for #2855 operational access refinement. -/
theorem finKernel_operational_access_refinement_bundle :
    (∀ {n : Nat}
      (P : FinKernel.ProbeFamily n)
      (K : FinKernel.FutureContextFamily n),
      FinKernel.AccessActionRefines P K K) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L M : FinKernel.FutureContextFamily n},
      FinKernel.AccessActionRefines P K L →
      FinKernel.AccessActionRefines P L M →
      FinKernel.AccessActionRefines P K M) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.GeneratedDomainLe K L →
      FinKernel.AccessActionRefines P K L) ∧
    FinKernel.AccessActionEq
      FinKernel.merge01ProbeFamily3
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    ¬ (∀ (K L : FinKernel.FutureContextFamily 3),
      FinKernel.AccessActionRefines FinKernel.merge01ProbeFamily3 K L →
      FinKernel.GeneratedDomainLe K L) ∧
    FinKernel.AccessActionStrictRefines
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  exact ⟨finKernel_accessActionRefines_refl,
    finKernel_accessActionRefines_trans,
    finKernel_generatedDomainLe_implies_accessActionRefines,
    finKernel_merge01_empty_safe_accessActionEq,
    finKernel_accessActionRefines_does_not_imply_generatedDomainLe,
    finKernel_merge01_safe_strictly_refines_expanded⟩

end RelayTheory
