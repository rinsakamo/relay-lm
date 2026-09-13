import RelayTheory.GeneratedContinuationClosure

namespace RelayTheory

namespace FinKernel

/--
Closure-relative contextual action equivalence: two endomorphic contexts are
identified only when every generated admissible future suffix still sees them as
the same probe-relative action on every compatible source.
-/
def ContextualActionEq {n : Nat}
    (P : ProbeFamily n)
    (K : FutureContextFamily n)
    (k l : FinKernel n n) : Prop :=
  ∀ c : FinKernel n n,
    GeneratedContext K c →
      ContextActionEq P (compose c k) (compose c l)

end FinKernel

/-- One-step induced context-action equivalence is transitive. -/
theorem finKernel_contextActionEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {k l r : FinKernel n n}
    (hkl : FinKernel.ContextActionEq P k l)
    (hlr : FinKernel.ContextActionEq P l r) :
    FinKernel.ContextActionEq P k r := by
  intro m f
  exact finKernel_probeEq_trans (hkl f) (hlr f)

/-- Closure-relative contextual action equivalence is reflexive. -/
theorem finKernel_contextualActionEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n)
    (k : FinKernel n n) :
    FinKernel.ContextualActionEq P K k k := by
  intro c hc
  exact finKernel_contextActionEq_refl P (FinKernel.compose c k)

/-- Closure-relative contextual action equivalence is symmetric. -/
theorem finKernel_contextualActionEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (h : FinKernel.ContextualActionEq P K k l) :
    FinKernel.ContextualActionEq P K l k := by
  intro c hc
  exact finKernel_contextActionEq_symm (h c hc)

/-- Closure-relative contextual action equivalence is transitive. -/
theorem finKernel_contextualActionEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l r : FinKernel n n}
    (hkl : FinKernel.ContextualActionEq P K k l)
    (hlr : FinKernel.ContextualActionEq P K l r) :
    FinKernel.ContextualActionEq P K k r := by
  intro c hc
  exact finKernel_contextActionEq_trans (hkl c hc) (hlr c hc)

/--
Because identity belongs to every generated closure, contextual action
equivalence always implies current one-step action equivalence.
-/
theorem finKernel_contextualActionEq_implies_actionEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (h : FinKernel.ContextualActionEq P K k l) :
    FinKernel.ContextActionEq P k l := by
  have hId : FinKernel.ContextActionEq P
      (FinKernel.compose (FinKernel.identity n) k)
      (FinKernel.compose (FinKernel.identity n) l) :=
    h (FinKernel.identity n) FinKernel.GeneratedContext.identity
  intro m f
  simpa only [finKernel_compose_identity_after] using hId f

/--
Contextual action equivalence is preserved when both sides are followed by the
same generated admissible future continuation.
-/
theorem finKernel_contextualActionEq_postcompose_generated {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {k l d : FinKernel n n}
    (h : FinKernel.ContextualActionEq P K k l)
    (hd : FinKernel.GeneratedContext K d) :
    FinKernel.ContextualActionEq P K
      (FinKernel.compose d k)
      (FinKernel.compose d l) := by
  intro c hc
  have hcd : FinKernel.GeneratedContext K (FinKernel.compose c d) :=
    FinKernel.GeneratedContext.seq hd hc
  have hAll : FinKernel.ContextActionEq P
      (FinKernel.compose (FinKernel.compose c d) k)
      (FinKernel.compose (FinKernel.compose c d) l) :=
    h (FinKernel.compose c d) hcd
  intro m f
  have hAtSource := hAll f
  simpa only [finKernel_compose_associative] using hAtSource

/--
Under the safe `merge01` continuation closure, hidden-state collapse and exact
identity are contextually action-equivalent even though they are different
literal kernels.
-/
theorem finKernel_merge01_collapse_identity_contextual_action_eq_safe :
    FinKernel.ContextualActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) := by
  intro c hc
  exact finKernel_contextActionEq_preserved_by_generated
    finKernel_merge01_contextActionEq_stable_under_safe_policy
    hc
    finKernel_merge01_collapse_identity_action_eq

/--
Expanding admissible continuation with `moveOneToTwo` splits the previous
contextual action class.
-/
theorem finKernel_merge01_collapse_identity_not_contextual_action_eq_expanded :
    ¬ FinKernel.ContextualActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) := by
  intro h
  have hAfterMove : FinKernel.ContextActionEq
      FinKernel.merge01ProbeFamily3
      (FinKernel.compose finKernelMoveOneToTwo
        (FinKernel.dirac finCollapseHidden3))
      (FinKernel.compose finKernelMoveOneToTwo
        (FinKernel.identity 3)) :=
    h finKernelMoveOneToTwo
      finKernel_merge01_move_generated_by_expanded_policy
  exact finKernel_merge01_collapse_identity_break_after_move hAfterMove

/--
Acceptance bundle: literal kernel inequality coexists with one contextual action
class under the safe closure, while expanding admissible continuation splits that
class.
-/
theorem finKernel_contextual_action_quotient_bundle :
    FinKernel.identity 3 ≠ FinKernel.dirac finCollapseHidden3 ∧
    FinKernel.ContextualActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) ∧
    ¬ FinKernel.ContextualActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) := by
  exact ⟨finKernel_identity3_ne_hidden_collapse,
    finKernel_merge01_collapse_identity_contextual_action_eq_safe,
    finKernel_merge01_collapse_identity_not_contextual_action_eq_expanded⟩

end RelayTheory
