import RelayTheory.GenericStochastic
import RelayTheory.UnboundedHistorySequentialization

namespace RelayTheory

/-- Exact finite-alphabet next-symbol law allowed to inspect the whole realized history. -/
abbrev HistoryLaw (q : Nat) := List (Fin q) → Fin q → Rat

namespace HistoryLaw

/-- Exact stochastic validity at every realized history. -/
def Valid {q : Nat} (law : HistoryLaw q) : Prop :=
  (∀ h a, 0 ≤ law h a) ∧
  (∀ h, sumFin q (fun a => law h a) = 1)

end HistoryLaw

/--
A homogeneous finitely-branching stochastic state machine over an arbitrary
state type.  The branch alphabet is finite, but the state carrier need not be.
-/
structure FinitelyBranchingKernel (σ : Type) (q : Nat) where
  weight : σ → Fin q → Rat
  advance : σ → Fin q → σ

namespace FinitelyBranchingKernel

/-- Exact branch normalization at every current state. -/
def Valid {σ : Type} {q : Nat} (k : FinitelyBranchingKernel σ q) : Prop :=
  (∀ s a, 0 ≤ k.weight s a) ∧
  (∀ s, sumFin q (fun a => k.weight s a) = 1)

/-- Exact probability weight of one declared finite branch trace. -/
def pathWeight {σ : Type} {q : Nat} (k : FinitelyBranchingKernel σ q) :
    σ → List (Fin q) → Rat
  | _, [] => 1
  | s, a :: as => k.weight s a * pathWeight k (k.advance s a) as

/-- Terminal state reached by one declared finite branch trace. -/
def run {σ : Type} {q : Nat} (k : FinitelyBranchingKernel σ q) :
    σ → List (Fin q) → σ
  | s, [] => s
  | s, a :: as => run k (k.advance s a) as

end FinitelyBranchingKernel

/--
Compile a whole-history stochastic law into one homogeneous stochastic machine
whose ordinary current state is the realized history itself.
-/
def compileHistoryLaw {q : Nat} (law : HistoryLaw q) :
    FinitelyBranchingKernel (List (Fin q)) q where
  weight := law
  advance := fun h a => h ++ [a]

/-- Stochastic validity transfers exactly to the homogeneous history-state machine. -/
theorem compileHistoryLaw_valid {q : Nat} (law : HistoryLaw q)
    (hvalid : HistoryLaw.Valid law) :
    FinitelyBranchingKernel.Valid (compileHistoryLaw law) := by
  simpa [HistoryLaw.Valid, FinitelyBranchingKernel.Valid, compileHistoryLaw] using hvalid

/-- Direct exact source probability of one finite continuation path. -/
def historyLawPathWeight {q : Nat} (law : HistoryLaw q) :
    List (Fin q) → List (Fin q) → Rat
  | _, [] => 1
  | h, a :: as => law h a * historyLawPathWeight law (h ++ [a]) as

/--
The homogeneous compiled machine preserves every finite path weight exactly,
with no bounded-memory or bounded-horizon assumption.
-/
theorem compileHistoryLaw_pathWeight {q : Nat} (law : HistoryLaw q)
    (h path : List (Fin q)) :
    FinitelyBranchingKernel.pathWeight (compileHistoryLaw law) h path =
      historyLawPathWeight law h path := by
  induction path generalizing h with
  | nil => rfl
  | cons a as ih =>
      simp [FinitelyBranchingKernel.pathWeight, compileHistoryLaw,
        historyLawPathWeight, ih]

/-- Every declared finite branch trace is stored exactly in the terminal history state. -/
theorem compileHistoryLaw_run_eq_append {q : Nat} (law : HistoryLaw q)
    (h path : List (Fin q)) :
    FinitelyBranchingKernel.run (compileHistoryLaw law) h path = h ++ path := by
  induction path generalizing h with
  | nil => simp [FinitelyBranchingKernel.run]
  | cons a as ih =>
      simp [FinitelyBranchingKernel.run, compileHistoryLaw, ih, List.append_assoc]

/-- Any inhabited finite alphabet yields an unbounded family of distinct history states. -/
theorem compiled_history_states_unbounded {q : Nat} (a : Fin q) :
    Function.Injective (fun n : Nat => List.replicate n a) :=
  repeatedHistory_injective a

/-- Current/last symbol for the non-vacuous binary history-sensitive control. -/
def currentFin2 : List (Fin 2) → Fin 2
  | [] => 0
  | [x] => x
  | _ :: xs => currentFin2 xs

/-- Oldest retained symbol; this deliberately makes the next law history-sensitive. -/
def oldestFin2 : List (Fin 2) → Fin 2
  | [] => 0
  | x :: _ => x

/-- A valid deterministic exact law whose next distribution consults old history. -/
def historySensitiveLaw : HistoryLaw 2 :=
  fun h a => if a = oldestFin2 h then 1 else 0

/-- The history-sensitive control is stochastic-valid at every binary history. -/
theorem historySensitiveLaw_valid : HistoryLaw.Valid historySensitiveLaw := by
  constructor
  · intro h a
    by_cases ha : a = oldestFin2 h
    · simp [historySensitiveLaw, ha, rat_zero_le_one]
    · simp [historySensitiveLaw, ha]
  · intro h
    simpa [historySensitiveLaw] using
      (sumFin_single (oldestFin2 h) (fun _ : Fin 2 => (1 : Rat)))

/-- Two histories with the same current symbol but different retained older symbols. -/
def stochasticHistoryA : List (Fin 2) := [0, 0]

def stochasticHistoryB : List (Fin 2) := [1, 0]

/--
Non-vacuous stochastic control: current observation agrees, but the exact next
law differs because the compiled current state retains older history.
-/
theorem historySensitiveLaw_same_current_different_distribution :
    currentFin2 stochasticHistoryA = currentFin2 stochasticHistoryB ∧
      historySensitiveLaw stochasticHistoryA 0 ≠
        historySensitiveLaw stochasticHistoryB 0 := by
  decide

/-- The same homogeneous compiled machine exposes those distinct exact branch weights. -/
theorem historySensitiveLaw_compiled_control :
    (compileHistoryLaw historySensitiveLaw).weight stochasticHistoryA 0 = 1 ∧
      (compileHistoryLaw historySensitiveLaw).weight stochasticHistoryB 0 = 0 := by
  decide

/--
Owner-local acceptance bundle: stochastic validity and every declared finite
path probability survive one ordinary homogeneous history-state compilation.
-/
theorem stochastic_history_state_markovization_bundle {q : Nat}
    (law : HistoryLaw q) (hvalid : HistoryLaw.Valid law)
    (h path : List (Fin q)) :
    FinitelyBranchingKernel.Valid (compileHistoryLaw law) ∧
      FinitelyBranchingKernel.pathWeight (compileHistoryLaw law) h path =
        historyLawPathWeight law h path ∧
      FinitelyBranchingKernel.run (compileHistoryLaw law) h path = h ++ path := by
  exact ⟨compileHistoryLaw_valid law hvalid,
    compileHistoryLaw_pathWeight law h path,
    compileHistoryLaw_run_eq_append law h path⟩

end RelayTheory
