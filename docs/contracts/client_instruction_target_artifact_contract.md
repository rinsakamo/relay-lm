# Client Instruction Target Artifact Contract

## Status

This document preserves the detailed **target-only** artifact shapes for client-instruction interpretation, validation, and cache storage.

It is not a current wire contract. Current behavior and active sequencing remain authoritative in:

- [Client Instruction Authority Contract](../architecture/client_instruction_authority_contract.md)
- [Phase 5-C4a Implementation Handoff](../architecture/phase5c4a_instruction_bearing_managed_apply_handoff.md)
- [Current / Target / Migration Guide](../architecture/current_target_migration_guide.md)
- [Pipeline Implementation Plan](../architecture/pipeline_implementation_plan.md)

Phase 5-C4a does not implement the artifacts below. Cache-hit RelaySCN projection belongs to Phase 5-C4b, typed parse/cache write to Phase 5-C5, and streaming control suppression to Phase 5.5.

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

This is a design example. The implemented producer must select and publish the exact schema/version before apply or cache write is enabled.

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

## Target cache entry

A target cache entry may contain only validated normalized state and bounded metadata:

```json
{
  "schema_version": "relaylm.client_instruction_cache.v0",
  "instruction_hash": "sha256:...",
  "route_model": "relaylm-vtuber",
  "character_id": "rin",
  "parser_schema_version": "relaylm.client_instruction_parse.v1",
  "authority_policy_version": "relaylm.client_instruction_authority.v1",
  "parse_status": "valid",
  "scene_state": {
    "scene_type": "vtuber_roleplay",
    "scene_role": {
      "role_name": "cafe_staff",
      "role_scope": "scene",
      "role_source": "client_system",
      "confidence": 0.96
    },
    "scene_constraints": []
  },
  "durable_candidate_count": 0,
  "blocked_instruction_kinds": [],
  "raw_instruction_persisted": false,
  "raw_response_persisted": false
}
```

The exact implemented cache schema may differ, but it must preserve these boundaries:

- instruction identity and entry scope are deterministic,
- route/character/schema/policy/parser changes invalidate scope,
- only allowlisted normalized RelaySCN fields are stored,
- raw instruction and raw backend response are not stored,
- arbitrary nested runtime artifacts are not stored,
- cache content does not become durable persona authority.

The cache is an interpretation cache, not a transcript, prompt archive, memory store, or persona store.

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
validated cache entry
  -> schema/version/scope/provenance check
  -> allowlisted RelaySCN projection
  -> Input-side RelaySCN consumer
  -> no raw instruction evidence block
```

The projection should expose only the normalized fields consumed by RelaySCN. Cache metadata, hashes, paths, parser records, and durable candidates do not enter backend context.

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

When the corresponding target phases are implemented, deterministic smoke must prove:

1. a cache miss emits at most one bounded evidence block,
2. visible text and internal control content are separated,
3. malformed artifacts do not block a valid visible response,
4. malformed artifacts do not write cache,
5. valid artifacts are allowlist validated before write,
6. raw instruction and response text never enter cache,
7. route/character/schema/policy/parser changes invalidate scope,
8. cache hit injects only the allowlisted RelaySCN projection,
9. cache hit suppresses repeated instruction evidence,
10. durable candidates never mutate RelaySOUL,
11. content-free diagnostics contain no prompt, response, scene values, hashes, or paths,
12. streaming markers and internal content never reach user/TTS output.

## Final boundary

```text
Phase 5-C4a
  bounded evidence for managed-request correctness

Phase 5-C4b
  validated allowlisted cache-hit RelaySCN projection

Phase 5-C5
  separately versioned parse validation and independent cache write

Phase 5.5
  streaming internal-control suppression
```

No target artifact becomes current merely because an example exists in this document.