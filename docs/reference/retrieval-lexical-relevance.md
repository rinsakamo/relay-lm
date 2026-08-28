# Retrieval lexical relevance

This document is the current authority for the deterministic lexical feature rule shared by bounded `MEMORY.md` retrieval, targeted Event-evidence retrieval, and Context Compiler State Working Set relevance.

## Current rule

`src/relaylm/retrieval_lexical.py` owns one shared feature extractor for these bounded lexical consumers.

For every query and consumer-owned lexical text surface:

- text is normalized with Unicode NFKC and case-folding;
- underscores keep the existing behavior of acting as token separators;
- the existing normalized `\w` tokens remain whole lexical features;
- each contiguous CJK run additionally contributes bounded character 2-grams and 3-grams;
- CJK coverage includes Han, Hiragana, Katakana, Hangul Jamo/compatibility Jamo, and Hangul syllables in the explicit Unicode ranges implemented by the shared extractor;
- no Latin/ASCII substring features are introduced.

The CJK features are additive. They allow natural phrasing differences such as query `コーヒーが好き` and persisted text `最近はコーヒーが好きです` to share lexical evidence even though the two continuous CJK strings are not identical whole tokens.

Unrelated Japanese text does not become relevant merely because it is CJK. MEMORY/Event retrieval still requires positive shared lexical evidence. State Working Set admission additionally applies its Context-owned conservative overlap rule so one accidental shared CJK n-gram does not by itself admit an otherwise unrelated State field.

## Selector convergence

The same shared feature rule is consumed by:

- `select_memory_chunks(...)` and `select_memory_chunks_with_diagnostics(...)`;
- the generic iterable path of `select_event_evidence(...)` and `select_event_evidence_with_diagnostics(...)`;
- `EventDiscoveryIndex` postings and indexed candidate scoring;
- Context Compiler State Working Set direct/current-turn and already-selected context lexical relevance.

Event iterable and indexed discovery therefore score the same query/content feature intersections. Existing Event exclusion, relevance ordering, newer-occurrence tie break, whole-Event budget admission, and chronological return rules remain unchanged.

State Working Set selection reuses only the shared feature extraction contract. Context Compiler still owns State admission and weighting: specific key evidence is stronger than semantic value evidence, which is stronger than State-class-tail evidence; identity anchor, Subjective Core, source-linked context admission, budget packing, and final Canonical State order are not defined by the shared extractor.

Diagnostics remain observations of selector-owned candidate/admission mechanics. They do not implement an independent relevance rule.

## Preserved boundaries

Latin/ASCII exact-token semantics remain unchanged. In particular, query token `likes` is not a feature of token `dislikes` and does not match it by substring.

Shared feature extraction does not make State Working Set residency a new State authority. Relevance admission changes only model-facing State residency; Canonical State persistence/lifecycle remains unchanged. The State-vs-MEMORY authority filter remains a separate semantic boundary and continues to compare MEMORY against the full eligible active Canonical State set, including State that is not resident in the current Working Set.

`memory/events.jsonl` remains the sole Event occurrence/provenance authority. `EventDiscoveryIndex` remains process-local, derived, disposable acceleration; the additional CJK postings do not create a persistent or independent Event authority.

No embeddings, vector search, semantic model, or LLM relevance call is used.

## Deferred

Semantic/vector retrieval, temporal interpretation, persistent/segmented derived indexes, runtime default retrieval budgets, total token-aware budgeting, and broader State-vs-MEMORY conflict semantics remain outside this rule.
