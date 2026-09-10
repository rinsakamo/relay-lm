import RelayTheory.BoundedMultidirectionSequentialization

namespace RelayTheory

/--
If every schedule entry used before the finite horizon is stochastic-valid, the
single homogeneous serialized step is itself stochastic-valid on the augmented
finite state space.
-/
theorem serializedStep_valid {n k : Nat} (schedule : DirectionSchedule n)
    (hschedule : ∀ r : Nat, r < k → FinKernel.Valid (schedule r)) :
    FinKernel.Valid (serializedStep (k := k) schedule) := by
  constructor
  · intro s t
    let si := finPairTransport.invFun s
    let ti := finPairTransport.invFun t
    change 0 ≤
      if _h : si.2.1 < k then
        if ti.2.1 = si.2.1 + 1 then schedule si.2.1 si.1 ti.1 else 0
      else
        if ti = si then 1 else 0
    by_cases hactive : si.2.1 < k
    · rw [dif_pos hactive]
      by_cases hphase : ti.2.1 = si.2.1 + 1
      · rw [if_pos hphase]
        exact (hschedule si.2.1 hactive).1 si.1 ti.1
      · rw [if_neg hphase]
        exact Rat.le_refl
    · rw [dif_neg hactive]
      by_cases heq : ti = si
      · rw [if_pos heq]
        exact rat_zero_le_one
      · rw [if_neg heq]
        exact Rat.le_refl
  · intro s
    let si := finPairTransport.invFun s
    rcases hsi : si with ⟨x, p⟩
    have hflat : finPairTransport.toFun (x, p) = s := by
      calc
        finPairTransport.toFun (x, p) = finPairTransport.toFun si := by rw [hsi]
        _ = s := by simpa [si] using finPair_flatten_roundtrip s
    rw [← hflat]
    unfold FinKernel.rowSum
    rw [sumFin_product]
    by_cases hp : p.1 < k
    · have hsrow := (hschedule p.1 hp).2 x
      change sumFin n (fun y => schedule p.1 x y) = 1 at hsrow
      calc
        sumFin n (fun y =>
            sumFin (k + 1) (fun q =>
              serializedStep (k := k) schedule
                (finPairTransport.toFun (x, p))
                (finPairTransport.toFun (y, q)))) =
          sumFin n (fun y =>
            sumFin (k + 1) (fun q =>
              if q.1 = p.1 + 1 then schedule p.1 x y else 0)) := by
                apply sumFin_congr
                intro y
                apply sumFin_congr
                intro q
                simp [serializedStep, finPair_transport_roundtrip, hp]
        _ = sumFin n (fun y => schedule p.1 x y) := by
              apply sumFin_congr
              intro y
              let pn : Fin (k + 1) := phaseIndex k (p.1 + 1) (by grind)
              calc
                sumFin (k + 1) (fun q =>
                    if q.1 = p.1 + 1 then schedule p.1 x y else 0) =
                  sumFin (k + 1) (fun q =>
                    if q = pn then schedule p.1 x y else 0) := by
                      apply sumFin_congr
                      intro q
                      by_cases hq : q = pn
                      · subst q
                        simp [pn, phaseIndex]
                      · have hqv : q.1 ≠ p.1 + 1 := by
                          intro hv
                          apply hq
                          apply Fin.eq_of_val_eq
                          simpa [pn, phaseIndex] using hv
                        simp [hq, hqv]
                _ = schedule p.1 x y :=
                  sumFin_single pn (fun _ => schedule p.1 x y)
        _ = 1 := hsrow
    · calc
        sumFin n (fun y =>
            sumFin (k + 1) (fun q =>
              serializedStep (k := k) schedule
                (finPairTransport.toFun (x, p))
                (finPairTransport.toFun (y, q)))) =
          sumFin n (fun y =>
            sumFin (k + 1) (fun q =>
              if (y, q) = (x, p) then 1 else 0)) := by
                apply sumFin_congr
                intro y
                apply sumFin_congr
                intro q
                simp [serializedStep, finPair_transport_roundtrip, hp]
        _ = sumFin n (fun y => if y = x then 1 else 0) := by
              apply sumFin_congr
              intro y
              by_cases hy : y = x
              · subst y
                simpa using (sumFin_single p (fun _ => (1 : Rat)))
              · calc
                  sumFin (k + 1) (fun q =>
                      if (y, q) = (x, p) then 1 else 0) =
                    sumFin (k + 1) (fun _ => (0 : Rat)) := by
                      apply sumFin_congr
                      intro q
                      simp [hy]
                  _ = 0 := sumFin_zero_values (k + 1)
                  _ = (if y = x then 1 else 0) := by simp [hy]
        _ = 1 := sumFin_single x (fun _ => (1 : Rat))

/-- Iterating one stochastic-valid homogeneous finite kernel preserves validity. -/
theorem kernelIterate_valid {n : Nat} {step : FinKernel n n}
    (hstep : FinKernel.Valid step) :
    ∀ r : Nat, FinKernel.Valid (kernelIterate step r)
  | 0 => finKernel_identity_valid n
  | Nat.succ r => finKernel_compose_valid (kernelIterate_valid hstep r) hstep

/-- Every valid prefix of a valid finite schedule remains stochastic-valid. -/
theorem scheduledPath_valid_prefix {n k : Nat} (schedule : DirectionSchedule n)
    (hschedule : ∀ r : Nat, r < k → FinKernel.Valid (schedule r)) :
    ∀ (r : Nat), r ≤ k → FinKernel.Valid (scheduledPath schedule r) := by
  intro r
  induction r with
  | zero =>
      intro _
      exact finKernel_identity_valid n
  | succ r ih =>
      intro hr
      have hrlt : r < k := by grind
      exact finKernel_compose_valid (ih (by grind)) (hschedule r hrlt)

/--
Stochastic-valid bounded sequentialization: the compiled one-time step and the
resulting horizon path are both normalized exact stochastic kernels.
-/
theorem bounded_multidirection_sequentialization_valid {n k : Nat}
    (schedule : DirectionSchedule n)
    (hschedule : ∀ r : Nat, r < k → FinKernel.Valid (schedule r)) :
    FinKernel.Valid (serializedStep (k := k) schedule) ∧
    FinKernel.Valid (scheduledPath schedule k) := by
  exact ⟨serializedStep_valid schedule hschedule,
    scheduledPath_valid_prefix schedule hschedule k (Nat.le_refl k)⟩

/-- Two deterministic directions on `Fin 2` used as a noncommuting control. -/
def boundedFlip2 (x : Fin 2) : Fin 2 :=
  if x = (0 : Fin 2) then 1 else 0

def boundedZero2 (_ : Fin 2) : Fin 2 := 0

/-- The two deterministic directions genuinely fail to commute. -/
theorem bounded_directions_noncommute :
    FinKernel.compose (FinKernel.dirac boundedFlip2) (FinKernel.dirac boundedZero2) ≠
      FinKernel.compose (FinKernel.dirac boundedZero2) (FinKernel.dirac boundedFlip2) := by
  intro h
  have hv := congrArg (fun q => q (0 : Fin 2) (0 : Fin 2)) h
  rw [finKernel_dirac_compose, finKernel_dirac_compose] at hv
  simp [FinKernel.dirac, boundedFlip2, boundedZero2] at hv

/-- A two-step schedule containing the noncommuting directions. -/
def boundedNoncommutingSchedule2 : DirectionSchedule 2 :=
  fun r => if r = 0 then FinKernel.dirac boundedZero2 else FinKernel.dirac boundedFlip2

theorem boundedNoncommutingSchedule2_valid (r : Nat) :
    FinKernel.Valid (boundedNoncommutingSchedule2 r) := by
  by_cases hr : r = 0
  · simp [boundedNoncommutingSchedule2, hr]
    exact finKernel_dirac_valid boundedZero2
  · simp [boundedNoncommutingSchedule2, hr]
    exact finKernel_dirac_valid boundedFlip2

/--
Positive control: noncommutativity of the original direction maps does not
obstruct exact stochastic-valid serialization of their fixed finite schedule.
-/
theorem bounded_noncommuting_positive_control :
    FinKernel.compose (FinKernel.dirac boundedFlip2) (FinKernel.dirac boundedZero2) ≠
        FinKernel.compose (FinKernel.dirac boundedZero2) (FinKernel.dirac boundedFlip2) ∧
    FinKernel.Valid (serializedStep (k := 2) boundedNoncommutingSchedule2) ∧
    FinKernel.compose (FinKernel.dirac (physicalProject (n := 2) (k := 2)))
        (FinKernel.compose (kernelIterate (serializedStep (k := 2) boundedNoncommutingSchedule2) 2)
          (FinKernel.dirac (phaseEmbed (n := 2) (k := 2) 0 (Nat.zero_le 2)))) =
      scheduledPath boundedNoncommutingSchedule2 2 := by
  refine ⟨bounded_directions_noncommute, ?_, ?_⟩
  · exact serializedStep_valid boundedNoncommutingSchedule2
      (fun r _ => boundedNoncommutingSchedule2_valid r)
  · exact bounded_multidirection_sequentialization boundedNoncommutingSchedule2

end RelayTheory