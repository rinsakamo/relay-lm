import RelayTheory.SequentialRecoveryReflection

namespace RelayTheory

namespace FinKernel

/--
Exact left-cancellation interface for an observation channel.  This is the
upstream dual of `ObservationEpic`: two exact kernels into the observation
source are equal whenever postcomposition by the observation makes them equal.
-/
def ObservationMonic {a q : Nat} (obs : FinKernel a q) : Prop :=
  ∀ {t : Nat} (h₁ h₂ : FinKernel t a),
    compose obs h₁ = compose obs h₂ → h₁ = h₂

end FinKernel

/-- Any explicit exact recovery witness gives universal left cancellation. -/
theorem finKernel_hasExactRecovery_to_observationMonic
    {a q : Nat} {obs : FinKernel a q}
    (hrecover : FinKernel.HasExactRecovery obs) :
    FinKernel.ObservationMonic obs := by
  rcases hrecover with ⟨recovery, hrec⟩
  intro t h₁ h₂ hEq
  calc
    h₁ = FinKernel.compose (FinKernel.identity a) h₁ :=
      (finKernel_compose_identity_after h₁).symm
    _ = FinKernel.compose (FinKernel.compose recovery obs) h₁ := by
      rw [hrec]
    _ = FinKernel.compose recovery (FinKernel.compose obs h₁) :=
      (finKernel_compose_associative h₁ obs recovery).symm
    _ = FinKernel.compose recovery (FinKernel.compose obs h₂) := by
      rw [hEq]
    _ = FinKernel.compose (FinKernel.compose recovery obs) h₂ :=
      finKernel_compose_associative h₂ obs recovery
    _ = FinKernel.compose (FinKernel.identity a) h₂ := by
      rw [hrec]
    _ = h₂ := finKernel_compose_identity_after h₂

/-- Identity has the universal left-cancellation property. -/
theorem finKernel_identity_observationMonic (n : Nat) :
    FinKernel.ObservationMonic (FinKernel.identity n) := by
  intro t h₁ h₂ hEq
  rw [finKernel_compose_identity_after,
    finKernel_compose_identity_after] at hEq
  exact hEq

/-- Observation monicity is closed under exact sequential composition. -/
theorem finKernel_observationMonic_compose
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hA : FinKernel.ObservationMonic obsA)
    (hB : FinKernel.ObservationMonic obsB) :
    FinKernel.ObservationMonic (FinKernel.compose obsB obsA) := by
  intro t h₁ h₂ hEq
  have hEqB :
      FinKernel.compose obsB (FinKernel.compose obsA h₁) =
        FinKernel.compose obsB (FinKernel.compose obsA h₂) := by
    calc
      FinKernel.compose obsB (FinKernel.compose obsA h₁) =
          FinKernel.compose (FinKernel.compose obsB obsA) h₁ :=
        finKernel_compose_associative h₁ obsA obsB
      _ = FinKernel.compose (FinKernel.compose obsB obsA) h₂ := hEq
      _ = FinKernel.compose obsB (FinKernel.compose obsA h₂) :=
        (finKernel_compose_associative h₂ obsA obsB).symm
  have hEqA : FinKernel.compose obsA h₁ = FinKernel.compose obsA h₂ :=
    hB (FinKernel.compose obsA h₁) (FinKernel.compose obsA h₂) hEqB
  exact hA h₁ h₂ hEqA

/-- Monicity of a composite always reflects to its earlier factor. -/
theorem finKernel_observationMonic_compose_reflect_earlier
    {a q r : Nat}
    {obsA : FinKernel a q} {obsB : FinKernel q r}
    (hcomp : FinKernel.ObservationMonic (FinKernel.compose obsB obsA)) :
    FinKernel.ObservationMonic obsA := by
  intro t h₁ h₂ hEq
  apply hcomp h₁ h₂
  calc
    FinKernel.compose (FinKernel.compose obsB obsA) h₁ =
        FinKernel.compose obsB (FinKernel.compose obsA h₁) :=
      (finKernel_compose_associative h₁ obsA obsB).symm
    _ = FinKernel.compose obsB (FinKernel.compose obsA h₂) := by
      rw [hEq]
    _ = FinKernel.compose (FinKernel.compose obsB obsA) h₂ :=
      finKernel_compose_associative h₂ obsA obsB

/--
Monicity of a deterministic Dirac observation forces ordinary injectivity.  A
collision is exposed by two singleton-source Dirac kernels selecting the two
colliding source points.
-/
theorem finKernel_dirac_injective_of_observationMonic
    {a q : Nat} (f : Fin a → Fin q)
    (hmonic : FinKernel.ObservationMonic (FinKernel.dirac f)) :
    Function.Injective f := by
  intro x y hxy
  let sourceX : Fin 1 → Fin a := fun _ => x
  let sourceY : Fin 1 → Fin a := fun _ => y
  have hcomp :
      FinKernel.compose (FinKernel.dirac f) (FinKernel.dirac sourceX) =
        FinKernel.compose (FinKernel.dirac f) (FinKernel.dirac sourceY) := by
    rw [finKernel_dirac_compose, finKernel_dirac_compose]
    apply finKernel_dirac_congr
    intro u
    simp [sourceX, sourceY, hxy]
  have hsources :
      FinKernel.dirac sourceX = FinKernel.dirac sourceY :=
    hmonic (FinKernel.dirac sourceX) (FinKernel.dirac sourceY) hcomp
  by_cases heq : x = y
  · exact heq
  · have hv := congrFun (congrFun hsources (0 : Fin 1)) x
    simp [FinKernel.dirac, sourceX, sourceY, heq] at hv

/-- For deterministic observations, universal left cancellation is injectivity. -/
theorem finKernel_dirac_observationMonic_iff_injective
    {a q : Nat} (f : Fin a → Fin q) :
    FinKernel.ObservationMonic (FinKernel.dirac f) ↔
      Function.Injective f := by
  constructor
  · exact finKernel_dirac_injective_of_observationMonic f
  · intro hinj
    exact finKernel_hasExactRecovery_to_observationMonic
      (finKernel_dirac_hasExactRecovery_of_injective f hinj)

/--
On deterministic Dirac kernels, the cancellation interface and explicit exact
recovery coincide because both are exactly injectivity.
-/
theorem finKernel_dirac_observationMonic_iff_hasExactRecovery
    {a q : Nat} (f : Fin a → Fin q) :
    FinKernel.ObservationMonic (FinKernel.dirac f) ↔
      FinKernel.HasExactRecovery (FinKernel.dirac f) := by
  constructor
  · intro hmonic
    exact (finKernel_dirac_hasExactRecovery_iff_injective f).2
      ((finKernel_dirac_observationMonic_iff_injective f).1 hmonic)
  · exact finKernel_hasExactRecovery_to_observationMonic

/-- The valid fair stochastic kernel has a valid stochastic recovery: discard. -/
theorem finFairKernel_hasValidStochasticRecovery :
    FinKernel.HasValidStochasticRecovery finFairKernel := by
  refine ⟨FinKernel.discard 2, finKernel_discard_valid 2, ?_⟩
  calc
    FinKernel.compose (FinKernel.discard 2) finFairKernel =
        FinKernel.discard 1 := finKernel_discard_causal finFairKernel_valid
    _ = FinKernel.identity 1 := finKernel_discard_one_eq_identity

/-- The genuinely stochastic fair kernel is monic despite being non-epic. -/
theorem finFairKernel_observationMonic :
    FinKernel.ObservationMonic finFairKernel := by
  apply finKernel_hasExactRecovery_to_observationMonic
  exact finKernel_hasValidStochasticRecovery_to_exactRecovery
    finFairKernel_hasValidStochasticRecovery

/-- The underlying binary discard function is not injective. -/
theorem finDiscardFn_two_not_injective :
    ¬ Function.Injective (@finDiscardFn 2) := by
  intro hinj
  have h01 : (0 : Fin 2) = (1 : Fin 2) := hinj (by rfl)
  exact (by decide : (0 : Fin 2) ≠ (1 : Fin 2)) h01

/-- Binary discard is not monic. -/
theorem finKernel_discard_two_not_observationMonic :
    ¬ FinKernel.ObservationMonic (FinKernel.discard 2) := by
  intro hmonic
  change FinKernel.ObservationMonic
    (FinKernel.dirac (@finDiscardFn 2)) at hmonic
  exact finDiscardFn_two_not_injective
    ((finKernel_dirac_observationMonic_iff_injective (@finDiscardFn 2)).1 hmonic)

/--
Acceptance package for the exact recovery cancellation interface.  The global
converse `ObservationMonic -> HasExactRecovery` for arbitrary rational kernels
is intentionally not asserted here.
-/
theorem finKernel_recovery_cancellation_interface_bundle :
    (∀ {a q : Nat} {obs : FinKernel a q},
      FinKernel.HasExactRecovery obs → FinKernel.ObservationMonic obs) ∧
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.ObservationMonic obsA →
      FinKernel.ObservationMonic obsB →
        FinKernel.ObservationMonic (FinKernel.compose obsB obsA)) ∧
    (∀ {a q r : Nat}
      {obsA : FinKernel a q} {obsB : FinKernel q r},
      FinKernel.ObservationMonic (FinKernel.compose obsB obsA) →
        FinKernel.ObservationMonic obsA) ∧
    (∀ {a q : Nat} (f : Fin a → Fin q),
      FinKernel.ObservationMonic (FinKernel.dirac f) ↔
        Function.Injective f) ∧
    FinKernel.HasValidStochasticRecovery finFairKernel ∧
    FinKernel.ObservationMonic finFairKernel ∧
    (¬ FinKernel.ObservationEpic finFairKernel) ∧
    (¬ FinKernel.ObservationMonic (FinKernel.discard 2)) := by
  exact ⟨finKernel_hasExactRecovery_to_observationMonic,
    finKernel_observationMonic_compose,
    finKernel_observationMonic_compose_reflect_earlier,
    finKernel_dirac_observationMonic_iff_injective,
    finFairKernel_hasValidStochasticRecovery,
    finFairKernel_observationMonic,
    finFairKernel_not_observationEpic,
    finKernel_discard_two_not_observationMonic⟩

end RelayTheory
