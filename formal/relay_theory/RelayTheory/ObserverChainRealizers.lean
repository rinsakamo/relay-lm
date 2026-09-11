import RelayTheory.CausalOrderProjection

namespace RelayTheory

/--
Comparison that survives every observer-local scalar chain.  The source causal
relation is deliberately absent from this definition.
-/
def ObserverInvariantRel {r n m : Nat}
    (time : Fin r → Fin n → Fin m) (x y : Fin n) : Prop :=
  ∀ o, (time o x).1 ≤ (time o y).1

/-- A family of scalar observer chains exactly reconstructs a finite causal order. -/
def ObserverFamilyRealizes {r n m : Nat} (P : FiniteCausalOrder n)
    (time : Fin r → Fin n → Fin m) : Prop :=
  ∀ x y, P.rel x y ↔ ObserverInvariantRel time x y

/-- With no observers, the induced relation is vacuously universal. -/
theorem observerInvariantRel_empty {n m : Nat}
    (time : Fin 0 → Fin n → Fin m) (x y : Fin n) :
    ObserverInvariantRel time x y := by
  intro o
  exact Fin.elim0 o

/-- The empty observer family therefore cannot exactly realize the diamond. -/
theorem diamond_no_empty_observer_realizer (m : Nat) :
    ¬ ∃ time : Fin 0 → Fin 4 → Fin m,
      ObserverFamilyRealizes diamondCausalOrder time := by
  intro h
  rcases h with ⟨time, htime⟩
  have h12 : diamondCausalOrder.rel (1 : Fin 4) (2 : Fin 4) :=
    (htime (1 : Fin 4) (2 : Fin 4)).2
      (observerInvariantRel_empty time (1 : Fin 4) (2 : Fin 4))
  exact diamond_middle_incomparable.1 h12

/-- Read the unique observer of a one-observer family as an ordinary scalar time. -/
def oneObserverScalar {n m : Nat} (time : Fin 1 → Fin n → Fin m) :
    Fin n → Fin m :=
  fun x => time (0 : Fin 1) x

/-- Exact realization by one observer is exactly the faithful scalar condition of #2540. -/
theorem observerFamilyRealizes_one_iff_faithfulScalarTime
    {n m : Nat} {P : FiniteCausalOrder n} {time : Fin 1 → Fin n → Fin m} :
    ObserverFamilyRealizes P time ↔ FaithfulScalarTime P (oneObserverScalar time) := by
  constructor
  · intro h
    constructor
    · intro x y hxy
      exact (h x y).1 hxy (0 : Fin 1)
    · intro x y hxy
      apply (h x y).2
      intro o
      have ho : o = (0 : Fin 1) := by
        apply Fin.eq_of_val_eq
        have hlt := o.isLt
        grind
      subst o
      exact hxy
  · intro h x y
    constructor
    · intro hxy o
      have ho : o = (0 : Fin 1) := by
        apply Fin.eq_of_val_eq
        have hlt := o.isLt
        grind
      subst o
      exact h.1 x y hxy
    · intro hxy
      exact h.2 x y (hxy (0 : Fin 1))

/-- Consequently any exactly realizing one-observer family forces source totality. -/
theorem observerFamilyRealizes_one_forces_total
    {n m : Nat} {P : FiniteCausalOrder n} {time : Fin 1 → Fin n → Fin m}
    (h : ObserverFamilyRealizes P time) : CausalTotal P := by
  exact faithfulScalarTime_forces_total
    ((observerFamilyRealizes_one_iff_faithfulScalarTime).1 h)

/-- The diamond cannot be reconstructed by a single observer chain. -/
theorem diamond_requires_more_than_one_observer (m : Nat) :
    ¬ ∃ time : Fin 1 → Fin 4 → Fin m,
      ObserverFamilyRealizes diamondCausalOrder time := by
  intro h
  rcases h with ⟨time, htime⟩
  exact diamond_not_total (observerFamilyRealizes_one_forces_total htime)

/-- First diamond observer: past < a < b < future. -/
def diamondObserverA : Fin 4 → Fin 4 := fun x => x

/-- Second diamond observer: past < b < a < future. -/
def diamondObserverB (x : Fin 4) : Fin 4 :=
  if x = (1 : Fin 4) then (2 : Fin 4)
  else if x = (2 : Fin 4) then (1 : Fin 4)
  else x

/-- Observer B preserves every genuine diamond causal comparison. -/
theorem diamondObserverB_order_preserving :
    ScalarOrderPreserving diamondCausalOrder diamondObserverB := by
  intro x y hxy
  change diamondCausalRel x y at hxy
  rcases hxy with hxy | hx | hy
  · have hxy' : x = y := Fin.eq_of_val_eq hxy
    subst y
    exact Nat.le_refl _
  · have hx' : x = (0 : Fin 4) := Fin.eq_of_val_eq hx
    subst x
    simp [diamondObserverB]
  · have hy' : y = (3 : Fin 4) := Fin.eq_of_val_eq hy
    subst y
    have hlt := (diamondObserverB x).isLt
    change (diamondObserverB x).1 ≤ 3
    grind

/-- The two observer-local scalar rankings used to realize the diamond. -/
def diamondObserverTime (o : Fin 2) (x : Fin 4) : Fin 4 :=
  if o = (0 : Fin 2) then diamondObserverA x else diamondObserverB x

/-- The middle pair is ordered one way by observer A. -/
theorem diamond_observerA_middle_forward :
    (diamondObserverTime (0 : Fin 2) (1 : Fin 4)).1 <
      (diamondObserverTime (0 : Fin 2) (2 : Fin 4)).1 := by
  decide

/-- The middle pair is ordered the opposite way by observer B. -/
theorem diamond_observerB_middle_reverse :
    (diamondObserverTime (1 : Fin 2) (2 : Fin 4)).1 <
      (diamondObserverTime (1 : Fin 2) (1 : Fin 4)).1 := by
  decide

/--
The intersection of the two observer chains is exactly the four-event diamond.
No source causal metadata is used by `ObserverInvariantRel`.
-/
theorem two_chain_observers_exactly_realize_diamond :
    ObserverFamilyRealizes diamondCausalOrder diamondObserverTime := by
  intro x y
  constructor
  · intro hxy o
    by_cases ho : o = (0 : Fin 2)
    · subst o
      have hA := diamond_serialization_order_preserving x y hxy
      simpa [diamondObserverTime, diamondObserverA, diamondSerializationA] using hA
    · have hB := diamondObserverB_order_preserving x y hxy
      simpa [diamondObserverTime, ho] using hB
  · intro hobs
    have hA : x.1 ≤ y.1 := by
      simpa [diamondObserverTime, diamondObserverA] using hobs (0 : Fin 2)
    have hB : (diamondObserverB x).1 ≤ (diamondObserverB y).1 := by
      simpa [diamondObserverTime] using hobs (1 : Fin 2)
    change diamondCausalRel x y
    by_cases hxy : x.1 = y.1
    · exact Or.inl hxy
    by_cases hx0 : x.1 = 0
    · exact Or.inr (Or.inl hx0)
    by_cases hy3 : y.1 = 3
    · exact Or.inr (Or.inr hy3)
    have hxlt := x.isLt
    have hylt := y.isLt
    have hx1 : x.1 = 1 := by grind
    have hy2 : y.1 = 2 := by grind
    have hx' : x = (1 : Fin 4) := Fin.eq_of_val_eq hx1
    have hy' : y = (2 : Fin 4) := Fin.eq_of_val_eq hy2
    subst x
    subst y
    simp [diamondObserverB] at hB

/-- Both observers preserve every common-past comparison. -/
theorem diamond_observers_agree_common_past (o : Fin 2) (x : Fin 4) :
    (diamondObserverTime o (0 : Fin 4)).1 ≤ (diamondObserverTime o x).1 := by
  have hrel : diamondCausalOrder.rel (0 : Fin 4) x := by
    change diamondCausalRel (0 : Fin 4) x
    exact Or.inr (Or.inl rfl)
  exact (two_chain_observers_exactly_realize_diamond (0 : Fin 4) x).1 hrel o

/-- Both observers preserve every common-future comparison. -/
theorem diamond_observers_agree_common_future (o : Fin 2) (x : Fin 4) :
    (diamondObserverTime o x).1 ≤ (diamondObserverTime o (3 : Fin 4)).1 := by
  have hrel : diamondCausalOrder.rel x (3 : Fin 4) := by
    change diamondCausalRel x (3 : Fin 4)
    exact Or.inr (Or.inr rfl)
  exact (two_chain_observers_exactly_realize_diamond x (3 : Fin 4)).1 hrel o

/-- The two observer chains disagree exactly enough to remove the middle comparison. -/
theorem observer_disagreement_recovers_diamond_incomparability :
    (diamondObserverTime (0 : Fin 2) (1 : Fin 4)).1 <
        (diamondObserverTime (0 : Fin 2) (2 : Fin 4)).1 ∧
      (diamondObserverTime (1 : Fin 2) (2 : Fin 4)).1 <
        (diamondObserverTime (1 : Fin 2) (1 : Fin 4)).1 ∧
      CausalIncomparable diamondCausalOrder (1 : Fin 4) (2 : Fin 4) := by
  exact ⟨diamond_observerA_middle_forward,
    diamond_observerB_middle_reverse,
    diamond_middle_incomparable⟩

/-- One observer is enough when the source order is already a chain. -/
def nativeSingleObserverTime (n : Nat) : Fin 1 → Fin n → Fin n :=
  fun _ x => x

/-- Positive control: a native total order is exactly realized by one observer. -/
theorem nativeSingleObserver_realizes (n : Nat) :
    ObserverFamilyRealizes (finiteNativeChain n) (nativeSingleObserverTime n) := by
  intro x y
  constructor
  · intro h o
    exact h
  · intro h
    exact h (0 : Fin 1)

/-- Duplicating a consistent observer also preserves exact realization. -/
def nativeTwoObserverTime (n : Nat) : Fin 2 → Fin n → Fin n :=
  fun _ x => x

/-- Positive control: disagreement is not required for observer-family realization. -/
theorem nativeTwoObserver_realizes (n : Nat) :
    ObserverFamilyRealizes (finiteNativeChain n) (nativeTwoObserverTime n) := by
  intro x y
  constructor
  · intro h o
    exact h
  · intro h
    exact h (0 : Fin 2)

end RelayTheory
