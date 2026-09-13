import RelayTheory.FullFutureResponseSignatures

namespace RelayTheory

namespace FinKernel

/--
A generated future continuation carried together with the proof that it belongs
 to the declared finite sequential closure.
-/
structure GeneratedContinuationIndex {n : Nat}
    (K : FutureContextFamily n) where
  kernel : FinKernel n n
  generated : GeneratedContext K kernel

/-- Generated-continuation indices are determined by their literal kernels. -/
theorem GeneratedContinuationIndex.ext_kernel {n : Nat}
    {K : FutureContextFamily n}
    {i j : GeneratedContinuationIndex K}
    (h : i.kernel = j.kernel) : i = j := by
  cases i with
  | mk ik ih =>
      cases j with
      | mk jk jh =>
          cases h
          rfl

/--
Literal right shift of the generated-future index by one generated continuation.
This is an index operation only; it does not mention response semantics or the
existing `FutureDerivative` operator.
-/
def GeneratedRightShift {n : Nat}
    {K : FutureContextFamily n}
    (l : FinKernel n n) (hl : GeneratedContext K l) :
    GeneratedContinuationIndex K → GeneratedContinuationIndex K :=
  fun i =>
    { kernel := compose i.kernel l
      generated := GeneratedContext.seq hl i.generated }

/--
Generic precomposition/reindexing of the complete future-response carrier by an
arbitrary generated-index map.  No action quotient or derivative structure is
used in this definition.
-/
def ReindexFullFutureResponse {n : Nat}
    {P : ProbeFamily n} {K : FutureContextFamily n}
    (r : GeneratedContinuationIndex K → GeneratedContinuationIndex K)
    (s : FullFutureResponseSpace P K) : FullFutureResponseSpace P K :=
  fun c hc m f obs hobs x z =>
    let shifted := r { kernel := c, generated := hc }
    s shifted.kernel shifted.generated m f obs hobs x z

/-- An endomorphism of the exact full-future response carrier. -/
abbrev FullFutureResponseOperator {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n) :=
  FullFutureResponseSpace P K → FullFutureResponseSpace P K

/-- Pointwise extensional equality of response-space operators. -/
def FullFutureResponseOperatorEq {n : Nat}
    {P : ProbeFamily n} {K : FutureContextFamily n}
    (op op' : FullFutureResponseOperator P K) : Prop :=
  ∀ s, FullFutureResponseSpaceEq (op s) (op' s)

/--
The scalar evaluation law that characterizes residual action by a generated
future continuation.  The law is stated without referring to
`FutureDerivative`.
-/
def ResidualEvaluationLaw {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (l : FinKernel n n) (hl : GeneratedContext K l)
    (op : FullFutureResponseOperator P K) : Prop :=
  ∀ s c (hc : GeneratedContext K c) m f obs (hobs : P obs) x z,
    op s c hc m f obs hobs x z =
      s (compose c l) (GeneratedContext.seq hl hc)
        m f obs hobs x z

/--
Semantic equality of canonical residual reindexing actions on the image of
literal full-future signatures.
-/
def CanonicalResidualEqOnSemanticSignatures {n : Nat}
    (P : ProbeFamily n) (K : FutureContextFamily n)
    (l l' : FinKernel n n)
    (hl : GeneratedContext K l) (hl' : GeneratedContext K l') : Prop :=
  ∀ k : FinKernel n n,
    FullFutureResponseSpaceEq
      (ReindexFullFutureResponse (GeneratedRightShift l hl)
        (FullFutureResponse P K k))
      (ReindexFullFutureResponse (GeneratedRightShift l' hl')
        (FullFutureResponse P K k))

end FinKernel

/-- The canonical index reindexing satisfies the residual evaluation law. -/
theorem finKernel_canonicalReindex_satisfies_residualEvaluationLaw {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.ResidualEvaluationLaw P K l hl
      (FinKernel.ReindexFullFutureResponse
        (FinKernel.GeneratedRightShift l hl)) := by
  intro s c hc m f obs hobs x z
  rfl

/--
Uniqueness / anti-tautology theorem: once the generated-future right shift and
its scalar evaluation law are fixed, any response operator satisfying that law
is extensionally the canonical precomposition operator.  There is no extra
operator choice left to specify.
-/
theorem finKernel_residualEvaluationLaw_unique {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    {op : FinKernel.FullFutureResponseOperator P K}
    (hop : FinKernel.ResidualEvaluationLaw P K l hl op) :
    FinKernel.FullFutureResponseOperatorEq op
      (FinKernel.ReindexFullFutureResponse
        (FinKernel.GeneratedRightShift l hl)) := by
  intro s c hc m f obs hobs x z
  have h := hop s c hc m f obs hobs x z
  simpa [FinKernel.ReindexFullFutureResponse,
    FinKernel.GeneratedRightShift] using h

/--
The previously introduced derivative factors through ordinary response-space
precomposition by the generated-continuation right shift.
-/
theorem finKernel_futureDerivative_factors_through_canonicalReindex {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseOperatorEq
      (FinKernel.FutureDerivative P K l hl)
      (FinKernel.ReindexFullFutureResponse
        (FinKernel.GeneratedRightShift l hl)) := by
  intro s c hc m f obs hobs x z
  rfl

/--
Generated right shifts compose contravariantly with the established execution
order: shifting by `l` and then by `k` is the shift for `l ∘ k`.
-/
theorem finKernel_generatedRightShift_composition {n : Nat}
    {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.GeneratedRightShift (FinKernel.compose l k)
        (FinKernel.GeneratedContext.seq hk hl) =
      fun i => FinKernel.GeneratedRightShift k hk
        (FinKernel.GeneratedRightShift l hl i) := by
  funext i
  apply FinKernel.GeneratedContinuationIndex.ext_kernel
  exact finKernel_compose_associative k l i.kernel

/--
Generic function-space fact: reindexing by a composite index map is ordinary
composition of reindexing operators, with the expected contravariant order.
-/
theorem finKernel_reindexFullFutureResponse_composition {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    (r q : FinKernel.GeneratedContinuationIndex K →
      FinKernel.GeneratedContinuationIndex K) :
    FinKernel.FullFutureResponseOperatorEq
      (FinKernel.ReindexFullFutureResponse (fun i => q (r i)))
      (fun s => FinKernel.ReindexFullFutureResponse r
        (FinKernel.ReindexFullFutureResponse q s)) := by
  intro s c hc m f obs hobs x z
  rfl

/--
Canonical residual composition is inherited from generated-index composition
plus generic function precomposition; no special derivative algebra is needed.
-/
theorem finKernel_canonicalResidual_composition {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseOperatorEq
      (FinKernel.ReindexFullFutureResponse
        (FinKernel.GeneratedRightShift (FinKernel.compose l k)
          (FinKernel.GeneratedContext.seq hk hl)))
      (fun s =>
        FinKernel.ReindexFullFutureResponse
          (FinKernel.GeneratedRightShift l hl)
          (FinKernel.ReindexFullFutureResponse
            (FinKernel.GeneratedRightShift k hk) s)) := by
  rw [finKernel_generatedRightShift_composition hk hl]
  exact finKernel_reindexFullFutureResponse_composition
    (P := P) (K := K)
    (FinKernel.GeneratedRightShift l hl)
    (FinKernel.GeneratedRightShift k hk)

/--
Consequently the derivative composition law holds on the entire response
carrier, not merely on response signatures generated by literal kernels.
-/
theorem finKernel_futureDerivative_composition_all_responses {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {k l : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l) :
    FinKernel.FullFutureResponseOperatorEq
      (FinKernel.FutureDerivative P K (FinKernel.compose l k)
        (FinKernel.GeneratedContext.seq hk hl))
      (fun s => FinKernel.FutureDerivative P K l hl
        (FinKernel.FutureDerivative P K k hk s)) := by
  intro s c hc m f obs hobs x z
  simp only [FinKernel.FutureDerivative]
  rw [finKernel_compose_associative k l c]

/--
The canonical reindexing presentation carries exactly the same semantic-image
identifications as the derivative presentation from #2794.
-/
theorem finKernel_derivativeEq_iff_canonicalResidualEqOnSemanticSignatures
    {n : Nat}
    {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
    {l l' : FinKernel n n}
    (hl : FinKernel.GeneratedContext K l)
    (hl' : FinKernel.GeneratedContext K l') :
    FinKernel.DerivativeEqOnSemanticSignatures P K l l' hl hl' ↔
      FinKernel.CanonicalResidualEqOnSemanticSignatures P K l l' hl hl' := by
  constructor
  · intro h k c hc m f obs hobs x z
    have hv := h k c hc m f obs hobs x z
    simpa [FinKernel.FutureDerivative,
      FinKernel.ReindexFullFutureResponse,
      FinKernel.GeneratedRightShift] using hv
  · intro h k c hc m f obs hobs x z
    have hv := h k c hc m f obs hobs x z
    simpa [FinKernel.FutureDerivative,
      FinKernel.ReindexFullFutureResponse,
      FinKernel.GeneratedRightShift] using hv

/--
Safe `merge01` keeps a literal distinction between right-shift maps even though
its admitted response semantics cannot distinguish their canonical residual
actions.
-/
theorem finKernel_merge01_safe_literal_rightShift_ne :
    FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe ≠
      FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity := by
  intro h
  let i : FinKernel.GeneratedContinuationIndex
      FinKernel.merge01SafeContextFamily3 :=
    { kernel := FinKernel.identity 3
      generated := FinKernel.GeneratedContext.identity }
  have hi := congrFun h i
  have hk :
      FinKernel.compose (FinKernel.identity 3)
          (FinKernel.dirac finCollapseHidden3) =
        FinKernel.compose (FinKernel.identity 3)
          (FinKernel.identity 3) := by
    simpa [i, FinKernel.GeneratedRightShift] using
      congrArg FinKernel.GeneratedContinuationIndex.kernel hi
  rw [finKernel_compose_identity_after,
    finKernel_compose_identity_after] at hk
  exact finKernel_identity3_ne_hidden_collapse hk.symm

/-- Safe `merge01`: canonical residual actions agree on semantic signatures. -/
theorem finKernel_merge01_safe_canonicalResidualEq :
    FinKernel.CanonicalResidualEqOnSemanticSignatures
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity := by
  exact (finKernel_derivativeEq_iff_canonicalResidualEqOnSemanticSignatures
    finKernel_merge01_collapse_generated_safe
    FinKernel.GeneratedContext.identity).1
    finKernel_merge01_safe_collapse_identity_derivativeEq

/-- Expanded `merge01` still splits the canonical residual semantics. -/
theorem finKernel_merge01_expanded_not_canonicalResidualEq :
    ¬ FinKernel.CanonicalResidualEqOnSemanticSignatures
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity := by
  intro h
  exact finKernel_merge01_expanded_collapse_identity_not_derivativeEq
    ((finKernel_derivativeEq_iff_canonicalResidualEqOnSemanticSignatures
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity).2 h)

/--
Acceptance bundle for #2801: residual evaluation uniquely fixes the response
operator, while literal right-shift structure can remain distinct under a safe
semantic identification and the expanded control still separates it.
-/
theorem finKernel_canonical_residual_reindexing_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n} {K : FinKernel.FutureContextFamily n}
      {l : FinKernel n n}
      (hl : FinKernel.GeneratedContext K l)
      (op : FinKernel.FullFutureResponseOperator P K),
      FinKernel.ResidualEvaluationLaw P K l hl op →
        FinKernel.FullFutureResponseOperatorEq op
          (FinKernel.ReindexFullFutureResponse
            (FinKernel.GeneratedRightShift l hl))) ∧
    FinKernel.GeneratedRightShift
        (FinKernel.dirac finCollapseHidden3)
        finKernel_merge01_collapse_generated_safe ≠
      FinKernel.GeneratedRightShift
        (FinKernel.identity 3)
        FinKernel.GeneratedContext.identity ∧
    FinKernel.CanonicalResidualEqOnSemanticSignatures
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_collapse_generated_safe
      FinKernel.GeneratedContext.identity ∧
    ¬ FinKernel.CanonicalResidualEqOnSemanticSignatures
      FinKernel.merge01ProbeFamily3
      FinKernel.merge01ExpandedContextFamily3
      (FinKernel.dirac finCollapseHidden3)
      (FinKernel.identity 3)
      finKernel_merge01_expanded_collapse_generated
      FinKernel.GeneratedContext.identity := by
  constructor
  · intro n P K l hl op hop
    exact finKernel_residualEvaluationLaw_unique hl hop
  · exact ⟨finKernel_merge01_safe_literal_rightShift_ne,
      finKernel_merge01_safe_canonicalResidualEq,
      finKernel_merge01_expanded_not_canonicalResidualEq⟩

end RelayTheory
