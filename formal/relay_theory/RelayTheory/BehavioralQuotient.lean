import RelayTheory.GenericMarkovLaws

namespace RelayTheory

namespace FinKernel

/--
Exact extensional behavioral equivalence for fully resolved finite stochastic
kernels: every declared source/output probability agrees exactly.
-/
def BehaviorEq {m n : Nat} (f g : FinKernel m n) : Prop :=
  ∀ x y, f x y = g x y

/-- Behavioral equivalence after one fixed downstream observation kernel. -/
def ObservedEq {m n q : Nat}
    (obs : FinKernel n q) (f g : FinKernel m n) : Prop :=
  BehaviorEq (compose obs f) (compose obs g)

/-- Contextual equivalence under every exact downstream finite-kernel context. -/
def ContextEq {m n : Nat} (f g : FinKernel m n) : Prop :=
  ∀ q (obs : FinKernel n q), ObservedEq obs f g

end FinKernel

/-- Exact kernel behavior is reflexive. -/
theorem finKernel_behaviorEq_refl {m n : Nat} (f : FinKernel m n) :
    FinKernel.BehaviorEq f f := by
  intro x y
  rfl

/-- Exact kernel behavior is symmetric. -/
theorem finKernel_behaviorEq_symm {m n : Nat} {f g : FinKernel m n}
    (h : FinKernel.BehaviorEq f g) :
    FinKernel.BehaviorEq g f := by
  intro x y
  exact (h x y).symm

/-- Exact kernel behavior is transitive. -/
theorem finKernel_behaviorEq_trans {m n : Nat} {f g h : FinKernel m n}
    (hfg : FinKernel.BehaviorEq f g)
    (hgh : FinKernel.BehaviorEq g h) :
    FinKernel.BehaviorEq f h := by
  intro x y
  exact Eq.trans (hfg x y) (hgh x y)

/--
The key Grand Null result: the current exact `FinKernel` representation is
already extensional. Exact behavioral equivalence is exactly Lean equality.
-/
theorem finKernel_behaviorEq_iff_eq {m n : Nat} (f g : FinKernel m n) :
    FinKernel.BehaviorEq f g ↔ f = g := by
  constructor
  · intro h
    funext x y
    exact h x y
  · intro h
    subst g
    exact finKernel_behaviorEq_refl f

/-- Stochastic validity is invariant under exact behavioral equivalence. -/
theorem finKernel_behaviorEq_valid_iff {m n : Nat} {f g : FinKernel m n}
    (h : FinKernel.BehaviorEq f g) :
    FinKernel.Valid f ↔ FinKernel.Valid g := by
  have heq : f = g := (finKernel_behaviorEq_iff_eq f g).1 h
  subst g
  rfl

/-- Exact behavioral equivalence is a two-sided congruence for composition. -/
theorem finKernel_behaviorEq_compose {a b c : Nat}
    {f f' : FinKernel a b} {g g' : FinKernel b c}
    (hf : FinKernel.BehaviorEq f f')
    (hg : FinKernel.BehaviorEq g g') :
    FinKernel.BehaviorEq
      (FinKernel.compose g f)
      (FinKernel.compose g' f') := by
  have hfeq : f = f' := (finKernel_behaviorEq_iff_eq f f').1 hf
  have hgeq : g = g' := (finKernel_behaviorEq_iff_eq g g').1 hg
  subst f'
  subst g'
  exact finKernel_behaviorEq_refl _

/-- Exact behavioral equivalence is a congruence for independent tensor. -/
theorem finKernel_behaviorEq_tensor {a b c d : Nat}
    {f f' : FinKernel a b} {g g' : FinKernel c d}
    (hf : FinKernel.BehaviorEq f f')
    (hg : FinKernel.BehaviorEq g g') :
    FinKernel.BehaviorEq
      (FinKernel.tensor f g)
      (FinKernel.tensor f' g') := by
  have hfeq : f = f' := (finKernel_behaviorEq_iff_eq f f').1 hf
  have hgeq : g = g' := (finKernel_behaviorEq_iff_eq g g').1 hg
  subst f'
  subst g'
  exact finKernel_behaviorEq_refl _

/-- A fixed observation relation is preserved by arbitrary precomposition. -/
theorem finKernel_observedEq_precompose {l m n q : Nat}
    {obs : FinKernel n q} {f g : FinKernel m n}
    (hfg : FinKernel.ObservedEq obs f g)
    (h : FinKernel l m) :
    FinKernel.ObservedEq obs
      (FinKernel.compose f h)
      (FinKernel.compose g h) := by
  unfold FinKernel.ObservedEq at hfg ⊢
  have heq : FinKernel.compose obs f = FinKernel.compose obs g :=
    (finKernel_behaviorEq_iff_eq _ _).1 hfg
  rw [finKernel_compose_associative, finKernel_compose_associative, heq]
  exact finKernel_behaviorEq_refl _

/-- Exact behavior implies equivalence in every exact downstream context. -/
theorem finKernel_behaviorEq_implies_contextEq {m n : Nat}
    {f g : FinKernel m n}
    (hfg : FinKernel.BehaviorEq f g) :
    FinKernel.ContextEq f g := by
  intro q obs
  exact finKernel_behaviorEq_compose hfg (finKernel_behaviorEq_refl obs)

/--
Conversely, quantifying over every exact downstream context adds no coarser
identification because the identity context can observe the whole kernel.
-/
theorem finKernel_contextEq_implies_behaviorEq {m n : Nat}
    {f g : FinKernel m n}
    (hfg : FinKernel.ContextEq f g) :
    FinKernel.BehaviorEq f g := by
  have hid := hfg n (FinKernel.identity n)
  unfold FinKernel.ObservedEq at hid
  simpa only [finKernel_compose_identity_after] using hid

/-- Exact contextual equivalence is therefore also the identity quotient. -/
theorem finKernel_contextEq_iff_behaviorEq {m n : Nat}
    (f g : FinKernel m n) :
    FinKernel.ContextEq f g ↔ FinKernel.BehaviorEq f g := by
  constructor
  · exact finKernel_contextEq_implies_behaviorEq
  · exact finKernel_behaviorEq_implies_contextEq

/-- Exact contextual equivalence coincides with literal kernel equality. -/
theorem finKernel_contextEq_iff_eq {m n : Nat} (f g : FinKernel m n) :
    FinKernel.ContextEq f g ↔ f = g := by
  rw [finKernel_contextEq_iff_behaviorEq, finKernel_behaviorEq_iff_eq]

/-- Deterministic source selecting the first point of `Fin 2`. -/
def finKernelFirst : FinKernel 1 2 :=
  FinKernel.dirac (fun _ => (0 : Fin 2))

/-- Deterministic source selecting the second point of `Fin 2`. -/
def finKernelSecond : FinKernel 1 2 :=
  FinKernel.dirac (fun _ => (1 : Fin 2))

/-- The two deterministic sources are genuinely different exact behaviors. -/
theorem finKernel_first_ne_second :
    ¬ FinKernel.BehaviorEq finKernelFirst finKernelSecond := by
  intro h
  have h00 := h (0 : Fin 1) (0 : Fin 2)
  simp [finKernelFirst, finKernelSecond, FinKernel.dirac] at h00

/-- Both deterministic counterexample kernels are stochastic-valid. -/
theorem finKernel_first_valid : FinKernel.Valid finKernelFirst :=
  finKernel_dirac_valid _

theorem finKernel_second_valid : FinKernel.Valid finKernelSecond :=
  finKernel_dirac_valid _

/--
A fixed coarse probe can identify distinct exact kernels: discard observes only
total mass, so the two deterministic sources become observationally equal.
-/
theorem finKernel_discard_observes_first_second_equal :
    FinKernel.ObservedEq (FinKernel.discard 2)
      finKernelFirst finKernelSecond := by
  unfold FinKernel.ObservedEq
  have hfirst := finKernel_discard_causal finKernel_first_valid
  have hsecond := finKernel_discard_causal finKernel_second_valid
  rw [hfirst, hsecond]
  exact finKernel_behaviorEq_refl _

/--
The same pair is immediately distinguished by the identity downstream context.
Thus one fixed-probe observational equivalence is non-trivial but is not a
universal contextual congruence.
-/
theorem finKernel_identity_distinguishes_first_second :
    ¬ FinKernel.ObservedEq (FinKernel.identity 2)
      finKernelFirst finKernelSecond := by
  unfold FinKernel.ObservedEq
  simpa only [finKernel_compose_identity_after] using finKernel_first_ne_second

/-- Fixed discard-observational equivalence is strictly coarser than exact behavior. -/
theorem finKernel_fixed_probe_is_strictly_coarser :
    FinKernel.ObservedEq (FinKernel.discard 2)
      finKernelFirst finKernelSecond ∧
    ¬ FinKernel.BehaviorEq finKernelFirst finKernelSecond := by
  exact ⟨finKernel_discard_observes_first_second_equal,
    finKernel_first_ne_second⟩

/--
The counterexample pair is not contextually equivalent, despite equivalence
under the single discard probe.
-/
theorem finKernel_fixed_probe_not_contextual :
    ¬ FinKernel.ContextEq finKernelFirst finKernelSecond := by
  intro h
  exact finKernel_first_ne_second
    (finKernel_contextEq_implies_behaviorEq h)

end RelayTheory
