import RelayTheory.Exact

namespace RelayTheory

/-- Exact 2x2 joint law in quarter units. -/
structure JointLaw where
  w00 : Nat
  w01 : Nat
  w10 : Nat
  w11 : Nat
deriving DecidableEq, Repr

namespace JointLaw

/-- Exact normalization for the bounded 2x2 model. -/
def Valid (j : JointLaw) : Prop :=
  j.w00 + j.w01 + j.w10 + j.w11 = 4

/-- First-coordinate exact marginal. -/
def marginalA (j : JointLaw) : BinaryLaw :=
  ⟨j.w00 + j.w01, j.w10 + j.w11⟩

/-- Second-coordinate exact marginal. -/
def marginalB (j : JointLaw) : BinaryLaw :=
  ⟨j.w00 + j.w10, j.w01 + j.w11⟩

end JointLaw

/-- Perfectly correlated uniform binary joint. -/
def correlatedJoint : JointLaw := ⟨2, 0, 0, 2⟩

/-- Perfectly anti-correlated uniform binary joint. -/
def antiCorrelatedJoint : JointLaw := ⟨0, 2, 2, 0⟩

theorem correlatedJoint_valid : correlatedJoint.Valid := rfl

theorem antiCorrelatedJoint_valid : antiCorrelatedJoint.Valid := rfl

/-- Equal one-context marginals do not determine the exact joint alignment. -/
theorem equalMarginals_not_equalJoint :
    correlatedJoint.marginalA = antiCorrelatedJoint.marginalA ∧
    correlatedJoint.marginalB = antiCorrelatedJoint.marginalB ∧
    correlatedJoint ≠ antiCorrelatedJoint := by
  simp [JointLaw.marginalA, JointLaw.marginalB, correlatedJoint, antiCorrelatedJoint]

/--
Explicit candidate/certificate for a bounded global construction. The candidate
joint is not assumed valid merely by being present.
-/
structure RealizabilityCertificate where
  expectedA : BinaryLaw
  expectedB : BinaryLaw
  joint : JointLaw
deriving DecidableEq, Repr

namespace RealizabilityCertificate

/-- Exact fail-closed certificate validation. -/
def Valid (c : RealizabilityCertificate) : Prop :=
  c.expectedA.Valid ∧
  c.expectedB.Valid ∧
  c.joint.Valid ∧
  c.joint.marginalA = c.expectedA ∧
  c.joint.marginalB = c.expectedB

theorem valid_implies_exact_constraints (c : RealizabilityCertificate)
    (h : c.Valid) :
    c.joint.marginalA = c.expectedA ∧
    c.joint.marginalB = c.expectedB := by
  rcases h with ⟨_, _, _, ha, hb⟩
  exact ⟨ha, hb⟩

end RealizabilityCertificate

/-- A valid exact global construction certificate for uniform marginals. -/
def goodCertificate : RealizabilityCertificate :=
  ⟨halfLaw, halfLaw, correlatedJoint⟩

/-- A deliberately invalid certificate: claimed A marginal is a point mass. -/
def badCertificate : RealizabilityCertificate :=
  ⟨deltaLeft, halfLaw, correlatedJoint⟩

theorem goodCertificate_valid : goodCertificate.Valid := by
  simp [RealizabilityCertificate.Valid, goodCertificate, BinaryLaw.Valid, JointLaw.Valid,
    JointLaw.marginalA, JointLaw.marginalB, halfLaw, correlatedJoint]

theorem badCertificate_rejected : ¬ badCertificate.Valid := by
  simp [RealizabilityCertificate.Valid, badCertificate, BinaryLaw.Valid, JointLaw.Valid,
    JointLaw.marginalA, JointLaw.marginalB, deltaLeft, halfLaw, correlatedJoint]

end RelayTheory
