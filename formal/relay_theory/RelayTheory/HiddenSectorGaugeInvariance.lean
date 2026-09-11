import RelayTheory.HiddenCarrierReturn

namespace RelayTheory

namespace HiddenSectorGaugeInvariance

/--
A minimal state-coordinate relabeling with an explicit inverse.  This is only a
finite/state transport interface; no geometric or spacetime interpretation is
built into it.
-/
structure StateRelabeling (α : Type) where
  forward : α → α
  backward : α → α
  forward_backward : ∀ x, forward (backward x) = x
  backward_forward : ∀ x, backward (forward x) = x

/-- Transport a source preparation through a state relabeling. -/
def transportedEmbed {σ α : Type}
    (e : StateRelabeling α) (embed : σ → α) : σ → α :=
  fun x => e.forward (embed x)

/-- Conjugate one WORLD step by the same state relabeling. -/
def transportedStep {α : Type}
    (e : StateRelabeling α) (step : α → α) : α → α :=
  fun x => e.forward (step (e.backward x))

/-- Transport an observer contravariantly so it denotes the same access. -/
def transportedObserver {α β : Type}
    (e : StateRelabeling α) (obs : α → β) : α → β :=
  fun x => obs (e.backward x)

/-- Transport an intervention by the same conjugation as WORLD dynamics. -/
def transportedIntervention {α : Type}
    (e : StateRelabeling α) (r : α → α) : α → α :=
  fun x => e.forward (r (e.backward x))

/-- Coherent state-coordinate relabeling preserves the prepared observation. -/
theorem transported_initial_observation
    {σ α β : Type}
    (e : StateRelabeling α) (embed : σ → α) (obs : α → β)
    (x : σ) :
    transportedObserver e obs (transportedEmbed e embed x) =
      obs (embed x) := by
  simp only [transportedObserver, transportedEmbed, e.backward_forward]

/-- Coherent state-coordinate relabeling preserves one-step observations. -/
theorem transported_one_step_observation
    {σ α β : Type}
    (e : StateRelabeling α) (embed : σ → α)
    (step : α → α) (obs : α → β) (x : σ) :
    transportedObserver e obs
        (transportedStep e step (transportedEmbed e embed x)) =
      obs (step (embed x)) := by
  simp only [transportedObserver, transportedStep, transportedEmbed,
    e.backward_forward]

/-- The same transport preserves two-step observations exactly. -/
theorem transported_two_step_observation
    {σ α β : Type}
    (e : StateRelabeling α) (embed : σ → α)
    (step : α → α) (obs : α → β) (x : σ) :
    transportedObserver e obs
        (transportedStep e step
          (transportedStep e step (transportedEmbed e embed x))) =
      obs (step (step (embed x))) := by
  simp only [transportedObserver, transportedStep, transportedEmbed,
    e.backward_forward]

/--
Intervention-level observer predictions are preserved when preparation,
dynamics, intervention and observer are all transported coherently.
-/
theorem transported_intervention_observation
    {σ α β : Type}
    (e : StateRelabeling α) (embed : σ → α)
    (step r : α → α) (obs : α → β) (x : σ) :
    transportedObserver e obs
        (transportedStep e step
          (transportedIntervention e r
            (transportedStep e step (transportedEmbed e embed x)))) =
      obs (step (r (step (embed x)))) := by
  simp only [transportedObserver, transportedStep, transportedIntervention,
    transportedEmbed, e.backward_forward]

/--
Use the existing involutive coordinate exchange as a concrete nontrivial state
renaming of the #2559 two-bit WORLD.
-/
def swapRelabeling : StateRelabeling HiddenCarrierReturn.World where
  forward := HiddenCarrierReturn.step
  backward := HiddenCarrierReturn.step
  forward_backward := HiddenCarrierReturn.step_involutive
  backward_forward := HiddenCarrierReturn.step_involutive

/-- The reduced one-step observation is unchanged by coherent relabeling. -/
theorem swapRelabeling_preserves_one_step_visible (x : Fin 2) :
    transportedObserver swapRelabeling HiddenCarrierReturn.visible
        (transportedStep swapRelabeling HiddenCarrierReturn.step
          (transportedEmbed swapRelabeling HiddenCarrierReturn.embed x)) =
      0 := by
  rw [transported_one_step_observation]
  exact HiddenCarrierReturn.visible_after_one x

/-- The exact two-step return is unchanged by coherent relabeling. -/
theorem swapRelabeling_preserves_two_step_visible (x : Fin 2) :
    transportedObserver swapRelabeling HiddenCarrierReturn.visible
        (transportedStep swapRelabeling HiddenCarrierReturn.step
          (transportedStep swapRelabeling HiddenCarrierReturn.step
            (transportedEmbed swapRelabeling HiddenCarrierReturn.embed x))) =
      x := by
  rw [transported_two_step_observation]
  exact HiddenCarrierReturn.visible_after_two x

/-- The hidden-reset intervention comparison is likewise coordinate-invariant. -/
theorem swapRelabeling_preserves_reset_path_visible (x : Fin 2) :
    transportedObserver swapRelabeling HiddenCarrierReturn.visible
        (transportedStep swapRelabeling HiddenCarrierReturn.step
          (transportedIntervention swapRelabeling HiddenCarrierReturn.resetHidden
            (transportedStep swapRelabeling HiddenCarrierReturn.step
              (transportedEmbed swapRelabeling HiddenCarrierReturn.embed x)))) =
      0 := by
  rw [transported_intervention_observation]
  exact HiddenCarrierReturn.resetHidden_blocks_return x

/-- The intervention-certified carrier-lineage inequality survives relabeling. -/
theorem swapRelabeling_preserves_carrier_lineage :
    transportedObserver swapRelabeling HiddenCarrierReturn.visible
        (transportedStep swapRelabeling HiddenCarrierReturn.step
          (transportedStep swapRelabeling HiddenCarrierReturn.step
            (transportedEmbed swapRelabeling HiddenCarrierReturn.embed
              (1 : Fin 2)))) ≠
      transportedObserver swapRelabeling HiddenCarrierReturn.visible
        (transportedStep swapRelabeling HiddenCarrierReturn.step
          (transportedIntervention swapRelabeling HiddenCarrierReturn.resetHidden
            (transportedStep swapRelabeling HiddenCarrierReturn.step
              (transportedEmbed swapRelabeling HiddenCarrierReturn.embed
                (1 : Fin 2))))) := by
  rw [transported_two_step_observation,
    transported_intervention_observation]
  exact HiddenCarrierReturn.hidden_carrier_controls_future_visible

/-- Enlarged access exposes the complete two-coordinate WORLD state. -/
def enlargedObserver (w : HiddenCarrierReturn.World) :
    HiddenCarrierReturn.World := w

@[simp] theorem enlargedObserver_after_one (x : Fin 2) :
    enlargedObserver
        (HiddenCarrierReturn.step (HiddenCarrierReturn.embed x)) =
      (0, x) := rfl

/--
The enlarged stage-1 observation retains the source distinction exactly, even
though the reduced visible observer has collapsed it.
-/
theorem enlargedObserver_after_one_injective :
    Function.Injective
      (fun x : Fin 2 =>
        enlargedObserver
          (HiddenCarrierReturn.step (HiddenCarrierReturn.embed x))) := by
  intro x y hxy
  have hhidden := congrArg Prod.snd hxy
  simpa [enlargedObserver, HiddenCarrierReturn.step,
    HiddenCarrierReturn.embed] using hhidden

/-- The reduced stage-1 observer identifies the two binary sources. -/
theorem reducedObserver_after_one_collapses :
    HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step (HiddenCarrierReturn.embed (0 : Fin 2))) =
      HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step (HiddenCarrierReturn.embed (1 : Fin 2))) := by
  rfl

/-- The enlarged observer distinguishes those same two source preparations. -/
theorem enlargedObserver_after_one_distinguishes :
    enlargedObserver
        (HiddenCarrierReturn.step (HiddenCarrierReturn.embed (0 : Fin 2))) ≠
      enlargedObserver
        (HiddenCarrierReturn.step (HiddenCarrierReturn.embed (1 : Fin 2))) := by
  intro h
  have h01 : (0 : Fin 2) = (1 : Fin 2) :=
    enlargedObserver_after_one_injective h
  exact (by decide : (0 : Fin 2) ≠ (1 : Fin 2)) h01

/-- Reading the second coordinate recovers the prepared source at stage 1. -/
def recoverSourceFromEnlarged
    (w : HiddenCarrierReturn.World) : Fin 2 :=
  HiddenCarrierReturn.hidden w

@[simp] theorem recoverSourceFromEnlarged_after_one (x : Fin 2) :
    recoverSourceFromEnlarged
        (enlargedObserver
          (HiddenCarrierReturn.step (HiddenCarrierReturn.embed x))) = x :=
  rfl

/--
Acceptance bundle: coherent state relabeling preserves the leave/return
predictions, while enlarged observer access exposes the carrier that the
reduced visible observer hides.  The intervention and reduced-collapse
certificates remain separate named theorems above.
-/
theorem hiddenSectorGaugeInvariance_bundle :
    (∀ x : Fin 2,
      transportedObserver swapRelabeling HiddenCarrierReturn.visible
          (transportedStep swapRelabeling HiddenCarrierReturn.step
            (transportedEmbed swapRelabeling HiddenCarrierReturn.embed x)) = 0) ∧
    (∀ x : Fin 2,
      transportedObserver swapRelabeling HiddenCarrierReturn.visible
          (transportedStep swapRelabeling HiddenCarrierReturn.step
            (transportedStep swapRelabeling HiddenCarrierReturn.step
              (transportedEmbed swapRelabeling HiddenCarrierReturn.embed x))) = x) ∧
    Function.Injective
      (fun x : Fin 2 =>
        enlargedObserver
          (HiddenCarrierReturn.step (HiddenCarrierReturn.embed x))) ∧
    (∀ x : Fin 2,
      recoverSourceFromEnlarged
          (enlargedObserver
            (HiddenCarrierReturn.step (HiddenCarrierReturn.embed x))) = x) := by
  exact ⟨
    swapRelabeling_preserves_one_step_visible,
    swapRelabeling_preserves_two_step_visible,
    enlargedObserver_after_one_injective,
    recoverSourceFromEnlarged_after_one⟩

end HiddenSectorGaugeInvariance

end RelayTheory
