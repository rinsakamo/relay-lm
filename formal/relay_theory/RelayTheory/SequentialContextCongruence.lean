import RelayTheory.ContextPolicyGauge

namespace RelayTheory

namespace FinKernel

/--
A one-step context-action equivalence is stable under a declared family of later
contexts when every admitted common future context preserves that equivalence.
-/
def ContextActionEqStableUnder {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n) : Prop :=
  ∀ (k l : FinKernel n n),
    ContextActionEq P k l →
    ∀ c : FinKernel n n, K c →
      ContextActionEq P (compose c k) (compose c l)

end FinKernel

/--
Applying `moveOneToTwo` after the hidden-state collapse changes nothing: the
collapse has already removed state 1, the only state moved by the later map.
-/
theorem finKernel_move_after_hidden_collapse_eq :
    FinKernel.compose finKernelMoveOneToTwo
      (FinKernel.dirac finCollapseHidden3) =
      FinKernel.dirac finCollapseHidden3 := by
  unfold finKernelMoveOneToTwo
  rw [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  by_cases h2 : x = (2 : Fin 3)
  · subst x
    simp [finCollapseHidden3, finSelectorAt, finMoveOneToTwo]
  · simp [finCollapseHidden3, finSelectorAt, finMoveOneToTwo, h2]

/-- Applying `moveOneToTwo` after the exact identity context is just `moveOneToTwo`. -/
theorem finKernel_move_after_identity_eq :
    FinKernel.compose finKernelMoveOneToTwo (FinKernel.identity 3) =
      finKernelMoveOneToTwo := by
  exact finKernel_compose_identity_before finKernelMoveOneToTwo

/--
The one-step quotient-action equivalence earned in #2761 is not preserved after
a common later `moveOneToTwo` context.
-/
theorem finKernel_merge01_collapse_identity_break_after_move :
    ¬ FinKernel.ContextActionEq
      FinKernel.merge01ProbeFamily3
      (FinKernel.compose finKernelMoveOneToTwo
        (FinKernel.dirac finCollapseHidden3))
      (FinKernel.compose finKernelMoveOneToTwo
        (FinKernel.identity 3)) := by
  rw [finKernel_move_after_hidden_collapse_eq,
    finKernel_move_after_identity_eq]
  intro hCollapseMove
  exact finKernel_merge01_move_not_collapse_action_eq
    (finKernel_contextActionEq_symm hCollapseMove)

/--
The restricted collapse-only policy does make the current one-step action
relation stable under every admitted later context.
-/
theorem finKernel_merge01_contextActionEq_stable_under_safe_policy :
    FinKernel.ContextActionEqStableUnder
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3 := by
  intro k l hkl c hc m f
  have hAfter :=
    finKernel_merge01_safe_context_stable
      (FinKernel.compose k f)
      (FinKernel.compose l f)
      c hc (hkl f)
  simpa only [
    finKernel_compose_associative f k c,
    finKernel_compose_associative f l c
  ] using hAfter

/--
The expanded policy from #2755 does not make one-step action equivalence a
future-composition congruence: it admits the distinguishing `moveOneToTwo`
context.
-/
theorem finKernel_merge01_contextActionEq_not_stable_under_expanded_policy :
    ¬ FinKernel.ContextActionEqStableUnder
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  intro hStable
  have hAfterMove :
      FinKernel.ContextActionEq
        FinKernel.merge01ProbeFamily3
        (FinKernel.compose finKernelMoveOneToTwo
          (FinKernel.dirac finCollapseHidden3))
        (FinKernel.compose finKernelMoveOneToTwo
          (FinKernel.identity 3)) :=
    hStable
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_identity_action_eq
      finKernelMoveOneToTwo
      (Or.inr rfl)
  exact finKernel_merge01_collapse_identity_break_after_move hAfterMove

/--
Acceptance bundle: collapse and identity are one-step action-equivalent under the
current quotient; the restricted future policy preserves that action relation;
but expanding admissible continuation with `moveOneToTwo` destroys automatic
future-composition congruence.
-/
theorem finKernel_sequential_context_congruence_bundle :
    FinKernel.ContextActionEq
        FinKernel.merge01ProbeFamily3
        (FinKernel.dirac finCollapseHidden3)
        (FinKernel.identity 3) ∧
    FinKernel.ContextActionEqStableUnder
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.ContextActionEqStableUnder
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01ExpandedContextFamily3 := by
  exact ⟨finKernel_merge01_collapse_identity_action_eq,
    finKernel_merge01_contextActionEq_stable_under_safe_policy,
    finKernel_merge01_contextActionEq_not_stable_under_expanded_policy⟩

end RelayTheory
