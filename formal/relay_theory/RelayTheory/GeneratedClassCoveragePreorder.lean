import RelayTheory.MutualGeneratedClassCoverage

namespace RelayTheory

/--
Generated contextual-class coverage is self-contained under composition: the
first coverage already transports the second frame's contextual equality back
to the first frame, so no separately supplied action-partition equality is
needed.
-/
theorem finKernel_generatedClassCovered_trans_preorder {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedClassCovered P K L)
    (hLM : FinKernel.GeneratedClassCovered P L M) :
    FinKernel.GeneratedClassCovered P K M := by
  intro k hk
  rcases hKL k hk with ⟨l, hl, hklK⟩
  rcases hLM l hl with ⟨m, hm, hlmL⟩
  have hlmK : FinKernel.ContextualActionEq P K l m :=
    finKernel_generatedClassCovered_implies_accessActionRefines hKL l m hlmL
  exact ⟨m, hm, finKernel_contextualActionEq_trans hklK hlmK⟩

/-- Literal generated-domain inclusion is sufficient for generated-class coverage. -/
theorem finKernel_generatedDomainLe_implies_generatedClassCovered {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainLe K L) :
    FinKernel.GeneratedClassCovered P K L := by
  intro k hk
  exact ⟨k, hKL k hk, finKernel_contextualActionEq_refl P K k⟩

/--
The symmetric kernel of the generated-class coverage preorder is exactly the
common realized-class support equivalence characterized in #2870.
-/
theorem finKernel_generatedClassCovered_symmetricKernel_iff_accessClassSupportEq
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    (FinKernel.GeneratedClassCovered P K L ∧
      FinKernel.GeneratedClassCovered P L K) ↔
      FinKernel.AccessClassSupportEq P K L := by
  simpa [FinKernel.MutualGeneratedClassCoverage] using
    (finKernel_accessClassSupportEq_iff_mutualGeneratedClassCoverage
      (P := P) (K := K) (L := L)).symm

/--
Under all exact probes, the safe and empty access frames still induce the same
global action partition, hence safe refines empty operationally.
-/
theorem finKernel_allProbes_safe_empty_accessActionRefines :
    FinKernel.AccessActionRefines
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact (finKernel_allProbes_accessActionEq
    FinKernel.merge01SafeContextFamily3
    (FinKernel.emptyFutureContextFamily 3)).1

/--
But safe does not cover empty at the realized contextual-class level: safe
realizes the hidden-collapse class, while empty realizes only identity.  This is
the strictness witness separating class coverage from action refinement.
-/
theorem finKernel_allProbes_safe_empty_not_generatedClassCovered :
    ¬ FinKernel.GeneratedClassCovered
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  intro hCover
  rcases hCover
      (FinKernel.dirac finCollapseHidden3)
      finKernel_merge01_collapse_generated_safe with
    ⟨l, hlEmpty, hCollapseL⟩
  have hLiteral : FinKernel.dirac finCollapseHidden3 = l :=
    (finKernel_contextualActionEq_allProbes_iff_eq
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3) l).1 hCollapseL
  have hIdentity : l = FinKernel.identity 3 :=
    (finKernel_generatedContext_empty_iff_identity).1 hlEmpty
  exact finKernel_identity3_ne_hidden_collapse
    (hLiteral.trans hIdentity).symm

/--
Generated contextual-class coverage therefore forms a preorder whose symmetric
kernel is `AccessClassSupportEq`, and its forgetful map to operational action
refinement is strict.
-/
theorem finKernel_generated_class_coverage_preorder_bundle :
    (∀ {n : Nat}
      (P : FinKernel.ProbeFamily n)
      (K : FinKernel.FutureContextFamily n),
      FinKernel.GeneratedClassCovered P K K) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L M : FinKernel.FutureContextFamily n},
      FinKernel.GeneratedClassCovered P K L →
      FinKernel.GeneratedClassCovered P L M →
      FinKernel.GeneratedClassCovered P K M) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.GeneratedDomainLe K L →
      FinKernel.GeneratedClassCovered P K L) ∧
    FinKernel.AccessActionRefines
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) ∧
    ¬ FinKernel.GeneratedClassCovered
      (FinKernel.allProbes 3)
      FinKernel.merge01SafeContextFamily3
      (FinKernel.emptyFutureContextFamily 3) := by
  exact ⟨finKernel_generatedClassCovered_refl,
    finKernel_generatedClassCovered_trans_preorder,
    finKernel_generatedDomainLe_implies_generatedClassCovered,
    finKernel_allProbes_safe_empty_accessActionRefines,
    finKernel_allProbes_safe_empty_not_generatedClassCovered⟩

end RelayTheory
