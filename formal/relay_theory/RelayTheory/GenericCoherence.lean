import RelayTheory.GenericInterchange

namespace RelayTheory

/-- Every inhabitant of `Fin 1` is the unique zero index. -/
theorem fin_one_eq_zero (i : Fin 1) : i = 0 := by
  apply Fin.eq_of_val_eq
  grind

/--
The pair transport right round-trip, exposed in component form so nested
coherence proofs do not depend on product eta being a definitional reduction.
-/
theorem finPair_flatten_components {m n : Nat} (x : Fin (m * n)) :
    finPairTransport.toFun
      ((finPairTransport.invFun x).1, (finPairTransport.invFun x).2) = x := by
  simpa using finPair_flatten_roundtrip x

/-- Explicit symmetry transport for the cardinal-indexed product objects. -/
def finSwapTransport {m n : Nat} :
    FiniteTransport (Fin (m * n)) (Fin (n * m)) where
  toFun x :=
    let p : Fin m × Fin n := finPairTransport.invFun x
    finPairTransport.toFun (p.2, p.1)
  invFun y :=
    let p : Fin n × Fin m := finPairTransport.invFun y
    finPairTransport.toFun (p.2, p.1)
  left_inv := by
    intro x
    simp [finPair_transport_roundtrip, finPair_flatten_components]
  right_inv := by
    intro y
    simp [finPair_transport_roundtrip, finPair_flatten_components]

/-- Explicit left-unitor transport `Fin (1*n) <-> Fin n`. -/
def finLeftUnitTransport {n : Nat} :
    FiniteTransport (Fin (1 * n)) (Fin n) where
  toFun x := (finPairTransport.invFun x).2
  invFun y := finPairTransport.toFun ((0 : Fin 1), y)
  left_inv := by
    intro x
    let p : Fin 1 × Fin n := finPairTransport.invFun x
    have hp : (0 : Fin 1) = p.1 := (fin_one_eq_zero p.1).symm
    change finPairTransport.toFun ((0 : Fin 1), p.2) = x
    rw [hp]
    exact finPair_flatten_components x
  right_inv := by
    intro y
    have h := finPair_transport_roundtrip ((0 : Fin 1), y)
    exact congrArg Prod.snd h

/-- Explicit right-unitor transport `Fin (n*1) <-> Fin n`. -/
def finRightUnitTransport {n : Nat} :
    FiniteTransport (Fin (n * 1)) (Fin n) where
  toFun x := (finPairTransport.invFun x).1
  invFun y := finPairTransport.toFun (y, (0 : Fin 1))
  left_inv := by
    intro x
    let p : Fin n × Fin 1 := finPairTransport.invFun x
    have hp : (0 : Fin 1) = p.2 := (fin_one_eq_zero p.2).symm
    change finPairTransport.toFun (p.1, (0 : Fin 1)) = x
    rw [hp]
    exact finPair_flatten_components x
  right_inv := by
    intro y
    have h := finPair_transport_roundtrip (y, (0 : Fin 1))
    exact congrArg Prod.fst h

/--
Explicit associator transport. Parenthesization is not treated as definitional
object equality: the map is built by decode/reassociate/encode.
-/
def finAssocTransport {a b c : Nat} :
    FiniteTransport (Fin ((a * b) * c)) (Fin (a * (b * c))) where
  toFun x :=
    let p : Fin (a * b) × Fin c := finPairTransport.invFun x
    let ab : Fin a × Fin b := finPairTransport.invFun p.1
    finPairTransport.toFun (ab.1, finPairTransport.toFun (ab.2, p.2))
  invFun y :=
    let p : Fin a × Fin (b * c) := finPairTransport.invFun y
    let bc : Fin b × Fin c := finPairTransport.invFun p.2
    finPairTransport.toFun (finPairTransport.toFun (p.1, bc.1), bc.2)
  left_inv := by
    intro x
    simp [finPair_transport_roundtrip, finPair_flatten_components]
  right_inv := by
    intro y
    simp [finPair_transport_roundtrip, finPair_flatten_components]

/-- Product map induced by two finite functions under the explicit flattening transport. -/
def finTensorMap {a b c d : Nat}
    (f : Fin a → Fin b) (g : Fin c → Fin d) :
    Fin (a * c) → Fin (b * d) :=
  fun q =>
    finPairTransport.toFun
      (f (finPairTransport.invFun q).1,
       g (finPairTransport.invFun q).2)

@[simp] theorem finTensorMap_encoded {a b c d : Nat}
    (f : Fin a → Fin b) (g : Fin c → Fin d)
    (x : Fin a) (u : Fin c) :
    finTensorMap f g (finPairTransport.toFun (x, u)) =
      finPairTransport.toFun (f x, g u) := by
  simp [finTensorMap, finPair_transport_roundtrip]

/-- Symmetry is natural with respect to arbitrary finite deterministic maps. -/
theorem finSwap_natural {a b c d : Nat}
    (f : Fin a → Fin b) (g : Fin c → Fin d) (x : Fin (a * c)) :
    finSwapTransport.toFun (finTensorMap f g x) =
      finTensorMap g f (finSwapTransport.toFun x) := by
  simp [finSwapTransport, finTensorMap, finPair_transport_roundtrip]

/-- Associator is natural with respect to arbitrary finite deterministic maps. -/
theorem finAssoc_natural
    {a a' b b' c c' : Nat}
    (f : Fin a → Fin a') (g : Fin b → Fin b') (h : Fin c → Fin c')
    (x : Fin ((a * b) * c)) :
    finAssocTransport.toFun (finTensorMap (finTensorMap f g) h x) =
      finTensorMap f (finTensorMap g h) (finAssocTransport.toFun x) := by
  simp [finAssocTransport, finTensorMap, finPair_transport_roundtrip,
    finPair_flatten_components]

/-- Triangle coherence for the explicit associator and unitors. -/
theorem finMonoidal_triangle {a b : Nat} (x : Fin ((a * 1) * b)) :
    finTensorMap (fun z : Fin a => z) finLeftUnitTransport.toFun
        (finAssocTransport.toFun x) =
      finTensorMap finRightUnitTransport.toFun (fun z : Fin b => z) x := by
  simp [finAssocTransport, finTensorMap, finLeftUnitTransport,
    finRightUnitTransport, finPair_transport_roundtrip,
    finPair_flatten_components]

/-- Pentagon coherence for the explicit cardinal product associator. -/
theorem finMonoidal_pentagon {a b c d : Nat}
    (x : Fin (((a * b) * c) * d)) :
    finAssocTransport.toFun (finAssocTransport.toFun x) =
      finTensorMap (fun z : Fin a => z) finAssocTransport.toFun
        (finAssocTransport.toFun
          (finTensorMap finAssocTransport.toFun (fun z : Fin d => z) x)) := by
  simp [finAssocTransport, finTensorMap, finPair_transport_roundtrip,
    finPair_flatten_components]

/-- Symmetry transport is an exact involution at the flattened interface level. -/
theorem finSwap_transport_roundtrip {m n : Nat} (x : Fin (m * n)) :
    finSwapTransport.invFun (finSwapTransport.toFun x) = x :=
  finSwapTransport.left_inv x

/-- Left-unitor transport round-trips exactly. -/
theorem finLeftUnit_transport_roundtrip {n : Nat} (x : Fin (1 * n)) :
    finLeftUnitTransport.invFun (finLeftUnitTransport.toFun x) = x :=
  finLeftUnitTransport.left_inv x

/-- Right-unitor transport round-trips exactly. -/
theorem finRightUnit_transport_roundtrip {n : Nat} (x : Fin (n * 1)) :
    finRightUnitTransport.invFun (finRightUnitTransport.toFun x) = x :=
  finRightUnitTransport.left_inv x

/-- Associator transport round-trips exactly in the forward direction. -/
theorem finAssoc_transport_roundtrip {a b c : Nat} (x : Fin ((a * b) * c)) :
    finAssocTransport.invFun (finAssocTransport.toFun x) = x :=
  finAssocTransport.left_inv x

/-- Associator transport round-trips exactly in the reverse direction. -/
theorem finAssoc_flatten_roundtrip {a b c : Nat} (x : Fin (a * (b * c))) :
    finAssocTransport.toFun (finAssocTransport.invFun x) = x :=
  finAssocTransport.right_inv x

end RelayTheory
