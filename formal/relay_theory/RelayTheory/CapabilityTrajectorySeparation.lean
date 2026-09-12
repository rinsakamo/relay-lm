import RelayTheory.OperatorStateGauge

namespace RelayTheory

/--
A deliberately tiny capability score for finite countermodels.  The score is a
declared evaluator for the fixture, not a definition of Skill, Generality, or
Intelligence.
-/
def boolCapabilityScore : Bool → Nat
  | false => 0
  | true => 1

/-- Scalar strict comparison under an explicitly supplied score. -/
def StrictCapabilityBetter
    {State : Type}
    (score : State → Nat)
    (candidate baseline : State) : Prop :=
  score baseline < score candidate

/--
A brittle specialist begins capable but loses the scored capability under the
`true` novelty condition.  A `false` condition leaves its current state intact.
-/
def brittleSpecialistStep (state input : Bool) : Bool :=
  if input then false else state

/--
A minimal learner-like control copies the current condition into its capability
state.  This is only an ordinary response law.
-/
def copyConditionStep (_state input : Bool) : Bool :=
  input

/--
Before the common novelty input, the specialist has strictly higher capability
under the same score convention.
-/
theorem specialist_strictly_better_at_snapshot :
    StrictCapabilityBetter boolCapabilityScore true false := by
  simp [StrictCapabilityBetter, boolCapabilityScore]

/--
After the same single `true` input is supplied to both systems, their ordering
reverses: the initially weaker learner-like system is now strictly better.
-/
theorem snapshot_dominance_does_not_force_future_dominance :
    StrictCapabilityBetter boolCapabilityScore
      (controlledRun copyConditionStep false [true])
      (controlledRun brittleSpecialistStep true [true]) := by
  simp [StrictCapabilityBetter, boolCapabilityScore, controlledRun,
    copyConditionStep, brittleSpecialistStep]

/--
Package the matched counterexample explicitly: one score convention, a strict
initial ordering, one common subsequent input sequence, and the opposite later
ordering all hold together.
-/
theorem current_order_can_reverse_under_common_input :
    StrictCapabilityBetter boolCapabilityScore true false ∧
    StrictCapabilityBetter boolCapabilityScore
      (controlledRun copyConditionStep false [true])
      (controlledRun brittleSpecialistStep true [true]) := by
  constructor
  · exact specialist_strictly_better_at_snapshot
  · exact snapshot_dominance_does_not_force_future_dominance

/-- Ordinary static response used for the equal-snapshot control. -/
def staticBoolStep (state _input : Bool) : Bool :=
  state

/--
The static and learner-like systems can begin at exactly the same scored current
capability.
-/
theorem equal_snapshot_control :
    boolCapabilityScore false = boolCapabilityScore false := by
  rfl

/--
Equal current capability does not identify later capability: under the same
`true` input, the static system remains `false` while the learner-like system
becomes `true`.
-/
theorem equal_snapshot_can_diverge_under_common_input :
    StrictCapabilityBetter boolCapabilityScore
      (controlledRun copyConditionStep false [true])
      (controlledRun staticBoolStep false [true]) := by
  simp [StrictCapabilityBetter, boolCapabilityScore, controlledRun,
    copyConditionStep, staticBoolStep]

/--
A response law whose scored future capability follows the declared condition.
-/
def conditionFollowerStep (_state input : Bool) : Bool :=
  input

/--
A response law with the opposite condition dependence.
-/
def conditionOpposerStep (_state input : Bool) : Bool :=
  if input then false else true

/-- The condition-sensitive pair has an equal current capability snapshot. -/
theorem condition_pair_equal_snapshot :
    boolCapabilityScore false = boolCapabilityScore false := by
  rfl

/--
Under the `true` condition, the follower is strictly better than the opposer.
-/
theorem condition_true_orders_follower_above_opposer :
    StrictCapabilityBetter boolCapabilityScore
      (controlledRun conditionFollowerStep false [true])
      (controlledRun conditionOpposerStep false [true]) := by
  simp [StrictCapabilityBetter, boolCapabilityScore, controlledRun,
    conditionFollowerStep, conditionOpposerStep]

/--
Under the `false` condition, with the same initial snapshot and same score
convention, the prospective ordering reverses.
-/
theorem condition_false_orders_opposer_above_follower :
    StrictCapabilityBetter boolCapabilityScore
      (controlledRun conditionOpposerStep false [false])
      (controlledRun conditionFollowerStep false [false]) := by
  simp [StrictCapabilityBetter, boolCapabilityScore, controlledRun,
    conditionFollowerStep, conditionOpposerStep]

/--
The same equal-snapshot pair therefore supports opposite later rankings under
two explicitly declared future conditions.  A context-free prospective order is
not determined by the snapshot alone.
-/
theorem equal_snapshot_admits_condition_relative_future_order :
    StrictCapabilityBetter boolCapabilityScore
      (controlledRun conditionFollowerStep false [true])
      (controlledRun conditionOpposerStep false [true]) ∧
    StrictCapabilityBetter boolCapabilityScore
      (controlledRun conditionOpposerStep false [false])
      (controlledRun conditionFollowerStep false [false]) := by
  constructor
  · exact condition_true_orders_follower_above_opposer
  · exact condition_false_orders_opposer_above_follower

end RelayTheory
