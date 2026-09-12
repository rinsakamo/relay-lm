import Lean.Elab.Tactic

namespace RelayTheory

/--
Two histories are predictively equivalent for a declared response surface when
no declared probe changes the output.  This definition contains no temporal
coordinate and does not identify the histories as objects.
-/
def PredictivelyEquivalent
    {History Probe Output : Type}
    (response : History → Probe → Output)
    (h₁ h₂ : History) : Prop :=
  ∀ probe, response h₁ probe = response h₂ probe

/--
An arbitrary state representation is exactly sufficient when equal encoded
states may only merge predictively equivalent histories.
-/
def StateSufficient
    {History Probe Output State : Type}
    (response : History → Probe → Output)
    (encode : History → State) : Prop :=
  ∀ h₁ h₂, encode h₁ = encode h₂ →
    PredictivelyEquivalent response h₁ h₂

/-- Exact sufficiency specialized to one fixed finite state carrier. -/
def FiniteStateSufficient
    {History Probe Output : Type}
    (response : History → Probe → Output)
    {n : Nat}
    (encode : History → Fin n) : Prop :=
  StateSufficient response encode

/--
A declared finite sample is pairwise predictively distinct when every two
separate sample indices admit some probe-level response distinction.
-/
def PairwisePredictivelyDistinct
    {History Probe Output : Type}
    (response : History → Probe → Output)
    {k : Nat}
    (sample : Fin k → History) : Prop :=
  ∀ i j, i ≠ j →
    ¬ PredictivelyEquivalent response (sample i) (sample j)

/--
Exact state sufficiency forces injectivity on every pairwise predictively
separated sample.  This is the operational core of the residual-capacity
lower bound; cardinality enters only afterwards.
-/
theorem stateSufficient_injective_on_pairwise_distinct
    {History Probe Output State : Type}
    {response : History → Probe → Output}
    {encode : History → State}
    {k : Nat}
    {sample : Fin k → History}
    (hsuff : StateSufficient response encode)
    (hdistinct : PairwisePredictivelyDistinct response sample) :
    Function.Injective (fun i => encode (sample i)) := by
  intro i j hij
  by_contra hne
  exact hdistinct i j hne (hsuff (sample i) (sample j) hij)

/--
Delete one distinguished element from `Fin (n+1)` while preserving the order
of the remaining values.  The proof argument records that the deleted point is
not the input; no broad finite-cardinality library is required.
-/
def finErase {n : Nat}
    (pivot value : Fin (n + 1))
    (hne : value ≠ pivot) : Fin n :=
  if hlt : value.val < pivot.val then
    ⟨value.val, by omega⟩
  else
    ⟨value.val - 1, by
      have hle : pivot.val ≤ value.val := Nat.le_of_not_gt hlt
      have hvalne : value.val ≠ pivot.val := by
        intro h
        exact hne (Fin.ext h)
      omega⟩

/-- `finErase` remains injective away from the deleted point. -/
theorem finErase_injective
    {n : Nat}
    (pivot : Fin (n + 1))
    {y z : Fin (n + 1)}
    (hy : y ≠ pivot)
    (hz : z ≠ pivot)
    (h : finErase pivot y hy = finErase pivot z hz) :
    y = z := by
  apply Fin.ext
  have hv := congrArg Fin.val h
  by_cases hyp : y.val < pivot.val
  · by_cases hzp : z.val < pivot.val
    · simp [finErase, hyp, hzp] at hv
      exact hv
    · simp [finErase, hyp, hzp] at hv
      have hzle : pivot.val ≤ z.val := Nat.le_of_not_gt hzp
      have hzneq : z.val ≠ pivot.val := by
        intro hzv
        exact hz (Fin.ext hzv)
      omega
  · by_cases hzp : z.val < pivot.val
    · simp [finErase, hyp, hzp] at hv
      have hyle : pivot.val ≤ y.val := Nat.le_of_not_gt hyp
      have hyneq : y.val ≠ pivot.val := by
        intro hyv
        exact hy (Fin.ext hyv)
      omega
    · simp [finErase, hyp, hzp] at hv
      have hyle : pivot.val ≤ y.val := Nat.le_of_not_gt hyp
      have hzle : pivot.val ≤ z.val := Nat.le_of_not_gt hzp
      have hyneq : y.val ≠ pivot.val := by
        intro hyv
        exact hy (Fin.ext hyv)
      have hzneq : z.val ≠ pivot.val := by
        intro hzv
        exact hz (Fin.ext hzv)
      omega

/--
Owner-local finite pigeonhole lemma: there is no injective map from `Fin (n+1)`
into `Fin n`.  The induction removes the image of the last source point and
reduces the alleged injection by one on both sides.
-/
theorem fin_succ_not_injective :
    ∀ n : Nat, ∀ f : Fin (n + 1) → Fin n,
      ¬ Function.Injective f
  | 0, f => by
      intro _
      exact Fin.elim0 (f 0)
  | n + 1, f => by
      intro hf
      let last : Fin (n + 2) := Fin.last (n + 1)
      let pivot : Fin (n + 1) := f last
      have hneq (i : Fin (n + 1)) :
          f (Fin.castSucc i) ≠ pivot := by
        intro h
        have heq : Fin.castSucc i = last := hf h
        have hv := congrArg Fin.val heq
        have hi := i.isLt
        simp [last] at hv
        omega
      let g : Fin (n + 1) → Fin n :=
        fun i => finErase pivot (f (Fin.castSucc i)) (hneq i)
      have hg : Function.Injective g := by
        intro i j hij
        have hfij :
            f (Fin.castSucc i) = f (Fin.castSucc j) := by
          exact finErase_injective pivot (hneq i) (hneq j) hij
        have hijCast : Fin.castSucc i = Fin.castSucc j := hf hfij
        have hv : i.val = j.val := by
          change (Fin.castSucc i).val = (Fin.castSucc j).val
          exact congrArg (fun x : Fin (n + 2) => x.val) hijCast
        exact Fin.ext hv
      exact fin_succ_not_injective n g hg

/--
`N+1` pairwise predictive residuals cannot be represented exactly by `N` finite
states.  This is a capacity result about the declared response interface, not a
temporal or ontological statement.
-/
theorem no_finiteStateSufficient_of_succ_pairwise_distinct
    {History Probe Output : Type}
    {response : History → Probe → Output}
    {n : Nat}
    {sample : Fin (n + 1) → History}
    (hdistinct : PairwisePredictivelyDistinct response sample)
    (encode : History → Fin n) :
    ¬ FiniteStateSufficient response encode := by
  intro hsuff
  have hinj : Function.Injective (fun i => encode (sample i)) :=
    stateSufficient_injective_on_pairwise_distinct hsuff hdistinct
  exact fin_succ_not_injective n (fun i => encode (sample i)) hinj

/--
Neutral unbounded residual fixture: a history label is queried only for exact
identity.  No ordering or temporal meaning is attached to the natural number.
-/
def natEqualityResponse (history probe : Nat) : Bool :=
  decide (history = probe)

/-- Predictive equivalence in the neutral equality fixture is exactly equality. -/
theorem natEqualityResponse_predictiveEquivalent_iff
    (h₁ h₂ : Nat) :
    PredictivelyEquivalent natEqualityResponse h₁ h₂ ↔ h₁ = h₂ := by
  constructor
  · intro heq
    by_contra hne
    have hne' : h₂ ≠ h₁ := by
      intro h
      exact hne h.symm
    have hp := heq h₁
    simp [natEqualityResponse, hne'] at hp
  · intro h
    subst h₂
    intro probe
    rfl

/-- The first `N+1` natural labels are pairwise predictive residuals. -/
theorem natEqualityResponse_succ_sample_pairwise_distinct
    (n : Nat) :
    PairwisePredictivelyDistinct natEqualityResponse
      (fun i : Fin (n + 1) => i.val) := by
  intro i j hij
  intro heq
  have hv : i.val = j.val :=
    (natEqualityResponse_predictiveEquivalent_iff i.val j.val).1 heq
  exact hij (Fin.ext hv)

/--
Every fixed finite carrier fails as an exact sufficient state for the neutral
`Nat` equality-response family.
-/
theorem natEqualityResponse_no_fixed_finite_state
    (n : Nat)
    (encode : Nat → Fin n) :
    ¬ FiniteStateSufficient natEqualityResponse encode := by
  exact no_finiteStateSufficient_of_succ_pairwise_distinct
    (natEqualityResponse_succ_sample_pairwise_distinct n) encode

/--
The same unbounded response family has an ordinary exact state representation:
store the natural residual label itself.  Thus failure of every fixed `Fin n`
does not imply failure of ordinary one-parameter state modeling.
-/
theorem natEqualityResponse_identity_state_sufficient :
    StateSufficient natEqualityResponse (fun h : Nat => h) := by
  intro h₁ h₂ hstate
  change h₁ = h₂ at hstate
  cases hstate
  intro probe
  rfl

/-- Bounded positive-control response over exactly `k` residual labels. -/
def finEqualityResponse {k : Nat}
    (history probe : Fin k) : Bool :=
  decide (history = probe)

/-- The bounded equality fixture admits the obvious exact `Fin k` state. -/
theorem finEqualityResponse_identity_finite_state_sufficient
    (k : Nat) :
    FiniteStateSufficient
      (@finEqualityResponse k)
      (fun h : Fin k => h) := by
  intro h₁ h₂ hstate
  change h₁ = h₂ at hstate
  cases hstate
  intro probe
  rfl

/--
Owner-local acceptance bundle.  It records the bounded/unbounded state-capacity
boundary only; it contains no claim about physical time, spacetime, entropy, or
fundamental ontology.
-/
theorem predictiveResidualComplexity_bundle :
    (∀ n : Nat, ∀ encode : Nat → Fin n,
      ¬ FiniteStateSufficient natEqualityResponse encode) ∧
    StateSufficient natEqualityResponse (fun h : Nat => h) ∧
    (∀ k : Nat,
      FiniteStateSufficient
        (@finEqualityResponse k)
        (fun h : Fin k => h)) := by
  exact ⟨
    natEqualityResponse_no_fixed_finite_state,
    natEqualityResponse_identity_state_sufficient,
    finEqualityResponse_identity_finite_state_sufficient⟩

end RelayTheory
