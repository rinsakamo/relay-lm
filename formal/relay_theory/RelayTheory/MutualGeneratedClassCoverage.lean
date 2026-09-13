import RelayTheory.ReachableClassSupportSufficiency

namespace RelayTheory

namespace FinKernel

/--
The two frames realize the same generated contextual-action classes, measured
in each source frame's own contextual equivalence.  No separate global action
partition equality is assumed.
-/
def MutualGeneratedClassCoverage {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  GeneratedClassCovered P K L ∧ GeneratedClassCovered P L K

end FinKernel

/--
Coverage of K-generated contextual classes by L-generated classes already makes
L's global contextual-action equivalence at least as fine as K's.  The key is
that a contextual equality between the covering continuations is a one-step
action equality for arbitrary prefixed sources.
-/
theorem finKernel_generatedClassCovered_implies_accessActionRefines {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hCover : FinKernel.GeneratedClassCovered P K L) :
    FinKernel.AccessActionRefines P K L := by
  intro k l hL c hc
  rcases hCover c hc with ⟨d, hd, hcdK⟩
  have hcd : FinKernel.ContextActionEq P c d :=
    finKernel_contextualActionEq_implies_actionEq hcdK
  intro m f
  have hLeft :
      FinKernel.ProbeEq P
        (FinKernel.compose (FinKernel.compose c k) f)
        (FinKernel.compose (FinKernel.compose d k) f) := by
    simpa only [finKernel_compose_associative] using
      hcd (FinKernel.compose k f)
  have hMiddle :
      FinKernel.ProbeEq P
        (FinKernel.compose (FinKernel.compose d k) f)
        (FinKernel.compose (FinKernel.compose d l) f) :=
    (hL d hd) f
  have hRight :
      FinKernel.ProbeEq P
        (FinKernel.compose (FinKernel.compose d l) f)
        (FinKernel.compose (FinKernel.compose c l) f) := by
    simpa only [finKernel_compose_associative] using
      (finKernel_contextActionEq_symm hcd) (FinKernel.compose l f)
  exact finKernel_probeEq_trans hLeft
    (finKernel_probeEq_trans hMiddle hRight)

/-- Mutual generated contextual-class coverage reconstructs global action equality. -/
theorem finKernel_mutualGeneratedClassCoverage_implies_accessActionEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.MutualGeneratedClassCoverage P K L) :
    FinKernel.AccessActionEq P K L := by
  exact ⟨finKernel_generatedClassCovered_implies_accessActionRefines h.1,
    finKernel_generatedClassCovered_implies_accessActionRefines h.2⟩

/-- Mutual generated contextual-class coverage is reflexive. -/
theorem finKernel_mutualGeneratedClassCoverage_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.MutualGeneratedClassCoverage P K K := by
  exact ⟨finKernel_generatedClassCovered_refl P K,
    finKernel_generatedClassCovered_refl P K⟩

/-- Mutual generated contextual-class coverage is symmetric. -/
theorem finKernel_mutualGeneratedClassCoverage_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.MutualGeneratedClassCoverage P K L) :
    FinKernel.MutualGeneratedClassCoverage P L K := by
  exact ⟨h.2, h.1⟩

/-- Mutual generated contextual-class coverage is transitive. -/
theorem finKernel_mutualGeneratedClassCoverage_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.MutualGeneratedClassCoverage P K L)
    (hLM : FinKernel.MutualGeneratedClassCoverage P L M) :
    FinKernel.MutualGeneratedClassCoverage P K M := by
  have hActionKL : FinKernel.AccessActionEq P K L :=
    finKernel_mutualGeneratedClassCoverage_implies_accessActionEq hKL
  have hActionLM : FinKernel.AccessActionEq P L M :=
    finKernel_mutualGeneratedClassCoverage_implies_accessActionEq hLM
  constructor
  · exact finKernel_generatedClassCovered_trans
      hActionKL hKL.1 hLM.1
  · exact finKernel_generatedClassCovered_trans
      (finKernel_accessActionEq_symm hActionLM) hLM.2 hKL.2

/--
The explicit global `AccessActionEq` conjunct in #2864 is redundant: common
access-class support is exactly mutual coverage of generated contextual classes.
-/
theorem finKernel_accessClassSupportEq_iff_mutualGeneratedClassCoverage
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n} :
    FinKernel.AccessClassSupportEq P K L ↔
      FinKernel.MutualGeneratedClassCoverage P K L := by
  constructor
  · intro h
    exact ⟨h.2.1, h.2.2⟩
  · intro h
    exact ⟨finKernel_mutualGeneratedClassCoverage_implies_accessActionEq h,
      h.1, h.2⟩

/--
Mutual generated contextual-class coverage therefore suffices for the
representative-free reachable dynamics correspondence already earned in #2864.
-/
theorem finKernel_mutualGeneratedClassCoverage_implies_relationalDynamics
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.MutualGeneratedClassCoverage P K L) :
    Nonempty (FinKernel.ReachableClassDynamicsCorrespondence P K L) := by
  exact finKernel_accessClassSupportEq_implies_relationalDynamics
    ((finKernel_accessClassSupportEq_iff_mutualGeneratedClassCoverage).2 h)

/--
#2861 remains a negative boundary: equal all-probes global action partitions do
not force mutual generated-class coverage when realized support differs.
-/
theorem finKernel_allProbes_empty_safe_not_mutualGeneratedClassCoverage :
    ¬ FinKernel.MutualGeneratedClassCoverage
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  intro h
  exact finKernel_allProbes_empty_safe_not_accessClassSupportEq
    ((finKernel_accessClassSupportEq_iff_mutualGeneratedClassCoverage).2 h)

/-- Acceptance bundle for #2870. -/
theorem finKernel_mutual_generated_class_coverage_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.GeneratedClassCovered P K L →
      FinKernel.AccessActionRefines P K L) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.AccessClassSupportEq P K L ↔
        FinKernel.MutualGeneratedClassCoverage P K L) ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.MutualGeneratedClassCoverage P K L →
      Nonempty (FinKernel.ReachableClassDynamicsCorrespondence P K L)) ∧
    FinKernel.AccessActionEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.MutualGeneratedClassCoverage
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  exact ⟨finKernel_generatedClassCovered_implies_accessActionRefines,
    finKernel_accessClassSupportEq_iff_mutualGeneratedClassCoverage,
    finKernel_mutualGeneratedClassCoverage_implies_relationalDynamics,
    finKernel_allProbes_accessActionEq _ _,
    finKernel_allProbes_empty_safe_not_mutualGeneratedClassCoverage⟩

end RelayTheory
