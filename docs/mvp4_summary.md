# MVP-4 Summary

MVP-4 adds controlled memory candidate selection to RelayLM.

The scope stays deterministic and local. It connects MVP-3 manual memory seeds to a candidate selection layer, then uses the selected candidates in the `memory_light` runtime compiler path.

## Completed scope

MVP-4 covers:

- `MemoryCandidate` schema
- candidate states: `active`, `promoted`, `demoted`, `disabled`
- deterministic scoring
- character-aware candidate filtering
- disabled candidate exclusion
- selected candidate to `retrieved_memory` `ContextBlock` assembly
- manual memory seed to `MemoryCandidate` conversion
- config-driven memory candidate selection
- `memory.candidate_limit`
- `memory.token_budget_hint`
- `memory_light` runtime compiler use of candidate memory blocks
- API diagnostics for memory source
- trace metadata for memory source

## Runtime behavior

```text
pass_through
  -> payload unchanged
  -> compiler_used=false
  -> memory_block_used=false
  -> no memory source header

memory_light
  -> profile context compiled
  -> seed memories converted to MemoryCandidate records
  -> candidates selected deterministically
  -> selected candidates assembled as retrieved_memory ContextBlock
  -> memory_block_used=true when a block is used
  -> memory_source=memory_candidate_selection
```

## Memory selection config

```yaml
memory:
  candidate_limit: 3
  token_budget_hint: 800
```

`candidate_limit` controls how many candidates are selected. `token_budget_hint` is attached to the assembled `retrieved_memory` block.

## Candidate scoring

Current scoring is intentionally simple and deterministic:

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

## API diagnostics

MVP-4 exposes candidate memory source through response headers:

```text
x-relaylm-memory-block-used: true|false
x-relaylm-memory-source: memory_candidate_selection
```

`pass_through` does not emit `x-relaylm-memory-source`.

## Trace metadata

When trace is enabled, runtime trace metadata can include:

```json
{
  "memory_source": "memory_candidate_selection"
}
```

Trace writing remains best-effort.

## Main validation commands

```bash
python -m compileall relaylm scripts/relaylm_memory_candidate_smoke.py
python scripts/relaylm_memory_candidate_smoke.py

python -m compileall relaylm scripts/relaylm_memory_selection_config_smoke.py
python scripts/relaylm_memory_selection_config_smoke.py

python -m compileall relaylm scripts/relaylm_memory_light_apply_smoke.py
python scripts/relaylm_memory_light_apply_smoke.py

python -m compileall relaylm scripts/relaylm_api_smoke.py
python scripts/relaylm_api_smoke.py --base-url http://127.0.0.1:8090 --model relaylm-default

python -m compileall relaylm scripts/relaylm_trace_success_smoke.py
python scripts/relaylm_trace_success_smoke.py
```

## Out of scope

MVP-4 does not include:

- embeddings
- vector DB
- semantic search
- automatic memory extraction
- automatic memory write policy
- learned scoring
- recency updates from live traces
- runtime memory candidate persistence
- streaming success trace
- token-accurate budget trimming

## Next phase

MVP-5 should focus on memory lifecycle control before adding embeddings.

Recommended first steps:

- manual promotion/demotion fields in memory seed files
- candidate state loading from seed/config
- deterministic memory budget assembly with truncation rules
- trace-derived manual memory promotion smoke
- memory selection summary logs

Keep `pass_through` unchanged and continue using `memory_light` for apply-path experiments.
