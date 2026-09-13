import RelayTheory.ActionQuotientSufficiency

namespace RelayTheory

namespace FinKernel

/--
Every contextual-action class realized by `K` is also realized by `L`, measured
using the contextual equivalence relation of the source frame `K`.  Literal
generated kernels need not coincide.
-/
def GeneratedClassCovered {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  ∀ k : FinKernel n n,
    GeneratedContext K k →
      ∃ l : FinKernel n n,
        GeneratedContext L l ∧ ContextualActionEq P K k l

/--
Two access frames have the same realized contextual-action support when they
induce the same action partition and mutually cover each other's generated
classes.  This is intentionally weaker than literal/generated-domain equality.
-/
def AccessClassSupportEq {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) : Prop :=
  AccessActionEq P K L ∧
  GeneratedClassCovered P K L ∧
  GeneratedClassCovered P L K

/--
Cross-frame relation between reachable complete-response states induced by a
common contextual-action class.  The representatives are existential witnesses;
no representative-selection function is introduced.
-/
def ReachableClassRel {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n)
    (s : FullFutureResponseSpace P K)
    (t : FullFutureResponseSpace P L) : Prop :=
  ∃ k : FinKernel n n,
    ∃ hk : GeneratedContext K k,
      ∃ l : FinKernel n n,
        ∃ hl : GeneratedContext L l,
          FullFutureResponseSpaceEq s (FullFutureResponse P K k) ∧
          FullFutureResponseSpaceEq t (FullFutureResponse P L l) ∧
          ContextualActionEq P K k l

/--
Relation-level packaging of reachable dynamics across two frames.  This is a
proof interface only: it does not select canonical representatives or claim a
new ontological state carrier.
-/
structure ReachableClassDynamicsCorrespondence {n : Nat}
    (P : ProbeFamily n) (K L : FutureContextFamily n) where
  rel : FullFutureResponseSpace P K → FullFutureResponseSpace P L → Prop
  total_left : ∀ {s}, ReachableResidualState P K s →
    ∃ t, ReachableResidualState P L t ∧ rel s t
  total_right : ∀ {t}, ReachableResidualState P L t →
    ∃ s, ReachableResidualState P K s ∧ rel s t
  right_functional : ∀ {s t u}, rel s t → rel s u →
    FullFutureResponseSpaceEq t u
  left_functional : ∀ {s u t}, rel s t → rel u t →
    FullFutureResponseSpaceEq s u
  root : rel (ResidualIdentityState P K) (ResidualIdentityState P L)
  successor_forward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P K sK tK uK →
    SourceSubstitutionSuccessorRel P L sL tL uL
  successor_backward : ∀ {sK tK uK sL tL uL},
    rel sK sL → rel tK tL → rel uK uL →
    SourceSubstitutionSuccessorRel P L sL tL uL →
    SourceSubstitutionSuccessorRel P K sK tK uK

end FinKernel

/-- Generated-class coverage is reflexive. -/
theorem finKernel_generatedClassCovered_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.GeneratedClassCovered P K K := by
  intro k hk
  exact ⟨k, hk, finKernel_contextualActionEq_refl P K k⟩

/-- Common realized-class support is reflexive. -/
theorem finKernel_accessClassSupportEq_refl {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K : FinKernel.FutureContextFamily n) :
    FinKernel.AccessClassSupportEq P K K := by
  exact ⟨finKernel_accessActionEq_refl P K,
    finKernel_generatedClassCovered_refl P K,
    finKernel_generatedClassCovered_refl P K⟩

/-- Common realized-class support is symmetric. -/
theorem finKernel_accessClassSupportEq_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (h : FinKernel.AccessClassSupportEq P K L) :
    FinKernel.AccessClassSupportEq P L K := by
  exact ⟨finKernel_accessActionEq_symm h.1, h.2.2, h.2.1⟩

/--
Coverage composes once the source and intermediate action partitions are known
to coincide.
-/
theorem finKernel_generatedClassCovered_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hAction : FinKernel.AccessActionEq P K L)
    (hKL : FinKernel.GeneratedClassCovered P K L)
    (hLM : FinKernel.GeneratedClassCovered P L M) :
    FinKernel.GeneratedClassCovered P K M := by
  intro k hk
  rcases hKL k hk with ⟨l, hl, hkl⟩
  rcases hLM l hl with ⟨m, hm, hlmL⟩
  have hlmK : FinKernel.ContextualActionEq P K l m :=
    hAction.1 l m hlmL
  exact ⟨m, hm, finKernel_contextualActionEq_trans hkl hlmK⟩

/-- Common realized-class support is transitive. -/
theorem finKernel_accessClassSupportEq_trans {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L M : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.AccessClassSupportEq P K L)
    (hLM : FinKernel.AccessClassSupportEq P L M) :
    FinKernel.AccessClassSupportEq P K M := by
  refine ⟨finKernel_accessActionEq_trans hKL.1 hLM.1, ?_, ?_⟩
  · exact finKernel_generatedClassCovered_trans
      hKL.1 hKL.2.1 hLM.2.1
  · exact finKernel_generatedClassCovered_trans
      (finKernel_accessActionEq_symm hLM.1) hLM.2.2 hKL.2.2

/-- Generated-domain equality is sufficient for common realized-class support. -/
theorem finKernel_generatedDomainEq_implies_accessClassSupportEq {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hKL : FinKernel.GeneratedDomainEq K L) :
    FinKernel.AccessClassSupportEq P K L := by
  have hLeKL : FinKernel.GeneratedDomainLe K L :=
    fun c hc => (hKL c).1 hc
  have hLeLK : FinKernel.GeneratedDomainLe L K :=
    fun c hc => (hKL c).2 hc
  refine ⟨⟨finKernel_generatedDomainLe_implies_accessActionRefines hLeKL,
      finKernel_generatedDomainLe_implies_accessActionRefines hLeLK⟩,
    ?_, ?_⟩
  · intro k hk
    exact ⟨k, hLeKL k hk, finKernel_contextualActionEq_refl P K k⟩
  · intro l hl
    exact ⟨l, hLeLK l hl, finKernel_contextualActionEq_refl P L l⟩

/--
#2861 negative control: the empty and safe frames have the same all-probes
action partition but do not have the same realized-class support.
-/
theorem finKernel_allProbes_empty_safe_not_accessClassSupportEq :
    ¬ FinKernel.AccessClassSupportEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 := by
  intro hSupport
  rcases hSupport.2.2
      (FinKernel.dirac finCollapseHidden3)
      finKernel_merge01_collapse_generated_safe with
    ⟨l, hlEmpty, hCollapseL⟩
  have hLiteral : FinKernel.dirac finCollapseHidden3 = l :=
    (finKernel_contextualActionEq_allProbes_iff_eq
      FinKernel.merge01SafeContextFamily3
      (FinKernel.dirac finCollapseHidden3) l).1 hCollapseL
  have hIdentity : l = FinKernel.identity 3 :=
    (finKernel_generatedContext_empty_iff_identity).1 hlEmpty
  exact finKernel_identity3_ne_hidden_collapse
    (hLiteral.trans hIdentity).symm

/--
Replacing K-generated representatives by L-generated representatives from the
same common classes preserves both generated composite support and the
composite contextual class.  No quotient multiplication is separately added.
-/
theorem finKernel_accessClassSupportEq_composite_bridge {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {k l k' l' : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hl : FinKernel.GeneratedContext K l)
    (hk' : FinKernel.GeneratedContext L k')
    (hl' : FinKernel.GeneratedContext L l')
    (hkk' : FinKernel.ContextualActionEq P K k k')
    (hll' : FinKernel.ContextualActionEq P K l l') :
    FinKernel.GeneratedContext K (FinKernel.compose l k) ∧
    FinKernel.GeneratedContext L (FinKernel.compose l' k') ∧
    FinKernel.ContextualActionEq P K
      (FinKernel.compose l k) (FinKernel.compose l' k') ∧
    FinKernel.ContextualActionEq P L
      (FinKernel.compose l k) (FinKernel.compose l' k') := by
  have hCompK : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k) (FinKernel.compose l' k') :=
    finKernel_contextualActionEq_compose_respects_representatives
      hkk' hll' hl
  have hCompL : FinKernel.ContextualActionEq P L
      (FinKernel.compose l k) (FinKernel.compose l' k') :=
    hSupport.1.2 _ _ hCompK
  exact ⟨finKernel_generatedContext_compose hk hl,
    finKernel_generatedContext_compose hk' hl', hCompK, hCompL⟩

/-- Every left state appearing in the cross-frame class relation is reachable. -/
theorem finKernel_reachableClassRel_left_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    {s : FinKernel.FullFutureResponseSpace P K}
    {t : FinKernel.FullFutureResponseSpace P L}
    (h : FinKernel.ReachableClassRel P K L s t) :
    FinKernel.ReachableResidualState P K s := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hkl⟩
  refine ⟨k, hk, ?_⟩
  exact finKernel_fullFutureResponseSpaceEq_trans hs
    (finKernel_fullFutureResponseSpaceEq_symm
      (finKernel_identityResidualState_eq_fullFutureResponse
        (P := P) hk))

/-- Every right state appearing in the cross-frame class relation is reachable. -/
theorem finKernel_reachableClassRel_right_reachable {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    {s : FinKernel.FullFutureResponseSpace P K}
    {t : FinKernel.FullFutureResponseSpace P L}
    (h : FinKernel.ReachableClassRel P K L s t) :
    FinKernel.ReachableResidualState P L t := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hkl⟩
  refine ⟨l, hl, ?_⟩
  exact finKernel_fullFutureResponseSpaceEq_trans ht
    (finKernel_fullFutureResponseSpaceEq_symm
      (finKernel_identityResidualState_eq_fullFutureResponse
        (P := P) hl))

/-- The cross-frame reachable-class relation reverses under support symmetry. -/
theorem finKernel_reachableClassRel_symm {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {s : FinKernel.FullFutureResponseSpace P K}
    {t : FinKernel.FullFutureResponseSpace P L}
    (h : FinKernel.ReachableClassRel P K L s t) :
    FinKernel.ReachableClassRel P L K t s := by
  rcases h with ⟨k, hk, l, hl, hs, ht, hklK⟩
  have hklL : FinKernel.ContextualActionEq P L k l :=
    hSupport.1.2 k l hklK
  exact ⟨l, hl, k, hk, ht, hs,
    finKernel_contextualActionEq_symm hklL⟩

/-- Common support relates every K-reachable state to some L-reachable state. -/
theorem finKernel_reachableClassRel_total_left {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {s : FinKernel.FullFutureResponseSpace P K}
    (hs : FinKernel.ReachableResidualState P K s) :
    ∃ t : FinKernel.FullFutureResponseSpace P L,
      FinKernel.ReachableResidualState P L t ∧
      FinKernel.ReachableClassRel P K L s t := by
  rcases finKernel_reachableResidualState_has_generated_signature hs with
    ⟨k, hk, hsk⟩
  rcases hSupport.2.1 k hk with ⟨l, hl, hkl⟩
  refine ⟨FinKernel.FullFutureResponse P L l,
    finKernel_generated_signature_reachableResidualState hl, ?_⟩
  exact ⟨k, hk, l, hl, hsk,
    finKernel_fullFutureResponseSpaceEq_refl _, hkl⟩

/-- Common support relates every L-reachable state to some K-reachable state. -/
theorem finKernel_reachableClassRel_total_right {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {t : FinKernel.FullFutureResponseSpace P L}
    (ht : FinKernel.ReachableResidualState P L t) :
    ∃ s : FinKernel.FullFutureResponseSpace P K,
      FinKernel.ReachableResidualState P K s ∧
      FinKernel.ReachableClassRel P K L s t := by
  have hSym := finKernel_accessClassSupportEq_symm hSupport
  rcases finKernel_reachableClassRel_total_left hSym ht with
    ⟨s, hs, hRel⟩
  exact ⟨s, hs, finKernel_reachableClassRel_symm hSym hRel⟩

/-- The cross-frame relation is functional on the right up to response equality. -/
theorem finKernel_reachableClassRel_right_functional {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {s : FinKernel.FullFutureResponseSpace P K}
    {t u : FinKernel.FullFutureResponseSpace P L}
    (hst : FinKernel.ReachableClassRel P K L s t)
    (hsu : FinKernel.ReachableClassRel P K L s u) :
    FinKernel.FullFutureResponseSpaceEq t u := by
  rcases hst with ⟨k, hk, l, hl, hsk, htl, hkl⟩
  rcases hsu with ⟨k', hk', l', hl', hsk', hul', hk'l'⟩
  have hkkResponse : FinKernel.FullFutureResponseEq P K k k' :=
    finKernel_fullFutureResponseSpaceEq_trans
      (finKernel_fullFutureResponseSpaceEq_symm hsk) hsk'
  have hkk : FinKernel.ContextualActionEq P K k k' :=
    (finKernel_contextualActionEq_iff_fullFutureResponseEq).2 hkkResponse
  have hllK : FinKernel.ContextualActionEq P K l l' :=
    finKernel_contextualActionEq_trans
      (finKernel_contextualActionEq_symm hkl)
      (finKernel_contextualActionEq_trans hkk hk'l')
  have hllL : FinKernel.ContextualActionEq P L l l' :=
    hSupport.1.2 l l' hllK
  have hllResponse : FinKernel.FullFutureResponseEq P L l l' :=
    (finKernel_contextualActionEq_iff_fullFutureResponseEq).1 hllL
  exact finKernel_fullFutureResponseSpaceEq_trans htl
    (finKernel_fullFutureResponseSpaceEq_trans hllResponse
      (finKernel_fullFutureResponseSpaceEq_symm hul'))

/-- The cross-frame relation is functional on the left up to response equality. -/
theorem finKernel_reachableClassRel_left_functional {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {s u : FinKernel.FullFutureResponseSpace P K}
    {t : FinKernel.FullFutureResponseSpace P L}
    (hst : FinKernel.ReachableClassRel P K L s t)
    (hut : FinKernel.ReachableClassRel P K L u t) :
    FinKernel.FullFutureResponseSpaceEq s u := by
  have hSym := finKernel_accessClassSupportEq_symm hSupport
  exact finKernel_reachableClassRel_right_functional hSym
    (finKernel_reachableClassRel_symm hSupport hst)
    (finKernel_reachableClassRel_symm hSupport hut)

/-- Distinguished residual roots are related by the common identity class. -/
theorem finKernel_reachableClassRel_root {n : Nat}
    (P : FinKernel.ProbeFamily n)
    (K L : FinKernel.FutureContextFamily n) :
    FinKernel.ReachableClassRel P K L
      (FinKernel.ResidualIdentityState P K)
      (FinKernel.ResidualIdentityState P L) := by
  refine ⟨FinKernel.identity n, FinKernel.GeneratedContext.identity,
    FinKernel.identity n, FinKernel.GeneratedContext.identity, ?_, ?_,
    finKernel_contextualActionEq_refl P K (FinKernel.identity n)⟩
  · change FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState P K (FinKernel.identity n)
        FinKernel.GeneratedContext.identity)
      (FinKernel.FullFutureResponse P K (FinKernel.identity n))
    exact finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) FinKernel.GeneratedContext.identity
  · change FinKernel.FullFutureResponseSpaceEq
      (FinKernel.IdentityResidualState P L (FinKernel.identity n)
        FinKernel.GeneratedContext.identity)
      (FinKernel.FullFutureResponse P L (FinKernel.identity n))
    exact finKernel_identityResidualState_eq_fullFutureResponse
      (P := P) FinKernel.GeneratedContext.identity

/--
A source-substitution successor whose inputs are represented by generated
kernels has the response signature of their literal sequential composite.
-/
theorem finKernel_sourceSubstitutionSuccessorRel_to_composite_signature
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K : FinKernel.FutureContextFamily n}
    {s t u : FinKernel.FullFutureResponseSpace P K}
    {k l : FinKernel n n}
    (hk : FinKernel.GeneratedContext K k)
    (hs : FinKernel.FullFutureResponseSpaceEq s
      (FinKernel.FullFutureResponse P K k))
    (ht : FinKernel.FullFutureResponseSpaceEq t
      (FinKernel.FullFutureResponse P K l))
    (hSucc : FinKernel.SourceSubstitutionSuccessorRel P K s t u) :
    FinKernel.FullFutureResponseSpaceEq u
      (FinKernel.FullFutureResponse P K (FinKernel.compose l k)) := by
  have hAtSource := hSucc k ⟨hk, hs⟩
  have hSubT := finKernel_sourceSubstituteResponse_respects_response_eq
    (P := P) (K := K) k ht
  have hSubSignature := finKernel_sourceSubstituteResponse_fullFutureResponse
    (P := P) (K := K) k l
  exact finKernel_fullFutureResponseSpaceEq_trans hAtSource
    (finKernel_fullFutureResponseSpaceEq_trans hSubT hSubSignature)

/--
Common action partition plus common realized-class support preserves intrinsic
source-substitution successor dynamics from K to L.
-/
theorem finKernel_reachableClassRel_successor_forward {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {sK tK uK : FinKernel.FullFutureResponseSpace P K}
    {sL tL uL : FinKernel.FullFutureResponseSpace P L}
    (hsRel : FinKernel.ReachableClassRel P K L sK sL)
    (htRel : FinKernel.ReachableClassRel P K L tK tL)
    (huRel : FinKernel.ReachableClassRel P K L uK uL)
    (hSuccK : FinKernel.SourceSubstitutionSuccessorRel P K sK tK uK) :
    FinKernel.SourceSubstitutionSuccessorRel P L sL tL uL := by
  rcases hsRel with ⟨k, hk, kL, hkL, hsK, hsL, hkCross⟩
  rcases htRel with ⟨l, hl, lL, hlL, htK, htL, hlCross⟩
  rcases huRel with ⟨r, hr, rL, hrL, huK, huL, hrCross⟩
  have huCompK : FinKernel.FullFutureResponseSpaceEq uK
      (FinKernel.FullFutureResponse P K (FinKernel.compose l k)) :=
    finKernel_sourceSubstitutionSuccessorRel_to_composite_signature
      hk hsK htK hSuccK
  have hrCompResponseK : FinKernel.FullFutureResponseEq P K r
      (FinKernel.compose l k) :=
    finKernel_fullFutureResponseSpaceEq_trans
      (finKernel_fullFutureResponseSpaceEq_symm huK) huCompK
  have hrCompK : FinKernel.ContextualActionEq P K r
      (FinKernel.compose l k) :=
    (finKernel_contextualActionEq_iff_fullFutureResponseEq).2
      hrCompResponseK
  have hBridge := finKernel_accessClassSupportEq_composite_bridge
    hSupport hk hl hkL hlL hkCross hlCross
  have hCompCrossK : FinKernel.ContextualActionEq P K
      (FinKernel.compose l k) (FinKernel.compose lL kL) :=
    hBridge.2.2.1
  have hrLCompK : FinKernel.ContextualActionEq P K rL
      (FinKernel.compose lL kL) :=
    finKernel_contextualActionEq_trans
      (finKernel_contextualActionEq_symm hrCross)
      (finKernel_contextualActionEq_trans hrCompK hCompCrossK)
  have hrLCompL : FinKernel.ContextualActionEq P L rL
      (FinKernel.compose lL kL) :=
    hSupport.1.2 rL (FinKernel.compose lL kL) hrLCompK
  have hrLCompResponseL : FinKernel.FullFutureResponseEq P L rL
      (FinKernel.compose lL kL) :=
    (finKernel_contextualActionEq_iff_fullFutureResponseEq).1 hrLCompL
  have huCompL : FinKernel.FullFutureResponseSpaceEq uL
      (FinKernel.FullFutureResponse P L (FinKernel.compose lL kL)) :=
    finKernel_fullFutureResponseSpaceEq_trans huL hrLCompResponseL
  have hsIdL : FinKernel.FullFutureResponseSpaceEq sL
      (FinKernel.IdentityResidualState P L kL hkL) :=
    finKernel_fullFutureResponseSpaceEq_trans hsL
      (finKernel_fullFutureResponseSpaceEq_symm
        (finKernel_identityResidualState_eq_fullFutureResponse
          (P := P) hkL))
  have htIdL : FinKernel.FullFutureResponseSpaceEq tL
      (FinKernel.IdentityResidualState P L lL hlL) :=
    finKernel_fullFutureResponseSpaceEq_trans htL
      (finKernel_fullFutureResponseSpaceEq_symm
        (finKernel_identityResidualState_eq_fullFutureResponse
          (P := P) hlL))
  have huIdL : FinKernel.FullFutureResponseSpaceEq uL
      (FinKernel.IdentityResidualState P L (FinKernel.compose lL kL)
        (finKernel_generatedContext_compose hkL hlL)) :=
    finKernel_fullFutureResponseSpaceEq_trans huCompL
      (finKernel_fullFutureResponseSpaceEq_symm
        (finKernel_identityResidualState_eq_fullFutureResponse
          (P := P) (finKernel_generatedContext_compose hkL hlL)))
  have hResidual : FinKernel.ResidualComposeRel P L sL tL uL :=
    ⟨kL, hkL, lL, hlL, hsIdL, htIdL, huIdL⟩
  have htReach : FinKernel.ReachableResidualState P L tL :=
    ⟨lL, hlL, htIdL⟩
  exact finKernel_residualComposeRel_implies_sourceSubstitutionSuccessorRel
    htReach hResidual

/-- The same relational correspondence reflects intrinsic successor dynamics. -/
theorem finKernel_reachableClassRel_successor_backward {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L)
    {sK tK uK : FinKernel.FullFutureResponseSpace P K}
    {sL tL uL : FinKernel.FullFutureResponseSpace P L}
    (hsRel : FinKernel.ReachableClassRel P K L sK sL)
    (htRel : FinKernel.ReachableClassRel P K L tK tL)
    (huRel : FinKernel.ReachableClassRel P K L uK uL)
    (hSuccL : FinKernel.SourceSubstitutionSuccessorRel P L sL tL uL) :
    FinKernel.SourceSubstitutionSuccessorRel P K sK tK uK := by
  have hSym := finKernel_accessClassSupportEq_symm hSupport
  exact finKernel_reachableClassRel_successor_forward hSym
    (finKernel_reachableClassRel_symm hSupport hsRel)
    (finKernel_reachableClassRel_symm hSupport htRel)
    (finKernel_reachableClassRel_symm hSupport huRel)
    hSuccL

/--
Construct the full relation-level dynamics correspondence from common action
partition plus realized-class support, without selecting representatives.
-/
def finKernel_reachableClassDynamicsCorrespondence_of_accessClassSupportEq
    {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L) :
    FinKernel.ReachableClassDynamicsCorrespondence P K L := by
  exact {
    rel := FinKernel.ReachableClassRel P K L
    total_left := finKernel_reachableClassRel_total_left hSupport
    total_right := finKernel_reachableClassRel_total_right hSupport
    right_functional := finKernel_reachableClassRel_right_functional hSupport
    left_functional := finKernel_reachableClassRel_left_functional hSupport
    root := finKernel_reachableClassRel_root P K L
    successor_forward := finKernel_reachableClassRel_successor_forward hSupport
    successor_backward := finKernel_reachableClassRel_successor_backward hSupport
  }

/--
Main positive Level-B target for #2864: common action partition plus common
realized generated classes determines the reachable dynamics relation up to
extensional response equality.  This theorem does not construct the stronger
function-valued `AccessEfficacyEq` interface and uses no representative choice.
-/
theorem finKernel_accessClassSupportEq_implies_relationalDynamics {n : Nat}
    {P : FinKernel.ProbeFamily n}
    {K L : FinKernel.FutureContextFamily n}
    (hSupport : FinKernel.AccessClassSupportEq P K L) :
    Nonempty (FinKernel.ReachableClassDynamicsCorrespondence P K L) := by
  exact ⟨finKernel_reachableClassDynamicsCorrespondence_of_accessClassSupportEq
    hSupport⟩

/-- Acceptance bundle for the first #2864 transaction. -/
theorem finKernel_reachable_class_support_sufficiency_bundle :
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.GeneratedDomainEq K L →
      FinKernel.AccessClassSupportEq P K L) ∧
    FinKernel.AccessActionEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    ¬ FinKernel.AccessClassSupportEq
      (FinKernel.allProbes 3)
      (FinKernel.emptyFutureContextFamily 3)
      FinKernel.merge01SafeContextFamily3 ∧
    (∀ {n : Nat}
      {P : FinKernel.ProbeFamily n}
      {K L : FinKernel.FutureContextFamily n},
      FinKernel.AccessClassSupportEq P K L →
      Nonempty (FinKernel.ReachableClassDynamicsCorrespondence P K L)) := by
  exact ⟨finKernel_generatedDomainEq_implies_accessClassSupportEq,
    finKernel_allProbes_accessActionEq _ _,
    finKernel_allProbes_empty_safe_not_accessClassSupportEq,
    finKernel_accessClassSupportEq_implies_relationalDynamics⟩

end RelayTheory
