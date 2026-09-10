import RelayTheory.StochasticObservationKernels

namespace RelayTheory

namespace FinKernel

/-- Extensional finite-kernel determinism: the kernel is exactly a Dirac map. -/
def DeterministicKernel {m n : Nat} (k : FinKernel m n) : Prop :=
  ∃ f : Fin m → Fin n, k = dirac f

end FinKernel

/-- The constructive product encoding is injective because its inverse is exact. -/
theorem finPairTransport_toFun_injective {m n : Nat}
    {a b : Fin m × Fin n}
    (h : finPairTransport.toFun a = finPairTransport.toFun b) :
    a = b := by
  have hi := congrArg (fun z => finPairTransport.invFun z) h
  simpa [finPair_transport_roundtrip] using hi

/--
Copying after an arbitrary kernel puts mass only on the encoded diagonal.
This is the transport-aware coordinate form of the left side of copy naturality.
-/
theorem finKernel_copy_after_eval {m n : Nat}
    (k : FinKernel m n) (x : Fin m) (y z : Fin n) :
    FinKernel.compose (FinKernel.copy n) k x
        (finPairTransport.toFun (y, z)) =
      if y = z then k x y else 0 := by
  unfold FinKernel.compose FinKernel.copy FinKernel.dirac
  by_cases hyz : y = z
  · subst z
    calc
      sumFin n (fun u =>
          k x u *
            (if finPairTransport.toFun (y, y) =
                finPairTransport.toFun (u, u) then 1 else 0)) =
          sumFin n (fun u => if u = y then k x u else 0) := by
            apply sumFin_congr
            intro u
            by_cases huy : u = y
            · subst u
              simp
            · have hp :
                  finPairTransport.toFun (y, y) ≠
                    finPairTransport.toFun (u, u) := by
                intro heq
                have hpair : (y, y) = (u, u) :=
                  finPairTransport_toFun_injective heq
                have hyu : y = u := congrArg Prod.fst hpair
                exact huy hyu.symm
              simp [huy, hp]
      _ = k x y := sumFin_single y (fun u => k x u)
      _ = (if y = y then k x y else 0) := by simp
  · have hp : ∀ u : Fin n,
        finPairTransport.toFun (y, z) ≠
          finPairTransport.toFun (u, u) := by
      intro u heq
      have hpair : (y, z) = (u, u) :=
        finPairTransport_toFun_injective heq
      have hyu : y = u := congrArg Prod.fst hpair
      have hzu : z = u := congrArg Prod.snd hpair
      exact hyz (hyu.trans hzu.symm)
    calc
      sumFin n (fun u =>
          k x u *
            (if finPairTransport.toFun (y, z) =
                finPairTransport.toFun (u, u) then 1 else 0)) =
          sumFin n (fun _ => (0 : Rat)) := by
            apply sumFin_congr
            intro u
            simp [hp u]
      _ = 0 := sumFin_zero_values n
      _ = (if y = z then k x y else 0) := by simp [hyz]

/--
Independent resampling after source copy evaluates to the product of the two
row coordinates.
-/
theorem finKernel_tensor_after_copy_eval {m n : Nat}
    (k : FinKernel m n) (x : Fin m) (y z : Fin n) :
    FinKernel.compose (FinKernel.tensor k k) (FinKernel.copy m) x
        (finPairTransport.toFun (y, z)) =
      k x y * k x z := by
  unfold FinKernel.compose FinKernel.copy FinKernel.dirac
  calc
    sumFin m (fun u =>
        (if u = finPairTransport.toFun (x, x) then 1 else 0) *
          FinKernel.tensor k k u (finPairTransport.toFun (y, z))) =
      sumFin m (fun u =>
        if u = finPairTransport.toFun (x, x) then
          FinKernel.tensor k k u (finPairTransport.toFun (y, z)) else 0) := by
          apply sumFin_congr
          intro u
          by_cases hu : u = finPairTransport.toFun (x, x) <;> simp [hu]
    _ = FinKernel.tensor k k
          (finPairTransport.toFun (x, x))
          (finPairTransport.toFun (y, z)) :=
      sumFin_single (finPairTransport.toFun (x, x))
        (fun u => FinKernel.tensor k k u (finPairTransport.toFun (y, z)))
    _ = k x y * k x z := by
      simpa using finKernel_tensor_encoded k k x x y z

/-- Full coordinate law forced by classical-copy preservation. -/
theorem finKernel_preservesCopy_coordinate {m n : Nat}
    {k : FinKernel m n}
    (hcopy : FinKernel.PreservesCopy k)
    (x : Fin m) (y z : Fin n) :
    (if y = z then k x y else 0) = k x y * k x z := by
  unfold FinKernel.PreservesCopy at hcopy
  have h := congrFun (congrFun hcopy x) (finPairTransport.toFun (y, z))
  rw [finKernel_copy_after_eval, finKernel_tensor_after_copy_eval] at h
  exact h

/-- Every coordinate of a copy-preserving kernel is multiplicatively idempotent. -/
theorem finKernel_preservesCopy_diagonal {m n : Nat}
    {k : FinKernel m n}
    (hcopy : FinKernel.PreservesCopy k)
    (x : Fin m) (y : Fin n) :
    k x y = k x y * k x y := by
  simpa using finKernel_preservesCopy_coordinate hcopy x y y

/-- Exact rational multiplicative idempotents are only zero and one. -/
theorem rat_mul_idempotent_zero_or_one (p : Rat)
    (h : p = p * p) : p = 0 ∨ p = 1 := by
  by_cases hp : p = 0
  · exact Or.inl hp
  · right
    have hm : p * 1 = p * p := by simpa using h
    have hi := congrArg (fun q => p⁻¹ * q) hm
    simpa [Rat.mul_assoc, Rat.inv_mul_cancel p hp] using hi.symm

/-- A valid copy-preserving row contains a unit-mass coordinate. -/
theorem finKernel_valid_preservesCopy_row_has_one {m n : Nat}
    {k : FinKernel m n}
    (hvalid : FinKernel.Valid k)
    (hcopy : FinKernel.PreservesCopy k)
    (x : Fin m) :
    ∃ y : Fin n, k x y = 1 := by
  classical
  by_contra hnone
  have hallzero : ∀ y : Fin n, k x y = 0 := by
    intro y
    rcases rat_mul_idempotent_zero_or_one (k x y)
      (finKernel_preservesCopy_diagonal hcopy x y) with h0 | h1
    · exact h0
    · exact False.elim (hnone ⟨y, h1⟩)
  have hsumzero : sumFin n (fun y => k x y) = 0 := by
    calc
      sumFin n (fun y => k x y) = sumFin n (fun _ => (0 : Rat)) := by
        apply sumFin_congr
        intro y
        exact hallzero y
      _ = 0 := sumFin_zero_values n
  have hrow := hvalid.2 x
  change sumFin n (fun y => k x y) = 1 at hrow
  grind

/--
Once a unit-mass coordinate is selected, copy preservation forces every distinct
coordinate in that row to be zero.
-/
theorem finKernel_preservesCopy_row_other_zero {m n : Nat}
    {k : FinKernel m n}
    (hcopy : FinKernel.PreservesCopy k)
    {x : Fin m} {chosen y : Fin n}
    (hone : k x chosen = 1)
    (hne : y ≠ chosen) :
    k x y = 0 := by
  have hchosen : chosen ≠ y := by
    intro h
    exact hne h.symm
  have hcoord := finKernel_preservesCopy_coordinate hcopy x chosen y
  rw [if_neg hchosen, hone, Rat.one_mul] at hcoord
  exact hcoord.symm

/-- Valid copy-preserving finite kernels are extensionally deterministic/Dirac. -/
theorem finKernel_valid_preservesCopy_deterministic {m n : Nat}
    {k : FinKernel m n}
    (hvalid : FinKernel.Valid k)
    (hcopy : FinKernel.PreservesCopy k) :
    FinKernel.DeterministicKernel k := by
  classical
  let rowWitness : ∀ x : Fin m, ∃ y : Fin n, k x y = 1 :=
    fun x => finKernel_valid_preservesCopy_row_has_one hvalid hcopy x
  let f : Fin m → Fin n := fun x => Classical.choose (rowWitness x)
  have hf : ∀ x : Fin m, k x (f x) = 1 := by
    intro x
    exact Classical.choose_spec (rowWitness x)
  refine ⟨f, ?_⟩
  funext x y
  by_cases hy : y = f x
  · subst y
    simp [FinKernel.dirac, hf x]
  · have hzero : k x y = 0 :=
      finKernel_preservesCopy_row_other_zero hcopy (hf x) hy
    simp [FinKernel.dirac, hy, hzero]

/--
Within the exact finite normalized stochastic slice, copy preservation is
exactly Dirac determinism.
-/
theorem finKernel_valid_preservesCopy_iff_deterministic {m n : Nat}
    {k : FinKernel m n}
    (hvalid : FinKernel.Valid k) :
    FinKernel.PreservesCopy k ↔ FinKernel.DeterministicKernel k := by
  constructor
  · intro hcopy
    exact finKernel_valid_preservesCopy_deterministic hvalid hcopy
  · rintro ⟨f, rfl⟩
    exact finKernel_dirac_preservesCopy f

/--
For valid stochastic observation channels, the canonical copy-descent square is
therefore equivalent to deterministic/Dirac observation.
-/
theorem finKernel_valid_copy_descent_iff_deterministic {a q : Nat}
    {obs : FinKernel a q}
    (hvalid : FinKernel.Valid obs) :
    (FinKernel.compose (FinKernel.tensor obs obs) (FinKernel.copy a) =
        FinKernel.compose (FinKernel.copy q) obs) ↔
      FinKernel.DeterministicKernel obs := by
  rw [finKernel_copy_factor_square_iff_preservesCopy]
  exact finKernel_valid_preservesCopy_iff_deterministic hvalid

/-- The exact fair observation is not deterministic. -/
theorem finFairKernel_not_deterministic :
    ¬ FinKernel.DeterministicKernel finFairKernel := by
  intro hdet
  have hcopy : FinKernel.PreservesCopy finFairKernel :=
    (finKernel_valid_preservesCopy_iff_deterministic finFairKernel_valid).2 hdet
  exact finFairObservation_not_preservesCopy hcopy

/-- Acceptance bundle for the copy-preserving characterization. -/
theorem finKernel_copy_preserving_characterization_bundle :
    (∀ {m n : Nat} {k : FinKernel m n},
      FinKernel.Valid k →
      (FinKernel.PreservesCopy k ↔ FinKernel.DeterministicKernel k)) ∧
    (¬ FinKernel.DeterministicKernel finFairKernel) := by
  constructor
  · intro m n k hvalid
    exact finKernel_valid_preservesCopy_iff_deterministic hvalid
  · exact finFairKernel_not_deterministic

end RelayTheory
