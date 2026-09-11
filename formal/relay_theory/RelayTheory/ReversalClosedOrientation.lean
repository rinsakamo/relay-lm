import RelayTheory.IntrinsicKernelDegradation

namespace RelayTheory

/-- The asymmetric/strict part of an arbitrary binary relation. -/
def StrictPart {α : Type} (R : α → α → Prop) (x y : α) : Prop :=
  R x y ∧ ¬ R y x

/-- An admissibility relation permits the reversed edge whenever it permits an edge. -/
def ReversalClosed {α : Type} (Adm : α → α → Prop) : Prop :=
  ∀ ⦃x y : α⦄, Adm x y → Adm y x

/-- Every admissible nontrivial edge follows one strict orientation of `R`. -/
def StrictlyOrientedBy {α : Type}
    (Adm R : α → α → Prop) : Prop :=
  ∀ ⦃x y : α⦄, Adm x y → x ≠ y → StrictPart R x y

/-- The admissibility relation contains at least one nontrivial edge. -/
def NontrivialAdmissibility {α : Type}
    (Adm : α → α → Prop) : Prop :=
  ∃ x y, Adm x y ∧ x ≠ y

/-- A nontrivial admissibility relation whose every nontrivial edge follows one strict orientation. -/
def SupportsStrictOrientation {α : Type}
    (Adm R : α → α → Prop) : Prop :=
  NontrivialAdmissibility Adm ∧ StrictlyOrientedBy Adm R

/-- The strict part of any relation is asymmetric by construction. -/
theorem strictPart_asymmetric {α : Type} {R : α → α → Prop} {x y : α}
    (hxy : StrictPart R x y) : ¬ StrictPart R y x := by
  intro hyx
  exact hxy.2 hyx.1

/--
Generic reversal obstruction. If every admissible edge has an admissible reverse,
then a global strict orientation can classify only diagonal admissible edges.
No order axioms on `R` are needed.
-/
theorem reversalClosed_strictlyOrientedBy_only_diagonal
    {α : Type} {Adm R : α → α → Prop}
    (hrev : ReversalClosed Adm)
    (horient : StrictlyOrientedBy Adm R) :
    ∀ ⦃x y : α⦄, Adm x y → x = y := by
  intro x y hxy
  by_contra hne
  have hforward : StrictPart R x y := horient hxy hne
  have hyx : Adm y x := hrev hxy
  have hbackward : StrictPart R y x := horient hyx (fun h => hne h.symm)
  exact hforward.2 hbackward.1

/--
Therefore reversal-closed admissibility cannot support any nontrivial global
strict orientation, regardless of which relation is proposed as the arrow.
-/
theorem reversalClosed_not_supportsStrictOrientation
    {α : Type} {Adm R : α → α → Prop}
    (hrev : ReversalClosed Adm) :
    ¬ SupportsStrictOrientation Adm R := by
  intro hsupport
  rcases hsupport.1 with ⟨x, y, hxy, hne⟩
  have hEq := reversalClosed_strictlyOrientedBy_only_diagonal hrev hsupport.2 hxy
  exact hne hEq

/--
A minimal two-way admissibility relation: diagonal edges plus both directions
between two distinguished points.
-/
def TwoWayPairAdm {α : Type} (a b : α) (x y : α) : Prop :=
  x = y ∨ (x = a ∧ y = b) ∨ (x = b ∧ y = a)

/-- The two-way pair relation is reversal-closed for arbitrary carrier type. -/
theorem twoWayPairAdm_reversalClosed {α : Type} (a b : α) :
    ReversalClosed (TwoWayPairAdm a b) := by
  intro x y hxy
  rcases hxy with hdiag | hab | hba
  · exact Or.inl hdiag.symm
  · exact Or.inr (Or.inr ⟨hab.2, hab.1⟩)
  · exact Or.inr (Or.inl ⟨hba.2, hba.1⟩)

/-- The distinguished forward edge is admissible. -/
theorem twoWayPairAdm_edge {α : Type} (a b : α) :
    TwoWayPairAdm a b a b := by
  exact Or.inr (Or.inl ⟨rfl, rfl⟩)

/-- Distinct distinguished points make the two-way relation nontrivial. -/
theorem twoWayPairAdm_nontrivial {α : Type} {a b : α} (hne : a ≠ b) :
    NontrivialAdmissibility (TwoWayPairAdm a b) := by
  exact ⟨a, b, twoWayPairAdm_edge a b, hne⟩

/-- No relation can globally strictly orient a genuine two-way admissible pair. -/
theorem twoWayPairAdm_not_strictlyOriented
    {α : Type} {a b : α} (hne : a ≠ b) (R : α → α → Prop) :
    ¬ StrictlyOrientedBy (TwoWayPairAdm a b) R := by
  intro horient
  have hEq := reversalClosed_strictlyOrientedBy_only_diagonal
    (twoWayPairAdm_reversalClosed a b) horient (twoWayPairAdm_edge a b)
  exact hne hEq

/-- Small finite anti-vacuity control: a genuine binary reversible pair exists. -/
theorem binary_two_way_pair_obstruction :
    ReversalClosed (TwoWayPairAdm (0 : Fin 2) (1 : Fin 2)) ∧
      NontrivialAdmissibility (TwoWayPairAdm (0 : Fin 2) (1 : Fin 2)) ∧
      (∀ R : Fin 2 → Fin 2 → Prop,
        ¬ StrictlyOrientedBy (TwoWayPairAdm (0 : Fin 2) (1 : Fin 2)) R) := by
  refine ⟨twoWayPairAdm_reversalClosed (0 : Fin 2) (1 : Fin 2), ?_, ?_⟩
  · exact twoWayPairAdm_nontrivial (by decide)
  · intro R
    exact twoWayPairAdm_not_strictlyOriented (by decide) R

/-- A one-way admissibility restriction: diagonal edges plus one distinguished direction. -/
def OneWayPairAdm {α : Type} (a b : α) (x y : α) : Prop :=
  x = y ∨ (x = a ∧ y = b)

/-- The distinguished one-way edge is admissible. -/
theorem oneWayPairAdm_edge {α : Type} (a b : α) :
    OneWayPairAdm a b a b := by
  exact Or.inr ⟨rfl, rfl⟩

/-- If `a -> b` is strict in `R`, the one-way restriction is globally strictly oriented by `R`. -/
theorem oneWayPairAdm_strictlyOriented
    {α : Type} {a b : α} {R : α → α → Prop}
    (hstrict : StrictPart R a b) :
    StrictlyOrientedBy (OneWayPairAdm a b) R := by
  intro x y hxy hne
  rcases hxy with hdiag | hab
  · exact False.elim (hne hdiag)
  · rcases hab with ⟨rfl, rfl⟩
    exact hstrict

/-- A genuine one-way pair is not reversal-closed. -/
theorem oneWayPairAdm_not_reversalClosed
    {α : Type} {a b : α} (hne : a ≠ b) :
    ¬ ReversalClosed (OneWayPairAdm a b) := by
  intro hrev
  have hback : OneWayPairAdm a b b a := hrev (oneWayPairAdm_edge a b)
  rcases hback with hdiag | hab
  · exact hne hdiag.symm
  · exact hne hab.1.symm

/-- The intrinsic kernel-derived diamond has a genuine strict fine-to-middle-A edge. -/
theorem intrinsic_fine_middleA_strict :
    StrictPart IntrinsicDegradationRel (0 : Fin 4) (1 : Fin 4) := by
  exact ⟨intrinsicDegradationRel_01, not_intrinsicDegradationRel_10⟩

/--
If both directions between the same intrinsic information states are declared
admissible, the intrinsic degradation relation cannot globally orient them.
-/
theorem intrinsic_two_way_fine_middleA_not_oriented :
    ¬ StrictlyOrientedBy
      (TwoWayPairAdm (0 : Fin 4) (1 : Fin 4)) IntrinsicDegradationRel := by
  exact twoWayPairAdm_not_strictlyOriented (by decide) IntrinsicDegradationRel

/-- The same two-way intrinsic-state control is genuinely reversal-closed and nontrivial. -/
theorem intrinsic_two_way_fine_middleA_control :
    ReversalClosed (TwoWayPairAdm (0 : Fin 4) (1 : Fin 4)) ∧
      NontrivialAdmissibility (TwoWayPairAdm (0 : Fin 4) (1 : Fin 4)) := by
  exact ⟨twoWayPairAdm_reversalClosed (0 : Fin 4) (1 : Fin 4),
    twoWayPairAdm_nontrivial (by decide)⟩

/--
Positive asymmetric control: once admissibility itself keeps only the strict
fine-to-middle-A direction, the intrinsic information relation does orient the
nontrivial transition.
-/
theorem intrinsic_one_way_fine_middleA_oriented :
    StrictlyOrientedBy
      (OneWayPairAdm (0 : Fin 4) (1 : Fin 4)) IntrinsicDegradationRel := by
  exact oneWayPairAdm_strictlyOriented intrinsic_fine_middleA_strict

/-- The successful one-way intrinsic control explicitly breaks reversal closure. -/
theorem intrinsic_one_way_fine_middleA_not_reversalClosed :
    ¬ ReversalClosed (OneWayPairAdm (0 : Fin 4) (1 : Fin 4)) := by
  exact oneWayPairAdm_not_reversalClosed (by decide)

/-- Final owner-local acceptance bundle for the reversal-closed orientation obstruction. -/
theorem reversal_closed_orientation_bundle :
    StrictPart IntrinsicDegradationRel (0 : Fin 4) (1 : Fin 4) ∧
      ReversalClosed (TwoWayPairAdm (0 : Fin 4) (1 : Fin 4)) ∧
      NontrivialAdmissibility (TwoWayPairAdm (0 : Fin 4) (1 : Fin 4)) ∧
      (¬ StrictlyOrientedBy
        (TwoWayPairAdm (0 : Fin 4) (1 : Fin 4)) IntrinsicDegradationRel) ∧
      StrictlyOrientedBy
        (OneWayPairAdm (0 : Fin 4) (1 : Fin 4)) IntrinsicDegradationRel ∧
      (¬ ReversalClosed (OneWayPairAdm (0 : Fin 4) (1 : Fin 4))) := by
  exact ⟨intrinsic_fine_middleA_strict,
    intrinsic_two_way_fine_middleA_control.1,
    intrinsic_two_way_fine_middleA_control.2,
    intrinsic_two_way_fine_middleA_not_oriented,
    intrinsic_one_way_fine_middleA_oriented,
    intrinsic_one_way_fine_middleA_not_reversalClosed⟩

end RelayTheory
