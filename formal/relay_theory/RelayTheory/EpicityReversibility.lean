import RelayTheory.MonoidalEpicity

namespace RelayTheory

namespace FinKernel

/--
Existence of an arbitrary exact recovery kernel.  No stochastic-validity
condition is imposed on the recovery map.
-/
def HasExactRecovery {a q : Nat} (obs : FinKernel a q) : Prop :=
  ∃ recovery : FinKernel q a,
    compose recovery obs = identity a

/--
Existence of a stochastic-valid recovery kernel.  This is deliberately stronger
than exact algebraic recoverability.
-/
def HasValidStochasticRecovery {a q : Nat} (obs : FinKernel a q) : Prop :=
  ∃ recovery : FinKernel q a,
    Valid recovery ∧ compose recovery obs = identity a

end FinKernel

/-- Exact algebraic inverse candidate for the noisy epic binary observation. -/
def finNoisyEpic2Inverse : FinKernel 2 2 :=
  fun x y => if x = y then (3 : Rat) / 2 else -qHalf

/-- The explicit noisy inverse recovers the source when applied after the noisy observation. -/
theorem finNoisyEpic2Inverse_after_noisy :
    FinKernel.compose finNoisyEpic2Inverse finNoisyEpic2 =
      FinKernel.identity 2 := by
  funext x z
  rcases finTwo_zero_or_one x with hx | hx
  · subst x
    rcases finTwo_zero_or_one z with hz | hz
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]
  · subst x
    rcases finTwo_zero_or_one z with hz | hz
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]

/-- The same explicit kernel is also an exact inverse in the other orientation. -/
theorem finNoisyEpic2_after_inverse :
    FinKernel.compose finNoisyEpic2 finNoisyEpic2Inverse =
      FinKernel.identity 2 := by
  funext x z
  rcases finTwo_zero_or_one x with hx | hx
  · subst x
    rcases finTwo_zero_or_one z with hz | hz
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]
  · subst x
    rcases finTwo_zero_or_one z with hz | hz
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]
    · subst z
      grind [FinKernel.compose, sumFin, finNoisyEpic2Inverse,
        finNoisyEpic2, FinKernel.identity, qHalf, qThreeQuarter, qQuarter]

/-- A concrete inverse off-diagonal coefficient is strictly negative. -/
theorem finNoisyEpic2Inverse_offDiagonal_neg :
    finNoisyEpic2Inverse (0 : Fin 2) (1 : Fin 2) < 0 := by
  have hhalf := qHalf_pos
  simp [finNoisyEpic2Inverse]
  grind

/-- Algebraically, every row of the explicit inverse still sums to one. -/
theorem finNoisyEpic2Inverse_rows_normalized :
    ∀ x : Fin 2, FinKernel.rowSum finNoisyEpic2Inverse x = 1 := by
  intro x
  rcases finTwo_zero_or_one x with hx | hx
  · subst x
    grind [FinKernel.rowSum, sumFin, finNoisyEpic2Inverse, qHalf]
  · subst x
    grind [FinKernel.rowSum, sumFin, finNoisyEpic2Inverse, qHalf]

/-- The exact inverse is not a stochastic-valid kernel because it has negative mass. -/
theorem finNoisyEpic2Inverse_not_valid :
    ¬ FinKernel.Valid finNoisyEpic2Inverse := by
  intro hvalid
  have hnonneg := hvalid.1 (0 : Fin 2) (1 : Fin 2)
  have hneg := finNoisyEpic2Inverse_offDiagonal_neg
  exact (not_lt_of_ge hnonneg) hneg

/-- The noisy epic observation has an exact algebraic recovery kernel. -/
theorem finNoisyEpic2_hasExactRecovery :
    FinKernel.HasExactRecovery finNoisyEpic2 := by
  exact ⟨finNoisyEpic2Inverse, finNoisyEpic2Inverse_after_noisy⟩

/--
No stochastic-valid recovery exists.  Epicity makes any alleged recovery equal
to the unique explicit exact inverse, whose negative coordinate violates
stochastic validity.
-/
theorem finNoisyEpic2_not_hasValidStochasticRecovery :
    ¬ FinKernel.HasValidStochasticRecovery finNoisyEpic2 := by
  rintro ⟨recovery, hvalid, hrecover⟩
  have hsame :
      FinKernel.compose recovery finNoisyEpic2 =
        FinKernel.compose finNoisyEpic2Inverse finNoisyEpic2 := by
    rw [hrecover, finNoisyEpic2Inverse_after_noisy]
  have hrecovery : recovery = finNoisyEpic2Inverse :=
    finNoisyEpic2_observationEpic recovery finNoisyEpic2Inverse hsame
  rw [hrecovery] at hvalid
  exact finNoisyEpic2Inverse_not_valid hvalid

/-- Binary flip is an involution on the deterministic two-point interface. -/
theorem finFlip2_involutive (x : Fin 2) :
    finFlip2 (finFlip2 x) = x := by
  rcases finTwo_zero_or_one x with hx | hx
  · subst x
    simp [finFlip2]
  · subst x
    simp [finFlip2]

/-- The deterministic binary flip Dirac kernel is its own exact inverse. -/
theorem finFlip2_dirac_self_inverse :
    FinKernel.compose (FinKernel.dirac finFlip2) (FinKernel.dirac finFlip2) =
      FinKernel.identity 2 := by
  rw [finKernel_dirac_compose]
  funext x y
  rw [finFlip2_involutive x]
  simp [FinKernel.dirac, FinKernel.identity, eq_comm]

/-- The deterministic binary flip observation is epic. -/
theorem finFlip2_dirac_observationEpic :
    FinKernel.ObservationEpic (FinKernel.dirac finFlip2) := by
  apply (finKernel_dirac_observationEpic_iff_surjective finFlip2).2
  intro y
  exact ⟨finFlip2 y, finFlip2_involutive y⟩

/-- Deterministic bijection control: binary flip has a valid stochastic recovery. -/
theorem finFlip2_dirac_hasValidStochasticRecovery :
    FinKernel.HasValidStochasticRecovery (FinKernel.dirac finFlip2) := by
  exact ⟨FinKernel.dirac finFlip2,
    finKernel_dirac_valid finFlip2,
    finFlip2_dirac_self_inverse⟩

/--
Acceptance bundle separating exact identifiability from stochastic/Markov-valid
recoverability while retaining a deterministic reversible control.
-/
theorem finKernel_epicity_reversibility_bundle :
    FinKernel.Valid finNoisyEpic2 ∧
    (¬ FinKernel.DeterministicKernel finNoisyEpic2) ∧
    FinKernel.ObservationEpic finNoisyEpic2 ∧
    FinKernel.HasExactRecovery finNoisyEpic2 ∧
    (¬ FinKernel.HasValidStochasticRecovery finNoisyEpic2) ∧
    FinKernel.Valid (FinKernel.dirac finFlip2) ∧
    FinKernel.ObservationEpic (FinKernel.dirac finFlip2) ∧
    FinKernel.HasValidStochasticRecovery (FinKernel.dirac finFlip2) := by
  exact ⟨finNoisyEpic2_valid,
    finNoisyEpic2_not_deterministic,
    finNoisyEpic2_observationEpic,
    finNoisyEpic2_hasExactRecovery,
    finNoisyEpic2_not_hasValidStochasticRecovery,
    finKernel_dirac_valid finFlip2,
    finFlip2_dirac_observationEpic,
    finFlip2_dirac_hasValidStochasticRecovery⟩

end RelayTheory
