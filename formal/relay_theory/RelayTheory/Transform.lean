import RelayTheory.Exact
import RelayTheory.Access

namespace RelayTheory

inductive CommandId where
  | choose
  | substitute
deriving DecidableEq, Repr

/--
One payload-free public experiment transformation contract. The command exposes
only identity plus declared read/write requirements; its exact behavior lives in
a separate response table.
-/
structure TransformCommand where
  name : CommandId
  readsHistory : Bool
  readsMechanism : Bool
  writesChoice : Bool
  writesMechanism : Bool
deriving DecidableEq, Repr

/-- Whether a command name is admitted by the current access declaration. -/
def AccessSpec.commandEnabled (a : AccessSpec) (name : CommandId) : Bool :=
  match name with
  | .choose => a.admitChoose
  | .substitute => a.admitSubstitute

/--
Admissibility is exactly declared command capability plus sufficient visible
information for every public read requirement.
-/
def AccessSpec.admits (a : AccessSpec) (command : TransformCommand) : Bool :=
  a.commandEnabled command.name &&
    (!command.readsHistory || a.visibleHistory) &&
    (!command.readsMechanism || a.visibleMechanism)

/-- Exact resolved response table for the two bounded public commands. -/
structure ResponseTable where
  chooseResponse : BinaryLaw
  substituteResponse : BinaryLaw
deriving DecidableEq, Repr

/-- Exact public operational signature; behavioral equivalence is derived from it. -/
structure OperationalSignature where
  base : BinaryLaw
  observeAudit : Bool
  observeResource : Bool
  chooseAdmitted : Bool
  substituteAdmitted : Bool
  responses : ResponseTable
deriving DecidableEq, Repr

/-- No quotient identity is stored: equivalence is exact public-signature equality. -/
def BehaviorEquivalent (x y : OperationalSignature) : Prop :=
  x = y

theorem behaviorEquivalent_refl (x : OperationalSignature) :
    BehaviorEquivalent x x := rfl

/-- A choice command requiring access to history. -/
def historyChoice : TransformCommand :=
  ⟨.choose, true, false, true, false⟩

/-- Coarse information blocks history-dependent choice. -/
def transformAccessCoarse : AccessSpec :=
  ⟨true, false, true, false, false, false⟩

/-- Richer information admits the same public choice command. -/
def transformAccessRich : AccessSpec :=
  ⟨true, false, true, false, true, false⟩

theorem information_changes_admissibility :
    transformAccessCoarse.admits historyChoice = false ∧
    transformAccessRich.admits historyChoice = true := by
  decide

/-- Unresolved selectable capability: two exact responses remain available. -/
def unresolvedSelectableResponses : List BinaryLaw :=
  [deltaLeft, deltaRight]

/-- One resolved stochastic response. -/
def resolvedMixedResponse : BinaryLaw := halfLaw

/-- A selectable family is not the same object as one resolved response. -/
theorem unresolvedFamily_ne_resolvedSingleton :
    unresolvedSelectableResponses ≠ [resolvedMixedResponse] := by
  decide

end RelayTheory
