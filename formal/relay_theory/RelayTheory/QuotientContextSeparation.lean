import RelayTheory.RestrictedContexts

namespace RelayTheory

namespace FinKernel

/-- A declared family of admissible endomorphic future contexts. -/
abbrev FutureContextFamily (n : Nat) := FinKernel n n → Prop

/--
A current probe-relative equivalence is stable for a declared future-context
family when every admitted context preserves that equivalence for every
compatible source interface.
-/
def ContextStableFor {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n) : Prop :=
  ∀ {m : Nat} (f g : FinKernel m n) (k : FinKernel n n),
    K k →
    ProbeEq P f g →
    ProbeEq P (compose k f) (compose k g)

/-- The coarse three-state probe used by the existing continuation counterexample. -/
def merge01ProbeFamily3 : ProbeFamily 3 :=
  singletonProbe ⟨2, finKernelMerge01⟩

/--
A safe future-context policy containing only the existing hidden-state collapse,
which factors through the coarse `merge01` observation.
-/
def merge01SafeContextFamily3 : FutureContextFamily 3 :=
  fun k => k = dirac finCollapseHidden3

/--
An expanded future-context policy that additionally admits the existing map
which moves hidden state 1 into the separately observed state 2.
-/
def merge01ExpandedContextFamily3 : FutureContextFamily 3 :=
  fun k =>
    k = dirac finCollapseHidden3 ∨
    k = finKernelMoveOneToTwo

end FinKernel

/--
The safe policy is universally stable for the coarse `merge01` quotient.  The
proof is not fixture-specific in `f` and `g`: every currently equivalent pair
remains equivalent after the admitted factorizing context.
-/
theorem finKernel_merge01_safe_context_stable :
    FinKernel.ContextStableFor
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3 := by
  intro m f g k hk hfg
  unfold FinKernel.merge01SafeContextFamily3 at hk
  subst k
  have hObserved :
      FinKernel.ObservedEq finKernelMerge01 f g := by
    apply (finKernel_probeEq_singleton_iff_observedEq
      finKernelMerge01 f g).1
    simpa [FinKernel.merge01ProbeFamily3] using hfg
  have hObservedDirac :
      FinKernel.ObservedEq (FinKernel.dirac finMerge01) f g := by
    simpa [finKernelMerge01] using hObserved
  have hAfterDirac :=
    finKernel_observedEq_postcompose_dirac_of_factors
      finMerge01 finMerge01 finCollapseHidden3
      finCollapseHidden3_factors_merge01 hObservedDirac
  have hAfter :
      FinKernel.ObservedEq finKernelMerge01
        (FinKernel.compose (FinKernel.dirac finCollapseHidden3) f)
        (FinKernel.compose (FinKernel.dirac finCollapseHidden3) g) := by
    simpa [finKernelMerge01] using hAfterDirac
  have hProbe :=
    (finKernel_probeEq_singleton_iff_observedEq
      finKernelMerge01
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) f)
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) g)).2 hAfter
  simpa [FinKernel.merge01ProbeFamily3] using hProbe

/--
The expanded policy is not stable for the very same current quotient: the
already-earned zero/one source pair is currently merged, while the additionally
admitted `moveOneToTwo` future context exposes their distinction.
-/
theorem finKernel_merge01_expanded_context_not_stable :
    ¬ FinKernel.ContextStableFor
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3 := by
  intro hStable
  have hCurrent :
      FinKernel.ProbeEq FinKernel.merge01ProbeFamily3
        finKernelZero3 finKernelOne3 := by
    have hSingleton :=
      (finKernel_probeEq_singleton_iff_observedEq
        finKernelMerge01 finKernelZero3 finKernelOne3).2
        finKernel_merge01_observes_zero_one_equal
    simpa [FinKernel.merge01ProbeFamily3] using hSingleton
  have hFuture :
      FinKernel.ProbeEq FinKernel.merge01ProbeFamily3
        (FinKernel.compose finKernelMoveOneToTwo finKernelZero3)
        (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) :=
    hStable finKernelZero3 finKernelOne3 finKernelMoveOneToTwo
      (Or.inr rfl) hCurrent
  have hFutureObserved :
      FinKernel.ObservedEq finKernelMerge01
        (FinKernel.compose finKernelMoveOneToTwo finKernelZero3)
        (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) := by
    apply (finKernel_probeEq_singleton_iff_observedEq
      finKernelMerge01
      (FinKernel.compose finKernelMoveOneToTwo finKernelZero3)
      (FinKernel.compose finKernelMoveOneToTwo finKernelOne3)).1
    simpa [FinKernel.merge01ProbeFamily3] using hFuture
  exact finKernel_fixed_probe_not_postcomposition_stable hFutureObserved

/--
The two future-context policies are literally different.  This follows from
their different quotient-stability behavior, without needing to privilege a
particular kernel coordinate as the reason for the difference.
-/
theorem finKernel_merge01_context_families_differ :
    FinKernel.merge01SafeContextFamily3 ≠
      FinKernel.merge01ExpandedContextFamily3 := by
  intro hEq
  have hExpandedStable :
      FinKernel.ContextStableFor
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01ExpandedContextFamily3 := by
    simpa [hEq] using finKernel_merge01_safe_context_stable
  exact finKernel_merge01_expanded_context_not_stable hExpandedStable

/--
Acceptance bundle: one and the same current probe-relative quotient supports a
universally stable restricted future-context policy and an unstable expanded
policy.  Bare current equivalence therefore does not determine future-context
stability in this finite exact model.
-/
theorem finKernel_quotient_context_separation_bundle :
    FinKernel.merge01SafeContextFamily3 ≠
        FinKernel.merge01ExpandedContextFamily3 ∧
    FinKernel.ContextStableFor
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.ContextStableFor
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01ExpandedContextFamily3 := by
  exact ⟨finKernel_merge01_context_families_differ,
    finKernel_merge01_safe_context_stable,
    finKernel_merge01_expanded_context_not_stable⟩

end RelayTheory
