import RelayTheory.Transform
import RelayTheory.Alignment

namespace RelayTheory

/-- Reference signature used to show equivalence is derived, not stored. -/
def signatureBase : OperationalSignature :=
  {
    base := halfLaw
    observeAudit := true
    observeResource := false
    chooseAdmitted := true
    substituteAdmitted := false
    responses := ⟨deltaLeft, halfLaw⟩
  }

/-- Same public signature, different declaration name is intentionally absent. -/
def signatureClone : OperationalSignature := signatureBase

/-- One exact public response differs. -/
def signatureChanged : OperationalSignature :=
  {
    base := halfLaw
    observeAudit := true
    observeResource := false
    chooseAdmitted := true
    substituteAdmitted := false
    responses := ⟨deltaRight, halfLaw⟩
  }

theorem samePublicSignature_equivalent :
    BehaviorEquivalent signatureBase signatureClone := rfl

theorem changedExactResponse_not_equivalent :
    ¬ BehaviorEquivalent signatureBase signatureChanged := by
  simp [BehaviorEquivalent, signatureBase, signatureChanged, deltaLeft, deltaRight, halfLaw]

/-- All first Lean milestone countermodels hold simultaneously. -/
theorem finiteCore_countermodel_bundle :
    (halfLaw.support = skewLaw.support ∧ halfLaw ≠ skewLaw) ∧
    (unresolvedSelectableResponses ≠ [resolvedMixedResponse]) ∧
    (transformAccessCoarse.admits historyChoice = false ∧
      transformAccessRich.admits historyChoice = true) ∧
    BehaviorEquivalent signatureBase signatureClone ∧
    (¬ BehaviorEquivalent signatureBase signatureChanged) ∧
    (correlatedJoint.marginalA = antiCorrelatedJoint.marginalA ∧
      correlatedJoint.marginalB = antiCorrelatedJoint.marginalB ∧
      correlatedJoint ≠ antiCorrelatedJoint) ∧
    goodCertificate.Valid ∧
    ¬ badCertificate.Valid := by
  exact ⟨
    sameSupport_not_sameExactLaw,
    unresolvedFamily_ne_resolvedSingleton,
    information_changes_admissibility,
    samePublicSignature_equivalent,
    changedExactResponse_not_equivalent,
    equalMarginals_not_equalJoint,
    goodCertificate_valid,
    badCertificate_rejected
  ⟩

end RelayTheory
