# MVP-5 Summary

MVP-5 adds memory lifecycle controls to RelayLM's deterministic memory candidate path.

The goal is to keep memory selection inspectable and controllable before adding embeddings, vector search, or automatic memory writing.

## Completed scope

MVP-5 covers:

- memory seed `state` loading
- valid seed states: `active`, `promoted`, `demoted`, `disabled`
- seed state validation
- `MemorySeed` to `MemoryCandidate` state inheritance
- state-aware deterministic candidate selection
- example memory states in `examples/memory/default_memories.yaml`
- `MemorySelectionSummary`
- runtime selection summary diagnostics
- trace metadata for selection summary
- deterministic memory block assembly
- character-budget trimming
- `MemoryBlockAssembly`
- runtime `memory.character_budget` config
- trace metadata for memory block assembly
- smoke coverage for state loading, summary payloads, and budget trimming

## Runtime memory flow

```text
memory_light
  -> character.memory_seed_path
  -> MemorySeed records
  -> MemoryCandidate records
  -> state-aware deterministic selection
  -> MemorySelectionSummary
  -> MemoryBlockAssembly
  -> retrieved_memory ContextBlock
  -> compiled system context
  -> diagnostics / trace metadata
```

## Memory states

```text
active
  Normal selectable memory.

promoted
  Boosted memory. It should rank above normal active memories unless limits or budgets prevent inclusion.

demoted
  Lower-priority memory. It remains available but is ranked after active memories.

disabled
  Excluded from candidate selection.
```

Current scoring remains deterministic:

```text
score = state_bonus + importance * 100 + recency
```

State bonuses:

```text
promoted: +1000
active: 0
demoted: -1000
disabled: excluded
```

Tie-breaker:

```text
memory_id ascending
```

## Memory selection summary

`MemorySelectionSummary` records:

```text
total_candidates
eligible_count
selected_count
limit
character_id
selected_memory_ids
excluded_disabled_ids
excluded_character_ids
state_counts
```

This summary is available in compiled request logs and trace metadata.

## Memory block assembly

`MemoryBlockAssembly` records:

```text
included_memory_ids
dropped_memory_ids
character_budget
rendered_characters
```

This makes budget trimming observable without requiring token-accurate accounting yet.

## Runtime config

```yaml
memory:
  candidate_limit: 3
  token_budget_hint: 800
  character_budget: 1200
```

`candidate_limit` controls how many candidates are selected before block assembly.

`token_budget_hint` is attached to the assembled `retrieved_memory` block.

`character_budget` is a deterministic character-level assembly budget. It is not token accurate and is intended as a simple MVP control surface.

## Trace metadata

When trace is enabled, runtime trace metadata can include:

```json
{
  "memory_source": "memory_candidate_selection",
  "memory_selection_summary": {
    "selected_count": 3,
    "selected_memory_ids": ["default-relaylm-project", "default-like-tea", "shared-short-replies"]
  },
  "memory_block_assembly": {
    "included_memory_ids": ["default-relaylm-project", "default-like-tea", "shared-short-replies"],
    "dropped_memory_ids": [],
    "character_budget": 1200,
    "rendered_characters": 300
  }
}
```

Trace writing remains best-effort.

## Main validation commands

```bash
python -m compileall relaylm scripts/relaylm_memory_state_smoke.py
python scripts/relaylm_memory_state_smoke.py

python -m compileall relaylm scripts/relaylm_memory_selection_summary_smoke.py
python scripts/relaylm_memory_selection_summary_smoke.py

python -m compileall relaylm scripts/relaylm_memory_budget_smoke.py
python scripts/relaylm_memory_budget_smoke.py

python -m compileall relaylm scripts/relaylm_memory_light_apply_smoke.py
python scripts/relaylm_memory_light_apply_smoke.py

python -m compileall relaylm scripts/relaylm_trace_success_smoke.py
python scripts/relaylm_trace_success_smoke.py
```

## Out of scope

MVP-5 does not include:

- embeddings
- vector DB
- semantic retrieval
- automatic memory extraction
- automatic memory write policy
- learned scoring
- recency updates from live traffic
- persistent memory candidate DB
- token-accurate trimming
- streaming success trace

## Next phase

MVP-6 should focus on reviewable memory lifecycle workflows.

Recommended first steps:

- trace-derived memory review queue
- manual memory promotion/demotion workflow
- generated memory candidate draft records
- approval-required memory writes
- append-only memory seed update helper

Keep automatic memory writing out of the default runtime path until review and rollback behavior are stable.
