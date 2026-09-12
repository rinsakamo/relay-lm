import RelayTheory.RepresentationRefinement

namespace RelayTheory

/--
Exact accessibility relative to a declared decoder family and natural-number
budget.  This is a resource-bounded factorization predicate only: it does not
assert empirical success, a cognitive primitive, or an information quantity.
-/
def AccessibleAt
    {History Carrier Output Decoder : Type}
    (cost : Decoder → Nat)
    (run : Decoder → Carrier → Output)
    (budget : Nat)
    (query : History → Output)
    (rep : History → Carrier) : Prop :=
  ∃ decoder, cost decoder ≤ budget ∧
    ∀ h, run decoder (rep h) = query h

/-- Increasing a declared budget cannot remove an already admitted exact decoder. -/
theorem accessibleAt_mono
    {History Carrier Output Decoder : Type}
    {cost : Decoder → Nat}
    {run : Decoder → Carrier → Output}
    {budget budget' : Nat}
    {query : History → Output}
    {rep : History → Carrier}
    (hAccess : AccessibleAt cost run budget query rep)
    (hBudget : budget ≤ budget') :
    AccessibleAt cost run budget' query rep := by
  rcases hAccess with ⟨decoder, hCost, hCorrect⟩
  exact ⟨decoder, Nat.le_trans hCost hBudget, hCorrect⟩

/-- A finite XOR used only for the deterministic accessibility countermodel. -/
def decoderXor : Bool → Bool → Bool
  | false, false => false
  | false, true => true
  | true, false => true
  | true, true => false

/-- The declared task asks only for the first history bit. -/
def decoderFirstBitQuery (h : Bool × Bool) : Bool :=
  h.1

/-- An immediately readable full-history coordinate. -/
def decoderEasyRepresentation (h : Bool × Bool) : Bool × Bool :=
  h

/--
A lossless relabeling of the same two-bit history.  Recovering the first source
bit from this coordinate requires XOR in the decoder language used below.
-/
def decoderMixedRepresentation (h : Bool × Bool) : Bool × Bool :=
  (decoderXor h.1 h.2, h.2)

/-- The mixed two-bit coordinate is an involution. -/
theorem decoderMixedRepresentation_involutive
    (h : Bool × Bool) :
    decoderMixedRepresentation (decoderMixedRepresentation h) = h := by
  rcases h with ⟨a, b⟩
  cases a <;> cases b <;> rfl

/-- Hence the mixed coordinate loses no declared history distinction. -/
theorem decoderMixedRepresentation_injective :
    Function.Injective decoderMixedRepresentation := by
  intro h₁ h₂ hEq
  calc
    h₁ = decoderMixedRepresentation (decoderMixedRepresentation h₁) :=
      (decoderMixedRepresentation_involutive h₁).symm
    _ = decoderMixedRepresentation (decoderMixedRepresentation h₂) :=
      congrArg decoderMixedRepresentation hEq
    _ = h₂ := decoderMixedRepresentation_involutive h₂

/--
The easy and mixed coordinates induce exactly the same history partition even
though a bounded decoder may treat them differently.
-/
theorem decoder_easy_mixed_representationEquivalent :
    RepresentationEquivalent
      decoderEasyRepresentation decoderMixedRepresentation := by
  apply (representationEquivalent_iff_same_fibers
    decoderEasyRepresentation decoderMixedRepresentation).2
  intro h₁ h₂
  constructor
  · intro hEasy
    have hHistory : h₁ = h₂ := by
      simpa [decoderEasyRepresentation] using hEasy
    exact congrArg decoderMixedRepresentation hHistory
  · intro hMixed
    have hHistory : h₁ = h₂ :=
      decoderMixedRepresentation_injective hMixed
    simpa [decoderEasyRepresentation] using hHistory

/-- The easy coordinate is semantically sufficient for the declared first-bit query. -/
theorem decoderEasyRepresentation_refines_firstBitQuery :
    RepresentationRefines
      decoderEasyRepresentation decoderFirstBitQuery := by
  apply (representationRefines_iff_fiber_inclusion
    decoderEasyRepresentation decoderFirstBitQuery).2
  intro h₁ h₂ hEasy
  have hHistory : h₁ = h₂ := by
    simpa [decoderEasyRepresentation] using hEasy
  simpa [hHistory]

/-- The losslessly mixed coordinate is also semantically sufficient. -/
theorem decoderMixedRepresentation_refines_firstBitQuery :
    RepresentationRefines
      decoderMixedRepresentation decoderFirstBitQuery := by
  exact representationRefines_trans
    decoder_easy_mixed_representationEquivalent.2
    decoderEasyRepresentation_refines_firstBitQuery

/-- A weak consumer family that can only project one pair coordinate. -/
inductive ProjectionDecoder where
  | first
  | second
deriving DecidableEq, Repr

/-- Projection-only decoders are declared zero-cost in the finite fixture. -/
def projectionDecoderCost (_ : ProjectionDecoder) : Nat := 0

/-- Semantics of the projection-only decoder family. -/
def projectionDecoderRun : ProjectionDecoder → Bool × Bool → Bool
  | .first, h => h.1
  | .second, h => h.2

/-- The easy coordinate is accessible to the projection-only consumer. -/
theorem decoderEasy_accessible_projection :
    AccessibleAt projectionDecoderCost projectionDecoderRun 0
      decoderFirstBitQuery decoderEasyRepresentation := by
  refine ⟨ProjectionDecoder.first, ?_, ?_⟩
  · simp [projectionDecoderCost]
  · intro h
    rcases h with ⟨a, b⟩
    rfl

/-- The same query is not accessible from the mixed coordinate by projections alone. -/
theorem decoderMixed_not_accessible_projection :
    ¬ AccessibleAt projectionDecoderCost projectionDecoderRun 0
      decoderFirstBitQuery decoderMixedRepresentation := by
  intro hAccess
  rcases hAccess with ⟨decoder, _hCost, hCorrect⟩
  cases decoder with
  | first =>
      have hBad := hCorrect (false, true)
      simp [projectionDecoderRun, decoderMixedRepresentation,
        decoderXor, decoderFirstBitQuery] at hBad
  | second =>
      have hBad := hCorrect (true, false)
      simp [projectionDecoderRun, decoderMixedRepresentation,
        decoderXor, decoderFirstBitQuery] at hBad

/-- A richer decoder family that additionally admits XOR. -/
inductive PairDecoder where
  | first
  | second
  | xor
deriving DecidableEq, Repr

/-- XOR costs one unit while direct projections cost zero in the fixture. -/
def pairDecoderCost : PairDecoder → Nat
  | .first => 0
  | .second => 0
  | .xor => 1

/-- Semantics of the richer pair decoder family. -/
def pairDecoderRun : PairDecoder → Bool × Bool → Bool
  | .first, h => h.1
  | .second, h => h.2
  | .xor, h => decoderXor h.1 h.2

/-- The richer family can still read the easy coordinate at zero budget. -/
theorem decoderEasy_accessible_at_zero :
    AccessibleAt pairDecoderCost pairDecoderRun 0
      decoderFirstBitQuery decoderEasyRepresentation := by
  refine ⟨PairDecoder.first, ?_, ?_⟩
  · simp [pairDecoderCost]
  · intro h
    rcases h with ⟨a, b⟩
    rfl

/-- Zero budget excludes XOR, so the mixed coordinate remains inaccessible. -/
theorem decoderMixed_not_accessible_at_zero :
    ¬ AccessibleAt pairDecoderCost pairDecoderRun 0
      decoderFirstBitQuery decoderMixedRepresentation := by
  intro hAccess
  rcases hAccess with ⟨decoder, hCost, hCorrect⟩
  cases decoder with
  | first =>
      have hBad := hCorrect (false, true)
      simp [pairDecoderRun, decoderMixedRepresentation,
        decoderXor, decoderFirstBitQuery] at hBad
  | second =>
      have hBad := hCorrect (true, false)
      simp [pairDecoderRun, decoderMixedRepresentation,
        decoderXor, decoderFirstBitQuery] at hBad
  | xor =>
      simp [pairDecoderCost] at hCost

/-- One unit of budget admits the XOR decoder and closes the finite access gap. -/
theorem decoderMixed_accessible_at_one :
    AccessibleAt pairDecoderCost pairDecoderRun 1
      decoderFirstBitQuery decoderMixedRepresentation := by
  refine ⟨PairDecoder.xor, ?_, ?_⟩
  · simp [pairDecoderCost]
  · intro h
    rcases h with ⟨a, b⟩
    cases a <;> cases b <;> rfl

/-- The easy coordinate remains accessible after the same budget increase. -/
theorem decoderEasy_accessible_at_one :
    AccessibleAt pairDecoderCost pairDecoderRun 1
      decoderFirstBitQuery decoderEasyRepresentation := by
  exact accessibleAt_mono decoderEasy_accessible_at_zero (by decide)

/--
Finite separation: information-gauge equivalence and unrestricted semantic
sufficiency coexist with different bounded-decoder accessibility.
-/
theorem semanticSufficiency_not_boundedAccessibility_fixture :
    RepresentationEquivalent
        decoderEasyRepresentation decoderMixedRepresentation ∧
    RepresentationRefines
        decoderEasyRepresentation decoderFirstBitQuery ∧
    RepresentationRefines
        decoderMixedRepresentation decoderFirstBitQuery ∧
    AccessibleAt pairDecoderCost pairDecoderRun 0
        decoderFirstBitQuery decoderEasyRepresentation ∧
    ¬ AccessibleAt pairDecoderCost pairDecoderRun 0
        decoderFirstBitQuery decoderMixedRepresentation := by
  exact ⟨decoder_easy_mixed_representationEquivalent,
    decoderEasyRepresentation_refines_firstBitQuery,
    decoderMixedRepresentation_refines_firstBitQuery,
    decoderEasy_accessible_at_zero,
    decoderMixed_not_accessible_at_zero⟩

/--
Consumer/regime swap witness: a projection-only regime distinguishes the access
status of the two information-equivalent coordinates, while the richer
one-unit regime admits both.
-/
theorem consumerRegime_swap_fixture :
    (AccessibleAt projectionDecoderCost projectionDecoderRun 0
        decoderFirstBitQuery decoderEasyRepresentation ∧
      ¬ AccessibleAt projectionDecoderCost projectionDecoderRun 0
        decoderFirstBitQuery decoderMixedRepresentation) ∧
    (AccessibleAt pairDecoderCost pairDecoderRun 1
        decoderFirstBitQuery decoderEasyRepresentation ∧
      AccessibleAt pairDecoderCost pairDecoderRun 1
        decoderFirstBitQuery decoderMixedRepresentation) := by
  exact ⟨⟨decoderEasy_accessible_projection,
      decoderMixed_not_accessible_projection⟩,
    ⟨decoderEasy_accessible_at_one, decoderMixed_accessible_at_one⟩⟩

/--
A representation-coordinate relabeling can be moved into the access interface
without changing the downstream composite, provided the declared inverse law
holds on the original carrier.
-/
theorem accessInterface_relabeling_gauge
    {History Carrier Carrier' View Output : Type}
    (rep : History → Carrier)
    (relabel : Carrier → Carrier')
    (unlabel : Carrier' → Carrier)
    (hInverse : ∀ c, unlabel (relabel c) = c)
    (access : Carrier → View)
    (decode : View → Output) :
    (fun h => decode (access (unlabel (relabel (rep h))))) =
      (fun h => decode (access (rep h))) := by
  funext h
  rw [hInverse]

end RelayTheory
