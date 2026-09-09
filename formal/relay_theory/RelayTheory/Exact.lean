import Std

namespace RelayTheory

/--
A bounded exact binary probability law for the first Relay Theory formalization
milestone. Mass is measured in exact quarter units, so `left + right = 4`
corresponds to total probability one. This is intentionally not a universal
finite-measure library.
-/
structure BinaryLaw where
  left : Nat
  right : Nat
deriving DecidableEq, Repr

namespace BinaryLaw

/-- Exact normalization for the bounded denominator-four model. -/
def Valid (p : BinaryLaw) : Prop :=
  p.left + p.right = 4

/-- Which of the two outcomes have non-zero exact mass. -/
def support (p : BinaryLaw) : Bool × Bool :=
  (decide (p.left ≠ 0), decide (p.right ≠ 0))

end BinaryLaw

/-- P(L)=1/2, P(R)=1/2. -/
def halfLaw : BinaryLaw := ⟨2, 2⟩

/-- Q(L)=3/4, Q(R)=1/4. -/
def skewLaw : BinaryLaw := ⟨3, 1⟩

/-- Point mass on the left outcome. -/
def deltaLeft : BinaryLaw := ⟨4, 0⟩

/-- Point mass on the right outcome. -/
def deltaRight : BinaryLaw := ⟨0, 4⟩

theorem halfLaw_valid : halfLaw.Valid := rfl

theorem skewLaw_valid : skewLaw.Valid := rfl

theorem deltaLeft_valid : deltaLeft.Valid := rfl

theorem deltaRight_valid : deltaRight.Valid := rfl

/-- Equal finite support does not imply equal exact stochastic law. -/
theorem sameSupport_not_sameExactLaw :
    halfLaw.support = skewLaw.support ∧ halfLaw ≠ skewLaw := by
  simp [BinaryLaw.support, halfLaw, skewLaw]

/-- Exact equality, not tolerance, is the bounded identity boundary. -/
def ExactEquivalent (p q : BinaryLaw) : Prop := p = q

theorem exactEquivalent_refl (p : BinaryLaw) : ExactEquivalent p p := rfl

end RelayTheory
