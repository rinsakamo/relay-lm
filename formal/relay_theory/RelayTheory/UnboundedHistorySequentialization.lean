import Lean.Elab.Tactic.Grind

namespace RelayTheory

/--
One ordinary homogeneous state transition for a rule that may consult the
entire realized history.  The augmented state is the history itself; no finite
memory or finite carrier bound is assumed.
-/
def historyStep {α : Type} (next : List α → α) (h : List α) : List α :=
  h ++ [next h]

/--
Direct history-dependent evolution.  At each step the rule may inspect every
symbol accumulated so far.
-/
def historyRun {α : Type} (next : List α → α) (h : List α) : Nat → List α
  | 0 => h
  | k + 1 => historyStep next (historyRun next h k)

/-- Each homogeneous history-state step appends exactly one new symbol. -/
@[simp] theorem historyStep_length {α : Type} (next : List α → α) (h : List α) :
    (historyStep next h).length = h.length + 1 := by
  simp [historyStep]

/--
The direct history-dependent recursion is exactly ordinary one-parameter
iteration of one homogeneous map on the augmented history state.
-/
theorem historyRun_eq_iterate {α : Type} (next : List α → α)
    (h : List α) (k : Nat) :
    historyRun next h k = (historyStep next)^[k] h := by
  induction k with
  | zero => rfl
  | succ k ih =>
      simp only [historyRun, Function.iterate_succ_apply]
      rw [ih]

/-- No bounded horizon is hidden in the compiler: the stored history grows by `k`. -/
theorem historyRun_length {α : Type} (next : List α → α)
    (h : List α) (k : Nat) :
    (historyRun next h k).length = h.length + k := by
  induction k with
  | zero => simp [historyRun]
  | succ k ih =>
      simp [historyRun, ih, Nat.add_assoc]

/-- Running `i+j` steps factors through the realized history after `i` steps. -/
theorem historyRun_add {α : Type} (next : List α → α)
    (h : List α) (i j : Nat) :
    historyRun next h (i + j) = historyRun next (historyRun next h i) j := by
  induction j with
  | zero => simp [historyRun]
  | succ j ih =>
      simp [Nat.add_succ, historyRun, ih]

/-- The initial realized history is preserved exactly as a prefix of every later state. -/
theorem historyRun_extends_initial {α : Type} (next : List α → α)
    (h : List α) (k : Nat) :
    ∃ tail : List α, historyRun next h k = h ++ tail := by
  induction k with
  | zero =>
      exact ⟨[], by simp [historyRun]⟩
  | succ k ih =>
      rcases ih with ⟨tail, htail⟩
      refine ⟨tail ++ [next (historyRun next h k)], ?_⟩
      simp [historyRun, historyStep, htail, List.append_assoc]

/-- Every prior realized state remains a prefix of every later finite continuation. -/
theorem historyRun_extends_prior {α : Type} (next : List α → α)
    (h : List α) (i j : Nat) :
    ∃ tail : List α,
      historyRun next h (i + j) = historyRun next h i ++ tail := by
  rw [historyRun_add]
  exact historyRun_extends_initial next (historyRun next h i) j

/--
For any inhabited carrier, `List α` already contains an injective copy of
`Nat`; the augmented history-state surface is therefore not a disguised fixed
finite carrier.
-/
theorem repeatedHistory_injective {α : Type} (a : α) :
    Function.Injective (fun n : Nat => List.replicate n a) := by
  intro m n hmn
  have hlen := congrArg List.length hmn
  simpa using hlen

/-- Current observation for the small history-sensitive control below. -/
def currentBool : List Bool → Bool
  | [] => false
  | [x] => x
  | _ :: xs => currentBool xs

/-- A deliberately non-first-order rule: consult the oldest retained symbol. -/
def oldestBool : List Bool → Bool
  | [] => false
  | x :: _ => x

/-- Two histories with the same current observation can demand different next symbols. -/
def historySensitiveA : List Bool := [false, false]

def historySensitiveB : List Bool := [true, false]

/--
Non-vacuous control: equal current observations do not make the source rule
first-order Markov; retained history changes the next result.
-/
theorem history_sensitive_same_current_different_next :
    currentBool historySensitiveA = currentBool historySensitiveB ∧
      oldestBool historySensitiveA ≠ oldestBool historySensitiveB := by
  decide

/-- The same homogeneous history-state compiler accepts the history-sensitive rule directly. -/
theorem history_sensitive_compiler_control :
    historyStep oldestBool historySensitiveA = [false, false, false] ∧
      historyStep oldestBool historySensitiveB = [true, false, true] := by
  decide

/--
Owner-local acceptance bundle: arbitrary whole-history dependence is preserved
by one homogeneous ordinary iteration, while the state surface is explicitly
unbounded rather than a fixed finite phase register.
-/
theorem unbounded_history_sequentialization_bundle {α : Type}
    (next : List α → α) (h : List α) (k : Nat) :
    historyRun next h k = (historyStep next)^[k] h ∧
      (historyRun next h k).length = h.length + k ∧
      (∃ tail : List α, historyRun next h k = h ++ tail) := by
  exact ⟨historyRun_eq_iterate next h k,
    historyRun_length next h k,
    historyRun_extends_initial next h k⟩

end RelayTheory
