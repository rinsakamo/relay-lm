import RelayTheory.BoundedDecoderFactorization

namespace RelayTheory

/--
Exact accessibility through an explicit access interface, while charging only
work performed by the declared downstream decoder.  This definition is useful
precisely because the results below show why an unconstrained free interface can
make such stage-local accounting vacuous.
-/
def AccessibleViaAt
    {History Carrier View Output Decoder : Type}
    (cost : Decoder → Nat)
    (run : Decoder → View → Output)
    (budget : Nat)
    (query : History → Output)
    (rep : History → Carrier)
    (access : Carrier → View) : Prop :=
  ∃ decoder, cost decoder ≤ budget ∧
    ∀ h, run decoder (access (rep h)) = query h

/-- One exact identity consumer used as a zero-cost downstream control. -/
inductive ZeroIdentityDecoder where
  | identity
deriving DecidableEq, Repr

/-- The identity consumer carries zero declared downstream cost. -/
def zeroIdentityDecoderCost (_ : ZeroIdentityDecoder) : Nat := 0

/-- Identity-consumer semantics for any view/output type that is the same type. -/
def zeroIdentityDecoderRun {α : Type} : ZeroIdentityDecoder → α → α
  | .identity, x => x

/--
If an exact semantic decoder may itself be chosen as the access interface for
free, the remaining consumer can be a zero-cost identity.  Thus unrestricted
target-aware free preprocessing collapses this stage-local accessibility notion
back to ordinary exact semantic factorization.
-/
theorem freeInterface_absorbs_semanticDecoder
    {History Carrier Output : Type}
    (query : History → Output)
    (rep : History → Carrier)
    (decode : Carrier → Output)
    (hExact : ∀ h, decode (rep h) = query h) :
    AccessibleViaAt zeroIdentityDecoderCost zeroIdentityDecoderRun 0
      query rep decode := by
  refine ⟨ZeroIdentityDecoder.identity, ?_, ?_⟩
  · simp [zeroIdentityDecoderCost]
  · intro h
    exact hExact h

/-- Identity access does not weaken the bounded decoder condition from #2674. -/
theorem decoderMixed_not_accessible_via_identity_at_zero :
    ¬ AccessibleViaAt pairDecoderCost pairDecoderRun 0
      decoderFirstBitQuery decoderMixedRepresentation (fun x => x) := by
  simpa [AccessibleViaAt, AccessibleAt] using
    decoderMixed_not_accessible_at_zero

/-- Target-aware preprocessing that extracts the source first bit from the mixed coordinate. -/
def decoderMixedXorAccess (x : Bool × Bool) : Bool :=
  decoderXor x.1 x.2

/-- The target-aware access map exactly decodes the declared first-bit query. -/
theorem decoderMixedXorAccess_exact
    (h : Bool × Bool) :
    decoderMixedXorAccess (decoderMixedRepresentation h) =
      decoderFirstBitQuery h := by
  rcases h with ⟨a, b⟩
  cases a <;> cases b <;> rfl

/--
The #2674 mixed representation becomes zero-decoder-budget accessible when its
XOR work is moved into an uncharged target-aware access interface.
-/
theorem decoderMixed_accessible_via_free_targetAccess_at_zero :
    AccessibleViaAt zeroIdentityDecoderCost zeroIdentityDecoderRun 0
      decoderFirstBitQuery decoderMixedRepresentation decoderMixedXorAccess := by
  exact freeInterface_absorbs_semanticDecoder
    decoderFirstBitQuery decoderMixedRepresentation decoderMixedXorAccess
    decoderMixedXorAccess_exact

/--
Pipeline accessibility charges the declared access transformation and downstream
decoder together.  This is only a tiny additive finite control, not a universal
model of real compute cost.
-/
def PipelineAccessibleAt
    {History Carrier View Output Decoder : Type}
    (accessCost : Nat)
    (decoderCost : Decoder → Nat)
    (run : Decoder → View → Output)
    (budget : Nat)
    (query : History → Output)
    (rep : History → Carrier)
    (access : Carrier → View) : Prop :=
  ∃ decoder, accessCost + decoderCost decoder ≤ budget ∧
    ∀ h, run decoder (access (rep h)) = query h

/--
Direct realization of the mixed query: identity access is free and the XOR
consumer carries the one unit of declared work.
-/
theorem decoderMixed_pipeline_direct_cost_one :
    PipelineAccessibleAt 0 pairDecoderCost pairDecoderRun 1
      decoderFirstBitQuery decoderMixedRepresentation (fun x => x) := by
  refine ⟨PairDecoder.xor, ?_, ?_⟩
  · simp [pairDecoderCost]
  · intro h
    rcases h with ⟨a, b⟩
    cases a <;> cases b <;> rfl

/--
Relocated realization of the same exact query: XOR work is charged to the access
interface while the downstream identity consumer is free.  Total declared work
remains one unit.
-/
theorem decoderMixed_pipeline_relocated_cost_one :
    PipelineAccessibleAt 1 zeroIdentityDecoderCost zeroIdentityDecoderRun 1
      decoderFirstBitQuery decoderMixedRepresentation decoderMixedXorAccess := by
  refine ⟨ZeroIdentityDecoder.identity, ?_, ?_⟩
  · simp [zeroIdentityDecoderCost]
  · intro h
    exact decoderMixedXorAccess_exact h

/--
Finite relocation control: the same behavior can place the one unit of declared
work on either side of the access/decoder boundary while preserving total cost.
-/
theorem decoderMixed_pipeline_work_relocation_control :
    PipelineAccessibleAt 0 pairDecoderCost pairDecoderRun 1
        decoderFirstBitQuery decoderMixedRepresentation (fun x => x) ∧
      PipelineAccessibleAt 1 zeroIdentityDecoderCost zeroIdentityDecoderRun 1
        decoderFirstBitQuery decoderMixedRepresentation decoderMixedXorAccess := by
  exact ⟨decoderMixed_pipeline_direct_cost_one,
    decoderMixed_pipeline_relocated_cost_one⟩

/--
Anti-trivialization fixture: freezing identity access preserves the zero-budget
access gap, while allowing the target-aware XOR access for free erases it.
-/
theorem freeInterface_trivialization_fixture :
    (¬ AccessibleViaAt pairDecoderCost pairDecoderRun 0
        decoderFirstBitQuery decoderMixedRepresentation (fun x => x)) ∧
      AccessibleViaAt zeroIdentityDecoderCost zeroIdentityDecoderRun 0
        decoderFirstBitQuery decoderMixedRepresentation decoderMixedXorAccess := by
  exact ⟨decoderMixed_not_accessible_via_identity_at_zero,
    decoderMixed_accessible_via_free_targetAccess_at_zero⟩

end RelayTheory
