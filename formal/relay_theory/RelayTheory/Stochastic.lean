import Lean.Elab.Tactic.Grind
import Init.Grind.Ordered.Rat
import RelayTheory.Transform
import RelayTheory.HigherOrder

namespace RelayTheory

/--
Exact rational constants used by the bounded finite stochastic reconstruction.
Unlike the older quarter-unit witness types, `Rat` remains closed under the
products needed by composition and independent tensor.
-/
def qHalf : Rat := (1 : Rat) / 2
def qQuarter : Rat := (1 : Rat) / 4
def qThreeQuarter : Rat := (3 : Rat) / 4

theorem qHalf_pos : 0 < qHalf := by
  rw [qHalf, Rat.div_def]
  exact Rat.mul_pos (by decide) (Rat.inv_pos.mpr (by decide))

theorem qQuarter_pos : 0 < qQuarter := by
  rw [qQuarter, Rat.div_def]
  exact Rat.mul_pos (by decide) (Rat.inv_pos.mpr (by decide))

theorem qThreeQuarter_pos : 0 < qThreeQuarter := by
  rw [qThreeQuarter, Rat.div_def]
  exact Rat.mul_pos (by decide) (Rat.inv_pos.mpr (by decide))

/-- A fully resolved exact stochastic channel on one binary interface. -/
abbrev BinaryKernel := Bool → Bool → Rat

namespace BinaryKernel

/-- Exact row mass. -/
def rowSum (k : BinaryKernel) (x : Bool) : Rat :=
  k x false + k x true

/-- Bounded stochastic validity: non-negative entries and normalized rows. -/
def Valid (k : BinaryKernel) : Prop :=
  ∀ x,
    0 ≤ k x false ∧
    0 ≤ k x true ∧
    rowSum k x = 1

/--
Sequential stochastic composition. `compose g f` means: first use `f`, then
use `g`, summing exactly over the intermediate binary interface.
-/
def compose (g f : BinaryKernel) : BinaryKernel :=
  fun x z =>
    f x false * g false z +
    f x true * g true z

/-- Exact identity channel. -/
def identity : BinaryKernel :=
  fun x y => if x = y then 1 else 0

/-- Exact deterministic / Dirac channel induced by a binary function. -/
def dirac (f : Bool → Bool) : BinaryKernel :=
  fun x y => if y = f x then 1 else 0

end BinaryKernel

/-- Every input is resolved to one fair binary draw. -/
def fairKernel : BinaryKernel :=
  fun _ _ => qHalf

/-- Nontrivial exact biased channel. -/
def biasKernel : BinaryKernel
  | false, false => qThreeQuarter
  | false, true => qQuarter
  | true, false => qQuarter
  | true, true => qThreeQuarter

/-- Nontrivial exact noisy-flip channel. -/
def noisyFlipKernel : BinaryKernel
  | false, false => qQuarter
  | false, true => qThreeQuarter
  | true, false => qThreeQuarter
  | true, true => qQuarter

theorem fairKernel_pos (x y : Bool) : 0 < fairKernel x y := by
  simpa [fairKernel] using qHalf_pos

theorem biasKernel_pos (x y : Bool) : 0 < biasKernel x y := by
  cases x <;> cases y
  · simpa [biasKernel] using qThreeQuarter_pos
  · simpa [biasKernel] using qQuarter_pos
  · simpa [biasKernel] using qQuarter_pos
  · simpa [biasKernel] using qThreeQuarter_pos

theorem noisyFlipKernel_pos (x y : Bool) : 0 < noisyFlipKernel x y := by
  cases x <;> cases y
  · simpa [noisyFlipKernel] using qQuarter_pos
  · simpa [noisyFlipKernel] using qThreeQuarter_pos
  · simpa [noisyFlipKernel] using qThreeQuarter_pos
  · simpa [noisyFlipKernel] using qQuarter_pos

theorem fairKernel_valid : BinaryKernel.Valid fairKernel := by
  intro x
  refine ⟨Rat.le_of_lt (fairKernel_pos x false),
    Rat.le_of_lt (fairKernel_pos x true), ?_⟩
  cases x <;> grind [fairKernel, BinaryKernel.rowSum, qHalf]

theorem biasKernel_valid : BinaryKernel.Valid biasKernel := by
  intro x
  refine ⟨Rat.le_of_lt (biasKernel_pos x false),
    Rat.le_of_lt (biasKernel_pos x true), ?_⟩
  cases x <;>
    grind [biasKernel, BinaryKernel.rowSum, qQuarter, qThreeQuarter]

theorem noisyFlipKernel_valid : BinaryKernel.Valid noisyFlipKernel := by
  intro x
  refine ⟨Rat.le_of_lt (noisyFlipKernel_pos x false),
    Rat.le_of_lt (noisyFlipKernel_pos x true), ?_⟩
  cases x <;>
    grind [noisyFlipKernel, BinaryKernel.rowSum, qQuarter, qThreeQuarter]

/-- Right identity for exact binary stochastic composition, proved generically. -/
theorem compose_identity_after (k : BinaryKernel) :
    BinaryKernel.compose BinaryKernel.identity k = k := by
  funext x z
  cases z <;>
    simp [BinaryKernel.compose, BinaryKernel.identity,
      Rat.mul_one, Rat.mul_zero, Rat.one_mul, Rat.zero_mul,
      Rat.add_zero, Rat.zero_add]

/-- Left identity for exact binary stochastic composition, proved generically. -/
theorem compose_identity_before (k : BinaryKernel) :
    BinaryKernel.compose k BinaryKernel.identity = k := by
  funext x z
  cases x <;>
    simp [BinaryKernel.compose, BinaryKernel.identity,
      Rat.mul_one, Rat.mul_zero, Rat.one_mul, Rat.zero_mul,
      Rat.add_zero, Rat.zero_add]

/--
Associativity on a nontrivial exact finite chain. This establishes the earned
bounded equation without importing category theory as a premise.
-/
theorem compose_associativity_fixture :
    BinaryKernel.compose noisyFlipKernel
        (BinaryKernel.compose biasKernel fairKernel) =
      BinaryKernel.compose
        (BinaryKernel.compose noisyFlipKernel biasKernel)
        fairKernel := by
  funext x z
  cases x <;> cases z <;>
    grind [BinaryKernel.compose, fairKernel, biasKernel, noisyFlipKernel,
      qHalf, qQuarter, qThreeQuarter]

def flipBit : Bool → Bool
  | false => true
  | true => false

/-- Deterministic Dirac composition agrees with ordinary function composition. -/
theorem dirac_composition_fixture :
    BinaryKernel.compose
        (BinaryKernel.dirac flipBit)
        (BinaryKernel.dirac flipBit) =
      BinaryKernel.dirac (fun x => flipBit (flipBit x)) := by
  funext x z
  cases x <;> cases z <;>
    simp [BinaryKernel.compose, BinaryKernel.dirac, flipBit,
      Rat.mul_one, Rat.mul_zero, Rat.one_mul, Rat.zero_mul,
      Rat.add_zero, Rat.zero_add]

/-- One-point output channel used to express exact discard. -/
abbrev ToUnitKernel := Bool → Rat

def discardKernel : ToUnitKernel :=
  fun _ => 1

/-- Compose a binary stochastic channel with a binary-to-unit channel. -/
def composeToUnit (d : ToUnitKernel) (k : BinaryKernel) : ToUnitKernel :=
  fun x =>
    k x false * d false +
    k x true * d true

/-- Exact bounded discard law. -/
theorem discard_after_bias :
    composeToUnit discardKernel biasKernel = discardKernel := by
  funext x
  cases x <;>
    grind [composeToUnit, discardKernel, biasKernel, qQuarter, qThreeQuarter]

/-- Deterministic classical-data copy on the bounded binary object. -/
def copyBit (x : Bool) : Bool × Bool :=
  (x, x)

def swapPair (p : Bool × Bool) : Bool × Bool :=
  (p.2, p.1)

def reassocRight (p : (Bool × Bool) × Bool) : Bool × (Bool × Bool) :=
  (p.1.1, (p.1.2, p.2))

/-- Bounded coassociativity of exact copy, with explicit reassociation. -/
theorem copy_coassociative (x : Bool) :
    reassocRight (copyBit x, x) = (x, copyBit x) := by
  cases x <;> rfl

/-- Bounded cocommutativity of exact copy. -/
theorem copy_cocommutative (x : Bool) :
    swapPair (copyBit x) = copyBit x := by
  cases x <;> rfl

/-- Bounded counit equations for copy/discard on classical data. -/
theorem copy_counit (x : Bool) :
    (copyBit x).1 = x ∧ (copyBit x).2 = x := by
  cases x <;> exact ⟨rfl, rfl⟩

def mapPair (f : Bool → Bool) (p : Bool × Bool) : Bool × Bool :=
  (f p.1, f p.2)

/-- A nontrivial deterministic map preserves exact classical copy. -/
theorem deterministic_preserves_copy (x : Bool) :
    mapPair flipBit (copyBit x) = copyBit (flipBit x) := by
  cases x <;> rfl

/-- Exact rational binary state. -/
structure RatBinaryLaw where
  p0 : Rat
  p1 : Rat
deriving DecidableEq, Repr

namespace RatBinaryLaw

def Valid (p : RatBinaryLaw) : Prop :=
  0 ≤ p.p0 ∧ 0 ≤ p.p1 ∧ p.p0 + p.p1 = 1

end RatBinaryLaw

/-- Exact rational joint law on two binary coordinates. -/
structure RatPairLaw where
  p00 : Rat
  p01 : Rat
  p10 : Rat
  p11 : Rat
deriving DecidableEq, Repr

namespace RatPairLaw

def Valid (p : RatPairLaw) : Prop :=
  0 ≤ p.p00 ∧
  0 ≤ p.p01 ∧
  0 ≤ p.p10 ∧
  0 ≤ p.p11 ∧
  p.p00 + p.p01 + p.p10 + p.p11 = 1

def marginalFirst (p : RatPairLaw) : RatBinaryLaw :=
  ⟨p.p00 + p.p01, p.p10 + p.p11⟩

def marginalSecond (p : RatPairLaw) : RatBinaryLaw :=
  ⟨p.p00 + p.p10, p.p01 + p.p11⟩

end RatPairLaw

def fairRatLaw : RatBinaryLaw :=
  ⟨qHalf, qHalf⟩

/-- Copy one random result, preserving shared randomness. -/
def copyLaw (p : RatBinaryLaw) : RatPairLaw :=
  ⟨p.p0, 0, 0, p.p1⟩

/-- Independent parallel product of two exact binary states. -/
def tensorLaw (p q : RatBinaryLaw) : RatPairLaw :=
  ⟨p.p0 * q.p0, p.p0 * q.p1, p.p1 * q.p0, p.p1 * q.p1⟩

theorem fairRatLaw_valid : fairRatLaw.Valid := by
  refine ⟨Rat.le_of_lt qHalf_pos, Rat.le_of_lt qHalf_pos, ?_⟩
  grind [fairRatLaw, qHalf]

theorem copyFair_valid : (copyLaw fairRatLaw).Valid := by
  change 0 ≤ qHalf ∧ 0 ≤ (0 : Rat) ∧ 0 ≤ (0 : Rat) ∧ 0 ≤ qHalf ∧
    qHalf + 0 + 0 + qHalf = 1
  refine ⟨Rat.le_of_lt qHalf_pos, Rat.le_refl 0, Rat.le_refl 0,
    Rat.le_of_lt qHalf_pos, ?_⟩
  grind [qHalf]

theorem independentFair_valid : (tensorLaw fairRatLaw fairRatLaw).Valid := by
  have hprod : 0 ≤ qHalf * qHalf :=
    Rat.le_of_lt (Rat.mul_pos qHalf_pos qHalf_pos)
  change 0 ≤ qHalf * qHalf ∧
    0 ≤ qHalf * qHalf ∧
    0 ≤ qHalf * qHalf ∧
    0 ≤ qHalf * qHalf ∧
    qHalf * qHalf + qHalf * qHalf + qHalf * qHalf + qHalf * qHalf = 1
  refine ⟨hprod, hprod, hprod, hprod, ?_⟩
  grind [qHalf]

/--
One fair draw followed by copy is exactly different from two independent fair
draws.
-/
theorem copy_one_random_result_ne_two_independent_draws :
    copyLaw fairRatLaw ≠ tensorLaw fairRatLaw fairRatLaw := by
  intro h
  have h00 := congrArg RatPairLaw.p00 h
  change qHalf = qHalf * qHalf at h00
  grind [qHalf]

theorem qHalf_square_twice :
    qHalf * qHalf + qHalf * qHalf = qHalf := by
  grind [qHalf]

/-- Both constructions still have the same fair single-coordinate marginals. -/
theorem shared_and_independent_have_same_fair_marginals :
    (copyLaw fairRatLaw).marginalFirst = fairRatLaw ∧
    (copyLaw fairRatLaw).marginalSecond = fairRatLaw ∧
    (tensorLaw fairRatLaw fairRatLaw).marginalFirst = fairRatLaw ∧
    (tensorLaw fairRatLaw fairRatLaw).marginalSecond = fairRatLaw := by
  change
    RatBinaryLaw.mk (qHalf + 0) (0 + qHalf) = RatBinaryLaw.mk qHalf qHalf ∧
    RatBinaryLaw.mk (qHalf + 0) (0 + qHalf) = RatBinaryLaw.mk qHalf qHalf ∧
    RatBinaryLaw.mk (qHalf * qHalf + qHalf * qHalf)
        (qHalf * qHalf + qHalf * qHalf) = RatBinaryLaw.mk qHalf qHalf ∧
    RatBinaryLaw.mk (qHalf * qHalf + qHalf * qHalf)
        (qHalf * qHalf + qHalf * qHalf) = RatBinaryLaw.mk qHalf qHalf
  have hcopy :
      RatBinaryLaw.mk (qHalf + 0) (0 + qHalf) = RatBinaryLaw.mk qHalf qHalf := by
    rw [Rat.add_zero, Rat.zero_add]
  have hind :
      RatBinaryLaw.mk (qHalf * qHalf + qHalf * qHalf)
          (qHalf * qHalf + qHalf * qHalf) = RatBinaryLaw.mk qHalf qHalf := by
    rw [qHalf_square_twice]
  exact ⟨hcopy, hcopy, hind, hind⟩

/-- Exact stochastic channel on a pair of binary interfaces. -/
abbrev PairKernel := (Bool × Bool) → (Bool × Bool) → Rat

namespace PairKernel

/-- Independent parallel composition of two resolved binary kernels. -/
def tensor (f g : BinaryKernel) : PairKernel :=
  fun x y => f x.1 y.1 * g x.2 y.2

/-- Exact row mass for a pair kernel. -/
def rowSum (k : PairKernel) (x : Bool × Bool) : Rat :=
  k x (false, false) +
  k x (false, true) +
  k x (true, false) +
  k x (true, true)

def Valid (k : PairKernel) : Prop :=
  ∀ x,
    0 ≤ k x (false, false) ∧
    0 ≤ k x (false, true) ∧
    0 ≤ k x (true, false) ∧
    0 ≤ k x (true, true) ∧
    rowSum k x = 1

/-- Exact sequential composition, summing over all four pair states. -/
def compose (g f : PairKernel) : PairKernel :=
  fun x z =>
    f x (false, false) * g (false, false) z +
    f x (false, true) * g (false, true) z +
    f x (true, false) * g (true, false) z +
    f x (true, true) * g (true, true) z

/-- Direct exact identity on the pair object. -/
def identity : PairKernel :=
  fun x y => if x = y then 1 else 0

end PairKernel

/-- Independent tensor of exact valid binary fixtures is exactly normalized here. -/
theorem tensor_fixture_valid :
    PairKernel.Valid (PairKernel.tensor biasKernel fairKernel) := by
  intro x
  refine ⟨
    Rat.le_of_lt (Rat.mul_pos (biasKernel_pos x.1 false) (fairKernel_pos x.2 false)),
    Rat.le_of_lt (Rat.mul_pos (biasKernel_pos x.1 false) (fairKernel_pos x.2 true)),
    Rat.le_of_lt (Rat.mul_pos (biasKernel_pos x.1 true) (fairKernel_pos x.2 false)),
    Rat.le_of_lt (Rat.mul_pos (biasKernel_pos x.1 true) (fairKernel_pos x.2 true)),
    ?_
  ⟩
  rcases x with ⟨a, b⟩
  cases a <;> cases b <;>
    grind [PairKernel.tensor, PairKernel.rowSum, biasKernel, fairKernel,
      qHalf, qQuarter, qThreeQuarter]

/-- Tensor of binary identities reconstructs the direct pair identity. -/
theorem tensor_identities :
    PairKernel.tensor BinaryKernel.identity BinaryKernel.identity =
      PairKernel.identity := by
  funext x y
  rcases x with ⟨xa, xb⟩
  rcases y with ⟨ya, yb⟩
  cases xa <;> cases xb <;> cases ya <;> cases yb <;>
    simp [PairKernel.tensor, PairKernel.identity, BinaryKernel.identity,
      Rat.mul_one, Rat.mul_zero, Rat.one_mul, Rat.zero_mul]

/-- Bounded interchange law for independent tensor and sequential composition. -/
theorem tensor_interchange_fixture :
    PairKernel.compose
        (PairKernel.tensor noisyFlipKernel biasKernel)
        (PairKernel.tensor biasKernel fairKernel) =
      PairKernel.tensor
        (BinaryKernel.compose noisyFlipKernel biasKernel)
        (BinaryKernel.compose biasKernel fairKernel) := by
  funext x z
  rcases x with ⟨xa, xb⟩
  rcases z with ⟨za, zb⟩
  cases xa <;> cases xb <;> cases za <;> cases zb <;>
    grind [PairKernel.compose, PairKernel.tensor, BinaryKernel.compose,
      noisyFlipKernel, biasKernel, fairKernel,
      qHalf, qQuarter, qThreeQuarter]

/--
The derived stochastic slice does not erase already-formalized outer boundaries:
unresolved selectable responses are still not one resolved law, and locally
consistent pair laws can still fail to glue globally.
-/
theorem stochastic_slice_outer_boundaries :
    unresolvedSelectableResponses ≠ [resolvedMixedResponse] ∧
    (¬ ∃ t : TripleLaw, antiTriangle.RealizedBy t) :=
  ⟨unresolvedFamily_ne_resolvedSingleton, antiTriangle_not_globally_realizable⟩

/-- The bounded reconstructed stochastic-slice acceptance bundle. -/
theorem finiteStochasticSlice_bundle :
    BinaryKernel.Valid fairKernel ∧
    BinaryKernel.Valid biasKernel ∧
    BinaryKernel.Valid noisyFlipKernel ∧
    BinaryKernel.compose BinaryKernel.identity biasKernel = biasKernel ∧
    BinaryKernel.compose biasKernel BinaryKernel.identity = biasKernel ∧
    BinaryKernel.compose noisyFlipKernel
        (BinaryKernel.compose biasKernel fairKernel) =
      BinaryKernel.compose
        (BinaryKernel.compose noisyFlipKernel biasKernel)
        fairKernel ∧
    BinaryKernel.compose
        (BinaryKernel.dirac flipBit)
        (BinaryKernel.dirac flipBit) =
      BinaryKernel.dirac (fun x => flipBit (flipBit x)) ∧
    composeToUnit discardKernel biasKernel = discardKernel ∧
    (∀ x, reassocRight (copyBit x, x) = (x, copyBit x)) ∧
    (∀ x, swapPair (copyBit x) = copyBit x) ∧
    (∀ x, mapPair flipBit (copyBit x) = copyBit (flipBit x)) ∧
    copyLaw fairRatLaw ≠ tensorLaw fairRatLaw fairRatLaw ∧
    PairKernel.Valid (PairKernel.tensor biasKernel fairKernel) ∧
    PairKernel.tensor BinaryKernel.identity BinaryKernel.identity =
      PairKernel.identity ∧
    PairKernel.compose
        (PairKernel.tensor noisyFlipKernel biasKernel)
        (PairKernel.tensor biasKernel fairKernel) =
      PairKernel.tensor
        (BinaryKernel.compose noisyFlipKernel biasKernel)
        (BinaryKernel.compose biasKernel fairKernel) ∧
    unresolvedSelectableResponses ≠ [resolvedMixedResponse] ∧
    (¬ ∃ t : TripleLaw, antiTriangle.RealizedBy t) := by
  refine ⟨
    fairKernel_valid,
    biasKernel_valid,
    noisyFlipKernel_valid,
    compose_identity_after biasKernel,
    compose_identity_before biasKernel,
    compose_associativity_fixture,
    dirac_composition_fixture,
    discard_after_bias,
    ?_,
    ?_,
    ?_,
    copy_one_random_result_ne_two_independent_draws,
    tensor_fixture_valid,
    tensor_identities,
    tensor_interchange_fixture,
    unresolvedFamily_ne_resolvedSingleton,
    antiTriangle_not_globally_realizable
  ⟩
  · intro x
    exact copy_coassociative x
  · intro x
    exact copy_cocommutative x
  · intro x
    exact deterministic_preserves_copy x

end RelayTheory
