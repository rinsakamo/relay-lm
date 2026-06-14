# MVP-3 Summary

MVP-3 adds the first practical local memory layer for RelayLM.

The scope stays intentionally small: manual memory seed files, local JSONL trace helpers, and memory-light context insertion. It does not add embeddings or vector search yet.

> **Current trace contract:** P0-A1 hardening supersedes the original MVP-3 trace payload shape. The default JSONL trace is now a content-free audit trace. It does not persist message bodies, assistant response text, snippets, evidence, tool payloads, or local paths. See `docs/architecture/audit_trace_content_free_contract.md`.

## Completed scope

MVP-3 covers:

- local JSONL audit trace records
- append/read trace helpers
- manual memory seed loading
- example memory seed file
- memory seed filtering by character ID
- shared memory entries
- memory seed to `retrieved_memory` `ContextBlock`
- memory block insertion after profile blocks
- config-based memory seed resolution
- `memory_light` payload compilation with memory seed block
- API diagnostics for memory block usage
- trace config diagnostics
- audit trace writing for backend error paths
- audit trace writing for non-stream JSON backend responses

## Runtime behavior

```text
pass_through
  -> payload unchanged
  -> memory_block_used=false

memory_light
  -> compiled profile context
  -> retrieved_memory block inserted when configured
  -> memory_block_used=true when a seed memory block is used
```

Current compiled context order:

```text
common_runtime_policy
character_soul_anchor
character_output_policy
room_anchor
retrieved_memory
incoming_system_prompt
```

## Trace behavior

Trace config is controlled by:

```yaml
trace:
  enabled: false
  path: traces/relaylm_trace.jsonl
```

When enabled, RelayLM can write content-free JSONL audit records for:

- backend error path
- non-stream JSON backend response path

The audit record retains request shape, event/status identifiers, content-free node diagnostics, counts, opaque IDs, and hashes. It does not retain conversation or retrieval content.

Streaming success trace is not included yet.

## Main validation commands

```bash
python -m compileall relaylm scripts/relaylm_jsonl_trace_smoke.py
python scripts/relaylm_jsonl_trace_smoke.py
python scripts/relaylm_trace_content_free_contract_smoke.py

python -m compileall relaylm scripts/relaylm_memory_seed_smoke.py
python scripts/relaylm_memory_seed_smoke.py

python -m compileall relaylm scripts/relaylm_memory_block_insertion_smoke.py
python scripts/relaylm_memory_block_insertion_smoke.py

python -m compileall relaylm scripts/relaylm_config_memory_seed_smoke.py
python scripts/relaylm_config_memory_seed_smoke.py

python -m compileall relaylm scripts/relaylm_memory_light_apply_smoke.py
python scripts/relaylm_memory_light_apply_smoke.py

python -m compileall relaylm scripts/relaylm_trace_success_smoke.py
python scripts/relaylm_trace_success_smoke.py
```

## Out of scope

MVP-3 does not include:

- embeddings
- vector DB
- semantic retrieval
- automatic memory extraction
- automatic memory write policy
- trace summarization
- sensitive debug trace sink
- streaming success trace
- token budget trimming

## Next phase

MVP-4 should focus on controlled memory candidate selection before adding vector search.

Recommended first steps:

- memory candidate schema
- manual promotion/demotion fields
- recency and importance scoring
- deterministic memory selection smoke
- fixed budget memory block assembly

Keep `pass_through` unchanged and use `memory_light` for apply-path experiments.
