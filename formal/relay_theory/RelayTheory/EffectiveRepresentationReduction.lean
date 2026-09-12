import RelayTheory.WorkloadInterfaceCompilation

namespace RelayTheory

/--
The consumer-facing effective representation obtained by composing a declared
representation with its declared access interface.  This is only functional
composition; it introduces no new semantic or cognitive object.
-/
def effectiveRepresentation
    {History Carrier View : Type}
    (rep : History → Carrier)
    (access : Carrier → View) : History → View :=
  fun h => access (rep h)

/--
In the current exact bounded-decoder model, explicit access-interface
accessibility is definitionally the same predicate as ordinary accessibility of
the composed consumer-facing effective representation.
-/
theorem accessibleViaAt_iff_accessibleAt_effectiveRepresentation
    {History Carrier View Output Decoder : Type}
    (cost : Decoder → Nat)
    (run : Decoder → View → Output)
    (budget : Nat)
    (query : History → Output)
    (rep : History → Carrier)
    (access : Carrier → View) :
    AccessibleViaAt cost run budget query rep access ↔
      AccessibleAt cost run budget query (effectiveRepresentation rep access) := by
  rfl

/--
The workload-family version adds no new factorization principle either: one
shared access interface is exactly one shared effective representation, tested
against each workload query through the ordinary bounded decoder predicate.
-/
theorem familyAccessibleViaAt_iff_eachAccessibleAt_effectiveRepresentation
    {Index History Carrier View Output Decoder : Type}
    (cost : Decoder → Nat)
    (run : Decoder → View → Output)
    (budget : Nat)
    (queries : Index → History → Output)
    (rep : History → Carrier)
    (access : Carrier → View) :
    FamilyAccessibleViaAt cost run budget queries rep access ↔
      ∀ i, AccessibleAt cost run budget (queries i)
        (effectiveRepresentation rep access) := by
  rfl

/--
If two representation/interface decompositions induce the same effective
consumer-facing representation, the current accessibility predicate cannot
distinguish which side of the boundary carried the transformation.
-/
theorem accessibleViaAt_congr_effectiveRepresentation
    {History Carrier₁ Carrier₂ View Output Decoder : Type}
    (cost : Decoder → Nat)
    (run : Decoder → View → Output)
    (budget : Nat)
    (query : History → Output)
    (rep₁ : History → Carrier₁)
    (access₁ : Carrier₁ → View)
    (rep₂ : History → Carrier₂)
    (access₂ : Carrier₂ → View)
    (hEffective :
      effectiveRepresentation rep₁ access₁ =
        effectiveRepresentation rep₂ access₂) :
    AccessibleViaAt cost run budget query rep₁ access₁ ↔
      AccessibleViaAt cost run budget query rep₂ access₂ := by
  rw [accessibleViaAt_iff_accessibleAt_effectiveRepresentation,
    accessibleViaAt_iff_accessibleAt_effectiveRepresentation,
    hEffective]

end RelayTheory