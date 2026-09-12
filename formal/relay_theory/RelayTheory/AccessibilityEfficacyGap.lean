import RelayTheory.BoundedDecoderFactorization

namespace RelayTheory

/--
A neutral finite-task comparison predicate.  It says only that a candidate
policy is never worse than a baseline under the declared utility and is
strictly better on at least one history.  It is not a cognitive primitive or a
universal definition of efficacy.
-/
def StrictPointwiseUtilityImprovement
    {History Action : Type}
    (utility : History → Action → Nat)
    (candidate baseline : History → Action) : Prop :=
  (∀ h, utility h (baseline h) ≤ utility h (candidate h)) ∧
  ∃ h, utility h (baseline h) < utility h (candidate h)

/-- No policy is a strict pointwise utility improvement over itself. -/
theorem strictPointwiseUtilityImprovement_irrefl
    {History Action : Type}
    (utility : History → Action → Nat)
    (policy : History → Action) :
    ¬ StrictPointwiseUtilityImprovement utility policy policy := by
  intro hImprove
  rcases hImprove.2 with ⟨h, hStrict⟩
  exact (Nat.lt_irrefl _ hStrict)

/-- Zero-cost one-element decoder family for the accessibility fixture. -/
def efficacyIdentityCost (_ : Unit) : Nat := 0

/-- The only decoder simply exposes the Boolean carrier it receives. -/
def efficacyIdentityRun (_ : Unit) (x : Bool) : Bool := x

/-- The declared finite query asks for the Boolean history distinction itself. -/
def efficacyBoolQuery (h : Bool) : Bool := h

/-- The representation preserves that distinction exactly. -/
def efficacyBoolRepresentation (h : Bool) : Bool := h

/-- A realized policy that ignores the accessible distinction. -/
def efficacyIgnoredPolicy (_ : Bool) : Bool := false

/-- One unit of utility exactly when the selected action matches the history. -/
def efficacyMatchUtility (h action : Bool) : Nat :=
  if action = h then 1 else 0

/-- The Boolean distinction is exactly accessible at zero declared decoder cost. -/
theorem efficacyBool_accessible :
    AccessibleAt efficacyIdentityCost efficacyIdentityRun 0
      efficacyBoolQuery efficacyBoolRepresentation := by
  refine ⟨(), ?_, ?_⟩
  · simp [efficacyIdentityCost]
  · intro h
    rfl

/--
Accessibility is existential over an admitted decoder and therefore does not
force the realized policy to gain task utility from the accessible distinction.
-/
theorem accessibility_does_not_imply_realizedTaskEfficacy_fixture :
    AccessibleAt efficacyIdentityCost efficacyIdentityRun 0
        efficacyBoolQuery efficacyBoolRepresentation ∧
    ¬ StrictPointwiseUtilityImprovement
        efficacyMatchUtility efficacyIgnoredPolicy efficacyIgnoredPolicy := by
  exact ⟨efficacyBool_accessible,
    strictPointwiseUtilityImprovement_irrefl
      efficacyMatchUtility efficacyIgnoredPolicy⟩

/--
Instrumented baseline: the internal trace is constant while the task action is
already exact.
-/
def efficacyTraceBaseline (h : Bool) : Bool × Bool :=
  (false, h)

/--
Instrumented treatment: the internal trace explicitly tracks the query while
the task action remains the same exact action as the baseline.
-/
def efficacyTraceTreatment (h : Bool) : Bool × Bool :=
  (h, h)

/-- Task utility observes only the declared action component of the instrumented output. -/
def efficacyTraceTaskUtility (h : Bool) (out : Bool × Bool) : Nat :=
  if out.2 = h then 1 else 0

/-- The treatment's internal trace explicitly carries the queried distinction. -/
theorem efficacyTraceTreatment_tracks_query (h : Bool) :
    (efficacyTraceTreatment h).1 = efficacyBoolQuery h := by
  rfl

/-- The instrumented internal trace really changes relative to baseline on one history. -/
theorem efficacyTraceTreatment_changes_internal_trace :
    (efficacyTraceTreatment true).1 ≠ (efficacyTraceBaseline true).1 := by
  simp [efficacyTraceTreatment, efficacyTraceBaseline]

/-- Internal trace uptake leaves declared task utility unchanged on every history. -/
theorem efficacyTrace_taskUtility_equal (h : Bool) :
    efficacyTraceTaskUtility h (efficacyTraceTreatment h) =
      efficacyTraceTaskUtility h (efficacyTraceBaseline h) := by
  cases h <;>
    rfl

/--
Explicit internal processing of the accessible distinction need not yield an
incremental utility improvement when the baseline already realizes the same
task action.
-/
theorem internalUptake_does_not_imply_incrementalTaskEfficacy_fixture :
    (∀ h, (efficacyTraceTreatment h).1 = efficacyBoolQuery h) ∧
    (efficacyTraceTreatment true).1 ≠ (efficacyTraceBaseline true).1 ∧
    (∀ h,
      efficacyTraceTaskUtility h (efficacyTraceTreatment h) =
        efficacyTraceTaskUtility h (efficacyTraceBaseline h)) ∧
    ¬ StrictPointwiseUtilityImprovement
        efficacyTraceTaskUtility efficacyTraceTreatment efficacyTraceBaseline := by
  refine ⟨efficacyTraceTreatment_tracks_query,
    efficacyTraceTreatment_changes_internal_trace,
    efficacyTrace_taskUtility_equal, ?_⟩
  intro hImprove
  rcases hImprove.2 with ⟨h, hStrict⟩
  cases h <;>
    simp [efficacyTraceTaskUtility, efficacyTraceTreatment,
      efficacyTraceBaseline] at hStrict

/--
Neutral same-task exact-realization cost comparison.  Both declared decoders
must realize the same query exactly; the first is then required to have lower
declared cost.  This is a finite comparison relation, not a universal
complexity or efficacy metric.
-/
def StrictExactCostAdvantage
    {History Carrier Output Decoder : Type}
    (cost : Decoder → Nat)
    (run : Decoder → Carrier → Output)
    (query : History → Output)
    (betterRep worseRep : History → Carrier)
    (betterDecoder worseDecoder : Decoder) : Prop :=
  (∀ h, run betterDecoder (betterRep h) = query h) ∧
  (∀ h, run worseDecoder (worseRep h) = query h) ∧
  cost betterDecoder < cost worseDecoder

/--
In the existing XOR fixture, direct projection realizes the easy coordinate at
cost zero while XOR realizes the information-equivalent mixed coordinate at
cost one, with both exactly solving the same first-bit query.
-/
theorem decoderEasy_strictExactCostAdvantage_over_mixed :
    StrictExactCostAdvantage
      pairDecoderCost pairDecoderRun decoderFirstBitQuery
      decoderEasyRepresentation decoderMixedRepresentation
      PairDecoder.first PairDecoder.xor := by
  refine ⟨?_, ?_, ?_⟩
  · intro h
    rcases h with ⟨a, b⟩
    rfl
  · intro h
    rcases h with ⟨a, b⟩
    cases a <;> cases b <;> rfl
  · simp [pairDecoderCost]

/--
Same exact semantic capability and the same history partition can coexist with
a strict declared decoder-cost difference.
-/
theorem sameSemanticCapability_canDifferOnDeclaredCostFrontier_fixture :
    RepresentationEquivalent
        decoderEasyRepresentation decoderMixedRepresentation ∧
    RepresentationRefines
        decoderEasyRepresentation decoderFirstBitQuery ∧
    RepresentationRefines
        decoderMixedRepresentation decoderFirstBitQuery ∧
    StrictExactCostAdvantage
      pairDecoderCost pairDecoderRun decoderFirstBitQuery
      decoderEasyRepresentation decoderMixedRepresentation
      PairDecoder.first PairDecoder.xor := by
  exact ⟨decoder_easy_mixed_representationEquivalent,
    decoderEasyRepresentation_refines_firstBitQuery,
    decoderMixedRepresentation_refines_firstBitQuery,
    decoderEasy_strictExactCostAdvantage_over_mixed⟩

end RelayTheory
