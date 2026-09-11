import RelayTheory.StochasticRecoverabilityPreorder
import RelayTheory.ObserverChainRealizers

namespace RelayTheory

/-- Reuse the finite 1 <-> 2 swap as a reversible four-state WORLD step. -/
def finWorldSwap4 : Fin 4 → Fin 4 := diamondObserverB

/-- The WORLD swap is an involution. -/
theorem finWorldSwap4_involutive (x : Fin 4) :
    finWorldSwap4 (finWorldSwap4 x) = x := by
  by_cases h1 : x = (1 : Fin 4)
  · subst x
    simp [finWorldSwap4, diamondObserverB]
  · by_cases h2 : x = (2 : Fin 4)
    · subst x
      simp [finWorldSwap4, diamondObserverB]
    · simp [finWorldSwap4, diamondObserverB, h1, h2]

/-- Fixed coarse observer with partition {0,1}|{2,3}. -/
def finWorldCoarseA (x : Fin 4) : Fin 2 :=
  if x = (0 : Fin 4) then (0 : Fin 2)
  else if x = (1 : Fin 4) then (0 : Fin 2)
  else (1 : Fin 2)

/-- The same fixed observer after one WORLD swap: partition {0,2}|{1,3}. -/
def finWorldCoarseB (x : Fin 4) : Fin 2 :=
  finWorldCoarseA (finWorldSwap4 x)

/-- Exact reversible deterministic WORLD step. -/
def finWorldStep4 : FinKernel 4 4 :=
  FinKernel.dirac finWorldSwap4

/-- Initial source-to-observation channel. -/
def finWorldObs0 : FinKernel 4 2 :=
  FinKernel.dirac finWorldCoarseA

/-- One WORLD step followed by the same fixed observer. -/
def finWorldObs1 : FinKernel 4 2 :=
  FinKernel.compose finWorldObs0 finWorldStep4

/-- Two WORLD steps followed by the same fixed observer. -/
def finWorldObs2 : FinKernel 4 2 :=
  FinKernel.compose finWorldObs1 finWorldStep4

/-- The deterministic WORLD step is stochastic-valid. -/
theorem finWorldStep4_valid : FinKernel.Valid finWorldStep4 :=
  finKernel_dirac_valid finWorldSwap4

/-- Two WORLD steps cancel exactly. -/
theorem finWorldStep4_self_inverse :
    FinKernel.compose finWorldStep4 finWorldStep4 = FinKernel.identity 4 := by
  unfold finWorldStep4
  rw [finKernel_dirac_compose]
  funext x y
  unfold FinKernel.dirac FinKernel.identity
  rw [finWorldSwap4_involutive x]
  simp [eq_comm]

/-- One-step observation is exactly the crossed partition. -/
theorem finWorldObs1_eq_crossed :
    finWorldObs1 = FinKernel.dirac finWorldCoarseB := by
  simpa [finWorldObs1, finWorldObs0, finWorldStep4, finWorldCoarseB] using
    (finKernel_dirac_compose finWorldSwap4 finWorldCoarseA)

/-- Finite recurrence returns the observer channel exactly after two WORLD steps. -/
theorem finWorldObs2_eq_obs0 : finWorldObs2 = finWorldObs0 := by
  unfold finWorldObs2 finWorldObs1
  calc
    FinKernel.compose (FinKernel.compose finWorldObs0 finWorldStep4) finWorldStep4 =
        FinKernel.compose finWorldObs0
          (FinKernel.compose finWorldStep4 finWorldStep4) :=
      (finKernel_compose_associative finWorldStep4 finWorldStep4 finWorldObs0).symm
    _ = FinKernel.compose finWorldObs0 (FinKernel.identity 4) := by
      rw [finWorldStep4_self_inverse]
    _ = finWorldObs0 := finKernel_compose_identity_before finWorldObs0

/-- Evaluate arbitrary output post-processing after a deterministic source channel. -/
theorem finKernel_compose_after_dirac_eval
    {a b c : Nat} (post : FinKernel b c) (f : Fin a → Fin b)
    (x : Fin a) (z : Fin c) :
    FinKernel.compose post (FinKernel.dirac f) x z = post (f x) z := by
  unfold FinKernel.compose FinKernel.dirac
  calc
    sumFin b (fun y => (if y = f x then 1 else 0) * post y z) =
        sumFin b (fun y => if y = f x then post y z else 0) := by
      apply sumFin_congr
      intro y
      by_cases h : y = f x <;> simp [h]
    _ = post (f x) z := sumFin_single (f x) (fun y => post y z)

/--
The crossed deterministic partitions cannot be obtained from each other by any
single output post-processing. Validity of the alleged post-processing is not
even needed for the contradiction.
-/
theorem finWorldObs0_not_degradesTo_obs1 :
    ¬ FinKernel.StochasticDegradesTo finWorldObs0 finWorldObs1 := by
  rintro ⟨post, _, hEq⟩
  rw [finWorldObs1_eq_crossed] at hEq
  change FinKernel.compose post (FinKernel.dirac finWorldCoarseA) =
    FinKernel.dirac finWorldCoarseB at hEq
  have h0 := congrFun (congrFun hEq (0 : Fin 4)) (0 : Fin 2)
  have h1 := congrFun (congrFun hEq (1 : Fin 4)) (0 : Fin 2)
  rw [finKernel_compose_after_dirac_eval] at h0 h1
  simp [FinKernel.dirac, finWorldCoarseA, finWorldCoarseB,
    finWorldSwap4, diamondObserverB] at h0 h1

/-- Nor can the crossed partition be post-processed back into the initial one. -/
theorem finWorldObs1_not_degradesTo_obs0 :
    ¬ FinKernel.StochasticDegradesTo finWorldObs1 finWorldObs0 := by
  rintro ⟨post, _, hEq⟩
  rw [finWorldObs1_eq_crossed] at hEq
  change FinKernel.compose post (FinKernel.dirac finWorldCoarseB) =
    FinKernel.dirac finWorldCoarseA at hEq
  have h0 := congrFun (congrFun hEq (0 : Fin 4)) (0 : Fin 2)
  have h2 := congrFun (congrFun hEq (2 : Fin 4)) (0 : Fin 2)
  rw [finKernel_compose_after_dirac_eval] at h0 h2
  simp [FinKernel.dirac, finWorldCoarseA, finWorldCoarseB,
    finWorldSwap4, diamondObserverB] at h0 h2

/-- Successive observations along this reversible WORLD orbit are incomparable. -/
theorem finWorld_successive_observations_incomparable :
    (¬ FinKernel.StochasticDegradesTo finWorldObs0 finWorldObs1) ∧
    (¬ FinKernel.StochasticDegradesTo finWorldObs1 finWorldObs0) := by
  exact ⟨finWorldObs0_not_degradesTo_obs1,
    finWorldObs1_not_degradesTo_obs0⟩

/-- Hence neither orientation supplies a strict stochastic information arrow. -/
theorem finWorld_successive_observations_no_strict_arrow :
    (¬ FinKernel.StrictStochasticLoss finWorldObs0 finWorldObs1) ∧
    (¬ FinKernel.StrictStochasticLoss finWorldObs1 finWorldObs0) := by
  constructor
  · intro h
    exact finWorldObs0_not_degradesTo_obs1 h.1
  · intro h
    exact finWorldObs1_not_degradesTo_obs0 h.1

/-- Explicit stochastic divisibility is sufficient for one preorder step. -/
theorem finKernel_divisible_step_degrades
    {n qa qb : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb}
    {post : FinKernel qa qb}
    (hpost : FinKernel.Valid post)
    (hfactor : FinKernel.compose post a = b) :
    FinKernel.StochasticDegradesTo a b := by
  exact ⟨post, hpost, hfactor⟩

/-- Two explicit divisible steps compose to a monotone preorder comparison. -/
theorem finKernel_two_divisible_steps_degrade
    {n qa qb qc : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb} {c : FinKernel n qc}
    {postAB : FinKernel qa qb} {postBC : FinKernel qb qc}
    (hABValid : FinKernel.Valid postAB)
    (hBCValid : FinKernel.Valid postBC)
    (hAB : FinKernel.compose postAB a = b)
    (hBC : FinKernel.compose postBC b = c) :
    FinKernel.StochasticDegradesTo a c := by
  exact finKernel_stochasticDegradesTo_trans
    (finKernel_divisible_step_degrades hABValid hAB)
    (finKernel_divisible_step_degrades hBCValid hBC)

/--
For an involutive WORLD step, any alleged one-step stochastic degradation of a
fixed observer automatically supplies the reverse degradation as well.
-/
theorem finKernel_involutive_world_forward_implies_reverse
    {n q : Nat}
    (obs : FinKernel n q) (u : FinKernel n n)
    (hu : FinKernel.compose u u = FinKernel.identity n)
    (hforward : FinKernel.StochasticDegradesTo obs (FinKernel.compose obs u)) :
    FinKernel.StochasticDegradesTo (FinKernel.compose obs u) obs := by
  rcases hforward with ⟨post, hpostValid, hpost⟩
  refine ⟨post, hpostValid, ?_⟩
  calc
    FinKernel.compose post (FinKernel.compose obs u) =
        FinKernel.compose (FinKernel.compose post obs) u :=
      finKernel_compose_associative u obs post
    _ = FinKernel.compose (FinKernel.compose obs u) u := by
      rw [hpost]
    _ = FinKernel.compose obs (FinKernel.compose u u) :=
      (finKernel_compose_associative u u obs).symm
    _ = FinKernel.compose obs (FinKernel.identity n) := by
      rw [hu]
    _ = obs := finKernel_compose_identity_before obs

/-- A fixed observer over an involutive WORLD step cannot have strict one-step loss. -/
theorem finKernel_involutive_world_no_strict_forward
    {n q : Nat}
    (obs : FinKernel n q) (u : FinKernel n n)
    (hu : FinKernel.compose u u = FinKernel.identity n) :
    ¬ FinKernel.StrictStochasticLoss obs (FinKernel.compose obs u) := by
  intro hstrict
  exact hstrict.2
    (finKernel_involutive_world_forward_implies_reverse obs u hu hstrict.1)

/-- The concrete recurrent WORLD fixture therefore admits no strict first-step arrow. -/
theorem finWorld_recurrence_no_strict_forward :
    ¬ FinKernel.StrictStochasticLoss finWorldObs0 finWorldObs1 := by
  change ¬ FinKernel.StrictStochasticLoss finWorldObs0
    (FinKernel.compose finWorldObs0 finWorldStep4)
  exact finKernel_involutive_world_no_strict_forward
    finWorldObs0 finWorldStep4 finWorldStep4_self_inverse

/-- Divisibility alone need not make a step strict: reversible relabeling is the control. -/
theorem finKernel_divisibility_not_strict_control :
    FinKernel.StochasticDegradesTo
        (FinKernel.identity 2) (FinKernel.dirac finFlip2) ∧
      ¬ FinKernel.StrictStochasticLoss
        (FinKernel.identity 2) (FinKernel.dirac finFlip2) := by
  exact ⟨finIdentity2_degradesTo_flip,
    finIdentity2_not_strictLoss_flip⟩

/--
Acceptance bundle: reversible WORLD dynamics do not force information
monotonicity; explicit divisibility is sufficient only for the non-strict
preorder, and recurrence blocks a strict arrow in the involutive control.
-/
theorem finKernel_process_monotonicity_bundle :
    FinKernel.Valid finWorldStep4 ∧
    FinKernel.compose finWorldStep4 finWorldStep4 = FinKernel.identity 4 ∧
    finWorldObs2 = finWorldObs0 ∧
    (¬ FinKernel.StochasticDegradesTo finWorldObs0 finWorldObs1) ∧
    (¬ FinKernel.StochasticDegradesTo finWorldObs1 finWorldObs0) ∧
    (¬ FinKernel.StrictStochasticLoss finWorldObs0 finWorldObs1) ∧
    (∀ {n qa qb : Nat}
      {a : FinKernel n qa} {b : FinKernel n qb} {post : FinKernel qa qb},
      FinKernel.Valid post →
      FinKernel.compose post a = b →
      FinKernel.StochasticDegradesTo a b) := by
  exact ⟨finWorldStep4_valid,
    finWorldStep4_self_inverse,
    finWorldObs2_eq_obs0,
    finWorldObs0_not_degradesTo_obs1,
    finWorldObs1_not_degradesTo_obs0,
    finWorld_recurrence_no_strict_forward,
    finKernel_divisible_step_degrades⟩

end RelayTheory
