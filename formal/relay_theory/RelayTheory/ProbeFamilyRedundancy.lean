import RelayTheory.ProbeDoctrine

namespace RelayTheory

namespace FinKernel

/--
`P` refines `Q` when exact equivalence under `P` always implies exact
equivalence under `Q`, uniformly over every compatible source interface.

This is an induced-behavior relation on probe families. It does not identify
literal family membership predicates.
-/
def ProbeFamilyRefines {n : Nat}
    (P Q : ProbeFamily n) : Prop :=
  ∀ {m : Nat} (f g : FinKernel m n), ProbeEq P f g → ProbeEq Q f g

/--
Two probe families are operationally equivalent at this exact finite-kernel
surface when they induce the same `ProbeEq` relation for every compatible
source interface.
-/
def ProbeFamilyEquivalent {n : Nat}
    (P Q : ProbeFamily n) : Prop :=
  ∀ {m : Nat} (f g : FinKernel m n), ProbeEq P f g ↔ ProbeEq Q f g

/-- Identity observation on the binary interface. -/
def finIdentityObservation2 : Observation 2 :=
  ⟨2, identity 2⟩

/-- Discard observation on the same binary interface. -/
def finDiscardObservation2 : Observation 2 :=
  ⟨1, discard 2⟩

/-- The family containing only the exact binary identity observation. -/
def identityProbeFamily2 : ProbeFamily 2 :=
  singletonProbe finIdentityObservation2

/--
A literally larger family containing both identity and discard observations.
The main witness will show that discard is redundant once identity is already
admitted.
-/
def identityDiscardProbeFamily2 : ProbeFamily 2 :=
  fun obs => obs = finIdentityObservation2 ∨ obs = finDiscardObservation2

end FinKernel

/-- Every probe family refines itself at the induced-equivalence level. -/
theorem finKernel_probeFamilyRefines_refl {n : Nat}
    (P : FinKernel.ProbeFamily n) :
    FinKernel.ProbeFamilyRefines P P := by
  intro m f g hfg
  exact hfg

/-- Induced probe-family refinement is transitive. -/
theorem finKernel_probeFamilyRefines_trans {n : Nat}
    {P Q R : FinKernel.ProbeFamily n}
    (hPQ : FinKernel.ProbeFamilyRefines P Q)
    (hQR : FinKernel.ProbeFamilyRefines Q R) :
    FinKernel.ProbeFamilyRefines P R := by
  intro m f g hP
  exact hQR f g (hPQ f g hP)

/--
Literal inclusion in the reverse direction gives the expected induced
refinement: if every `Q` probe is already admitted by `P`, equivalence under
`P` is strong enough to imply equivalence under `Q`.
-/
theorem finKernel_probeFamilyRefines_of_reverse_inclusion {n : Nat}
    {P Q : FinKernel.ProbeFamily n}
    (hQP : ∀ obs, Q obs → P obs) :
    FinKernel.ProbeFamilyRefines P Q := by
  intro m f g hP
  exact finKernel_probeEq_antitone hQP hP

/-- Mutual induced equivalence is reflexive. -/
theorem finKernel_probeFamilyEquivalent_refl {n : Nat}
    (P : FinKernel.ProbeFamily n) :
    FinKernel.ProbeFamilyEquivalent P P := by
  intro m f g
  rfl

/-- Mutual induced equivalence is symmetric. -/
theorem finKernel_probeFamilyEquivalent_symm {n : Nat}
    {P Q : FinKernel.ProbeFamily n}
    (hPQ : FinKernel.ProbeFamilyEquivalent P Q) :
    FinKernel.ProbeFamilyEquivalent Q P := by
  intro m f g
  exact (hPQ f g).symm

/-- Mutual induced equivalence is transitive. -/
theorem finKernel_probeFamilyEquivalent_trans {n : Nat}
    {P Q R : FinKernel.ProbeFamily n}
    (hPQ : FinKernel.ProbeFamilyEquivalent P Q)
    (hQR : FinKernel.ProbeFamilyEquivalent Q R) :
    FinKernel.ProbeFamilyEquivalent P R := by
  intro m f g
  exact Iff.trans (hPQ f g) (hQR f g)

/-- The binary identity-only family already forces literal kernel equality. -/
theorem finKernel_identityProbeFamily2_probeEq_iff_eq {m : Nat}
    (f g : FinKernel m 2) :
    FinKernel.ProbeEq FinKernel.identityProbeFamily2 f g ↔ f = g := by
  unfold FinKernel.identityProbeFamily2 FinKernel.finIdentityObservation2
  rw [finKernel_probeEq_singleton_iff_observedEq]
  unfold FinKernel.ObservedEq
  rw [finKernel_compose_identity_after]
  exact finKernel_behaviorEq_iff_eq f g

/--
The identity-only and identity-plus-discard families are literally different
predicates: the latter admits the typed discard observation and the former does
not.
-/
theorem finKernel_identity_and_identityDiscard_families_differ :
    FinKernel.identityProbeFamily2 ≠
      FinKernel.identityDiscardProbeFamily2 := by
  intro hEq
  have hInLarger :
      FinKernel.identityDiscardProbeFamily2
        FinKernel.finDiscardObservation2 := by
    exact Or.inr rfl
  have hInSmaller :
      FinKernel.identityProbeFamily2
        FinKernel.finDiscardObservation2 := by
    rw [hEq]
    exact hInLarger
  unfold FinKernel.identityProbeFamily2 FinKernel.singletonProbe at hInSmaller
  have hCard := congrArg
    (fun obs : FinKernel.Observation 2 => obs.1) hInSmaller
  simp [FinKernel.finDiscardObservation2,
    FinKernel.finIdentityObservation2] at hCard

/--
Despite literal family inequality, adding discard to an already admitted
identity probe changes no exact `ProbeEq` judgment on any compatible kernels.
-/
theorem finKernel_identityDiscard_probeFamilyEquivalent :
    FinKernel.ProbeFamilyEquivalent
      FinKernel.identityProbeFamily2
      FinKernel.identityDiscardProbeFamily2 := by
  intro m f g
  constructor
  · intro hIdentity
    have hEq : f = g :=
      (finKernel_identityProbeFamily2_probeEq_iff_eq f g).1 hIdentity
    subst g
    exact finKernel_probeEq_refl _ _
  · intro hBoth
    apply finKernel_probeEq_antitone
      (P := FinKernel.identityProbeFamily2)
      (Q := FinKernel.identityDiscardProbeFamily2)
    · intro obs hObs
      exact Or.inl hObs
    · exact hBoth

/--
Anti-overclaim control: discard alone is strictly weaker on the existing pair
of distinct deterministic binary sources.  Thus discard is redundant only
relative to a family that already contains a stronger separator such as
identity; it is not universally redundant.
-/
theorem finKernel_discard_only_weaker_than_identity_witness :
    FinKernel.ProbeEq (FinKernel.discardDoctrine 2)
      finKernelFirst finKernelSecond ∧
    ¬ FinKernel.ProbeEq FinKernel.identityProbeFamily2
      finKernelFirst finKernelSecond := by
  constructor
  · exact finKernel_discardDoctrine_probeEq_of_valid
      finKernel_first_valid finKernel_second_valid
  · intro hIdentity
    have hEq : finKernelFirst = finKernelSecond :=
      (finKernel_identityProbeFamily2_probeEq_iff_eq
        finKernelFirst finKernelSecond).1 hIdentity
    have hBehavior :
        FinKernel.BehaviorEq finKernelFirst finKernelSecond :=
      (finKernel_behaviorEq_iff_eq finKernelFirst finKernelSecond).2 hEq
    exact finKernel_first_ne_second hBehavior

/--
Acceptance bundle: the two families differ literally, induce the same exact
observational equivalence, and the added discard probe remains nontrivial when
identity is absent.
-/
theorem finKernel_probeFamilyRedundancy_bundle :
    FinKernel.identityProbeFamily2 ≠
        FinKernel.identityDiscardProbeFamily2 ∧
    FinKernel.ProbeFamilyEquivalent
        FinKernel.identityProbeFamily2
        FinKernel.identityDiscardProbeFamily2 ∧
    FinKernel.ProbeEq (FinKernel.discardDoctrine 2)
        finKernelFirst finKernelSecond ∧
    ¬ FinKernel.ProbeEq FinKernel.identityProbeFamily2
        finKernelFirst finKernelSecond := by
  exact ⟨finKernel_identity_and_identityDiscard_families_differ,
    finKernel_identityDiscard_probeFamilyEquivalent,
    finKernel_discard_only_weaker_than_identity_witness.1,
    finKernel_discard_only_weaker_than_identity_witness.2⟩

end RelayTheory
