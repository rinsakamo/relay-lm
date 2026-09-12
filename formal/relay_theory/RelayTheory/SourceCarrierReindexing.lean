import RelayTheory.RepresentationRefinement

namespace RelayTheory

/--
Precompose one representation by a common source-carrier reindexing.
This definition is representation-theoretic only; `Source` carries no required
history, temporal, or cognitive structure.
-/
def reindexRepresentation
    {Source Source' Carrier : Type}
    (reindex : Source' → Source)
    (rep : Source → Carrier) :
    Source' → Carrier :=
  fun source' => rep (reindex source')

/--
Any common source reindexing preserves an already-valid exact refinement.
Restricting, duplicating, or relabeling source points cannot create a violation
of a fiber implication that already held on the original source.
-/
theorem representationRefines_reindex
    {Source Source' Fine Coarse : Type}
    (reindex : Source' → Source)
    (fine : Source → Fine)
    (coarse : Source → Coarse)
    (hRefines : RepresentationRefines fine coarse) :
    RepresentationRefines
      (reindexRepresentation reindex fine)
      (reindexRepresentation reindex coarse) := by
  apply (representationRefines_iff_fiber_inclusion _ _).2
  intro source₁ source₂ hFine
  change fine (reindex source₁) = fine (reindex source₂) at hFine
  change coarse (reindex source₁) = coarse (reindex source₂)
  exact
    (representationRefines_iff_fiber_inclusion fine coarse).1
      hRefines (reindex source₁) (reindex source₂) hFine

/--
A surjective common source reindexing also reflects exact refinement: every
original source point has a representative in the reindexed source, so no
original fiber violation can be hidden.
-/
theorem representationRefines_of_reindex_surjective
    {Source Source' Fine Coarse : Type}
    (reindex : Source' → Source)
    (fine : Source → Fine)
    (coarse : Source → Coarse)
    (hSurjective : Function.Surjective reindex)
    (hRefines : RepresentationRefines
      (reindexRepresentation reindex fine)
      (reindexRepresentation reindex coarse)) :
    RepresentationRefines fine coarse := by
  apply (representationRefines_iff_fiber_inclusion _ _).2
  intro source₁ source₂ hFine
  rcases hSurjective source₁ with ⟨source₁', hSource₁⟩
  rcases hSurjective source₂ with ⟨source₂', hSource₂⟩
  have hFine' :
      reindexRepresentation reindex fine source₁' =
        reindexRepresentation reindex fine source₂' := by
    change fine (reindex source₁') = fine (reindex source₂')
    rw [hSource₁, hSource₂]
    exact hFine
  have hCoarse' :=
    (representationRefines_iff_fiber_inclusion _ _).1
      hRefines source₁' source₂' hFine'
  change coarse (reindex source₁') = coarse (reindex source₂') at hCoarse'
  rw [hSource₁, hSource₂] at hCoarse'
  exact hCoarse'

/--
Under a surjective common source reindexing, the exact refinement verdict is
unchanged in both directions.
-/
theorem representationRefines_reindex_iff_of_surjective
    {Source Source' Fine Coarse : Type}
    (reindex : Source' → Source)
    (fine : Source → Fine)
    (coarse : Source → Coarse)
    (hSurjective : Function.Surjective reindex) :
    RepresentationRefines
        (reindexRepresentation reindex fine)
        (reindexRepresentation reindex coarse) ↔
      RepresentationRefines fine coarse := by
  constructor
  · intro h
    exact representationRefines_of_reindex_surjective
      reindex fine coarse hSurjective h
  · intro h
    exact representationRefines_reindex reindex fine coarse h

/--
Mutual-refinement gauge equivalence is likewise invariant under a surjective
common source reindexing.
-/
theorem representationEquivalent_reindex_iff_of_surjective
    {Source Source' A B : Type}
    (reindex : Source' → Source)
    (a : Source → A)
    (b : Source → B)
    (hSurjective : Function.Surjective reindex) :
    RepresentationEquivalent
        (reindexRepresentation reindex a)
        (reindexRepresentation reindex b) ↔
      RepresentationEquivalent a b := by
  constructor
  · intro h
    exact ⟨
      representationRefines_of_reindex_surjective
        reindex a b hSurjective h.1,
      representationRefines_of_reindex_surjective
        reindex b a hSurjective h.2
    ⟩
  · intro h
    exact ⟨
      representationRefines_reindex reindex a b h.1,
      representationRefines_reindex reindex b a h.2
    ⟩

/-- Concrete source-duplication map: every two-bit source receives an irrelevant Bool label. -/
def duplicateTwoBitSource : (Bool × Bool) × Bool → Bool × Bool :=
  fun source => source.1

/-- The duplicate-label source map covers every original two-bit source point. -/
theorem duplicateTwoBitSource_surjective :
    Function.Surjective duplicateTwoBitSource := by
  intro source
  exact ⟨(source, false), rfl⟩

/--
Duplicating every source point by an irrelevant Bool label leaves the exact
full-pair-versus-first-bit refinement verdict unchanged.
-/
theorem duplicateSource_preserves_fullPair_firstBit_refinement :
    RepresentationRefines
        (reindexRepresentation duplicateTwoBitSource (fun h : Bool × Bool => h))
        (reindexRepresentation duplicateTwoBitSource firstBit) ↔
      RepresentationRefines (fun h : Bool × Bool => h) firstBit := by
  exact representationRefines_reindex_iff_of_surjective
    duplicateTwoBitSource (fun h : Bool × Bool => h) firstBit
    duplicateTwoBitSource_surjective

end RelayTheory
