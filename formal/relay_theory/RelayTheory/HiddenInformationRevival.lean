import RelayTheory.ProcessMonotonicity
import RelayTheory.GenericMarkovLaws

namespace RelayTheory

/-- Embed one visible source bit into a two-bit WORLD with hidden bit fixed to zero. -/
def finHiddenEmbed0 (x : Fin 2) : Fin (2 * 2) :=
  finPairTransport.toFun (x, (0 : Fin 2))

/-- Fixed visible observer: read the first coordinate of the two-bit WORLD. -/
def finVisibleRead2 (w : Fin (2 * 2)) : Fin 2 :=
  (finPairTransport.invFun w).1

/-- Hidden-coordinate observer used only to certify the carrier at the intermediate cut. -/
def finHiddenRead2 (w : Fin (2 * 2)) : Fin 2 :=
  (finPairTransport.invFun w).2

/-- Ordinary two-bit WORLD swap, reusing the existing structural symmetry. -/
def finHiddenWorldSwap : FinKernel (2 * 2) (2 * 2) :=
  FinKernel.symmetry 2 2

/-- Source embedding into the enlarged WORLD. -/
def finHiddenWorld0 : FinKernel 2 (2 * 2) :=
  FinKernel.dirac finHiddenEmbed0

/-- One application of the reversible WORLD swap. -/
def finHiddenWorld1 : FinKernel 2 (2 * 2) :=
  FinKernel.compose finHiddenWorldSwap finHiddenWorld0

/-- A second application of exactly the same WORLD swap; no fresh input is inserted. -/
def finHiddenWorld2 : FinKernel 2 (2 * 2) :=
  FinKernel.compose finHiddenWorldSwap finHiddenWorld1

/-- Fixed visible observation channel on the enlarged WORLD. -/
def finVisibleObserver2 : FinKernel (2 * 2) 2 :=
  FinKernel.dirac finVisibleRead2

/-- Hidden-coordinate readout used to certify where the inaccessible distinction resides. -/
def finHiddenObserver2 : FinKernel (2 * 2) 2 :=
  FinKernel.dirac finHiddenRead2

/-- Visible source channel before the WORLD swap. -/
def finHiddenObs0 : FinKernel 2 2 :=
  FinKernel.compose finVisibleObserver2 finHiddenWorld0

/-- Visible source channel after one WORLD swap. -/
def finHiddenObs1 : FinKernel 2 2 :=
  FinKernel.compose finVisibleObserver2 finHiddenWorld1

/-- Visible source channel after two WORLD swaps. -/
def finHiddenObs2 : FinKernel 2 2 :=
  FinKernel.compose finVisibleObserver2 finHiddenWorld2

/-- Hidden-coordinate source channel at the intermediate WORLD cut. -/
def finHiddenCarrier1 : FinKernel 2 2 :=
  FinKernel.compose finHiddenObserver2 finHiddenWorld1

/-- Deterministic channel that forgets the source bit and always emits zero. -/
def finConstantZero2 : FinKernel 2 2 :=
  FinKernel.dirac (fun _ : Fin 2 => (0 : Fin 2))

/-- Function-level state after the first swap, exposed for the lineage check. -/
def finHiddenState1 (x : Fin 2) : Fin (2 * 2) :=
  finSwapTransport.toFun (finHiddenEmbed0 x)

/-- The source embedding round-trips through the visible projection. -/
theorem finVisibleRead2_embed0 (x : Fin 2) :
    finVisibleRead2 (finHiddenEmbed0 x) = x := by
  simp [finVisibleRead2, finHiddenEmbed0, finPair_transport_roundtrip]

/-- Initially the hidden coordinate is the declared zero bit. -/
theorem finHiddenRead2_embed0 (x : Fin 2) :
    finHiddenRead2 (finHiddenEmbed0 x) = (0 : Fin 2) := by
  simp [finHiddenRead2, finHiddenEmbed0, finPair_transport_roundtrip]

/-- The structural swap sends `(x,0)` exactly to `(0,x)`. -/
theorem finHidden_swap_embed0 (x : Fin 2) :
    finSwapTransport.toFun (finHiddenEmbed0 x) =
      finPairTransport.toFun ((0 : Fin 2), x) := by
  simp [finSwapTransport, finHiddenEmbed0, finPair_transport_roundtrip]

/-- For the two-bit WORLD, the existing swap transport is an exact involution. -/
theorem finHidden_swap_involutive (w : Fin (2 * 2)) :
    finSwapTransport.toFun (finSwapTransport.toFun w) = w := by
  simp [finSwapTransport, finPair_transport_roundtrip,
    finPair_flatten_components]

/-- The reused WORLD symmetry is stochastic-valid. -/
theorem finHiddenWorldSwap_valid : FinKernel.Valid finHiddenWorldSwap := by
  exact finKernel_symmetry_valid 2 2

/-- The reused WORLD symmetry is exactly self-inverse. -/
theorem finHiddenWorldSwap_self_inverse :
    FinKernel.compose finHiddenWorldSwap finHiddenWorldSwap =
      FinKernel.identity (2 * 2) := by
  unfold finHiddenWorldSwap FinKernel.symmetry
  rw [finKernel_dirac_compose, finKernel_identity_eq_dirac_id]
  apply finKernel_dirac_congr
  intro w
  exact finHidden_swap_involutive w

/-- One WORLD step is exactly the deterministic embedding `x |-> (0,x)`. -/
theorem finHiddenWorld1_eq_hiddenEmbedding :
    finHiddenWorld1 =
      FinKernel.dirac (fun x : Fin 2 =>
        finPairTransport.toFun ((0 : Fin 2), x)) := by
  unfold finHiddenWorld1 finHiddenWorldSwap finHiddenWorld0 FinKernel.symmetry
  rw [finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  exact finHidden_swap_embed0 x

/-- Applying the same reversible WORLD law twice returns the full WORLD channel. -/
theorem finHiddenWorld2_eq_world0 : finHiddenWorld2 = finHiddenWorld0 := by
  unfold finHiddenWorld2 finHiddenWorld1
  calc
    FinKernel.compose finHiddenWorldSwap
        (FinKernel.compose finHiddenWorldSwap finHiddenWorld0) =
      FinKernel.compose
        (FinKernel.compose finHiddenWorldSwap finHiddenWorldSwap)
        finHiddenWorld0 :=
      finKernel_compose_associative finHiddenWorld0
        finHiddenWorldSwap finHiddenWorldSwap
    _ = FinKernel.compose (FinKernel.identity (2 * 2)) finHiddenWorld0 := by
      rw [finHiddenWorldSwap_self_inverse]
    _ = finHiddenWorld0 := finKernel_compose_identity_after finHiddenWorld0

/-- The visible channel initially exposes the source bit exactly. -/
theorem finHiddenObs0_eq_identity :
    finHiddenObs0 = FinKernel.identity 2 := by
  unfold finHiddenObs0 finVisibleObserver2 finHiddenWorld0
  rw [finKernel_dirac_compose, finKernel_identity_eq_dirac_id]
  apply finKernel_dirac_congr
  intro x
  exact finVisibleRead2_embed0 x

/-- After one swap the fixed visible observer sees only constant zero. -/
theorem finHiddenObs1_eq_constantZero :
    finHiddenObs1 = finConstantZero2 := by
  unfold finHiddenObs1 finVisibleObserver2 finConstantZero2
  rw [finHiddenWorld1_eq_hiddenEmbedding, finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  simp [finVisibleRead2, finPair_transport_roundtrip]

/-- At the same intermediate cut, the hidden coordinate exposes the source bit exactly. -/
theorem finHiddenCarrier1_eq_identity :
    finHiddenCarrier1 = FinKernel.identity 2 := by
  unfold finHiddenCarrier1 finHiddenObserver2
  rw [finHiddenWorld1_eq_hiddenEmbedding, finKernel_dirac_compose,
    finKernel_identity_eq_dirac_id]
  apply finKernel_dirac_congr
  intro x
  simp [finHiddenRead2, finPair_transport_roundtrip]

/-- After the second swap the visible observer channel returns exactly to its initial value. -/
theorem finHiddenObs2_eq_obs0 : finHiddenObs2 = finHiddenObs0 := by
  unfold finHiddenObs2 finHiddenObs0
  rw [finHiddenWorld2_eq_world0]

/-- Equivalently, the second visible channel is again exact identity on the source bit. -/
theorem finHiddenObs2_eq_identity :
    finHiddenObs2 = FinKernel.identity 2 := by
  rw [finHiddenObs2_eq_obs0, finHiddenObs0_eq_identity]

/-- The constant-zero output channel is stochastic-valid. -/
theorem finConstantZero2_valid : FinKernel.Valid finConstantZero2 := by
  exact finKernel_dirac_valid (fun _ : Fin 2 => (0 : Fin 2))

/-- Exact visible information can be stochastically degraded into the constant intermediate view. -/
theorem finHiddenObs0_degradesTo_obs1 :
    FinKernel.StochasticDegradesTo finHiddenObs0 finHiddenObs1 := by
  rw [finHiddenObs0_eq_identity, finHiddenObs1_eq_constantZero]
  refine ⟨finConstantZero2, finConstantZero2_valid, ?_⟩
  exact finKernel_compose_identity_before finConstantZero2

/-- No stochastic post-processing can reconstruct identity from the constant intermediate view. -/
theorem finHiddenObs1_not_degradesTo_obs0 :
    ¬ FinKernel.StochasticDegradesTo finHiddenObs1 finHiddenObs0 := by
  rw [finHiddenObs1_eq_constantZero, finHiddenObs0_eq_identity]
  rintro ⟨post, _, hEq⟩
  unfold finConstantZero2 at hEq
  have h0 := congrFun (congrFun hEq (0 : Fin 2)) (0 : Fin 2)
  have h1 := congrFun (congrFun hEq (1 : Fin 2)) (0 : Fin 2)
  rw [finKernel_compose_after_dirac_eval] at h0 h1
  simp [FinKernel.identity] at h0 h1
  grind

/-- The first visible step is therefore a strict stochastic information loss. -/
theorem finHiddenObs0_strictLoss_obs1 :
    FinKernel.StrictStochasticLoss finHiddenObs0 finHiddenObs1 := by
  exact ⟨finHiddenObs0_degradesTo_obs1,
    finHiddenObs1_not_degradesTo_obs0⟩

/-- Exact return makes the second visible channel stochastically equivalent to the first. -/
theorem finHiddenObs2_equivalent_obs0 :
    FinKernel.StochasticEquivalent finHiddenObs2 finHiddenObs0 := by
  rw [finHiddenObs2_eq_obs0]
  exact finKernel_stochasticEquivalent_refl finHiddenObs0

/-- Every source has the same visible intermediate value. -/
theorem finHiddenState1_visible_zero (x : Fin 2) :
    finVisibleRead2 (finHiddenState1 x) = (0 : Fin 2) := by
  rw [finHidden_swap_embed0]
  simp [finHiddenState1, finVisibleRead2, finPair_transport_roundtrip]

/-- The hidden intermediate coordinate is exactly the original source bit. -/
theorem finHiddenState1_hidden_source (x : Fin 2) :
    finHiddenRead2 (finHiddenState1 x) = x := by
  rw [finHidden_swap_embed0]
  simp [finHiddenState1, finHiddenRead2, finPair_transport_roundtrip]

/-- Applying the same WORLD swap once more returns the source bit to the visible coordinate. -/
theorem finHiddenState1_return_visible (x : Fin 2) :
    finVisibleRead2 (finSwapTransport.toFun (finHiddenState1 x)) = x := by
  unfold finHiddenState1
  rw [finHidden_swap_involutive]
  exact finVisibleRead2_embed0 x

/--
Pointwise lineage certificate: sources 0 and 1 are visibly identical at the
intermediate cut, remain distinct in the hidden coordinate, and become visibly
distinct after the same second SWAP with no fresh source input.
-/
theorem finHidden_intermediate_carrier_controls_return :
    finVisibleRead2 (finHiddenState1 (0 : Fin 2)) =
        finVisibleRead2 (finHiddenState1 (1 : Fin 2)) ∧
    finHiddenRead2 (finHiddenState1 (0 : Fin 2)) ≠
        finHiddenRead2 (finHiddenState1 (1 : Fin 2)) ∧
    finVisibleRead2
        (finSwapTransport.toFun (finHiddenState1 (0 : Fin 2))) ≠
      finVisibleRead2
        (finSwapTransport.toFun (finHiddenState1 (1 : Fin 2))) := by
  rw [finHiddenState1_visible_zero, finHiddenState1_visible_zero,
    finHiddenState1_hidden_source, finHiddenState1_hidden_source,
    finHiddenState1_return_visible, finHiddenState1_return_visible]
  exact ⟨rfl, by decide, by decide⟩

/--
Acceptance bundle for the bounded hidden-coordinate revival transaction.
The visible observer strictly loses the source distinction, the hidden
coordinate retains it exactly, and the same reversible WORLD law returns it.
-/
theorem finKernel_hidden_information_revival_bundle :
    FinKernel.Valid finHiddenWorldSwap ∧
    FinKernel.compose finHiddenWorldSwap finHiddenWorldSwap =
      FinKernel.identity (2 * 2) ∧
    finHiddenObs0 = FinKernel.identity 2 ∧
    finHiddenObs1 = finConstantZero2 ∧
    finHiddenCarrier1 = FinKernel.identity 2 ∧
    finHiddenObs2 = finHiddenObs0 ∧
    FinKernel.StrictStochasticLoss finHiddenObs0 finHiddenObs1 ∧
    FinKernel.StochasticEquivalent finHiddenObs2 finHiddenObs0 ∧
    (finVisibleRead2 (finHiddenState1 (0 : Fin 2)) =
      finVisibleRead2 (finHiddenState1 (1 : Fin 2)) ∧
     finHiddenRead2 (finHiddenState1 (0 : Fin 2)) ≠
      finHiddenRead2 (finHiddenState1 (1 : Fin 2)) ∧
     finVisibleRead2
        (finSwapTransport.toFun (finHiddenState1 (0 : Fin 2))) ≠
      finVisibleRead2
        (finSwapTransport.toFun (finHiddenState1 (1 : Fin 2)))) := by
  exact ⟨finHiddenWorldSwap_valid,
    finHiddenWorldSwap_self_inverse,
    finHiddenObs0_eq_identity,
    finHiddenObs1_eq_constantZero,
    finHiddenCarrier1_eq_identity,
    finHiddenObs2_eq_obs0,
    finHiddenObs0_strictLoss_obs1,
    finHiddenObs2_equivalent_obs0,
    finHidden_intermediate_carrier_controls_return⟩

end RelayTheory
