# Retrieval lexical relevance

This document is the current authority for the deterministic lexical feature rule shared by bounded `MEMORY.md` retrieval and targeted Event-evidence retrieval.

## Current rule

`src/relaylm/retrieval_lexical.py` owns one shared feature extractor for both retrieval families.

For every query, MEMORY heading/body, and eligible Event message content:

- text is normalized with Unicode NFKC and case-folding;
- underscores keep the existing behavior of acting as token separators;
- the existing normalized `\w` tokens remain whole lexical features;
- each contiguous CJK run additionally contributes bounded character 2-grams and 3-grams;
- CJK coverage includes Han, Hiragana, Katakana, Hangul Jamo/compatibility Jamo, and Hangul syllables in the explicit Unicode ranges implemented by the shared extractor;
- no Latin/ASCII substring features are introduced.

The CJK features are additive. They allow natural phrasing differences such as query `コーヒーが好き` and persisted text `最近はコーヒーが好きです` to share positive lexical evidence even though the two continuous CJK strings are not identical whole tokens.

Unrelated Japanese text does not receive a positive candidate merely because it is CJK. A candidate still requires at least one shared lexical feature.

## Selector convergence

The same shared feature rule is consumed by:

- `select_memory_chunks(...)` and `select_memory_chunks_with_diagnostics(...)`;
- the generic iterable path of `select_event_evidence(...)` and `select_event_evidence_with_diagnostics(...)`;
- `EventDiscoveryIndex` postings and indexed candidate scoring.

Event iterable and indexed discovery therefore score the same query/content feature intersections. Existing Event exclusion, relevance ordering, newer-occurrence tie break, whole-Event budget admission, and chronological return rules remain unchanged.

Diagnostics remain observations of the selector-owned candidate/admission mechanics. They do not implement an independent relevance rule.

## Preserved boundaries

Latin/ASCII exact-token semantics remain unchanged. In particular, query token `likes` is not a feature of token `dislikes` and does not match it by substring.

This lexical feature rule does not alter Context Compiler active-State selection or State-vs-MEMORY authority filtering. Those remain separate semantic owners and keep their existing lexical contracts.

`memory/events.jsonl` remains the sole Event occurrence/provenance authority. `EventDiscoveryIndex` remains process-local, derived, disposable acceleration; the additional CJK postings do not create a persistent or independent Event authority.

No embeddings, vector search, semantic model, or LLM relevance call is used.

## Deferred

Semantic/vector retrieval, temporal interpretation, persistent/segmented derived indexes, runtime default retrieval budgets, total token-aware budgeting, and broader State-vs-MEMORY conflict semantics remain outside this rule.
