import RelayTheory.SequentialEpicityReflection

namespace RelayTheory

/-- Every stochastic-valid recovery is, in particular, an exact recovery. -/
theorem finKernel_hasValidStochasticRecovery_to_exactRecovery
    {a q : Nat} {obs : FinKernel a q}
    (hvalid : FinKernel.HasValidStochasticRecovery obs) :
    FinKernel.HasExactRecovery obs := by
  rcases hvalid with ⟨recovery, _, hrec⟩
  exact ⟨recovery, hrec⟩

/--
If the later factor has an exact recovery, epicity of the composite reflects to
its earlier factor.  No stochastic-validity premise is required.
-/
theorem finKernel_observationEpic_compose_reflect_earlier_of_exactRecovery
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hcomp : FinKernel.ObservationEpic (FinKernel.compose obsB obsA))
    (hrecover : FinKernel.HasExactRecovery obsB) :
    FinKernel.ObservationEpic obsA := by
  rcases hrecover with ⟨recovery, hrec⟩
  intro t h₁ h₂ hEq
  have hcollapse :
      FinKernel.compose recovery (FinKernel.compose obsB obsA) = obsA := by
    calc
      FinKernel.compose recovery (FinKernel.compose obsB obsA) =
          FinKernel.compose (FinKernel.compose recovery obsB) obsA :=
        finKernel_compose_associative obsA obsB recovery
      _ = FinKernel.compose (FinKernel.identity q) obsA := by
        rw [hrec]
      _ = obsA := finKernel_compose_identity_after obsA
  have hlift :
      FinKernel.compose (FinKernel.compose h₁ recovery)
          (FinKernel.compose obsB obsA) =
        FinKernel.compose (FinKernel.compose h₂ recovery)
          (FinKernel.compose obsB obsA) := by
    calc
      FinKernel.compose (FinKernel.compose h₁ recovery)
          (FinKernel.compose obsB obsA) =
          FinKernel.compose h₁
            (FinKernel.compose recovery (FinKernel.compose obsB obsA)) :=
        (finKernel_compose_associative
          (FinKernel.compose obsB obsA) recovery h₁).symm
      _ = FinKernel.compose h₁ obsA := by rw [hcollapse]
      _ = FinKernel.compose h₂ obsA := hEq
      _ = FinKernel.compose h₂
          (FinKernel.compose recovery (FinKernel.compose obsB obsA)) := by
        rw [hcollapse]
      _ = FinKernel.compose (FinKernel.compose h₂ recovery)
          (FinKernel.compose obsB obsA) :=
        finKernel_compose_associative
          (FinKernel.compose obsB obsA) recovery h₂
  have hliftEq :
      FinKernel.compose h₁ recovery = FinKernel.compose h₂ recovery :=
    hcomp (FinKernel.compose h₁ recovery)
      (FinKernel.compose h₂ recovery) hlift
  calc
    h₁ = FinKernel.compose h₁ (FinKernel.identity q) :=
      (finKernel_compose_identity_before h₁).symm
    _ = FinKernel.compose h₁ (FinKernel.compose recovery obsB) := by
      rw [hrec]
    _ = FinKernel.compose (FinKernel.compose h₁ recovery) obsB :=
      finKernel_compose_associative obsB recovery h₁
    _ = FinKernel.compose (FinKernel.compose h₂ recovery) obsB := by
      rw [hliftEq]
    _ = FinKernel.compose h₂ (FinKernel.compose recovery obsB) :=
      (finKernel_compose_associative obsB recovery h₂).symm
    _ = FinKernel.compose h₂ (FinKernel.identity q) := by
      rw [hrec]
    _ = h₂ := finKernel_compose_identity_before h₂

/--
An epic observation with a one-sided exact recovery automatically upgrades that
same recovery to a two-sided exact inverse.
-/
theorem finKernel_observationEpic_exactRecovery_twoSided
    {a q : Nat} {obs : FinKernel a q}
    (hepic : FinKernel.ObservationEpic obs)
    (hrecover : FinKernel.HasExactRecovery obs) :
    ∃ recovery : FinKernel q a,
      FinKernel.compose recovery obs = FinKernel.identity a ∧
      FinKernel.compose obs recovery = FinKernel.identity q := by
  rcases hrecover with ⟨recovery, hleft⟩
  refine ⟨recovery, hleft, ?_⟩
  apply hepic (FinKernel.compose obs recovery) (FinKernel.identity q)
  calc
    FinKernel.compose (FinKernel.compose obs recovery) obs =
        FinKernel.compose obs (FinKernel.compose recovery obs) :=
      (finKernel_compose_associative obs recovery obs).symm
    _ = FinKernel.compose obs (FinKernel.identity a) := by
      rw [hleft]
    _ = obs := finKernel_compose_identity_before obs
    _ = FinKernel.compose (FinKernel.identity q) obs :=
      (finKernel_compose_identity_after obs).symm

/--
If an epic composite has an exactly recoverable later factor, that later factor
is itself epic and its recovery is therefore two-sided.
-/
theorem finKernel_epicComposite_exactRecovery_later_twoSided
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hcomp : FinKernel.ObservationEpic (FinKernel.compose obsB obsA))
    (hrecover : FinKernel.HasExactRecovery obsB) :
    ∃ recovery : FinKernel r q,
      FinKernel.compose recovery obsB = FinKernel.identity q ∧
      FinKernel.compose obsB recovery = FinKernel.identity r := by
  exact finKernel_observationEpic_exactRecovery_twoSided
    (finKernel_observationEpic_compose_reflect_later hcomp)
    hrecover

/--
The noisy epic channel reflects earlier epicity despite having no
stochastic-valid recovery: exact recoverability is sufficient at this boundary.
-/
theorem finNoisyEpic2_later_reflects_earlier
    {a : Nat} {obsA : FinKernel a 2}
    (hcomp :
      FinKernel.ObservationEpic
        (FinKernel.compose finNoisyEpic2 obsA)) :
    FinKernel.ObservationEpic obsA :=
  finKernel_observationEpic_compose_reflect_earlier_of_exactRecovery
    hcomp finNoisyEpic2_hasExactRecovery

/-- Explicit non-Markov recovery/reflection package for the noisy fixture. -/
theorem finNoisyEpic2_nonMarkov_recovery_reflection_bundle :
    (¬ FinKernel.HasValidStochasticRecovery finNoisyEpic2) ∧
    (∀ {a : Nat} {obsA : FinKernel a 2},
      FinKernel.ObservationEpic (FinKernel.compose finNoisyEpic2 obsA) →
        FinKernel.ObservationEpic obsA) := by
  exact ⟨finNoisyEpic2_not_hasValidStochasticRecovery,
    fun hcomp => finNoisyEpic2_later_reflects_earlier hcomp⟩

/--
The deterministic binary flip gives the physically admissible positive control:
its valid stochastic recovery is enough to obtain exact earlier reflection.
-/
theorem finFlip2_dirac_later_reflects_earlier
    {a : Nat} {obsA : FinKernel a 2}
    (hcomp :
      FinKernel.ObservationEpic
        (FinKernel.compose (FinKernel.dirac finFlip2) obsA)) :
    FinKernel.ObservationEpic obsA := by
  apply finKernel_observationEpic_compose_reflect_earlier_of_exactRecovery hcomp
  exact finKernel_hasValidStochasticRecovery_to_exactRecovery
    finFlip2_dirac_hasValidStochasticRecovery

/--
The epic binary discard from #2501 cannot admit any exact recovery.  Otherwise
its epic composite with the non-epic fair prefix would force that prefix epic.
-/
theorem finKernel_discard_two_not_hasExactRecovery :
    ¬ FinKernel.HasExactRecovery (FinKernel.discard 2) := by
  intro hrecover
  have hfair : FinKernel.ObservationEpic finFairKernel :=
    finKernel_observationEpic_compose_reflect_earlier_of_exactRecovery
      finFairKernel_then_discard_observationEpic hrecover
  exact finFairKernel_not_observationEpic hfair

/--
Acceptance package separating epicity, exact recovery, two-sided invertibility,
and stochastic-valid recoverability.
-/
theorem finKernel_split_later_reflection_bundle :
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.ObservationEpic (FinKernel.compose obsB obsA) →
      FinKernel.HasExactRecovery obsB →
        FinKernel.ObservationEpic obsA) ∧
    (∀ {a q : Nat} {obs : FinKernel a q},
      FinKernel.ObservationEpic obs →
      FinKernel.HasExactRecovery obs →
      ∃ recovery : FinKernel q a,
        FinKernel.compose recovery obs = FinKernel.identity a ∧
        FinKernel.compose obs recovery = FinKernel.identity q) ∧
    (¬ FinKernel.HasValidStochasticRecovery finNoisyEpic2) ∧
    (¬ FinKernel.HasExactRecovery (FinKernel.discard 2)) := by
  exact ⟨finKernel_observationEpic_compose_reflect_earlier_of_exactRecovery,
    finKernel_observationEpic_exactRecovery_twoSided,
    finNoisyEpic2_not_hasValidStochasticRecovery,
    finKernel_discard_two_not_hasExactRecovery⟩

end RelayTheory
