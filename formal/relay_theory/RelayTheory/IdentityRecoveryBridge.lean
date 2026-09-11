import RelayTheory.CorrelationCarrier

namespace RelayTheory

/--
Source identity stochastically degrades to a channel exactly when that channel
is itself stochastic-valid.
-/
theorem finKernel_identity_degradesTo_iff_valid
    {a q : Nat} (k : FinKernel a q) :
    FinKernel.StochasticDegradesTo (FinKernel.identity a) k ↔
      FinKernel.Valid k := by
  constructor
  · intro h
    exact finKernel_stochasticDegradesTo_preserves_validity
      (finKernel_identity_valid a) h
  · intro hk
    exact ⟨k, hk, finKernel_compose_identity_before k⟩

/--
A channel stochastically degrades back to source identity exactly when it has a
valid stochastic source recovery. This is the same existential interface, not a
new recoverability primitive.
-/
theorem finKernel_degradesTo_identity_iff_validRecovery
    {a q : Nat} (k : FinKernel a q) :
    FinKernel.StochasticDegradesTo k (FinKernel.identity a) ↔
      FinKernel.HasValidStochasticRecovery k := by
  rfl

/--
Generic identity-experiment bridge: mutual stochastic simulation with source
identity is exactly channel validity plus valid stochastic source recovery.
-/
theorem finKernel_stochasticEquivalent_identity_iff
    {a q : Nat} (k : FinKernel a q) :
    FinKernel.StochasticEquivalent k (FinKernel.identity a) ↔
      FinKernel.Valid k ∧ FinKernel.HasValidStochasticRecovery k := by
  constructor
  · intro h
    exact ⟨
      (finKernel_identity_degradesTo_iff_valid k).1 h.2,
      (finKernel_degradesTo_identity_iff_validRecovery k).1 h.1⟩
  · rintro ⟨hkValid, hkRecover⟩
    exact ⟨
      (finKernel_degradesTo_identity_iff_validRecovery k).2 hkRecover,
      (finKernel_identity_degradesTo_iff_valid k).2 hkValid⟩

/--
For an already valid channel, Blackwell-style equivalence to source identity is
exactly valid stochastic source recoverability.
-/
theorem finKernel_valid_stochasticEquivalent_identity_iff_recovery
    {a q : Nat} {k : FinKernel a q}
    (hk : FinKernel.Valid k) :
    FinKernel.StochasticEquivalent k (FinKernel.identity a) ↔
      FinKernel.HasValidStochasticRecovery k := by
  rw [finKernel_stochasticEquivalent_identity_iff k]
  simp [hk]

/--
The noisy binary channel remains excluded despite exact signed algebraic
recovery: it is valid, but not stochastically equivalent to source identity.
-/
theorem finNoisyEpic2_not_stochasticEquivalent_identity :
    ¬ FinKernel.StochasticEquivalent finNoisyEpic2 (FinKernel.identity 2) := by
  rw [finKernel_valid_stochasticEquivalent_identity_iff_recovery finNoisyEpic2_valid]
  exact finNoisyEpic2_not_hasValidStochasticRecovery

/-- The reversible deterministic flip remains a positive identity-equivalence control. -/
theorem finFlip2_stochasticEquivalent_identity_via_bridge :
    FinKernel.StochasticEquivalent (FinKernel.dirac finFlip2) (FinKernel.identity 2) := by
  apply (finKernel_valid_stochasticEquivalent_identity_iff_recovery
    (finKernel_dirac_valid finFlip2)).2
  exact finFlip2_dirac_hasValidStochasticRecovery

/-- The merged correlation carrier is another positive instance of the generic bridge. -/
theorem correlationCarrier_stochasticEquivalent_identity_via_bridge :
    FinKernel.StochasticEquivalent correlationCarrier (FinKernel.identity 2) := by
  apply (finKernel_valid_stochasticEquivalent_identity_iff_recovery
    correlationCarrier_valid).2
  exact correlationCarrier_hasValidStochasticRecovery

/--
Level-B acceptance bundle for the identity-experiment recovery bridge.
No temporal, causal, thermodynamic or ontological content is added.
-/
theorem finKernel_identityRecoveryBridge_bundle :
    (∀ {a q : Nat} (k : FinKernel a q),
      FinKernel.StochasticDegradesTo (FinKernel.identity a) k ↔
        FinKernel.Valid k) ∧
    (∀ {a q : Nat} (k : FinKernel a q),
      FinKernel.StochasticDegradesTo k (FinKernel.identity a) ↔
        FinKernel.HasValidStochasticRecovery k) ∧
    (∀ {a q : Nat} (k : FinKernel a q),
      FinKernel.StochasticEquivalent k (FinKernel.identity a) ↔
        FinKernel.Valid k ∧ FinKernel.HasValidStochasticRecovery k) ∧
    FinKernel.HasExactRecovery finNoisyEpic2 ∧
    (¬ FinKernel.StochasticEquivalent finNoisyEpic2 (FinKernel.identity 2)) ∧
    FinKernel.StochasticEquivalent correlationCarrier (FinKernel.identity 2) := by
  exact ⟨
    finKernel_identity_degradesTo_iff_valid,
    finKernel_degradesTo_identity_iff_validRecovery,
    finKernel_stochasticEquivalent_identity_iff,
    finNoisyEpic2_hasExactRecovery,
    finNoisyEpic2_not_stochasticEquivalent_identity,
    correlationCarrier_stochasticEquivalent_identity_via_bridge⟩

end RelayTheory
