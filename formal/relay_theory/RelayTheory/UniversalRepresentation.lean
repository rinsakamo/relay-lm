import RelayTheory.RepresentationRefinement

namespace RelayTheory

/--
A representation refines every deterministic representation of the same
declared history, within the Lean universe quantified here.

This is a maximal exact-workload property only. It carries no claim of physical
availability, efficiency, cognition, memory, or ontology.
-/
def RefinesEveryRepresentation
    {History Carrier : Type}
    (rep : History → Carrier) : Prop :=
  ∀ (Output : Type) (query : History → Output),
    RepresentationRefines rep query

/-- Full declared history refines every deterministic representation of it. -/
theorem identityRepresentation_refinesEveryRepresentation
    {History : Type} :
    RefinesEveryRepresentation
      (identityRepresentation : History → History) := by
  intro Output query
  exact identityRepresentation_refines query

/--
Universal deterministic refinement is equivalent to mutual refinement with the
identity/full-history representation.
-/
theorem refinesEveryRepresentation_iff_equivalent_identity
    {History Carrier : Type}
    (rep : History → Carrier) :
    RefinesEveryRepresentation rep ↔
      RepresentationEquivalent rep
        (identityRepresentation : History → History) := by
  constructor
  · intro hAll
    constructor
    · exact hAll History (identityRepresentation : History → History)
    · exact identityRepresentation_refines rep
  · intro hEquivalent Output query
    exact representationRefines_trans hEquivalent.1
      (identityRepresentation_refines query)

/--
A representation refines every deterministic workload exactly when it merges no
pair of distinct declared histories.
-/
theorem refinesEveryRepresentation_iff_injective
    {History Carrier : Type}
    (rep : History → Carrier) :
    RefinesEveryRepresentation rep ↔ Function.Injective rep := by
  constructor
  · intro hAll h₁ h₂ hRep
    have hIdentity :
        RepresentationRefines rep
          (identityRepresentation : History → History) :=
      hAll History (identityRepresentation : History → History)
    exact factorsThroughReachable_preserves_fibers hIdentity hRep
  · intro hInjective Output query
    apply fiber_preservation_implies_factorsThroughReachable
    intro h₁ h₂ hRep
    exact congrArg query (hInjective hRep)

/--
One genuine history merge is enough to defeat unrestricted exact deterministic
reinterpretation.
-/
theorem merged_distinct_histories_not_refinesEveryRepresentation
    {History Carrier : Type}
    {rep : History → Carrier}
    {h₁ h₂ : History}
    (hDistinct : h₁ ≠ h₂)
    (hMerged : rep h₁ = rep h₂) :
    ¬ RefinesEveryRepresentation rep := by
  intro hAll
  have hInjective : Function.Injective rep :=
    (refinesEveryRepresentation_iff_injective rep).1 hAll
  exact hDistinct (hInjective hMerged)

/--
The first-bit projection of a two-bit history is not universal: it merges two
histories separated by the full-history identity representation.
-/
theorem firstBit_not_refinesEveryRepresentation :
    ¬ RefinesEveryRepresentation firstBit := by
  apply merged_distinct_histories_not_refinesEveryRepresentation
    (rep := firstBit)
    (h₁ := (false, false))
    (h₂ := (false, true))
  · intro hEq
    have hSecond : false = true := congrArg Prod.snd hEq
    cases hSecond
  · rfl

end RelayTheory
