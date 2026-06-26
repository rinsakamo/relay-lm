# RelayLM Configuration Reference

## Status and authority

This is the active current configuration reference for `relaylm.config.RelayLMConfig`.

- The runtime source of truth is `relaylm/config.py`.
- `config.example.yaml` is the exhaustive commented example.
- `examples/config/openwebui_lmstudio.yaml` is the copy-ready standard setup.
- Target architecture documents do not create current config fields by themselves.
- A helper or runtime boundary without a `RelayLMConfig` field must not be documented as if it had a top-level enable/apply gate.
- CLI flags do not override server/operator-owned safety gates.

## Important authority warning

Client `system` and `developer` messages are not fallback RelaySOUL sources.

```text
client system/developer message
  -> current low-trust instruction evidence
  -> current compatibility compiler or future RelaySCN normalization
  -> never direct durable SOUL authority
```

Current managed profiles require configured `soul` and `output_policy` files. Missing profile configuration raises `ProfileConfigurationError`; RelayLM does not silently promote a client system prompt into SOUL.

See [Client Instruction Authority Contract](architecture/client_instruction_authority_contract.md).

## Minimal pass-through example

```yaml
mode: pass_through

listen:
  host: 127.0.0.1
  port: 8090

backends:
  local_backend:
    type: openai_compatible
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-default:
    backend: local_backend
    backend_model: local-model
    mode: pass_through
```

A pass-through route does not require a character profile.

## Minimal current `memory_light` example

```yaml
mode: memory_light
common_runtime_policy: examples/profiles/default/common_runtime_policy.md

backends:
  local_backend:
    type: openai_compatible
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: local-model

model_routes:
  relaylm-companion:
    backend: local_backend
    backend_model: local-model
    character_id: companion
    mode: memory_light
    cache_namespace: character/companion
    memory_namespace: character/companion

characters:
  companion:
    soul: examples/profiles/companion/SOUL.md
    output_policy: examples/profiles/companion/OUTPUT_POLICY.md
    scene_state: examples/profiles/default/SCENE_STATE.md
    memory_seed_path: examples/memory/companion_memories.yaml
```

## Current history-authority limitation

The default `memory_light` compatibility compiler may preserve prior client user/assistant history after the RelayLM-owned compiled system message.

```yaml
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
```

Implemented bounded apply contracts:

- `client_history_exclusion_apply.v0` supports managed `memory_light` requests with no client `system` or `developer` messages.
- `client_history_exclusion_apply.v1` supports instruction-bearing managed requests only when an exact `client_instruction_source.v1` provenance envelope selects the current instruction candidates.
- Missing, invalid, unordered, duplicated, out-of-range, post-user, non-instruction, or identity-mismatched v1 provenance fails closed.
- Failure never restores raw prior history or treats all client instruction messages as current evidence.

Do not claim current-turn-only managed reconstruction unless the exact request shape and apply gates are verified. Active tool-chain reconstruction and broader compatibility shapes remain incomplete.

## Core top-level fields

### `mode`

```text
pass_through | memory_light | memory_full
```

Default: `pass_through`.

- `pass_through`: delegated client-message authority; profile compiler diagnostics only.
- `memory_light`: current profile compiler apply-capable.
- `memory_full`: accepted by config/routing, but current profile compile apply is not enabled for this mode.

A route-level mode may override the top-level default.

### `listen`

```yaml
listen:
  host: 127.0.0.1
  port: 8090
```

Defaults are `127.0.0.1` and `8090`. SOUL Lab read routes require both a loopback configured host and a loopback transport peer; this does not change Core route availability.

### `common_runtime_policy`

Optional path to a shared RelayLM-owned runtime policy file. A managed character may override it with `characters.<id>.common_runtime_policy`.

### `trace`

```yaml
trace:
  enabled: false
  path: traces/relaylm_trace.jsonl
```

Trace is default-off. Persisted trace must remain typed and content-free.

## `backends`

Required mapping of backend IDs to OpenAI-compatible backend configuration.

```yaml
backends:
  local_backend:
    type: openai_compatible
    base_url: http://127.0.0.1:8000/v1
    api_key: dummy
    default_model: local-model
    timeout_seconds: 60.0
```

Fields:

- `type`: currently only `openai_compatible`.
- `base_url`: required.
- `api_key`: optional.
- `default_model`: optional backend model fallback.
- `timeout_seconds`: default `60.0`.

## `model_routes`

```yaml
model_routes:
  relaylm-companion:
    backend: local_backend
    backend_model: local-model
    character_id: companion
    mode: memory_light
    cache_namespace: character/companion
    memory_namespace: character/companion
    user_id:
    user_type:
    room_id:
    scene_id:
    session_id:
```

Fields:

- `backend`: required backend ID.
- `backend_model`: optional backend model override.
- `character_id`: required for current managed profile compilation; optional for pass-through.
- `mode`: optional route mode override.
- `cache_namespace`: optional instruction/cache scope metadata.
- `memory_namespace`: optional memory scope metadata.
- `user_id`, `user_type`, `room_id`, `scene_id`, `session_id`: optional route-level scope metadata.

Persona file paths belong under `characters`, not `model_routes`.

## `characters`

```yaml
characters:
  companion:
    common_runtime_policy:
    soul: examples/profiles/companion/SOUL.md
    output_policy: examples/profiles/companion/OUTPUT_POLICY.md
    room_anchor:
    memory_seed_path: examples/memory/companion_memories.yaml
    relationship_anchor:
    stable_memory_summary:
    scene_state: examples/profiles/default/SCENE_STATE.md
    room_state:
    token_policy_shadow_enabled:
```

Required fields:

- `soul`
- `output_policy`

Optional fields:

- `common_runtime_policy`
- `room_anchor`
- `memory_seed_path`
- `relationship_anchor`
- `stable_memory_summary`
- `scene_state`
- `room_state`
- `token_policy_shadow_enabled`

`room_state` is a legacy alias used only when `scene_state` is unset. `room_anchor` is a compatibility field for fixed durable room constraints; do not place current topic, current mood, open questions, recent turns, or durable memory bodies there.

### Scene/CTX/EMO ownership

`scene_state` describes semantic situation and policy inputs. Current mood/raw affect belongs to RelayEMO; current topic, open questions, unresolved slots, and transcript-shaped recent turns belong to RelayCTX; durable memory bodies belong to RelayMEM.

## `memory`

```yaml
memory:
  candidate_limit: 3
  token_budget_hint: 800
  character_budget:
  token_budget:
  chars_per_token: 4
  token_policy_shadow_enabled: false
  token_budget_truncation_enabled: false
  root_path:
  store_enabled: false
  retrieval_dry_run_only: true
  ctx_block_apply_enabled: false
  snippet_extraction_enabled: false
  snippet_dry_run_only: true
  snippet_apply_enabled: false
  snippet_runtime_injection_enabled: false
  snippet_runtime_dry_run_only: true
  snippet_budget: 512
  max_snippet_chars: 512
  max_snippet_candidates: 3
```

- Retrieval/store inspection is local-first and read-only by default.
- Snippet extraction/injection is default-off and explicitly gated.
- Retrieval does not mutate MEM or SOUL.
- `token_budget`, `chars_per_token`, `snippet_budget`, and `max_snippet_chars` must be greater than zero; `max_snippet_candidates` may be zero.
- `chars_per_token=4` is a deterministic model-agnostic estimate, not tokenizer-exact.
- The older `default_store` / `stores` shape is not part of the current Pydantic model.
- O0 requires `memory.root_path` to be an absolute operator-owned root before the local worker is enabled.

## Client-message and instruction flags

```yaml
client_message_canonicalization_dry_run_enabled: false
client_history_exclusion_preflight_enabled: false
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
client_instruction_extraction_dry_run_enabled: false
client_instruction_cache_lookup_enabled: false
client_instruction_cache_root:
client_instruction_cache_max_entry_bytes: 65536
client_instruction_typed_parse_enabled: false
client_instruction_cache_write_enabled: false
client_instruction_cache_write_dry_run_only: true
```

- Canonicalization, extraction, and preflight are diagnostics/request-local planning boundaries.
- v0/v1 history apply is default-off and dry-run-only by default.
- Cache lookup is bounded and read-only.
- `client_instruction_cache_max_entry_bytes` accepts 1 through 1048576.
- Typed parse and cache-write wiring are default-off and require a trusted in-process runtime-private source.
- The runtime does not parse arbitrary backend visible text, trust frontend metadata as typed parse source, apply RelaySCN semantics, or provide parser-versioned lookup/write compatibility.

## RelayCTX flags

```yaml
relayctx_short_term_source_diagnostics_enabled: false
relayctx_short_term_extraction_dry_run_enabled: false
relayctx_short_term_block_assembly_dry_run_enabled: false
relayctx_short_term_runtime_injection_preflight_enabled: false
relayctx_short_term_runtime_injection_apply_enabled: false
relayctx_short_term_runtime_injection_dry_run_only: true
relayctx_short_term_runtime_injection_token_budget: 400
relayctx_unpack_enabled: false
relayctx_unpack_apply_enabled: false
relayctx_unpack_dry_run_only: true
relayctx_unpack_max_update_chars: 4096
relayctx_stream_unpack_dry_run_enabled: false
relayctx_stream_unpack_dry_run_only: true
relayctx_stream_unpack_max_buffer_chars: 256
relayctx_tts_adapter_handoff_runtime_enabled: false
relayctx_tts_adapter_handoff_runtime_dry_run_only: true
relayctx_tts_adapter_handoff_max_segment_chars: 120
relayctx_tts_adapter_handoff_min_segment_chars: 8
```

- Short-term CTX and non-stream Unpack remain default-off.
- Non-stream Unpack does not affect streaming responses.
- Default streaming remains byte-compatible backend SSE forwarding.
- `relayctx_stream_unpack_max_buffer_chars` accepts 32 through 4096.
- Phase 5.5 flags can construct suppression/segmentation/handoff metadata but do not deliver transport, execute TTS, generate audio, or control avatars.

## RelayMEM / RelaySLP Phase 6 flags

```yaml
relaymem_slp_runtime_enqueue_enabled: false
relaymem_slp_runtime_enqueue_dry_run_only: true
relaymem_slp_runtime_enqueue_apply_enabled: false
relaymem_slp_queue_root:
relaymem_slp_protected_source_root:
relaymem_slp_protected_source_max_artifact_bytes: 262144
relaymem_slp_source_registry_max_entries: 256
relaymem_slp_source_registry_ttl_seconds: 1800
```

These are the complete current top-level fields for the ordinary I1-B/C1-5 source-publication and B2 enqueue seam.

- Dry-run observation requires `relaymem_slp_runtime_enqueue_enabled=true`; no durable source or queue mutation occurs while `relaymem_slp_runtime_enqueue_dry_run_only=true`.
- Durable publication requires `relaymem_slp_runtime_enqueue_enabled=true`, `relaymem_slp_runtime_enqueue_dry_run_only=false`, and `relaymem_slp_runtime_enqueue_apply_enabled=true`.
- Apply also requires absolute existing `relaymem_slp_queue_root` and runtime-private `relaymem_slp_protected_source_root` directories.
- `relaymem_slp_protected_source_max_artifact_bytes` defaults to 262144 and accepts 1 through 1048576 bytes.
- `relaymem_slp_source_registry_max_entries` and `relaymem_slp_source_registry_ttl_seconds` default to 256 and 1800 and must be at least 1.
- The registry is only a capacity/TTL-bounded process-local hot cache. At capacity, a new entry is rejected rather than evicting an existing entry. Restart rehydration uses the durable C1-5 artifact.
- The B2 queue record remains content-free; the protected-source root contains runtime-private content-bearing artifacts.

B3 claim/lease helpers, C1-2 worker execution, and the C2 one-job adapter remain explicit caller-driven boundaries. They do not themselves gain separate top-level `RelayLMConfig` gates, do not scan the queue, and do not start a scheduler or daemon.

## I1-GB durable-finalization publication flags

```yaml
relaymem_slp_durable_finalization_enabled: false
relaymem_slp_durable_finalization_dry_run_only: true
relaymem_slp_durable_finalization_apply_enabled: false
relaymem_slp_durable_finalization_root:
relaymem_slp_durable_finalization_max_record_bytes: 524288
relaymem_slp_durable_finalization_max_segment_bytes: 65536
relaymem_slp_durable_finalization_max_segment_count: 256
relaymem_slp_durable_finalization_max_record_count: 1024
relaymem_slp_durable_finalization_publication_timeout_ms: 5000
```

I1-GB is default-off. Exactly these gate combinations are valid:

| Mode | enabled | dry_run_only | apply_enabled | Behavior |
|---|---:|---:|---:|---|
| disabled | false | true | false | no private record; current response order |
| dry-run | true | true | false | validate/prepare only; no file mutation or response blocking |
| apply | true | false | true | durable base/segment/seal admission before protected release |

All other combinations fail closed. Apply additionally requires ordinary runtime enqueue apply mode (`relaymem_slp_runtime_enqueue_enabled=true`, `relaymem_slp_runtime_enqueue_dry_run_only=false`, `relaymem_slp_runtime_enqueue_apply_enabled=true`) and an absolute, pre-existing, non-symlink runtime-private root. Relative or missing roots are rejected in apply mode. Boolean gates are strict booleans, and numeric bounds reject booleans.

Bounds and accepted ranges:

- total logical record bytes: 1 through 4194304, default 524288;
- one stream segment: 1 through 1048576 bytes, default 65536;
- segments per record: 1 through 4096, default 256;
- admitted record locators: 1 through 100000, default 1024;
- one bounded publication operation: 1 through 60000 milliseconds, default 5000.

The private record is content-bearing and separate from C1-5 and B2. I1-GB publishes restart evidence only. I1-GC one-record replay/completion and I1-GD retention/isolation cleanup are complete; I1-GE full crash validation remains unimplemented.

## I1-GD durable-finalization retention flags

```yaml
relaymem_slp_durable_finalization_retention_enabled: false
relaymem_slp_durable_finalization_retention_dry_run_only: true
relaymem_slp_durable_finalization_retention_apply_enabled: false
relaymem_slp_durable_finalization_completed_retention_seconds: 604800
relaymem_slp_durable_finalization_orphan_grace_seconds: 86400
relaymem_slp_durable_finalization_isolated_retention_seconds: 2592000
relaymem_slp_durable_finalization_cleanup_max_records_per_pass: 64
relaymem_slp_durable_finalization_cleanup_timeout_ms: 5000
```

I1-GD is separately default-off and dry-run-first. Valid operating modes are disabled (`false/true/false`), dry-run (`true/true/false`), and apply (`true/false/true`). Apply additionally requires the same absolute pre-existing private durable-finalization root. One call performs one bounded non-recursive maintenance pass; it does not poll, invoke I1-GC replay, or mutate C1-5, B2, B3, C2, worker, or M3 state.

Retention age uses stable filesystem `mtime` as a private operational clock. Completed retention defaults to 604800 seconds, orphan grace to 86400 seconds, isolated-marker retention to 2592000 seconds, records per pass to 64, and timeout to 5000 milliseconds. All are strict positive bounded integers. Sealed records without completion are retained regardless of age.

## O0 local one-job worker flags

```yaml
relaymem_local_worker_enabled: false
relaymem_local_worker_dry_run_only: true
relaymem_local_worker_apply_enabled: false
relaymem_local_worker_claim_owner: relaylm-worker-once
relaymem_local_worker_lease_duration_seconds: 300
relaymem_local_worker_discovery_max_entries: 256
```

O0 is default-off. Exactly these gate combinations are valid:

| Mode | enabled | dry_run_only | apply_enabled |
|---|---:|---:|---:|
| disabled | false | true | false |
| dry-run | true | true | false |
| apply | true | false | true |

Every other combination is invalid configuration. The `relaylm-worker` CLI cannot elevate config to apply. When enabled, `relaymem_slp_queue_root`, `relaymem_slp_protected_source_root`, and `memory.root_path` must be absolute. `relaymem_local_worker_claim_owner` must be a bounded token. Lease duration accepts 1 through 604800 seconds. Discovery accepts 1 through 4096 entries and defaults to 256.

O0 processes at most one eligible queued record per `--once` invocation. It delegates claim, lease, retry, rehydration, worker execution, terminal transition, and cleanup to existing B3/C1-5/C2/C1-2 boundaries. It does not poll or start a daemon.

## O1D1 local production scheduler flags

```yaml
relaymem_local_scheduler_enabled: false
relaymem_local_scheduler_dry_run_only: true
relaymem_local_scheduler_apply_enabled: false
relaymem_local_scheduler_replay_lane_enabled: true
relaymem_local_scheduler_queue_lane_enabled: true
```

All five fields are strict booleans. Integer values, strings, and null are rejected instead of being coerced. The exact accepted scheduler modes are:

| Mode | enabled | dry_run_only | apply_enabled |
|---|---:|---:|---:|
| disabled | false | true | false |
| dry-run | true | true | false |
| apply | true | false | true |

Every other mode triple is invalid configuration. An enabled scheduler must enable at least one lane. The default remains disabled and dry-run-first, while both lane selectors default to enabled so an operator can opt into the bounded round without introducing a hidden single-lane default.

The scheduler gate is an upper gate only. Scheduler apply does not elevate the I1-G replay/durable-finalization authority or the O0/C2/B3 local-worker authority. Roots, character scope, locators, jobs, dispatch records, and claims continue to resolve from existing server-owned configuration and lower authorities; O1D1 adds no interval, polling, fairness, backoff, jitter, worker-count, or shutdown-timeout field.

One call to `run_relaymem_slp_scheduler_round_once(...)` invokes the replay lane at most once, then the queue lane at most once, aggregates through O1A, validates the content-free projection, and returns without sleep. It is not an always-on scheduler, polling loop, daemon, or service-supervision boundary.

## RelayINT flags

```yaml
relayint_fast_path_dry_run_enabled: false
relayint_fast_path_high_confidence_threshold: 0.80
relayint_fast_path_low_confidence_threshold: 0.55
relayint_quick_clarification_preflight_enabled: false
relayint_quick_clarification_dry_run_only: true
relayint_quick_clarification_apply_enabled: false
relayint_quick_clarification_apply_dry_run_only: true
relayint_quick_clarification_response_max_chars: 120
```

Confidence thresholds accept 0.0 through 1.0. Quick-clarification apply remains plan/preflight-oriented and does not provide a complete user-visible short-circuit route.

## RelayEMO flags

```yaml
relayemo_enabled: false
relayemo_dry_run: true
relayemo_text_marker_enabled: false
relayemo_text_marker_apply_mode: diagnostics_only
relayemo_marker_open_threshold: 0.65
relayemo_marker_close_threshold: 0.45
relayemo_max_markers: 3
relayemo_scene_gate_enabled: true
relayemo_session_state_enabled: false
relayemo_session_state_ttl_seconds: 1800
relayemo_session_state_max_entries: 256
relayemo_affect_probe_mode: heuristic
relayemo_llm_affect_probe_enabled: false
relayemo_llm_affect_probe_dry_run: true
relayemo_llm_affect_probe_max_input_chars: 2000
relayemo_llm_affect_probe_timeout_ms: 1500
relayemo_llm_affect_probe_max_output_tokens: 160
relayemo_llm_affect_probe_skip_when_busy: true
relayemo_llm_affect_probe_every_n_turns: 1
```

`relayemo_text_marker_apply_mode` accepts `diagnostics_only`, `preview`, or `apply`. `relayemo_affect_probe_mode` accepts `heuristic` or `llm_structured_dry_run`. The LLM affect probe remains default-off, dry-run, budgeted, and fail-closed; it must not mutate durable affect, MEM, SOUL, TTS, or visible output.

## RelayRUN flags

```yaml
relayrun_checkpoint_write_enabled: false
relayrun_checkpoint_root: .relayrun/checkpoints
relayrun_checkpoint_dry_run_only: true
relayrun_resume_preflight_enabled: false
relayrun_resume_dry_run_only: true
relayrun_checkpoint_index_enabled: false
relayrun_checkpoint_index_dry_run_only: true
relayrun_checkpoint_index_max_files: 100
relayrun_recovery_transition_enabled: false
relayrun_recovery_transition_dry_run_only: true
relayrun_waiting_user_contract_enabled: false
relayrun_waiting_user_contract_dry_run_only: true
relayrun_recovery_apply_preflight_enabled: false
relayrun_recovery_apply_dry_run_only: true
relayrun_recovery_response_draft_enabled: false
relayrun_recovery_response_draft_dry_run_only: true
relayrun_visible_recovery_preflight_enabled: false
relayrun_visible_recovery_dry_run_only: true
relayrun_recovery_response_generator_enabled: false
relayrun_recovery_response_generator_dry_run_only: true
relayrun_output_relayscn_recovery_gate_enabled: false
relayrun_output_relayscn_recovery_gate_dry_run_only: true
relayrun_visible_recovery_apply_preflight_enabled: false
relayrun_visible_recovery_apply_preflight_dry_run_only: true
relayrun_user_action_dry_run_enabled: false
relayrun_user_action_dry_run_only: true
```

These are default-off diagnostics/preflight contracts unless a dedicated current contract says otherwise. They do not imply actual resume, retry, visible recovery output, or response mutation. `relayrun_checkpoint_index_max_files` must be at least 1.

## Config design rules

- Prefer explicit model routes over prompt inference.
- Keep persona file paths under `characters`, not `model_routes`.
- Keep cache and memory namespaces explicit.
- Do not require character files for pass-through routes.
- Require configured approved profile sources for current managed compilation.
- Never use incoming client instructions as fallback durable SOUL authority.
- Treat client system/developer messages as low-trust current instruction evidence.
- Keep current, compatibility, and target config examples labeled.
- Do not enable mutation, persistence, recovery, worker execution, or scheduling merely because a helper/schema exists.
