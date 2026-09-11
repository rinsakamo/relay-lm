import RelayTheory.StochasticRecoverabilityPreorder
import RelayTheory.ObserverChainRealizers

namespace RelayTheory

namespace FinKernel

/--
Exact intrinsic information degradation on a fixed concrete source.
`ExactPostprocess fine coarse` means that `coarse` is obtainable from `fine`
by a postprocessing kernel. No external causal/order relation is an input.

Unlike `StochasticDegradesTo`, this relation deliberately does not require the
postprocessor to be stochastic-valid. It is the larger signed-rational relation
used to make the incomparability obstruction stronger.
-/
def ExactPostprocess {a q r : Nat}
    (fine : FinKernel a q) (coarse : FinKernel a r) : Prop :=
  ∃ post : FinKernel q r, compose post fine = coarse

end FinKernel

/-- Every stochastic-valid garbling is, after forgetting validity, an exact postprocessing. -/
theorem finKernel_stochasticDegradesTo_to_exactPostprocess
    {a q r : Nat} {fine : FinKernel a q} {coarse : FinKernel a r}
    (h : FinKernel.StochasticDegradesTo fine coarse) :
    FinKernel.ExactPostprocess fine coarse := by
  rcases h with ⟨post, _, hpost⟩
  exact ⟨post, hpost⟩

/-- Exact postprocessing is reflexive. -/
theorem finKernel_exactPostprocess_refl {a q : Nat} (obs : FinKernel a q) :
    FinKernel.ExactPostprocess obs obs := by
  exact ⟨FinKernel.identity q, finKernel_compose_identity_after obs⟩

/-- Exact postprocessing is transitive by ordinary kernel composition. -/
theorem finKernel_exactPostprocess_trans
    {a q r s : Nat}
    {fine : FinKernel a q} {middle : FinKernel a r} {coarse : FinKernel a s}
    (hfm : FinKernel.ExactPostprocess fine middle)
    (hmc : FinKernel.ExactPostprocess middle coarse) :
    FinKernel.ExactPostprocess fine coarse := by
  rcases hfm with ⟨postFM, hFM⟩
  rcases hmc with ⟨postMC, hMC⟩
  refine ⟨FinKernel.compose postMC postFM, ?_⟩
  calc
    FinKernel.compose (FinKernel.compose postMC postFM) fine =
        FinKernel.compose postMC (FinKernel.compose postFM fine) :=
      (finKernel_compose_associative fine postFM postMC).symm
    _ = FinKernel.compose postMC middle := by rw [hFM]
    _ = coarse := hMC

/-- Applying an arbitrary exact kernel after a Dirac observation selects one row. -/
theorem finKernel_compose_after_dirac_apply
    {a q r : Nat} (post : FinKernel q r) (f : Fin a → Fin q)
    (x : Fin a) (z : Fin r) :
    FinKernel.compose post (FinKernel.dirac f) x z = post (f x) z := by
  unfold FinKernel.compose FinKernel.dirac
  calc
    sumFin q (fun y => (if y = f x then 1 else 0) * post y z) =
        sumFin q (fun y => if y = f x then post y z else 0) := by
      apply sumFin_congr
      intro y
      by_cases h : y = f x <;> simp [h]
    _ = post (f x) z := sumFin_single (f x) (fun y => post y z)

/--
Postprocessing cannot recover a deterministic distinction that the earlier
Dirac observation has already identified. The postprocessor may be any exact
signed-rational kernel; stochastic validity is not assumed.
-/
theorem finKernel_exactPostprocess_dirac_preserves_fibers
    {a q r : Nat} {f : Fin a → Fin q} {g : Fin a → Fin r}
    (h : FinKernel.ExactPostprocess (FinKernel.dirac f) (FinKernel.dirac g))
    {x y : Fin a} (hxy : f x = f y) : g x = g y := by
  rcases h with ⟨post, hpost⟩
  by_cases hEq : g x = g y
  · exact hEq
  · have hx := congrFun (congrFun hpost x) (g x)
    have hy := congrFun (congrFun hpost y) (g x)
    rw [finKernel_compose_after_dirac_apply] at hx hy
    have hx1 : post (f x) (g x) = 1 := by
      calc
        post (f x) (g x) = FinKernel.dirac g x (g x) := hx
        _ = 1 := by simp [FinKernel.dirac]
    have hy0 : post (f y) (g x) = 0 := by
      calc
        post (f y) (g x) = FinKernel.dirac g y (g x) := hy
        _ = 0 := by simp [FinKernel.dirac, hEq]
    rw [hxy] at hx1
    have h10 : (1 : Rat) = 0 := hx1.symm.trans hy0
    exact False.elim ((by decide : (1 : Rat) ≠ 0) h10)

/-- Exact finite identity is the Dirac kernel of the identity function. -/
theorem finKernel_identity_eq_dirac_id (n : Nat) :
    FinKernel.identity n = FinKernel.dirac (fun x : Fin n => x) := by
  funext x y
  by_cases h : x = y
  · subst y
    simp [FinKernel.identity, FinKernel.dirac]
  · have h' : y ≠ x := by
      intro e
      exact h e.symm
    simp [FinKernel.identity, FinKernel.dirac, h, h']

/-- If a deterministic observation can be exactly postprocessed back to identity, it was injective. -/
theorem finKernel_exactPostprocess_dirac_to_identity_injective
    {a q : Nat} {f : Fin a → Fin q}
    (h : FinKernel.ExactPostprocess (FinKernel.dirac f) (FinKernel.identity a)) :
    Function.Injective f := by
  intro x y hxy
  have hDirac :
      FinKernel.ExactPostprocess
        (FinKernel.dirac f) (FinKernel.dirac (fun z : Fin a => z)) := by
    rw [← finKernel_identity_eq_dirac_id a]
    exact h
  exact finKernel_exactPostprocess_dirac_preserves_fibers hDirac hxy

/-- First crossing partition: `{0,1} | {2,3}`. -/
def degradationPartitionA (x : Fin 4) : Fin 2 :=
  if x = (0 : Fin 4) ∨ x = (1 : Fin 4) then (0 : Fin 2) else (1 : Fin 2)

/-- Second crossing partition: `{0,2} | {1,3}`. -/
def degradationPartitionB (x : Fin 4) : Fin 2 :=
  if x = (0 : Fin 4) ∨ x = (2 : Fin 4) then (0 : Fin 2) else (1 : Fin 2)

/-- Terminal one-cell partition. -/
def degradationCoarseFn (_ : Fin 4) : Fin 1 := (0 : Fin 1)

/-- Maximally distinguishing observation. -/
def degradationFine : FinKernel 4 4 := FinKernel.identity 4

/-- First two-cell deterministic observation. -/
def degradationMiddleA : FinKernel 4 2 := FinKernel.dirac degradationPartitionA

/-- Crossing two-cell deterministic observation. -/
def degradationMiddleB : FinKernel 4 2 := FinKernel.dirac degradationPartitionB

/-- Completely coarse deterministic observation. -/
def degradationCoarse : FinKernel 4 1 := FinKernel.dirac degradationCoarseFn

/-- All four concrete observation nodes are stochastic-valid. -/
theorem intrinsic_degradation_nodes_valid :
    FinKernel.Valid degradationFine ∧
      FinKernel.Valid degradationMiddleA ∧
      FinKernel.Valid degradationMiddleB ∧
      FinKernel.Valid degradationCoarse := by
  exact ⟨finKernel_identity_valid 4,
    finKernel_dirac_valid degradationPartitionA,
    finKernel_dirac_valid degradationPartitionB,
    finKernel_dirac_valid degradationCoarseFn⟩

/-- Fine observation degrades stochastically to middle A. -/
theorem degradationFine_stochastic_to_middleA :
    FinKernel.StochasticDegradesTo degradationFine degradationMiddleA := by
  refine ⟨degradationMiddleA, intrinsic_degradation_nodes_valid.2.1, ?_⟩
  exact finKernel_compose_identity_before degradationMiddleA

/-- Fine observation degrades stochastically to middle B. -/
theorem degradationFine_stochastic_to_middleB :
    FinKernel.StochasticDegradesTo degradationFine degradationMiddleB := by
  refine ⟨degradationMiddleB, intrinsic_degradation_nodes_valid.2.2.1, ?_⟩
  exact finKernel_compose_identity_before degradationMiddleB

/-- Middle A degrades stochastically to the terminal coarse observation. -/
theorem degradationMiddleA_stochastic_to_coarse :
    FinKernel.StochasticDegradesTo degradationMiddleA degradationCoarse := by
  refine ⟨FinKernel.dirac (fun _ : Fin 2 => (0 : Fin 1)),
    finKernel_dirac_valid (fun _ : Fin 2 => (0 : Fin 1)), ?_⟩
  unfold degradationMiddleA degradationCoarse
  rw [finKernel_dirac_compose]
  rfl

/-- Middle B degrades stochastically to the terminal coarse observation. -/
theorem degradationMiddleB_stochastic_to_coarse :
    FinKernel.StochasticDegradesTo degradationMiddleB degradationCoarse := by
  refine ⟨FinKernel.dirac (fun _ : Fin 2 => (0 : Fin 1)),
    finKernel_dirac_valid (fun _ : Fin 2 => (0 : Fin 1)), ?_⟩
  unfold degradationMiddleB degradationCoarse
  rw [finKernel_dirac_compose]
  rfl

/-- Fine therefore also degrades stochastically to the terminal observation. -/
theorem degradationFine_stochastic_to_coarse :
    FinKernel.StochasticDegradesTo degradationFine degradationCoarse :=
  finKernel_stochasticDegradesTo_trans
    degradationFine_stochastic_to_middleA degradationMiddleA_stochastic_to_coarse

/-- Fine observation degrades exactly to middle A. -/
theorem degradationFine_to_middleA :
    FinKernel.ExactPostprocess degradationFine degradationMiddleA :=
  finKernel_stochasticDegradesTo_to_exactPostprocess degradationFine_stochastic_to_middleA

/-- Fine observation degrades exactly to middle B. -/
theorem degradationFine_to_middleB :
    FinKernel.ExactPostprocess degradationFine degradationMiddleB :=
  finKernel_stochasticDegradesTo_to_exactPostprocess degradationFine_stochastic_to_middleB

/-- Middle A degrades exactly to the terminal coarse observation. -/
theorem degradationMiddleA_to_coarse :
    FinKernel.ExactPostprocess degradationMiddleA degradationCoarse :=
  finKernel_stochasticDegradesTo_to_exactPostprocess degradationMiddleA_stochastic_to_coarse

/-- Middle B degrades exactly to the terminal coarse observation. -/
theorem degradationMiddleB_to_coarse :
    FinKernel.ExactPostprocess degradationMiddleB degradationCoarse :=
  finKernel_stochasticDegradesTo_to_exactPostprocess degradationMiddleB_stochastic_to_coarse

/-- Fine degrades exactly to the terminal coarse observation. -/
theorem degradationFine_to_coarse :
    FinKernel.ExactPostprocess degradationFine degradationCoarse :=
  finKernel_stochasticDegradesTo_to_exactPostprocess degradationFine_stochastic_to_coarse

/-- The first partition really identifies source points 0 and 1. -/
theorem degradationPartitionA_same_01 :
    degradationPartitionA (0 : Fin 4) = degradationPartitionA (1 : Fin 4) := by
  decide

/-- The crossing partition distinguishes source points 0 and 1. -/
theorem degradationPartitionB_diff_01 :
    degradationPartitionB (0 : Fin 4) ≠ degradationPartitionB (1 : Fin 4) := by
  decide

/-- The crossing partition really identifies source points 0 and 2. -/
theorem degradationPartitionB_same_02 :
    degradationPartitionB (0 : Fin 4) = degradationPartitionB (2 : Fin 4) := by
  decide

/-- The first partition distinguishes source points 0 and 2. -/
theorem degradationPartitionA_diff_02 :
    degradationPartitionA (0 : Fin 4) ≠ degradationPartitionA (2 : Fin 4) := by
  decide

/-- No arbitrary exact rational postprocessor turns middle A into middle B. -/
theorem degradationMiddleA_not_to_middleB :
    ¬ FinKernel.ExactPostprocess degradationMiddleA degradationMiddleB := by
  intro h
  have hfiber := finKernel_exactPostprocess_dirac_preserves_fibers h
    degradationPartitionA_same_01
  exact degradationPartitionB_diff_01 hfiber

/-- No arbitrary exact rational postprocessor turns middle B into middle A. -/
theorem degradationMiddleB_not_to_middleA :
    ¬ FinKernel.ExactPostprocess degradationMiddleB degradationMiddleA := by
  intro h
  have hfiber := finKernel_exactPostprocess_dirac_preserves_fibers h
    degradationPartitionB_same_02
  exact degradationPartitionA_diff_02 hfiber

/-- Middle A cannot exactly reconstruct the maximally distinguishing observation. -/
theorem degradationMiddleA_not_to_fine :
    ¬ FinKernel.ExactPostprocess degradationMiddleA degradationFine := by
  intro h
  unfold degradationMiddleA degradationFine at h
  have hinj := finKernel_exactPostprocess_dirac_to_identity_injective h
  have h01 : (0 : Fin 4) = (1 : Fin 4) := hinj degradationPartitionA_same_01
  exact (by decide : (0 : Fin 4) ≠ (1 : Fin 4)) h01

/-- Middle B cannot exactly reconstruct the maximally distinguishing observation. -/
theorem degradationMiddleB_not_to_fine :
    ¬ FinKernel.ExactPostprocess degradationMiddleB degradationFine := by
  intro h
  unfold degradationMiddleB degradationFine at h
  have hinj := finKernel_exactPostprocess_dirac_to_identity_injective h
  have h02 : (0 : Fin 4) = (2 : Fin 4) := hinj degradationPartitionB_same_02
  exact (by decide : (0 : Fin 4) ≠ (2 : Fin 4)) h02

/-- The terminal coarse observation cannot reconstruct the maximally distinguishing observation. -/
theorem degradationCoarse_not_to_fine :
    ¬ FinKernel.ExactPostprocess degradationCoarse degradationFine := by
  intro h
  unfold degradationCoarse degradationFine at h
  have hinj := finKernel_exactPostprocess_dirac_to_identity_injective h
  have h01 : (0 : Fin 4) = (1 : Fin 4) := hinj (show
    degradationCoarseFn (0 : Fin 4) = degradationCoarseFn (1 : Fin 4) from rfl)
  exact (by decide : (0 : Fin 4) ≠ (1 : Fin 4)) h01

/-- The terminal observation cannot reconstruct middle A. -/
theorem degradationCoarse_not_to_middleA :
    ¬ FinKernel.ExactPostprocess degradationCoarse degradationMiddleA := by
  intro h
  unfold degradationCoarse degradationMiddleA at h
  have hfiber := finKernel_exactPostprocess_dirac_preserves_fibers h
    (show degradationCoarseFn (0 : Fin 4) = degradationCoarseFn (2 : Fin 4) from rfl)
  exact degradationPartitionA_diff_02 hfiber

/-- The terminal observation cannot reconstruct middle B. -/
theorem degradationCoarse_not_to_middleB :
    ¬ FinKernel.ExactPostprocess degradationCoarse degradationMiddleB := by
  intro h
  unfold degradationCoarse degradationMiddleB at h
  have hfiber := finKernel_exactPostprocess_dirac_preserves_fibers h
    (show degradationCoarseFn (0 : Fin 4) = degradationCoarseFn (1 : Fin 4) from rfl)
  exact degradationPartitionB_diff_01 hfiber

/-- The four Hasse edges admit stochastic-valid postprocessors. -/
theorem intrinsic_degradation_stochastic_edges_bundle :
    FinKernel.StochasticDegradesTo degradationFine degradationMiddleA ∧
      FinKernel.StochasticDegradesTo degradationFine degradationMiddleB ∧
      FinKernel.StochasticDegradesTo degradationMiddleA degradationCoarse ∧
      FinKernel.StochasticDegradesTo degradationMiddleB degradationCoarse := by
  exact ⟨degradationFine_stochastic_to_middleA,
    degradationFine_stochastic_to_middleB,
    degradationMiddleA_stochastic_to_coarse,
    degradationMiddleB_stochastic_to_coarse⟩

/-- Core exact-diamond package before indexing the heterogeneous observations by four nodes. -/
theorem intrinsic_degradation_core_bundle :
    FinKernel.ExactPostprocess degradationFine degradationMiddleA ∧
      FinKernel.ExactPostprocess degradationFine degradationMiddleB ∧
      FinKernel.ExactPostprocess degradationMiddleA degradationCoarse ∧
      FinKernel.ExactPostprocess degradationMiddleB degradationCoarse ∧
      (¬ FinKernel.ExactPostprocess degradationMiddleA degradationMiddleB) ∧
      (¬ FinKernel.ExactPostprocess degradationMiddleB degradationMiddleA) := by
  exact ⟨degradationFine_to_middleA,
    degradationFine_to_middleB,
    degradationMiddleA_to_coarse,
    degradationMiddleB_to_coarse,
    degradationMiddleA_not_to_middleB,
    degradationMiddleB_not_to_middleA⟩

/-- A finite observation packaged with its heterogeneous output-interface size. -/
structure PackedFinObservation (source : Nat) where
  outputSize : Nat
  kernel : FinKernel source outputSize

namespace PackedFinObservation

/-- Exact postprocessing between packaged observations on one fixed source. -/
def ExactPostprocess {source : Nat}
    (strong weak : PackedFinObservation source) : Prop :=
  FinKernel.ExactPostprocess strong.kernel weak.kernel

end PackedFinObservation

/-- The four heterogeneous observations indexed in the same order as `diamondCausalOrder`. -/
def degradationObservation (i : Fin 4) : PackedFinObservation 4 :=
  if i = (0 : Fin 4) then ⟨4, degradationFine⟩
  else if i = (1 : Fin 4) then ⟨2, degradationMiddleA⟩
  else if i = (2 : Fin 4) then ⟨2, degradationMiddleB⟩
  else ⟨1, degradationCoarse⟩

/-- Relation induced only by exact output postprocessing of the packaged kernels. -/
def IntrinsicDegradationRel (x y : Fin 4) : Prop :=
  PackedFinObservation.ExactPostprocess
    (degradationObservation x) (degradationObservation y)

@[simp] theorem intrinsicDegradationRel_00 :
    IntrinsicDegradationRel (0 : Fin 4) (0 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using
    finKernel_exactPostprocess_refl degradationFine

@[simp] theorem intrinsicDegradationRel_01 :
    IntrinsicDegradationRel (0 : Fin 4) (1 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationFine_to_middleA

@[simp] theorem intrinsicDegradationRel_02 :
    IntrinsicDegradationRel (0 : Fin 4) (2 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationFine_to_middleB

@[simp] theorem intrinsicDegradationRel_03 :
    IntrinsicDegradationRel (0 : Fin 4) (3 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationFine_to_coarse

@[simp] theorem not_intrinsicDegradationRel_10 :
    ¬ IntrinsicDegradationRel (1 : Fin 4) (0 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationMiddleA_not_to_fine

@[simp] theorem intrinsicDegradationRel_11 :
    IntrinsicDegradationRel (1 : Fin 4) (1 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using
    finKernel_exactPostprocess_refl degradationMiddleA

@[simp] theorem not_intrinsicDegradationRel_12 :
    ¬ IntrinsicDegradationRel (1 : Fin 4) (2 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationMiddleA_not_to_middleB

@[simp] theorem intrinsicDegradationRel_13 :
    IntrinsicDegradationRel (1 : Fin 4) (3 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationMiddleA_to_coarse

@[simp] theorem not_intrinsicDegradationRel_20 :
    ¬ IntrinsicDegradationRel (2 : Fin 4) (0 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationMiddleB_not_to_fine

@[simp] theorem not_intrinsicDegradationRel_21 :
    ¬ IntrinsicDegradationRel (2 : Fin 4) (1 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationMiddleB_not_to_middleA

@[simp] theorem intrinsicDegradationRel_22 :
    IntrinsicDegradationRel (2 : Fin 4) (2 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using
    finKernel_exactPostprocess_refl degradationMiddleB

@[simp] theorem intrinsicDegradationRel_23 :
    IntrinsicDegradationRel (2 : Fin 4) (3 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationMiddleB_to_coarse

@[simp] theorem not_intrinsicDegradationRel_30 :
    ¬ IntrinsicDegradationRel (3 : Fin 4) (0 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationCoarse_not_to_fine

@[simp] theorem not_intrinsicDegradationRel_31 :
    ¬ IntrinsicDegradationRel (3 : Fin 4) (1 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationCoarse_not_to_middleA

@[simp] theorem not_intrinsicDegradationRel_32 :
    ¬ IntrinsicDegradationRel (3 : Fin 4) (2 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using degradationCoarse_not_to_middleB

@[simp] theorem intrinsicDegradationRel_33 :
    IntrinsicDegradationRel (3 : Fin 4) (3 : Fin 4) := by
  simpa [IntrinsicDegradationRel, degradationObservation,
    PackedFinObservation.ExactPostprocess] using
    finKernel_exactPostprocess_refl degradationCoarse

/-- Every `Fin 4` node is one of the four concrete diamond indices. -/
theorem fin4_exhaustive (x : Fin 4) :
    x = (0 : Fin 4) ∨ x = (1 : Fin 4) ∨
      x = (2 : Fin 4) ∨ x = (3 : Fin 4) := by
  have hx := x.isLt
  have hv : x.1 = 0 ∨ x.1 = 1 ∨ x.1 = 2 ∨ x.1 = 3 := by
    grind
  rcases hv with h0 | h1 | h2 | h3
  · exact Or.inl (Fin.eq_of_val_eq h0)
  · exact Or.inr (Or.inl (Fin.eq_of_val_eq h1))
  · exact Or.inr (Or.inr (Or.inl (Fin.eq_of_val_eq h2)))
  · exact Or.inr (Or.inr (Or.inr (Fin.eq_of_val_eq h3)))

/--
The relation generated by exact kernel postprocessing is exactly the same
four-node diamond relation used by the order-only #2540/#2543 probes.
The diamond relation is a theorem here, not an input to `IntrinsicDegradationRel`.
-/
theorem intrinsic_degradation_rel_iff_diamond (x y : Fin 4) :
    IntrinsicDegradationRel x y ↔ diamondCausalOrder.rel x y := by
  rcases fin4_exhaustive x with hx | hx | hx | hx <;>
    subst x <;>
    rcases fin4_exhaustive y with hy | hy | hy | hy <;>
    subst y <;>
    simp [diamondCausalOrder, diamondCausalRel]

/-- The intrinsic kernel relation is therefore non-total on its four selected observations. -/
theorem intrinsic_degradation_not_total :
    ¬ (∀ x y : Fin 4, IntrinsicDegradationRel x y ∨ IntrinsicDegradationRel y x) := by
  intro h
  rcases h (1 : Fin 4) (2 : Fin 4) with h12 | h21
  · exact not_intrinsicDegradationRel_12 h12
  · exact not_intrinsicDegradationRel_21 h21

/-- Observer-family realization formulated directly against the kernel-derived relation. -/
def ObserverFamilyRealizesIntrinsic {r m : Nat}
    (time : Fin r → Fin 4 → Fin m) : Prop :=
  ∀ x y, IntrinsicDegradationRel x y ↔ ObserverInvariantRel time x y

/-- The two #2543 scalar chains exactly realize the kernel-derived degradation relation. -/
theorem two_chain_observers_exactly_realize_intrinsic_degradation :
    ObserverFamilyRealizesIntrinsic diamondObserverTime := by
  intro x y
  calc
    IntrinsicDegradationRel x y ↔ diamondCausalOrder.rel x y :=
      intrinsic_degradation_rel_iff_diamond x y
    _ ↔ ObserverInvariantRel diamondObserverTime x y :=
      two_chain_observers_exactly_realize_diamond x y

/-- One scalar observer cannot exactly realize the intrinsically generated diamond relation. -/
theorem intrinsic_degradation_requires_more_than_one_observer (m : Nat) :
    ¬ ∃ time : Fin 1 → Fin 4 → Fin m,
      ObserverFamilyRealizesIntrinsic time := by
  intro h
  rcases h with ⟨time, htime⟩
  apply diamond_requires_more_than_one_observer m
  refine ⟨time, ?_⟩
  intro x y
  calc
    diamondCausalOrder.rel x y ↔ IntrinsicDegradationRel x y :=
      (intrinsic_degradation_rel_iff_diamond x y).symm
    _ ↔ ObserverInvariantRel time x y := htime x y

/-- Final owner-local bundle for #2547. -/
theorem intrinsic_kernel_degradation_diamond_bundle :
    (∀ x y, IntrinsicDegradationRel x y ↔ diamondCausalOrder.rel x y) ∧
      ObserverFamilyRealizesIntrinsic diamondObserverTime ∧
      (¬ ∃ time : Fin 1 → Fin 4 → Fin 4, ObserverFamilyRealizesIntrinsic time) ∧
      FinKernel.Valid degradationFine ∧
      FinKernel.Valid degradationMiddleA ∧
      FinKernel.Valid degradationMiddleB ∧
      FinKernel.Valid degradationCoarse := by
  exact ⟨intrinsic_degradation_rel_iff_diamond,
    two_chain_observers_exactly_realize_intrinsic_degradation,
    intrinsic_degradation_requires_more_than_one_observer 4,
    intrinsic_degradation_nodes_valid⟩

end RelayTheory
