import RelayTheory.RecoveryCancellation

namespace RelayTheory

/-- Exact finite sums commute with additive negation. -/
theorem sumFin_neg (n : Nat) (f : Fin n → Rat) :
    sumFin n (fun i => - f i) = - sumFin n f := by
  calc
    sumFin n (fun i => - f i) =
        sumFin n (fun i => (-1 : Rat) * f i) := by
          apply sumFin_congr
          intro i
          grind
    _ = (-1 : Rat) * sumFin n f := sumFin_mul_left n (-1 : Rat) f
    _ = - sumFin n f := by grind

/-- Exact finite sums commute with subtraction. -/
theorem sumFin_sub (n : Nat) (f g : Fin n → Rat) :
    sumFin n (fun i => f i - g i) = sumFin n f - sumFin n g := by
  calc
    sumFin n (fun i => f i - g i) =
        sumFin n (fun i => f i + (- g i)) := by
          apply sumFin_congr
          intro i
          grind
    _ = sumFin n f + sumFin n (fun i => - g i) := sumFin_add n f (fun i => - g i)
    _ = sumFin n f + (- sumFin n g) := by rw [sumFin_neg]
    _ = sumFin n f - sumFin n g := by grind

/-- Pull a common left scalar through a sum of products. -/
theorem sumFin_scaled_product (n : Nat) (c : Rat)
    (f g : Fin n → Rat) :
    sumFin n (fun i => (c * f i) * g i) =
      c * sumFin n (fun i => f i * g i) := by
  calc
    sumFin n (fun i => (c * f i) * g i) =
        sumFin n (fun i => c * (f i * g i)) := by
          apply sumFin_congr
          intro i
          rw [Rat.mul_assoc]
    _ = c * sumFin n (fun i => f i * g i) :=
      sumFin_mul_left n c (fun i => f i * g i)

namespace FinKernel

/-- The exact all-zero kernel, used only as an algebraic cancellation witness. -/
def zeroExact (m n : Nat) : FinKernel m n :=
  fun _ _ => 0

end FinKernel

/-- Swap output coordinate `0` with `p`, leaving all other coordinates fixed. -/
def finSwapZero {n : Nat} (p : Fin (Nat.succ n))
    (x : Fin (Nat.succ n)) : Fin (Nat.succ n) :=
  if x = 0 then p else if x = p then 0 else x

@[simp] theorem finSwapZero_zero {n : Nat} (p : Fin (Nat.succ n)) :
    finSwapZero p 0 = p := by
  simp [finSwapZero]

/-- The pivot swap is an involution, including the `p = 0` case. -/
theorem finSwapZero_involutive {n : Nat} (p x : Fin (Nat.succ n)) :
    finSwapZero p (finSwapZero p x) = x := by
  by_cases hp : p = 0
  · subst p
    by_cases hx : x = 0
    · subst x
      simp [finSwapZero]
    · simp [finSwapZero, hx]
  · by_cases hx0 : x = 0
    · subst x
      simp [finSwapZero, hp]
    · by_cases hxp : x = p
      · subst x
        simp [finSwapZero, hp]
      · simp [finSwapZero, hx0, hxp]

/-- Postcomposition by an involutive Dirac map reindexes output coordinates. -/
theorem finKernel_compose_dirac_involution_eval
    {m n : Nat} (k : FinKernel m n) (s : Fin n → Fin n)
    (hs : ∀ y, s (s y) = y) (x : Fin m) (z : Fin n) :
    FinKernel.compose (FinKernel.dirac s) k x z = k x (s z) := by
  unfold FinKernel.compose FinKernel.dirac
  calc
    sumFin n (fun y => k x y * (if z = s y then 1 else 0)) =
        sumFin n (fun y => if y = s z then k x y else 0) := by
          apply sumFin_congr
          intro y
          by_cases hy : y = s z
          · have hz : z = s y := by
              calc
                z = s (s z) := (hs z).symm
                _ = s y := congrArg s hy.symm
            rw [if_pos hz, if_pos hy, Rat.mul_one]
          · have hz : z ≠ s y := by
              intro hzy
              apply hy
              have hmap := congrArg s hzy
              calc
                y = s (s y) := (hs y).symm
                _ = s z := hmap.symm
            rw [if_neg hz, if_neg hy, Rat.mul_zero]
    _ = k x (s z) := sumFin_single (s z) (fun y => k x y)

/-- The pivot-swap Dirac kernel is its own exact inverse. -/
theorem finKernel_dirac_finSwapZero_self_inverse
    {n : Nat} (p : Fin (Nat.succ n)) :
    FinKernel.compose (FinKernel.dirac (finSwapZero p))
        (FinKernel.dirac (finSwapZero p)) =
      FinKernel.identity (Nat.succ n) := by
  rw [finKernel_dirac_compose]
  rw [finKernel_identity_eq_dirac_id (Nat.succ n)]
  apply finKernel_dirac_congr
  intro x
  exact finSwapZero_involutive p x

/-- The pivot swap has an explicit exact recovery. -/
theorem finKernel_dirac_finSwapZero_hasExactRecovery
    {n : Nat} (p : Fin (Nat.succ n)) :
    FinKernel.HasExactRecovery (FinKernel.dirac (finSwapZero p)) := by
  exact ⟨FinKernel.dirac (finSwapZero p),
    finKernel_dirac_finSwapZero_self_inverse p⟩

/-- Postcomposing a monic observation by the pivot swap preserves monicity. -/
theorem finKernel_swapZero_preserves_observationMonic
    {a n : Nat} (obs : FinKernel a (Nat.succ n))
    (p : Fin (Nat.succ n))
    (hmonic : FinKernel.ObservationMonic obs) :
    FinKernel.ObservationMonic
      (FinKernel.compose (FinKernel.dirac (finSwapZero p)) obs) := by
  exact finKernel_observationMonic_compose hmonic
    (finKernel_hasExactRecovery_to_observationMonic
      (finKernel_dirac_finSwapZero_hasExactRecovery p))

/-- After the pivot swap, output coordinate zero is the selected pivot. -/
theorem finKernel_swapZero_zero_eval
    {a n : Nat} (obs : FinKernel a (Nat.succ n))
    (p : Fin (Nat.succ n)) (x : Fin a) :
    FinKernel.compose (FinKernel.dirac (finSwapZero p)) obs x 0 =
      obs x p := by
  rw [finKernel_compose_dirac_involution_eval
    obs (finSwapZero p) (finSwapZero_involutive p)]
  rw [finSwapZero_zero]

/-- A monic kernel with inhabited source has a nonzero coordinate in row zero. -/
theorem finKernel_monic_firstRow_has_nonzero
    {a q : Nat} (obs : FinKernel (Nat.succ a) q)
    (hmonic : FinKernel.ObservationMonic obs) :
    ∃ y : Fin q, obs 0 y ≠ 0 := by
  apply Classical.byContradiction
  intro hnone
  have hrowZero : ∀ y : Fin q, obs 0 y = 0 := by
    intro y
    by_cases hy : obs 0 y = 0
    · exact hy
    · exact False.elim (hnone ⟨y, hy⟩)
  let z : FinKernel 1 (Nat.succ a) := FinKernel.zeroExact 1 (Nat.succ a)
  let pick : FinKernel 1 (Nat.succ a) :=
    FinKernel.dirac (fun _ : Fin 1 => (0 : Fin (Nat.succ a)))
  have hcomp : FinKernel.compose obs z = FinKernel.compose obs pick := by
    funext x y
    calc
      FinKernel.compose obs z x y = 0 := by
        unfold FinKernel.compose z FinKernel.zeroExact
        calc
          sumFin (Nat.succ a) (fun i => 0 * obs i y) =
              sumFin (Nat.succ a) (fun _ => (0 : Rat)) := by
                apply sumFin_congr
                intro i
                rw [Rat.zero_mul]
          _ = 0 := sumFin_zero_values (Nat.succ a)
      _ = obs 0 y := (hrowZero y).symm
      _ = FinKernel.compose obs pick x y := by
        symm
        simpa [pick] using
          (finKernel_compose_after_dirac_eval obs
            (fun _ : Fin 1 => (0 : Fin (Nat.succ a))) x y)
  have heq : z = pick := hmonic z pick hcomp
  have hv := congrFun (congrFun heq (0 : Fin 1)) (0 : Fin (Nat.succ a))
  simp [z, pick, FinKernel.zeroExact, FinKernel.dirac] at hv

/--
Scaled lower-right pivot block.  Scaling by the pivot avoids division during the
monicity descent:
`Bᵢⱼ = p*Aᵢ₊₁,ⱼ₊₁ - Aᵢ₊₁,0*A₀,ⱼ₊₁`.
-/
def finKernelPivotBlock {a q : Nat}
    (obs : FinKernel (Nat.succ a) (Nat.succ q)) : FinKernel a q :=
  fun i j =>
    obs 0 0 * obs i.succ j.succ - obs i.succ 0 * obs 0 j.succ

/--
Lift an upstream kernel into the pivoted source so the pivot output coordinate
cancels exactly, while the remaining coordinates become the scaled pivot block.
-/
def finKernelPivotLift {t a q : Nat}
    (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (h : FinKernel t a) : FinKernel t (Nat.succ a) :=
  fun x y =>
    Fin.cases
      (- sumFin a (fun i => h x i * obs i.succ 0))
      (fun i => obs 0 0 * h x i)
      y

@[simp] theorem finKernelPivotLift_zero
    {t a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (h : FinKernel t a) (x : Fin t) :
    finKernelPivotLift obs h x 0 =
      - sumFin a (fun i => h x i * obs i.succ 0) := by
  rfl

@[simp] theorem finKernelPivotLift_succ
    {t a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (h : FinKernel t a) (x : Fin t) (i : Fin a) :
    finKernelPivotLift obs h x i.succ = obs 0 0 * h x i := by
  rfl

/-- The scaled pivot lift annihilates output coordinate zero. -/
theorem finKernelPivotLift_compose_zero
    {t a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (h : FinKernel t a) (x : Fin t) :
    FinKernel.compose obs (finKernelPivotLift obs h) x 0 = 0 := by
  unfold FinKernel.compose
  rw [sumFin_succ]
  rw [finKernelPivotLift_zero]
  have htail :
      sumFin a (fun i => finKernelPivotLift obs h x i.succ * obs i.succ 0) =
        sumFin a (fun i => (obs 0 0 * h x i) * obs i.succ 0) := by
    apply sumFin_congr
    intro i
    rw [finKernelPivotLift_succ]
  rw [htail, sumFin_scaled_product]
  grind

/-- Exact formula for composing through the scaled pivot block. -/
theorem finKernelPivotBlock_compose_formula
    {t a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (h : FinKernel t a) (x : Fin t) (z : Fin q) :
    FinKernel.compose (finKernelPivotBlock obs) h x z =
      obs 0 0 * sumFin a (fun i => h x i * obs i.succ z.succ) -
      sumFin a (fun i => h x i * obs i.succ 0) * obs 0 z.succ := by
  unfold FinKernel.compose finKernelPivotBlock
  calc
    sumFin a (fun i =>
        h x i * (obs 0 0 * obs i.succ z.succ -
          obs i.succ 0 * obs 0 z.succ)) =
      sumFin a (fun i =>
        (obs 0 0 * h x i) * obs i.succ z.succ -
          (h x i * obs i.succ 0) * obs 0 z.succ) := by
        apply sumFin_congr
        intro i
        grind
    _ = sumFin a (fun i => (obs 0 0 * h x i) * obs i.succ z.succ) -
        sumFin a (fun i => (h x i * obs i.succ 0) * obs 0 z.succ) := by
        rw [sumFin_sub]
    _ = obs 0 0 * sumFin a (fun i => h x i * obs i.succ z.succ) -
        sumFin a (fun i => h x i * obs i.succ 0) * obs 0 z.succ := by
        rw [sumFin_scaled_product, sumFin_mul_right]

/-- Remaining output coordinates of the lift are exactly the pivot-block composite. -/
theorem finKernelPivotLift_compose_succ
    {t a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (h : FinKernel t a) (x : Fin t) (z : Fin q) :
    FinKernel.compose obs (finKernelPivotLift obs h) x z.succ =
      FinKernel.compose (finKernelPivotBlock obs) h x z := by
  unfold FinKernel.compose
  rw [sumFin_succ]
  rw [finKernelPivotLift_zero]
  have htail :
      sumFin a (fun i => finKernelPivotLift obs h x i.succ * obs i.succ z.succ) =
        sumFin a (fun i => (obs 0 0 * h x i) * obs i.succ z.succ) := by
    apply sumFin_congr
    intro i
    rw [finKernelPivotLift_succ]
  rw [htail, sumFin_scaled_product]
  rw [finKernelPivotBlock_compose_formula]
  grind

/--
Monicity descends to the scaled lower-right pivot block whenever the pivot is
nonzero.  No row-operation matrix or rank theorem is required.
-/
theorem finKernelPivotBlock_observationMonic
    {a q : Nat} (obs : FinKernel (Nat.succ a) (Nat.succ q))
    (hpivot : obs 0 0 ≠ 0)
    (hmonic : FinKernel.ObservationMonic obs) :
    FinKernel.ObservationMonic (finKernelPivotBlock obs) := by
  intro t h₁ h₂ hEq
  have hLiftEq :
      FinKernel.compose obs (finKernelPivotLift obs h₁) =
        FinKernel.compose obs (finKernelPivotLift obs h₂) := by
    funext x z
    refine Fin.cases ?_ (fun j => ?_) z
    · rw [finKernelPivotLift_compose_zero, finKernelPivotLift_compose_zero]
    · rw [finKernelPivotLift_compose_succ, finKernelPivotLift_compose_succ]
      exact congrFun (congrFun hEq x) j
  have hUp : finKernelPivotLift obs h₁ = finKernelPivotLift obs h₂ :=
    hmonic (finKernelPivotLift obs h₁) (finKernelPivotLift obs h₂) hLiftEq
  funext x i
  have hv := congrFun (congrFun hUp x) i.succ
  change obs 0 0 * h₁ x i = obs 0 0 * h₂ x i at hv
  have hinv : (1 / obs 0 0) * obs 0 0 = (1 : Rat) := by
    exact Rat.div_mul_cancel hpivot
  calc
    h₁ x i = 1 * h₁ x i := by rw [Rat.one_mul]
    _ = ((1 / obs 0 0) * obs 0 0) * h₁ x i := by rw [hinv]
    _ = (1 / obs 0 0) * (obs 0 0 * h₁ x i) := by rw [Rat.mul_assoc]
    _ = (1 / obs 0 0) * (obs 0 0 * h₂ x i) := by rw [hv]
    _ = ((1 / obs 0 0) * obs 0 0) * h₂ x i := by rw [Rat.mul_assoc]
    _ = 1 * h₂ x i := by rw [hinv]
    _ = h₂ x i := by rw [Rat.one_mul]

end RelayTheory
