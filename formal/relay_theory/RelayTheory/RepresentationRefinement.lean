import RelayTheory.RepresentationFamily

namespace RelayTheory

/--
`fine` refines `coarse` when the coarse representation is exactly recoverable
from reachable values of the fine representation.

This relation is representation-theoretic only. It does not assert an
information quantity, cognitive state ontology, or physical ordering.
-/
def RepresentationRefines
    {History Fine Coarse : Type}
    (fine : History → Fine) (coarse : History → Coarse) : Prop :=
  FactorsThroughReachable fine coarse

/-- Every representation refines itself. -/
theorem representationRefines_refl
    {History A : Type}
    (rep : History → A) :
    RepresentationRefines rep rep := by
  apply fiber_preservation_implies_factorsThroughReachable
  intro h₁ h₂ hEq
  exact hEq

/-- Reachable representation refinement is transitive. -/
theorem representationRefines_trans
    {History A B C : Type}
    {a : History → A} {b : History → B} {c : History → C}
    (hab : RepresentationRefines a b)
    (hbc : RepresentationRefines b c) :
    RepresentationRefines a c := by
  apply fiber_preservation_implies_factorsThroughReachable
  intro h₁ h₂ hA
  have hB : b h₁ = b h₂ :=
    factorsThroughReachable_preserves_fibers hab hA
  exact factorsThroughReachable_preserves_fibers hbc hB

/--
Refinement is exactly inclusion of history fibers: if the fine representation
merges two histories, the coarse representation must merge them as well.
-/
theorem representationRefines_iff_fiber_inclusion
    {History Fine Coarse : Type}
    (fine : History → Fine) (coarse : History → Coarse) :
    RepresentationRefines fine coarse ↔
      ∀ h₁ h₂, fine h₁ = fine h₂ → coarse h₁ = coarse h₂ := by
  simpa [RepresentationRefines] using
    (factorsThroughReachable_iff_fiber_preservation fine coarse)

/-- Mutual reachable refinement, used as a representation-gauge equivalence. -/
def RepresentationEquivalent
    {History A B : Type}
    (a : History → A) (b : History → B) : Prop :=
  RepresentationRefines a b ∧ RepresentationRefines b a

/-- Mutual refinement is reflexive. -/
theorem representationEquivalent_refl
    {History A : Type}
    (rep : History → A) :
    RepresentationEquivalent rep rep := by
  exact ⟨representationRefines_refl rep, representationRefines_refl rep⟩

/-- Mutual refinement is symmetric. -/
theorem representationEquivalent_symm
    {History A B : Type}
    {a : History → A} {b : History → B}
    (hab : RepresentationEquivalent a b) :
    RepresentationEquivalent b a := by
  exact ⟨hab.2, hab.1⟩

/-- Mutual refinement is transitive. -/
theorem representationEquivalent_trans
    {History A B C : Type}
    {a : History → A} {b : History → B} {c : History → C}
    (hab : RepresentationEquivalent a b)
    (hbc : RepresentationEquivalent b c) :
    RepresentationEquivalent a c := by
  exact ⟨representationRefines_trans hab.1 hbc.1,
    representationRefines_trans hbc.2 hab.2⟩

/--
Two representations are mutually refinable exactly when they induce the same
history fibers. Literal codomain labels or coordinates need not agree.
-/
theorem representationEquivalent_iff_same_fibers
    {History A B : Type}
    (a : History → A) (b : History → B) :
    RepresentationEquivalent a b ↔
      ∀ h₁ h₂, a h₁ = a h₂ ↔ b h₁ = b h₂ := by
  constructor
  · intro hab h₁ h₂
    constructor
    · intro hA
      exact factorsThroughReachable_preserves_fibers hab.1 hA
    · intro hB
      exact factorsThroughReachable_preserves_fibers hab.2 hB
  · intro hFibers
    constructor
    · apply fiber_preservation_implies_factorsThroughReachable
      intro h₁ h₂ hA
      exact (hFibers h₁ h₂).1 hA
    · apply fiber_preservation_implies_factorsThroughReachable
      intro h₁ h₂ hB
      exact (hFibers h₁ h₂).2 hB

/-- Full declared history as the identity representation. -/
def identityRepresentation {History : Type} : History → History :=
  fun h => h

/-- Full declared history refines every deterministic representation of it. -/
theorem identityRepresentation_refines
    {History A : Type}
    (rep : History → A) :
    RepresentationRefines (identityRepresentation : History → History) rep := by
  apply fiber_preservation_implies_factorsThroughReachable
  intro h₁ h₂ hEq
  exact congrArg rep hEq

/-- Strict refinement means refinement without refinement in the reverse direction. -/
def StrictlyRefines
    {History A B : Type}
    (a : History → A) (b : History → B) : Prop :=
  RepresentationRefines a b ∧ ¬ RepresentationRefines b a

/-- The full two-bit fixture strictly refines its first-bit projection. -/
theorem fullPair_strictly_refines_firstBit :
    StrictlyRefines (fun h : Bool × Bool => h) firstBit := by
  constructor
  · exact factorsThrough_implies_reachable fullPair_factors_to_firstBit
  · intro hRefines
    have hImpossible :
        (false, false) = (false, true) :=
      factorsThroughReachable_preserves_fibers hRefines (by rfl)
    cases hImpossible

/-- Bool identity and complement are gauge-equivalent under mutual refinement. -/
theorem bool_relabeling_representationEquivalent :
    RepresentationEquivalent boolIdentity boolComplement := by
  exact ⟨factorsThrough_implies_reachable bool_relabeling_factors_both_ways.1,
    factorsThrough_implies_reachable bool_relabeling_factors_both_ways.2⟩

/-- The gauge-equivalent Bool coordinates are nevertheless literally different at `false`. -/
theorem bool_relabeling_differs_literally :
    boolIdentity false ≠ boolComplement false := by
  simp [boolIdentity, boolComplement]

/-- The family profile refines every declared coordinate. -/
theorem familyRepresentation_refines_coordinate
    {History Index : Type}
    {State : Index → Type}
    (rep : ∀ i, History → State i)
    (i : Index) :
    RepresentationRefines (familyRepresentation rep) (rep i) := by
  exact factorsThrough_implies_reachable
    (familyRepresentation_factors_coordinate rep i)

/--
Any representation that refines every declared coordinate also refines the
whole family profile. The proof uses only fiber preservation, so no unreachable
codomain defaults or additional choice principle is introduced here.
-/
theorem commonRefinement_refines_familyRepresentation
    {History Index Carrier : Type}
    {State : Index → Type}
    (carrier : History → Carrier)
    (rep : ∀ i, History → State i)
    (hCommon : ∀ i, RepresentationRefines carrier (rep i)) :
    RepresentationRefines carrier (familyRepresentation rep) := by
  apply fiber_preservation_implies_factorsThroughReachable
  intro h₁ h₂ hCarrier
  funext i
  exact factorsThroughReachable_preserves_fibers (hCommon i) hCarrier

/--
Universal common-refinement property at the reachable-factorization level.
A carrier refines the family profile exactly when it refines every coordinate.
-/
theorem representationRefines_family_iff_coordinates
    {History Index Carrier : Type}
    {State : Index → Type}
    (carrier : History → Carrier)
    (rep : ∀ i, History → State i) :
    RepresentationRefines carrier (familyRepresentation rep) ↔
      ∀ i, RepresentationRefines carrier (rep i) := by
  constructor
  · intro hFamily i
    exact representationRefines_trans hFamily
      (familyRepresentation_refines_coordinate rep i)
  · exact commonRefinement_refines_familyRepresentation carrier rep

/--
Order-theoretic common-refinement package: the family profile refines each
coordinate, and every common refinement refines the family profile. Literal
representations are therefore unique only up to mutual-refinement gauge.
-/
theorem familyRepresentation_common_refinement_universal
    {History Index : Type}
    {State : Index → Type}
    (rep : ∀ i, History → State i) :
    (∀ i, RepresentationRefines (familyRepresentation rep) (rep i)) ∧
    (∀ (Carrier : Type) (carrier : History → Carrier),
      (∀ i, RepresentationRefines carrier (rep i)) →
      RepresentationRefines carrier (familyRepresentation rep)) := by
  constructor
  · exact familyRepresentation_refines_coordinate rep
  · intro Carrier carrier hCommon
    exact commonRefinement_refines_familyRepresentation carrier rep hCommon

end RelayTheory
