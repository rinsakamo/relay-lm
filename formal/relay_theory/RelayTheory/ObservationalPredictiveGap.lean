import RelayTheory.ProbeRelative

namespace RelayTheory

namespace FinKernel

/-- The observer obtained by admitting every probe from either declared family. -/
def unionProbes {n : Nat}
    (P Q : ProbeFamily n) : ProbeFamily n :=
  fun obs => P obs ∨ Q obs

/--
Neutral pairwise gap: two alternatives are equivalent for the declared current
probe family but not for the declared downstream/predictive probe family.
No temporal coordinate or hidden-object ontology appears in the definition.
-/
def ObservationPredictionGap {m n : Nat}
    (current future : ProbeFamily n)
    (f g : FinKernel m n) : Prop :=
  ProbeEq current f g ∧ ¬ ProbeEq future f g

end FinKernel

/-- Equivalence for the union observer is exactly equivalence for both families. -/
theorem finKernel_probeEq_union_iff {m n : Nat}
    {P Q : FinKernel.ProbeFamily n}
    {f g : FinKernel m n} :
    FinKernel.ProbeEq (FinKernel.unionProbes P Q) f g ↔
      FinKernel.ProbeEq P f g ∧ FinKernel.ProbeEq Q f g := by
  constructor
  · intro h
    constructor
    · intro obs hP
      exact h obs (Or.inl hP)
    · intro obs hQ
      exact h obs (Or.inr hQ)
  · rintro ⟨hP, hQ⟩ obs hUnion
    rcases hUnion with hPobs | hQobs
    · exact hP obs hPobs
    · exact hQ obs hQobs

/--
If every declared future/context probe is already available to the current
observer, current equivalence is sufficient for future equivalence.
-/
theorem finKernel_probeEq_future_of_current
    {m n : Nat}
    {current future : FinKernel.ProbeFamily n}
    {f g : FinKernel m n}
    (hsub : ∀ obs, future obs → current obs)
    (hcurrent : FinKernel.ProbeEq current f g) :
    FinKernel.ProbeEq future f g := by
  exact finKernel_probeEq_antitone hsub hcurrent

/-- Containment of all future probes rules out the declared pairwise gap. -/
theorem finKernel_no_observationPredictionGap_of_future_subfamily
    {m n : Nat}
    {current future : FinKernel.ProbeFamily n}
    {f g : FinKernel m n}
    (hsub : ∀ obs, future obs → current obs) :
    ¬ FinKernel.ObservationPredictionGap current future f g := by
  intro hgap
  exact hgap.2 (finKernel_probeEq_future_of_current hsub hgap.1)

/--
Any declared gap disappears as an equivalence claim once the current observer is
enlarged to include the distinguishing future/context family.
-/
theorem finKernel_observationPredictionGap_exposed_by_union
    {m n : Nat}
    {current future : FinKernel.ProbeFamily n}
    {f g : FinKernel m n}
    (hgap : FinKernel.ObservationPredictionGap current future f g) :
    FinKernel.ProbeEq current f g ∧
      ¬ FinKernel.ProbeEq (FinKernel.unionProbes current future) f g := by
  refine ⟨hgap.1, ?_⟩
  intro hunion
  have hfuture := (finKernel_probeEq_union_iff).1 hunion
  exact hgap.2 hfuture.2

/-- Current coarse observer family for the explicit three-state fixture. -/
def finKernelCurrentMergeFamily : FinKernel.ProbeFamily 3 :=
  FinKernel.singletonProbe ⟨2, finKernelMerge01⟩

/--
Downstream context that first applies the ordinary deterministic state map and
then uses the same coarse observation.
-/
def finKernelDownstreamMergeObservation : FinKernel 3 2 :=
  FinKernel.compose finKernelMerge01 finKernelMoveOneToTwo

/-- Predictive/context family containing exactly the composed downstream probe. -/
def finKernelDownstreamMergeFamily : FinKernel.ProbeFamily 3 :=
  FinKernel.singletonProbe ⟨2, finKernelDownstreamMergeObservation⟩

/-- The restricted current observer identifies the two deterministic sources. -/
theorem finKernel_currentMergeFamily_equivalent :
    FinKernel.ProbeEq finKernelCurrentMergeFamily
      finKernelZero3 finKernelOne3 := by
  unfold finKernelCurrentMergeFamily
  exact finKernel_singleton_probe_postcomposition_counterexample.1

/--
The composed downstream observation distinguishes the same two source
alternatives on the original cut.
-/
theorem finKernel_downstreamMergeObservation_distinguishes :
    ¬ FinKernel.ObservedEq finKernelDownstreamMergeObservation
      finKernelZero3 finKernelOne3 := by
  intro h
  apply finKernel_fixed_probe_not_postcomposition_stable
  unfold FinKernel.ObservedEq at h ⊢
  have hzero :
      FinKernel.compose finKernelMerge01
          (FinKernel.compose finKernelMoveOneToTwo finKernelZero3) =
        FinKernel.compose finKernelDownstreamMergeObservation finKernelZero3 := by
    exact finKernel_compose_associative
      finKernelZero3 finKernelMoveOneToTwo finKernelMerge01
  have hone :
      FinKernel.compose finKernelMerge01
          (FinKernel.compose finKernelMoveOneToTwo finKernelOne3) =
        FinKernel.compose finKernelDownstreamMergeObservation finKernelOne3 := by
    exact finKernel_compose_associative
      finKernelOne3 finKernelMoveOneToTwo finKernelMerge01
  rw [hzero, hone]
  exact h

/-- The declared downstream singleton family therefore distinguishes the pair. -/
theorem finKernel_downstreamMergeFamily_not_equivalent :
    ¬ FinKernel.ProbeEq finKernelDownstreamMergeFamily
      finKernelZero3 finKernelOne3 := by
  unfold finKernelDownstreamMergeFamily
  rw [finKernel_probeEq_singleton_iff_observedEq]
  exact finKernel_downstreamMergeObservation_distinguishes

/--
Concrete Level-B witness: current observational equivalence is strictly coarser
than the declared downstream/context equivalence for this ordinary finite model.
-/
theorem finKernel_observationalPredictiveGap_fixture :
    FinKernel.ObservationPredictionGap
      finKernelCurrentMergeFamily finKernelDownstreamMergeFamily
      finKernelZero3 finKernelOne3 := by
  exact ⟨finKernel_currentMergeFamily_equivalent,
    finKernel_downstreamMergeFamily_not_equivalent⟩

/-- Enlarging the current observer with the downstream probe exposes the pair. -/
theorem finKernel_observationalPredictiveGap_enlargement_fixture :
    FinKernel.ProbeEq finKernelCurrentMergeFamily
      finKernelZero3 finKernelOne3 ∧
    ¬ FinKernel.ProbeEq
      (FinKernel.unionProbes
        finKernelCurrentMergeFamily finKernelDownstreamMergeFamily)
      finKernelZero3 finKernelOne3 := by
  exact finKernel_observationPredictionGap_exposed_by_union
    finKernel_observationalPredictiveGap_fixture

/--
Acceptance bundle for the observational/predictive gap transaction.
It establishes only a finite probe-family quotient gap and observer-enlargement
control, not a hidden object, extra time, or a physical ontology.
-/
theorem finKernel_observationalPredictiveGap_bundle :
    FinKernel.Valid finKernelZero3 ∧
    FinKernel.Valid finKernelOne3 ∧
    FinKernel.Valid finKernelMerge01 ∧
    FinKernel.Valid finKernelMoveOneToTwo ∧
    FinKernel.ObservationPredictionGap
      finKernelCurrentMergeFamily finKernelDownstreamMergeFamily
      finKernelZero3 finKernelOne3 ∧
    ¬ FinKernel.ProbeEq
      (FinKernel.unionProbes
        finKernelCurrentMergeFamily finKernelDownstreamMergeFamily)
      finKernelZero3 finKernelOne3 := by
  exact ⟨finKernel_zero3_valid,
    finKernel_one3_valid,
    finKernel_merge01_valid,
    finKernel_moveOneToTwo_valid,
    finKernel_observationalPredictiveGap_fixture,
    finKernel_observationalPredictiveGap_enlargement_fixture.2⟩

end RelayTheory
