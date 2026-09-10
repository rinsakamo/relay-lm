import RelayTheory.BehavioralQuotient

namespace RelayTheory

namespace FinKernel

/-- A typed downstream observation from `Fin n`, carrying its output cardinal. -/
abbrev Observation (n : Nat) := Sigma (fun q : Nat => FinKernel n q)

/-- An explicitly declared family of admissible downstream observations. -/
abbrev ProbeFamily (n : Nat) := Observation n → Prop

/--
Probe-relative equivalence: every observation admitted by `P` sees exactly the
same stochastic behavior after the two kernels.
-/
def ProbeEq {m n : Nat} (P : ProbeFamily n)
    (f g : FinKernel m n) : Prop :=
  ∀ obs : Observation n, P obs →
    BehaviorEq (compose obs.2 f) (compose obs.2 g)

/-- The family containing every exact downstream finite-kernel observation. -/
def allProbes (n : Nat) : ProbeFamily n := fun _ => True

/-- The deliberately vacuous family, useful only as an anti-vacuity extreme. -/
def noProbes (n : Nat) : ProbeFamily n := fun _ => False

/-- A family containing exactly one typed observation. -/
def singletonProbe {n : Nat} (obs : Observation n) : ProbeFamily n :=
  fun candidate => candidate = obs

/--
Contravariant closure needed to transport a probe-relative quotient through a
future map `k`: every `Q` probe pulled back through `k` must already belong to
`P`.
-/
def PullbackClosedAlong {n p : Nat}
    (P : ProbeFamily n) (k : FinKernel n p) (Q : ProbeFamily p) : Prop :=
  ∀ obs : Observation p, Q obs →
    P ⟨obs.1, compose obs.2 k⟩

/--
The product-probe family generated only by independent tensors of probes from
`P` and `Q`. This intentionally does not include arbitrary joint probes.
-/
def tensorGeneratedProbes {b d : Nat}
    (P : ProbeFamily b) (Q : ProbeFamily d) : ProbeFamily (b * d) :=
  fun obs =>
    ∃ (left : Observation b) (right : Observation d),
      P left ∧ Q right ∧
        obs = ⟨left.1 * right.1, tensor left.2 right.2⟩

end FinKernel

/-- Probe-relative equivalence is reflexive for every declared family. -/
theorem finKernel_probeEq_refl {m n : Nat}
    (P : FinKernel.ProbeFamily n) (f : FinKernel m n) :
    FinKernel.ProbeEq P f f := by
  intro obs hobs
  exact finKernel_behaviorEq_refl _

/-- Probe-relative equivalence is symmetric for every declared family. -/
theorem finKernel_probeEq_symm {m n : Nat}
    {P : FinKernel.ProbeFamily n} {f g : FinKernel m n}
    (h : FinKernel.ProbeEq P f g) :
    FinKernel.ProbeEq P g f := by
  intro obs hobs
  exact finKernel_behaviorEq_symm (h obs hobs)

/-- Probe-relative equivalence is transitive for every declared family. -/
theorem finKernel_probeEq_trans {m n : Nat}
    {P : FinKernel.ProbeFamily n} {f g h : FinKernel m n}
    (hfg : FinKernel.ProbeEq P f g)
    (hgh : FinKernel.ProbeEq P g h) :
    FinKernel.ProbeEq P f h := by
  intro obs hobs
  exact finKernel_behaviorEq_trans (hfg obs hobs) (hgh obs hobs)

/-- More admitted probes produce a finer equivalence relation. -/
theorem finKernel_probeEq_antitone {m n : Nat}
    {P Q : FinKernel.ProbeFamily n} {f g : FinKernel m n}
    (hPQ : ∀ obs, P obs → Q obs)
    (hQ : FinKernel.ProbeEq Q f g) :
    FinKernel.ProbeEq P f g := by
  intro obs hobs
  exact hQ obs (hPQ obs hobs)

/-- The empty probe family identifies every compatible pair vacuously. -/
theorem finKernel_noProbes_vacuous {m n : Nat} (f g : FinKernel m n) :
    FinKernel.ProbeEq (FinKernel.noProbes n) f g := by
  intro obs hobs
  exact False.elim hobs

/-- All-probe equivalence is exactly the all-downstream-context relation. -/
theorem finKernel_probeEq_all_iff_contextEq {m n : Nat}
    (f g : FinKernel m n) :
    FinKernel.ProbeEq (FinKernel.allProbes n) f g ↔
      FinKernel.ContextEq f g := by
  constructor
  · intro h q obs
    exact h ⟨q, obs⟩ trivial
  · intro h obs hobs
    exact h obs.1 obs.2

/-- By #2447, admitting all exact probes collapses back to literal equality. -/
theorem finKernel_probeEq_all_iff_eq {m n : Nat}
    (f g : FinKernel m n) :
    FinKernel.ProbeEq (FinKernel.allProbes n) f g ↔ f = g := by
  rw [finKernel_probeEq_all_iff_contextEq, finKernel_contextEq_iff_eq]

/-- A singleton family recovers the fixed-probe observational relation exactly. -/
theorem finKernel_probeEq_singleton_iff_observedEq {m n q : Nat}
    (obs : FinKernel n q) (f g : FinKernel m n) :
    FinKernel.ProbeEq (FinKernel.singletonProbe ⟨q, obs⟩) f g ↔
      FinKernel.ObservedEq obs f g := by
  constructor
  · intro h
    exact h ⟨q, obs⟩ rfl
  · intro h candidate hc
    cases hc
    exact h

/--
Source-side precomposition is automatically stable: no extra closure property
of the downstream probe family is required.
-/
theorem finKernel_probeEq_precompose {l m n : Nat}
    {P : FinKernel.ProbeFamily n} {f g : FinKernel m n}
    (hfg : FinKernel.ProbeEq P f g) (h : FinKernel l m) :
    FinKernel.ProbeEq P
      (FinKernel.compose f h) (FinKernel.compose g h) := by
  intro obs hobs
  have hbase := hfg obs hobs
  have heq : FinKernel.compose obs.2 f = FinKernel.compose obs.2 g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hbase
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose obs.2 (FinKernel.compose f h) =
        FinKernel.compose (FinKernel.compose obs.2 f) h :=
      finKernel_compose_associative h f obs.2
    _ = FinKernel.compose (FinKernel.compose obs.2 g) h := by rw [heq]
    _ = FinKernel.compose obs.2 (FinKernel.compose g h) :=
      (finKernel_compose_associative h g obs.2).symm

/--
Probe pullback closure is sufficient for stability under a future map.
This is the explicit context contract that arbitrary probe families lack.
-/
theorem finKernel_probeEq_postcompose_of_pullback {m n p : Nat}
    {P : FinKernel.ProbeFamily n} {Q : FinKernel.ProbeFamily p}
    {f g : FinKernel m n} (k : FinKernel n p)
    (hfg : FinKernel.ProbeEq P f g)
    (hclose : FinKernel.PullbackClosedAlong P k Q) :
    FinKernel.ProbeEq Q
      (FinKernel.compose k f) (FinKernel.compose k g) := by
  intro obs hobs
  have hbase := hfg
    ⟨obs.1, FinKernel.compose obs.2 k⟩
    (hclose obs hobs)
  have heq :
      FinKernel.compose (FinKernel.compose obs.2 k) f =
        FinKernel.compose (FinKernel.compose obs.2 k) g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hbase
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose obs.2 (FinKernel.compose k f) =
        FinKernel.compose (FinKernel.compose obs.2 k) f :=
      finKernel_compose_associative f k obs.2
    _ = FinKernel.compose (FinKernel.compose obs.2 k) g := heq
    _ = FinKernel.compose obs.2 (FinKernel.compose k g) :=
      (finKernel_compose_associative g k obs.2).symm

/--
Tensor-generated probes preserve probe-relative equivalence by generic tensor
interchange. No claim is made for arbitrary joint probes.
-/
theorem finKernel_probeEq_tensor_generated {a b c d : Nat}
    {P : FinKernel.ProbeFamily b} {Q : FinKernel.ProbeFamily d}
    {f f' : FinKernel a b} {g g' : FinKernel c d}
    (hf : FinKernel.ProbeEq P f f')
    (hg : FinKernel.ProbeEq Q g g') :
    FinKernel.ProbeEq (FinKernel.tensorGeneratedProbes P Q)
      (FinKernel.tensor f g) (FinKernel.tensor f' g') := by
  intro obs hobs
  rcases hobs with ⟨left, right, hleft, hright, rfl⟩
  have hlf := hf left hleft
  have hrg := hg right hright
  have ht := finKernel_behaviorEq_tensor hlf hrg
  have hteq :
      FinKernel.tensor
          (FinKernel.compose left.2 f)
          (FinKernel.compose right.2 g) =
        FinKernel.tensor
          (FinKernel.compose left.2 f')
          (FinKernel.compose right.2 g') :=
    (finKernel_behaviorEq_iff_eq _ _).1 ht
  apply (finKernel_behaviorEq_iff_eq _ _).2
  calc
    FinKernel.compose (FinKernel.tensor left.2 right.2)
        (FinKernel.tensor f g) =
      FinKernel.tensor
        (FinKernel.compose left.2 f)
        (FinKernel.compose right.2 g) :=
          finKernel_tensor_interchange f left.2 g right.2
    _ = FinKernel.tensor
        (FinKernel.compose left.2 f')
        (FinKernel.compose right.2 g') := hteq
    _ = FinKernel.compose (FinKernel.tensor left.2 right.2)
        (FinKernel.tensor f' g') :=
          (finKernel_tensor_interchange f' left.2 g' right.2).symm

/-- Three-state coarse observation: states 0 and 1 are merged; state 2 is distinct. -/
def finMerge01 : Fin 3 → Fin 2 :=
  fun x => if x = (2 : Fin 3) then (1 : Fin 2) else 0

/-- Deterministic future map moving state 1 into the separately observed state 2. -/
def finMoveOneToTwo : Fin 3 → Fin 3 :=
  fun x => if x = (1 : Fin 3) then (2 : Fin 3) else x

/-- Deterministic source at state 0 of the three-state interface. -/
def finKernelZero3 : FinKernel 1 3 :=
  FinKernel.dirac (fun _ => (0 : Fin 3))

/-- Deterministic source at state 1 of the three-state interface. -/
def finKernelOne3 : FinKernel 1 3 :=
  FinKernel.dirac (fun _ => (1 : Fin 3))

/-- Deterministic coarse observation kernel. -/
def finKernelMerge01 : FinKernel 3 2 := FinKernel.dirac finMerge01

/-- Deterministic future-map kernel. -/
def finKernelMoveOneToTwo : FinKernel 3 3 :=
  FinKernel.dirac finMoveOneToTwo

theorem finKernel_zero3_valid : FinKernel.Valid finKernelZero3 :=
  finKernel_dirac_valid _

theorem finKernel_one3_valid : FinKernel.Valid finKernelOne3 :=
  finKernel_dirac_valid _

theorem finKernel_merge01_valid : FinKernel.Valid finKernelMerge01 :=
  finKernel_dirac_valid _

theorem finKernel_moveOneToTwo_valid :
    FinKernel.Valid finKernelMoveOneToTwo :=
  finKernel_dirac_valid _

/-- The coarse observation identifies source states 0 and 1. -/
theorem finKernel_merge01_observes_zero_one_equal :
    FinKernel.ObservedEq finKernelMerge01 finKernelZero3 finKernelOne3 := by
  unfold FinKernel.ObservedEq
  unfold finKernelMerge01 finKernelZero3 finKernelOne3
  rw [finKernel_dirac_compose, finKernel_dirac_compose]
  apply (finKernel_behaviorEq_iff_eq _ _).2
  apply finKernel_dirac_congr
  intro x
  simp [finMerge01]

/-- After the future map, the coarse observation sends source 0 to observed 0. -/
theorem finKernel_merge01_after_move_zero :
    FinKernel.compose finKernelMerge01
      (FinKernel.compose finKernelMoveOneToTwo finKernelZero3) =
      FinKernel.dirac (fun _ : Fin 1 => (0 : Fin 2)) := by
  unfold finKernelMerge01 finKernelMoveOneToTwo finKernelZero3
  rw [finKernel_dirac_compose, finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  simp [finMoveOneToTwo, finMerge01]

/-- After the future map, source 1 is moved to observed state 1. -/
theorem finKernel_merge01_after_move_one :
    FinKernel.compose finKernelMerge01
      (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) =
      FinKernel.dirac (fun _ : Fin 1 => (1 : Fin 2)) := by
  unfold finKernelMerge01 finKernelMoveOneToTwo finKernelOne3
  rw [finKernel_dirac_compose, finKernel_dirac_compose]
  apply finKernel_dirac_congr
  intro x
  simp [finMoveOneToTwo, finMerge01]

/--
The same fixed coarse probe no longer identifies the sources after the future
map. This is a deterministic valid counterexample to automatic postcomposition
congruence for arbitrary fixed-probe equivalence.
-/
theorem finKernel_fixed_probe_not_postcomposition_stable :
    ¬ FinKernel.ObservedEq finKernelMerge01
      (FinKernel.compose finKernelMoveOneToTwo finKernelZero3)
      (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) := by
  intro h
  unfold FinKernel.ObservedEq at h
  rw [finKernel_merge01_after_move_zero,
    finKernel_merge01_after_move_one] at h
  have h00 := h (0 : Fin 1) (0 : Fin 2)
  simp [FinKernel.dirac] at h00

/-- Exact fixed-probe pressure: equal before the future map, unequal after it. -/
theorem finKernel_fixed_probe_postcomposition_counterexample :
    FinKernel.ObservedEq finKernelMerge01 finKernelZero3 finKernelOne3 ∧
    ¬ FinKernel.ObservedEq finKernelMerge01
      (FinKernel.compose finKernelMoveOneToTwo finKernelZero3)
      (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) := by
  exact ⟨finKernel_merge01_observes_zero_one_equal,
    finKernel_fixed_probe_not_postcomposition_stable⟩

/-- The same counterexample is expressible directly as singleton-family `ProbeEq`. -/
theorem finKernel_singleton_probe_postcomposition_counterexample :
    FinKernel.ProbeEq
      (FinKernel.singletonProbe ⟨2, finKernelMerge01⟩)
      finKernelZero3 finKernelOne3 ∧
    ¬ FinKernel.ProbeEq
      (FinKernel.singletonProbe ⟨2, finKernelMerge01⟩)
      (FinKernel.compose finKernelMoveOneToTwo finKernelZero3)
      (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) := by
  rw [finKernel_probeEq_singleton_iff_observedEq,
    finKernel_probeEq_singleton_iff_observedEq]
  exact finKernel_fixed_probe_postcomposition_counterexample

end RelayTheory
