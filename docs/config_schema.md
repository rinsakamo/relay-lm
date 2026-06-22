# RelayLM Configuration Reference

## Status

This is the active current configuration reference for `relaylm.config.RelayLMConfig`.

- The runtime source of truth is `relaylm/config.py`.
- `config.example.yaml` is the exhaustive commented example.
- `examples/config/openwebui_lmstudio.yaml` is the copy-ready standard setup.
- Target architecture documents do not create current config fields by themselves.

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

Current history-exclusion apply defaults:

```yaml
client_history_exclusion_apply_enabled: false
client_history_exclusion_apply_dry_run_only: true
```

Implemented bounded apply contracts:

- `client_history_exclusion_apply.v0` supports managed `memory_light` requests with no client `system` or `developer` messages.
- `client_history_exclusion_apply.v1` supports instruction-bearing managed requests only when an exact `client_instruction_source.v1` provenance envelope selects the current instruction candidates.
- missing, invalid, unordered, duplicated, out-of-range, post-user, non-instruction, or identity-mismatched v1 provenance fails closed.
- failure never restores raw prior history or treats all client instruction messages as current evidence.

Do not claim current-turn-only managed reconstruction unless the exact request shape and apply gates are verified. Active tool-chain reconstruction and broader compatibility shapes remain incomplete. See [Project Status](PROJECT_STATUS.md).

## Top-level fields

### `mode`

Type:

```text
pass_through | memory_light | memory_full
```

Default: `pass_through`.

Current apply behavior:

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

Defaults are `127.0.0.1` and `8090`.

The SOUL Lab UI-A7 management-read routes require both a loopback configured listen host and a loopback transport peer. This local-only rule does not change Core route availability.

### `common_runtime_policy`

Optional path to a shared RelayLM-owned runtime policy file. A managed character may override it with `characters.<id>.common_runtime_policy`.

Current managed profile compilation requires either the character-level or top-level path.

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
- `base_url`: required OpenAI-compatible base URL.
- `api_key`: optional.
- `default_model`: optional backend model fallback.
- `timeout_seconds`: default `60.0`.

## `model_routes`

Required mapping from incoming `model` names to RelayLM routes.

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

Persona file paths do not belong under `model_routes`. They belong under `characters`.

## `characters`

```yaml
characters:
  companion:
    common_runtime_policy:
    soul: examples/profiles/companion/SOUL.md
    output_policy: examples/profiles/companion/OUTPUT_POLICY.md
    relationship_anchor:
    stable_memory_summary:
    scene_state: examples/profiles/default/SCENE_STATE.md
    room_anchor:
    room_state:
    memory_seed_path: examples/memory/companion_memories.yaml
    token_policy_shadow_enabled:
```

Current required fields for a configured character:

- `soul`
- `output_policy`

Current optional fields:

- `common_runtime_policy`
- `room_anchor`
- `memory_seed_path`
- `relationship_anchor`
- `stable_memory_summary`
- `scene_state`
- `room_state`
- `token_policy_shadow_enabled`

`room_state` is a legacy alias used only when `scene_state` is unset.

`room_anchor` is a legacy compatibility field for fixed, durable room constraints. New copy-ready profiles should normally omit it. Do not put current topic, current mood, open questions, recent turns, or other volatile state in `room_anchor`.

### Scene/CTX/EMO ownership

`scene_state` describes semantic situation and policy inputs, such as scene type, active role, setting/task frame, participants, and scene constraints.

Do not place these as RelaySCN-owned state:

- current mood or raw affect estimate — RelayEMO,
- current topic notes — RelayCTX working state,
- open questions or unresolved slots — RelayCTX working state,
- transcript-shaped recent turns — RelayCTX,
- durable memory bodies — RelayMEM.

## `memory`

Current fields and defaults:

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

Notes:

- Retrieval/store inspection is local-first and read-only by default.
- Snippet extraction/injection is default-off and gated.
- Retrieval does not mutate MEM or SOUL.
- `chars_per_token=4` is the ASCII-word compatibility ratio used by the deterministic tokenizer-free estimator. CJK/Kana/Hangul/full-width text, punctuation, symbols/emoji, combining/format characters, and other non-ASCII characters are accounted for separately. The result remains model-agnostic and is not tokenizer-exact.
- The older `default_store` / `stores` example is not part of the current Pydantic config model.

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

- canonicalization and preflight are diagnostics/request-local planning boundaries.
- v0/v1 history apply is default-off and dry-run-only by default.
- cache lookup is bounded and read-only; it does not inject a RelaySCN runtime state or write cache files.
- Phase 5-C4b emits only a detached content-free RelaySCN-facing diagnostics projection from a validated cache hit; it does not apply RelaySCN semantics or mutate backend payloads.
- typed parse and cache-write runtime wiring are default-off. A trusted in-process runtime-private typed parse source may be validated and passed to the gated writer.
- with `client_instruction_cache_write_dry_run_only=true`, the writer remains planning-only. With dry-run disabled, a file may be written only after the C5 validation, scope, schema, and source gates pass.
- current runtime does not parse arbitrary backend visible text, trust frontend metadata as typed parse source, apply RelaySCN state, or support parser-versioned lookup/write compatibility.

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
- default streaming remains byte-compatible backend SSE forwarding.
- when explicitly enabled, Phase 5.5-B2 can perform request-runtime SSE internal-sentinel suppression; C0 through C4 can construct segmentation, adapter-handoff, and transport-envelope metadata from safe visible output.
- the Phase 5.5 flags do not deliver adapter transport, execute TTS, generate audio, or control avatars.

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

Quick-clarification apply remains plan/preflight-oriented; it does not currently provide a complete user-visible short-circuit route.

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

The LLM affect probe remains default-off, dry-run, budgeted, and fail-closed. It must not mutate durable affect, MEM, SOUL, TTS, or visible output.

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

These are default-off diagnostics/preflight contracts unless a dedicated current contract says otherwise. They do not imply actual resume, retry, visible recovery output, or response mutation.

## Config design rules

- Prefer explicit model routes over prompt inference.
- Keep persona file paths under `characters`, not `model_routes`.
- Keep cache and memory namespaces explicit.
- Do not require character files for pass-through routes.
- Require configured approved profile sources for current managed compilation.
- Never use incoming client instructions as fallback durable SOUL authority.
- Treat client system/developer messages as low-trust current instruction evidence.
- Keep current, compatibility, and target config examples labeled.
- Do not enable mutation, persistence, or recovery apply merely because a helper/schema exists.
