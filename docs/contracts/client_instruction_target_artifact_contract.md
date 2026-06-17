# Client Instruction Artifact Current / Target Contract

## Status

This document preserves the detailed artifact shapes for client-instruction interpretation, validation, cache storage, and future RelaySCN projection.

The boundaries are mixed and must be read separately:

- **Current implemented:** read-only validation of `relaylm.client_instruction_cache.v0` entries through `relaylm.client_instruction_cache_lookup.resolve_client_instruction_cache_lookup` and request-local runtime lookup wiring.
- **Target only:** first-pass control-envelope production, typed parse validation, cache-entry write, allowlisted RelaySCN projection apply, retry execution, and Stream Unpack.

Current behavior and active sequencing remain authoritative in:

- [Client Instruction Authority Contract](../architecture/client_instruction_authority_contract.md)
- [Phase 5-C4a Implementation Handoff](../architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md)
- [Pipeline Implementation Plan](../architecture/pipeline_implementation_plan.md)

Phase 5-C4a does not implement the target producer/apply artifacts below. Cache-hit RelaySCN projection belongs to Phase 5-C4b, typed parse/cache write to Phase 5-C5, and streaming control suppression to Phase 5.5.

## Authority invariant

```text
client instruction content
  = low-trust current-scene evidence

validated RelaySCN projection
  = bounded normalized scene state

RelaySOUL
  = separate durable persona authority
```

No artifact in this document may override runtime/safety policy, directly mutate RelaySOUL, persist raw prompt/response text, or become an opaque backend prompt block.

## Target first-pass envelope

A future cache-miss response may contain visible text plus an internal separately versioned control envelope:

```text
いらっしゃいませ。今日は何にしますか？

<relaylm_control version="1">
{
  "client_instruction_parse": {
    "scene_type": "vtuber_roleplay",
    "scene_role": {
      "role_name": "cafe_staff",
      "role_scope": "scene",
      "confidence": 0.96
    },
    "scene_context": {
      "setting": "virtual_cafe"
    },
    "scene_constraints": [
      {
        "constraint_type": "spoken_response_length",
        "value": "short"
      }
    ],
    "durable_persona_candidates": [],
    "blocked_instruction_kinds": []
  }
}
</relaylm_control>
```

This is a design example. The implemented producer must select and publish the exact schema/version before parse apply or cache write is enabled.

## Target parse schema

Suggested allowlisted shape:

```json
{
  "scene_type": "string|null",
  "scene_role": {
    "role_name": "string|null",
    "role_scope": "turn|scene",
    "confidence": 0.0
  },
  "scene_context": {
    "setting": "string|null",
    "task": "string|null",
    "participants": []
  },
  "scene_constraints": [
    {
      "constraint_type": "string",
      "value": "string|number|boolean"
    }
  ],
  "durable_persona_candidates": [
    {
      "candidate_kind": "identity|value|worldview|output_policy|relationship",
      "normalized_value": "string",
      "confidence": 0.0
    }
  ],
  "blocked_instruction_kinds": []
}
```

Validation must reject or strip:

- unknown keys,
- excessive nesting or collection sizes,
- raw prompt or response copies,
- secret-bearing URLs or paths,
- runtime/safety/tool authority claims,
- direct persistence instructions,
- unsupported semantic value types,
- invalid confidence/range/scope values.

Durable persona entries remain candidates only. They are not RelaySOUL patches and cannot be applied by the parser or cache writer.

## Current read-only cache-entry acceptance schema

Current code already validates the following entry schema without writing or applying it:

```text
schema_version:
  relaylm.client_instruction_cache.v0

validator/consumer:
  relaylm.client_instruction_cache_lookup.resolve_client_instruction_cache_lookup

runtime reader/wiring:
  relaylm.client_instruction_cache_reader.read_client_instruction_cache_candidate
  relaylm.client_instruction_cache_lookup_runtime

current effects:
  hit / miss / blocked request-local result
  typed runtime-private parsed entry on hit
  content-free diagnostics projection

not current:
  cache writer
  RelaySCN projection apply
  backend prompt injection
```

An entry accepted by the current validator has this exact top-level shape:

```json
{
  "schema_version": "relaylm.client_instruction_cache.v0",
  "cache_key_sha256": "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
  "instruction_fingerprint_sha256": "abcdef0123456789abcdef0123456789abcdef0123456789abcdef0123456789",
  "route_model": "relaylm-vtuber",
  "character_id": "rin",
  "instruction_parse_schema_version": "client_instruction_parse.v1",
  "authority_policy_version": "client_instruction_authority.v1",
  "parser_version": null,
  "parse_status": "valid",
  "scene_state": {
    "scene_type": "vtuber_roleplay",
    "scene_role": {
      "role_name": "cafe_staff",
      "role_scope": "scene",
      "role_source": "client_system",
      "confidence": 0.96
    },
    "scene_context": {
      "setting": "virtual_cafe",
      "task": null,
      "participants": ["character", "viewer"]
    },
    "scene_constraints": []
  },
  "durable_candidate_count": 0,
  "blocked_instruction_kinds": [],
  "raw_instruction_persisted": false,
  "raw_response_persisted": false
}
```

The two SHA-256 fields are exactly 64 lowercase hexadecimal characters and remain runtime-private. The example values are placeholders with the required lexical shape, not real cache identities.

A future Phase 5-C5 writer must either:

1. emit this exact v0 shape so the current validator accepts it, or
2. introduce a new schema version and update reader, validator, runtime wiring, compatibility handling, and smoke coverage together.

It must not change fields while retaining `relaylm.client_instruction_cache.v0`.

The cache is an interpretation cache, not a transcript, prompt archive, memory store, or persona store. Only allowlisted normalized RelaySCN fields and bounded metadata may be present. Raw instruction, raw response, arbitrary nested runtime artifacts, and durable persona bodies are forbidden.

## Target validation and write sequence

```text
cache miss
  -> bounded low-trust evidence
  -> visible response + target control artifact
  -> RelayCTX Unpack separates visible/internal content
  -> schema validation
  -> authority/policy validation
  -> route/character/version/provenance validation
  -> independent cache-write gate
```

A valid visible response and cache mutation are separate outcomes.

```text
valid visible response
+ invalid control artifact
  -> return visible response
  -> do not write cache
  -> record bounded content-free failure metadata
```

Suggested failure record:

```json
{
  "parse_status": "failed",
  "retry_count": 1,
  "last_failure_reason": "invalid_schema",
  "cache_entry_written": false
}
```

A bounded retry policy should allow at most a small defined number of later first-pass attempts. Repeated failure keeps the instruction non-authoritative and uses only an existing safe scene/default or explicit setup/repair path.

## Target cache-hit projection

A cache hit must not inject an opaque cache entry. It must first produce an allowlisted projection:

```text
validated relaylm.client_instruction_cache.v0 entry
  -> schema/version/scope/provenance check
  -> allowlisted RelaySCN projection
  -> Input-side RelaySCN consumer
  -> no raw instruction evidence block
```

The projection should expose only the normalized fields consumed by RelaySCN. Cache metadata, hashes, paths, parser records, and durable candidates do not enter backend context.

The current read-only lookup result does not itself implement this projection or apply it.

## Target non-stream and stream handling

### Non-stream

```text
complete backend response
  -> split visible text / target control envelope
  -> validate control artifact independently
  -> return visible text
  -> optionally write validated cache entry through its own gate
```

### Stream

The Stream Unpack implementation must:

- detect the target opening sentinel without leaking partial markers,
- hold a trailing buffer at least as long as the sentinel,
- stop forwarding once an internal envelope is confirmed,
- collect the envelope internally until the closing sentinel,
- preserve already emitted valid visible text if the envelope is malformed,
- keep internal content out of user output, captions, TTS, and avatar speech,
- never write cache from an incomplete or unvalidated envelope.

## Design-only configuration shape

The following names remain design examples until added to the formal Pydantic schema and config ledger:

```yaml
client_history_policy: replace_with_relayctx
client_instruction_policy: relay_scn_first

client_instruction_cache_enabled: true
client_instruction_cache_root: .relaylm/client_instruction_cache
client_instruction_cache_max_entries: 256

client_instruction_first_pass_enabled: true
client_instruction_control_artifact_enabled: true
client_instruction_parse_retry_limit: 1

client_instruction_schema_version: v1
client_instruction_policy_version: v1

client_instruction_durable_candidate_enabled: false
```

Current operators must use only fields present in `relaylm/config.py`, `docs/config_schema.md`, and `config.example.yaml`.

## Required implementation smoke

Current read-only regressions must continue to prove:

1. strict v0 entry shape and unknown-key rejection,
2. exact hash, route, character, schema, policy, and parser scope matching,
3. malformed, oversized, symlinked, or out-of-root entries fail closed,
4. hit/miss/blocked diagnostics remain content-free,
5. lookup does not write cache or apply scene state.

When the corresponding target phases are implemented, deterministic smoke must additionally prove:

6. a cache miss emits at most one bounded evidence block,
7. visible text and internal control content are separated,
8. malformed artifacts do not block a valid visible response,
9. malformed artifacts do not write cache,
10. valid artifacts are allowlist validated before write,
11. raw instruction and response text never enter cache,
12. route/character/schema/policy/parser changes invalidate scope,
13. cache hit injects only the allowlisted RelaySCN projection,
14. cache hit suppresses repeated instruction evidence,
15. durable candidates never mutate RelaySOUL,
16. content-free diagnostics contain no prompt, response, scene values, hashes, or paths,
17. streaming markers and internal content never reach user/TTS output.

## Final boundary

```text
Current
  validate relaylm.client_instruction_cache.v0 entries read-only
  no writer
  no RelaySCN projection apply

Phase 5-C4a
  bounded evidence for managed-request correctness

Phase 5-C4b
  validated allowlisted cache-hit RelaySCN projection

Phase 5-C5
  separately versioned parse validation and independent cache write

Phase 5.5
  streaming internal-control suppression
```

No target producer or apply behavior becomes current merely because an example exists in this document.