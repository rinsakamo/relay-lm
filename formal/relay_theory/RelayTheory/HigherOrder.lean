import RelayTheory.Alignment

namespace RelayTheory

/--
Exact binary triple law in quarter units for the bounded higher-order
alignment/gluing witnesses. The eight fields correspond to outcomes
`000, 001, 010, 011, 100, 101, 110, 111`.
-/
structure TripleLaw where
  w000 : Nat
  w001 : Nat
  w010 : Nat
  w011 : Nat
  w100 : Nat
  w101 : Nat
  w110 : Nat
  w111 : Nat
deriving DecidableEq, Repr

namespace TripleLaw

/-- Exact normalization for the bounded denominator-four triple model. -/
def Valid (t : TripleLaw) : Prop :=
  t.w000 + t.w001 + t.w010 + t.w011 +
    t.w100 + t.w101 + t.w110 + t.w111 = 4

/-- Exact `(A,B)` marginal, summing over `C`. -/
def pairAB (t : TripleLaw) : JointLaw :=
  ⟨t.w000 + t.w001, t.w010 + t.w011,
   t.w100 + t.w101, t.w110 + t.w111⟩

/-- Exact `(B,C)` marginal, summing over `A`. -/
def pairBC (t : TripleLaw) : JointLaw :=
  ⟨t.w000 + t.w100, t.w001 + t.w101,
   t.w010 + t.w110, t.w011 + t.w111⟩

/-- Exact `(A,C)` marginal, summing over `B`. -/
def pairAC (t : TripleLaw) : JointLaw :=
  ⟨t.w000 + t.w010, t.w001 + t.w011,
   t.w100 + t.w110, t.w101 + t.w111⟩

/-- Exact mass on even-parity outcomes. -/
def evenParityMass (t : TripleLaw) : Nat :=
  t.w000 + t.w011 + t.w101 + t.w110

end TripleLaw

/-- Uniform pair law: every binary pair outcome has exact mass `1/4`. -/
def uniformPair : JointLaw := ⟨1, 1, 1, 1⟩

/-- Even-parity triple: `000,011,101,110` each have exact mass `1/4`. -/
def evenParityTriple : TripleLaw :=
  ⟨1, 0, 0, 1, 0, 1, 1, 0⟩

/-- Odd-parity triple: `001,010,100,111` each have exact mass `1/4`. -/
def oddParityTriple : TripleLaw :=
  ⟨0, 1, 1, 0, 1, 0, 0, 1⟩

theorem evenParityTriple_valid : evenParityTriple.Valid := rfl

theorem oddParityTriple_valid : oddParityTriple.Valid := rfl

theorem evenParity_pairwise_uniform :
    evenParityTriple.pairAB = uniformPair ∧
    evenParityTriple.pairBC = uniformPair ∧
    evenParityTriple.pairAC = uniformPair := by
  exact ⟨rfl, rfl, rfl⟩

theorem oddParity_pairwise_uniform :
    oddParityTriple.pairAB = uniformPair ∧
    oddParityTriple.pairBC = uniformPair ∧
    oddParityTriple.pairAC = uniformPair := by
  exact ⟨rfl, rfl, rfl⟩

/-- All three pairwise marginals agree exactly between even and odd parity. -/
theorem parity_pairwise_equal :
    evenParityTriple.pairAB = oddParityTriple.pairAB ∧
    evenParityTriple.pairBC = oddParityTriple.pairBC ∧
    evenParityTriple.pairAC = oddParityTriple.pairAC := by
  exact ⟨rfl, rfl, rfl⟩

/-- The full triples remain unequal despite identical pairwise marginals. -/
theorem parity_triples_unequal : evenParityTriple ≠ oddParityTriple := by
  intro h
  have h000 := congrArg (fun t : TripleLaw => t.w000) h
  simp [evenParityTriple, oddParityTriple] at h000

/-- A smallest exact triple probe separates the two parity witnesses. -/
theorem parity_probe_distinguishes :
    evenParityTriple.evenParityMass = 4 ∧
    oddParityTriple.evenParityMass = 0 := by
  exact ⟨rfl, rfl⟩

/-- Pairwise data do not determine one unique triple joint. -/
theorem samePairwise_not_sameTriple :
    (evenParityTriple.pairAB = oddParityTriple.pairAB ∧
     evenParityTriple.pairBC = oddParityTriple.pairBC ∧
     evenParityTriple.pairAC = oddParityTriple.pairAC) ∧
    evenParityTriple ≠ oddParityTriple :=
  ⟨parity_pairwise_equal, parity_triples_unequal⟩

/-- Fair perfect anti-correlation on one binary pair. -/
def antiPair : JointLaw := ⟨0, 2, 2, 0⟩

theorem antiPair_valid : antiPair.Valid := rfl

theorem antiPair_has_fair_singletons :
    antiPair.marginalA = halfLaw ∧
    antiPair.marginalB = halfLaw := by
  exact ⟨rfl, rfl⟩

/-- Three local pair contexts over coordinates `AB`, `BC`, and `AC`. -/
structure PairContextFamily where
  ab : JointLaw
  bc : JointLaw
  ac : JointLaw
deriving DecidableEq, Repr

namespace PairContextFamily

/-- Exact agreement on all singleton overlaps of `AB`, `BC`, and `AC`. -/
def OverlapConsistent (f : PairContextFamily) : Prop :=
  f.ab.marginalA = f.ac.marginalA ∧
  f.ab.marginalB = f.bc.marginalA ∧
  f.bc.marginalB = f.ac.marginalB

/-- One exact triple realizes all three local pair laws. -/
def RealizedBy (f : PairContextFamily) (t : TripleLaw) : Prop :=
  t.Valid ∧
  t.pairAB = f.ab ∧
  t.pairBC = f.bc ∧
  t.pairAC = f.ac

end PairContextFamily

/-- Locally valid fair anti-correlation on every edge of the triangle. -/
def antiTriangle : PairContextFamily :=
  ⟨antiPair, antiPair, antiPair⟩

/-- Matched positive control: fair equality on every edge. -/
def equalityTriangle : PairContextFamily :=
  ⟨correlatedJoint, correlatedJoint, correlatedJoint⟩

theorem antiTriangle_local_laws_valid :
    antiTriangle.ab.Valid ∧ antiTriangle.bc.Valid ∧ antiTriangle.ac.Valid := by
  exact ⟨antiPair_valid, antiPair_valid, antiPair_valid⟩

theorem antiTriangle_overlap_consistent : antiTriangle.OverlapConsistent := by
  simp [PairContextFamily.OverlapConsistent, antiTriangle, antiPair,
    JointLaw.marginalA, JointLaw.marginalB]

/--
Odd-cycle obstruction: no exact binary triple can realize fair anti-correlation
on `AB`, `BC`, and `AC` simultaneously. This is a finite theorem, not a claim
about arbitrary marginal polytopes.
-/
theorem antiTriangle_not_globally_realizable :
    ¬ ∃ t : TripleLaw, antiTriangle.RealizedBy t := by
  intro h
  rcases h with ⟨t, _hvalid, hab, hbc, hac⟩
  have hab01 : t.w010 + t.w011 = 2 := by
    have hfield := congrArg (fun j : JointLaw => j.w01) hab
    simpa [TripleLaw.pairAB, antiTriangle, antiPair] using hfield
  have hbc11 : t.w011 + t.w111 = 0 := by
    have hfield := congrArg (fun j : JointLaw => j.w11) hbc
    simpa [TripleLaw.pairBC, antiTriangle, antiPair] using hfield
  have hac00 : t.w000 + t.w010 = 0 := by
    have hfield := congrArg (fun j : JointLaw => j.w00) hac
    simpa [TripleLaw.pairAC, antiTriangle, antiPair] using hfield
  rcases Nat.add_eq_zero_iff.mp hbc11 with ⟨h011, _h111⟩
  rcases Nat.add_eq_zero_iff.mp hac00 with ⟨_h000, h010⟩
  simp [h010, h011] at hab01

/-- Explicit global witness for the equality-triangle positive control. -/
def equalityTriangleWitness : TripleLaw :=
  ⟨2, 0, 0, 0, 0, 0, 0, 2⟩

theorem equalityTriangleWitness_realizes :
    equalityTriangle.RealizedBy equalityTriangleWitness := by
  exact ⟨rfl, rfl, rfl, rfl⟩

/-- Explicit witness after ablating the `AC` anti-correlation edge. -/
def antiChainWitness : TripleLaw :=
  ⟨0, 0, 2, 0, 0, 2, 0, 0⟩

theorem antiChainWitness_valid : antiChainWitness.Valid := rfl

theorem antiChainWitness_realizes_AB_BC :
    antiChainWitness.pairAB = antiPair ∧
    antiChainWitness.pairBC = antiPair := by
  exact ⟨rfl, rfl⟩

/--
Adding the locally valid `AC` anti-correlation edge destroys all global
completions while leaving the pre-existing `AB` and `BC` laws unchanged.
-/
theorem contextExpansion_can_destroy_realizability :
    (∃ t : TripleLaw,
      t.Valid ∧ t.pairAB = antiPair ∧ t.pairBC = antiPair) ∧
    (¬ ∃ t : TripleLaw, antiTriangle.RealizedBy t) := by
  constructor
  · exact ⟨antiChainWitness, antiChainWitness_valid,
      antiChainWitness_realizes_AB_BC.1,
      antiChainWitness_realizes_AB_BC.2⟩
  · exact antiTriangle_not_globally_realizable

/-- All higher-order/gluing acceptance witnesses hold simultaneously. -/
theorem higherOrder_countermodel_bundle :
    evenParityTriple.Valid ∧
    oddParityTriple.Valid ∧
    (evenParityTriple.pairAB = oddParityTriple.pairAB ∧
      evenParityTriple.pairBC = oddParityTriple.pairBC ∧
      evenParityTriple.pairAC = oddParityTriple.pairAC) ∧
    evenParityTriple ≠ oddParityTriple ∧
    (evenParityTriple.evenParityMass = 4 ∧
      oddParityTriple.evenParityMass = 0) ∧
    (antiTriangle.ab.Valid ∧ antiTriangle.bc.Valid ∧ antiTriangle.ac.Valid) ∧
    antiTriangle.OverlapConsistent ∧
    (¬ ∃ t : TripleLaw, antiTriangle.RealizedBy t) ∧
    equalityTriangle.RealizedBy equalityTriangleWitness ∧
    (antiChainWitness.Valid ∧
      antiChainWitness.pairAB = antiPair ∧
      antiChainWitness.pairBC = antiPair) := by
  exact ⟨
    evenParityTriple_valid,
    oddParityTriple_valid,
    parity_pairwise_equal,
    parity_triples_unequal,
    parity_probe_distinguishes,
    antiTriangle_local_laws_valid,
    antiTriangle_overlap_consistent,
    antiTriangle_not_globally_realizable,
    equalityTriangleWitness_realizes,
    antiChainWitness_valid,
    antiChainWitness_realizes_AB_BC.1,
    antiChainWitness_realizes_AB_BC.2
  ⟩

end RelayTheory
