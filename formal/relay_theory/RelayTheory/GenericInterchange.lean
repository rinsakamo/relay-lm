import RelayTheory.GenericTensorKernel

namespace RelayTheory

/-- Finite separability of an independent product of two exact summands. -/
theorem sumFin_separable_product {m n : Nat}
    (f : Fin m → Rat) (g : Fin n → Rat) :
    sumFin m (fun i => sumFin n (fun j => f i * g j)) =
      sumFin m f * sumFin n g := by
  calc
    sumFin m (fun i => sumFin n (fun j => f i * g j)) =
        sumFin m (fun i => f i * sumFin n g) := by
          apply sumFin_congr
          intro i
          rw [sumFin_mul_left]
    _ = sumFin m f * sumFin n g :=
          sumFin_mul_right m f (sumFin n g)

/-- Tensor evaluation on an explicitly encoded source pair. -/
@[simp] theorem finKernel_tensor_source_encoded {a b c d : Nat}
    (f : FinKernel a b) (g : FinKernel c d)
    (x : Fin a) (u : Fin c) (y : Fin (b * d)) :
    FinKernel.tensor f g (finPairTransport.toFun (x, u)) y =
      f x (finPairTransport.invFun y).1 *
      g u (finPairTransport.invFun y).2 := by
  simp [FinKernel.tensor, finPair_transport_roundtrip]

/--
Generic interchange/bifunctoriality of independent tensor with exact finite
stochastic composition. No category or monoidal library is assumed.
-/
theorem finKernel_tensor_interchange {a b c d e f : Nat}
    (g1 : FinKernel a b) (g2 : FinKernel b c)
    (h1 : FinKernel d e) (h2 : FinKernel e f) :
    FinKernel.compose (FinKernel.tensor g2 h2) (FinKernel.tensor g1 h1) =
      FinKernel.tensor (FinKernel.compose g2 g1) (FinKernel.compose h2 h1) := by
  funext x z
  change
    sumFin (b * e) (fun q =>
      FinKernel.tensor g1 h1 x q * FinKernel.tensor g2 h2 q z) =
      FinKernel.tensor (FinKernel.compose g2 g1) (FinKernel.compose h2 h1) x z
  calc
    sumFin (b * e) (fun q =>
        FinKernel.tensor g1 h1 x q * FinKernel.tensor g2 h2 q z) =
      sumFin b (fun y => sumFin e (fun v =>
        FinKernel.tensor g1 h1 x (finPairTransport.toFun (y, v)) *
        FinKernel.tensor g2 h2 (finPairTransport.toFun (y, v)) z)) :=
        sumFin_product b e (fun q =>
          FinKernel.tensor g1 h1 x q * FinKernel.tensor g2 h2 q z)
    _ = sumFin b (fun y => sumFin e (fun v =>
          (g1 (finPairTransport.invFun x).1 y *
            h1 (finPairTransport.invFun x).2 v) *
          (g2 y (finPairTransport.invFun z).1 *
            h2 v (finPairTransport.invFun z).2))) := by
          apply sumFin_congr
          intro y
          apply sumFin_congr
          intro v
          rw [finKernel_tensor_output_encoded, finKernel_tensor_source_encoded]
    _ = sumFin b (fun y => sumFin e (fun v =>
          (g1 (finPairTransport.invFun x).1 y *
            g2 y (finPairTransport.invFun z).1) *
          (h1 (finPairTransport.invFun x).2 v *
            h2 v (finPairTransport.invFun z).2))) := by
          apply sumFin_congr
          intro y
          apply sumFin_congr
          intro v
          grind
    _ = sumFin b (fun y =>
          g1 (finPairTransport.invFun x).1 y *
          g2 y (finPairTransport.invFun z).1) *
        sumFin e (fun v =>
          h1 (finPairTransport.invFun x).2 v *
          h2 v (finPairTransport.invFun z).2) :=
          sumFin_separable_product
            (fun y =>
              g1 (finPairTransport.invFun x).1 y *
              g2 y (finPairTransport.invFun z).1)
            (fun v =>
              h1 (finPairTransport.invFun x).2 v *
              h2 v (finPairTransport.invFun z).2)
    _ = FinKernel.compose g2 g1
          (finPairTransport.invFun x).1 (finPairTransport.invFun z).1 *
        FinKernel.compose h2 h1
          (finPairTransport.invFun x).2 (finPairTransport.invFun z).2 := by
          rfl
    _ = FinKernel.tensor (FinKernel.compose g2 g1) (FinKernel.compose h2 h1) x z := by
          rfl

end RelayTheory
