# RelayLM 2.0 Deterministic Semantic Transaction Prototype

Status: **Post-1.0 research implementation contract for `v2`.** This surface is
owned by Issue #2135 and exists only to falsify the current RelayLM 2.0 minimal
basis before any language model is introduced. It does not redefine RelayLM 1.x
semantics.

## Claim under test

The prototype tests whether the following are sufficient for deterministic
cognitive semantics:

```text
one canonical transaction writer
+ stable entity/symbol anchors
+ immutable content-addressed semantic expressions
+ governed provenance
+ immutable generations
+ external governance
```

No MEMORY, Event, Emotion, Attention, Goal, Theory-of-Mind, SOUL, WORLD, or
migration-specific persistence engine is introduced.

The current persistent cognitive candidate remains two-substrate:

```text
Cognitive semantic substrate
Governed provenance substrate
```

Governance and transaction staging are control-plane/runtime mechanisms rather
than cognitive stores.

## Stable anchors

Anchors are opaque identities:

```text
EntityRef(id)
SymbolRef(id)
```

Mutable names, labels, attributed identity, and co-reference are represented as
ordinary semantics. Current cognition may assert:

```text
same_as(E1, E2)
different_from(E1, E2)
```

without physically merging the two anchors. A later correction therefore
changes the active semantic relation, not historical identity.

## Semantic expression algebra

The prototype stores only these expression forms:

```text
Literal(value)
Ref(anchor)
Var(scoped_name)
Apply(symbol, args...)
```

Expressions are deterministically serialized and content-addressed. The digest
means **serialization identity only**. It is not a claim of general logical
equivalence.

Narrow canonicalization is allowed only where it is mechanically safe. The
prototype normalizes bound variable names for `forall`, `exists`, and `lambda`
so alpha-equivalent expressions receive the same serialization identity.

The store is open-world:

```text
absence(P) != not(P)
```

Explicit positive and negative roots may coexist. Contradiction is represented
as `CONFLICT`; it does not authorize arbitrary inference.

Embedded propositions remain quarantined. Activating:

```text
believes(A, P)
hypothetical(P)
counterfactual(P)
```

does not activate root `P`.

## Provenance

A provenance record is:

```text
ProvenanceRecord
  id
  origin: observed | endogenous
  time
  source
  payload_ref?
  links[]
```

Observed payload bytes are carried by the same provenance substrate through a
content-addressed payload reference. They are not embedded in semantic nodes.

Hard boundary:

```text
observed
  grounded occurrence lineage

endogenous
  cognition / proposal / action-process lineage
```

Repeated endogenous records never promote themselves to observed authority.

Current relation vocabulary is fixture-driven and includes support, revision,
production, action attempt, payload deletion, and erasure relations. Relation
growth must be justified by a deterministic fixture rather than by creating a
new semantic subclass.

## Staging before canonical persistence

A proposal is an ephemeral transaction value. It is not first interned and then
governed.

Required order:

```text
staging expression
  -> syntax / lineage validation
  -> governance
  -> ACCEPT
  -> canonical semantic intern
```

Rejected semantics and anchors leave no canonical semantic or anchor state.

Trusted boundary observations are different: once the observation adapter has
accepted the occurrence, it remains grounded provenance even when every later
semantic proposal in the same transaction is rejected.

## Explicit support

A proposal may cite:

```text
observed_support_slots[]
existing_provenance_support[]
revision_of[]
```

Co-occurrence inside one transaction is not support. The writer validates each
reference and creates the provenance edges only after the proposal is accepted.

An endogenous root `outcome(...)` is rejected unless it cites sufficient
observed provenance. An Action attempt alone creates only endogenous attempt
Trace.

```text
Intention != Action != Outcome
```

## Root-context governance

Governance is external to semantic nodes.

Protected root predicates such as identity/value semantics require explicit
stronger control-plane authorization when they are asserted at root.

The same predicate inside an attributed or hypothetical world does not inherit
root mutation authority:

```text
values(self, X)                     -> protected root
believes(A, values(self, X))        -> attributed belief
counterfactual(values(self, X))     -> simulation
```

The writer therefore governs assertion scope rather than scanning a semantic
tree for protected words.

## Immutable generations

Every canonical transaction creates an immutable generation manifest:

```text
Generation
  generation_id
  parent_generation_id?
  active_roots[]
  anchor_root
  provenance_head?
  target_cognition?
  horizon?
  created_by_transaction
```

Correction creates a new generation and does not rewrite an earlier generation.

Immutability does not mean permanent retention. A retired generation can be
excluded from retention; semantic objects unreachable from every retained
generation may then be garbage-collected. This is required so crystallization
can reduce physical semantic cost rather than only reduce the active root set.

## Evidence deletion and erasure

Evidence payload availability is independent from semantic meaning.

Payload deletion removes the retained payload while preserving the occurrence
record and appending a governance tombstone.

Full erasure may remove the occurrence record as well. A historical generation
whose provenance head depended on the erased record becomes explicitly retired
or non-exact. If the current generation is affected, the writer creates a new
current generation whose provenance head is valid.

RelayLM must report lost reconstructability rather than regenerate deleted
Evidence from model priors.

## Target-relative symbols

A compact target-specific semantic operator may be retained as a stable symbol.
Migration to another cognition target is legal only when each non-native symbol
used anywhere in the active semantic expression tree has a reconstruction path.

A definition is ordinary canonical meaning:

```text
defines(SymbolRef(S), expansion)
```

It must not live in hidden side metadata. Decoder validation recursively checks
nested attributed/hypothetical semantics as well as root operators.

## One writer transaction

The prototype writer follows this bounded shape:

```text
BIND
  validate base generation and transaction syntax

OBSERVE
  trusted adapters create observed provenance

PASSIVE / DERIVE
  deterministic views only; no new persistent cognitive store

PROPOSE
  stage semantic candidates

CANONICALIZE / LINEAGE VALIDATE / GOVERN
  reject authority escalation, stale roots, unsupported Outcome,
  lost symbol reconstruction, invalid anchors, or invalid support

COMMIT
  intern accepted semantics, append their lineage, create one generation

ACT
  append endogenous action-attempt Trace

CLOSE LOOP
  only a later observation may ground Outcome
```

All canonical semantic, anchor, and provenance mutations exposed by this
prototype are methods of the same transaction store/writer boundary. There is no
separate migration or crystallization writer.

## Derived views

`Need`, deadline pressure, query truth status, symbol indexes, and migration
validation are derived views. They are not canonical stores.

The prototype query result is intentionally small:

```text
TRUE
FALSE
CONFLICT
UNKNOWN
```

No closed-world assumption or general theorem prover is introduced.

## Deterministic fixture gate

`tests/unit/test_v2_semantic_transaction.py` freezes the Issue #2135 campaign:

- grounded assertion and correction;
- endogenous self-confirmation isolation;
- contradiction and open-world unknown;
- stable entity identity and revisable co-reference;
- attributed and nested belief quarantine;
- root SOUL/identity-value governance;
- passive deadline pressure;
- Action/Outcome separation and failed Action;
- causal-overreach resistance;
- counterfactual contamination resistance;
- actual semantic-cost reduction after generation retirement/GC;
- stronger-to-weaker target decoder requirements;
- payload deletion and full erasure;
- unitary versus decomposed target representation;
- Trace/Evidence authority isolation;
- stale-base compare-and-swap;
- deterministic canonical rebuild;
- syntactic-hash versus logical-equivalence separation;
- alpha-stable binder normalization;
- embedded protected-predicate quarantine;
- direct self-authored Outcome attack;
- rejected-staging isolation;
- nested opaque-symbol migration;
- erasure provenance-head integrity;
- transaction prevalidation before boundary observation mutation.

Every fixture includes negative assertions where a forbidden canonical state
would otherwise be easy to miss.

## Kill criteria

The candidate fails if correct implementation materially requires any of:

1. a third persistent cognitive substrate;
2. direct semantic mutation outside the writer;
3. truth/source/authority metadata inside semantic nodes;
4. irreversible entity fusion;
5. closed-world default reasoning;
6. a theorem prover that commits deductions directly;
7. privileged migration/crystallization writers;
8. Action-as-Outcome;
9. logical equivalence guessed from content hashes;
10. hidden canonical state in caches/indexes/decoder side tables;
11. deleted Evidence reconstructed as observed;
12. opaque target migration without a reconstruction path.

A fixture failure matching one of these criteria is evidence against the current
minimal basis and must be reconciled to #2132 rather than repaired with an
unowned special case.

## Boundary

This prototype intentionally has no LLM/provider/GPU dependency and is not
RelayLM 2.0 product acceptance.

Actual-model work remains blocked until #2135 reaches repository
deterministic-PASS or produces an explicit falsification reconciled to #2132.

> **Ground what was observed. Trace what cognition did. Commit only through
> governance.**
