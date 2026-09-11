import RelayTheory.StochasticRecoverabilityPreorder

namespace RelayTheory

/-- Every element of `Fin 4` is one of the four explicit labels. -/
theorem finFour_zero_or_one_or_two_or_three (x : Fin 4) :
    x = (0 : Fin 4) ∨ x = (1 : Fin 4) ∨ x = (2 : Fin 4) ∨ x = (3 : Fin 4) := by
  have hx := x.isLt
  grind

/--
Exact finite correlation-only source carrier.

Flat joint labels are interpreted as:

* `0 = (0,0)`
* `1 = (0,1)`
* `2 = (1,0)`
* `3 = (1,1)`

For source `0` the joint law is fair on `0,3`; for source `1` it is fair on
`1,2`. Thus each coordinate marginal is fair and source-blind, while parity
recovers the source exactly.
-/
def correlationCarrier : FinKernel 2 4 :=
  fun x y =>
    if x.val = 0 then
      if y.val = 0 ∨ y.val = 3 then qHalf else 0
    else
      if y.val = 1 ∨ y.val = 2 then qHalf else 0

/-- First-coordinate observer on the flat four-point joint interface. -/
def correlationFirst : Fin 4 → Fin 2 :=
  fun y => if y.val = 0 ∨ y.val = 1 then (0 : Fin 2) else (1 : Fin 2)

/-- Second-coordinate observer on the flat four-point joint interface. -/
def correlationSecond : Fin 4 → Fin 2 :=
  fun y => if y.val = 0 ∨ y.val = 2 then (0 : Fin 2) else (1 : Fin 2)

/-- Joint parity observer: equal coordinate bits map to source `0`, unequal to source `1`. -/
def correlationParity : Fin 4 → Fin 2 :=
  fun y => if y.val = 0 ∨ y.val = 3 then (0 : Fin 2) else (1 : Fin 2)

/-- Completely source-blind fair binary observation. -/
def correlationBlindMarginal : FinKernel 2 2 :=
  fun _ _ => qHalf

/-- The joint correlation carrier is a valid stochastic kernel. -/
theorem correlationCarrier_valid : FinKernel.Valid correlationCarrier := by
  constructor
  · intro x y
    have hh : 0 ≤ qHalf := Rat.le_of_lt qHalf_pos
    unfold correlationCarrier
    split <;> split <;> simp [hh]
  · intro x
    rcases finTwo_zero_or_one x with hx | hx
    · subst x
      grind [FinKernel.rowSum, correlationCarrier, sumFin, qHalf]
    · subst x
      grind [FinKernel.rowSum, correlationCarrier, sumFin, qHalf]

/-- The source-blind fair marginal is itself stochastic-valid. -/
theorem correlationBlindMarginal_valid :
    FinKernel.Valid correlationBlindMarginal := by
  constructor
  · intro x y
    exact Rat.le_of_lt qHalf_pos
  · intro x
    rcases finTwo_zero_or_one x with hx | hx <;> subst x <;>
      grind [FinKernel.rowSum, correlationBlindMarginal, sumFin, qHalf]

/-- The first coordinate marginal has exactly the same law for both source values. -/
theorem correlationCarrier_first_marginal_blind :
    FinKernel.compose (FinKernel.dirac correlationFirst) correlationCarrier =
      correlationBlindMarginal := by
  funext x z
  rcases finTwo_zero_or_one x with hx | hx <;> subst x
  all_goals
    rcases finTwo_zero_or_one z with hz | hz <;> subst z <;>
      grind [FinKernel.compose, FinKernel.dirac, correlationCarrier,
        correlationFirst, correlationBlindMarginal, sumFin, qHalf]

/-- The second coordinate marginal is also exactly source-blind. -/
theorem correlationCarrier_second_marginal_blind :
    FinKernel.compose (FinKernel.dirac correlationSecond) correlationCarrier =
      correlationBlindMarginal := by
  funext x z
  rcases finTwo_zero_or_one x with hx | hx <;> subst x
  all_goals
    rcases finTwo_zero_or_one z with hz | hz <;> subst z <;>
      grind [FinKernel.compose, FinKernel.dirac, correlationCarrier,
        correlationSecond, correlationBlindMarginal, sumFin, qHalf]

/-- The joint parity observer recovers the source identity exactly. -/
theorem correlationCarrier_parity_recovers :
    FinKernel.compose (FinKernel.dirac correlationParity) correlationCarrier =
      FinKernel.identity 2 := by
  funext x z
  rcases finTwo_zero_or_one x with hx | hx <;> subst x
  all_goals
    rcases finTwo_zero_or_one z with hz | hz <;> subst z <;>
      grind [FinKernel.compose, FinKernel.dirac, FinKernel.identity,
        correlationCarrier, correlationParity, sumFin, qHalf]

/-- The joint carrier therefore has a valid stochastic recovery. -/
theorem correlationCarrier_hasValidStochasticRecovery :
    FinKernel.HasValidStochasticRecovery correlationCarrier := by
  exact ⟨FinKernel.dirac correlationParity,
    finKernel_dirac_valid correlationParity,
    correlationCarrier_parity_recovers⟩

/-- Source identity can be stochastically encoded into the joint correlation carrier. -/
theorem identity2_stochasticDegradesTo_correlationCarrier :
    FinKernel.StochasticDegradesTo (FinKernel.identity 2) correlationCarrier := by
  exact ⟨correlationCarrier,
    correlationCarrier_valid,
    finKernel_compose_identity_before correlationCarrier⟩

/-- The joint carrier stochastically degrades back to source identity via parity. -/
theorem correlationCarrier_stochasticDegradesTo_identity2 :
    FinKernel.StochasticDegradesTo correlationCarrier (FinKernel.identity 2) := by
  exact ⟨FinKernel.dirac correlationParity,
    finKernel_dirac_valid correlationParity,
    correlationCarrier_parity_recovers⟩

/-- The joint carrier is Blackwell-style equivalent to the source identity experiment. -/
theorem correlationCarrier_stochasticEquivalent_identity2 :
    FinKernel.StochasticEquivalent correlationCarrier (FinKernel.identity 2) := by
  exact ⟨correlationCarrier_stochasticDegradesTo_identity2,
    identity2_stochasticDegradesTo_correlationCarrier⟩

/-- Each marginal is obtained from the joint carrier by an ordinary valid postprocessing. -/
theorem correlationCarrier_degradesTo_both_blind_marginals :
    FinKernel.StochasticDegradesTo correlationCarrier correlationBlindMarginal ∧
      FinKernel.StochasticDegradesTo correlationCarrier correlationBlindMarginal := by
  exact ⟨⟨FinKernel.dirac correlationFirst,
      finKernel_dirac_valid correlationFirst,
      correlationCarrier_first_marginal_blind⟩,
    ⟨FinKernel.dirac correlationSecond,
      finKernel_dirac_valid correlationSecond,
      correlationCarrier_second_marginal_blind⟩⟩

/--
Level-B acceptance bundle for the correlation-only Grand Null fixture.

No physical conservation law or ontology is claimed here: only exact finite
stochastic validity, marginal blindness, and joint recoverability.
-/
theorem correlationCarrier_bundle :
    FinKernel.Valid correlationCarrier ∧
    FinKernel.Valid correlationBlindMarginal ∧
    FinKernel.compose (FinKernel.dirac correlationFirst) correlationCarrier =
      correlationBlindMarginal ∧
    FinKernel.compose (FinKernel.dirac correlationSecond) correlationCarrier =
      correlationBlindMarginal ∧
    FinKernel.compose (FinKernel.dirac correlationParity) correlationCarrier =
      FinKernel.identity 2 ∧
    FinKernel.HasValidStochasticRecovery correlationCarrier ∧
    FinKernel.StochasticEquivalent correlationCarrier (FinKernel.identity 2) := by
  exact ⟨correlationCarrier_valid,
    correlationBlindMarginal_valid,
    correlationCarrier_first_marginal_blind,
    correlationCarrier_second_marginal_blind,
    correlationCarrier_parity_recovers,
    correlationCarrier_hasValidStochasticRecovery,
    correlationCarrier_stochasticEquivalent_identity2⟩

end RelayTheory
