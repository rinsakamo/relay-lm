import Lean.Elab.Tactic.Grind
import RelayTheory.GenericTensorKernel

namespace RelayTheory

/--
A finite-horizon evolution schedule. Only the first `k` entries are operationally
relevant to a horizon-`k` serialization; using `Nat` here keeps the theorem
about finite path semantics rather than about a particular word encoding.
-/
abbrev DirectionSchedule (n : Nat) := Nat → FinKernel n n

/-- Ordered exact path semantics: step `0`, then step `1`, and so on. -/
def scheduledPath {n : Nat} (schedule : DirectionSchedule n) : Nat → FinKernel n n
  | 0 => FinKernel.identity n
  | Nat.succ r => FinKernel.compose (schedule r) (scheduledPath schedule r)

/-- Exact iteration of one time-homogeneous finite kernel. -/
def kernelIterate {n : Nat} (step : FinKernel n n) : Nat → FinKernel n n
  | 0 => FinKernel.identity n
  | Nat.succ r => FinKernel.compose step (kernelIterate step r)

/-- The phase `r` inside a horizon `k`, including the terminal phase `k`. -/
def phaseIndex (k r : Nat) (_hr : r ≤ k) : Fin (k + 1) :=
  ⟨r, by grind⟩

@[simp] theorem phaseIndex_val (k r : Nat) (hr : r ≤ k) :
    (phaseIndex k r hr).1 = r := rfl

/-- The constructive product encoding is injective because it has an exact inverse. -/
theorem finPairTransport_toFun_injective {m n : Nat} :
    Function.Injective (finPairTransport (m := m) (n := n)).toFun := by
  intro a b h
  have h' := congrArg (finPairTransport (m := m) (n := n)).invFun h
  simpa only [finPair_transport_roundtrip] using h'

/-- Embed a physical state into one declared phase of the augmented finite state. -/
def phaseEmbed {n k : Nat} (r : Nat) (hr : r ≤ k) :
    Fin n → Fin (n * (k + 1)) :=
  fun x => finPairTransport.toFun (x, phaseIndex k r hr)

/-- Forget the finite phase register and retain only the physical state. -/
def physicalProject {n k : Nat} : Fin (n * (k + 1)) → Fin n :=
  fun x => (finPairTransport.invFun x).1

@[simp] theorem physicalProject_phaseEmbed {n k r : Nat} (hr : r ≤ k) (x : Fin n) :
    physicalProject (phaseEmbed r hr x) = x := by
  simp [physicalProject, phaseEmbed, finPair_transport_roundtrip]

/--
Lift an arbitrary exact physical kernel into a single phase layer. It may be
sub-stochastic away from the selected phase; it is proof apparatus for tracking
the unique phase occupied by a serialized run.
-/
def phaseKernel {n k : Nat} (r : Nat) (_hr : r ≤ k) (f : FinKernel n n) :
    FinKernel n (n * (k + 1)) :=
  fun x y =>
    let yi := finPairTransport.invFun y
    if yi.2.1 = r then f x yi.1 else 0

@[simp] theorem phaseKernel_encoded {n k r : Nat} (hr : r ≤ k)
    (f : FinKernel n n) (x y : Fin n) (p : Fin (k + 1)) :
    phaseKernel r hr f x (finPairTransport.toFun (y, p)) =
      if p.1 = r then f x y else 0 := by
  simp [phaseKernel, finPair_transport_roundtrip]

/--
One homogeneous exact kernel that serializes the first `k` schedule entries.
At nonterminal phase `p < k` it applies `schedule p` and increments the phase.
The terminal phase self-loops exactly.
-/
def serializedStep {n k : Nat} (schedule : DirectionSchedule n) :
    FinKernel (n * (k + 1)) (n * (k + 1)) :=
  fun s t =>
    let si := finPairTransport.invFun s
    let ti := finPairTransport.invFun t
    if _h : si.2.1 < k then
      if ti.2.1 = si.2.1 + 1 then schedule si.2.1 si.1 ti.1 else 0
    else
      if ti = si then 1 else 0

/-- Active-phase evaluation of the serialized kernel on encoded pairs. -/
theorem serializedStep_encoded_active {n k r : Nat}
    (schedule : DirectionSchedule n) (hr : r < k)
    (x y : Fin n) (q : Fin (k + 1)) :
    serializedStep schedule
        (phaseEmbed r (Nat.le_of_lt hr) x)
        (finPairTransport.toFun (y, q)) =
      if q.1 = r + 1 then schedule r x y else 0 := by
  simp [serializedStep, phaseEmbed, phaseIndex, finPair_transport_roundtrip, hr]

/-- The phase-zero identity layer is exactly the deterministic initial embedding. -/
theorem phaseKernel_zero_identity_eq_dirac {n k : Nat} :
    phaseKernel 0 (Nat.zero_le k) (FinKernel.identity n) =
      FinKernel.dirac (phaseEmbed 0 (Nat.zero_le k)) := by
  funext x t
  have hencoded : ∀ (y : Fin n) (p : Fin (k + 1)),
      phaseKernel 0 (Nat.zero_le k) (FinKernel.identity n) x
          (finPairTransport.toFun (y, p)) =
        FinKernel.dirac (phaseEmbed 0 (Nat.zero_le k)) x
          (finPairTransport.toFun (y, p)) := by
    intro y p
    rw [phaseKernel_encoded]
    by_cases hp : p.1 = 0
    · have hp0 : p = phaseIndex k 0 (Nat.zero_le k) := by
        apply Fin.eq_of_val_eq
        simpa [phaseIndex] using hp
      subst p
      by_cases hxy : x = y
      · subst y
        simp [FinKernel.identity, FinKernel.dirac, phaseEmbed, phaseIndex]
      · have hencZero :
            finPairTransport.toFun (y, (0 : Fin (k + 1))) ≠
              finPairTransport.toFun (x, (0 : Fin (k + 1))) := by
          intro h
          apply hxy
          exact (congrArg Prod.fst (finPairTransport_toFun_injective h)).symm
        simp [FinKernel.identity, FinKernel.dirac, phaseEmbed, phaseIndex, hxy, hencZero]
    · have hp0 : p ≠ phaseIndex k 0 (Nat.zero_le k) := by
        intro h
        apply hp
        simpa [phaseIndex] using congrArg Fin.val h
      have henc :
          finPairTransport.toFun (y, p) ≠ phaseEmbed 0 (Nat.zero_le k) x := by
        intro h
        apply hp0
        have hpair := congrArg finPairTransport.invFun h
        have hpair' : (y, p) = (x, phaseIndex k 0 (Nat.zero_le k)) := by
          simpa [phaseEmbed, finPair_transport_roundtrip] using hpair
        exact congrArg Prod.snd hpair'
      simp [hp, FinKernel.dirac, henc]
  let ti := finPairTransport.invFun t
  rcases hti : ti with ⟨y, p⟩
  have h := hencoded y p
  have hflat : finPairTransport.toFun (y, p) = t := by
    calc
      finPairTransport.toFun (y, p) = finPairTransport.toFun ti := by rw [hti]
      _ = t := by simpa [ti] using finPair_flatten_roundtrip t
  rw [hflat] at h
  exact h

/--
A single serialized step advances an exact kernel carried entirely at phase `r`
to phase `r+1`, applying exactly schedule entry `r` to the physical state.
-/
theorem serializedStep_advance_phase {n k r : Nat}
    (schedule : DirectionSchedule n) (hr : r < k) (f : FinKernel n n) :
    FinKernel.compose (serializedStep schedule)
        (phaseKernel r (Nat.le_of_lt hr) f) =
      phaseKernel (r + 1) (by grind) (FinKernel.compose (schedule r) f) := by
  funext x t
  have hencoded : ∀ (z : Fin n) (q : Fin (k + 1)),
      FinKernel.compose (serializedStep schedule)
          (phaseKernel r (Nat.le_of_lt hr) f) x
          (finPairTransport.toFun (z, q)) =
        phaseKernel (r + 1) (by grind) (FinKernel.compose (schedule r) f) x
          (finPairTransport.toFun (z, q)) := by
    intro z q
    unfold FinKernel.compose
    rw [sumFin_product]
    have hphase :
        ∀ y : Fin n,
          sumFin (k + 1) (fun p =>
            phaseKernel r (Nat.le_of_lt hr) f x (finPairTransport.toFun (y, p)) *
              serializedStep schedule (finPairTransport.toFun (y, p))
                (finPairTransport.toFun (z, q))) =
          f x y * serializedStep schedule
            (phaseEmbed r (Nat.le_of_lt hr) y)
            (finPairTransport.toFun (z, q)) := by
      intro y
      let pr : Fin (k + 1) := phaseIndex k r (Nat.le_of_lt hr)
      calc
        sumFin (k + 1) (fun p =>
            phaseKernel r (Nat.le_of_lt hr) f x (finPairTransport.toFun (y, p)) *
              serializedStep schedule (finPairTransport.toFun (y, p))
                (finPairTransport.toFun (z, q))) =
          sumFin (k + 1) (fun p =>
            if p = pr then
              f x y * serializedStep schedule (finPairTransport.toFun (y, p))
                (finPairTransport.toFun (z, q))
            else 0) := by
              apply sumFin_congr
              intro p
              by_cases hp : p = pr
              · subst p
                simp [phaseKernel_encoded, pr, phaseIndex]
              · have hv : p.1 ≠ r := by
                  intro hv
                  apply hp
                  apply Fin.eq_of_val_eq
                  simpa [pr, phaseIndex] using hv
                simp [phaseKernel_encoded, hv, hp]
        _ = f x y * serializedStep schedule
            (finPairTransport.toFun (y, pr))
            (finPairTransport.toFun (z, q)) :=
              sumFin_single pr (fun p =>
                f x y * serializedStep schedule (finPairTransport.toFun (y, p))
                  (finPairTransport.toFun (z, q)))
        _ = f x y * serializedStep schedule
            (phaseEmbed r (Nat.le_of_lt hr) y)
            (finPairTransport.toFun (z, q)) := by
              rfl
    calc
      sumFin n (fun y =>
          sumFin (k + 1) (fun p =>
            phaseKernel r (Nat.le_of_lt hr) f x (finPairTransport.toFun (y, p)) *
              serializedStep schedule (finPairTransport.toFun (y, p))
                (finPairTransport.toFun (z, q)))) =
        sumFin n (fun y =>
          f x y * serializedStep schedule
            (phaseEmbed r (Nat.le_of_lt hr) y)
            (finPairTransport.toFun (z, q))) := by
          apply sumFin_congr
          intro y
          exact hphase y
      _ = sumFin n (fun y =>
            f x y * (if q.1 = r + 1 then schedule r y z else 0)) := by
            apply sumFin_congr
            intro y
            rw [serializedStep_encoded_active schedule hr y z q]
      _ = (if q.1 = r + 1 then
            FinKernel.compose (schedule r) f x z else 0) := by
            by_cases hq : q.1 = r + 1
            · simp [hq, FinKernel.compose]
            · simp [hq, sumFin_zero_values]
      _ = phaseKernel (r + 1) (by grind) (FinKernel.compose (schedule r) f) x
            (finPairTransport.toFun (z, q)) := by
            simp [phaseKernel_encoded]
  let ti := finPairTransport.invFun t
  rcases hti : ti with ⟨z, q⟩
  have h := hencoded z q
  have hflat : finPairTransport.toFun (z, q) = t := by
    calc
      finPairTransport.toFun (z, q) = finPairTransport.toFun ti := by rw [hti]
      _ = t := by simpa [ti] using finPair_flatten_roundtrip t
  rw [hflat] at h
  exact h

/-- Exact serialization theorem at every prefix of a fixed finite horizon. -/
theorem serialized_prefix {n k : Nat} (schedule : DirectionSchedule n) :
    ∀ (r : Nat) (hr : r ≤ k),
      FinKernel.compose (kernelIterate (serializedStep schedule) r)
          (FinKernel.dirac (phaseEmbed 0 (Nat.zero_le k))) =
        phaseKernel r hr (scheduledPath schedule r) := by
  intro r
  induction r with
  | zero =>
      intro hr
      rw [show kernelIterate (serializedStep schedule) 0 =
        FinKernel.identity (n * (k + 1)) from rfl]
      rw [finKernel_compose_identity_after]
      exact phaseKernel_zero_identity_eq_dirac.symm
  | succ r ih =>
      intro hsucc
      have hrlt : r < k := by grind
      have hrle : r ≤ k := Nat.le_of_lt hrlt
      change FinKernel.compose
          (FinKernel.compose (serializedStep schedule)
            (kernelIterate (serializedStep schedule) r))
          (FinKernel.dirac (phaseEmbed 0 (Nat.zero_le k))) = _
      rw [← finKernel_compose_associative]
      rw [ih hrle]
      rw [serializedStep_advance_phase schedule hrlt (scheduledPath schedule r)]
      rfl

/-- Terminal physical projection erases the phase lift and returns its kernel exactly. -/
theorem physicalProject_after_phaseKernel {n k : Nat} (f : FinKernel n n) :
    FinKernel.compose (FinKernel.dirac (physicalProject (n := n) (k := k)))
        (phaseKernel k (Nat.le_refl k) f) = f := by
  funext x z
  unfold FinKernel.compose
  rw [sumFin_product]
  calc
    sumFin n (fun y =>
        sumFin (k + 1) (fun p =>
          phaseKernel k (Nat.le_refl k) f x (finPairTransport.toFun (y, p)) *
            FinKernel.dirac (physicalProject (n := n) (k := k))
              (finPairTransport.toFun (y, p)) z)) =
      sumFin n (fun y =>
        sumFin (k + 1) (fun p =>
          (if p.1 = k then f x y else 0) * (if z = y then 1 else 0))) := by
          apply sumFin_congr
          intro y
          apply sumFin_congr
          intro p
          simp [phaseKernel_encoded, FinKernel.dirac, physicalProject,
            finPair_transport_roundtrip]
    _ = sumFin n (fun y => f x y * (if z = y then 1 else 0)) := by
          apply sumFin_congr
          intro y
          let pk : Fin (k + 1) := phaseIndex k k (Nat.le_refl k)
          calc
            sumFin (k + 1) (fun p =>
                (if p.1 = k then f x y else 0) * (if z = y then 1 else 0)) =
              sumFin (k + 1) (fun p =>
                if p = pk then f x y * (if z = y then 1 else 0) else 0) := by
                  apply sumFin_congr
                  intro p
                  by_cases hp : p = pk
                  · subst p
                    simp [pk, phaseIndex]
                  · have hv : p.1 ≠ k := by
                      intro hv
                      apply hp
                      apply Fin.eq_of_val_eq
                      simpa [pk, phaseIndex] using hv
                    simp [hv, hp]
            _ = f x y * (if z = y then 1 else 0) :=
              sumFin_single pk (fun _ => f x y * (if z = y then 1 else 0))
    _ = sumFin n (fun y => if y = z then f x y else 0) := by
          apply sumFin_congr
          intro y
          by_cases hy : y = z
          · subst y
            simp
          · have hzy : z ≠ y := by intro h; exact hy h.symm
            simp [hy, hzy]
    _ = f x z := sumFin_single z (fun y => f x y)

/--
Any fixed finite schedule is reproduced exactly by one homogeneous kernel on a
finite state augmentation, followed by a deterministic phase-forgetting map.
-/
theorem bounded_multidirection_sequentialization {n k : Nat}
    (schedule : DirectionSchedule n) :
    FinKernel.compose (FinKernel.dirac (physicalProject (n := n) (k := k)))
        (FinKernel.compose (kernelIterate (serializedStep schedule) k)
          (FinKernel.dirac (phaseEmbed 0 (Nat.zero_le k)))) =
      scheduledPath schedule k := by
  rw [serialized_prefix schedule k (Nat.le_refl k)]
  exact physicalProject_after_phaseKernel (scheduledPath schedule k)

end RelayTheory