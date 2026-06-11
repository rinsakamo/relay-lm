# MVP-6 Summary

MVP-6 adds a reviewable memory lifecycle workflow to RelayLM.

The goal is to prevent automatic memory writes from becoming a hidden runtime side effect. New memories now pass through a review queue, can be approved or rejected, and only approved items are applied to the memory seed file.

## Completed scope

MVP-6 covers:

- `MemoryReviewCandidate` schema
- review statuses: `pending`, `approved`, `rejected`, `applied`
- suggested memory states: `active`, `promoted`, `demoted`, `disabled`
- unambiguous length-prefixed `review_id`
- trace response to review candidate draft helper
- JSONL review queue append/read/write helpers
- review queue status update helper
- approved review candidate to `MemorySeed` conversion
- append-only memory seed YAML helper
- memory seed write validation
- approved review apply helper
- duplicate seed ID handling
- fail-fast handling for non-duplicate apply errors
- smoke coverage for review, queue, seed conversion, status update, and apply workflows

## Reviewable memory flow

```text
trace response
  -> draft MemoryReviewCandidate
  -> JSONL review queue
  -> human or tool marks pending item approved/rejected
  -> approved item becomes MemorySeed
  -> append-only seed YAML write
  -> queue item becomes applied
  -> runtime memory_light can load it as a normal memory seed
```

## MemoryReviewCandidate

A review candidate records the proposed memory and where it came from.

```text
review_id
source_trace_id
proposed_memory_id
content
character_id
suggested_state
reason
status
source
```

`review_id` uses a length-prefixed format so trace and memory IDs cannot collide through ambiguous string concatenation.

Example:

```text
review-t9:trace-001-m16:default-warm-tea
```

## Queue file

The review queue is JSONL.

Each line is one serialized `MemoryReviewCandidate`.

This keeps the MVP easy to inspect, edit, diff, and recover manually.

## Status lifecycle

```text
pending
  Drafted but not reviewed.

approved
  Allowed to be applied to the memory seed file.

rejected
  Rejected by review, or rejected during duplicate-memory apply handling.

applied
  Successfully appended to the memory seed file.
```

## Apply behavior

`apply_approved_memory_reviews_to_seed_file()`:

- reads the JSONL review queue
- skips non-approved items
- converts approved items to `MemorySeed`
- appends each seed to YAML
- marks successful items as `applied`
- handles duplicate seed IDs without blocking the whole queue
- preserves successful progress before fail-fast errors

Duplicate seed IDs are handled inside the workflow:

```text
approved duplicate -> rejected
```

Non-duplicate storage or validation errors fail fast:

```text
malformed seed file -> raise
invalid approved review content -> raise
```

Before re-raising, successful progress that already happened in the same run is persisted back to the queue.

## Safety properties

MVP-6 intentionally keeps memory writes reviewable.

Important safety properties:

- no automatic memory write in the chat request path
- no hidden runtime mutation of memory seed files
- approved-only seed conversion
- append-only seed helper rejects duplicate memory IDs
- seed write validation rejects blank content and invalid states
- duplicate approved items do not wedge the queue
- malformed seed storage fails fast instead of silently rejecting approved memories

## Main validation commands

```bash
python -m compileall relaylm scripts/relaylm_memory_review_smoke.py
python scripts/relaylm_memory_review_smoke.py

python -m compileall relaylm scripts/relaylm_memory_review_to_seed_smoke.py
python scripts/relaylm_memory_review_to_seed_smoke.py

python -m compileall relaylm scripts/relaylm_memory_review_status_smoke.py
python scripts/relaylm_memory_review_status_smoke.py

python -m compileall relaylm scripts/relaylm_memory_review_apply_smoke.py
python scripts/relaylm_memory_review_apply_smoke.py
```

## Out of scope

MVP-6 does not include:

- automatic memory extraction policy
- automatic memory writes in request handling
- memory review UI
- CLI command wrapper
- semantic deduplication
- embeddings
- vector DB
- rollback file snapshots
- multi-writer locking
- production-grade atomic queue/seed transactions

## Next phase

MVP-7 should focus on token budget and deterministic trimming improvements.

Recommended first steps:

- token budget estimator interface
- deterministic trimming based on estimated tokens rather than characters
- budget summary diagnostics
- stronger budget-related smoke coverage
- preserve current character budget as a fallback path
