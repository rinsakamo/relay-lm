# Context Compiler semantic expansion boundary

Owning Issue: #1825. Parent owner: #1267.

This reference defines the forward-looking semantic boundary for Context Compiler work after the realized C5-C37 State-vs-MEMORY structural grammar.

## Decision

**C37 is the proactive deterministic semantic-grammar freeze point.**

**Semantic completeness is not a Context Compiler goal.**

Existing C5-C37 behavior and tests remain regression protection. They are not deleted, weakened, or reinterpreted merely because the realized matrix is large.

New deterministic semantic grammar after C37 is **evidence-triggered only**.

A future rule requires fresh evidence of a material defect that cannot safely remain in the model-mediated semantic layer, such as:

- an authority or provenance violation;
- a repeatable Character-realization defect under #1823;
- a concrete stale/conflicting MEMORY failure that crosses the existing Canonical State authority boundary;
- a runtime safety/correctness failure with a bounded deterministic remedy.

The following are not sufficient reasons to add another grammar branch:

- another natural-language paraphrase or synonym;
- broader negation/composite coverage for completeness;
- non-exact degree/intensity interpretation;
- improving an exact fixture or proposal metric where exactness is not part of the semantic contract;
- forcing different Characters toward one neutral interpretation;
- speculative handling of omitted keys, aliases, pragmatic force, or language-specific nuance.

## Responsibility split

Context Compiler remains strict about deterministic mechanics it actually owns:

- authority ordering;
- provenance/source role;
- bounded selection and residency;
- typed structural projection;
- explicit fail-closed structural boundaries;
- current-State protection from lower-authority current claims;
- content-free diagnostics for compiler-owned mechanics.

Free-form interpretation remains model-mediated and Character-relative unless a separately evidenced defect proves a deterministic boundary is required.

This preserves the intended product split:

> Normalize structure and authority, not language into one universal meaning.

## Relationship to the existing C5-C37 matrix

The detailed C5-C37 cases in `docs/architecture/context-compiler.md` and their focused unit tests describe realized behavior and remain valid regression evidence. They are not a roadmap for C38, C39, or an unbounded combinatorial NLP program.

No proactive C38+ semantic slice exists after this decision.

## Relationship to evaluation

Stage R Character-realization evaluation may expose a concrete defect. A surprising or unusual interpretation is not enough by itself: Character-plausible behavior remains valid. Deterministic expansion is justified only when the failure crosses a material authority/runtime boundary or is a repeatable out-of-character defect that cannot be handled safely by model-mediated cognition.

## Non-goals

This boundary does not:

- change existing C5-C37 runtime behavior;
- delete or consolidate existing C5-C37 tests;
- weaken Canonical State authority;
- make MEMORY authoritative;
- change retrieval ranking, budgets, Continuity, diagnostics, or persistence;
- forbid future bug fixes supported by concrete evidence.

## Principle

> Keep deterministic authority small and explicit; let Character cognition interpret the rest.
