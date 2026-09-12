import RelayTheory.RepresentationFactorization

namespace RelayTheory

/--
Pair a complete constituent description with a macro that is deterministically
derived from that same description.

This is a neutral functional construction.  It does not assign cognitive,
intelligence, causal, or ontological status to either coordinate.
-/
def macroEnriched {Constituent Macro : Type}
    (phi : Constituent → Macro) (z : Constituent) : Constituent × Macro :=
  (z, phi z)

/--
Compile any consumer of a constituent-plus-derived-macro pair into a consumer
of the constituent description alone.

The theorem family below is exact and unrestricted.  It does not say that the
compiled consumer has the same description length, decoder class, sample cost,
latency, or other bounded-resource cost as an implementation that is handed the
macro explicitly.
-/
def compileMacroPredictor {Constituent Macro Output : Type}
    (phi : Constituent → Macro)
    (predict : Constituent × Macro → Output) : Constituent → Output :=
  fun z => predict (macroEnriched phi z)

/--
The deterministic enrichment itself factors exactly through the complete
constituent description.
-/
theorem macroEnriched_factors_through_constituents
    {Constituent Macro : Type}
    (phi : Constituent → Macro) :
    FactorsThrough (fun z : Constituent => z) (macroEnriched phi) := by
  refine ⟨macroEnriched phi, ?_⟩
  intro z
  rfl

/-- Pointwise exactness of compiling an enriched predictor back to constituents. -/
theorem macroEnriched_predictor_compiles
    {Constituent Macro Output : Type}
    (phi : Constituent → Macro)
    (predict : Constituent × Macro → Output)
    (z : Constituent) :
    predict (macroEnriched phi z) = compileMacroPredictor phi predict z := by
  rfl

/--
Any deterministic post-processing of the enriched pair also factors exactly
through the complete constituent description.
-/
theorem deterministicMacro_postprocessing_factors_through_constituents
    {Constituent Macro Output : Type}
    (phi : Constituent → Macro)
    (predict : Constituent × Macro → Output) :
    FactorsThrough
      (fun z : Constituent => z)
      (fun z => predict (macroEnriched phi z)) := by
  refine ⟨compileMacroPredictor phi predict, ?_⟩
  intro z
  rfl

/--
Existential form of deterministic macro elimination for exact prediction: an
arbitrary enriched predictor always has a constituent-only predictor with the
same pointwise output.
-/
theorem deterministicMacro_predictor_reduces_to_constituents
    {Constituent Macro Output : Type}
    (phi : Constituent → Macro)
    (predict : Constituent × Macro → Output) :
    ∃ predictZ : Constituent → Output,
      ∀ z, predict (macroEnriched phi z) = predictZ z := by
  exact ⟨compileMacroPredictor phi predict, fun z => rfl⟩

/--
If an enriched predictor exactly realizes a declared target, then a
constituent-only predictor exactly realizes the same target.

This proves only deterministic functional factorization.  It does not establish
an information-theoretic equality, finite-sample equivalence, bounded-decoder
cost equivalence, or causal eliminability of a scientifically useful macro.
-/
theorem exactTarget_with_deterministicMacro_reduces_to_constituents
    {Constituent Macro Output : Type}
    (phi : Constituent → Macro)
    (predict : Constituent × Macro → Output)
    (target : Constituent → Output)
    (hExact : ∀ z, predict (macroEnriched phi z) = target z) :
    ∃ predictZ : Constituent → Output,
      ∀ z, predictZ z = target z := by
  refine ⟨compileMacroPredictor phi predict, ?_⟩
  intro z
  exact hExact z

/--
A declared query for the finite compression control.  It depends only on the
first constituent bit, while the second bit is irrelevant to this query.
-/
def macroCompressionQuery (h : Bool × Bool) : Bool :=
  boolComplement (firstBit h)

/--
The first-bit macro exactly determines the declared query, despite being
many-to-one on the complete two-bit constituent description.
-/
theorem firstBitMacro_factors_to_compressionQuery :
    FactorsThrough firstBit macroCompressionQuery := by
  refine ⟨boolComplement, ?_⟩
  intro h
  rfl

/-- The finite macro really discards a constituent distinction. -/
theorem firstBitMacro_is_manyToOne :
    (false, false) ≠ (false, true) ∧
    firstBit (false, false) = firstBit (false, true) := by
  constructor
  · simp
  · rfl

/--
Positive control: a deterministic many-to-one macro can still be an exact
sufficient representation for a declared query.  Thus no-new-distinction does
not imply no compression value.
-/
theorem deterministicMacro_compression_fixture :
    FactorsThrough firstBit macroCompressionQuery ∧
    (false, false) ≠ (false, true) ∧
    firstBit (false, false) = firstBit (false, true) := by
  exact ⟨firstBitMacro_factors_to_compressionQuery, firstBitMacro_is_manyToOne⟩

end RelayTheory
