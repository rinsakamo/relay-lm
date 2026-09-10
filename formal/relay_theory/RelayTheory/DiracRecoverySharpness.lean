import RelayTheory.SplitLaterReflection

namespace RelayTheory

/--
Transpose-delta exact recovery candidate for a deterministic map.  No
stochastic-validity claim is built into this kernel: target points outside the
image may have zero row mass.
-/
def finKernelDiracTranspose {a q : Nat}
    (f : Fin a → Fin q) : FinKernel q a :=
  fun y x => if y = f x then 1 else 0

/--
Injectivity is sufficient for the transpose-delta kernel to recover a Dirac map
exactly.  This statement includes empty finite interfaces without a nonempty
premise.
-/
theorem finKernel_diracTranspose_after_dirac_of_injective
    {a q : Nat} (f : Fin a → Fin q)
    (hinj : Function.Injective f) :
    FinKernel.compose (finKernelDiracTranspose f) (FinKernel.dirac f) =
      FinKernel.identity a := by
  funext x z
  rw [finKernel_compose_after_dirac_eval]
  by_cases hxz : x = z
  · subst z
    simp [finKernelDiracTranspose, FinKernel.identity]
  · have hfne : f x ≠ f z := by
      intro h
      exact hxz (hinj h)
    simp [finKernelDiracTranspose, FinKernel.identity, hxz, hfne]

/-- Every injective finite function gives exact recovery of its Dirac kernel. -/
theorem finKernel_dirac_hasExactRecovery_of_injective
    {a q : Nat} (f : Fin a → Fin q)
    (hinj : Function.Injective f) :
    FinKernel.HasExactRecovery (FinKernel.dirac f) := by
  exact ⟨finKernelDiracTranspose f,
    finKernel_diracTranspose_after_dirac_of_injective f hinj⟩

/--
No arbitrary signed/exact recovery kernel can undo a deterministic collision.
Thus exact recovery of a Dirac kernel forces injectivity of the underlying map.
-/
theorem finKernel_dirac_injective_of_hasExactRecovery
    {a q : Nat} (f : Fin a → Fin q)
    (hrecover : FinKernel.HasExactRecovery (FinKernel.dirac f)) :
    Function.Injective f := by
  rcases hrecover with ⟨recovery, hrec⟩
  intro x y hxy
  by_contra hne
  have hne' : y ≠ x := by
    intro h
    exact hne h.symm
  have hx := congrFun (congrFun hrec x) x
  have hy := congrFun (congrFun hrec y) x
  rw [finKernel_compose_after_dirac_eval] at hx hy
  have hxone : recovery (f x) x = 1 := by
    simpa [FinKernel.identity] using hx
  have hyzero : recovery (f y) x = 0 := by
    simpa [FinKernel.identity, hne'] using hy
  rw [hxy] at hyzero
  grind

/-- Exact deterministic recovery is precisely injectivity. -/
theorem finKernel_dirac_hasExactRecovery_iff_injective
    {a q : Nat} (f : Fin a → Fin q) :
    FinKernel.HasExactRecovery (FinKernel.dirac f) ↔
      Function.Injective f := by
  constructor
  · exact finKernel_dirac_injective_of_hasExactRecovery f
  · exact finKernel_dirac_hasExactRecovery_of_injective f

/--
Combining the already-earned deterministic epicity characterization with exact
recovery sharpness gives the exact bijective boundary.
-/
theorem finKernel_dirac_epic_and_exactRecovery_iff_bijective
    {a q : Nat} (f : Fin a → Fin q) :
    (FinKernel.ObservationEpic (FinKernel.dirac f) ∧
      FinKernel.HasExactRecovery (FinKernel.dirac f)) ↔
      Function.Bijective f := by
  constructor
  · intro h
    exact ⟨
      (finKernel_dirac_hasExactRecovery_iff_injective f).1 h.2,
      (finKernel_dirac_observationEpic_iff_surjective f).1 h.1⟩
  · intro h
    exact ⟨
      (finKernel_dirac_observationEpic_iff_surjective f).2 h.2,
      (finKernel_dirac_hasExactRecovery_iff_injective f).2 h.1⟩

/--
For a bijection, every target point has exactly one preimage, so the explicit
transpose-delta recovery is itself stochastic-valid.
-/
theorem finKernel_diracTranspose_valid_of_bijective
    {a q : Nat} (f : Fin a → Fin q)
    (hbij : Function.Bijective f) :
    FinKernel.Valid (finKernelDiracTranspose f) := by
  constructor
  · intro y x
    by_cases h : y = f x
    · simpa [finKernelDiracTranspose, h] using rat_zero_le_one
    · simp [finKernelDiracTranspose, h]
  · intro y
    rcases hbij.2 y with ⟨x, hx⟩
    unfold FinKernel.rowSum
    calc
      sumFin a (fun z => finKernelDiracTranspose f y z) =
          sumFin a (fun z => if z = x then (1 : Rat) else 0) := by
        apply sumFin_congr
        intro z
        by_cases hzx : z = x
        · subst z
          have hy : y = f x := hx.symm
          simp [finKernelDiracTranspose, hy]
        · have hyne : y ≠ f z := by
            intro hyz
            apply hzx
            apply hbij.1
            calc
              f z = y := hyz.symm
              _ = f x := hx.symm
          simp [finKernelDiracTranspose, hzx, hyne]
      _ = 1 := by
        simpa using sumFin_single x (fun _ => (1 : Rat))

/-- Every deterministic bijection has an explicit stochastic-valid recovery. -/
theorem finKernel_dirac_hasValidStochasticRecovery_of_bijective
    {a q : Nat} (f : Fin a → Fin q)
    (hbij : Function.Bijective f) :
    FinKernel.HasValidStochasticRecovery (FinKernel.dirac f) := by
  exact ⟨finKernelDiracTranspose f,
    finKernel_diracTranspose_valid_of_bijective f hbij,
    finKernel_diracTranspose_after_dirac_of_injective f hbij.1⟩

/-- A concrete injective but non-surjective deterministic control. -/
def finInjectOneToTwo : Fin 1 → Fin 2 :=
  fun _ => 0

theorem finInjectOneToTwo_injective : Function.Injective finInjectOneToTwo := by
  intro x y _
  calc
    x = (0 : Fin 1) := fin_one_eq_zero x
    _ = y := (fin_one_eq_zero y).symm

theorem finInjectOneToTwo_not_surjective :
    ¬ Function.Surjective finInjectOneToTwo := by
  intro hsurj
  rcases hsurj (1 : Fin 2) with ⟨x, hx⟩
  have hzeroone : (0 : Fin 2) = (1 : Fin 2) := by
    simpa [finInjectOneToTwo] using hx
  exact (by decide : (0 : Fin 2) ≠ (1 : Fin 2)) hzeroone

/--
Injectivity without surjectivity gives exact recovery but not epicity, providing
one side of the deterministic sharpness boundary.
-/
theorem finInjectOneToTwo_recoverable_not_epic_bundle :
    FinKernel.Valid (FinKernel.dirac finInjectOneToTwo) ∧
    FinKernel.HasExactRecovery (FinKernel.dirac finInjectOneToTwo) ∧
    (¬ FinKernel.ObservationEpic (FinKernel.dirac finInjectOneToTwo)) := by
  refine ⟨finKernel_dirac_valid finInjectOneToTwo,
    finKernel_dirac_hasExactRecovery_of_injective
      finInjectOneToTwo finInjectOneToTwo_injective, ?_⟩
  intro hepic
  exact finInjectOneToTwo_not_surjective
    ((finKernel_dirac_observationEpic_iff_surjective finInjectOneToTwo).1 hepic)

/--
The opposite one-sided boundary is already supplied by binary discard: epic but
not exactly recoverable.
-/
theorem finKernel_discard_two_epic_not_recoverable_bundle :
    FinKernel.Valid (FinKernel.discard 2) ∧
    FinKernel.ObservationEpic (FinKernel.discard 2) ∧
    (¬ FinKernel.HasExactRecovery (FinKernel.discard 2)) := by
  exact ⟨finKernel_discard_valid 2,
    finKernel_discard_two_observationEpic,
    finKernel_discard_two_not_hasExactRecovery⟩

/--
Acceptance package for deterministic exact-recovery sharpness.
-/
theorem finKernel_dirac_recovery_sharpness_bundle :
    (∀ {a q : Nat} (f : Fin a → Fin q),
      FinKernel.HasExactRecovery (FinKernel.dirac f) ↔
        Function.Injective f) ∧
    (∀ {a q : Nat} (f : Fin a → Fin q),
      (FinKernel.ObservationEpic (FinKernel.dirac f) ∧
        FinKernel.HasExactRecovery (FinKernel.dirac f)) ↔
        Function.Bijective f) ∧
    (∀ {a q : Nat} (f : Fin a → Fin q),
      Function.Bijective f →
        FinKernel.HasValidStochasticRecovery (FinKernel.dirac f)) := by
  exact ⟨finKernel_dirac_hasExactRecovery_iff_injective,
    finKernel_dirac_epic_and_exactRecovery_iff_bijective,
    finKernel_dirac_hasValidStochasticRecovery_of_bijective⟩

end RelayTheory
