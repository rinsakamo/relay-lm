import RelayTheory.AdaptiveFeedbackSequentialization

namespace RelayTheory

/-- Encode a fixed policy label together with the live controller node. -/
def policyControllerEncode {b c : Nat} (policy : Fin b) (node : Fin c) : Fin (b * c) :=
  finPairTransport.toFun (policy, node)

/-- Recover the fixed policy label from the combined controller state. -/
def policyControllerPolicy {b c : Nat} (pc : Fin (b * c)) : Fin b :=
  (finPairTransport.invFun pc).1

/-- Recover the live controller node from the combined controller state. -/
def policyControllerNode {b c : Nat} (pc : Fin (b * c)) : Fin c :=
  (finPairTransport.invFun pc).2

@[simp] theorem policyControllerPolicy_encode {b c : Nat}
    (policy : Fin b) (node : Fin c) :
    policyControllerPolicy (policyControllerEncode policy node) = policy := by
  simp [policyControllerPolicy, policyControllerEncode, finPair_transport_roundtrip]

@[simp] theorem policyControllerNode_encode {b c : Nat}
    (policy : Fin b) (node : Fin c) :
    policyControllerNode (policyControllerEncode policy node) = node := by
  simp [policyControllerNode, policyControllerEncode, finPair_transport_roundtrip]

/--
Selection for a finite adaptive policy family. The policy label is read from the
ordinary combined controller state, while the action is still chosen online
from the current realized observation and live controller node.
-/
def familySelect {b c q d : Nat}
    (select : Fin b → Nat → Fin c → Fin q → Fin d)
    (r : Nat) (pc : Fin (b * c)) (obs : Fin q) : Fin d :=
  select (policyControllerPolicy pc) r (policyControllerNode pc) obs

/--
Update the live controller while preserving the fixed policy component.
-/
def familyUpdate {b c q : Nat}
    (update : Fin b → Nat → Fin c → Fin q → Fin q → Fin c)
    (r : Nat) (pc : Fin (b * c)) (oldObs newObs : Fin q) : Fin (b * c) :=
  policyControllerEncode (policyControllerPolicy pc)
    (update (policyControllerPolicy pc) r (policyControllerNode pc) oldObs newObs)

@[simp] theorem familySelect_encoded {b c q d : Nat}
    (select : Fin b → Nat → Fin c → Fin q → Fin d)
    (policy : Fin b) (r : Nat) (node : Fin c) (obs : Fin q) :
    familySelect select r (policyControllerEncode policy node) obs =
      select policy r node obs := by
  simp [familySelect]

@[simp] theorem familyUpdate_encoded {b c q : Nat}
    (update : Fin b → Nat → Fin c → Fin q → Fin q → Fin c)
    (policy : Fin b) (r : Nat) (node : Fin c) (oldObs newObs : Fin q) :
    familyUpdate update r (policyControllerEncode policy node) oldObs newObs =
      policyControllerEncode policy (update policy r node oldObs newObs) := by
  simp [familyUpdate]

/-- One common homogeneous compiler for the whole finite policy family. -/
def familyAdaptiveCompiledStep {n q b c d k : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Fin b → Nat → Fin c → Fin q → Fin d)
    (update : Fin b → Nat → Fin c → Fin q → Fin q → Fin c) :
    FinKernel (((b * c) * n) * (k + 1)) (((b * c) * n) * (k + 1)) :=
  adaptiveCompiledStep (k := k) observe actions (familySelect select) (familyUpdate update)

/-- Direct projected adaptive path for one selected policy and initial live controller node. -/
def familyAdaptiveProjectedPath {n q b c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Fin b → Nat → Fin c → Fin q → Fin d)
    (update : Fin b → Nat → Fin c → Fin q → Fin q → Fin c)
    (policy : Fin b) (node0 : Fin c) (r : Nat) : FinKernel n n :=
  adaptiveProjectedPath observe actions (familySelect select) (familyUpdate update)
    (policyControllerEncode policy node0) r

/-- Initial interface varies only by the chosen policy label and live controller node. -/
def familyAdaptiveInitial {n b c k : Nat}
    (policy : Fin b) (node0 : Fin c) :
    FinKernel n (((b * c) * n) * (k + 1)) :=
  adaptiveInitial (n := n) (k := k) (policyControllerEncode policy node0)

/-- Terminal interface forgets phase, policy and controller, retaining only physical state. -/
def familyAdaptiveTerminal {n b c k : Nat} :
    FinKernel (((b * c) * n) * (k + 1)) n :=
  adaptiveTerminal (n := n) (c := b * c) (k := k)

/--
A single homogeneous augmented-state kernel simultaneously represents every
policy in a finite family. The compiler is independent of the selected policy;
only the deterministic initial combined controller state varies with
`(policy,node0)`.
-/
theorem bounded_adaptive_policy_family_sequentialization
    {n q b c d k : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Fin b → Nat → Fin c → Fin q → Fin d)
    (update : Fin b → Nat → Fin c → Fin q → Fin q → Fin c)
    (policy : Fin b) (node0 : Fin c) :
    FinKernel.compose (familyAdaptiveTerminal (n := n) (b := b) (c := c) (k := k))
        (FinKernel.compose
          (kernelIterate
            (familyAdaptiveCompiledStep (k := k) observe actions select update) k)
          (familyAdaptiveInitial (n := n) (k := k) policy node0)) =
      familyAdaptiveProjectedPath observe actions select update policy node0 k := by
  exact bounded_adaptive_feedback_sequentialization
    observe actions (familySelect select) (familyUpdate update)
    (policyControllerEncode policy node0)

/-- Common post-observation preserves every policy-specific exact equality. -/
theorem bounded_adaptive_policy_family_observer_preserved
    {n q b c d k z : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Fin b → Nat → Fin c → Fin q → Fin d)
    (update : Fin b → Nat → Fin c → Fin q → Fin q → Fin c)
    (policy : Fin b) (node0 : Fin c) (obs : FinKernel n z) :
    FinKernel.compose obs
      (FinKernel.compose (familyAdaptiveTerminal (n := n) (b := b) (c := c) (k := k))
        (FinKernel.compose
          (kernelIterate
            (familyAdaptiveCompiledStep (k := k) observe actions select update) k)
          (familyAdaptiveInitial (n := n) (k := k) policy node0))) =
      FinKernel.compose obs
        (familyAdaptiveProjectedPath observe actions select update policy node0 k) := by
  rw [bounded_adaptive_policy_family_sequentialization
    observe actions select update policy node0]

/-- Valid actions imply one valid homogeneous compiler shared by all policies. -/
theorem familyAdaptiveCompiledStep_valid {n q b c d k : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Fin b → Nat → Fin c → Fin q → Fin d)
    (update : Fin b → Nat → Fin c → Fin q → Fin q → Fin c)
    (hvalid : ∀ a : Fin d, FinKernel.Valid (actions a)) :
    FinKernel.Valid (familyAdaptiveCompiledStep (k := k) observe actions select update) := by
  exact adaptiveCompiledStep_valid observe actions (familySelect select) (familyUpdate update) hvalid

/-- Every policy-specific deterministic initial interface and the common terminal interface are valid. -/
theorem familyAdaptiveInterfaces_valid {n b c k : Nat}
    (policy : Fin b) (node0 : Fin c) :
    FinKernel.Valid (familyAdaptiveInitial (n := n) (k := k) policy node0) ∧
    FinKernel.Valid (familyAdaptiveTerminal (n := n) (b := b) (c := c) (k := k)) := by
  exact adaptiveInterfaces_valid (n := n) (k := k) (policyControllerEncode policy node0)

/-- Two-policy control: policy zero uses the merged online selector; policy one inverts it. -/
def policyFamilySelect2
    (policy : Fin 2) (_r : Nat) (_node : Fin 1) (obs : Fin 2) : Fin 2 :=
  if policy = (0 : Fin 2) then
    feedbackSelect2 0 (0 : Fin 1) obs
  else if obs = (0 : Fin 2) then 1 else 0

/-- One live node is enough for the non-vacuous policy-family control. -/
def policyFamilyUpdate1
    (_policy : Fin 2) (_r : Nat) (_node : Fin 1)
    (_oldObs _newObs : Fin 2) : Fin 1 := 0

/-- At the same realized observation, the two policy labels select different actions. -/
theorem policyFamilySelect2_policy_sensitive :
    policyFamilySelect2 (0 : Fin 2) 0 (0 : Fin 1) (0 : Fin 2) ≠
      policyFamilySelect2 (1 : Fin 2) 0 (0 : Fin 1) (0 : Fin 2) := by
  simp [policyFamilySelect2, feedbackSelect2]

/-- The different online selections have different physical response at the same input/output cell. -/
theorem policyFamilySelect2_changes_response :
    feedbackActions2
        (policyFamilySelect2 (0 : Fin 2) 0 (0 : Fin 1) (0 : Fin 2))
        (0 : Fin 2) (0 : Fin 2) = 1 ∧
    feedbackActions2
        (policyFamilySelect2 (1 : Fin 2) 0 (0 : Fin 1) (0 : Fin 2))
        (0 : Fin 2) (0 : Fin 2) = 0 := by
  simp [policyFamilySelect2, feedbackSelect2, feedbackActions2, boundedFlip2,
    FinKernel.identity, FinKernel.dirac]

/--
Non-vacuous positive control: the policy labels change online action choice, yet
one valid homogeneous compiled kernel represents both policies exactly.
-/
theorem adaptivePolicyFamily_positive_control :
    policyFamilySelect2 (0 : Fin 2) 0 (0 : Fin 1) (0 : Fin 2) ≠
      policyFamilySelect2 (1 : Fin 2) 0 (0 : Fin 1) (0 : Fin 2) ∧
    FinKernel.Valid
      (familyAdaptiveCompiledStep (k := 2)
        feedbackObserve2 feedbackActions2 policyFamilySelect2 policyFamilyUpdate1) ∧
    (∀ policy : Fin 2,
      FinKernel.compose
        (familyAdaptiveTerminal (n := 2) (b := 2) (c := 1) (k := 2))
        (FinKernel.compose
          (kernelIterate
            (familyAdaptiveCompiledStep (k := 2)
              feedbackObserve2 feedbackActions2 policyFamilySelect2 policyFamilyUpdate1) 2)
          (familyAdaptiveInitial (n := 2) (k := 2) policy (0 : Fin 1))) =
        familyAdaptiveProjectedPath
          feedbackObserve2 feedbackActions2 policyFamilySelect2 policyFamilyUpdate1
          policy (0 : Fin 1) 2) := by
  refine ⟨policyFamilySelect2_policy_sensitive, ?_, ?_⟩
  · exact familyAdaptiveCompiledStep_valid
      feedbackObserve2 feedbackActions2 policyFamilySelect2 policyFamilyUpdate1
      feedbackActions2_valid
  · intro policy
    exact bounded_adaptive_policy_family_sequentialization
      feedbackObserve2 feedbackActions2 policyFamilySelect2 policyFamilyUpdate1
      policy (0 : Fin 1)

end RelayTheory
