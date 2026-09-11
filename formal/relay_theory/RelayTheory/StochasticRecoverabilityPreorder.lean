import RelayTheory.EpicityReversibility

namespace RelayTheory

namespace FinKernel

/--
`strong` stochastically degrades to `weak` when `weak` is exactly obtainable
from `strong` by one stochastic-valid output post-processing kernel.

No temporal coordinate or causal relation appears in this definition.
-/
def StochasticDegradesTo {n qa qb : Nat}
    (strong : FinKernel n qa) (weak : FinKernel n qb) : Prop :=
  ∃ post : FinKernel qa qb,
    Valid post ∧ compose post strong = weak

/-- Mutual stochastic simulation, kept separate from literal kernel equality. -/
def StochasticEquivalent {n qa qb : Nat}
    (a : FinKernel n qa) (b : FinKernel n qb) : Prop :=
  StochasticDegradesTo a b ∧ StochasticDegradesTo b a

/-- Strict stochastic information loss: forward garbling exists but reverse garbling does not. -/
def StrictStochasticLoss {n qa qb : Nat}
    (a : FinKernel n qa) (b : FinKernel n qb) : Prop :=
  StochasticDegradesTo a b ∧ ¬ StochasticDegradesTo b a

end FinKernel

/-- Stochastic garbling is reflexive via the valid identity output channel. -/
theorem finKernel_stochasticDegradesTo_refl {n q : Nat}
    (obs : FinKernel n q) :
    FinKernel.StochasticDegradesTo obs obs := by
  refine ⟨FinKernel.identity q, finKernel_identity_valid q, ?_⟩
  exact finKernel_compose_identity_after obs

/-- Stochastic garbling is transitive by composing the two valid post-processings. -/
theorem finKernel_stochasticDegradesTo_trans
    {n qa qb qc : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb} {c : FinKernel n qc}
    (hab : FinKernel.StochasticDegradesTo a b)
    (hbc : FinKernel.StochasticDegradesTo b c) :
    FinKernel.StochasticDegradesTo a c := by
  rcases hab with ⟨postAB, hABValid, hAB⟩
  rcases hbc with ⟨postBC, hBCValid, hBC⟩
  refine ⟨FinKernel.compose postBC postAB,
    finKernel_compose_valid hABValid hBCValid, ?_⟩
  calc
    FinKernel.compose (FinKernel.compose postBC postAB) a =
        FinKernel.compose postBC (FinKernel.compose postAB a) :=
      (finKernel_compose_associative a postAB postBC).symm
    _ = FinKernel.compose postBC b := by rw [hAB]
    _ = c := hBC

/-- Validity propagates down a valid stochastic garbling. -/
theorem finKernel_stochasticDegradesTo_preserves_validity
    {n qa qb : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb}
    (ha : FinKernel.Valid a)
    (hab : FinKernel.StochasticDegradesTo a b) :
    FinKernel.Valid b := by
  rcases hab with ⟨post, hpost, hab⟩
  rw [← hab]
  exact finKernel_compose_valid ha hpost

/-- Mutual stochastic simulation is reflexive. -/
theorem finKernel_stochasticEquivalent_refl {n q : Nat}
    (obs : FinKernel n q) :
    FinKernel.StochasticEquivalent obs obs := by
  exact ⟨finKernel_stochasticDegradesTo_refl obs,
    finKernel_stochasticDegradesTo_refl obs⟩

/-- Mutual stochastic simulation is symmetric by definition. -/
theorem finKernel_stochasticEquivalent_symm
    {n qa qb : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb}
    (h : FinKernel.StochasticEquivalent a b) :
    FinKernel.StochasticEquivalent b a := by
  exact ⟨h.2, h.1⟩

/-- Mutual stochastic simulation is transitive. -/
theorem finKernel_stochasticEquivalent_trans
    {n qa qb qc : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb} {c : FinKernel n qc}
    (hab : FinKernel.StochasticEquivalent a b)
    (hbc : FinKernel.StochasticEquivalent b c) :
    FinKernel.StochasticEquivalent a c := by
  exact ⟨finKernel_stochasticDegradesTo_trans hab.1 hbc.1,
    finKernel_stochasticDegradesTo_trans hbc.2 hab.2⟩

/-- The strict part of stochastic garbling is irreflexive. -/
theorem finKernel_strictStochasticLoss_irrefl {n q : Nat}
    (obs : FinKernel n q) :
    ¬ FinKernel.StrictStochasticLoss obs obs := by
  intro h
  exact h.2 h.1

/-- The strict part is asymmetric. -/
theorem finKernel_strictStochasticLoss_asymm
    {n qa qb : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb}
    (hab : FinKernel.StrictStochasticLoss a b) :
    ¬ FinKernel.StrictStochasticLoss b a := by
  intro hba
  exact hab.2 hba.1

/-- The strict part of the stochastic garbling preorder is transitive. -/
theorem finKernel_strictStochasticLoss_trans
    {n qa qb qc : Nat}
    {a : FinKernel n qa} {b : FinKernel n qb} {c : FinKernel n qc}
    (hab : FinKernel.StrictStochasticLoss a b)
    (hbc : FinKernel.StrictStochasticLoss b c) :
    FinKernel.StrictStochasticLoss a c := by
  refine ⟨finKernel_stochasticDegradesTo_trans hab.1 hbc.1, ?_⟩
  intro hca
  have hcb : FinKernel.StochasticDegradesTo c b :=
    finKernel_stochasticDegradesTo_trans hca hab.1
  exact hbc.2 hcb

/-- Identity can be stochastically post-processed into the deterministic binary flip. -/
theorem finIdentity2_degradesTo_flip :
    FinKernel.StochasticDegradesTo
      (FinKernel.identity 2) (FinKernel.dirac finFlip2) := by
  refine ⟨FinKernel.dirac finFlip2, finKernel_dirac_valid finFlip2, ?_⟩
  exact finKernel_compose_identity_before (FinKernel.dirac finFlip2)

/-- The binary flip can be stochastically post-processed back into identity. -/
theorem finFlip2_degradesTo_identity :
    FinKernel.StochasticDegradesTo
      (FinKernel.dirac finFlip2) (FinKernel.identity 2) := by
  exact ⟨FinKernel.dirac finFlip2,
    finKernel_dirac_valid finFlip2,
    finFlip2_dirac_self_inverse⟩

/-- Identity and flip are distinct kernels despite mutual stochastic simulation. -/
theorem finIdentity2_ne_flip :
    FinKernel.identity 2 ≠ FinKernel.dirac finFlip2 := by
  intro h
  have hv := congrFun (congrFun h (0 : Fin 2)) (0 : Fin 2)
  simp [FinKernel.identity, FinKernel.dirac, finFlip2] at hv

/-- Raw kernel equality is therefore not antisymmetric under stochastic garbling. -/
theorem finKernel_stochasticDegradesTo_not_antisymmetric :
    ∃ a b : FinKernel 2 2,
      FinKernel.StochasticDegradesTo a b ∧
      FinKernel.StochasticDegradesTo b a ∧
      a ≠ b := by
  exact ⟨FinKernel.identity 2, FinKernel.dirac finFlip2,
    finIdentity2_degradesTo_flip,
    finFlip2_degradesTo_identity,
    finIdentity2_ne_flip⟩

/-- Identity stochastically degrades to the noisy binary observation. -/
theorem finIdentity2_degradesTo_noisy :
    FinKernel.StochasticDegradesTo (FinKernel.identity 2) finNoisyEpic2 := by
  refine ⟨finNoisyEpic2, finNoisyEpic2_valid, ?_⟩
  exact finKernel_compose_identity_before finNoisyEpic2

/-- A stochastic degradation from noisy back to identity is exactly a valid stochastic recovery. -/
theorem finNoisyEpic2_degradesTo_identity_iff_validRecovery :
    FinKernel.StochasticDegradesTo finNoisyEpic2 (FinKernel.identity 2) ↔
      FinKernel.HasValidStochasticRecovery finNoisyEpic2 := by
  rfl

/-- The noisy observation cannot stochastically degrade back to identity. -/
theorem finNoisyEpic2_not_degradesTo_identity :
    ¬ FinKernel.StochasticDegradesTo finNoisyEpic2 (FinKernel.identity 2) := by
  rw [finNoisyEpic2_degradesTo_identity_iff_validRecovery]
  exact finNoisyEpic2_not_hasValidStochasticRecovery

/-- The noisy channel is a strict stochastic information loss from identity. -/
theorem finIdentity2_strictLoss_noisy :
    FinKernel.StrictStochasticLoss (FinKernel.identity 2) finNoisyEpic2 := by
  exact ⟨finIdentity2_degradesTo_noisy,
    finNoisyEpic2_not_degradesTo_identity⟩

/--
Critical F1 discriminator: strict stochastic loss survives even though the noisy
observation has an exact signed algebraic recovery kernel.
-/
theorem finNoisy_exactRecovery_with_strictStochasticLoss :
    FinKernel.HasExactRecovery finNoisyEpic2 ∧
      FinKernel.StrictStochasticLoss (FinKernel.identity 2) finNoisyEpic2 := by
  exact ⟨finNoisyEpic2_hasExactRecovery, finIdentity2_strictLoss_noisy⟩

/-- Identity and deterministic flip are stochastically equivalent. -/
theorem finIdentity2_flip_stochasticEquivalent :
    FinKernel.StochasticEquivalent
      (FinKernel.identity 2) (FinKernel.dirac finFlip2) := by
  exact ⟨finIdentity2_degradesTo_flip, finFlip2_degradesTo_identity⟩

/-- Therefore no strict information arrow exists from identity to reversible flip. -/
theorem finIdentity2_not_strictLoss_flip :
    ¬ FinKernel.StrictStochasticLoss
      (FinKernel.identity 2) (FinKernel.dirac finFlip2) := by
  intro h
  exact h.2 finFlip2_degradesTo_identity

/-- Nor does a strict information arrow exist in the reverse direction. -/
theorem finFlip2_not_strictLoss_identity :
    ¬ FinKernel.StrictStochasticLoss
      (FinKernel.dirac finFlip2) (FinKernel.identity 2) := by
  intro h
  exact h.2 finIdentity2_degradesTo_flip

/--
Acceptance bundle for the atemporal stochastic-recoverability transaction.
It deliberately earns an information preorder/strict part, not a time order.
-/
theorem finKernel_stochasticRecoverabilityPreorder_bundle :
    (∀ {n q : Nat} (obs : FinKernel n q),
      FinKernel.StochasticDegradesTo obs obs) ∧
    (∀ {n qa qb qc : Nat}
      {a : FinKernel n qa} {b : FinKernel n qb} {c : FinKernel n qc},
      FinKernel.StochasticDegradesTo a b →
      FinKernel.StochasticDegradesTo b c →
      FinKernel.StochasticDegradesTo a c) ∧
    (∃ a b : FinKernel 2 2,
      FinKernel.StochasticDegradesTo a b ∧
      FinKernel.StochasticDegradesTo b a ∧ a ≠ b) ∧
    FinKernel.HasExactRecovery finNoisyEpic2 ∧
    FinKernel.StrictStochasticLoss (FinKernel.identity 2) finNoisyEpic2 ∧
    FinKernel.StochasticEquivalent
      (FinKernel.identity 2) (FinKernel.dirac finFlip2) ∧
    (¬ FinKernel.StrictStochasticLoss
      (FinKernel.identity 2) (FinKernel.dirac finFlip2)) := by
  exact ⟨finKernel_stochasticDegradesTo_refl,
    finKernel_stochasticDegradesTo_trans,
    finKernel_stochasticDegradesTo_not_antisymmetric,
    finNoisyEpic2_hasExactRecovery,
    finIdentity2_strictLoss_noisy,
    finIdentity2_flip_stochasticEquivalent,
    finIdentity2_not_strictLoss_flip⟩

end RelayTheory
