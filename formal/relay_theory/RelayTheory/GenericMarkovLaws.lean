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

/-- Left unitor is exactly its transport map as a Dirac kernel. -/
theorem finKernel_leftUnitor_as_dirac (n : Nat) :
    FinKernel.leftUnitor n = FinKernel.dirac finLeftUnitTransport.toFun := rfl

/-- Right unitor is exactly its transport map as a Dirac kernel. -/
theorem finKernel_rightUnitor_as_dirac (n : Nat) :
    FinKernel.rightUnitor n = FinKernel.dirac finRightUnitTransport.toFun := rfl

/-- Associator is exactly its transport map as a Dirac kernel. -/
theorem finKernel_associator_as_dirac (a b c : Nat) :
    FinKernel.associator a b c = FinKernel.dirac finAssocTransport.toFun := rfl

/-- Equality of deterministic functions lifts to equality of their Dirac kernels. -/
theorem finKernel_dirac_congr {m n : Nat}
    (f g : Fin m → Fin n) (h : ∀ x, f x = g x) :
    FinKernel.dirac f = FinKernel.dirac g := by
  funext x y
  simp [FinKernel.dirac, h x]

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

/-- Tensoring copy with identity remains an exact deterministic map. -/
theorem finKernel_tensor_copy_identity (n : Nat) :
    FinKernel.tensor (FinKernel.copy n) (FinKernel.identity n) =
      FinKernel.dirac (fun q : Fin (n * n) =>
        finPairTransport.toFun
          (finCopyFn (finPairTransport.invFun q).1,
           (finPairTransport.invFun q).2)) := by
  rw [finKernel_copy_as_dirac n, finKernel_identity_eq_dirac_id n]
  rw [finKernel_tensor_dirac]
  apply finKernel_dirac_congr
  intro q
  rfl

/-- Tensoring identity with copy remains an exact deterministic map. -/
theorem finKernel_tensor_identity_copy (n : Nat) :
    FinKernel.tensor (FinKernel.identity n) (FinKernel.copy n) =
      FinKernel.dirac (fun q : Fin (n * n) =>
        finPairTransport.toFun
          ((finPairTransport.invFun q).1,
           finCopyFn (finPairTransport.invFun q).2)) := by
  rw [finKernel_identity_eq_dirac_id n, finKernel_copy_as_dirac n]
  rw [finKernel_tensor_dirac]
  apply finKernel_dirac_congr
  intro q
  rfl

/-- Generic copy is coassociative up to the explicit associator kernel. -/
theorem finKernel_copy_coassociative (n : Nat) :
    FinKernel.compose (FinKernel.associator n n n)
        (FinKernel.compose
          (FinKernel.tensor (FinKernel.copy n) (FinKernel.identity n))
          (FinKernel.copy n)) =
      FinKernel.compose
        (FinKernel.tensor (FinKernel.identity n) (FinKernel.copy n))
        (FinKernel.copy n) := by
  rw [finKernel_tensor_copy_identity, finKernel_tensor_identity_copy]
  rw [finKernel_associator_as_dirac, finKernel_copy_as_dirac]
  simp only [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  simp [finCopyFn, finAssocTransport, finPair_transport_roundtrip]

/-- Tensoring discard with identity remains deterministic. -/
theorem finKernel_tensor_discard_identity (n : Nat) :
    FinKernel.tensor (FinKernel.discard n) (FinKernel.identity n) =
      FinKernel.dirac (fun q : Fin (n * n) =>
        finPairTransport.toFun
          ((0 : Fin 1), (finPairTransport.invFun q).2)) := by
  rw [finKernel_discard_as_dirac n, finKernel_identity_eq_dirac_id n]
  rw [finKernel_tensor_dirac]
  apply finKernel_dirac_congr
  intro q
  rfl

/-- Tensoring identity with discard remains deterministic. -/
theorem finKernel_tensor_identity_discard (n : Nat) :
    FinKernel.tensor (FinKernel.identity n) (FinKernel.discard n) =
      FinKernel.dirac (fun q : Fin (n * n) =>
        finPairTransport.toFun
          ((finPairTransport.invFun q).1, (0 : Fin 1))) := by
  rw [finKernel_identity_eq_dirac_id n, finKernel_discard_as_dirac n]
  rw [finKernel_tensor_dirac]
  apply finKernel_dirac_congr
  intro q
  rfl

/-- Generic copy satisfies the left counit equation. -/
theorem finKernel_copy_left_counit (n : Nat) :
    FinKernel.compose (FinKernel.leftUnitor n)
        (FinKernel.compose
          (FinKernel.tensor (FinKernel.discard n) (FinKernel.identity n))
          (FinKernel.copy n)) =
      FinKernel.identity n := by
  rw [finKernel_tensor_discard_identity]
  rw [finKernel_leftUnitor_as_dirac, finKernel_copy_as_dirac]
  rw [finKernel_identity_eq_dirac_id]
  simp only [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  simp [finCopyFn, finLeftUnitTransport, finPair_transport_roundtrip]

/-- Generic copy satisfies the right counit equation. -/
theorem finKernel_copy_right_counit (n : Nat) :
    FinKernel.compose (FinKernel.rightUnitor n)
        (FinKernel.compose
          (FinKernel.tensor (FinKernel.identity n) (FinKernel.discard n))
          (FinKernel.copy n)) =
      FinKernel.identity n := by
  rw [finKernel_tensor_identity_discard]
  rw [finKernel_rightUnitor_as_dirac, finKernel_copy_as_dirac]
  rw [finKernel_identity_eq_dirac_id]
  simp only [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  simp [finCopyFn, finRightUnitTransport, finPair_transport_roundtrip]

/-- Every deterministic finite map preserves the generic classical copy. -/
theorem finKernel_deterministic_preserves_copy {m n : Nat}
    (f : Fin m → Fin n) :
    FinKernel.compose (FinKernel.copy n) (FinKernel.dirac f) =
      FinKernel.compose
        (FinKernel.tensor (FinKernel.dirac f) (FinKernel.dirac f))
        (FinKernel.copy m) := by
  rw [finKernel_copy_as_dirac n, finKernel_copy_as_dirac m]
  rw [finKernel_tensor_dirac]
  simp only [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  simp [finCopyFn, finPair_transport_roundtrip]

/-- A generic exact fair state on a two-point finite interface. -/
def finFairKernel : FinKernel 1 2 :=
  fun _ _ => qHalf

/-- The generic exact fair state is stochastic-valid. -/
theorem finFairKernel_valid : FinKernel.Valid finFairKernel := by
  constructor
  · intro x y
    exact Rat.le_of_lt qHalf_pos
  · intro x
    unfold FinKernel.rowSum finFairKernel
    grind [sumFin, qHalf]

/--
Generic negative control: one fair draw followed by copy is not two independent
fair draws. Copy therefore remains classical deterministic structure, not a
natural operation of arbitrary stochastic maps.
-/
theorem finKernel_fair_copy_ne_independent :
    FinKernel.compose (FinKernel.copy 2) finFairKernel ≠
      FinKernel.tensor finFairKernel finFairKernel := by
  intro h
  let src : Fin (1 * 1) :=
    finPairTransport.toFun ((0 : Fin 1), (0 : Fin 1))
  let target : Fin (2 * 2) :=
    finPairTransport.toFun ((0 : Fin 2), (1 : Fin 2))
  have hOff : ∀ y : Fin 2, target ≠ finCopyFn y := by
    intro y hy
    have hd := congrArg (fun z => finPairTransport.invFun z) hy
    have hpair : ((0 : Fin 2), (1 : Fin 2)) = (y, y) := by
      simpa [target, finCopyFn, finPair_transport_roundtrip] using hd
    have h0y := congrArg Prod.fst hpair
    have h1y := congrArg Prod.snd hpair
    have h01 : (0 : Fin 2) = (1 : Fin 2) := h0y.trans h1y.symm
    have hv := congrArg Fin.val h01
    grind
  have hleft :
      FinKernel.compose (FinKernel.copy 2) finFairKernel src target = 0 := by
    unfold FinKernel.compose
    calc
      sumFin 2 (fun y => finFairKernel src y * FinKernel.copy 2 y target) =
          sumFin 2 (fun _ => 0) := by
            apply sumFin_congr
            intro y
            simp [FinKernel.copy, FinKernel.dirac, finFairKernel,
              finCopyFn, hOff y]
      _ = 0 := by grind [sumFin]
  have hright :
      FinKernel.tensor finFairKernel finFairKernel src target = qHalf * qHalf := by
    simpa [src, target, finFairKernel] using
      (finKernel_tensor_encoded finFairKernel finFairKernel
        (0 : Fin 1) (0 : Fin 1) (0 : Fin 2) (1 : Fin 2))
  have hv := congrFun (congrFun h src) target
  rw [hleft, hright] at hv
  grind [qHalf]

end RelayTheory
