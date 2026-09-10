import RelayTheory.ProbeRelative

namespace RelayTheory

namespace FinKernel

/-- A probe family assigned to every declared finite interface. -/
abbrev ProbeDoctrine := ∀ n : Nat, ProbeFamily n

/--
Closure under pullback along every deterministic future map.  If an observation
is admitted after `k`, composing it with the Dirac kernel of `k` must already
be admitted before `k`.
-/
def DeterministicPullbackClosed (D : ProbeDoctrine) : Prop :=
  ∀ {n p : Nat} (k : Fin n → Fin p) (obs : Observation p),
    D p obs → D n ⟨obs.1, compose obs.2 (dirac k)⟩

/-- Closure under pullback along every stochastic-valid future kernel. -/
def ValidPullbackClosed (D : ProbeDoctrine) : Prop :=
  ∀ {n p : Nat} (k : FinKernel n p), Valid k →
    ∀ obs : Observation p,
      D p obs → D n ⟨obs.1, compose obs.2 k⟩

/-- The doctrine that admits exactly generic discard at every interface. -/
def discardDoctrine : ProbeDoctrine :=
  fun n => singletonProbe ⟨1, discard n⟩

end FinKernel

/--
A deterministic selector sends one chosen finite state to `hit` and every
other state to `miss`.
-/
def finSelectorAt {n p : Nat}
    (target : Fin n) (hit miss : Fin p) : Fin n → Fin p :=
  fun y => if y = target then hit else miss

/--
Core coordinate-extraction lemma.  If a deterministic observation distinguishes
`hit` from `miss`, then pulling it back through the selector for `target` and
observing at `h hit` extracts exactly the `target` coordinate of any exact
kernel.  No stochastic-validity assumption is used.
-/
theorem finKernel_pulled_dirac_selector_extract
    {m n p q : Nat}
    (f : FinKernel m n)
    (target : Fin n) (hit miss : Fin p)
    (h : Fin p → Fin q)
    (hne : h hit ≠ h miss)
    (x : Fin m) :
    FinKernel.compose
        (FinKernel.compose (FinKernel.dirac h)
          (FinKernel.dirac (finSelectorAt target hit miss)))
        f x (h hit) =
      f x target := by
  rw [finKernel_dirac_compose]
  unfold FinKernel.compose FinKernel.dirac
  calc
    sumFin n (fun y =>
        f x y *
          (if h hit = h (finSelectorAt target hit miss y) then 1 else 0)) =
      sumFin n (fun y => if y = target then f x y else 0) := by
        apply sumFin_congr
        intro y
        by_cases hy : y = target
        · subst y
          simp [finSelectorAt]
        · simp [finSelectorAt, hy, hne]
    _ = f x target := sumFin_single target (fun y => f x y)

/--
One admitted non-constant deterministic probe collapses a deterministically
pullback-closed probe-relative quotient to literal exact-kernel equality.
-/
theorem finKernel_probeDoctrine_nonconstant_dirac_forces_eq
    {m n p q : Nat}
    (D : FinKernel.ProbeDoctrine)
    (hclose : FinKernel.DeterministicPullbackClosed D)
    (h : Fin p → Fin q)
    (hit miss : Fin p)
    (hne : h hit ≠ h miss)
    (hadmit : D p ⟨q, FinKernel.dirac h⟩)
    {f g : FinKernel m n}
    (hfg : FinKernel.ProbeEq (D n) f g) :
    f = g := by
  funext x target
  have hpull :
      D n ⟨q,
        FinKernel.compose (FinKernel.dirac h)
          (FinKernel.dirac (finSelectorAt target hit miss))⟩ :=
    hclose (finSelectorAt target hit miss)
      ⟨q, FinKernel.dirac h⟩ hadmit
  have hobs := hfg
    ⟨q,
      FinKernel.compose (FinKernel.dirac h)
        (FinKernel.dirac (finSelectorAt target hit miss))⟩
    hpull
  have hv := hobs x (h hit)
  have hfextract :=
    finKernel_pulled_dirac_selector_extract
      f target hit miss h hne x
  have hgextract :=
    finKernel_pulled_dirac_selector_extract
      g target hit miss h hne x
  rw [hfextract, hgextract] at hv
  exact hv

/--
Motivating binary special case: admitting identity on `Fin 2` under deterministic
pullback closure is already enough to recover literal exact-kernel equality.
-/
theorem finKernel_probeDoctrine_binary_identity_forces_eq
    {m n : Nat}
    (D : FinKernel.ProbeDoctrine)
    (hclose : FinKernel.DeterministicPullbackClosed D)
    (hadmit : D 2 ⟨2, FinKernel.identity 2⟩)
    {f g : FinKernel m n}
    (hfg : FinKernel.ProbeEq (D n) f g) :
    f = g := by
  have hadmitDirac :
      D 2 ⟨2, FinKernel.dirac (fun x : Fin 2 => x)⟩ := by
    simpa only [finKernel_identity_eq_dirac_id] using hadmit
  apply finKernel_probeDoctrine_nonconstant_dirac_forces_eq
    D hclose (fun x : Fin 2 => x) (1 : Fin 2) (0 : Fin 2)
  · intro h10
    have hv := congrArg Fin.val h10
    grind
  · exact hadmitDirac
  · exact hfg

/--
Discard-only observation is closed under every stochastic-valid future context:
causality rewrites every pulled-back discard to the discard of the source.
-/
theorem finKernel_discardDoctrine_valid_pullback_closed :
    FinKernel.ValidPullbackClosed FinKernel.discardDoctrine := by
  intro n p k hk obs hobs
  unfold FinKernel.discardDoctrine FinKernel.singletonProbe at hobs ⊢
  subst obs
  rw [finKernel_discard_causal hk]

/-- Deterministic pullback closure is an immediate corollary of valid closure. -/
theorem finKernel_discardDoctrine_deterministic_pullback_closed :
    FinKernel.DeterministicPullbackClosed FinKernel.discardDoctrine := by
  intro n p k obs hobs
  exact finKernel_discardDoctrine_valid_pullback_closed
    (FinKernel.dirac k) (finKernel_dirac_valid k) obs hobs

/--
On stochastic-valid kernels the discard-only doctrine is completely blind:
all compatible normalized kernels are probe-equivalent.
-/
theorem finKernel_discardDoctrine_probeEq_of_valid
    {m n : Nat} {f g : FinKernel m n}
    (hf : FinKernel.Valid f) (hg : FinKernel.Valid g) :
    FinKernel.ProbeEq (FinKernel.discardDoctrine n) f g := by
  unfold FinKernel.discardDoctrine
  rw [finKernel_probeEq_singleton_iff_observedEq]
  unfold FinKernel.ObservedEq
  rw [finKernel_discard_causal hf, finKernel_discard_causal hg]
  exact finKernel_behaviorEq_refl _

/--
The two proven poles coexist: discard is valid-context-closed and blind on
valid kernels, while any admitted non-constant deterministic separator under
deterministic pullback closure forces exact equality.  This theorem records
only conjunction of those earned facts; it does not assert that no intermediate
doctrine exists.
-/
theorem finKernel_probeDoctrine_poles_earned :
    FinKernel.ValidPullbackClosed FinKernel.discardDoctrine ∧
    FinKernel.DeterministicPullbackClosed FinKernel.discardDoctrine := by
  exact ⟨finKernel_discardDoctrine_valid_pullback_closed,
    finKernel_discardDoctrine_deterministic_pullback_closed⟩

end RelayTheory
