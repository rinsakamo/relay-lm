import RelayTheory.IntrinsicKernelDegradation
import RelayTheory.HiddenCarrierReturn

namespace RelayTheory

namespace RevivalBackflowSeparation

/--
Arbitrary output postprocessing cannot separate two source rows that are already
identical at the declared intermediate cut.  No stochastic-validity assumption
is needed: this is an exact signed-rational statement about the current finite
kernel surface.
-/
theorem finKernel_postprocess_preserves_equal_source_rows
    {a q r : Nat}
    (mid : FinKernel a q) (post : FinKernel q r)
    {x y : Fin a}
    (hxy : ∀ z : Fin q, mid x z = mid y z)
    (out : Fin r) :
    FinKernel.compose post mid x out =
      FinKernel.compose post mid y out := by
  unfold FinKernel.compose
  apply sumFin_congr
  intro z
  rw [hxy z]

/--
Exact downstream factorization therefore preserves every source-row equality
already present at the intermediate cut.
-/
theorem finKernel_exactPostprocess_preserves_equal_source_rows
    {a q r : Nat}
    {mid : FinKernel a q} {later : FinKernel a r}
    (hfactor : FinKernel.ExactPostprocess mid later)
    {x y : Fin a}
    (hxy : ∀ z : Fin q, mid x z = mid y z)
    (out : Fin r) :
    later x out = later y out := by
  rcases hfactor with ⟨post, hpost⟩
  rw [← hpost]
  exact finKernel_postprocess_preserves_equal_source_rows mid post hxy out

/--
Deterministic specialization, deliberately reusing #2549's stronger fiber
invariant rather than rebuilding deterministic collision algebra here.
-/
theorem finKernel_exactPostprocess_dirac_preserves_identification
    {a q r : Nat}
    {f : Fin a → Fin q} {g : Fin a → Fin r}
    (hfactor :
      FinKernel.ExactPostprocess (FinKernel.dirac f) (FinKernel.dirac g))
    {x y : Fin a}
    (hxy : f x = f y) :
    g x = g y :=
  finKernel_exactPostprocess_dirac_preserves_fibers hfactor hxy

/-- The collapsed binary visible map really is non-injective. -/
theorem constZero2_not_injective :
    ¬ Function.Injective HiddenCarrierReturn.constZero2 := by
  intro hinj
  have h01 : (0 : Fin 2) = (1 : Fin 2) :=
    hinj (show
      HiddenCarrierReturn.constZero2 (0 : Fin 2) =
        HiddenCarrierReturn.constZero2 (1 : Fin 2) from rfl)
  exact (by decide : (0 : Fin 2) ≠ (1 : Fin 2)) h01

/--
Even an arbitrary signed-rational exact postprocessor cannot reconstruct binary
identity from the collapsed constant observation.
-/
theorem constZero2_not_exactPostprocess_identity :
    ¬ FinKernel.ExactPostprocess
      (FinKernel.dirac HiddenCarrierReturn.constZero2)
      (FinKernel.identity 2) := by
  intro h
  exact constZero2_not_injective
    (finKernel_exactPostprocess_dirac_to_identity_injective h)

/-- The two binary source rows at the #2559 visible middle cut are identical. -/
theorem preparedObs1_equal_source_rows
    (out : Fin 2) :
    HiddenCarrierReturn.preparedObs1 (0 : Fin 2) out =
      HiddenCarrierReturn.preparedObs1 (1 : Fin 2) out := by
  rw [HiddenCarrierReturn.preparedObs1_eq_constZero]
  simp [FinKernel.dirac, HiddenCarrierReturn.constZero2]

/--
The informative #2559 return cannot factor through the collapsed visible cut
alone.  The proof uses only exact output postprocessing, so stochastic validity
is not the obstruction.
-/
theorem preparedObs1_not_exactPostprocess_obs2 :
    ¬ FinKernel.ExactPostprocess
      HiddenCarrierReturn.preparedObs1
      HiddenCarrierReturn.preparedObs2 := by
  intro hfactor
  have heq :=
    finKernel_exactPostprocess_preserves_equal_source_rows
      hfactor preparedObs1_equal_source_rows (0 : Fin 2)
  rw [HiddenCarrierReturn.preparedObs2_eq_obs0,
    HiddenCarrierReturn.preparedObs0_eq_identity] at heq
  simp [FinKernel.identity] at heq

/--
Explicit fresh source reinjection.  The declared collapsed value is accepted as
an argument but the later value is supplied anew by the source side input.
This is a negative control, not a carrier transport law.
-/
def reinjectFromSource (_declared source : Fin 2) : Fin 2 := source

/-- The fresh side input is source-sensitive even at one fixed declared cut. -/
theorem reinjectFromSource_source_sensitive :
    reinjectFromSource (0 : Fin 2) (0 : Fin 2) ≠
      reinjectFromSource (0 : Fin 2) (1 : Fin 2) := by
  simp [reinjectFromSource]

/-- Source-to-visible map after explicit fresh reinjection. -/
def reinjectedVisible (source : Fin 2) : Fin 2 :=
  reinjectFromSource (HiddenCarrierReturn.constZero2 source) source

@[simp] theorem reinjectedVisible_apply (source : Fin 2) :
    reinjectedVisible source = source := rfl

/-- Initial endpoint of the reinjection control. -/
def reinjectedObs0 : FinKernel 2 2 := HiddenCarrierReturn.preparedObs0

/-- Collapsed intermediate endpoint of the reinjection control. -/
def reinjectedObs1 : FinKernel 2 2 := HiddenCarrierReturn.preparedObs1

/-- Later endpoint supplied through the explicit source side input. -/
def reinjectedObs2 : FinKernel 2 2 := FinKernel.dirac reinjectedVisible

/--
Fresh reinjection reproduces exactly the same later observer channel as the
hidden-carrier fixture, despite using a distinct declared mechanism.
-/
theorem reinjectedObs2_eq_preparedObs2 :
    reinjectedObs2 = HiddenCarrierReturn.preparedObs2 := by
  funext x y
  simp [reinjectedObs2, reinjectedVisible, reinjectFromSource,
    HiddenCarrierReturn.preparedObs2, FinKernel.dirac]

/-- The full three observer endpoints match the #2559 leave-and-return shape. -/
theorem reinjection_endpoint_shape_matches_hidden_carrier :
    reinjectedObs0 = HiddenCarrierReturn.preparedObs0 ∧
    reinjectedObs1 = HiddenCarrierReturn.preparedObs1 ∧
    reinjectedObs2 = HiddenCarrierReturn.preparedObs2 := by
  exact ⟨rfl, rfl, reinjectedObs2_eq_preparedObs2⟩

/--
The merged #2559 intervention witness certifies a stronger fact than endpoint
revival: a hidden-only change preserves the intermediate visible observation
while changing the later visible result.
-/
theorem hiddenCarrier_intervention_lineage :
    HiddenCarrierReturn.visible
        (HiddenCarrierReturn.resetHidden
          (HiddenCarrierReturn.step
            (HiddenCarrierReturn.embed (1 : Fin 2)))) =
      HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step
          (HiddenCarrierReturn.embed (1 : Fin 2))) ∧
    HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step
          (HiddenCarrierReturn.step
            (HiddenCarrierReturn.embed (1 : Fin 2)))) ≠
      HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step
          (HiddenCarrierReturn.resetHidden
            (HiddenCarrierReturn.step
              (HiddenCarrierReturn.embed (1 : Fin 2)))) ) := by
  exact ⟨
    HiddenCarrierReturn.resetHidden_preserves_visible _,
    HiddenCarrierReturn.hidden_carrier_controls_future_visible⟩

/--
Acceptance bundle for the bounded revival/backflow discriminator.

The same coarse endpoint revival can arise from an ordinary hidden carrier or
from explicit fresh source reinjection.  The collapsed visible cut cannot by
itself generate the source-dependent return; #2559 additionally supplies the
intervention-certified hidden-carrier lineage.  Nothing here requires hidden
spacetime or an additional timelike dimension.
-/
theorem revivalBackflowSeparation_bundle :
    (¬ FinKernel.ExactPostprocess
      HiddenCarrierReturn.preparedObs1
      HiddenCarrierReturn.preparedObs2) ∧
    (reinjectedObs0 = HiddenCarrierReturn.preparedObs0 ∧
      reinjectedObs1 = HiddenCarrierReturn.preparedObs1 ∧
      reinjectedObs2 = HiddenCarrierReturn.preparedObs2) ∧
    reinjectFromSource (0 : Fin 2) (0 : Fin 2) ≠
      reinjectFromSource (0 : Fin 2) (1 : Fin 2) ∧
    HiddenCarrierReturn.visible
        (HiddenCarrierReturn.resetHidden
          (HiddenCarrierReturn.step
            (HiddenCarrierReturn.embed (1 : Fin 2)))) =
      HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step
          (HiddenCarrierReturn.embed (1 : Fin 2))) ∧
    HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step
          (HiddenCarrierReturn.step
            (HiddenCarrierReturn.embed (1 : Fin 2)))) ≠
      HiddenCarrierReturn.visible
        (HiddenCarrierReturn.step
          (HiddenCarrierReturn.resetHidden
            (HiddenCarrierReturn.step
              (HiddenCarrierReturn.embed (1 : Fin 2)))) ) := by
  exact ⟨
    preparedObs1_not_exactPostprocess_obs2,
    reinjection_endpoint_shape_matches_hidden_carrier,
    reinjectFromSource_source_sensitive,
    hiddenCarrier_intervention_lineage.1,
    hiddenCarrier_intervention_lineage.2⟩

end RevivalBackflowSeparation

end RelayTheory
