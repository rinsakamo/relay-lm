import RelayTheory.RepresentationRefinement

namespace RelayTheory

/--
Restrict a declared representation family along an index map.
The map only selects coordinates; it carries no observer or cognitive ontology.
-/
def reindexRepresentationFamily
    {History SmallIndex LargeIndex : Type}
    {State : LargeIndex → Type}
    (include : SmallIndex → LargeIndex)
    (rep : ∀ j, History → State j) :
    ∀ i, History → State (include i) :=
  fun i => rep (include i)

/--
Equality of the full family profile implies equality of every reindexed
subfamily profile.
-/
theorem familyRepresentation_reindex_eq_of_eq
    {History SmallIndex LargeIndex : Type}
    {State : LargeIndex → Type}
    (include : SmallIndex → LargeIndex)
    (rep : ∀ j, History → State j)
    {h₁ h₂ : History}
    (hEq : familyRepresentation rep h₁ = familyRepresentation rep h₂) :
    familyRepresentation (reindexRepresentationFamily include rep) h₁ =
      familyRepresentation (reindexRepresentationFamily include rep) h₂ := by
  funext i
  exact congrFun hEq (include i)

/--
A declared family refines every family obtained by restricting its coordinates.
Adding declared coordinates can therefore only preserve or refine the required
history partition at this exact representation layer.
-/
theorem familyRepresentation_refines_reindex
    {History SmallIndex LargeIndex : Type}
    {State : LargeIndex → Type}
    (include : SmallIndex → LargeIndex)
    (rep : ∀ j, History → State j) :
    RepresentationRefines
      (familyRepresentation rep)
      (familyRepresentation (reindexRepresentationFamily include rep)) := by
  apply fiber_preservation_implies_factorsThroughReachable
  intro h₁ h₂ hEq
  exact familyRepresentation_reindex_eq_of_eq include rep hEq

/-- Reindex every small-frame coordinate to the first Bool coordinate. -/
def firstCoordinateReindex : Bool → Bool :=
  fun _ => false

/--
In the two-bit fixture, the repeated-first-coordinate restricted family merges
histories that differ only in the second bit.
-/
theorem firstCoordinateReindex_merges_secondBit_witness :
    familyRepresentation
        (reindexRepresentationFamily firstCoordinateReindex bothBitsWorkload)
        (false, false) =
      familyRepresentation
        (reindexRepresentationFamily firstCoordinateReindex bothBitsWorkload)
        (false, true) := by
  funext i
  cases i <;> rfl

/--
The full complementary two-coordinate family separates the same two histories.
-/
theorem bothBitsFamily_separates_secondBit_witness :
    familyRepresentation bothBitsWorkload (false, false) ≠
      familyRepresentation bothBitsWorkload (false, true) := by
  intro hEq
  have hTrue := congrFun hEq true
  simp [familyRepresentation, bothBitsWorkload] at hTrue

/--
The complementary two-bit family strictly refines the frame that reuses only
its first coordinate. This is a finite witness that expanding a declared family
can split a previously merged history class.
-/
theorem bothBitsFamily_strictly_refines_firstCoordinateReindex :
    StrictlyRefines
      (familyRepresentation bothBitsWorkload)
      (familyRepresentation
        (reindexRepresentationFamily firstCoordinateReindex bothBitsWorkload)) := by
  constructor
  · exact familyRepresentation_refines_reindex
      firstCoordinateReindex bothBitsWorkload
  · intro hReverse
    have hImpossible :
        familyRepresentation bothBitsWorkload (false, false) =
          familyRepresentation bothBitsWorkload (false, true) :=
      factorsThroughReachable_preserves_fibers hReverse
        firstCoordinateReindex_merges_secondBit_witness
    exact bothBitsFamily_separates_secondBit_witness hImpossible

/-- A one-coordinate first-bit workload family. -/
def singletonFirstWorkload : Unit → (Bool × Bool) → Bool :=
  fun _ h => h.1

/--
Duplicating an already-declared distinction need not change the representation
gauge class: the Bool-indexed repeated-first family and the singleton first-bit
family mutually refine one another.
-/
theorem repeatedFirst_and_singletonFirst_representationEquivalent :
    RepresentationEquivalent
      (familyRepresentation firstOnlyWorkload)
      (familyRepresentation singletonFirstWorkload) := by
  constructor
  · apply fiber_preservation_implies_factorsThroughReachable
    intro h₁ h₂ hExpanded
    funext u
    have hFirst := congrFun hExpanded false
    simpa [familyRepresentation, firstOnlyWorkload, singletonFirstWorkload] using hFirst
  · apply fiber_preservation_implies_factorsThroughReachable
    intro h₁ h₂ hSingleton
    funext i
    have hFirst := congrFun hSingleton ()
    simpa [familyRepresentation, firstOnlyWorkload, singletonFirstWorkload] using hFirst

end RelayTheory
