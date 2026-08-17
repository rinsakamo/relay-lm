# Ordinary-turn retrieval diagnostics

`src/relaylm/turn.py` owns the runtime orchestration surface that connects explicit ordinary-turn retrieval budgets to the existing selector-owned retrieval diagnostics.

This surface is diagnostic observation only. It does not define MEMORY selection semantics, Event selection semantics, Context Compiler semantics, runtime default budgets, or a total token-aware budgeting policy.

## Explicit opt-in

The ordinary non-diagnostic APIs remain unchanged:

- `run_user_turn(...)`
- `run_user_turn_streaming(...)`

Retrieval diagnostics are requested only through:

- `run_user_turn_with_retrieval_diagnostics(...)`
- `run_user_turn_streaming_with_retrieval_diagnostics(...)`

Both diagnostic APIs return `TurnResultWithRetrievalDiagnostics`. Its `turn` member is the ordinary `TurnResult`; its `retrieval` member is a `TurnRetrievalDiagnostics` aggregate.

If a MEMORY or Event retrieval budget is not configured for the turn, the corresponding diagnostic member is `None`. The diagnostic API does not invent a default budget or pretend that an unrequested selector ran.

## Budget-to-selector linkage

For configured MEMORY retrieval, `MemoryTurnRetrievalDiagnostics` pairs:

- the exact `MemoryRetrievalBudget` supplied to the turn; and
- the `MemoryRetrievalDiagnostics` returned by `select_memory_chunks_with_diagnostics(...)`.

For configured Event retrieval, `EventTurnRetrievalDiagnostics` pairs:

- the exact `EventRetrievalBudget` supplied to the turn; and
- the `EventRetrievalDiagnostics` returned by `select_event_evidence_with_diagnostics(...)`.

The turn layer does not recalculate candidate populations, admissions, budget use, skip counts, or pressure. Those observations remain selector-owned and are carried through unchanged.

Consequently, the integrated surface can connect configured limits with observed candidate/admission/budget-pressure mechanics without becoming a second retrieval authority.

## Content-free contract

Turn retrieval diagnostics contain only the configured numeric budgets and the selector-owned aggregate diagnostics.

They do not expose:

- Event IDs, actors, timestamps, or dialogue content;
- MEMORY headings, locations, or content;
- State keys or values;
- lexical query terms or scores.

The ordinary `TurnResult` still contains the persisted user/assistant Events required by normal turn behavior. The content-free restriction applies to the retrieval diagnostics surface, not to the ordinary turn result that accompanies it.

## Shared ordinary-turn preparation

Buffered and streaming turns share the same runtime preparation owner before provider generation. The diagnostic variants use that same preparation path with retrieval diagnostics enabled.

The preparation order remains:

1. validate non-blank user content;
2. load character config, identity, and State;
3. create and persist the Current User Event;
4. perform the configured optional MEMORY/Event retrieval;
5. compile the cognitive input;
6. invoke exactly one cognitive provider generation;
7. persist the Assistant Event and validate/apply State candidates after provider completion.

A retrieval failure therefore occurs after the Current User Event has been persisted but before provider generation. Existing fail-closed behavior is preserved: the User Event remains, no Assistant Event is written, and no State mutation is applied.

## Deferred policy

This surface intentionally does not choose:

- default `MemoryRetrievalBudget` or `EventRetrievalBudget` values;
- cross-layer or total token budgets;
- degradation/fallback policy under a total budget;
- client-facing OpenAI API budget or diagnostics controls.

Those remain separate future policy work.