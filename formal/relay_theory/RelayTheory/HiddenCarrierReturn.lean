import RelayTheory.StochasticRecoverabilityPreorder

namespace RelayTheory

namespace HiddenCarrierReturn

/--
A minimal finite WORLD with one observer-visible coordinate and one hidden
coordinate.  No spacetime or extra-time interpretation is built into the type.
-/
abbrev World := Fin 2 × Fin 2

/-- Prepare a source value with the hidden coordinate initialized to zero. -/
def embed (x : Fin 2) : World := (x, 0)

/-- The declared observer sees only the first WORLD coordinate. -/
def visible (w : World) : Fin 2 := w.1

/-- The complementary coordinate is hidden from the declared observer. -/
def hidden (w : World) : Fin 2 := w.2

/-- Reversible WORLD dynamics: exchange visible and hidden coordinates. -/
def step (w : World) : World := (w.2, w.1)

/-- Intervention that changes only the hidden coordinate. -/
def resetHidden (w : World) : World := (w.1, 0)

@[simp] theorem visible_embed (x : Fin 2) :
    visible (embed x) = x := rfl

@[simp] theorem visible_after_one (x : Fin 2) :
    visible (step (embed x)) = 0 := rfl

@[simp] theorem hidden_after_one (x : Fin 2) :
    hidden (step (embed x)) = x := rfl

@[simp] theorem visible_after_two (x : Fin 2) :
    visible (step (step (embed x))) = x := rfl

@[simp] theorem step_involutive (w : World) :
    step (step w) = w := by
  rcases w with ⟨s, h⟩
  rfl

@[simp] theorem resetHidden_preserves_visible (w : World) :
    visible (resetHidden w) = visible w := rfl

@[simp] theorem resetHidden_blocks_return (x : Fin 2) :
    visible (step (resetHidden (step (embed x)))) = 0 := rfl

/--
At the nonzero prepared source, changing only the hidden intermediate state
changes the later visible outcome.  This is the finite causal-lineage witness.
-/
theorem hidden_carrier_controls_future_visible :
    visible (step (step (embed (1 : Fin 2)))) ≠
      visible (step (resetHidden (step (embed (1 : Fin 2))))) := by
  simp [embed, visible, step, resetHidden]

/-- Prepared source-to-visible function before WORLD evolution. -/
def preparedVisible0 (x : Fin 2) : Fin 2 := visible (embed x)

/-- Prepared source-to-visible function after one WORLD step. -/
def preparedVisible1 (x : Fin 2) : Fin 2 := visible (step (embed x))

/-- Prepared source-to-visible function after two WORLD steps. -/
def preparedVisible2 (x : Fin 2) : Fin 2 := visible (step (step (embed x)))

/-- Constant binary observation used to expose the one-step information loss. -/
def constZero2 (_ : Fin 2) : Fin 2 := 0

@[simp] theorem preparedVisible0_apply (x : Fin 2) :
    preparedVisible0 x = x := rfl

@[simp] theorem preparedVisible1_apply (x : Fin 2) :
    preparedVisible1 x = 0 := rfl

@[simp] theorem preparedVisible2_apply (x : Fin 2) :
    preparedVisible2 x = x := rfl

/-- Observer channel at the prepared initial cut. -/
def preparedObs0 : FinKernel 2 2 := FinKernel.dirac preparedVisible0

/-- Observer channel after one reversible WORLD step. -/
def preparedObs1 : FinKernel 2 2 := FinKernel.dirac preparedVisible1

/-- Observer channel after two reversible WORLD steps. -/
def preparedObs2 : FinKernel 2 2 := FinKernel.dirac preparedVisible2

/-- Initial prepared observation is exactly the binary identity channel. -/
theorem preparedObs0_eq_identity :
    preparedObs0 = FinKernel.identity 2 := by
  funext x y
  simp [preparedObs0, preparedVisible0, FinKernel.dirac,
    FinKernel.identity, eq_comm]

/-- The one-step prepared observation is exactly the constant-zero Dirac channel. -/
theorem preparedObs1_eq_constZero :
    preparedObs1 = FinKernel.dirac constZero2 := by
  rfl

/-- After two reversible WORLD steps the prepared observer channel returns exactly. -/
theorem preparedObs2_eq_obs0 : preparedObs2 = preparedObs0 := by
  rfl

/-- The one-step constant observation is a valid stochastic channel. -/
theorem preparedObs1_valid : FinKernel.Valid preparedObs1 := by
  exact finKernel_dirac_valid preparedVisible1

/-- The informative prepared observation can be garbled into the one-step constant one. -/
theorem preparedObs0_degradesTo_obs1 :
    FinKernel.StochasticDegradesTo preparedObs0 preparedObs1 := by
  refine ⟨preparedObs1, preparedObs1_valid, ?_⟩
  rw [preparedObs0_eq_identity]
  exact finKernel_compose_identity_before preparedObs1

/-- No output post-processing of the constant one-step channel can restore identity. -/
theorem preparedObs1_not_degradesTo_obs0 :
    ¬ FinKernel.StochasticDegradesTo preparedObs1 preparedObs0 := by
  rintro ⟨post, _, hEq⟩
  rw [preparedObs1_eq_constZero, preparedObs0_eq_identity] at hEq
  have h0 := congrFun (congrFun hEq (0 : Fin 2)) (0 : Fin 2)
  have h1 := congrFun (congrFun hEq (1 : Fin 2)) (0 : Fin 2)
  rw [finKernel_compose_after_dirac_eval] at h0 h1
  simp [constZero2, FinKernel.identity] at h0 h1
  grind

/-- Prepared observer information is strictly lost at the one-step cut. -/
theorem preparedObs0_strictLoss_obs1 :
    FinKernel.StrictStochasticLoss preparedObs0 preparedObs1 := by
  exact ⟨preparedObs0_degradesTo_obs1, preparedObs1_not_degradesTo_obs0⟩

/-- The returned two-step channel is stochastically equivalent to the initial one. -/
theorem preparedObs2_stochasticEquivalent_obs0 :
    FinKernel.StochasticEquivalent preparedObs2 preparedObs0 := by
  rw [preparedObs2_eq_obs0]
  exact finKernel_stochasticEquivalent_refl preparedObs0

/--
Acceptance bundle for the finite hidden-carrier return transaction.

The fixture establishes observer-relative strict information loss followed by
exact revival, with a hidden-only intervention proving future-visible causal
lineage.  Because the entire construction is already an ordinary product state
with one reversible sequential step, it does not establish hidden spacetime or
an additional timelike dimension.
-/
theorem hiddenCarrierReturn_bundle :
    (∀ x : Fin 2, visible (step (embed x)) = 0) ∧
    (∀ x : Fin 2, hidden (step (embed x)) = x) ∧
    (∀ x : Fin 2, visible (step (step (embed x))) = x) ∧
    (∀ w : World, step (step w) = w) ∧
    (∀ w : World, visible (resetHidden w) = visible w) ∧
    visible (step (step (embed (1 : Fin 2)))) ≠
      visible (step (resetHidden (step (embed (1 : Fin 2))))) ∧
    FinKernel.StrictStochasticLoss preparedObs0 preparedObs1 ∧
    preparedObs2 = preparedObs0 := by
  exact ⟨visible_after_one,
    hidden_after_one,
    visible_after_two,
    step_involutive,
    resetHidden_preserves_visible,
    hidden_carrier_controls_future_visible,
    preparedObs0_strictLoss_obs1,
    preparedObs2_eq_obs0⟩

end HiddenCarrierReturn

end RelayTheory
