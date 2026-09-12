import RelayTheory.AccessibilityEfficacyGap

namespace RelayTheory

/--
Weak criterion-indexed operational dominance.  `higher = better` is only the
finite convention used by this module.  Criteria, histories, outcomes and the
score function are all declared externally; this definition is not a cognitive
primitive or a universal utility scale.
-/
def WeakOperationalDominance
    {Criterion History Outcome : Type}
    (score : Criterion → History → Outcome → Nat)
    (candidate baseline : History → Outcome) : Prop :=
  ∀ criterion history,
    score criterion history (baseline history) ≤
      score criterion history (candidate history)

/--
Strict operational dominance adds at least one strictly improved declared
criterion/history pair to weak dominance.
-/
def StrictOperationalDominance
    {Criterion History Outcome : Type}
    (score : Criterion → History → Outcome → Nat)
    (candidate baseline : History → Outcome) : Prop :=
  WeakOperationalDominance score candidate baseline ∧
    ∃ criterion history,
      score criterion history (baseline history) <
        score criterion history (candidate history)

/-- Weak dominance is reflexive for every externally declared score frame. -/
theorem weakOperationalDominance_refl
    {Criterion History Outcome : Type}
    (score : Criterion → History → Outcome → Nat)
    (realization : History → Outcome) :
    WeakOperationalDominance score realization realization := by
  intro criterion history
  exact Nat.le_refl _

/-- Strict dominance is irreflexive. -/
theorem strictOperationalDominance_irrefl
    {Criterion History Outcome : Type}
    (score : Criterion → History → Outcome → Nat)
    (realization : History → Outcome) :
    ¬ StrictOperationalDominance score realization realization := by
  intro hDominates
  rcases hDominates.2 with ⟨criterion, history, hStrict⟩
  exact Nat.lt_irrefl _ hStrict

/--
The single-utility comparison introduced in #2695 is exactly the singleton-
criterion special case of ordinary criterion-indexed operational dominance.
No additional efficacy primitive is needed for that finite comparison.
-/
theorem strictPointwiseUtilityImprovement_iff_singleCriterionDominance
    {History Action : Type}
    (utility : History → Action → Nat)
    (candidate baseline : History → Action) :
    StrictPointwiseUtilityImprovement utility candidate baseline ↔
      StrictOperationalDominance
        (fun (_ : Unit) => utility) candidate baseline := by
  constructor
  · rintro ⟨hWeak, ⟨history, hStrict⟩⟩
    refine ⟨?_, ?_⟩
    · intro criterion h
      cases criterion
      exact hWeak h
    · exact ⟨(), history, hStrict⟩
  · rintro ⟨hWeak, ⟨criterion, history, hStrict⟩⟩
    refine ⟨?_, ?_⟩
    · intro h
      exact hWeak () h
    · cases criterion
      exact ⟨history, hStrict⟩

/-- One task-only criterion used by the criterion-expansion fixture. -/
inductive DominanceTaskCriterion where
  | task

deriving DecidableEq, Repr

/-- Expanded task/resource criterion family. -/
inductive DominanceTaskResourceCriterion where
  | task
  | resource

deriving DecidableEq, Repr

/-- Candidate realization for the finite criterion-expansion fixture. -/
def dominanceCandidate (_ : Unit) : Bool := true

/-- Baseline realization for the finite criterion-expansion fixture. -/
def dominanceBaseline (_ : Unit) : Bool := false

/-- Under the task-only frame, the candidate receives the higher score. -/
def dominanceTaskOnlyScore :
    DominanceTaskCriterion → Unit → Bool → Nat
  | .task, _, false => 1
  | .task, _, true => 2

/--
After resource accounting is added, the candidate remains better on task score
but the baseline is better on the resource coordinate.
-/
def dominanceTaskResourceScore :
    DominanceTaskResourceCriterion → Unit → Bool → Nat
  | .task, _, false => 1
  | .task, _, true => 2
  | .resource, _, false => 1
  | .resource, _, true => 0

/-- The candidate strictly dominates under the task-only criterion family. -/
theorem dominanceCandidate_strictlyDominates_taskOnly :
    StrictOperationalDominance
      dominanceTaskOnlyScore dominanceCandidate dominanceBaseline := by
  constructor
  · intro criterion history
    cases criterion
    cases history
    simp [dominanceTaskOnlyScore, dominanceCandidate, dominanceBaseline]
  · refine ⟨DominanceTaskCriterion.task, (), ?_⟩
    simp [dominanceTaskOnlyScore, dominanceCandidate, dominanceBaseline]

/-- Adding the resource criterion destroys candidate weak dominance. -/
theorem dominanceCandidate_not_weaklyDominates_taskResource :
    ¬ WeakOperationalDominance
      dominanceTaskResourceScore dominanceCandidate dominanceBaseline := by
  intro hDominates
  have hBad := hDominates DominanceTaskResourceCriterion.resource ()
  simp [dominanceTaskResourceScore, dominanceCandidate, dominanceBaseline] at hBad

/-- The baseline also fails weak dominance because it loses the task criterion. -/
theorem dominanceBaseline_not_weaklyDominates_taskResource :
    ¬ WeakOperationalDominance
      dominanceTaskResourceScore dominanceBaseline dominanceCandidate := by
  intro hDominates
  have hBad := hDominates DominanceTaskResourceCriterion.task ()
  simp [dominanceTaskResourceScore, dominanceCandidate, dominanceBaseline] at hBad

/-- Hence the two realizations are Pareto-incomparable under the expanded family. -/
theorem dominanceTaskResource_incomparable :
    ¬ StrictOperationalDominance
        dominanceTaskResourceScore dominanceCandidate dominanceBaseline ∧
      ¬ StrictOperationalDominance
        dominanceTaskResourceScore dominanceBaseline dominanceCandidate := by
  constructor
  · intro hStrict
    exact dominanceCandidate_not_weaklyDominates_taskResource hStrict.1
  · intro hStrict
    exact dominanceBaseline_not_weaklyDominates_taskResource hStrict.1

/--
Finite criterion-family relativity witness: the very same candidate/baseline
pair is strictly ordered in the task-only frame and incomparable after a
conflicting independently declared resource criterion is included.
-/
theorem criterionExpansion_canDestroyOperationalDominance_fixture :
    StrictOperationalDominance
        dominanceTaskOnlyScore dominanceCandidate dominanceBaseline ∧
      (¬ StrictOperationalDominance
          dominanceTaskResourceScore dominanceCandidate dominanceBaseline ∧
       ¬ StrictOperationalDominance
          dominanceTaskResourceScore dominanceBaseline dominanceCandidate) := by
  exact ⟨dominanceCandidate_strictlyDominates_taskOnly,
    dominanceTaskResource_incomparable⟩

/-- A realized outcome records task success together with helper use. -/
structure ResourceAccountedOutcome where
  taskSuccess : Bool
  helperUsed : Bool

deriving DecidableEq, Repr

/-- Local frame scores only task success and leaves helper cost outside its ledger. -/
inductive LocalOutcomeCriterion where
  | task

deriving DecidableEq, Repr

/-- System frame additionally scores conserved resource / no-helper realization. -/
inductive SystemOutcomeCriterion where
  | task
  | resource

deriving DecidableEq, Repr

/-- Better task outcome obtained with the declared external helper. -/
def helperCandidate (_ : Unit) : ResourceAccountedOutcome :=
  ⟨true, true⟩

/-- Worse task outcome that uses no helper. -/
def noHelperBaseline (_ : Unit) : ResourceAccountedOutcome :=
  ⟨false, false⟩

/-- A one-criterion local evaluator that ignores helper consumption. -/
def localOutcomeScore :
    LocalOutcomeCriterion → Unit → ResourceAccountedOutcome → Nat
  | .task, _, ⟨false, _⟩ => 0
  | .task, _, ⟨true, _⟩ => 1

/--
A system evaluator uses the same task score but adds a coordinate rewarding
resource conservation.  This is explicit accounting, not a universal cost law.
-/
def systemOutcomeScore :
    SystemOutcomeCriterion → Unit → ResourceAccountedOutcome → Nat
  | .task, _, ⟨false, _⟩ => 0
  | .task, _, ⟨true, _⟩ => 1
  | .resource, _, ⟨_, false⟩ => 1
  | .resource, _, ⟨_, true⟩ => 0

/-- If helper cost is outside the declared ledger, the helper candidate dominates. -/
theorem helperCandidate_strictlyDominates_localFrame :
    StrictOperationalDominance
      localOutcomeScore helperCandidate noHelperBaseline := by
  constructor
  · intro criterion history
    cases criterion
    cases history
    simp [localOutcomeScore, helperCandidate, noHelperBaseline]
  · refine ⟨LocalOutcomeCriterion.task, (), ?_⟩
    simp [localOutcomeScore, helperCandidate, noHelperBaseline]

/-- Once helper/resource use is explicitly charged, the candidate no longer weakly dominates. -/
theorem helperCandidate_not_weaklyDominates_systemFrame :
    ¬ WeakOperationalDominance
      systemOutcomeScore helperCandidate noHelperBaseline := by
  intro hDominates
  have hBad := hDominates SystemOutcomeCriterion.resource ()
  simp [systemOutcomeScore, helperCandidate, noHelperBaseline] at hBad

/-- The baseline does not dominate either because its task outcome is worse. -/
theorem noHelperBaseline_not_weaklyDominates_systemFrame :
    ¬ WeakOperationalDominance
      systemOutcomeScore noHelperBaseline helperCandidate := by
  intro hDominates
  have hBad := hDominates SystemOutcomeCriterion.task ()
  simp [systemOutcomeScore, helperCandidate, noHelperBaseline] at hBad

/--
The same realized candidate/baseline behaviors receive different dominance
verdicts solely because the declared accounting frame includes or excludes the
helper/resource coordinate.
-/
theorem resourceAccounting_canChangeOperationalDominance_fixture :
    StrictOperationalDominance
        localOutcomeScore helperCandidate noHelperBaseline ∧
      (¬ StrictOperationalDominance
          systemOutcomeScore helperCandidate noHelperBaseline ∧
       ¬ StrictOperationalDominance
          systemOutcomeScore noHelperBaseline helperCandidate) := by
  refine ⟨helperCandidate_strictlyDominates_localFrame, ?_, ?_⟩
  · intro hStrict
    exact helperCandidate_not_weaklyDominates_systemFrame hStrict.1
  · intro hStrict
    exact noHelperBaseline_not_weaklyDominates_systemFrame hStrict.1

end RelayTheory
