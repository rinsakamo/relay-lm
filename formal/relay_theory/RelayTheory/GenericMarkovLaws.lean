import RelayTheory.GenericStructuralKernels

namespace RelayTheory

/-- Function underlying generic classical copy. -/
def finCopyFn {n : Nat} (x : Fin n) : Fin (n * n) :=
  finPairTransport.toFun (x, x)

/-- Function underlying generic discard. -/
def finDiscardFn {n : Nat} (_ : Fin n) : Fin 1 :=
  0

/-- Copy is exactly the Dirac kernel of `finCopyFn`. -/
theorem finKernel_copy_as_dirac (n : Nat) :
    FinKernel.copy n = FinKernel.dirac (@finCopyFn n) := rfl

/-- Discard is exactly the Dirac kernel of `finDiscardFn`. -/
theorem finKernel_discard_as_dirac (n : Nat) :
    FinKernel.discard n = FinKernel.dirac (@finDiscardFn n) := rfl

/-- Equality of deterministic functions lifts to equality of their Dirac kernels. -/
theorem finKernel_dirac_congr {m n : Nat}
    (f g : Fin m → Fin n) (h : ∀ x, f x = g x) :
    FinKernel.dirac f = FinKernel.dirac g := by
  funext x y
  rw [h x]

/-- Generic copy is cocommutative at the underlying finite-function level. -/
theorem finCopyFn_cocommutative {n : Nat} (x : Fin n) :
    finSwapTransport.toFun (finCopyFn x) = finCopyFn x := by
  simp [finCopyFn, finSwapTransport, finPair_transport_roundtrip]

/-- Generic copy is coassociative up to the explicit associator transport. -/
theorem finCopyFn_coassociative {n : Nat} (x : Fin n) :
    finAssocTransport.toFun
      (finPairTransport.toFun (finCopyFn x, x)) =
      finPairTransport.toFun (x, finCopyFn x) := by
  simp [finCopyFn, finAssocTransport, finPair_transport_roundtrip]

/-- Left counit at the underlying finite-function level. -/
theorem finCopyFn_left_counit {n : Nat} (x : Fin n) :
    finLeftUnitTransport.toFun
      (finPairTransport.toFun ((0 : Fin 1), x)) = x :=
  finLeftUnitTransport.right_inv x

/-- Right counit at the underlying finite-function level. -/
theorem finCopyFn_right_counit {n : Nat} (x : Fin n) :
    finRightUnitTransport.toFun
      (finPairTransport.toFun (x, (0 : Fin 1))) = x :=
  finRightUnitTransport.right_inv x

/--
Every exact stochastic kernel is causal with respect to generic discard:
discarding after the kernel equals discarding before it.
-/
theorem finKernel_discard_causal {m n : Nat}
    {k : FinKernel m n} (hk : FinKernel.Valid k) :
    FinKernel.compose (FinKernel.discard n) k = FinKernel.discard m := by
  funext x z
  have hz : z = (0 : Fin 1) := fin_one_eq_zero z
  subst z
  unfold FinKernel.compose FinKernel.discard FinKernel.dirac
  calc
    sumFin n (fun y => k x y * (if (0 : Fin 1) = 0 then 1 else 0)) =
        sumFin n (fun y => k x y) := by
          apply sumFin_congr
          intro y
          simp
    _ = 1 := by
          have hrow := hk.2 x
          change sumFin n (fun y => k x y) = 1 at hrow
          exact hrow
    _ = (if (0 : Fin 1) = 0 then 1 else 0) := by simp

/-- Generic copy is cocommutative as an exact stochastic-kernel equation. -/
theorem finKernel_copy_cocommutative (n : Nat) :
    FinKernel.compose (FinKernel.symmetry n n) (FinKernel.copy n) =
      FinKernel.copy n := by
  change
    FinKernel.compose
      (FinKernel.dirac finSwapTransport.toFun)
      (FinKernel.dirac (@finCopyFn n)) =
      FinKernel.dirac (@finCopyFn n)
  rw [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  exact finCopyFn_cocommutative x

end RelayTheory
