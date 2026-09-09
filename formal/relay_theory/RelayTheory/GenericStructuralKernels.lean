import RelayTheory.GenericCoherence

namespace RelayTheory

/-- Generic identity is exactly the Dirac kernel of the identity function. -/
theorem finKernel_identity_eq_dirac_id (n : Nat) :
    FinKernel.identity n = FinKernel.dirac (fun x : Fin n => x) := by
  funext x y
  by_cases h : x = y
  · subst y
    simp [FinKernel.identity, FinKernel.dirac]
  · have h' : y ≠ x := by
      intro e
      exact h e.symm
    simp [FinKernel.identity, FinKernel.dirac, h, h']

/-- Independent tensor of deterministic maps is the deterministic product map. -/
theorem finKernel_tensor_dirac {a b c d : Nat}
    (f : Fin a → Fin b) (g : Fin c → Fin d) :
    FinKernel.tensor (FinKernel.dirac f) (FinKernel.dirac g) =
      FinKernel.dirac (fun x =>
        finPairTransport.toFun
          (f (finPairTransport.invFun x).1,
           g (finPairTransport.invFun x).2)) := by
  funext x y
  by_cases h1 : (finPairTransport.invFun y).1 = f (finPairTransport.invFun x).1
  · by_cases h2 : (finPairTransport.invFun y).2 = g (finPairTransport.invFun x).2
    · have hp :
          finPairTransport.invFun y =
            (f (finPairTransport.invFun x).1,
             g (finPairTransport.invFun x).2) :=
        Prod.ext h1 h2
      have hy :
          y = finPairTransport.toFun
            (f (finPairTransport.invFun x).1,
             g (finPairTransport.invFun x).2) := by
        calc
          y = finPairTransport.toFun (finPairTransport.invFun y) :=
            (finPair_flatten_roundtrip y).symm
          _ = finPairTransport.toFun
                (f (finPairTransport.invFun x).1,
                 g (finPairTransport.invFun x).2) :=
                congrArg finPairTransport.toFun hp
      simp [FinKernel.tensor, FinKernel.dirac, hy, finPair_transport_roundtrip]
    · have hyne :
          y ≠ finPairTransport.toFun
            (f (finPairTransport.invFun x).1,
             g (finPairTransport.invFun x).2) := by
        intro hy
        have hd :
            finPairTransport.invFun y =
              (f (finPairTransport.invFun x).1,
               g (finPairTransport.invFun x).2) := by
          calc
            finPairTransport.invFun y =
                finPairTransport.invFun
                  (finPairTransport.toFun
                    (f (finPairTransport.invFun x).1,
                     g (finPairTransport.invFun x).2)) := congrArg _ hy
            _ = (f (finPairTransport.invFun x).1,
                 g (finPairTransport.invFun x).2) :=
                  finPair_transport_roundtrip _
        exact h2 (congrArg Prod.snd hd)
      simp [FinKernel.tensor, FinKernel.dirac, h1, h2, hyne]
  · have hyne :
        y ≠ finPairTransport.toFun
          (f (finPairTransport.invFun x).1,
           g (finPairTransport.invFun x).2) := by
      intro hy
      have hd :
          finPairTransport.invFun y =
            (f (finPairTransport.invFun x).1,
             g (finPairTransport.invFun x).2) := by
        calc
          finPairTransport.invFun y =
              finPairTransport.invFun
                (finPairTransport.toFun
                  (f (finPairTransport.invFun x).1,
                   g (finPairTransport.invFun x).2)) := congrArg _ hy
          _ = (f (finPairTransport.invFun x).1,
               g (finPairTransport.invFun x).2) :=
                finPair_transport_roundtrip _
      exact h1 (congrArg Prod.fst hd)
    simp [FinKernel.tensor, FinKernel.dirac, h1, hyne]

/-- Tensor of generic identities is the identity on the flattened product object. -/
theorem finKernel_tensor_identity (m n : Nat) :
    FinKernel.tensor (FinKernel.identity m) (FinKernel.identity n) =
      FinKernel.identity (m * n) := by
  rw [finKernel_identity_eq_dirac_id m, finKernel_identity_eq_dirac_id n]
  rw [finKernel_tensor_dirac]
  have hfun :
      (fun x : Fin (m * n) =>
        finPairTransport.toFun
          ((finPairTransport.invFun x).1,
           (finPairTransport.invFun x).2)) =
        (fun x : Fin (m * n) => x) := by
    funext x
    exact finPair_flatten_components x
  rw [hfun]
  exact (finKernel_identity_eq_dirac_id (m * n)).symm

namespace FinKernel

/-- Symmetry as an exact deterministic/Dirac stochastic kernel. -/
def symmetry (m n : Nat) : FinKernel (m * n) (n * m) :=
  dirac finSwapTransport.toFun

/-- Left unitor as an exact deterministic/Dirac stochastic kernel. -/
def leftUnitor (n : Nat) : FinKernel (1 * n) n :=
  dirac finLeftUnitTransport.toFun

/-- Right unitor as an exact deterministic/Dirac stochastic kernel. -/
def rightUnitor (n : Nat) : FinKernel (n * 1) n :=
  dirac finRightUnitTransport.toFun

/-- Associator as an exact deterministic/Dirac stochastic kernel. -/
def associator (a b c : Nat) : FinKernel ((a * b) * c) (a * (b * c)) :=
  dirac finAssocTransport.toFun

/-- Generic stochastic discard into the monoidal unit. -/
def discard (n : Nat) : FinKernel n 1 :=
  dirac (fun _ => (0 : Fin 1))

/-- Classical-data copy into the flattened product object. -/
def copy (n : Nat) : FinKernel n (n * n) :=
  dirac (fun x => finPairTransport.toFun (x, x))

end FinKernel

/-- Structural symmetry is stochastic-valid. -/
theorem finKernel_symmetry_valid (m n : Nat) :
    FinKernel.Valid (FinKernel.symmetry m n) :=
  finKernel_dirac_valid _

/-- Structural left unitor is stochastic-valid. -/
theorem finKernel_leftUnitor_valid (n : Nat) :
    FinKernel.Valid (FinKernel.leftUnitor n) :=
  finKernel_dirac_valid _

/-- Structural right unitor is stochastic-valid. -/
theorem finKernel_rightUnitor_valid (n : Nat) :
    FinKernel.Valid (FinKernel.rightUnitor n) :=
  finKernel_dirac_valid _

/-- Structural associator is stochastic-valid. -/
theorem finKernel_associator_valid (a b c : Nat) :
    FinKernel.Valid (FinKernel.associator a b c) :=
  finKernel_dirac_valid _

/-- Generic discard is stochastic-valid. -/
theorem finKernel_discard_valid (n : Nat) :
    FinKernel.Valid (FinKernel.discard n) :=
  finKernel_dirac_valid _

/-- Generic classical-data copy is stochastic-valid. -/
theorem finKernel_copy_valid (n : Nat) :
    FinKernel.Valid (FinKernel.copy n) :=
  finKernel_dirac_valid _

end RelayTheory
