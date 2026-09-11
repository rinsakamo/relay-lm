import RelayTheory.BoundedMultidirectionSequentializationValid

namespace RelayTheory

/-- Encode the current finite controller node together with the current physical state. -/
def feedbackEncode {n c : Nat} (node : Fin c) (x : Fin n) : Fin (c * n) :=
  finPairTransport.toFun (node, x)

/-- Forget the controller node and retain only the current physical state. -/
def feedbackPhysical {n c : Nat} (s : Fin (c * n)) : Fin n :=
  (finPairTransport.invFun s).2

/-- Read the current controller node from the augmented state. -/
def feedbackNode {n c : Nat} (s : Fin (c * n)) : Fin c :=
  (finPairTransport.invFun s).1

@[simp] theorem feedbackPhysical_feedbackEncode {n c : Nat}
    (node : Fin c) (x : Fin n) :
    feedbackPhysical (feedbackEncode node x) = x := by
  simp [feedbackPhysical, feedbackEncode, finPair_transport_roundtrip]

@[simp] theorem feedbackNode_feedbackEncode {n c : Nat}
    (node : Fin c) (x : Fin n) :
    feedbackNode (feedbackEncode node x) = node := by
  simp [feedbackNode, feedbackEncode, finPair_transport_roundtrip]

/--
One genuinely online adaptive step. The action is selected from the current
realized observation and current controller node. After the physical transition,
the next controller node may depend on both the old and new observations.

No complete future branch/program label appears in the state.
-/
def adaptiveStep {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (r : Nat) : FinKernel (c * n) (c * n) :=
  fun s t =>
    let si : Fin c × Fin n := finPairTransport.invFun s
    let ti : Fin c × Fin n := finPairTransport.invFun t
    let oldObs := observe si.2
    let action := select r si.1 oldObs
    if ti.1 = update r si.1 oldObs (observe ti.2) then
      actions action si.2 ti.2
    else
      0

@[simp] theorem adaptiveStep_encoded {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (r : Nat) (node next : Fin c) (x y : Fin n) :
    adaptiveStep observe actions select update r
        (feedbackEncode node x) (feedbackEncode next y) =
      if next = update r node (observe x) (observe y) then
        actions (select r node (observe x)) x y
      else
        0 := by
  simp [adaptiveStep, feedbackEncode, finPair_transport_roundtrip]

/--
The physical one-step response selected online from the current controller node
and current realized observation, before retaining the next controller node.
-/
def adaptivePhysicalResponse {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (r : Nat) : FinKernel (c * n) n :=
  fun s y =>
    let si : Fin c × Fin n := finPairTransport.invFun s
    actions (select r si.1 (observe si.2)) si.2 y

@[simp] theorem adaptivePhysicalResponse_encoded {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (r : Nat) (node : Fin c) (x y : Fin n) :
    adaptivePhysicalResponse observe actions select r (feedbackEncode node x) y =
      actions (select r node (observe x)) x y := by
  simp [adaptivePhysicalResponse, feedbackEncode, finPair_transport_roundtrip]

/-- Summing over all possible next controller nodes recovers exactly the selected physical mass. -/
theorem adaptiveStep_sum_next_nodes {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (r : Nat) (node : Fin c) (x y : Fin n) :
    sumFin c (fun next =>
      adaptiveStep observe actions select update r
        (feedbackEncode node x) (feedbackEncode next y)) =
      actions (select r node (observe x)) x y := by
  calc
    sumFin c (fun next =>
        adaptiveStep observe actions select update r
          (feedbackEncode node x) (feedbackEncode next y)) =
      sumFin c (fun next =>
        if next = update r node (observe x) (observe y) then
          actions (select r node (observe x)) x y
        else 0) := by
          apply sumFin_congr
          intro next
          rw [adaptiveStep_encoded]
    _ = actions (select r node (observe x)) x y :=
      sumFin_single (update r node (observe x) (observe y))
        (fun _ => actions (select r node (observe x)) x y)

/--
Forgetting the controller after one adaptive step yields exactly the physical
response chosen from the realized current observation. This is the one-step
online-feedback commutation square.
-/
theorem adaptiveStep_project_physical {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (r : Nat) :
    FinKernel.compose (FinKernel.dirac (feedbackPhysical (n := n) (c := c)))
        (adaptiveStep observe actions select update r) =
      adaptivePhysicalResponse observe actions select r := by
  funext s y
  let si : Fin c × Fin n := finPairTransport.invFun s
  rcases hsi : si with ⟨node, x⟩
  have hflat : feedbackEncode node x = s := by
    calc
      feedbackEncode node x = finPairTransport.toFun si := by rw [hsi]; rfl
      _ = s := by simpa [si, feedbackEncode] using finPair_flatten_roundtrip s
  rw [← hflat]
  unfold FinKernel.compose
  rw [sumFin_product]
  calc
    sumFin c (fun next =>
        sumFin n (fun z =>
          adaptiveStep observe actions select update r
              (feedbackEncode node x) (finPairTransport.toFun (next, z)) *
            FinKernel.dirac (feedbackPhysical (n := n) (c := c))
              (finPairTransport.toFun (next, z)) y)) =
      sumFin n (fun z =>
        sumFin c (fun next =>
          adaptiveStep observe actions select update r
              (feedbackEncode node x) (finPairTransport.toFun (next, z)) *
            FinKernel.dirac (feedbackPhysical (n := n) (c := c))
              (finPairTransport.toFun (next, z)) y)) :=
        sumFin_swap c n (fun next z =>
          adaptiveStep observe actions select update r
              (feedbackEncode node x) (finPairTransport.toFun (next, z)) *
            FinKernel.dirac (feedbackPhysical (n := n) (c := c))
              (finPairTransport.toFun (next, z)) y)
    _ = sumFin n (fun z =>
          if z = y then actions (select r node (observe x)) x z else 0) := by
          apply sumFin_congr
          intro z
          by_cases hzy : z = y
          · subst z
            calc
              sumFin c (fun next =>
                  adaptiveStep observe actions select update r
                      (feedbackEncode node x) (finPairTransport.toFun (next, y)) *
                    FinKernel.dirac (feedbackPhysical (n := n) (c := c))
                      (finPairTransport.toFun (next, y)) y) =
                sumFin c (fun next =>
                  adaptiveStep observe actions select update r
                    (feedbackEncode node x) (feedbackEncode next y)) := by
                    apply sumFin_congr
                    intro next
                    simp [feedbackEncode, feedbackPhysical, FinKernel.dirac,
                      finPair_transport_roundtrip]
              _ = actions (select r node (observe x)) x y :=
                adaptiveStep_sum_next_nodes observe actions select update r node x y
              _ = (if y = y then actions (select r node (observe x)) x y else 0) := by
                simp
          · calc
              sumFin c (fun next =>
                  adaptiveStep observe actions select update r
                      (feedbackEncode node x) (finPairTransport.toFun (next, z)) *
                    FinKernel.dirac (feedbackPhysical (n := n) (c := c))
                      (finPairTransport.toFun (next, z)) y) =
                sumFin c (fun _ => (0 : Rat)) := by
                    apply sumFin_congr
                    intro next
                    have hyz : y ≠ z := by intro h; exact hzy h.symm
                    simp [feedbackPhysical, FinKernel.dirac,
                      finPair_transport_roundtrip, hyz]
              _ = 0 := sumFin_zero_values c
              _ = (if z = y then actions (select r node (observe x)) x z else 0) := by
                simp [hzy]
    _ = actions (select r node (observe x)) x y :=
      sumFin_single y (fun z => actions (select r node (observe x)) x z)
    _ = adaptivePhysicalResponse observe actions select r (feedbackEncode node x) y := by
      rw [adaptivePhysicalResponse_encoded]

/-- Any valid finite action family induces a valid adaptive augmented step. -/
theorem adaptiveStep_valid {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (r : Nat)
    (hvalid : ∀ a : Fin d, FinKernel.Valid (actions a)) :
    FinKernel.Valid (adaptiveStep observe actions select update r) := by
  constructor
  · intro s t
    let si : Fin c × Fin n := finPairTransport.invFun s
    let ti : Fin c × Fin n := finPairTransport.invFun t
    change 0 ≤
      if ti.1 = update r si.1 (observe si.2) (observe ti.2) then
        actions (select r si.1 (observe si.2)) si.2 ti.2
      else 0
    by_cases hnode : ti.1 = update r si.1 (observe si.2) (observe ti.2)
    · rw [if_pos hnode]
      exact (hvalid (select r si.1 (observe si.2))).1 si.2 ti.2
    · rw [if_neg hnode]
      exact Rat.le_refl
  · intro s
    let si : Fin c × Fin n := finPairTransport.invFun s
    rcases hsi : si with ⟨node, x⟩
    have hflat : feedbackEncode node x = s := by
      calc
        feedbackEncode node x = finPairTransport.toFun si := by rw [hsi]; rfl
        _ = s := by simpa [si, feedbackEncode] using finPair_flatten_roundtrip s
    rw [← hflat]
    unfold FinKernel.rowSum
    rw [sumFin_product]
    calc
      sumFin c (fun next =>
          sumFin n (fun y =>
            adaptiveStep observe actions select update r
              (feedbackEncode node x) (finPairTransport.toFun (next, y)))) =
        sumFin n (fun y =>
          sumFin c (fun next =>
            adaptiveStep observe actions select update r
              (feedbackEncode node x) (finPairTransport.toFun (next, y)))) :=
          sumFin_swap c n (fun next y =>
            adaptiveStep observe actions select update r
              (feedbackEncode node x) (finPairTransport.toFun (next, y)))
      _ = sumFin n (fun y =>
          actions (select r node (observe x)) x y) := by
            apply sumFin_congr
            intro y
            simpa [feedbackEncode] using
              adaptiveStep_sum_next_nodes observe actions select update r node x y
      _ = 1 := by
        have hrow := (hvalid (select r node (observe x))).2 x
        change sumFin n (fun y => actions (select r node (observe x)) x y) = 1 at hrow
        exact hrow

/-- The phase-indexed adaptive controller dynamics as an ordinary finite schedule. -/
def adaptiveSchedule {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c) :
    DirectionSchedule (c * n) :=
  fun r => adaptiveStep observe actions select update r

/-- Direct bounded adaptive-feedback path before the controller node is forgotten. -/
def adaptivePath {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (r : Nat) : FinKernel (c * n) (c * n) :=
  scheduledPath (adaptiveSchedule observe actions select update) r

/-- Direct bounded adaptive-feedback response from physical input with one initial node. -/
def adaptiveProjectedPath {n q c d : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (node0 : Fin c) (r : Nat) : FinKernel n n :=
  FinKernel.compose (FinKernel.dirac (feedbackPhysical (n := n) (c := c)))
    (FinKernel.compose (adaptivePath observe actions select update r)
      (FinKernel.dirac (feedbackEncode node0)))

/-- Initial deterministic interface: choose only the current controller node and phase zero. -/
def adaptiveInitial {n c k : Nat} (node0 : Fin c) :
    FinKernel n ((c * n) * (k + 1)) :=
  FinKernel.compose
    (FinKernel.dirac (phaseEmbed (n := c * n) (k := k) 0 (Nat.zero_le k)))
    (FinKernel.dirac (feedbackEncode node0))

/-- Terminal deterministic interface: forget phase and controller, retaining only physical state. -/
def adaptiveTerminal {n c k : Nat} :
    FinKernel ((c * n) * (k + 1)) n :=
  FinKernel.compose
    (FinKernel.dirac (feedbackPhysical (n := n) (c := c)))
    (FinKernel.dirac (physicalProject (n := c * n) (k := k)))

/-- One homogeneous finite kernel compiling the bounded online-feedback schedule. -/
def adaptiveCompiledStep {n q c d k : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c) :
    FinKernel ((c * n) * (k + 1)) ((c * n) * (k + 1)) :=
  serializedStep (k := k) (adaptiveSchedule observe actions select update)

/--
Main bounded adaptive-feedback theorem. One homogeneous augmented-state kernel
reproduces the direct finite online policy exactly; no complete future branch is
encoded at initialization.
-/
theorem bounded_adaptive_feedback_sequentialization {n q c d k : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (node0 : Fin c) :
    FinKernel.compose (adaptiveTerminal (n := n) (c := c) (k := k))
        (FinKernel.compose
          (kernelIterate
            (adaptiveCompiledStep (k := k) observe actions select update) k)
          (adaptiveInitial (n := n) (k := k) node0)) =
      adaptiveProjectedPath observe actions select update node0 k := by
  unfold adaptiveTerminal adaptiveInitial adaptiveCompiledStep adaptiveProjectedPath adaptivePath
  calc
    FinKernel.compose
        (FinKernel.compose
          (FinKernel.dirac (feedbackPhysical (n := n) (c := c)))
          (FinKernel.dirac (physicalProject (n := c * n) (k := k))))
        (FinKernel.compose
          (kernelIterate
            (serializedStep (k := k) (adaptiveSchedule observe actions select update)) k)
          (FinKernel.compose
            (FinKernel.dirac
              (phaseEmbed (n := c * n) (k := k) 0 (Nat.zero_le k)))
            (FinKernel.dirac (feedbackEncode node0)))) =
      FinKernel.compose (FinKernel.dirac (feedbackPhysical (n := n) (c := c)))
        (FinKernel.compose
          (FinKernel.compose
            (FinKernel.dirac (physicalProject (n := c * n) (k := k)))
            (FinKernel.compose
              (kernelIterate
                (serializedStep (k := k) (adaptiveSchedule observe actions select update)) k)
              (FinKernel.dirac
                (phaseEmbed (n := c * n) (k := k) 0 (Nat.zero_le k)))))
          (FinKernel.dirac (feedbackEncode node0))) := by
            simp only [finKernel_compose_associative]
    _ = FinKernel.compose (FinKernel.dirac (feedbackPhysical (n := n) (c := c)))
        (FinKernel.compose
          (scheduledPath (adaptiveSchedule observe actions select update) k)
          (FinKernel.dirac (feedbackEncode node0))) := by
          rw [bounded_multidirection_sequentialization]

/-- Common post-observation preserves the exact compiled/direct adaptive response equality. -/
theorem bounded_adaptive_feedback_observer_preserved {n q c d k z : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (node0 : Fin c) (obs : FinKernel n z) :
    FinKernel.compose obs
        (FinKernel.compose (adaptiveTerminal (n := n) (c := c) (k := k))
          (FinKernel.compose
            (kernelIterate
              (adaptiveCompiledStep (k := k) observe actions select update) k)
            (adaptiveInitial (n := n) (k := k) node0))) =
      FinKernel.compose obs
        (adaptiveProjectedPath observe actions select update node0 k) := by
  rw [bounded_adaptive_feedback_sequentialization observe actions select update node0]

/-- Valid actions imply a valid homogeneous adaptive-feedback compiler. -/
theorem adaptiveCompiledStep_valid {n q c d k : Nat}
    (observe : Fin n → Fin q)
    (actions : Fin d → FinKernel n n)
    (select : Nat → Fin c → Fin q → Fin d)
    (update : Nat → Fin c → Fin q → Fin q → Fin c)
    (hvalid : ∀ a : Fin d, FinKernel.Valid (actions a)) :
    FinKernel.Valid (adaptiveCompiledStep (k := k) observe actions select update) := by
  unfold adaptiveCompiledStep
  apply serializedStep_valid
  intro r _
  exact adaptiveStep_valid observe actions select update r hvalid

/-- The initial and terminal adaptive compiler interfaces are deterministic stochastic maps. -/
theorem adaptiveInterfaces_valid {n c k : Nat} (node0 : Fin c) :
    FinKernel.Valid (adaptiveInitial (n := n) (k := k) node0) ∧
    FinKernel.Valid (adaptiveTerminal (n := n) (c := c) (k := k)) := by
  constructor
  · unfold adaptiveInitial
    exact finKernel_compose_valid
      (finKernel_dirac_valid (feedbackEncode node0))
      (finKernel_dirac_valid
        (phaseEmbed (n := c * n) (k := k) 0 (Nat.zero_le k)))
  · unfold adaptiveTerminal
    exact finKernel_compose_valid
      (finKernel_dirac_valid (physicalProject (n := c * n) (k := k)))
      (finKernel_dirac_valid (feedbackPhysical (n := n) (c := c)))

/-- Identity observation for the smallest genuine online-selection control. -/
def feedbackObserve2 (x : Fin 2) : Fin 2 := x

/-- Two valid actions: identity for action zero and bit-flip for action one. -/
def feedbackActions2 (a : Fin 2) : FinKernel 2 2 :=
  if a = (0 : Fin 2) then FinKernel.identity 2 else FinKernel.dirac boundedFlip2

/-- Online policy: current observed zero selects identity; current observed one selects flip. -/
def feedbackSelect2 (_r : Nat) (_node : Fin 1) (o : Fin 2) : Fin 2 :=
  if o = (0 : Fin 2) then 0 else 1

/-- One-node controller; the generic theorem already permits arbitrary finite observation-dependent updates. -/
def feedbackUpdate1 (_r : Nat) (_node : Fin 1) (_oldObs _newObs : Fin 2) : Fin 1 := 0

theorem feedbackActions2_valid (a : Fin 2) : FinKernel.Valid (feedbackActions2 a) := by
  by_cases ha : a = (0 : Fin 2)
  · simp [feedbackActions2, ha]
    exact finKernel_identity_valid 2
  · simp [feedbackActions2, ha]
    exact finKernel_dirac_valid boundedFlip2

/-- The same policy really selects different actions from different realized observations. -/
theorem feedbackSelect2_observation_sensitive :
    feedbackSelect2 0 (0 : Fin 1) (0 : Fin 2) ≠
      feedbackSelect2 0 (0 : Fin 1) (1 : Fin 2) := by
  simp [feedbackSelect2]

/-- At observed one the online policy flips, differing observably from fixed identity behavior. -/
theorem feedback_online_choice_changes_response :
    adaptivePhysicalResponse feedbackObserve2 feedbackActions2 feedbackSelect2 0
        (feedbackEncode (0 : Fin 1) (1 : Fin 2)) (0 : Fin 2) = 1 ∧
    FinKernel.identity 2 (1 : Fin 2) (0 : Fin 2) = 0 := by
  constructor
  · simp [adaptivePhysicalResponse, feedbackEncode, feedbackObserve2,
      feedbackActions2, feedbackSelect2, boundedFlip2, FinKernel.dirac,
      finPair_transport_roundtrip]
  · simp [FinKernel.identity]

/-- The genuine online-feedback control itself compiles to one valid homogeneous kernel. -/
theorem feedback_online_positive_control :
    feedbackSelect2 0 (0 : Fin 1) (0 : Fin 2) ≠
        feedbackSelect2 0 (0 : Fin 1) (1 : Fin 2) ∧
    FinKernel.Valid
      (adaptiveCompiledStep (k := 2)
        feedbackObserve2 feedbackActions2 feedbackSelect2 feedbackUpdate1) ∧
    FinKernel.compose (adaptiveTerminal (n := 2) (c := 1) (k := 2))
        (FinKernel.compose
          (kernelIterate
            (adaptiveCompiledStep (k := 2)
              feedbackObserve2 feedbackActions2 feedbackSelect2 feedbackUpdate1) 2)
          (adaptiveInitial (n := 2) (k := 2) (0 : Fin 1))) =
      adaptiveProjectedPath
        feedbackObserve2 feedbackActions2 feedbackSelect2 feedbackUpdate1
        (0 : Fin 1) 2 := by
  refine ⟨feedbackSelect2_observation_sensitive, ?_, ?_⟩
  · exact adaptiveCompiledStep_valid
      feedbackObserve2 feedbackActions2 feedbackSelect2 feedbackUpdate1
      feedbackActions2_valid
  · exact bounded_adaptive_feedback_sequentialization
      feedbackObserve2 feedbackActions2 feedbackSelect2 feedbackUpdate1 (0 : Fin 1)

end RelayTheory
