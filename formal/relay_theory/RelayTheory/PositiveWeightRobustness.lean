import RelayTheory.WorkloadWeightedCompression

namespace RelayTheory

/--
A two-coordinate loss profile is robustly no worse when every strictly positive
natural-number weighting gives it weighted loss no greater than the comparator.
This is a finite scalarization property only.
-/
def PositiveWeightRobustNoWorse (candidate baseline : Nat × Nat) : Prop :=
  ∀ w₁ w₂ : Nat,
    0 < w₁ →
    0 < w₂ →
    weightedWorkloadLoss (w₁, w₂) candidate ≤
      weightedWorkloadLoss (w₁, w₂) baseline

/-- Componentwise loss dominance implies no-worse loss under every positive weighting. -/
theorem componentwiseLossDominance_implies_positiveWeightRobustNoWorse
    (candidate baseline : Nat × Nat)
    (h₁ : candidate.1 ≤ baseline.1)
    (h₂ : candidate.2 ≤ baseline.2) :
    PositiveWeightRobustNoWorse candidate baseline := by
  intro w₁ w₂ _ _
  exact Nat.add_le_add
    (Nat.mul_le_mul_left w₁ h₁)
    (Nat.mul_le_mul_left w₂ h₂)

/--
Robust no-worse loss under every strictly positive weighting forces dominance
on the first coordinate. The separating weight keeps the second coordinate
strictly live rather than setting its weight to zero.
-/
theorem positiveWeightRobustNoWorse_implies_firstCoordinateDominance
    (candidate baseline : Nat × Nat)
    (h : PositiveWeightRobustNoWorse candidate baseline) :
    candidate.1 ≤ baseline.1 := by
  apply Nat.le_of_not_gt
  intro hlt
  have hweighted :
      (baseline.2 + 1) * candidate.1 + candidate.2 ≤
        (baseline.2 + 1) * baseline.1 + baseline.2 := by
    simpa [weightedWorkloadLoss] using
      h (baseline.2 + 1) 1 (Nat.zero_lt_succ baseline.2) Nat.zero_lt_one
  have hstep :
      (baseline.2 + 1) * baseline.1 + baseline.2 <
        (baseline.2 + 1) * (baseline.1 + 1) := by
    simpa [Nat.mul_add] using
      Nat.add_lt_add_left
        (Nat.lt_succ_self baseline.2)
        ((baseline.2 + 1) * baseline.1)
  have hmul :
      (baseline.2 + 1) * (baseline.1 + 1) ≤
        (baseline.2 + 1) * candidate.1 :=
    Nat.mul_le_mul_left
      (baseline.2 + 1)
      (Nat.add_one_le_of_lt hlt)
  have hpad :
      (baseline.2 + 1) * candidate.1 ≤
        (baseline.2 + 1) * candidate.1 + candidate.2 :=
    Nat.le_add_right ((baseline.2 + 1) * candidate.1) candidate.2
  have hstrict :
      (baseline.2 + 1) * baseline.1 + baseline.2 <
        (baseline.2 + 1) * candidate.1 + candidate.2 :=
    Nat.lt_of_lt_of_le hstep (Nat.le_trans hmul hpad)
  exact (Nat.not_lt_of_ge hweighted) hstrict

/--
The symmetric separating argument forces dominance on the second coordinate
while keeping the first coordinate at strictly positive weight one.
-/
theorem positiveWeightRobustNoWorse_implies_secondCoordinateDominance
    (candidate baseline : Nat × Nat)
    (h : PositiveWeightRobustNoWorse candidate baseline) :
    candidate.2 ≤ baseline.2 := by
  apply Nat.le_of_not_gt
  intro hlt
  have hweighted :
      candidate.1 + (baseline.1 + 1) * candidate.2 ≤
        baseline.1 + (baseline.1 + 1) * baseline.2 := by
    simpa [weightedWorkloadLoss] using
      h 1 (baseline.1 + 1) Nat.zero_lt_one (Nat.zero_lt_succ baseline.1)
  have hstep :
      baseline.1 + (baseline.1 + 1) * baseline.2 <
        (baseline.1 + 1) * (baseline.2 + 1) := by
    simpa [Nat.mul_add, Nat.add_comm, Nat.add_left_comm, Nat.add_assoc] using
      Nat.add_lt_add_right
        (Nat.lt_succ_self baseline.1)
        ((baseline.1 + 1) * baseline.2)
  have hmul :
      (baseline.1 + 1) * (baseline.2 + 1) ≤
        (baseline.1 + 1) * candidate.2 :=
    Nat.mul_le_mul_left
      (baseline.1 + 1)
      (Nat.add_one_le_of_lt hlt)
  have hpad :
      (baseline.1 + 1) * candidate.2 ≤
        candidate.1 + (baseline.1 + 1) * candidate.2 :=
    Nat.le_add_left ((baseline.1 + 1) * candidate.2) candidate.1
  have hstrict :
      baseline.1 + (baseline.1 + 1) * baseline.2 <
        candidate.1 + (baseline.1 + 1) * candidate.2 :=
    Nat.lt_of_lt_of_le hstep (Nat.le_trans hmul hpad)
  exact (Nat.not_lt_of_ge hweighted) hstrict

/--
Across all strictly positive linear weightings of two natural-number loss
coordinates, robust scalar no-worse ordering is exactly componentwise loss
dominance.
-/
theorem positiveWeightRobustNoWorse_iff_componentwiseLossDominance
    (candidate baseline : Nat × Nat) :
    PositiveWeightRobustNoWorse candidate baseline ↔
      candidate.1 ≤ baseline.1 ∧ candidate.2 ≤ baseline.2 := by
  constructor
  · intro h
    exact ⟨
      positiveWeightRobustNoWorse_implies_firstCoordinateDominance candidate baseline h,
      positiveWeightRobustNoWorse_implies_secondCoordinateDominance candidate baseline h
    ⟩
  · intro h
    exact componentwiseLossDominance_implies_positiveWeightRobustNoWorse
      candidate baseline h.1 h.2

end RelayTheory
