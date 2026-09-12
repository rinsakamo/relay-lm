import RelayTheory.QuotientContextSeparation

namespace RelayTheory

namespace FinKernel

/-- Two endomorphic future contexts induce the same action relative to a probe family
when every compatible source is probe-equivalent after either context. -/
def ContextActionEq {n : Nat}
    (P : ProbeFamily n) (k l : FinKernel n n) : Prop :=
  ∀ {m : Nat} (f : FinKernel m n),
    ProbeEq P (compose k f) (compose l f)

/-- One literal context family is covered by another up to induced probe-relative action. -/
def ContextFamilyActionRefines {n : Nat}
    (P : ProbeFamily n)
    (K L : FutureContextFamily n) : Prop :=
  ∀ k, K k → ∃ l, L l ∧ ContextActionEq P k l

/-- Mutual coverage of literal context families up to induced probe-relative action. -/
def ContextFamilyActionEq {n : Nat}
    (P : ProbeFamily n)
    (K L : FutureContextFamily n) : Prop :=
  ContextFamilyActionRefines P K L ∧
  ContextFamilyActionRefines P L K

/-- The context family containing only the hidden-state collapse. -/
def merge01CollapseOnlyContextFamily3 : FutureContextFamily 3 :=
  fun k => k = dirac finCollapseHidden3

/-- The collapse-only family with an additional literal identity context. -/
def merge01CollapseIdentityContextFamily3 : FutureContextFamily 3 :=
  fun k =>
    k = dirac finCollapseHidden3 ∨
    k = identity 3

end FinKernel

/-- Induced context-action equivalence is reflexive. -/
theorem finKernel_contextActionEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n) (k : FinKernel n n) :
    FinKernel.ContextActionEq P k k := by
  intro m f
  exact finKernel_probeEq_refl P _

/-- Induced context-action equivalence is symmetric. -/
theorem finKernel_contextActionEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n} {k l : FinKernel n n}
    (h : FinKernel.ContextActionEq P k l) :
    FinKernel.ContextActionEq P l k := by
  intro m f
  exact finKernel_probeEq_symm (h f)

/--
Under the coarse `merge01` observation, postcomposing that observation with the
hidden-state collapse changes nothing exactly.
-/
theorem finKernel_merge01_after_hidden_collapse_eq :
    FinKernel.compose finKernelMerge01 (FinKernel.dirac finCollapseHidden3) =
      finKernelMerge01 := by
  unfold finKernelMerge01
  rw [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  by_cases h2 : x = (2 : Fin 3)
  · subst x
    simp [finCollapseHidden3, finSelectorAt, finMerge01]
  · simp [finCollapseHidden3, finSelectorAt, finMerge01, h2]

/--
The hidden-state collapse and literal identity context induce exactly the same
action on every source relative to the current `merge01` quotient.
-/
theorem finKernel_merge01_collapse_identity_action_eq :
    FinKernel.ContextActionEq
      FinKernel.merge01ProbeFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3) := by
  intro m f
  have hObserved :
      FinKernel.ObservedEq finKernelMerge01
        (FinKernel.compose (FinKernel.dirac finCollapseHidden3) f)
        (FinKernel.compose (FinKernel.identity 3) f) := by
    unfold FinKernel.ObservedEq
    apply (finKernel_behaviorEq_iff_eq _ _).2
    calc
      FinKernel.compose finKernelMerge01
          (FinKernel.compose (FinKernel.dirac finCollapseHidden3) f) =
        FinKernel.compose
          (FinKernel.compose finKernelMerge01
            (FinKernel.dirac finCollapseHidden3)) f :=
          finKernel_compose_associative f
            (FinKernel.dirac finCollapseHidden3) finKernelMerge01
      _ = FinKernel.compose finKernelMerge01 f := by
          rw [finKernel_merge01_after_hidden_collapse_eq]
      _ = FinKernel.compose finKernelMerge01
          (FinKernel.compose (FinKernel.identity 3) f) := by
          rw [finKernel_compose_identity_after f]
  have hProbe :=
    (finKernel_probeEq_singleton_iff_observedEq
      finKernelMerge01
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) f)
      (FinKernel.compose (FinKernel.identity 3) f)).2 hObserved
  simpa [FinKernel.merge01ProbeFamily3] using hProbe

/-- The exact identity kernel is literally distinct from the hidden-state collapse kernel. -/
theorem finKernel_identity3_ne_hidden_collapse :
    FinKernel.identity 3 ≠ FinKernel.dirac finCollapseHidden3 := by
  intro h
  have hv := congrArg
    (fun k => k (1 : Fin 3) (1 : Fin 3)) h
  simp [FinKernel.identity, FinKernel.dirac,
    finCollapseHidden3, finSelectorAt] at hv

/-- The collapse-only and collapse-plus-identity policies are literally different. -/
theorem finKernel_merge01_context_policy_families_differ :
    FinKernel.merge01CollapseOnlyContextFamily3 ≠
      FinKernel.merge01CollapseIdentityContextFamily3 := by
  intro hEq
  have hExpanded :
      FinKernel.merge01CollapseIdentityContextFamily3
        (FinKernel.identity 3) := by
    unfold FinKernel.merge01CollapseIdentityContextFamily3
    exact Or.inr rfl
  have hSafe :
      FinKernel.merge01CollapseOnlyContextFamily3
        (FinKernel.identity 3) := by
    rw [hEq]
    exact hExpanded
  unfold FinKernel.merge01CollapseOnlyContextFamily3 at hSafe
  exact finKernel_identity3_ne_hidden_collapse hSafe

/--
Despite literal inequality, the collapse-only and collapse-plus-identity
families induce the same set of probe-relative context actions.
-/
theorem finKernel_merge01_context_policy_action_eq :
    FinKernel.ContextFamilyActionEq
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01CollapseOnlyContextFamily3
      FinKernel.merge01CollapseIdentityContextFamily3 := by
  constructor
  · intro k hk
    unfold FinKernel.merge01CollapseOnlyContextFamily3 at hk
    subst k
    refine ⟨FinKernel.dirac finCollapseHidden3, ?_, ?_⟩
    · unfold FinKernel.merge01CollapseIdentityContextFamily3
      exact Or.inl rfl
    · exact finKernel_contextActionEq_refl
        FinKernel.merge01ProbeFamily3
        (FinKernel.dirac finCollapseHidden3)
  · intro k hk
    unfold FinKernel.merge01CollapseIdentityContextFamily3 at hk
    rcases hk with hk | hk
    · subst k
      refine ⟨FinKernel.dirac finCollapseHidden3, ?_, ?_⟩
      · unfold FinKernel.merge01CollapseOnlyContextFamily3
        rfl
      · exact finKernel_contextActionEq_refl
          FinKernel.merge01ProbeFamily3
          (FinKernel.dirac finCollapseHidden3)
    · subst k
      refine ⟨FinKernel.dirac finCollapseHidden3, ?_, ?_⟩
      · unfold FinKernel.merge01CollapseOnlyContextFamily3
        rfl
      · exact finKernel_contextActionEq_symm
          finKernel_merge01_collapse_identity_action_eq

/-- The collapsed source-1 path is observed as coarse state 0. -/
theorem finKernel_merge01_after_collapse_one :
    FinKernel.compose finKernelMerge01
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelOne3) =
      FinKernel.dirac (fun _ : Fin 1 => (0 : Fin 2)) := by
  calc
    FinKernel.compose finKernelMerge01
        (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelOne3) =
      FinKernel.compose
        (FinKernel.compose finKernelMerge01
          (FinKernel.dirac finCollapseHidden3)) finKernelOne3 :=
        finKernel_compose_associative finKernelOne3
          (FinKernel.dirac finCollapseHidden3) finKernelMerge01
    _ = FinKernel.compose finKernelMerge01 finKernelOne3 := by
        rw [finKernel_merge01_after_hidden_collapse_eq]
    _ = FinKernel.dirac (fun _ : Fin 1 => (0 : Fin 2)) := by
        unfold finKernelMerge01 finKernelOne3
        rw [finKernel_dirac_compose]
        apply finKernel_dirac_congr
        intro x
        simp [finMerge01]

/--
Negative control: the existing `moveOneToTwo` context is not redundant with the
hidden-state collapse under the same current quotient.
-/
theorem finKernel_merge01_move_not_collapse_action_eq :
    ¬ FinKernel.ContextActionEq
      FinKernel.merge01ProbeFamily3
      finKernelMoveOneToTwo
      (FinKernel.dirac finCollapseHidden3) := by
  intro hAction
  have hProbe := hAction finKernelOne3
  have hObserved :
      FinKernel.ObservedEq finKernelMerge01
        (FinKernel.compose finKernelMoveOneToTwo finKernelOne3)
        (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelOne3) := by
    apply (finKernel_probeEq_singleton_iff_observedEq
      finKernelMerge01
      (FinKernel.compose finKernelMoveOneToTwo finKernelOne3)
      (FinKernel.compose (FinKernel.dirac finCollapseHidden3) finKernelOne3)).1
    simpa [FinKernel.merge01ProbeFamily3] using hProbe
  unfold FinKernel.ObservedEq at hObserved
  rw [finKernel_merge01_after_move_one,
    finKernel_merge01_after_collapse_one] at hObserved
  have hv := hObserved (0 : Fin 1) (0 : Fin 2)
  simp [FinKernel.dirac] at hv

/--
Acceptance bundle: distinct literal admissible-context families can induce the
same current quotient action, while the existing distinguishing context remains
outside that action-equivalence class.
-/
theorem finKernel_context_policy_gauge_bundle :
    FinKernel.merge01CollapseOnlyContextFamily3 ≠
        FinKernel.merge01CollapseIdentityContextFamily3 ∧
    FinKernel.ContextFamilyActionEq
        FinKernel.merge01ProbeFamily3
        FinKernel.merge01CollapseOnlyContextFamily3
        FinKernel.merge01CollapseIdentityContextFamily3 ∧
    ¬ FinKernel.ContextActionEq
        FinKernel.merge01ProbeFamily3
        finKernelMoveOneToTwo
        (FinKernel.dirac finCollapseHidden3) := by
  exact ⟨finKernel_merge01_context_policy_families_differ,
    finKernel_merge01_context_policy_action_eq,
    finKernel_merge01_move_not_collapse_action_eq⟩

end RelayTheory
