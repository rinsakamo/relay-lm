# E1-R5 Primary MEM Recall Candidate Discovery Bridge

Last reviewed: 2026-06-28 JST

## Status

E1-R5 adds a bounded request-side bridge for character-scoped Primary MEM recall. E1-R4 already builds backend-bound grounded recall instructions from selected Primary MEM evidence, but local E2E evaluation showed a gap before that stage: formed Primary MEM pages could exist under the character-scoped store while `selected_count` stayed `0` because no Primary MEM page became an M2 selected candidate.

## Problem

The failing local path was:

```text
trusted Home / explicit trusted request
  -> durable source and queue evidence
  -> local worker drain
  -> Primary MEM durable formation
  -> character-scoped Primary MEM index/log/page creation
  -> later SOUL Lab Home recall
  -> Primary recall projection attempted
  -> selected_count: 0
  -> primary_recall_no_scoped_match
```

The symlink workaround `runtime/memory/memory -> runtime/memory/characters/<hash>/memory` could make the index/log visible to older flat-store diagnostics, but it did not guarantee that the page became an eligible Primary recall candidate. The issue was candidate bridging, not only path visibility.

## Implemented boundary

The preferred M2 path remains the first relevance owner. E1-R5 only runs after the scoped Primary recall adapter cannot select an eligible Primary candidate from existing M2 results.

When the fallback runs, it:

1. resolves the character-scoped store root from configured root + route character id;
2. reads only bounded Primary MEM control files from that scoped root;
3. derives bounded Primary page candidates from index entries for the exact namespace;
4. validates page path, schema, digest, index entry, and log entry consistency;
5. applies Primary retrieval lifecycle eligibility, including hidden / prepared / prior / recovery-required / corrupt exclusions;
6. checks bounded query relevance against the validated Primary summary when query hints are available;
7. rebuilds the existing bounded snippet handoff consumed by RelayCTX and E1-R4 grounded recall.

The bridge does not depend on the compatibility symlink and does not materialize an unbounded tree.

## Namespace decision

Primary recall now accepts the same namespace token shape used by the queue/worker side, including slash-style namespaces such as `character/default`. The goal is to avoid a formation-success / recall-reject split. Character and namespace values remain runtime-private and are not exposed in public projections.

## Grounded recall behavior

When the bridge selects a Primary MEM page, E1-R4 grounded recall receives the same selected-memory shape as the M2 path. Backend-bound context may include the bounded supported summary as private evidence, and the instruction continues to require unsupported-detail suppression:

```text
Use only grounded_recall_context evidence_items for remembered facts.
Do not invent dates, names, preferences, quantities, relationships, or causes.
Say the retrieved memory does not support unsupported details.
```

## Public projection

Public diagnostics remain content-free. Allowed public fields include counts and booleans such as:

```text
primary_candidate_discovery_attempted
primary_candidate_count
grounding_enabled
grounded_item_count
unsupported_detail_policy
evidence_content_included=false
runtime_private_evidence_omitted=true
```

The projection must not include raw memory text, raw transcript text, protected source body, queue payload, store root, source path, claim token, lease owner, token digest, source digest, page digest, lineage, or exact private ids.

## Non-goals

E1-R5 does not add O2/O3 supervision, polling, daemons, new queue authority, worker authority, browser-owned trust, automatic bootstrap, broad memory layout migration, Pin / Unpin semantics, Held Apply / Discard behavior, Forget / Correct behavior, Secondary MEM consolidation, RelaySOUL mutation, media runtime work, or post-hoc visible response rewriting.
