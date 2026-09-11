import RelayTheory.RepresentationFactorization

namespace RelayTheory

/--
Package a declared family of representations into one dependent profile.
This is an ordinary representation construction, not a cognitive ontology.
-/
def familyRepresentation
    {History Index : Type}
    {State : Index → Type}
    (rep : ∀ i, History → State i) :
    History → (∀ i, State i) :=
  fun h i => rep i h

/-- Every declared coordinate is exactly recoverable from the family profile. -/
theorem familyRepresentation_factors_coordinate
    {History Index : Type}
    {State : Index → Type}
    (rep : ∀ i, History → State i)
    (i : Index) :
    FactorsThrough (familyRepresentation rep) (rep i) := by
  refine ⟨fun profile => profile i, ?_⟩
  intro h
  rfl

/-- Factoring through the full family profile implies factoring through each coordinate. -/
theorem factorsThrough_family_implies_coordinates
    {History Index Carrier : Type}
    {State : Index → Type}
    (carrier : History → Carrier)
    (rep : ∀ i, History → State i)
    (hFac : FactorsThrough carrier (familyRepresentation rep)) :
    ∀ i, FactorsThrough carrier (rep i) := by
  intro i
  rcases hFac with ⟨migrate, hmigrate⟩
  refine ⟨fun c => migrate c i, ?_⟩
  intro h
  exact congrFun (hmigrate h) i

/--
If one carrier exactly determines every declared coordinate, it exactly
determines the combined family profile. Classical choice only selects the
already-assumed coordinate migrations; no new representation hypothesis is
introduced.
-/
theorem factorsThrough_coordinates_implies_family
    {History Index Carrier : Type}
    {State : Index → Type}
    (carrier : History → Carrier)
    (rep : ∀ i, History → State i)
    (hFac : ∀ i, FactorsThrough carrier (rep i)) :
    FactorsThrough carrier (familyRepresentation rep) := by
  classical
  let migrate : Carrier → (∀ i, State i) :=
    fun c i => Classical.choose (hFac i) c
  refine ⟨migrate, ?_⟩
  intro h
  funext i
  exact Classical.choose_spec (hFac i) h

/--
Universal factorization property of the declared family profile: a carrier
exactly determines the whole profile iff it exactly determines every declared
coordinate.
-/
theorem factorsThrough_family_iff_coordinates
    {History Index Carrier : Type}
    {State : Index → Type}
    (carrier : History → Carrier)
    (rep : ∀ i, History → State i) :
    FactorsThrough carrier (familyRepresentation rep) ↔
      ∀ i, FactorsThrough carrier (rep i) := by
  constructor
  · exact factorsThrough_family_implies_coordinates carrier rep
  · exact factorsThrough_coordinates_implies_family carrier rep

/--
Two histories have the same family profile exactly when every declared
coordinate gives them the same representation.
-/
theorem familyRepresentation_eq_iff_coordinates
    {History Index : Type}
    {State : Index → Type}
    (rep : ∀ i, History → State i)
    (h₁ h₂ : History) :
    familyRepresentation rep h₁ = familyRepresentation rep h₂ ↔
      ∀ i, rep i h₁ = rep i h₂ := by
  constructor
  · intro hEq i
    exact congrFun hEq i
  · intro hCoord
    funext i
    exact hCoord i

/-- A two-workload family in which every coordinate asks only for the first bit. -/
def firstOnlyWorkload : Bool → (Bool × Bool) → Bool :=
  fun _ h => h.1

/-- The first bit alone exactly determines the entire repeated-first-bit family. -/
theorem firstBit_factors_to_firstOnlyFamily :
    FactorsThrough firstBit (familyRepresentation firstOnlyWorkload) := by
  refine ⟨fun b _ => b, ?_⟩
  intro h
  rfl

/-- Every coordinate of the repeated-first-bit family factors through the first bit. -/
theorem firstBit_factors_to_each_firstOnly_workload :
    ∀ i, FactorsThrough firstBit (firstOnlyWorkload i) := by
  intro i
  refine ⟨fun b => b, ?_⟩
  intro h
  rfl

/--
Multiple declared workloads do not by themselves force full-history retention:
the entire repeated-first-bit family is determined by the first bit, while the
second bit remains unavailable from that carrier.
-/
theorem repeated_first_workloads_do_not_force_second_bit :
    FactorsThrough firstBit (familyRepresentation firstOnlyWorkload) ∧
    ¬ FactorsThrough firstBit secondBit := by
  exact ⟨firstBit_factors_to_firstOnlyFamily,
    firstBit_does_not_factor_to_secondBit⟩

/-- A complementary workload family: false asks for the first bit, true for the second. -/
def bothBitsWorkload : Bool → (Bool × Bool) → Bool
  | false, h => h.1
  | true, h => h.2

/-- Retaining the full pair exactly determines the complementary workload family. -/
theorem fullPair_factors_to_bothBitsFamily :
    FactorsThrough (fun h : Bool × Bool => h)
      (familyRepresentation bothBitsWorkload) := by
  refine ⟨fun h i => bothBitsWorkload i h, ?_⟩
  intro h
  rfl

/-- The complementary workload family exactly reconstructs the full pair. -/
theorem bothBitsFamily_factors_to_fullPair :
    FactorsThrough (familyRepresentation bothBitsWorkload)
      (fun h : Bool × Bool => h) := by
  refine ⟨fun profile => (profile false, profile true), ?_⟩
  intro h
  cases h
  rfl

/--
The complementary workload profile and the full two-bit fixture are mutually
factorizable. On this fixture, the declared family preserves every pair
coordinate without implying any universal full-history necessity.
-/
theorem bothBitsFamily_and_fullPair_factor_both_ways :
    FactorsThrough (fun h : Bool × Bool => h)
      (familyRepresentation bothBitsWorkload) ∧
    FactorsThrough (familyRepresentation bothBitsWorkload)
      (fun h : Bool × Bool => h) := by
  exact ⟨fullPair_factors_to_bothBitsFamily,
    bothBitsFamily_factors_to_fullPair⟩

end RelayTheory
