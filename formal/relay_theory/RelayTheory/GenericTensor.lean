import RelayTheory.GenericMonoidal

namespace RelayTheory

/--
Exact flattening/Fubini theorem for the constructive row-major finite-product
transport. This is the algebraic bridge from the sequential finite kernel core
to a generic tensor: summing over the flattened product object is exactly the
same as summing over both component interfaces.
-/
theorem sumFin_product : ∀ (m n : Nat) (f : Fin (m * n) → Rat),
    sumFin (m * n) f =
      sumFin m (fun i =>
        sumFin n (fun j => f (finPairTransport.toFun (i, j))))
  | 0, n, f => by
      simp [Nat.zero_mul, sumFin]
  | Nat.succ m, n, f => by
      let h : Nat.succ m * n = n + m * n := by
        rw [Nat.succ_mul, Nat.add_comm]
      let f' : Fin (n + m * n) → Rat :=
        fun k => f (Fin.cast h.symm k)
      let g : Fin (m * n) → Rat :=
        fun k => f' (Fin.natAdd n k)
      have hcast :
          sumFin (Nat.succ m * n) f = sumFin (n + m * n) f' := by
        simpa [f'] using sumFin_cast h f
      have hsplit :
          sumFin (n + m * n) f' =
            sumFin n (fun j => f' (Fin.castAdd (m * n) j)) +
            sumFin (m * n) g := by
        simpa [g] using sumFin_add_split n (m * n) f'
      have hfirst :
          sumFin n (fun j => f' (Fin.castAdd (m * n) j)) =
            sumFin n (fun j =>
              f (finPairTransport.toFun ((0 : Fin (Nat.succ m)), j))) := by
        apply sumFin_congr
        intro j
        dsimp [f']
        apply congrArg f
        apply Fin.eq_of_val_eq
        simp
      have htail :
          sumFin (m * n) g =
            sumFin m (fun i =>
              sumFin n (fun j =>
                f (finPairTransport.toFun (i.succ, j)))) := by
        calc
          sumFin (m * n) g =
              sumFin m (fun i =>
                sumFin n (fun j => g (finPairTransport.toFun (i, j)))) :=
                sumFin_product m n g
          _ = sumFin m (fun i =>
                sumFin n (fun j =>
                  f (finPairTransport.toFun (i.succ, j)))) := by
                apply sumFin_congr
                intro i
                apply sumFin_congr
                intro j
                dsimp [g, f']
                apply congrArg f
                apply Fin.eq_of_val_eq
                simp [Nat.mul_add, Nat.add_assoc, Nat.add_comm, Nat.add_left_comm]
      calc
        sumFin (Nat.succ m * n) f
            = sumFin (n + m * n) f' := hcast
        _ = sumFin n (fun j => f' (Fin.castAdd (m * n) j)) +
              sumFin (m * n) g := hsplit
        _ = sumFin n (fun j =>
              f (finPairTransport.toFun ((0 : Fin (Nat.succ m)), j))) +
              sumFin (m * n) g := by rw [hfirst]
        _ = sumFin n (fun j =>
              f (finPairTransport.toFun ((0 : Fin (Nat.succ m)), j))) +
              sumFin m (fun i =>
                sumFin n (fun j =>
                  f (finPairTransport.toFun (i.succ, j)))) := by rw [htail]
        _ = sumFin (Nat.succ m) (fun i =>
              sumFin n (fun j => f (finPairTransport.toFun (i, j)))) := by
              rw [sumFin_succ]

end RelayTheory
