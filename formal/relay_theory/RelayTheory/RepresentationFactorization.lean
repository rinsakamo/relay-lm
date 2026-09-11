import RelayTheory.Exact

namespace RelayTheory

/--
`new` factors exactly through `old` when one deterministic map from the old
representation reproduces the new representation on every history.

This definition is representation-theoretic only. It carries no cognitive,
memory, or ontological interpretation by itself.
-/
def FactorsThrough {History Old New : Type}
    (old : History → Old) (new : History → New) : Prop :=
  ∃ migrate : Old → New, ∀ h, migrate (old h) = new h

/--
Reachable-only factorization avoids imposing any value on old-representation
points that are not produced by a history.
-/
def FactorsThroughReachable {History Old New : Type}
    (old : History → Old) (new : History → New) : Prop :=
  ∃ migrate : ∀ a : Old, (∃ h, old h = a) → New,
    ∀ h, migrate (old h) ⟨h, rfl⟩ = new h

/-- Exact total factorization preserves every fiber of the old representation. -/
theorem factorsThrough_preserves_fibers
    {History Old New : Type}
    {old : History → Old} {new : History → New}
    (hFac : FactorsThrough old new)
    {h₁ h₂ : History}
    (hOld : old h₁ = old h₂) :
    new h₁ = new h₂ := by
  rcases hFac with ⟨migrate, hmigrate⟩
  calc
    new h₁ = migrate (old h₁) := (hmigrate h₁).symm
    _ = migrate (old h₂) := congrArg migrate hOld
    _ = new h₂ := hmigrate h₂

/-- A single old-fiber/new-separation witness blocks exact old-only migration. -/
theorem fiber_violation_blocks_factorization
    {History Old New : Type}
    {old : History → Old} {new : History → New}
    {h₁ h₂ : History}
    (hOld : old h₁ = old h₂)
    (hNew : new h₁ ≠ new h₂) :
    ¬ FactorsThrough old new := by
  intro hFac
  exact hNew (factorsThrough_preserves_fibers hFac hOld)

/-- Total factorization trivially supplies a reachable-only factorization. -/
theorem factorsThrough_implies_reachable
    {History Old New : Type}
    {old : History → Old} {new : History → New}
    (hFac : FactorsThrough old new) :
    FactorsThroughReachable old new := by
  rcases hFac with ⟨migrate, hmigrate⟩
  refine ⟨fun a _ => migrate a, ?_⟩
  intro h
  exact hmigrate h

/-- Reachable-only factorization also preserves every old-representation fiber. -/
theorem factorsThroughReachable_preserves_fibers
    {History Old New : Type}
    {old : History → Old} {new : History → New}
    (hFac : FactorsThroughReachable old new)
    {h₁ h₂ : History}
    (hOld : old h₁ = old h₂) :
    new h₁ = new h₂ := by
  rcases hFac with ⟨migrate, hmigrate⟩
  cases hOld
  have hProof :
      (⟨h₁, rfl⟩ : ∃ h, old h = old h₁) =
      (⟨h₂, rfl⟩ : ∃ h, old h = old h₁) :=
    Subsingleton.elim _ _
  calc
    new h₁ = migrate (old h₁) ⟨h₁, rfl⟩ := (hmigrate h₁).symm
    _ = migrate (old h₁) ⟨h₂, rfl⟩ := congrArg (migrate (old h₁)) hProof
    _ = new h₂ := hmigrate h₂

/--
Fiber preservation is sufficient for exact factorization on reachable old
representation points. No default inhabitant of the new representation is
needed because unreachable old points are not totalized.
-/
theorem fiber_preservation_implies_factorsThroughReachable
    {History Old New : Type}
    {old : History → Old} {new : History → New}
    (hPreserves : ∀ h₁ h₂, old h₁ = old h₂ → new h₁ = new h₂) :
    FactorsThroughReachable old new := by
  classical
  let migrate : ∀ a : Old, (∃ h, old h = a) → New :=
    fun _ hReachable => new (Classical.choose hReachable)
  refine ⟨migrate, ?_⟩
  intro h
  dsimp [migrate]
  apply hPreserves
  exact Classical.choose_spec
    (show ∃ x, old x = old h from ⟨h, rfl⟩)

/--
Exact reachable migration criterion: the new representation factors through the
old representation exactly when the old representation never merges histories
that the new representation separates.
-/
theorem factorsThroughReachable_iff_fiber_preservation
    {History Old New : Type}
    (old : History → Old) (new : History → New) :
    FactorsThroughReachable old new ↔
      ∀ h₁ h₂, old h₁ = old h₂ → new h₁ = new h₂ := by
  constructor
  · intro hFac h₁ h₂ hOld
    exact factorsThroughReachable_preserves_fibers hFac hOld
  · exact fiber_preservation_implies_factorsThroughReachable

/-- Pair two representations without claiming that the pair is minimal. -/
def pairRepresentation {History Left Right : Type}
    (left : History → Left) (right : History → Right) :
    History → Left × Right :=
  fun h => (left h, right h)

/-- The paired representation factors exactly to its left component. -/
theorem pairRepresentation_factors_left
    {History Left Right : Type}
    (left : History → Left) (right : History → Right) :
    FactorsThrough (pairRepresentation left right) left := by
  refine ⟨fun p => p.1, ?_⟩
  intro h
  rfl

/-- The paired representation factors exactly to its right component. -/
theorem pairRepresentation_factors_right
    {History Left Right : Type}
    (left : History → Left) (right : History → Right) :
    FactorsThrough (pairRepresentation left right) right := by
  refine ⟨fun p => p.2, ?_⟩
  intro h
  rfl

/-- First-bit representation for the minimal obstruction fixture. -/
def firstBit : Bool × Bool → Bool :=
  fun h => h.1

/-- Second-bit representation for the minimal obstruction fixture. -/
def secondBit : Bool × Bool → Bool :=
  fun h => h.2

/--
The first bit alone cannot exactly determine the second bit. This is the minimal
information-loss counterexample: two histories share one old representation but
must be separated by the new representation.
-/
theorem firstBit_does_not_factor_to_secondBit :
    ¬ FactorsThrough firstBit secondBit := by
  apply fiber_violation_blocks_factorization
    (h₁ := (false, false)) (h₂ := (false, true))
  · rfl
  · intro hEq
    cases hEq

/-- Retaining the full pair is an exact positive control for first-bit projection. -/
theorem fullPair_factors_to_firstBit :
    FactorsThrough (fun h : Bool × Bool => h) firstBit := by
  refine ⟨fun h => h.1, ?_⟩
  intro h
  rfl

/-- Adding the missing second bit as side information restores exact migration. -/
theorem firstBit_with_secondBit_factors_to_secondBit :
    FactorsThrough (pairRepresentation firstBit secondBit) secondBit :=
  pairRepresentation_factors_right firstBit secondBit

/-- Identity coordinate on Bool for the representation-gauge control. -/
def boolIdentity : Bool → Bool :=
  fun b => b

/-- An invertible relabeling of Bool for the representation-gauge control. -/
def boolComplement : Bool → Bool
  | false => true
  | true => false

/--
An invertible coordinate relabeling factors both ways. This separates mere
representation change from genuine information loss.
-/
theorem bool_relabeling_factors_both_ways :
    FactorsThrough boolIdentity boolComplement ∧
    FactorsThrough boolComplement boolIdentity := by
  constructor
  · refine ⟨boolComplement, ?_⟩
    intro b
    rfl
  · refine ⟨boolComplement, ?_⟩
    intro b
    cases b <;> rfl

end RelayTheory
