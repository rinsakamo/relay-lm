# E1-R5 Completion Report — Primary MEM Recall Candidate Discovery Bridge

Last reviewed: 2026-06-28 JST

## Source PR

Placeholder: source PR to be assigned after branch publication.

## Local E2E failure reproduced

Local evaluation showed that Primary MEM formation could succeed and produce durable character-scoped index/log/page evidence, while a later recall projected:

```text
selected_count: 0
selected_layer_counts.primary: 0
primary_recall_no_scoped_match
```

The backend then received generic/sample memory context instead of the formed Primary MEM fact.

## Implementation boundary

E1-R5 adds a request-side bounded fallback bridge inside the Primary recall runtime path. Existing M2 selection remains preferred. If no eligible scoped Primary candidate survives M2 narrowing, the bridge derives candidates from the character-scoped Primary index/log controls, validates the page and digest, applies lifecycle/scope exclusions, and rebuilds the existing RelayCTX / grounded recall handoff.

## Why symlink workaround is not sufficient

The symlink workaround can make a character-scoped store look like the older flat layout, but it does not guarantee that M2 returns a Primary MEM candidate. E1-R5 fixes the candidate handoff itself and resolves the scoped store from configured root + character id rather than relying on `runtime/memory/memory` compatibility links.

## Candidate discovery bridge design

```text
ordinary recall request
  -> scoped character store root
  -> existing M2 candidates first
  -> if no eligible Primary candidate
  -> bounded index/log scan
  -> namespace + path validation
  -> page schema/digest/index/log validation
  -> lifecycle eligibility
  -> query relevance on validated summary
  -> selected Primary MEM evidence
  -> E1-R4 grounded recall context
```

## Path/layout authority

The configured RelayMEM root remains operator-owned. Character id is converted to an opaque hash partition and is not used directly as a path component. Public diagnostics do not expose store roots or page paths.

## Namespace validator decision

Primary recall accepts the namespace shape used by queue/worker formation, including slash-style namespace tokens such as `character/default`, so memory formation and recall do not diverge.

## Request-side grounding behavior

When a candidate is selected, the E1-R4 grounded recall context receives the bounded Primary summary as runtime-private evidence and continues to instruct the backend not to invent unsupported dates, names, quantities, relationships, causes, preferences, or first-heard/first-met details.

## Response-side non-goals

No post-hoc visible response rewriting is added. E1-R5 only prepares backend-bound request context and public-safe projections.

## Tests / smokes added

```text
scripts/relaylm_e1r5_primary_mem_recall_candidate_bridge_smoke.py
scripts/relaylm_e1r5_primary_mem_recall_bridge_security_smoke.py
scripts/relaylm_e1r5_primary_mem_recall_no_symlink_smoke.py
```

The local environment available to this author did not contain a checkout of `rinsakamo/relay-lm`, so full repository smoke execution remains a PR/CI gate. The new Python files were syntax-checked before publication.

## Content leakage review

Public projections include counts, booleans, and reason ids only. The bridge explicitly preserves content-free public diagnostics and keeps memory text, protected sources, queue payloads, store roots, paths, digests, lineage, and claim/lease data out of the public projection.

## Authority preservation

E1-R5 does not add worker, queue, scheduler, browser trust, store mutation, RelaySOUL, Pin / Unpin, Held Governance, Forget / Correct, TTS/audio/avatar, or O2/O3 authority.

## Remaining gates

Run the full required validation set from the implementation prompt before merge, especially the E1-R5 smokes, E1-R4 grounded recall smokes, Phase I-1/I-2/I-4D smokes, documentation boundary smoke, docs link check, and PR-link smoke.
