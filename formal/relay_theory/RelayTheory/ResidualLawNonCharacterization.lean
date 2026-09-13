import RelayTheory.ResidualCarrierNonDeterminacy
import RelayTheory.WitnessFreeResidualAssociativity

namespace RelayTheory

/--
A theory-local falsification harness for asking whether complete static state
identity plus the standard sequential law schema determines one unique dynamics.
`observe` is injective, so no static carrier distinction is hidden from the
observer.  This is not an ontology claim and not a Mathlib algebra instance.
-/
structure ObservedResidualDynamics (α β : Type) where
  root : α
  observe : α → β
  observe_injective : Function.Injective observe
  compose : α → α → α
  assoc : ∀ a b c : α,
    compose (compose a b) c = compose a (compose b c)
  root_left : ∀ a : α, compose root a = a
  root_right : ∀ a : α, compose a root = a

namespace ObservedResidualDynamics

/-- Root reachability induced by the sequential law. -/
def Reachable {α β : Type} (D : ObservedResidualDynamics α β)
    (x : α) : Prop :=
  ∃ a : α, D.compose D.root a = x

/-- Ternary relational presentation induced by the deterministic composition. -/
def ComposeRel {α β : Type} (D : ObservedResidualDynamics α β)
    (a b out : α) : Prop :=
  D.compose a b = out

/--
The same witness-free law shape used at the Relay residual-state boundary:
totality, functionality, two-sided identity, and associativity.
-/
structure ComposeRelLaws {α β : Type} (D : ObservedResidualDynamics α β) where
  total : ∀ a b : α, ∃ out : α, D.ComposeRel a b out
  functional : ∀ {a b out out' : α},
    D.ComposeRel a b out → D.ComposeRel a b out' → out = out'
  identity_later : ∀ {a out : α},
    D.ComposeRel a D.root out → out = a
  identity_earlier : ∀ {a out : α},
    D.ComposeRel D.root a out → out = a
  associative : ∀ {a b c ab bc out₁ out₂ : α},
    D.ComposeRel a b ab →
    D.ComposeRel ab c out₁ →
    D.ComposeRel b c bc →
    D.ComposeRel a bc out₂ →
    out₁ = out₂

end ObservedResidualDynamics

/-- Every state is root-reachable in an observed unital dynamics. -/
theorem observedResidualDynamics_all_reachable {α β : Type}
    (D : ObservedResidualDynamics α β) (x : α) :
    D.Reachable x := by
  exact ⟨x, D.root_left x⟩

/--
Every deterministic associative unital observed dynamics induces the complete
witness-free relation-law bundle.  The law bundle constrains a relation; it does
not by itself characterize which relation is present.
-/
theorem observedResidualDynamics_composeRel_laws {α β : Type}
    (D : ObservedResidualDynamics α β) :
    D.ComposeRelLaws := by
  refine {
    total := ?_,
    functional := ?_,
    identity_later := ?_,
    identity_earlier := ?_,
    associative := ?_
  }
  · intro a b
    exact ⟨D.compose a b, rfl⟩
  · intro a b out out' h h'
    exact h.symm.trans h'
  · intro a out h
    exact h.symm.trans (D.root_right a)
  · intro a out h
    exact h.symm.trans (D.root_left a)
  · intro a b c ab bc out₁ out₂ hAB hLeft hBC hRight
    calc
      out₁ = D.compose ab c := hLeft.symm
      _ = D.compose (D.compose a b) c := by rw [← hAB]
      _ = D.compose a (D.compose b c) := D.assoc a b c
      _ = D.compose a bc := by rw [hBC]
      _ = out₂ := hRight

/-- XOR dynamics with complete static observation `id`. -/
def boolXorObservedDynamics : ObservedResidualDynamics Bool Bool where
  root := false
  observe := fun x => x
  observe_injective := by
    intro a b h
    exact h
  compose := boolXorCompose
  assoc := boolXorCompose_assoc
  root_left := boolXorCompose_false_left
  root_right := boolXorCompose_false_right

/-- OR dynamics on the same carrier, root, and complete static observation. -/
def boolOrObservedDynamics : ObservedResidualDynamics Bool Bool where
  root := false
  observe := fun x => x
  observe_injective := by
    intro a b h
    exact h
  compose := boolOrCompose
  assoc := boolOrCompose_assoc
  root_left := boolOrCompose_false_left
  root_right := boolOrCompose_false_right

/-- The two countermodel arms expose literally the same complete static state map. -/
theorem bool_observed_same_static_observation :
    boolXorObservedDynamics.observe = boolOrObservedDynamics.observe := by
  rfl

/-- The two countermodel arms have exactly the same root. -/
theorem bool_observed_same_root :
    boolXorObservedDynamics.root = boolOrObservedDynamics.root := by
  rfl

/-- The two countermodel arms have the same reachable-state predicate. -/
theorem bool_observed_same_reachable (x : Bool) :
    boolXorObservedDynamics.Reachable x ↔
      boolOrObservedDynamics.Reachable x := by
  constructor
  · intro _
    exact observedResidualDynamics_all_reachable boolOrObservedDynamics x
  · intro _
    exact observedResidualDynamics_all_reachable boolXorObservedDynamics x

/-- XOR satisfies the full generic witness-free sequential law bundle. -/
theorem boolXorObservedDynamics_laws :
    boolXorObservedDynamics.ComposeRelLaws :=
  observedResidualDynamics_composeRel_laws boolXorObservedDynamics

/-- OR satisfies the same generic witness-free sequential law bundle. -/
theorem boolOrObservedDynamics_laws :
    boolOrObservedDynamics.ComposeRelLaws :=
  observedResidualDynamics_composeRel_laws boolOrObservedDynamics

/--
Despite identical complete static observation and the same law schema, the
actual induced successor relation differs at `(true,true)`.
-/
theorem bool_observed_composeRel_distinguished :
    boolXorObservedDynamics.ComposeRel true true false ∧
      ¬ boolOrObservedDynamics.ComposeRel true true false := by
  constructor
  · rfl
  · intro h
    cases h

/--
Level-B strengthened negative result for #2822: even complete injective static
state identity, common root/reachability, and the full standard sequential law
schema do not characterize one unique dynamics in general.
-/
theorem complete_static_state_plus_standard_laws_do_not_characterize_dynamics :
    ∃ D₁ D₂ : ObservedResidualDynamics Bool Bool,
      D₁.root = D₂.root ∧
      D₁.observe = D₂.observe ∧
      (∀ x : Bool, D₁.Reachable x ↔ D₂.Reachable x) ∧
      D₁.ComposeRelLaws ∧
      D₂.ComposeRelLaws ∧
      (∃ a b out : Bool,
        D₁.ComposeRel a b out ∧ ¬ D₂.ComposeRel a b out) := by
  refine ⟨boolXorObservedDynamics, boolOrObservedDynamics,
    bool_observed_same_root, bool_observed_same_static_observation, ?_,
    boolXorObservedDynamics_laws, boolOrObservedDynamics_laws, ?_⟩
  · intro x
    exact bool_observed_same_reachable x
  · exact ⟨true, true, false, bool_observed_composeRel_distinguished⟩

/--
Direct bridge to #2813: the current Relay residual relation does satisfy this
law shape.  Combined with the generic countermodel above, this records that the
law shape alone is not a uniqueness theorem for a residual relation.
-/
theorem finKernel_current_residual_relation_has_witness_free_laws {n : Nat}
    (P : FinKernel.ProbeFamily n) (K : FinKernel.FutureContextFamily n) :
    FinKernel.ResidualComposeRelLaws P K :=
  finKernel_residualComposeRel_laws P K

/--
Index-retention audit only: the current complete response carrier is still
explicitly indexed by a context family `K`, and evaluation still requires a
`GeneratedContext K c` witness.  This theorem is deliberately reflexive; its
purpose is to keep the surviving interface dependency visible, not to claim
that `K` is irreducible.
-/
theorem finKernel_fullFutureResponseSpace_context_index_audit {n : Nat}
    (P : FinKernel.ProbeFamily n) (K : FinKernel.FutureContextFamily n)
    (s : FinKernel.FullFutureResponseSpace P K) :
    ∀ c (hc : FinKernel.GeneratedContext K c) m f obs
        (hobs : P obs) x z,
      s c hc m f obs hobs x z = s c hc m f obs hobs x z := by
  intro c hc m f obs hobs x z
  rfl

/-- Acceptance bundle for the #2822 first transaction. -/
theorem residual_law_noncharacterization_bundle :
    (∃ D₁ D₂ : ObservedResidualDynamics Bool Bool,
      D₁.root = D₂.root ∧
      D₁.observe = D₂.observe ∧
      (∀ x : Bool, D₁.Reachable x ↔ D₂.Reachable x) ∧
      D₁.ComposeRelLaws ∧
      D₂.ComposeRelLaws ∧
      (∃ a b out : Bool,
        D₁.ComposeRel a b out ∧ ¬ D₂.ComposeRel a b out)) ∧
    (∀ {n : Nat} (P : FinKernel.ProbeFamily n)
        (K : FinKernel.FutureContextFamily n),
      FinKernel.ResidualComposeRelLaws P K) := by
  constructor
  · exact complete_static_state_plus_standard_laws_do_not_characterize_dynamics
  · intro n P K
    exact finKernel_current_residual_relation_has_witness_free_laws P K

end RelayTheory
