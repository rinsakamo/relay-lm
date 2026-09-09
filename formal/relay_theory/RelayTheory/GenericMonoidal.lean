import Lean.Elab.Tactic.Grind
import Init.Data.Fin.Lemmas
import Init.Data.Nat.Mod
import RelayTheory.GenericStochastic

namespace RelayTheory

/--
Constructive product encoding for the current cardinal-indexed finite object family.

This is deliberately proved from natural-number div/mod rather than imported as
category or finite-equivalence infrastructure. The orientation matches row-major
pair indexing: the second coordinate varies fastest.
-/
def finPairEquiv {m n : Nat} : Fin m × Fin n ≃ Fin (m * n) where
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
          simp at x
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
    calc
      x.1 % n + n * (x.1 / n) = x.1 % n + (x.1 / n) * n := by
        rw [Nat.mul_comm n (x.1 / n)]
      _ = x.1 := Nat.mod_add_div _ _

@[simp] theorem finPairEquiv_apply_val {m n : Nat} (x : Fin m × Fin n) :
    (finPairEquiv x).1 = x.2.1 + n * x.1.1 := rfl

@[simp] theorem finPairEquiv_symm_apply_fst_val {m n : Nat} (x : Fin (m * n)) :
    ((finPairEquiv.symm x).1).1 = x.1 / n := rfl

@[simp] theorem finPairEquiv_symm_apply_snd_val {m n : Nat} (x : Fin (m * n)) :
    ((finPairEquiv.symm x).2).1 = x.1 % n := rfl

/-- The product transport round-trips every declared finite pair exactly. -/
theorem finPair_transport_roundtrip {m n : Nat} (x : Fin m × Fin n) :
    finPairEquiv.symm (finPairEquiv x) = x :=
  finPairEquiv.left_inv x

/-- The flattened finite product transport round-trips every encoded index exactly. -/
theorem finPair_flatten_roundtrip {m n : Nat} (x : Fin (m * n)) :
    finPairEquiv (finPairEquiv.symm x) = x :=
  finPairEquiv.right_inv x

end RelayTheory
