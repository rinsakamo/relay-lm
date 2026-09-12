import RelayTheory.RepresentationFactorization

namespace RelayTheory

/-- The complete finite history set for the two-bit workload-weight fixture. -/
def twoBitHistories : List (Bool × Bool) :=
  [(false, false), (false, true), (true, false), (true, true)]

/-- Unit loss for a wrong Bool prediction and zero loss for a correct one. -/
def boolMismatchLoss (prediction target : Bool) : Nat :=
  if prediction = target then 0 else 1

/--
Finite deterministic error count for one representation/decoder/query triple.
This is only a fixture-level loss; it is not a probability or information measure.
-/
def queryErrorCount
    (rep : Bool × Bool → Bool)
    (decode : Bool → Bool)
    (query : Bool × Bool → Bool) : Nat :=
  (twoBitHistories.map fun h =>
    boolMismatchLoss (decode (rep h)) (query h)).sum

/--
Error profile of the first-bit compression against the two declared future
queries. The identity decoder is intentionally held fixed in this symmetric
fixture.
-/
def firstBitErrorProfile : Nat × Nat :=
  (queryErrorCount firstBit id firstBit,
   queryErrorCount firstBit id secondBit)

/-- Symmetric error profile of the second-bit compression. -/
def secondBitErrorProfile : Nat × Nat :=
  (queryErrorCount secondBit id firstBit,
   queryErrorCount secondBit id secondBit)

/-- Weighted loss over the two declared workload coordinates. -/
def weightedWorkloadLoss (weights errors : Nat × Nat) : Nat :=
  weights.1 * errors.1 + weights.2 * errors.2

/-- Both future queries retain positive weight, with the first query heavier. -/
def firstHeavyWeights : Nat × Nat := (2, 1)

/-- Both future queries retain positive weight, with the second query heavier. -/
def secondHeavyWeights : Nat × Nat := (1, 2)

/-- The first-bit compression is exact for the first query and misses two second-bit cases. -/
theorem firstBit_errorProfile_exact :
    firstBitErrorProfile = (0, 2) := by
  rfl

/-- The second-bit compression has the complementary finite error profile. -/
theorem secondBit_errorProfile_exact :
    secondBitErrorProfile = (2, 0) := by
  rfl

/-- The first-heavy workload keeps both coordinates live. -/
theorem firstHeavyWeights_strictlyPositive :
    0 < firstHeavyWeights.1 ∧ 0 < firstHeavyWeights.2 := by
  decide

/-- The second-heavy workload also keeps both coordinates live. -/
theorem secondHeavyWeights_strictlyPositive :
    0 < secondHeavyWeights.1 ∧ 0 < secondHeavyWeights.2 := by
  decide

/-- Under first-heavy future workload weights, first-bit compression has lower loss. -/
theorem firstHeavy_prefers_firstBit :
    weightedWorkloadLoss firstHeavyWeights firstBitErrorProfile <
      weightedWorkloadLoss firstHeavyWeights secondBitErrorProfile := by
  decide

/-- Under second-heavy future workload weights, second-bit compression has lower loss. -/
theorem secondHeavy_prefers_secondBit :
    weightedWorkloadLoss secondHeavyWeights secondBitErrorProfile <
      weightedWorkloadLoss secondHeavyWeights firstBitErrorProfile := by
  decide

/--
The same histories, candidate representations, decoders, and query semantics
admit opposite strict rankings when only the positive workload weights are
swapped.
-/
theorem lossyRepresentationRanking_reverses_under_workloadWeightSwap :
    (weightedWorkloadLoss firstHeavyWeights firstBitErrorProfile <
      weightedWorkloadLoss firstHeavyWeights secondBitErrorProfile) ∧
    (weightedWorkloadLoss secondHeavyWeights secondBitErrorProfile <
      weightedWorkloadLoss secondHeavyWeights firstBitErrorProfile) := by
  exact ⟨firstHeavy_prefers_firstBit, secondHeavy_prefers_secondBit⟩

end RelayTheory
