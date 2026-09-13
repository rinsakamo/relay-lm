import RelayTheory.ReachableResidualOrbit

namespace RelayTheory

/--
Minimal rooted sequential dynamics used to test whether a reachable carrier by
itself determines composition.  This is a theory-local falsification harness,
not a claim that all cognitive dynamics are monoids.
-/
structure ResidualSequentialDynamics (α : Type) where
  root : α
  compose : α → α → α
  assoc : ∀ a b c : α,
    compose (compose a b) c = compose a (compose b c)
  root_left : ∀ a : α, compose root a = a
  root_right : ∀ a : α, compose a root = a

namespace ResidualSequentialDynamics

/-- One-step reachability from the distinguished root using a carrier element. -/
def Reachable {α : Type} (D : ResidualSequentialDynamics α) (x : α) : Prop :=
  ∃ a : α, D.compose D.root a = x

/-- The right-regular transition/action retained by a sequential dynamics. -/
def RightAction {α : Type} (D : ResidualSequentialDynamics α)
    (a x : α) : α :=
  D.compose a x

end ResidualSequentialDynamics

/--
For a rooted unital carrier of this form, every carrier element is reachable.
Thus the unlabeled reachability predicate contributes no information about which
associative unital composition law is present.
-/
theorem residualSequentialDynamics_all_reachable {α : Type}
    (D : ResidualSequentialDynamics α) (x : α) :
    D.Reachable x := by
  exact ⟨x, D.root_left x⟩

/-- Boolean XOR written explicitly so the countermodel needs no extra algebra. -/
def boolXorCompose : Bool → Bool → Bool
  | false, b => b
  | true, false => true
  | true, true => false

/-- Boolean OR written explicitly with the same identity element `false`. -/
def boolOrCompose : Bool → Bool → Bool
  | false, b => b
  | true, _ => true

theorem boolXorCompose_assoc (a b c : Bool) :
    boolXorCompose (boolXorCompose a b) c =
      boolXorCompose a (boolXorCompose b c) := by
  cases a <;> cases b <;> cases c <;> rfl

theorem boolXorCompose_false_left (a : Bool) :
    boolXorCompose false a = a := by
  cases a <;> rfl

theorem boolXorCompose_false_right (a : Bool) :
    boolXorCompose a false = a := by
  cases a <;> rfl

theorem boolOrCompose_assoc (a b c : Bool) :
    boolOrCompose (boolOrCompose a b) c =
      boolOrCompose a (boolOrCompose b c) := by
  cases a <;> cases b <;> cases c <;> rfl

theorem boolOrCompose_false_left (a : Bool) :
    boolOrCompose false a = a := by
  cases a <;> rfl

theorem boolOrCompose_false_right (a : Bool) :
    boolOrCompose a false = a := by
  cases a <;> rfl

/-- Associative unital XOR dynamics on the Bool carrier. -/
def boolXorDynamics : ResidualSequentialDynamics Bool where
  root := false
  compose := boolXorCompose
  assoc := boolXorCompose_assoc
  root_left := boolXorCompose_false_left
  root_right := boolXorCompose_false_right

/-- Associative unital OR dynamics on the same Bool carrier and same root. -/
def boolOrDynamics : ResidualSequentialDynamics Bool where
  root := false
  compose := boolOrCompose
  assoc := boolOrCompose_assoc
  root_left := boolOrCompose_false_left
  root_right := boolOrCompose_false_right

/-- Every Bool is reachable in the XOR dynamics. -/
theorem boolXorDynamics_all_reachable (x : Bool) :
    boolXorDynamics.Reachable x :=
  residualSequentialDynamics_all_reachable boolXorDynamics x

/-- Every Bool is reachable in the OR dynamics. -/
theorem boolOrDynamics_all_reachable (x : Bool) :
    boolOrDynamics.Reachable x :=
  residualSequentialDynamics_all_reachable boolOrDynamics x

/-- The two dynamics therefore have exactly the same reachable carrier. -/
theorem bool_xor_or_same_reachable (x : Bool) :
    boolXorDynamics.Reachable x ↔ boolOrDynamics.Reachable x := by
  constructor
  · intro _
    exact boolOrDynamics_all_reachable x
  · intro _
    exact boolXorDynamics_all_reachable x

/--
The composition laws are nevertheless different: XOR sends `(true,true)` to
`false`, whereas OR sends it to `true`.
-/
theorem bool_xor_or_compose_ne :
    boolXorDynamics.compose ≠ boolOrDynamics.compose := by
  intro h
  have hTrueTrue := congrFun (congrFun h true) true
  cases hTrueTrue

/-- The surviving right-action also exposes the same dynamics distinction. -/
theorem bool_xor_or_rightAction_true_true_ne :
    boolXorDynamics.RightAction true true ≠
      boolOrDynamics.RightAction true true := by
  intro h
  cases h

/--
Once the transition/right-action is retained, composition is immediately
reconstructible by evaluation.  The information lost by the carrier-only view
is therefore transition structure, not another carrier coordinate.
-/
theorem residualSequentialDynamics_compose_reconstructed_from_rightAction
    {α : Type} (D : ResidualSequentialDynamics α) :
    D.compose = fun a x => D.RightAction a x := by
  rfl

/--
Level-B negative result for #2806: same carrier type, same distinguished root,
and the same reachable-state predicate do not determine sequential dynamics,
even after associativity and two-sided identity are held fixed.
-/
theorem unlabeled_reachable_rooted_carrier_does_not_determine_sequential_dynamics :
    ∃ D₁ D₂ : ResidualSequentialDynamics Bool,
      D₁.root = D₂.root ∧
      (∀ x : Bool, D₁.Reachable x ↔ D₂.Reachable x) ∧
      D₁.compose ≠ D₂.compose := by
  refine ⟨boolXorDynamics, boolOrDynamics, rfl, ?_, bool_xor_or_compose_ne⟩
  intro x
  exact bool_xor_or_same_reachable x

/--
Acceptance bundle for #2806.  It deliberately proves only a structural
non-identifiability result: the reachable rooted carrier does not fix dynamics.
It does not claim that the Bool fixture is itself a full-future-response model,
or that sequential dynamics is a final ontology.
-/
theorem residual_carrier_nondeterminacy_bundle :
    (∃ D₁ D₂ : ResidualSequentialDynamics Bool,
      D₁.root = D₂.root ∧
      (∀ x : Bool, D₁.Reachable x ↔ D₂.Reachable x) ∧
      D₁.compose ≠ D₂.compose) ∧
    (∀ {α : Type} (D : ResidualSequentialDynamics α),
      D.compose = fun a x => D.RightAction a x) := by
  constructor
  · exact unlabeled_reachable_rooted_carrier_does_not_determine_sequential_dynamics
  · intro α D
    exact residualSequentialDynamics_compose_reconstructed_from_rightAction D

end RelayTheory
