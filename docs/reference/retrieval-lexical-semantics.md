# Retrieval lexical semantics

This document is the current shared semantic authority for deterministic lexical discovery and relevance used by RelayLM MEMORY and Event retrieval.

## Shared lexical feature owner

`src/relaylm/retrieval_lexical.py` owns the lexical feature contract consumed by both `memory_retrieval.py` and `event_retrieval.py`.

Current feature semantics are:

- normalize with Unicode NFKC and case-folding;
- preserve normalized whole `\w` tokens as exact features;
- replace `_` with a token boundary;
- add bounded 2- and 3-character features for contiguous CJK runs;
- do not introduce Latin/ASCII substring matching, so `likes` does not match `dislikes`;
- retrieval query evidence is a **set of distinct eligible lexical features** with length at least two;
- repeating the same normalized query feature does not increase relevance by itself.

The distinct-query rule applies equally to MEMORY and Event retrieval. A selector may apply source-specific weights after the shared query features are defined, but it must not reinterpret query multiplicity as additional evidence.

## MEMORY relevance

For each parsed MEMORY heading chunk:

- each distinct query feature contributes `+4` when present in the heading path;
- the same distinct query feature contributes `+1` when present in the complete chunk content;
- only positive-score chunks are candidates;
- score ties preserve document order for admission;
- selected chunks are restored to document order after bounded admission.

Heading/body weighting is MEMORY-specific ranking policy. The shared lexical feature meaning remains common with Event retrieval.

## Event relevance and discovery

For each eligible message Event:

- relevance is the number of distinct query features also present in Event content;
- only positive-score Events are candidates;
- higher overlap ranks first;
- equal relevance prefers the newer occurrence by Event Journal source order;
- selected Events are restored to source chronology after bounded admission.

`EventDiscoveryIndex` is a derived process-local acceleration surface. Its postings and candidate scores must preserve the same lexical feature and relevance semantics as generic iterable Event retrieval. It is not occurrence authority and does not change Event Journal validation or provenance.

## Boundaries

These lexical rules are read/select semantics only. They do not:

- mutate MEMORY, Events, State, or indexes as authority;
- define State-vs-MEMORY authority;
- define Working Context retention;
- choose runtime/default budgets or total token policy;
- imply semantic/vector/embedding relevance, temporal interpretation, or LLM adjudication.

Stronger semantic or temporal retrieval may be added only as a separately bounded semantic transaction. Candidate acceleration must remain subordinate to the same current retrieval semantics rather than becoming an alternate authority.
