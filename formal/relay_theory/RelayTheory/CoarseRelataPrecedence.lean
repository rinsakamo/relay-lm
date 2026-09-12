import Lean.Elab.Tactic.Grind

namespace RelayTheory

/-- Strict precedence on a finite one-dimensional fine event order. -/
def FinePrecedes {n : Nat} (x y : Fin n) : Prop :=
  x.1 < y.1

/-- Fine strict precedence is irreflexive. -/
theorem finePrecedes_irrefl {n : Nat} (x : Fin n) :
    ¬ FinePrecedes x x := by
  intro h
  exact Nat.lt_irrefl x.1 h

/-- Fine strict precedence is transitive. -/
theorem finePrecedes_trans {n : Nat} {x y z : Fin n}
    (hxy : FinePrecedes x y) (hyz : FinePrecedes y z) :
    FinePrecedes x z := by
  exact Nat.lt_trans hxy hyz

/-- A fine strict pair cannot simultaneously point in both directions. -/
theorem finePrecedes_not_two_way {n : Nat} {x y : Fin n}
    (hxy : FinePrecedes x y) : ¬ FinePrecedes y x := by
  intro hyx
  exact Nat.not_lt_of_ge (Nat.le_of_lt hxy) hyx

/--
Existential precedence after grouping fine events into coarse relata.
This is a neutral coarse-order construction, not a causal primitive.
-/
def CoarsePrecedes {n r : Nat} (label : Fin n → Fin r) (a b : Fin r) : Prop :=
  ∃ x y, label x = a ∧ label y = b ∧ FinePrecedes x y

/--
Interleaving labels A-B-A along one fine strict order are sufficient to make the
existential coarse precedence point both A→B and B→A.
-/
theorem coarsePrecedes_two_way_of_interleaving
    {n r : Nat} {label : Fin n → Fin r}
    {x y z : Fin n} {a b : Fin r}
    (hxy : FinePrecedes x y) (hyz : FinePrecedes y z)
    (hx : label x = a) (hy : label y = b) (hz : label z = a) :
    CoarsePrecedes label a b ∧ CoarsePrecedes label b a := by
  constructor
  · exact ⟨x, y, hx, hy, hxy⟩
  · exact ⟨y, z, hy, hz, hyz⟩

/-- Interleaved two-relatum fixture: A-B-A-B over fine slots 0-1-2-3. -/
def interleavedRelata (x : Fin 4) : Fin 2 :=
  if x = (0 : Fin 4) then (0 : Fin 2)
  else if x = (1 : Fin 4) then (1 : Fin 2)
  else if x = (2 : Fin 4) then (0 : Fin 2)
  else (1 : Fin 2)

/-- A precedes B in the interleaved fixture. -/
theorem interleavedRelata_forward :
    CoarsePrecedes interleavedRelata (0 : Fin 2) (1 : Fin 2) := by
  refine ⟨(0 : Fin 4), (1 : Fin 4), ?_, ?_, ?_⟩
  · rfl
  · rfl
  · change (0 : Nat) < 1
    decide

/-- B also precedes A in the same interleaved fixture. -/
theorem interleavedRelata_reverse :
    CoarsePrecedes interleavedRelata (1 : Fin 2) (0 : Fin 2) := by
  refine ⟨(1 : Fin 4), (2 : Fin 4), ?_, ?_, ?_⟩
  · rfl
  · rfl
  · change (1 : Nat) < 2
    decide

/-- The two coarse relata used by the fixture are distinct. -/
theorem interleavedRelata_distinct : (0 : Fin 2) ≠ (1 : Fin 2) := by
  decide

/--
The fine four-slot order remains asymmetric even though the grouped coarse
fixture has a two-way pair.
-/
theorem interleaved_coarse_two_way_over_fine_asymmetry :
    CoarsePrecedes interleavedRelata (0 : Fin 2) (1 : Fin 2) ∧
      CoarsePrecedes interleavedRelata (1 : Fin 2) (0 : Fin 2) ∧
      (0 : Fin 2) ≠ (1 : Fin 2) ∧
      (∀ x y : Fin 4, FinePrecedes x y → ¬ FinePrecedes y x) := by
  exact ⟨interleavedRelata_forward, interleavedRelata_reverse,
    interleavedRelata_distinct, fun _ _ hxy => finePrecedes_not_two_way hxy⟩

/-- Contiguous two-relatum control: A-A-B-B over fine slots 0-1-2-3. -/
def contiguousRelata (x : Fin 4) : Fin 2 :=
  if x.1 < 2 then (0 : Fin 2) else (1 : Fin 2)

/-- A precedes B in the contiguous control. -/
theorem contiguousRelata_forward :
    CoarsePrecedes contiguousRelata (0 : Fin 2) (1 : Fin 2) := by
  refine ⟨(1 : Fin 4), (2 : Fin 4), ?_, ?_, ?_⟩
  · decide
  · decide
  · change (1 : Nat) < 2
    decide

/-- The contiguous control has no reverse B→A coarse edge. -/
theorem contiguousRelata_no_reverse :
    ¬ CoarsePrecedes contiguousRelata (1 : Fin 2) (0 : Fin 2) := by
  intro h
  rcases h with ⟨x, y, hx, hy, hxy⟩
  have hxge : 2 ≤ x.1 := by
    by_cases hlt : x.1 < 2
    · simp [contiguousRelata, hlt] at hx
    · exact Nat.le_of_not_gt hlt
  have hylt : y.1 < 2 := by
    by_cases hlt : y.1 < 2
    · exact hlt
    · simp [contiguousRelata, hlt] at hy
  have hxlt : x.1 < 2 := Nat.lt_trans hxy hylt
  exact (Nat.not_lt_of_ge hxge) hxlt

/-- Owner-local finite negative-control bundle. -/
theorem coarse_relata_precedence_bundle :
    (∀ x : Fin 4, ¬ FinePrecedes x x) ∧
      CoarsePrecedes interleavedRelata (0 : Fin 2) (1 : Fin 2) ∧
      CoarsePrecedes interleavedRelata (1 : Fin 2) (0 : Fin 2) ∧
      CoarsePrecedes contiguousRelata (0 : Fin 2) (1 : Fin 2) ∧
      ¬ CoarsePrecedes contiguousRelata (1 : Fin 2) (0 : Fin 2) := by
  exact ⟨finePrecedes_irrefl,
    interleavedRelata_forward,
    interleavedRelata_reverse,
    contiguousRelata_forward,
    contiguousRelata_no_reverse⟩

end RelayTheory
