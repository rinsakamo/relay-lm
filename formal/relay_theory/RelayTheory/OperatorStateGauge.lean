namespace RelayTheory

/--
Run an ordinary controlled transition over a finite list of inputs.  The state
carrier and input carrier are completely generic; no finiteness or cognitive
ontology is assumed by this definition.
-/
def controlledRun
    {Sigma Input : Type}
    (step : Sigma → Input → Sigma) : Sigma → List Input → Sigma
  | state, [] => state
  | state, input :: rest => controlledRun step (step state input) rest

/--
Pair a parameter-like coordinate and an object-state-like coordinate into one
ordinary controlled transition.  Both updates see the same pre-transition pair.
-/
def pairedStep
    {Parameter State Input : Type}
    (parameterNext : Parameter → State → Input → Parameter)
    (stateNext : Parameter → State → Input → State) :
    (Parameter × State) → Input → (Parameter × State)
  | (parameter, state), input =>
      (parameterNext parameter state input,
       stateNext parameter state input)

/--
The same parameter/object update written directly as a split recursion.  This
surface exists only so that exact equivalence with ordinary paired-state
execution can be proved rather than assumed.
-/
def splitRun
    {Parameter State Input : Type}
    (parameterNext : Parameter → State → Input → Parameter)
    (stateNext : Parameter → State → Input → State) :
    (Parameter × State) → List Input → (Parameter × State)
  | pair, [] => pair
  | (parameter, state), input :: rest =>
      splitRun parameterNext stateNext
        (parameterNext parameter state input,
         stateNext parameter state input)
        rest

/--
A changing parameter and changing object state are represented exactly by one
ordinary paired-state controlled run for every finite input list.
-/
theorem splitRun_eq_controlledRun
    {Parameter State Input : Type}
    (parameterNext : Parameter → State → Input → Parameter)
    (stateNext : Parameter → State → Input → State)
    (initial : Parameter × State)
    (inputs : List Input) :
    splitRun parameterNext stateNext initial inputs =
      controlledRun (pairedStep parameterNext stateNext) initial inputs := by
  induction inputs generalizing initial with
  | nil => rfl
  | cons input rest ih =>
      cases initial with
      | mk parameter state =>
          simpa [splitRun, controlledRun, pairedStep] using
            ih (parameterNext parameter state input,
                stateNext parameter state input)

/-- A response operator is simply a state/input response function. -/
abbrev ResponseOperator (State Input : Type) := State → Input → State

/--
Specialize `pairedStep` to a function-valued active response operator.  The
fixed `metaUpdate` changes which operator is active, while the currently active
operator updates the object state.
-/
def operatorStep
    {State Input : Type}
    (metaUpdate :
      ResponseOperator State Input → State → Input →
        ResponseOperator State Input) :
    (ResponseOperator State Input × State) → Input →
      (ResponseOperator State Input × State) :=
  pairedStep metaUpdate (fun op state input => op state input)

/--
The split presentation of changing operator plus changing object state.  This is
only a specialization of the generic parameter/object recursion above.
-/
def operatorSplitRun
    {State Input : Type}
    (metaUpdate :
      ResponseOperator State Input → State → Input →
        ResponseOperator State Input) :
    (ResponseOperator State Input × State) → List Input →
      (ResponseOperator State Input × State) :=
  splitRun metaUpdate (fun op state input => op state input)

/--
A function-valued changing response operator is carried exactly as one
coordinate of an ordinary augmented state under the fixed meta-update.
-/
theorem operatorSplitRun_eq_controlledRun
    {State Input : Type}
    (metaUpdate :
      ResponseOperator State Input → State → Input →
        ResponseOperator State Input)
    (initial : ResponseOperator State Input × State)
    (inputs : List Input) :
    operatorSplitRun metaUpdate initial inputs =
      controlledRun (operatorStep metaUpdate) initial inputs := by
  exact splitRun_eq_controlledRun
    metaUpdate (fun op state input => op state input) initial inputs

/-- Boolean operator that keeps the current object state. -/
def keepBoolOperator : ResponseOperator Bool Bool :=
  fun state _ => state

/-- Boolean operator that copies the current input into object state. -/
def copyBoolInputOperator : ResponseOperator Bool Bool :=
  fun _ input => input

/--
A fixed meta-update rule that switches the active operator to `copy` whenever a
`true` input is observed; otherwise it preserves the current operator.
-/
def switchToCopyOnTrue
    (op : ResponseOperator Bool Bool)
    (_state : Bool)
    (input : Bool) : ResponseOperator Bool Bool :=
  if input then copyBoolInputOperator else op

/-- Negative control: keep the active response operator fixed forever. -/
def frozenBoolMeta
    (op : ResponseOperator Bool Bool)
    (_state : Bool)
    (_input : Bool) : ResponseOperator Bool Bool :=
  op

/--
In the positive control, the first `true` input changes the active operator but
not the object state because the pre-transition `keep` operator is still the one
used for that step.
-/
theorem operatorGauge_firstStep_stateUnchanged :
    (operatorStep switchToCopyOnTrue
      (keepBoolOperator, false) true).2 = false := by
  rfl

/--
After that first step, the newly active operator already has observably different
response behavior: on `(false,true)` it returns `true`.
-/
theorem operatorGauge_firstStep_newOperatorChangesResponse :
    (operatorStep switchToCopyOnTrue
      (keepBoolOperator, false) true).1 false true = true := by
  rfl

/--
With two `true` inputs, the operator change made on step one changes object state
on step two.  This prevents the generic theorem from being vacuous in the
operator coordinate.
-/
theorem operatorGauge_twoSteps_changesLaterObjectState :
    (controlledRun (operatorStep switchToCopyOnTrue)
      (keepBoolOperator, false) [true, true]).2 = true := by
  rfl

/--
Matched negative control: with the same starting state and inputs, freezing the
operator leaves the object state `false`.
-/
theorem operatorGauge_frozenMeta_twoSteps_stateUnchanged :
    (controlledRun (operatorStep frozenBoolMeta)
      (keepBoolOperator, false) [true, true]).2 = false := by
  rfl

/--
The positive and frozen controls therefore produce different later object-state
outcomes under the same input sequence solely because the active operator was
allowed to change in the positive arm.
-/
theorem operatorGauge_change_hasLaterBehavioralEffect :
    (controlledRun (operatorStep switchToCopyOnTrue)
        (keepBoolOperator, false) [true, true]).2 ≠
      (controlledRun (operatorStep frozenBoolMeta)
        (keepBoolOperator, false) [true, true]).2 := by
  simp [controlledRun, operatorStep, pairedStep, switchToCopyOnTrue,
    keepBoolOperator, copyBoolInputOperator, frozenBoolMeta]

end RelayTheory
