# RelayLM 2.0 Cognitive Work — R2 replacement preregistration

Owner: #2290  
Parent experiment: #2187  
Historical failed execution: #2288  
Original preregistration: #2279 / #2283

## Status boundary

#2288 remains a terminal `R2_INCOMPLETE` transaction. It stopped after three completed provider calls when a BANK:THINK response was strict one-key JSON but encoded a numeric semantic answer as a JSON integer:

```json
{"answer":87}
```

The frozen v1 parser required a non-empty JSON string and therefore rejected that completion. No task bank, arm outcome, R2 category, or scientific allocator result was created.

This document defines a replacement experiment identity only. It adds no provider calls and does not authorize a replacement physical campaign.

## Forensic classification

`REPRESENTATION_PROTOCOL_DEFECT`

Reason:

- the generator deliberately contains integer-valued tasks and stores their evaluator targets as canonical decimal strings;
- the failed response preserved the required one-key JSON object and represented the answer as the corresponding JSON integer scalar;
- string-vs-integer serialization is not part of the Cognitive Work treatment;
- accepting a bounded scalar representation can be defined without consulting evaluator truth.

The original host was correct to fail closed because its frozen contract was string-only. The repair therefore receives a new preregistration identity rather than rewriting #2288.

## Versioned answer protocol

Historical R2 v1:

```text
answer protocol = STRING_ONLY
example shape = {"answer":"..."}
```

Replacement R2 v2:

```text
answer protocol = CANONICAL_STRING_OR_INTEGER
```

Accepted raw JSON values:

```text
non-empty string
integer, excluding bool
```

Canonical evaluator representation:

```text
string  -> trim surrounding whitespace
integer -> canonical base-10 decimal string
```

Rejected:

```text
bool
float
null
array
object
empty/whitespace string
extra keys
duplicate keys
NaN / Infinity / non-standard JSON constants
```

Canonicalization does not receive or inspect `expected_answer`.

## Fresh unseen task identity

The replacement campaign must not reuse the original #2283 root seed because #2288 exposed physical model behavior for the beginning of that task sequence.

The new root seed is derived only from the future merge commit of this replacement preregistration:

```text
root_seed = SHA256-framed(
  "relaylm2-2187-r2-replacement-v2",
  exact_replacement_preregistration_merge_commit_sha
)
```

No seed selection occurs after generated tasks or model outputs are inspected.

The original and replacement task IDs must be disjoint under the same commit input because their root-seed domains differ.

## Scientific invariants preserved from #2283

The replacement imports or directly reuses the original scientific machinery wherever possible.

Unchanged:

```text
5 hidden regimes x 8 tasks = 40
ZERO / THINK / RETRIEVE / OBSERVE
A0 = fixed THINK
A1 = availability heuristic
A2 = one charged actual-model allocator call
A3 = evaluator-only oracle
shared physical operation bank
hidden-regime / expected-answer / packet anti-leak rules
A2 overhead accounting
physical plan shape = 136 calls
per-arm treatment call ceiling = 120
retrieval-unit ceiling = 8
observation-unit ceiling = 8
context limit = 8192
aggregate input/output tokens measured, not hard-capped
paired directional exact tests
10,000-resample paired bootstrap
material-task / heuristic-gap thresholds
interpretation categories
oracle Pareto-frontier tie-break
no retry / fallback
```

The replacement does not change task templates or regime semantics; it invokes the original frozen generator logic under the new root seed domain.

## Physical boundary

Provider calls in #2290:

```text
0
```

After this preregistration is merged, a separate owner must bind the replacement merge commit/root seed into a replacement host identity. The existing #2286 host is intentionally frozen to #2283 and must not be made dynamically permissive.

A later physical execution requires another separately named one-shot owner with fresh repository and physical authority.

## Scientific consequence

```text
scientific allocator verdict = NONE
production scheduler authority = NONE
architecture consequence = NONE
```

The protocol repair changes the measuring interface, not the answer to the allocation hypothesis.

> Fail closed on the frozen claim; repair the interface only in a new experiment identity.

> Do not make serialization trivia the treatment.
