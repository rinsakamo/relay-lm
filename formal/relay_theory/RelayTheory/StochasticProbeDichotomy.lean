import RelayTheory.ProbeDoctrine

namespace RelayTheory

namespace FinKernel

/-- An observation is row-constant when its response is independent of input. -/
def RowConstant {p q : Nat} (obs : FinKernel p q) : Prop :=
  ∀ a b z, obs a z = obs b z

/-- Every admitted observation in the doctrine is row-constant. -/
def DoctrineRowConstant (D : ProbeDoctrine) : Prop :=
  ∀ p (obs : Observation p), D p obs → RowConstant obs.2

end FinKernel

/-- Deterministic precomposition evaluates an arbitrary kernel at the selected state. -/
theorem finKernel_compose_after_dirac_eval
    {a b c : Nat} (k : FinKernel b c) (f : Fin a → Fin b)
    (x : Fin a) (z : Fin c) :
    FinKernel.compose k (FinKernel.dirac f) x z = k (f x) z := by
  unfold FinKernel.compose FinKernel.dirac
  calc
    sumFin b (fun y => (if y = f x then 1 else 0) * k y z) =
      sumFin b (fun y => if y = f x then k y z else 0) := by
        apply sumFin_congr
        intro y
        by_cases hy : y = f x <;> simp [hy]
    _ = k (f x) z := sumFin_single (f x) (fun y => k y z)

/--
For a normalized source row, pulling an arbitrary observation back through a
selector gives an exact affine function of the selected source coordinate.
-/
theorem finKernel_selector_affine
    {m n p q : Nat}
    (f : FinKernel m n) (hf : FinKernel.Valid f)
    (obs : FinKernel p q)
    (target : Fin n) (hit miss : Fin p)
    (x : Fin m) (z : Fin q) :
    FinKernel.compose
        (FinKernel.compose obs
          (FinKernel.dirac (finSelectorAt target hit miss)))
        f x z =
      obs miss z + f x target * (obs hit z - obs miss z) := by
  unfold FinKernel.compose
  calc
    sumFin n (fun y =>
        f x y *
          FinKernel.compose obs
            (FinKernel.dirac (finSelectorAt target hit miss)) y z) =
      sumFin n (fun y =>
        f x y * obs (finSelectorAt target hit miss y) z) := by
          apply sumFin_congr
          intro y
          rw [finKernel_compose_after_dirac_eval]
    _ = sumFin n (fun y =>
        f x y * obs miss z +
          if y = target then
            f x y * (obs hit z - obs miss z)
          else 0) := by
          apply sumFin_congr
          intro y
          by_cases hy : y = target
          · subst y
            simp [finSelectorAt]
            grind
          · simp [finSelectorAt, hy, Rat.add_zero]
    _ = sumFin n (fun y => f x y * obs miss z) +
        sumFin n (fun y =>
          if y = target then
            f x y * (obs hit z - obs miss z)
          else 0) := by
          rw [sumFin_add]
    _ = sumFin n (fun y => f x y) * obs miss z +
        f x target * (obs hit z - obs miss z) := by
          rw [sumFin_mul_right]
          rw [sumFin_single target
            (fun y => f x y * (obs hit z - obs miss z))]
    _ = obs miss z + f x target * (obs hit z - obs miss z) := by
          have hrow := hf.2 x
          change sumFin n (fun y => f x y) = 1 at hrow
          rw [hrow]
          grind

/--
Any admitted stochastic observation with two rows differing at one output
coordinate becomes an exact separator on stochastic-valid kernels once the
probe doctrine is closed under deterministic pullback.
-/
theorem finKernel_probeDoctrine_nonconstant_stochastic_forces_eq_of_valid
    {m n p q : Nat}
    (D : FinKernel.ProbeDoctrine)
    (hclose : FinKernel.DeterministicPullbackClosed D)
    (obs : FinKernel p q)
    (hit miss : Fin p) (z : Fin q)
    (hne : obs hit z ≠ obs miss z)
    (hadmit : D p ⟨q, obs⟩)
    {f g : FinKernel m n}
    (hf : FinKernel.Valid f) (hg : FinKernel.Valid g)
    (hfg : FinKernel.ProbeEq (D n) f g) :
    f = g := by
  funext x target
  have hpull :
      D n ⟨q,
        FinKernel.compose obs
          (FinKernel.dirac (finSelectorAt target hit miss))⟩ :=
    hclose (finSelectorAt target hit miss) ⟨q, obs⟩ hadmit
  have hobs := hfg
    ⟨q,
      FinKernel.compose obs
        (FinKernel.dirac (finSelectorAt target hit miss))⟩
    hpull
  have hv := hobs x z
  have hfa := finKernel_selector_affine
    f hf obs target hit miss x z
  have hga := finKernel_selector_affine
    g hg obs target hit miss x z
  rw [hfa, hga] at hv
  grind

/--
A single row-constant observation cannot distinguish any compatible pair of
stochastic-valid kernels.
-/
theorem finKernel_rowConstant_observation_blind_of_valid
    {m n q : Nat}
    (obs : FinKernel n q)
    (hconst : FinKernel.RowConstant obs)
    {f g : FinKernel m n}
    (hf : FinKernel.Valid f) (hg : FinKernel.Valid g) :
    FinKernel.BehaviorEq
      (FinKernel.compose obs f)
      (FinKernel.compose obs g) := by
  intro x z
  cases n with
  | zero =>
      exact False.elim ((no_valid_kernel_to_empty x f) hf)
  | succ n =>
      let ref : Fin (Nat.succ n) := 0
      have hfrow := hf.2 x
      have hgrow := hg.2 x
      change sumFin (Nat.succ n) (fun y => f x y) = 1 at hfrow
      change sumFin (Nat.succ n) (fun y => g x y) = 1 at hgrow
      unfold FinKernel.compose
      calc
        sumFin (Nat.succ n) (fun y => f x y * obs y z) =
            sumFin (Nat.succ n) (fun y => f x y * obs ref z) := by
              apply sumFin_congr
              intro y
              rw [hconst y ref z]
        _ = sumFin (Nat.succ n) (fun y => f x y) * obs ref z := by
              rw [sumFin_mul_right]
        _ = obs ref z := by rw [hfrow]; grind
        _ = sumFin (Nat.succ n) (fun y => g x y) * obs ref z := by
              rw [hgrow]; grind
        _ = sumFin (Nat.succ n) (fun y => g x y * obs ref z) := by
              rw [sumFin_mul_right]
        _ = sumFin (Nat.succ n) (fun y => g x y * obs y z) := by
              apply sumFin_congr
              intro y
              rw [hconst y ref z]

/--
If every admitted observation is row-constant, the whole doctrine is blind on
compatible stochastic-valid kernels.
-/
theorem finKernel_rowConstant_doctrine_blind_of_valid
    {m n : Nat}
    (D : FinKernel.ProbeDoctrine)
    (hconst : FinKernel.DoctrineRowConstant D)
    {f g : FinKernel m n}
    (hf : FinKernel.Valid f) (hg : FinKernel.Valid g) :
    FinKernel.ProbeEq (D n) f g := by
  intro obs hobs
  exact finKernel_rowConstant_observation_blind_of_valid
    obs.2 (hconst n obs hobs) hf hg

/--
Constructive two-case interface: row-constant doctrines are blind on valid
kernels, while any explicit admitted row-nonconstant observation witness forces
exact equality on valid kernels under deterministic pullback closure.
-/
theorem finKernel_valid_probe_dichotomy_parts
    (D : FinKernel.ProbeDoctrine)
    (hclose : FinKernel.DeterministicPullbackClosed D) :
    (FinKernel.DoctrineRowConstant D →
      ∀ {m n : Nat} {f g : FinKernel m n},
        FinKernel.Valid f → FinKernel.Valid g →
        FinKernel.ProbeEq (D n) f g) ∧
    (∀ {m n p q : Nat}
        (obs : FinKernel p q) (hit miss : Fin p) (z : Fin q),
        obs hit z ≠ obs miss z →
        D p ⟨q, obs⟩ →
        ∀ {f g : FinKernel m n},
          FinKernel.Valid f → FinKernel.Valid g →
          FinKernel.ProbeEq (D n) f g → f = g) := by
  constructor
  · intro hrows m n f g hf hg
    exact finKernel_rowConstant_doctrine_blind_of_valid D hrows hf hg
  · intro m n p q obs hit miss z hne hadmit f g hf hg hfg
    exact finKernel_probeDoctrine_nonconstant_stochastic_forces_eq_of_valid
      D hclose obs hit miss z hne hadmit hf hg hfg

end RelayTheory
