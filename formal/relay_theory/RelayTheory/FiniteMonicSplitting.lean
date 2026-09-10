import RelayTheory.FinitePivot

namespace RelayTheory

/-- Pull a scalar appearing on the right factor through a finite product sum. -/
theorem sumFin_product_scale_right (n : Nat) (c : Rat)
    (f g : Fin n → Rat) :
    sumFin n (fun i => f i * (c * g i)) =
      c * sumFin n (fun i => f i * g i) := by
  calc
    sumFin n (fun i => f i * (c * g i)) =
        sumFin n (fun i => c * (f i * g i)) := by
          apply sumFin_congr
          intro i
          grind
    _ = c * sumFin n (fun i => f i * g i) :=
      sumFin_mul_left n c (fun i => f i * g i)

/--
Lower recovery columns induced by a recovery of the scaled pivot block.  The
head coefficient cancels row-zero leakage; every tail coefficient is scaled by
the pivot so no division is needed here.
-/
def finKernelPivotLowerRecovery {a q : Nat}
    (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) : FinKernel (Nat.succ q) a :=
  fun y i =>
    Fin.cases
      (- sumFin q (fun j => obs 0 j.succ * recoveryB j i))
      (fun j => obs 0 0 * recoveryB j i)
      y

@[simp] theorem finKernelPivotLowerRecovery_zero
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) (i : Fin a) :
    finKernelPivotLowerRecovery obs recoveryB 0 i =
      - sumFin q (fun j => obs 0 j.succ * recoveryB j i) := by
  rfl

@[simp] theorem finKernelPivotLowerRecovery_succ
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) (j : Fin q) (i : Fin a) :
    finKernelPivotLowerRecovery obs recoveryB j.succ i =
      obs 0 0 * recoveryB j i := by
  rfl

/-- Every lower recovery column annihilates source row zero. -/
theorem finKernelPivotLowerRecovery_compose_zero
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) (i : Fin a) :
    FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs 0 i = 0 := by
  unfold FinKernel.compose
  rw [sumFin_succ, finKernelPivotLowerRecovery_zero]
  have htail :
      sumFin q (fun j =>
        obs 0 j.succ * finKernelPivotLowerRecovery obs recoveryB j.succ i) =
      obs 0 0 * sumFin q (fun j => obs 0 j.succ * recoveryB j i) := by
    calc
      sumFin q (fun j =>
          obs 0 j.succ * finKernelPivotLowerRecovery obs recoveryB j.succ i) =
        sumFin q (fun j =>
          obs 0 j.succ * (obs 0 0 * recoveryB j i)) := by
            apply sumFin_congr
            intro j
            rw [finKernelPivotLowerRecovery_succ]
      _ = obs 0 0 * sumFin q (fun j => obs 0 j.succ * recoveryB j i) :=
        sumFin_product_scale_right q (obs 0 0)
          (fun j => obs 0 j.succ) (fun j => recoveryB j i)
  rw [htail]
  grind

/--
For a nonzero source row, a lower recovery column through the original pivoted
kernel equals the corresponding recovery composite through the scaled block.
-/
theorem finKernelPivotLowerRecovery_compose_succ_formula
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) (x i : Fin a) :
    FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs x.succ i =
      FinKernel.compose recoveryB (finKernelPivotBlock obs) x i := by
  have htail :
      sumFin q (fun j =>
        obs x.succ j.succ * finKernelPivotLowerRecovery obs recoveryB j.succ i) =
      obs 0 0 * sumFin q (fun j => obs x.succ j.succ * recoveryB j i) := by
    calc
      sumFin q (fun j =>
          obs x.succ j.succ * finKernelPivotLowerRecovery obs recoveryB j.succ i) =
        sumFin q (fun j =>
          obs x.succ j.succ * (obs 0 0 * recoveryB j i)) := by
            apply sumFin_congr
            intro j
            rw [finKernelPivotLowerRecovery_succ]
      _ = obs 0 0 * sumFin q (fun j => obs x.succ j.succ * recoveryB j i) :=
        sumFin_product_scale_right q (obs 0 0)
          (fun j => obs x.succ j.succ) (fun j => recoveryB j i)
  have hblock :
      sumFin q (fun j =>
        (obs 0 0 * obs x.succ j.succ - obs x.succ 0 * obs 0 j.succ) *
          recoveryB j i) =
      obs 0 0 * sumFin q (fun j => obs x.succ j.succ * recoveryB j i) -
        obs x.succ 0 * sumFin q (fun j => obs 0 j.succ * recoveryB j i) := by
    calc
      sumFin q (fun j =>
          (obs 0 0 * obs x.succ j.succ - obs x.succ 0 * obs 0 j.succ) *
            recoveryB j i) =
        sumFin q (fun j =>
          obs 0 0 * (obs x.succ j.succ * recoveryB j i) -
            obs x.succ 0 * (obs 0 j.succ * recoveryB j i)) := by
              apply sumFin_congr
              intro j
              grind
      _ = sumFin q (fun j => obs 0 0 * (obs x.succ j.succ * recoveryB j i)) -
          sumFin q (fun j => obs x.succ 0 * (obs 0 j.succ * recoveryB j i)) := by
            rw [sumFin_sub]
      _ = obs 0 0 * sumFin q (fun j => obs x.succ j.succ * recoveryB j i) -
          obs x.succ 0 * sumFin q (fun j => obs 0 j.succ * recoveryB j i) := by
            rw [sumFin_mul_left, sumFin_mul_left]
  calc
    FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs x.succ i =
      obs 0 0 * sumFin q (fun j => obs x.succ j.succ * recoveryB j i) -
        obs x.succ 0 * sumFin q (fun j => obs 0 j.succ * recoveryB j i) := by
          unfold FinKernel.compose
          rw [sumFin_succ, finKernelPivotLowerRecovery_zero, htail]
          grind
    _ = sumFin q (fun j =>
          (obs 0 0 * obs x.succ j.succ - obs x.succ 0 * obs 0 j.succ) *
            recoveryB j i) := hblock.symm
    _ = FinKernel.compose recoveryB (finKernelPivotBlock obs) x i := by
          rfl

/-- A recovery of the pivot block makes the lower columns exact coordinate recoveries. -/
theorem finKernelPivotLowerRecovery_compose_succ
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a)
    (hrecB : FinKernel.compose recoveryB (finKernelPivotBlock obs) =
      FinKernel.identity a)
    (x i : Fin a) :
    FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs x.succ i =
      FinKernel.identity a x i := by
  rw [finKernelPivotLowerRecovery_compose_succ_formula]
  exact congrFun (congrFun hrecB x) i

/--
Raw head column: start from output basis zero and subtract each lower recovered
coordinate weighted by that source row's pivot-column coefficient.
-/
def finKernelPivotHeadRaw {a q : Nat}
    (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (lower : FinKernel (Nat.succ q) a) : FinKernel (Nat.succ q) 1 :=
  fun y _ =>
    (if y = 0 then 1 else 0) -
      sumFin a (fun i => obs i.succ 0 * lower y i)

/-- Composition of the raw head column is the first source column minus lower corrections. -/
theorem finKernelPivotHeadRaw_compose_formula
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (lower : FinKernel (Nat.succ q) a) (x : Fin (Nat.succ a)) :
    FinKernel.compose (finKernelPivotHeadRaw obs lower) obs x 0 =
      obs x 0 - sumFin a (fun i =>
        obs i.succ 0 * FinKernel.compose lower obs x i) := by
  have hseed :
      sumFin (Nat.succ q) (fun y =>
        obs x y * (if y = 0 then 1 else 0)) = obs x 0 := by
    calc
      sumFin (Nat.succ q) (fun y =>
          obs x y * (if y = 0 then 1 else 0)) =
        sumFin (Nat.succ q) (fun y => if y = 0 then obs x y else 0) := by
          apply sumFin_congr
          intro y
          by_cases hy : y = 0 <;> simp [hy]
      _ = obs x 0 := sumFin_single 0 (fun y => obs x y)
  have hcross :
      sumFin (Nat.succ q) (fun y =>
        obs x y * sumFin a (fun i => obs i.succ 0 * lower y i)) =
      sumFin a (fun i => obs i.succ 0 * FinKernel.compose lower obs x i) := by
    calc
      sumFin (Nat.succ q) (fun y =>
          obs x y * sumFin a (fun i => obs i.succ 0 * lower y i)) =
        sumFin (Nat.succ q) (fun y =>
          sumFin a (fun i => obs x y * (obs i.succ 0 * lower y i))) := by
            apply sumFin_congr
            intro y
            exact (sumFin_mul_left a (obs x y)
              (fun i => obs i.succ 0 * lower y i)).symm
      _ = sumFin a (fun i =>
          sumFin (Nat.succ q) (fun y => obs x y * (obs i.succ 0 * lower y i))) :=
        sumFin_swap (Nat.succ q) a
          (fun y i => obs x y * (obs i.succ 0 * lower y i))
      _ = sumFin a (fun i =>
          sumFin (Nat.succ q) (fun y => obs i.succ 0 * (obs x y * lower y i))) := by
            apply sumFin_congr
            intro i
            apply sumFin_congr
            intro y
            grind
      _ = sumFin a (fun i =>
          obs i.succ 0 * sumFin (Nat.succ q) (fun y => obs x y * lower y i)) := by
            apply sumFin_congr
            intro i
            rw [sumFin_mul_left]
      _ = sumFin a (fun i =>
          obs i.succ 0 * FinKernel.compose lower obs x i) := by
            rfl
  unfold FinKernel.compose finKernelPivotHeadRaw
  calc
    sumFin (Nat.succ q) (fun y =>
        obs x y * ((if y = 0 then 1 else 0) -
          sumFin a (fun i => obs i.succ 0 * lower y i))) =
      sumFin (Nat.succ q) (fun y =>
        obs x y * (if y = 0 then 1 else 0) -
          obs x y * sumFin a (fun i => obs i.succ 0 * lower y i)) := by
            apply sumFin_congr
            intro y
            grind
    _ = sumFin (Nat.succ q) (fun y =>
          obs x y * (if y = 0 then 1 else 0)) -
        sumFin (Nat.succ q) (fun y =>
          obs x y * sumFin a (fun i => obs i.succ 0 * lower y i)) := by
            rw [sumFin_sub]
    _ = obs x 0 - sumFin a (fun i =>
          obs i.succ 0 * FinKernel.compose lower obs x i) := by
            rw [hseed, hcross]

/-- The raw head column evaluates to the pivot on source row zero. -/
theorem finKernelPivotHeadRaw_compose_zero
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a)
    (hrecB : FinKernel.compose recoveryB (finKernelPivotBlock obs) =
      FinKernel.identity a) :
    FinKernel.compose
        (finKernelPivotHeadRaw obs (finKernelPivotLowerRecovery obs recoveryB))
        obs 0 0 = obs 0 0 := by
  rw [finKernelPivotHeadRaw_compose_formula]
  have hzero :
      sumFin a (fun i => obs i.succ 0 *
        FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs 0 i) = 0 := by
    calc
      sumFin a (fun i => obs i.succ 0 *
          FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs 0 i) =
        sumFin a (fun _ => (0 : Rat)) := by
          apply sumFin_congr
          intro i
          rw [finKernelPivotLowerRecovery_compose_zero]
          rw [Rat.mul_zero]
      _ = 0 := sumFin_zero_values a
  rw [hzero]
  grind

/-- Every nonzero source row is cancelled by the raw head correction. -/
theorem finKernelPivotHeadRaw_compose_succ
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a)
    (hrecB : FinKernel.compose recoveryB (finKernelPivotBlock obs) =
      FinKernel.identity a)
    (x : Fin a) :
    FinKernel.compose
        (finKernelPivotHeadRaw obs (finKernelPivotLowerRecovery obs recoveryB))
        obs x.succ 0 = 0 := by
  rw [finKernelPivotHeadRaw_compose_formula]
  have hsum :
      sumFin a (fun i => obs i.succ 0 *
        FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs x.succ i) =
      obs x.succ 0 := by
    calc
      sumFin a (fun i => obs i.succ 0 *
          FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs x.succ i) =
        sumFin a (fun i => obs i.succ 0 * FinKernel.identity a x i) := by
          apply sumFin_congr
          intro i
          rw [finKernelPivotLowerRecovery_compose_succ obs recoveryB hrecB x i]
      _ = sumFin a (fun i => if i = x then obs i.succ 0 else 0) := by
          apply sumFin_congr
          intro i
          by_cases hix : i = x
          · subst i
            simp [FinKernel.identity]
          · have hxi : x ≠ i := by
              intro h
              exact hix h.symm
            simp [FinKernel.identity, hix, hxi]
      _ = obs x.succ 0 := by
          simpa using sumFin_single x (fun i => obs i.succ 0)
  rw [hsum]
  grind

/-- Normalize the raw head column by the nonzero pivot. -/
def finKernelPivotHeadRecovery {a q : Nat}
    (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (lower : FinKernel (Nat.succ q) a) : FinKernel (Nat.succ q) 1 :=
  fun y _ => (1 / obs 0 0) * finKernelPivotHeadRaw obs lower y 0

/-- Scaling the raw head column pulls through exact composition. -/
theorem finKernelPivotHeadRecovery_compose_formula
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (lower : FinKernel (Nat.succ q) a) (x : Fin (Nat.succ a)) :
    FinKernel.compose (finKernelPivotHeadRecovery obs lower) obs x 0 =
      (1 / obs 0 0) *
        FinKernel.compose (finKernelPivotHeadRaw obs lower) obs x 0 := by
  unfold FinKernel.compose finKernelPivotHeadRecovery
  calc
    sumFin (Nat.succ q) (fun y =>
        obs x y * ((1 / obs 0 0) * finKernelPivotHeadRaw obs lower y 0)) =
      sumFin (Nat.succ q) (fun y =>
        (1 / obs 0 0) * (obs x y * finKernelPivotHeadRaw obs lower y 0)) := by
          apply sumFin_congr
          intro y
          grind
    _ = (1 / obs 0 0) *
        sumFin (Nat.succ q) (fun y => obs x y * finKernelPivotHeadRaw obs lower y 0) :=
      sumFin_mul_left (Nat.succ q) (1 / obs 0 0)
        (fun y => obs x y * finKernelPivotHeadRaw obs lower y 0)

/-- The normalized head column recovers source coordinate zero. -/
theorem finKernelPivotHeadRecovery_compose_zero
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a)
    (hpivot : obs 0 0 ≠ 0)
    (hrecB : FinKernel.compose recoveryB (finKernelPivotBlock obs) =
      FinKernel.identity a) :
    FinKernel.compose
        (finKernelPivotHeadRecovery obs (finKernelPivotLowerRecovery obs recoveryB))
        obs 0 0 = 1 := by
  rw [finKernelPivotHeadRecovery_compose_formula]
  rw [finKernelPivotHeadRaw_compose_zero obs recoveryB hrecB]
  exact Rat.div_mul_cancel hpivot

/-- The normalized head column vanishes on every lower source row. -/
theorem finKernelPivotHeadRecovery_compose_succ
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a)
    (hrecB : FinKernel.compose recoveryB (finKernelPivotBlock obs) =
      FinKernel.identity a)
    (x : Fin a) :
    FinKernel.compose
        (finKernelPivotHeadRecovery obs (finKernelPivotLowerRecovery obs recoveryB))
        obs x.succ 0 = 0 := by
  rw [finKernelPivotHeadRecovery_compose_formula]
  rw [finKernelPivotHeadRaw_compose_succ obs recoveryB hrecB x]
  grind

/-- Assemble the normalized head column with all lower recovery columns. -/
def finKernelPivotRecovery {a q : Nat}
    (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) : FinKernel (Nat.succ q) (Nat.succ a) :=
  fun y z =>
    Fin.cases
      (finKernelPivotHeadRecovery obs
        (finKernelPivotLowerRecovery obs recoveryB) y 0)
      (fun i => finKernelPivotLowerRecovery obs recoveryB y i)
      z

@[simp] theorem finKernelPivotRecovery_zero
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) (y : Fin (Nat.succ q)) :
    finKernelPivotRecovery obs recoveryB y 0 =
      finKernelPivotHeadRecovery obs
        (finKernelPivotLowerRecovery obs recoveryB) y 0 := by
  rfl

@[simp] theorem finKernelPivotRecovery_succ
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a) (y : Fin (Nat.succ q)) (i : Fin a) :
    finKernelPivotRecovery obs recoveryB y i.succ =
      finKernelPivotLowerRecovery obs recoveryB y i := by
  rfl

/-- A recovery of the scaled pivot block lifts to an exact recovery of the pivoted kernel. -/
theorem finKernelPivotRecovery_after_obs
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (recoveryB : FinKernel q a)
    (hpivot : obs 0 0 ≠ 0)
    (hrecB : FinKernel.compose recoveryB (finKernelPivotBlock obs) =
      FinKernel.identity a) :
    FinKernel.compose (finKernelPivotRecovery obs recoveryB) obs =
      FinKernel.identity (Nat.succ a) := by
  funext x z
  refine Fin.cases ?_ (fun i => ?_) z
  · change FinKernel.compose
      (finKernelPivotHeadRecovery obs
        (finKernelPivotLowerRecovery obs recoveryB)) obs x 0 =
      FinKernel.identity (Nat.succ a) x 0
    refine Fin.cases ?_ (fun k => ?_) x
    · rw [finKernelPivotHeadRecovery_compose_zero obs recoveryB hpivot hrecB]
      simp [FinKernel.identity]
    · rw [finKernelPivotHeadRecovery_compose_succ obs recoveryB hrecB k]
      simp [FinKernel.identity]
      grind
  · change FinKernel.compose (finKernelPivotLowerRecovery obs recoveryB) obs x i =
      FinKernel.identity (Nat.succ a) x i.succ
    refine Fin.cases ?_ (fun k => ?_) x
    · rw [finKernelPivotLowerRecovery_compose_zero]
      simp [FinKernel.identity]
      grind
    · rw [finKernelPivotLowerRecovery_compose_succ obs recoveryB hrecB k i]
      simp [FinKernel.identity]

/-- A split scaled pivot block implies an exact split of the whole pivoted kernel. -/
theorem finKernel_hasExactRecovery_of_pivotBlock
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (hpivot : obs 0 0 ≠ 0)
    (hblock : FinKernel.HasExactRecovery (finKernelPivotBlock obs)) :
    FinKernel.HasExactRecovery obs := by
  rcases hblock with ⟨recoveryB, hrecB⟩
  exact ⟨finKernelPivotRecovery obs recoveryB,
    finKernelPivotRecovery_after_obs obs recoveryB hpivot hrecB⟩

/--
Finite rational monicity splits constructively.  The induction is on source
cardinality: expose a nonzero pivot, swap it to output zero, descend to the
scaled lower block, split recursively, and lift that split back through the
pivot.
-/
theorem finKernel_observationMonic_to_hasExactRecovery :
    ∀ (a q : Nat) (obs : FinKernel a q),
      FinKernel.ObservationMonic obs → FinKernel.HasExactRecovery obs
  | 0, q, obs => by
      intro _
      refine ⟨FinKernel.zeroExact q 0, ?_⟩
      funext x
      exact Fin.elim0 x
  | Nat.succ a, 0, obs => by
      intro hmonic
      rcases finKernel_monic_firstRow_has_nonzero obs hmonic with ⟨y, _⟩
      exact Fin.elim0 y
  | Nat.succ a, Nat.succ q, obs => by
      intro hmonic
      rcases finKernel_monic_firstRow_has_nonzero obs hmonic with ⟨pivot, hpivotOriginal⟩
      let swapped : FinKernel (Nat.succ a) (Nat.succ q) :=
        FinKernel.compose (FinKernel.dirac (finSwapZero pivot)) obs
      have hswapped : FinKernel.ObservationMonic swapped := by
        dsimp [swapped]
        exact finKernel_swapZero_preserves_observationMonic obs pivot hmonic
      have hpivot : swapped 0 0 ≠ 0 := by
        intro hzero
        apply hpivotOriginal
        have heval := finKernel_swapZero_zero_eval obs pivot (0 : Fin (Nat.succ a))
        change swapped 0 0 = obs 0 pivot at heval
        exact heval.symm.trans hzero
      let block : FinKernel a q := finKernelPivotBlock swapped
      have hblockMonic : FinKernel.ObservationMonic block := by
        dsimp [block]
        exact finKernelPivotBlock_observationMonic swapped hpivot hswapped
      have hblockRecovery : FinKernel.HasExactRecovery block :=
        finKernel_observationMonic_to_hasExactRecovery a q block hblockMonic
      have hswappedRecovery : FinKernel.HasExactRecovery swapped := by
        dsimp [block] at hblockRecovery
        exact finKernel_hasExactRecovery_of_pivotBlock swapped hpivot hblockRecovery
      have hcomposite :
          FinKernel.HasExactRecovery
            (FinKernel.compose (FinKernel.dirac (finSwapZero pivot)) obs) := by
        simpa [swapped] using hswappedRecovery
      exact finKernel_hasExactRecovery_compose_reflect_earlier hcomposite
termination_by a q obs => a

/-- In this concrete finite rational kernel category, monicity is exactly exact recoverability. -/
theorem finKernel_observationMonic_iff_hasExactRecovery
    {a q : Nat} {obs : FinKernel a q} :
    FinKernel.ObservationMonic obs ↔ FinKernel.HasExactRecovery obs := by
  constructor
  · exact finKernel_observationMonic_to_hasExactRecovery a q obs
  · exact finKernel_hasExactRecovery_to_observationMonic

/--
Acceptance bundle: exact monicity and exact splitting coincide, while valid
stochastic recovery remains a strictly stronger notion.
-/
theorem finKernel_finite_monic_splitting_bundle :
    (∀ {a q : Nat} {obs : FinKernel a q},
      FinKernel.ObservationMonic obs ↔ FinKernel.HasExactRecovery obs) ∧
    FinKernel.ObservationMonic finFairKernel ∧
    FinKernel.HasValidStochasticRecovery finFairKernel ∧
    FinKernel.HasExactRecovery finNoisyEpic2 ∧
    (¬ FinKernel.HasValidStochasticRecovery finNoisyEpic2) ∧
    (¬ FinKernel.ObservationMonic (FinKernel.discard 2)) := by
  exact ⟨finKernel_observationMonic_iff_hasExactRecovery,
    finFairKernel_observationMonic,
    finFairKernel_hasValidStochasticRecovery,
    finNoisyEpic2_hasExactRecovery,
    finNoisyEpic2_not_hasValidStochasticRecovery,
    finKernel_discard_two_not_observationMonic⟩

end RelayTheory
