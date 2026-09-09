import Std

namespace RelayTheory

/--
Finite declarative access for the bounded 0.1 core. Names are deliberately
absent: only observable/admissible/information bits enter semantics.
-/
structure AccessSpec where
  observeAudit : Bool
  observeResource : Bool
  admitChoose : Bool
  admitSubstitute : Bool
  visibleHistory : Bool
  visibleMechanism : Bool
deriving DecidableEq, Repr

/-- Boolean inclusion used only for observational capability. -/
def BoolLe (a b : Bool) : Prop :=
  a = true → b = true

/--
Pure forgetting may remove observations but must not change transform
capability or the information available to transforms.
-/
def PureForgetting (coarse rich : AccessSpec) : Prop :=
  BoolLe coarse.observeAudit rich.observeAudit ∧
  BoolLe coarse.observeResource rich.observeResource ∧
  coarse.admitChoose = rich.admitChoose ∧
  coarse.admitSubstitute = rich.admitSubstitute ∧
  coarse.visibleHistory = rich.visibleHistory ∧
  coarse.visibleMechanism = rich.visibleMechanism

theorem pureForgetting_refl (a : AccessSpec) : PureForgetting a a := by
  constructor
  · intro h
    exact h
  constructor
  · intro h
    exact h
  exact ⟨rfl, rfl, rfl, rfl⟩

theorem pureForgetting_trans {a b c : AccessSpec}
    (hab : PureForgetting a b) (hbc : PureForgetting b c) :
    PureForgetting a c := by
  rcases hab with ⟨haudit₁, hresource₁, hchoose₁, hsub₁, hhistory₁, hmechanism₁⟩
  rcases hbc with ⟨haudit₂, hresource₂, hchoose₂, hsub₂, hhistory₂, hmechanism₂⟩
  refine ⟨?_, ?_, hchoose₁.trans hchoose₂, hsub₁.trans hsub₂,
    hhistory₁.trans hhistory₂, hmechanism₁.trans hmechanism₂⟩
  · intro h
    exact haudit₂ (haudit₁ h)
  · intro h
    exact hresource₂ (hresource₁ h)

/-- A three-step bounded forgetting chain used as the structural witness. -/
def accessCoarse : AccessSpec :=
  ⟨false, false, true, true, true, true⟩

def accessMiddle : AccessSpec :=
  ⟨true, false, true, true, true, true⟩

def accessRich : AccessSpec :=
  ⟨true, true, true, true, true, true⟩

theorem coarse_forgets_middle : PureForgetting accessCoarse accessMiddle := by
  simp [PureForgetting, BoolLe, accessCoarse, accessMiddle]

theorem middle_forgets_rich : PureForgetting accessMiddle accessRich := by
  simp [PureForgetting, BoolLe, accessMiddle, accessRich]

theorem coarse_forgets_rich : PureForgetting accessCoarse accessRich :=
  pureForgetting_trans coarse_forgets_middle middle_forgets_rich

end RelayTheory
