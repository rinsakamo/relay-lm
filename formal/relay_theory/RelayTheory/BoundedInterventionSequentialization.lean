import RelayTheory.BoundedMultidirectionSequentializationValid

namespace RelayTheory

/-- A finite family of bounded intervention programs, each program supplying one schedule. -/
abbrev ProgramSchedule (n b : Nat) := Fin b → DirectionSchedule n

/-- Encode one program label together with one physical state. -/
def branchEncode {n b : Nat} (p : Fin b) (x : Fin n) : Fin (b * n) :=
  finPairTransport.toFun (p, x)

/-- Forget the program label and retain only the physical state. -/
def branchProject {n b : Nat} (x : Fin (b * n)) : Fin n :=
  (finPairTransport.invFun x).2

@[simp] theorem branchProject_branchEncode {n b : Nat} (p : Fin b) (x : Fin n) :
    branchProject (branchEncode p x) = x := by
  simp [branchProject, branchEncode, finPair_transport_roundtrip]

/--
Lift a physical kernel into one fixed program fibre. The program label is
preserved as ordinary finite state rather than interpreted as a temporal axis.
-/
def branchLift {n b : Nat} (p : Fin b) (f : FinKernel n n) :
    FinKernel n (b * n) :=
  fun x t =>
    let ti : Fin b × Fin n := finPairTransport.invFun t
    if ti.1 = p then f x ti.2 else 0

@[simp] theorem branchLift_encoded {n b : Nat} (p q : Fin b)
    (f : FinKernel n n) (x y : Fin n) :
    branchLift p f x (finPairTransport.toFun (q, y)) =
      if q = p then f x y else 0 := by
  simp [branchLift, finPair_transport_roundtrip]

/--
One schedule on the enlarged `program × physical` state simultaneously carries
all declared intervention programs. Each step preserves the program label and
uses the schedule selected by that label.
-/
def programmedSchedule {n b : Nat} (programs : ProgramSchedule n b) :
    DirectionSchedule (b * n) :=
  fun r s t =>
    let si : Fin b × Fin n := finPairTransport.invFun s
    let ti : Fin b × Fin n := finPairTransport.invFun t
    if ti.1 = si.1 then programs si.1 r si.2 ti.2 else 0

@[simp] theorem programmedSchedule_encoded {n b : Nat}
    (programs : ProgramSchedule n b) (r : Nat)
    (p q : Fin b) (x y : Fin n) :
    programmedSchedule programs r
        (finPairTransport.toFun (p, x))
        (finPairTransport.toFun (q, y)) =
      if q = p then programs p r x y else 0 := by
  simp [programmedSchedule, finPair_transport_roundtrip]

/-- The identity path in one program fibre is exactly the deterministic branch embedding. -/
theorem branchLift_identity_eq_dirac {n b : Nat} (p : Fin b) :
    branchLift p (FinKernel.identity n) = FinKernel.dirac (branchEncode p) := by
  funext x t
  let ti : Fin b × Fin n := finPairTransport.invFun t
  rcases hti : ti with ⟨q, y⟩
  have hflat : finPairTransport.toFun (q, y) = t := by
    calc
      finPairTransport.toFun (q, y) = finPairTransport.toFun ti := by rw [hti]
      _ = t := by simpa [ti] using finPair_flatten_roundtrip t
  rw [← hflat]
  by_cases hq : q = p
  · subst q
    by_cases hxy : x = y
    · subst y
      simp [branchLift, branchEncode, FinKernel.identity, FinKernel.dirac,
        finPair_transport_roundtrip]
    · have henc :
          finPairTransport.toFun (p, y) ≠ finPairTransport.toFun (p, x) := by
        intro h
        apply hxy
        have hpairs := bounded_finPairTransport_toFun_injective h
        exact (congrArg Prod.snd hpairs).symm
      simp [branchLift, branchEncode, FinKernel.identity, FinKernel.dirac,
        finPair_transport_roundtrip, hxy, henc]
  · have henc :
        finPairTransport.toFun (q, y) ≠ finPairTransport.toFun (p, x) := by
      intro h
      apply hq
      have hpairs := bounded_finPairTransport_toFun_injective h
      exact congrArg Prod.fst hpairs
    simp [branchLift, branchEncode, FinKernel.dirac,
      finPair_transport_roundtrip, hq, henc]

/--
One programmed step advances a kernel confined to branch `p` exactly by that
branch's selected physical kernel. Other program fibres remain inaccessible.
-/
theorem programmedSchedule_advance_branch {n b : Nat}
    (programs : ProgramSchedule n b) (r : Nat) (p : Fin b)
    (f : FinKernel n n) :
    FinKernel.compose (programmedSchedule programs r) (branchLift p f) =
      branchLift p (FinKernel.compose (programs p r) f) := by
  funext x t
  let ti : Fin b × Fin n := finPairTransport.invFun t
  rcases hti : ti with ⟨q, z⟩
  have hflat : finPairTransport.toFun (q, z) = t := by
    calc
      finPairTransport.toFun (q, z) = finPairTransport.toFun ti := by rw [hti]
      _ = t := by simpa [ti] using finPair_flatten_roundtrip t
  rw [← hflat]
  unfold FinKernel.compose
  rw [sumFin_product]
  calc
    sumFin b (fun j =>
        sumFin n (fun y =>
          branchLift p f x (finPairTransport.toFun (j, y)) *
            programmedSchedule programs r
              (finPairTransport.toFun (j, y))
              (finPairTransport.toFun (q, z)))) =
      sumFin b (fun j =>
        if j = p then
          sumFin n (fun y =>
            f x y * (if q = p then programs p r y z else 0))
        else 0) := by
          apply sumFin_congr
          intro j
          by_cases hj : j = p
          · subst j
            simp [branchLift_encoded, programmedSchedule_encoded]
          · simp [branchLift_encoded, programmedSchedule_encoded, hj]
            exact sumFin_zero_values n
    _ = sumFin n (fun y =>
          f x y * (if q = p then programs p r y z else 0)) :=
      sumFin_single p (fun _ =>
        sumFin n (fun y => f x y * (if q = p then programs p r y z else 0)))
    _ = (if q = p then FinKernel.compose (programs p r) f x z else 0) := by
      by_cases hqp : q = p
      · simp [hqp, FinKernel.compose]
      · simp [hqp, sumFin_zero_values]
    _ = branchLift p (FinKernel.compose (programs p r) f) x
          (finPairTransport.toFun (q, z)) := by
      simp [branchLift, finPair_transport_roundtrip]

/-- Every prefix of every declared program is carried by the same enlarged schedule. -/
theorem programmedPath_branch_lift {n b : Nat}
    (programs : ProgramSchedule n b) (p : Fin b) :
    ∀ r : Nat,
      FinKernel.compose (scheduledPath (programmedSchedule programs) r)
          (FinKernel.dirac (branchEncode p)) =
        branchLift p (scheduledPath (programs p) r) := by
  intro r
  induction r with
  | zero =>
      change FinKernel.compose (FinKernel.identity (b * n))
          (FinKernel.dirac (branchEncode p)) =
        branchLift p (FinKernel.identity n)
      rw [finKernel_compose_identity_after]
      exact (branchLift_identity_eq_dirac p).symm
  | succ r ih =>
      change FinKernel.compose
          (FinKernel.compose (programmedSchedule programs r)
            (scheduledPath (programmedSchedule programs) r))
          (FinKernel.dirac (branchEncode p)) =
        branchLift p
          (FinKernel.compose (programs p r) (scheduledPath (programs p) r))
      rw [← finKernel_compose_associative]
      rw [ih]
      exact programmedSchedule_advance_branch programs r p (scheduledPath (programs p) r)

/-- Forgetting the program label after a branch lift returns the physical kernel exactly. -/
theorem branchProject_after_branchLift {n b : Nat}
    (p : Fin b) (f : FinKernel n n) :
    FinKernel.compose (FinKernel.dirac (branchProject (n := n) (b := b)))
        (branchLift p f) = f := by
  funext x z
  unfold FinKernel.compose
  rw [sumFin_product]
  calc
    sumFin b (fun q =>
        sumFin n (fun y =>
          branchLift p f x (finPairTransport.toFun (q, y)) *
            FinKernel.dirac (branchProject (n := n) (b := b))
              (finPairTransport.toFun (q, y)) z)) =
      sumFin b (fun q =>
        if q = p then
          sumFin n (fun y => f x y * (if z = y then 1 else 0))
        else 0) := by
          apply sumFin_congr
          intro q
          by_cases hq : q = p
          · subst q
            simp [branchLift_encoded, FinKernel.dirac, branchProject,
              finPair_transport_roundtrip]
          · simp [branchLift_encoded, FinKernel.dirac, branchProject,
              finPair_transport_roundtrip, hq]
            exact sumFin_zero_values n
    _ = sumFin n (fun y => f x y * (if z = y then 1 else 0)) :=
      sumFin_single p (fun _ =>
        sumFin n (fun y => f x y * (if z = y then 1 else 0)))
    _ = sumFin n (fun y => if y = z then f x y else 0) := by
          apply sumFin_congr
          intro y
          by_cases hy : y = z
          · subst y
            simp
          · have hzy : z ≠ y := by intro h; exact hy h.symm
            simp [hy, hzy]
    _ = f x z := sumFin_single z (fun y => f x y)

/-- Every intervention program's exact path is recovered from the common enlarged schedule. -/
theorem programmedPath_branch_exact {n b : Nat}
    (programs : ProgramSchedule n b) (p : Fin b) (r : Nat) :
    FinKernel.compose (FinKernel.dirac (branchProject (n := n) (b := b)))
        (FinKernel.compose (scheduledPath (programmedSchedule programs) r)
          (FinKernel.dirac (branchEncode p))) =
      scheduledPath (programs p) r := by
  rw [programmedPath_branch_lift programs p r]
  exact branchProject_after_branchLift p (scheduledPath (programs p) r)

/-- Initial interface selecting program `p` and phase zero for the common compiler. -/
def interventionInitial {n b k : Nat} (p : Fin b) :
    FinKernel n ((b * n) * (k + 1)) :=
  FinKernel.compose
    (FinKernel.dirac (phaseEmbed (n := b * n) (k := k) 0 (Nat.zero_le k)))
    (FinKernel.dirac (branchEncode p))

/-- Terminal interface forgetting both phase and program registers. -/
def interventionTerminal {n b k : Nat} :
    FinKernel ((b * n) * (k + 1)) n :=
  FinKernel.compose
    (FinKernel.dirac (branchProject (n := n) (b := b)))
    (FinKernel.dirac (physicalProject (n := b * n) (k := k)))

/-- One homogeneous finite kernel shared by every declared intervention program. -/
def interventionCompiledStep {n b k : Nat} (programs : ProgramSchedule n b) :
    FinKernel ((b * n) * (k + 1)) ((b * n) * (k + 1)) :=
  serializedStep (k := k) (programmedSchedule programs)

/--
Main bounded branching theorem: one homogeneous augmented-state kernel reproduces
every declared finite intervention program exactly. Only the initial finite
program register differs between branches.
-/
theorem bounded_intervention_branch_sequentialization {n b k : Nat}
    (programs : ProgramSchedule n b) (p : Fin b) :
    FinKernel.compose (interventionTerminal (n := n) (b := b) (k := k))
        (FinKernel.compose
          (kernelIterate (interventionCompiledStep (k := k) programs) k)
          (interventionInitial (n := n) (k := k) p)) =
      scheduledPath (programs p) k := by
  unfold interventionTerminal interventionInitial interventionCompiledStep
  calc
    FinKernel.compose
        (FinKernel.compose
          (FinKernel.dirac (branchProject (n := n) (b := b)))
          (FinKernel.dirac (physicalProject (n := b * n) (k := k))))
        (FinKernel.compose
          (kernelIterate (serializedStep (k := k) (programmedSchedule programs)) k)
          (FinKernel.compose
            (FinKernel.dirac
              (phaseEmbed (n := b * n) (k := k) 0 (Nat.zero_le k)))
            (FinKernel.dirac (branchEncode p)))) =
      FinKernel.compose (FinKernel.dirac (branchProject (n := n) (b := b)))
        (FinKernel.compose
          (FinKernel.compose
            (FinKernel.dirac (physicalProject (n := b * n) (k := k)))
            (FinKernel.compose
              (kernelIterate (serializedStep (k := k) (programmedSchedule programs)) k)
              (FinKernel.dirac
                (phaseEmbed (n := b * n) (k := k) 0 (Nat.zero_le k)))))
          (FinKernel.dirac (branchEncode p))) := by
            simp only [finKernel_compose_associative]
    _ = FinKernel.compose (FinKernel.dirac (branchProject (n := n) (b := b)))
        (FinKernel.compose
          (scheduledPath (programmedSchedule programs) k)
          (FinKernel.dirac (branchEncode p))) := by
          rw [bounded_multidirection_sequentialization]
    _ = scheduledPath (programs p) k :=
      programmedPath_branch_exact programs p k

/-- Exact observer predictions are preserved for every branch by common postcomposition. -/
theorem bounded_intervention_observer_preserved {n b k q : Nat}
    (programs : ProgramSchedule n b) (p : Fin b) (obs : FinKernel n q) :
    FinKernel.compose obs
        (FinKernel.compose (interventionTerminal (n := n) (b := b) (k := k))
          (FinKernel.compose
            (kernelIterate (interventionCompiledStep (k := k) programs) k)
            (interventionInitial (n := n) (k := k) p))) =
      FinKernel.compose obs (scheduledPath (programs p) k) := by
  rw [bounded_intervention_branch_sequentialization programs p]

/-- The block-diagonal enlarged schedule is valid whenever every selected branch step is valid. -/
theorem programmedSchedule_valid {n b : Nat}
    (programs : ProgramSchedule n b) (r : Nat)
    (hvalid : ∀ p : Fin b, FinKernel.Valid (programs p r)) :
    FinKernel.Valid (programmedSchedule programs r) := by
  constructor
  · intro s t
    let si : Fin b × Fin n := finPairTransport.invFun s
    let ti : Fin b × Fin n := finPairTransport.invFun t
    change 0 ≤ if ti.1 = si.1 then programs si.1 r si.2 ti.2 else 0
    by_cases hp : ti.1 = si.1
    · rw [if_pos hp]
      exact (hvalid si.1).1 si.2 ti.2
    · rw [if_neg hp]
      exact Rat.le_refl
  · intro s
    let si : Fin b × Fin n := finPairTransport.invFun s
    rcases hsi : si with ⟨p, x⟩
    have hflat : finPairTransport.toFun (p, x) = s := by
      calc
        finPairTransport.toFun (p, x) = finPairTransport.toFun si := by rw [hsi]
        _ = s := by simpa [si] using finPair_flatten_roundtrip s
    rw [← hflat]
    unfold FinKernel.rowSum
    rw [sumFin_product]
    have hrow := (hvalid p).2 x
    change sumFin n (fun y => programs p r x y) = 1 at hrow
    calc
      sumFin b (fun q =>
          sumFin n (fun y =>
            programmedSchedule programs r
              (finPairTransport.toFun (p, x))
              (finPairTransport.toFun (q, y)))) =
        sumFin b (fun q =>
          if q = p then sumFin n (fun y => programs p r x y) else 0) := by
            apply sumFin_congr
            intro q
            by_cases hq : q = p
            · subst q
              simp [programmedSchedule_encoded]
            · simp [programmedSchedule_encoded, hq, sumFin_zero_values]
      _ = sumFin n (fun y => programs p r x y) :=
        sumFin_single p (fun _ => sumFin n (fun y => programs p r x y))
      _ = 1 := hrow

/-- The common homogeneous compiler is stochastic-valid when all branch steps are valid. -/
theorem interventionCompiledStep_valid {n b k : Nat}
    (programs : ProgramSchedule n b)
    (hvalid : ∀ (p : Fin b) (r : Nat), r < k → FinKernel.Valid (programs p r)) :
    FinKernel.Valid (interventionCompiledStep (k := k) programs) := by
  unfold interventionCompiledStep
  apply serializedStep_valid
  intro r hr
  exact programmedSchedule_valid programs r (fun p => hvalid p r hr)

/-- Program-selection and program-forgetting interfaces are deterministic and valid. -/
theorem intervention_interfaces_valid {n b k : Nat} (p : Fin b) :
    FinKernel.Valid (interventionInitial (n := n) (k := k) p) ∧
    FinKernel.Valid (interventionTerminal (n := n) (b := b) (k := k)) := by
  constructor
  · unfold interventionInitial
    exact finKernel_compose_valid
      (finKernel_dirac_valid (branchEncode p))
      (finKernel_dirac_valid
        (phaseEmbed (n := b * n) (k := k) 0 (Nat.zero_le k)))
  · unfold interventionTerminal
    exact finKernel_compose_valid
      (finKernel_dirac_valid (physicalProject (n := b * n) (k := k)))
      (finKernel_dirac_valid (branchProject (n := n) (b := b)))

/-- Reverse ordering of the existing noncommuting two-step positive control. -/
def boundedReverseNoncommutingSchedule2 : DirectionSchedule 2 :=
  fun r => if r = 0 then FinKernel.dirac boundedFlip2 else FinKernel.dirac boundedZero2

theorem boundedReverseNoncommutingSchedule2_valid (r : Nat) :
    FinKernel.Valid (boundedReverseNoncommutingSchedule2 r) := by
  by_cases hr : r = 0
  · simp [boundedReverseNoncommutingSchedule2, hr]
    exact finKernel_dirac_valid boundedFlip2
  · simp [boundedReverseNoncommutingSchedule2, hr]
    exact finKernel_dirac_valid boundedZero2

/-- Two alternative intervention programs encode the two noncommuting orderings. -/
def boundedTwoBranchPrograms : ProgramSchedule 2 2 :=
  fun p => if p = (0 : Fin 2) then
    boundedNoncommutingSchedule2 else boundedReverseNoncommutingSchedule2

theorem boundedTwoBranchPrograms_valid (p : Fin 2) (r : Nat) :
    FinKernel.Valid (boundedTwoBranchPrograms p r) := by
  by_cases hp : p = (0 : Fin 2)
  · subst p
    simp [boundedTwoBranchPrograms]
    exact boundedNoncommutingSchedule2_valid r
  · simp [boundedTwoBranchPrograms, hp]
    exact boundedReverseNoncommutingSchedule2_valid r

/--
Positive control: genuinely order-sensitive programs are both reproduced by the
same homogeneous augmented process; the only branch selector is finite state.
-/
theorem bounded_two_branch_noncommuting_same_compiler :
    FinKernel.compose (FinKernel.dirac boundedFlip2) (FinKernel.dirac boundedZero2) ≠
        FinKernel.compose (FinKernel.dirac boundedZero2) (FinKernel.dirac boundedFlip2) ∧
    (∀ p : Fin 2,
      FinKernel.compose (interventionTerminal (n := 2) (b := 2) (k := 2))
          (FinKernel.compose
            (kernelIterate (interventionCompiledStep (k := 2) boundedTwoBranchPrograms) 2)
            (interventionInitial (n := 2) (k := 2) p)) =
        scheduledPath (boundedTwoBranchPrograms p) 2) ∧
    FinKernel.Valid (interventionCompiledStep (k := 2) boundedTwoBranchPrograms) := by
  refine ⟨bounded_directions_noncommute, ?_, ?_⟩
  · intro p
    exact bounded_intervention_branch_sequentialization boundedTwoBranchPrograms p
  · exact interventionCompiledStep_valid boundedTwoBranchPrograms
      (fun p r _ => boundedTwoBranchPrograms_valid p r)

end RelayTheory
