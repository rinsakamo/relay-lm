import RelayTheory.AccessInterfaceTrivialization

namespace RelayTheory

/--
Exact accessibility for a whole workload family through one shared access
interface.  Each workload member may choose an admissible downstream decoder,
but the representation, access map, decoder semantics, and budget are shared.
-/
def FamilyAccessibleViaAt
    {Index History Carrier View Output Decoder : Type}
    (cost : Decoder → Nat)
    (run : Decoder → View → Output)
    (budget : Nat)
    (queries : Index → History → Output)
    (rep : History → Carrier)
    (access : Carrier → View) : Prop :=
  ∀ i, ∃ decoder, cost decoder ≤ budget ∧
    ∀ h, run decoder (access (rep h)) = queries i h

/-- A workload index can itself name a zero-cost projection consumer. -/
def familyProjectionCost {Index : Type} (_ : Index) : Nat := 0

/-- Project one declared workload response out of a compiled response vector. -/
def familyProjectionRun {Index Output : Type}
    (i : Index) (view : Index → Output) : Output :=
  view i

/--
If every query in a declared workload family has an exact semantic decoder, one
single free interface can compile all of those responses into a function-valued
view.  Zero-cost projection consumers then recover every declared response.

The theorem deliberately places no capacity or construction-cost bound on the
function-valued view.  Its role is to show that shared reuse alone is not an
anti-trivialization condition when workload-aware compilation is free.
-/
theorem sharedFreeInterface_compilesWorkload
    {Index History Carrier Output : Type}
    (queries : Index → History → Output)
    (rep : History → Carrier)
    (decode : Index → Carrier → Output)
    (hExact : ∀ i h, decode i (rep h) = queries i h) :
    FamilyAccessibleViaAt familyProjectionCost familyProjectionRun 0
      queries rep (fun c i => decode i c) := by
  intro i
  refine ⟨i, ?_, ?_⟩
  · simp [familyProjectionCost]
  · intro h
    exact hExact i h

/-- Two tiny workload members for the held-out expansion control. -/
inductive BitWorkload where
  | first
  | second
deriving DecidableEq, Repr

/-- Query either coordinate of a two-bit history. -/
def twoBitQueries : BitWorkload → Bool × Bool → Bool
  | .first, h => h.1
  | .second, h => h.2

/-- One shared free interface that compiles both known query responses. -/
def twoBitCompiledAccess (h : Bool × Bool) : BitWorkload → Bool :=
  fun i => twoBitQueries i h

/--
Concrete shared-reuse fixture: one access map serves both declared workload
members at zero downstream projection cost.
-/
theorem twoBit_family_accessible_via_sharedCompiledVector_at_zero :
    FamilyAccessibleViaAt familyProjectionCost familyProjectionRun 0
      twoBitQueries (fun h : Bool × Bool => h) twoBitCompiledAccess := by
  exact sharedFreeInterface_compilesWorkload
    twoBitQueries
    (fun h : Bool × Bool => h)
    (fun i h => twoBitQueries i h)
    (by
      intro i h
      rfl)

/-- A deliberately narrow frozen interface that exposes only the first bit. -/
def frozenFirstBitAccess (h : Bool × Bool) : Bool := h.1

/-- All Bool-to-Bool downstream decoders are allowed in the expansion control. -/
def boolFunctionDecoderCost (_ : Bool → Bool) : Nat := 0

/-- Execute an unrestricted Bool-to-Bool downstream decoder. -/
def boolFunctionDecoderRun (decoder : Bool → Bool) (view : Bool) : Bool :=
  decoder view

/-- The original one-member workload asks only for the first bit. -/
def firstOnlyQueries (_ : Unit) (h : Bool × Bool) : Bool := h.1

/-- The frozen first-bit interface exactly serves its original workload. -/
theorem firstOnly_family_accessible_via_frozenFirstBit :
    FamilyAccessibleViaAt boolFunctionDecoderCost boolFunctionDecoderRun 0
      firstOnlyQueries (fun h : Bool × Bool => h) frozenFirstBitAccess := by
  intro i
  refine ⟨(fun x => x), ?_, ?_⟩
  · simp [boolFunctionDecoderCost]
  · intro h
    rfl

/-- The held-out second-bit query used after the first-bit interface is frozen. -/
def secondBitQuery (h : Bool × Bool) : Bool := h.2

/--
No downstream Bool-to-Bool decoder can reconstruct the second bit from a view
that contains only the first bit.  The two histories `(false,false)` and
`(false,true)` have the same frozen view but require different answers.
-/
theorem secondBit_not_decodable_from_frozenFirstBit :
    ¬ ∃ decoder : Bool → Bool, ∀ h : Bool × Bool,
        boolFunctionDecoderRun decoder (frozenFirstBitAccess h) =
          secondBitQuery h := by
  intro hExists
  rcases hExists with ⟨decoder, hExact⟩
  have hFalse := hExact (false, false)
  have hTrue := hExact (false, true)
  simp [boolFunctionDecoderRun, frozenFirstBitAccess, secondBitQuery] at hFalse hTrue
  have hContradiction : (false : Bool) = true := hFalse.symm.trans hTrue
  cases hContradiction

/--
After expanding the workload to include the second-bit query, the same frozen
first-bit interface fails even though every Bool-to-Bool downstream decoder is
admissible at zero declared decoder cost.
-/
theorem twoBit_family_not_accessible_via_frozenFirstBit :
    ¬ FamilyAccessibleViaAt boolFunctionDecoderCost boolFunctionDecoderRun 0
      twoBitQueries (fun h : Bool × Bool => h) frozenFirstBitAccess := by
  intro hFamily
  rcases hFamily BitWorkload.second with ⟨decoder, _, hExact⟩
  apply secondBit_not_decodable_from_frozenFirstBit
  refine ⟨decoder, ?_⟩
  intro h
  simpa [twoBitQueries, secondBitQuery] using hExact h

/--
Prospective expansion control: the interface is sufficient for the workload it
was frozen to serve, but not for a later family containing an unexposed
distinction.
-/
theorem frozenInterface_workloadExpansion_control :
    FamilyAccessibleViaAt boolFunctionDecoderCost boolFunctionDecoderRun 0
        firstOnlyQueries (fun h : Bool × Bool => h) frozenFirstBitAccess ∧
      ¬ FamilyAccessibleViaAt boolFunctionDecoderCost boolFunctionDecoderRun 0
        twoBitQueries (fun h : Bool × Bool => h) frozenFirstBitAccess := by
  exact ⟨firstOnly_family_accessible_via_frozenFirstBit,
    twoBit_family_not_accessible_via_frozenFirstBit⟩

end RelayTheory