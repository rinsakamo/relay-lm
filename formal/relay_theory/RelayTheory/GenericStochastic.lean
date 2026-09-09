import Lean.Elab.Tactic.Grind
import Init.Data.Fin.Lemmas
import Init.Grind.Ordered.Rat
import RelayTheory.Stochastic

namespace RelayTheory

/--
Exact finite summation over a declared `Fin n` interface.

This is intentionally the smallest summation apparatus needed by the generic
finite stochastic category-core transaction. It is not a general-purpose
algebra library.
-/
def sumFin : (n : Nat) → (Fin n → Rat) → Rat
  | 0, _ => 0
  | Nat.succ n, f => f 0 + sumFin n (fun i => f i.succ)

@[simp] theorem sumFin_zero (f : Fin 0 → Rat) :
    sumFin 0 f = 0 := rfl

@[simp] theorem sumFin_succ {n : Nat} (f : Fin (Nat.succ n) → Rat) :
    sumFin (Nat.succ n) f = f 0 + sumFin n (fun i => f i.succ) := rfl

theorem sumFin_zero_values : ∀ n : Nat,
    sumFin n (fun _ => (0 : Rat)) = 0
  | 0 => rfl
  | Nat.succ n => by
      rw [sumFin_succ, sumFin_zero_values n, Rat.zero_add]

theorem sumFin_congr : ∀ (n : Nat) (f g : Fin n → Rat),
    (∀ i, f i = g i) → sumFin n f = sumFin n g
  | 0, _, _, _ => rfl
  | Nat.succ n, f, g, h => by
      rw [sumFin_succ, sumFin_succ, h 0]
      rw [sumFin_congr n (fun i => f i.succ) (fun i => g i.succ) (fun i => h i.succ)]

theorem sumFin_add : ∀ (n : Nat) (f g : Fin n → Rat),
    sumFin n (fun i => f i + g i) = sumFin n f + sumFin n g
  | 0, _, _ => by
      simp [sumFin, Rat.zero_add]
  | Nat.succ n, f, g => by
      rw [sumFin_succ, sumFin_succ, sumFin_succ]
      rw [sumFin_add n (fun i => f i.succ) (fun i => g i.succ)]
      grind

theorem sumFin_mul_left : ∀ (n : Nat) (a : Rat) (f : Fin n → Rat),
    sumFin n (fun i => a * f i) = a * sumFin n f
  | 0, _, _ => by
      simp [sumFin, Rat.mul_zero]
  | Nat.succ n, a, f => by
      rw [sumFin_succ, sumFin_succ]
      rw [sumFin_mul_left n a (fun i => f i.succ)]
      grind

theorem sumFin_mul_right : ∀ (n : Nat) (f : Fin n → Rat) (a : Rat),
    sumFin n (fun i => f i * a) = sumFin n f * a
  | 0, _, _ => by
      simp [sumFin, Rat.zero_mul]
  | Nat.succ n, f, a => by
      rw [sumFin_succ, sumFin_succ]
      rw [sumFin_mul_right n (fun i => f i.succ) a]
      grind

theorem sumFin_nonneg : ∀ (n : Nat) (f : Fin n → Rat),
    (∀ i, 0 ≤ f i) → 0 ≤ sumFin n f
  | 0, _, _ => (show (0 : Rat) ≤ 0 from Rat.le_refl)
  | Nat.succ n, f, h => by
      rw [sumFin_succ]
      exact Rat.add_nonneg
        (h 0)
        (sumFin_nonneg n (fun i => f i.succ) (fun i => h i.succ))

/-- Finite Fubini/interchange for exact rational sums. -/
theorem sumFin_swap : ∀ (m n : Nat) (f : Fin m → Fin n → Rat),
    sumFin m (fun i => sumFin n (fun j => f i j)) =
      sumFin n (fun j => sumFin m (fun i => f i j))
  | 0, n, _ => by
      simp [sumFin, sumFin_zero_values n]
  | Nat.succ m, n, f => by
      rw [sumFin_succ]
      rw [sumFin_swap m n (fun i j => f i.succ j)]
      rw [← sumFin_add]
      apply sumFin_congr
      intro j
      rfl

/-- Exact finite delta/singleton summation. -/
theorem sumFin_single : ∀ {n : Nat} (x : Fin n) (f : Fin n → Rat),
    sumFin n (fun y => if y = x then f y else 0) = f x := by
  intro n
  induction n with
  | zero =>
      intro x
      exact Fin.elim0 x
  | succ n ih =>
      intro x f
      refine Fin.cases ?_ (fun i => ?_) x
      · rw [sumFin_succ]
        simp [sumFin_zero_values]
      · intro i
        rw [sumFin_succ]
        simp [ih i (fun j => f j.succ)]

/--
Bilinear finite-sum reassociation used directly by stochastic associativity.
This theorem is the non-categorical algebraic core: distribute, swap finite
sums, and reassociate exact rational multiplication.
-/
theorem sumFin_bilinear_assoc {m n : Nat}
    (a : Fin m → Rat)
    (b : Fin m → Fin n → Rat)
    (c : Fin n → Rat) :
    sumFin n (fun z => sumFin m (fun y => a y * b y z) * c z) =
      sumFin m (fun y => a y * sumFin n (fun z => b y z * c z)) := by
  calc
    sumFin n (fun z => sumFin m (fun y => a y * b y z) * c z)
        = sumFin n (fun z => sumFin m (fun y => (a y * b y z) * c z)) := by
            apply sumFin_congr
            intro z
            rw [sumFin_mul_right]
    _ = sumFin m (fun y => sumFin n (fun z => (a y * b y z) * c z)) := by
          exact (sumFin_swap m n (fun y z => (a y * b y z) * c z)).symm
    _ = sumFin m (fun y => sumFin n (fun z => a y * (b y z * c z))) := by
          apply sumFin_congr
          intro y
          apply sumFin_congr
          intro z
          exact Rat.mul_assoc _ _ _
    _ = sumFin m (fun y => a y * sumFin n (fun z => b y z * c z)) := by
          apply sumFin_congr
          intro y
          rw [sumFin_mul_left]

/-- Exact resolved stochastic kernel between arbitrary declared finite interfaces. -/
abbrev FinKernel (m n : Nat) := Fin m → Fin n → Rat

namespace FinKernel

/-- Exact row mass over the declared finite output interface. -/
def rowSum {m n : Nat} (k : FinKernel m n) (x : Fin m) : Rat :=
  sumFin n (fun y => k x y)

/-- Exact stochastic validity: every mass is non-negative and every inhabited row sums to one. -/
def Valid {m n : Nat} (k : FinKernel m n) : Prop :=
  (∀ x y, 0 ≤ k x y) ∧
  (∀ x, rowSum k x = 1)

/-- Exact finite probability sum/product composition. `compose g f` means first `f`, then `g`. -/
def compose {m n p : Nat} (g : FinKernel n p) (f : FinKernel m n) : FinKernel m p :=
  fun x z => sumFin n (fun y => f x y * g y z)

/-- Exact Dirac identity on every declared finite interface. -/
def identity (n : Nat) : FinKernel n n :=
  fun x y => if x = y then 1 else 0

/-- Exact deterministic/Dirac stochastic map. -/
def dirac {m n : Nat} (f : Fin m → Fin n) : FinKernel m n :=
  fun x y => if y = f x then 1 else 0

end FinKernel

/-- No normalized stochastic row exists from an inhabited source into an empty target. -/
theorem no_valid_kernel_to_empty {m : Nat} (x : Fin m) (k : FinKernel m 0) :
    ¬ FinKernel.Valid k := by
  intro hk
  have hrow := hk.2 x
  change sumFin 0 (fun y => k x y) = 1 at hrow
  grind [sumFin] at hrow

/-- Generic exact identity is stochastic-valid. -/
theorem finKernel_identity_valid (n : Nat) :
    FinKernel.Valid (FinKernel.identity n) := by
  constructor
  · intro x y
    by_cases h : x = y <;>
      simp [FinKernel.identity, h]
  · intro x
    unfold FinKernel.rowSum FinKernel.identity
    have h := sumFin_single x (fun _ => (1 : Rat))
    simpa [eq_comm] using h

/-- Generic right identity for arbitrary exact finite kernels. -/
theorem finKernel_compose_identity_after {m n : Nat} (k : FinKernel m n) :
    FinKernel.compose (FinKernel.identity n) k = k := by
  funext x z
  unfold FinKernel.compose FinKernel.identity
  have h := sumFin_single z (fun y => k x y)
  simpa [Rat.mul_one, Rat.mul_zero] using h

/-- Generic left identity for arbitrary exact finite kernels. -/
theorem finKernel_compose_identity_before {m n : Nat} (k : FinKernel m n) :
    FinKernel.compose k (FinKernel.identity m) = k := by
  funext x z
  unfold FinKernel.compose FinKernel.identity
  have h := sumFin_single x (fun y => k y z)
  simpa [eq_comm, Rat.one_mul, Rat.zero_mul] using h

/-- Exact stochastic validity is closed under generic finite composition. -/
theorem finKernel_compose_valid {m n p : Nat}
    {f : FinKernel m n} {g : FinKernel n p}
    (hf : FinKernel.Valid f) (hg : FinKernel.Valid g) :
    FinKernel.Valid (FinKernel.compose g f) := by
  constructor
  · intro x z
    unfold FinKernel.compose
    apply sumFin_nonneg
    intro y
    exact Rat.mul_nonneg (hf.1 x y) (hg.1 y z)
  · intro x
    unfold FinKernel.rowSum FinKernel.compose
    calc
      sumFin p (fun z => sumFin n (fun y => f x y * g y z))
          = sumFin n (fun y => sumFin p (fun z => f x y * g y z)) := by
              exact (sumFin_swap n p (fun y z => f x y * g y z)).symm
      _ = sumFin n (fun y => f x y * sumFin p (fun z => g y z)) := by
            apply sumFin_congr
            intro y
            rw [sumFin_mul_left]
      _ = sumFin n (fun y => f x y * 1) := by
            apply sumFin_congr
            intro y
            rw [hg.2 y]
      _ = sumFin n (fun y => f x y) := by
            apply sumFin_congr
            intro y
            rw [Rat.mul_one]
      _ = 1 := hf.2 x

/--
Generic associativity over arbitrary compatible finite interface sizes and
arbitrary exact kernels. No category structure is assumed in the statement or
proof.
-/
theorem finKernel_compose_associative {a b c d : Nat}
    (f : FinKernel a b) (g : FinKernel b c) (h : FinKernel c d) :
    FinKernel.compose h (FinKernel.compose g f) =
      FinKernel.compose (FinKernel.compose h g) f := by
  funext x w
  unfold FinKernel.compose
  exact sumFin_bilinear_assoc
    (fun y => f x y)
    (fun y z => g y z)
    (fun z => h z w)

/-- Generic deterministic Dirac kernels are stochastic-valid whenever the function exists. -/
theorem finKernel_dirac_valid {m n : Nat} (f : Fin m → Fin n) :
    FinKernel.Valid (FinKernel.dirac f) := by
  constructor
  · intro x y
    by_cases h : y = f x <;>
      simp [FinKernel.dirac, h]
  · intro x
    unfold FinKernel.rowSum FinKernel.dirac
    have h := sumFin_single (f x) (fun _ => (1 : Rat))
    simpa using h

/-- Generic deterministic composition agrees exactly with ordinary function composition. -/
theorem finKernel_dirac_compose {a b c : Nat}
    (f : Fin a → Fin b) (g : Fin b → Fin c) :
    FinKernel.compose (FinKernel.dirac g) (FinKernel.dirac f) =
      FinKernel.dirac (fun x => g (f x)) := by
  funext x z
  unfold FinKernel.compose FinKernel.dirac
  have h := sumFin_single (f x) (fun y => if z = g y then (1 : Rat) else 0)
  simpa [Rat.one_mul, Rat.zero_mul] using h

/-- A genuinely non-binary exact stochastic fixture: one source state to three target states. -/
def triKernel : FinKernel 1 3 :=
  fun _ y => if y = 0 then qHalf else qQuarter

theorem triKernel_valid : FinKernel.Valid triKernel := by
  constructor
  · intro x y
    by_cases h : y = 0
    · simpa [triKernel, h] using Rat.le_of_lt qHalf_pos
    · simpa [triKernel, h] using Rat.le_of_lt qQuarter_pos
  · intro x
    unfold FinKernel.rowSum triKernel
    grind [sumFin, qHalf, qQuarter]

/--
The generic finite sequential core retains the already-earned non-stochastic
outer boundaries rather than encoding them inside an arrow.
-/
theorem genericFiniteStochasticCore_outer_boundaries :
    unresolvedSelectableResponses ≠ [resolvedMixedResponse] ∧
    (¬ ∃ t : TripleLaw, antiTriangle.RealizedBy t) :=
  stochastic_slice_outer_boundaries

/--
Acceptance bundle for the first generic finite stochastic category-core
milestone. The universal laws are supplied by the generic theorems above; this
bundle keeps the positive non-binary control and outer boundaries explicit.
-/
theorem genericFiniteStochasticCore_bundle :
    FinKernel.Valid triKernel ∧
    unresolvedSelectableResponses ≠ [resolvedMixedResponse] ∧
    (¬ ∃ t : TripleLaw, antiTriangle.RealizedBy t) :=
  ⟨triKernel_valid,
    unresolvedFamily_ne_resolvedSingleton,
    antiTriangle_not_globally_realizable⟩

end RelayTheory
