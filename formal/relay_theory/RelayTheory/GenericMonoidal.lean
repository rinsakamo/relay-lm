import Lean.Elab.Tactic.Grind
import Init.Data.Fin.Lemmas
import Init.Data.Nat.Mod
import RelayTheory.GenericStochastic

namespace RelayTheory

/--
The minimal transport contract needed by this transaction: two executable maps
with exact round trips. This is intentionally narrower than importing a general
finite-equivalence or category framework.
-/
structure FiniteTransport (α β : Type) where
  toFun : α → β
  invFun : β → α
  left_inv : ∀ x, invFun (toFun x) = x
  right_inv : ∀ y, toFun (invFun y) = y

/--
Constructive product encoding for the current cardinal-indexed finite object family.

This is deliberately proved from natural-number div/mod rather than imported as
category or finite-equivalence infrastructure. The orientation matches row-major
pair indexing: the second coordinate varies fastest.
-/
def finPairTransport {m n : Nat} : FiniteTransport (Fin m × Fin n) (Fin (m * n)) where
  toFun x :=
    ⟨x.2.1 + n * x.1.1,
      calc
        x.2.1 + n * x.1.1 + 1 = x.1.1 * n + x.2.1 + 1 := by grind
        _ ≤ x.1.1 * n + n := Nat.add_le_add_left x.2.2 _
        _ = (x.1.1 + 1) * n := Eq.symm <| Nat.succ_mul _ _
        _ ≤ m * n := Nat.mul_le_mul_right _ x.1.2⟩
  invFun x :=
    (⟨x.1 / n, by
        have h : x.1 < n * m := by
          simpa [Nat.mul_comm] using x.2
        exact Nat.div_lt_of_lt_mul h⟩,
     ⟨x.1 % n, by
        have hn : n ≠ 0 := by
          intro hn0
          subst n
          have hz : x.1 < 0 := by simpa using x.2
          exact Nat.not_lt_zero _ hz
        exact Nat.mod_lt _ (Nat.pos_of_ne_zero hn)⟩)
  left_inv := by
    intro x
    rcases x with ⟨x, y⟩
    have hn : 0 < n := Nat.pos_of_ne_zero (by
      intro hn0
      subst n
      exact Nat.not_lt_zero y.1 y.2)
    apply Prod.ext
    · apply Fin.eq_of_val_eq
      calc
        (y.1 + n * x.1) / n = y.1 / n + x.1 := Nat.add_mul_div_left _ _ hn
        _ = 0 + x.1 := by rw [Nat.div_eq_of_lt y.2]
        _ = x.1 := Nat.zero_add _
    · apply Fin.eq_of_val_eq
      calc
        (y.1 + n * x.1) % n = y.1 % n := Nat.add_mul_mod_self_left _ _ _
        _ = y.1 := Nat.mod_eq_of_lt y.2
  right_inv := by
    intro x
    apply Fin.eq_of_val_eq
    change (x.1 % n + n * (x.1 / n)) = x.1
    exact Nat.mod_add_div _ _

@[simp] theorem finPairTransport_apply_val {m n : Nat} (x : Fin m × Fin n) :
    (finPairTransport.toFun x).1 = x.2.1 + n * x.1.1 := rfl

@[simp] theorem finPairTransport_inv_fst_val {m n : Nat} (x : Fin (m * n)) :
    ((finPairTransport.invFun x).1).1 = x.1 / n := rfl

@[simp] theorem finPairTransport_inv_snd_val {m n : Nat} (x : Fin (m * n)) :
    ((finPairTransport.invFun x).2).1 = x.1 % n := rfl

/-- The product transport round-trips every declared finite pair exactly. -/
theorem finPair_transport_roundtrip {m n : Nat} (x : Fin m × Fin n) :
    finPairTransport.invFun (finPairTransport.toFun x) = x :=
  finPairTransport.left_inv x

/-- The flattened finite product transport round-trips every encoded index exactly. -/
theorem finPair_flatten_roundtrip {m n : Nat} (x : Fin (m * n)) :
    finPairTransport.toFun (finPairTransport.invFun x) = x :=
  finPairTransport.right_inv x

/-- Exact finite summation splits into a left prefix and right translated block. -/
theorem sumFin_add_split : ∀ (m n : Nat) (f : Fin (m + n) → Rat),
    sumFin (m + n) f =
      sumFin m (fun i => f (Fin.castAdd n i)) +
      sumFin n (fun j => f (Fin.natAdd m j))
  | 0, n, f => by
      change sumFin n f =
        sumFin 0 (fun i => f (Fin.castAdd n i)) +
        sumFin n (fun j => f (Fin.natAdd 0 j))
      rw [sumFin_zero, Rat.zero_add]
      apply sumFin_congr
      intro j
      apply congrArg f
      apply Fin.eq_of_val_eq
      rfl
  | Nat.succ m, n, f => by
      rw [sumFin_succ]
      rw [sumFin_succ]
      rw [sumFin_add_split m n (fun i => f i.succ)]
      have h0 : f 0 = f (Fin.castAdd n (0 : Fin (Nat.succ m))) := by
        apply congrArg f
        apply Fin.eq_of_val_eq
        rfl
      have hleft :
          sumFin m (fun i => f (Fin.castAdd n i).succ) =
            sumFin m (fun i => f (Fin.castAdd n i.succ)) := by
        apply sumFin_congr
        intro i
        apply congrArg f
        apply Fin.eq_of_val_eq
        rfl
      have hright :
          sumFin n (fun j => f (Fin.natAdd m j).succ) =
            sumFin n (fun j => f (Fin.natAdd (Nat.succ m) j)) := by
        apply sumFin_congr
        intro j
        apply congrArg f
        apply Fin.eq_of_val_eq
        grind
      rw [h0, hleft, hright]
      exact (Rat.add_assoc _ _ _).symm

end RelayTheory