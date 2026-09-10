import Lean.Elab.Tactic.Grind

namespace RelayTheory

/--
Minimal finite partial-order interface used only as an operational causal /
recoverability-order test surface. No spacetime interpretation is built in.
-/
structure FiniteCausalOrder (n : Nat) where
  rel : Fin n → Fin n → Prop
  refl : ∀ x, rel x x
  antisymm : ∀ {x y}, rel x y → rel y x → x = y
  trans : ∀ {x y z}, rel x y → rel y z → rel x z

/-- Every pair is causally comparable in at least one direction. -/
def CausalTotal {n : Nat} (P : FiniteCausalOrder n) : Prop :=
  ∀ x y, P.rel x y ∨ P.rel y x

/-- Neither direction of the source causal order compares the two events. -/
def CausalIncomparable {n : Nat} (P : FiniteCausalOrder n) (x y : Fin n) : Prop :=
  ¬ P.rel x y ∧ ¬ P.rel y x

/-- A scalar timestamp respects every source causal comparison. -/
def ScalarOrderPreserving {n m : Nat} (P : FiniteCausalOrder n)
    (time : Fin n → Fin m) : Prop :=
  ∀ x y, P.rel x y → (time x).1 ≤ (time y).1

/-- Every comparison made by the scalar chain was already a source causal comparison. -/
def ScalarOrderReflecting {n m : Nat} (P : FiniteCausalOrder n)
    (time : Fin n → Fin m) : Prop :=
  ∀ x y, (time x).1 ≤ (time y).1 → P.rel x y

/-- Exact one-chain representation: preserve and reflect the source order. -/
def FaithfulScalarTime {n m : Nat} (P : FiniteCausalOrder n)
    (time : Fin n → Fin m) : Prop :=
  ScalarOrderPreserving P time ∧ ScalarOrderReflecting P time

/--
A faithful scalar-chain representation forces the source causal order itself to
be total. Target-chain comparability is reflected back to every source pair.
-/
theorem faithfulScalarTime_forces_total {n m : Nat} {P : FiniteCausalOrder n}
    {time : Fin n → Fin m} (h : FaithfulScalarTime P time) :
    CausalTotal P := by
  intro x y
  rcases Nat.le_total (time x).1 (time y).1 with hxy | hyx
  · exact Or.inl (h.2 x y hxy)
  · exact Or.inr (h.2 y x hyx)

/-- Equal scalar timestamps cannot identify distinct source events under fidelity. -/
theorem faithfulScalarTime_injective {n m : Nat} {P : FiniteCausalOrder n}
    {time : Fin n → Fin m} (h : FaithfulScalarTime P time) :
    Function.Injective time := by
  intro x y hxy
  apply P.antisymm
  · apply h.2 x y
    exact Nat.le_of_eq (congrArg Fin.val hxy)
  · apply h.2 y x
    exact Nat.le_of_eq (congrArg Fin.val hxy).symm

/--
Four-event diamond relation: event 0 is a common past, event 3 a common future,
and middle events 1 and 2 are incomparable.
-/
def diamondCausalRel (x y : Fin 4) : Prop :=
  x.1 = y.1 ∨ x.1 = 0 ∨ y.1 = 3

/-- The four-event diamond is an exact finite partial order. -/
def diamondCausalOrder : FiniteCausalOrder 4 where
  rel := diamondCausalRel
  refl := by
    intro x
    exact Or.inl rfl
  antisymm := by
    intro x y hxy hyx
    apply Fin.eq_of_val_eq
    unfold diamondCausalRel at hxy hyx
    have hx := x.isLt
    have hy := y.isLt
    grind
  trans := by
    intro x y z hxy hyz
    unfold diamondCausalRel at hxy hyz ⊢
    have hx := x.isLt
    have hy := y.isLt
    have hz := z.isLt
    grind

/-- The two middle diamond events are genuinely incomparable. -/
theorem diamond_middle_incomparable :
    CausalIncomparable diamondCausalOrder (1 : Fin 4) (2 : Fin 4) := by
  simp [CausalIncomparable, diamondCausalOrder, diamondCausalRel]

/-- Hence the diamond causal order is not total. -/
theorem diamond_not_total : ¬ CausalTotal diamondCausalOrder := by
  intro h
  rcases h (1 : Fin 4) (2 : Fin 4) with h12 | h21
  · exact diamond_middle_incomparable.1 h12
  · exact diamond_middle_incomparable.2 h21

/-- No scalar finite chain can faithfully preserve and reflect the diamond order. -/
theorem diamond_rejects_faithful_scalar_time (m : Nat) :
    ¬ ∃ time : Fin 4 → Fin m, FaithfulScalarTime diamondCausalOrder time := by
  intro h
  rcases h with ⟨time, htime⟩
  exact diamond_not_total (faithfulScalarTime_forces_total htime)

/-- One perfectly ordinary serial execution order for the diamond. -/
def diamondSerializationA : Fin 4 → Fin 4 := fun x => x

/-- The serial order respects every diamond causal arrow. -/
theorem diamond_serialization_order_preserving :
    ScalarOrderPreserving diamondCausalOrder diamondSerializationA := by
  intro x y hxy
  change x.1 ≤ y.1
  change diamondCausalRel x y at hxy
  unfold diamondCausalRel at hxy
  have hx := x.isLt
  have hy := y.isLt
  grind

/-- But the same serial order invents the middle comparison 1 < 2. -/
theorem diamond_serialization_not_order_reflecting :
    ¬ ScalarOrderReflecting diamondCausalOrder diamondSerializationA := by
  intro h
  have h12 : diamondCausalOrder.rel (1 : Fin 4) (2 : Fin 4) := by
    apply h (1 : Fin 4) (2 : Fin 4)
    decide
  exact diamond_middle_incomparable.1 h12

/--
Native finite scalar order, used as a positive control showing that faithful
scalar representation is available when the source order is already chain-like.
-/
def finiteNativeChain (n : Nat) : FiniteCausalOrder n where
  rel := fun x y => x.1 ≤ y.1
  refl := by
    intro x
    exact Nat.le_refl x.1
  antisymm := by
    intro x y hxy hyx
    apply Fin.eq_of_val_eq
    exact Nat.le_antisymm hxy hyx
  trans := by
    intro x y z hxy hyz
    exact Nat.le_trans hxy hyz

/-- Identity scalar coordinate faithfully represents the native finite chain. -/
theorem finiteNativeChain_identity_faithful (n : Nat) :
    FaithfulScalarTime (finiteNativeChain n) (fun x : Fin n => x) := by
  constructor
  · intro x y hxy
    exact hxy
  · intro x y hxy
    exact hxy

/-- The positive-control source really is total. -/
theorem finiteNativeChain_total (n : Nat) : CausalTotal (finiteNativeChain n) := by
  intro x y
  exact Nat.le_total x.1 y.1

/--
Minimal discriminator earned by this interface: serializability can preserve all
causal arrows while failing to preserve the absence of an arrow.
-/
theorem diamond_preserving_but_not_faithful :
    ScalarOrderPreserving diamondCausalOrder diamondSerializationA ∧
      ¬ ScalarOrderReflecting diamondCausalOrder diamondSerializationA := by
  exact ⟨diamond_serialization_order_preserving,
    diamond_serialization_not_order_reflecting⟩

end RelayTheory
