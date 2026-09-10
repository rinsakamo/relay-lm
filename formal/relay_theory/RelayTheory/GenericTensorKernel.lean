import RelayTheory.GenericTensor

namespace RelayTheory

namespace FinKernel

/--
Independent tensor of two exact finite kernels, represented inside the existing
cardinality-indexed object family through the constructive product transport.
-/
def tensor {a b c d : Nat}
    (f : FinKernel a b) (g : FinKernel c d) : FinKernel (a * c) (b * d) :=
  fun x y =>
    let xi : Fin a × Fin c := finPairTransport.invFun x
    let yi : Fin b × Fin d := finPairTransport.invFun y
    f xi.1 yi.1 * g xi.2 yi.2

end FinKernel

/-- Tensor evaluation on an explicitly encoded output pair. -/
@[simp] theorem finKernel_tensor_output_encoded {a b c d : Nat}
    (f : FinKernel a b) (g : FinKernel c d)
    (x : Fin (a * c)) (y : Fin b) (v : Fin d) :
    FinKernel.tensor f g x (finPairTransport.toFun (y, v)) =
      f (finPairTransport.invFun x).1 y *
      g (finPairTransport.invFun x).2 v := by
  simp [FinKernel.tensor, finPair_transport_roundtrip]

/-- Tensor evaluation on explicitly encoded source and target pairs. -/
@[simp] theorem finKernel_tensor_encoded {a b c d : Nat}
    (f : FinKernel a b) (g : FinKernel c d)
    (x : Fin a) (u : Fin c) (y : Fin b) (v : Fin d) :
    FinKernel.tensor f g
      (finPairTransport.toFun (x, u))
      (finPairTransport.toFun (y, v)) = f x y * g u v := by
  simp [FinKernel.tensor, finPair_transport_roundtrip]

/-- Generic independent tensor preserves exact stochastic validity. -/
theorem finKernel_tensor_valid {a b c d : Nat}
    {f : FinKernel a b} {g : FinKernel c d}
    (hf : FinKernel.Valid f) (hg : FinKernel.Valid g) :
    FinKernel.Valid (FinKernel.tensor f g) := by
  constructor
  · intro x y
    unfold FinKernel.tensor
    exact Rat.mul_nonneg
      (hf.1 (finPairTransport.invFun x).1 (finPairTransport.invFun y).1)
      (hg.1 (finPairTransport.invFun x).2 (finPairTransport.invFun y).2)
  · intro x
    unfold FinKernel.rowSum
    calc
      sumFin (b * d) (fun y => FinKernel.tensor f g x y) =
          sumFin b (fun y =>
            sumFin d (fun v =>
              FinKernel.tensor f g x (finPairTransport.toFun (y, v)))) :=
            sumFin_product b d (fun y => FinKernel.tensor f g x y)
      _ = sumFin b (fun y =>
            sumFin d (fun v =>
              f (finPairTransport.invFun x).1 y *
              g (finPairTransport.invFun x).2 v)) := by
            apply sumFin_congr
            intro y
            apply sumFin_congr
            intro v
            rw [finKernel_tensor_output_encoded]
      _ = sumFin b (fun y =>
            f (finPairTransport.invFun x).1 y *
            sumFin d (fun v => g (finPairTransport.invFun x).2 v)) := by
            apply sumFin_congr
            intro y
            rw [sumFin_mul_left]
      _ = sumFin b (fun y =>
            f (finPairTransport.invFun x).1 y * 1) := by
            apply sumFin_congr
            intro y
            have hrow := hg.2 (finPairTransport.invFun x).2
            change sumFin d (fun v => g (finPairTransport.invFun x).2 v) = 1 at hrow
            rw [hrow]
      _ = sumFin b (fun y => f (finPairTransport.invFun x).1 y) := by
            apply sumFin_congr
            intro y
            rw [Rat.mul_one]
      _ = 1 := by
            have hrow := hf.2 (finPairTransport.invFun x).1
            change sumFin b (fun y => f (finPairTransport.invFun x).1 y) = 1 at hrow
            exact hrow

end RelayTheory
