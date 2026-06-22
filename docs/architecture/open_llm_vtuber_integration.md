# Open-LLM-VTuber Integration Design

## Purpose

RelayLM integrates with Open-LLM-VTuber as an optional OpenAI-compatible frontend path.

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

RelayLM does not own Open-LLM-VTuber's UI, display history, ASR, TTS engine, or avatar runtime. On managed routes, RelayLM owns the backend-bound context authority and the bounded visible/internal output-safety boundary.

The primary local MVP path remains OpenWebUI -> RelayLM -> LM Studio. Open-LLM-VTuber is an optional realtime profile.

## Current implementation boundary

Current behavior:

- default streaming remains compatible backend SSE forwarding,
- Phase 5.5-B2 can perform gated request-runtime internal-sentinel suppression,
- Phase 5.5-C0 through C4 can construct TTS-safe segmentation, adapter-handoff, and transport-envelope metadata from B2 safe visible output,
- default `memory_light` compatibility may retain prior frontend user/assistant history,
- `client_history_exclusion_apply.v0` supports bounded no-instruction managed requests,
- `client_history_exclusion_apply.v1` supports bounded instruction-bearing managed requests only with exact `client_instruction_source.v1` provenance,
- both apply paths remain default-off and dry-run-only by default,
- complete RelayREF and Output-side RelaySCN execution are not implemented,
- incoming persona/system text is not durable RelaySOUL authority,
- RelayLM Core does not deliver adapter transport or execute TTS/audio/avatar behavior.

The broader target current-turn-only path described below includes more compatibility shapes, active transaction preservation, typed RelaySCN semantic apply, and ordinary default-on managed reconstruction. See [Open-LLM-VTuber Current / Target Boundary](open_llm_vtuber_current_target.md) and [Project Status](../PROJECT_STATUS.md).

## Required API surface

RelayLM exposes:

```text
POST /v1/chat/completions
GET  /v1/models
```

Streaming must be preserved for realtime speech latency.

Common request fields such as `model`, `stream`, `temperature`, tools, structured-output settings, and current multimodal parts are preserved or explicitly blocked by compatibility preflight.

`/v1/responses` is not currently implemented.

## Request authority boundary

Open-LLM-VTuber may send:

- a client `system` persona prompt,
- previous user/assistant messages,
- frontend summaries,
- the current user turn,
- tool or multimodal transaction state.

For an explicit `pass_through` route, delegated client authority is preserved.

For a RelayLM-managed route, the target authority flow is:

```text
client messages
  -> extract validated current user turn
  -> select bounded current system/developer evidence through explicit provenance
  -> preserve minimum active transaction state
  -> exclude prior client history and raw instructions
  -> RelaySCN normalization
  -> RelayLM-owned context reconstruction
```

Current v0/v1 apply implements a bounded subset. It does not yet preserve active tool transactions or make semantic RelaySCN normalization the ordinary apply path.

## Persona prompt handling

Open-LLM-VTuber's `persona_prompt` or equivalent incoming system prompt is not automatically RelaySOUL.

```text
incoming persona prompt
  -> request-local instruction identity
  -> explicit provenance selection when v1 apply is requested
  -> bounded low-trust instruction evidence
  -> current request behavior

optional explicit import path
  -> RelaySOUL initialization candidate
  -> target-source classification
  -> review / approval
  -> versioned approved SOUL.md / OUTPUT_POLICY.md / RELATIONSHIP_ANCHOR.md
```

Rules:

- never copy the raw prompt wholesale into `SOUL.md`,
- never treat it as fallback durable persona authority,
- never infer v1 provenance from role, wording, or position,
- never place instruction evidence above RelayLM-owned durable policy on a managed route,
- durable import is an explicit migration/calibration workflow,
- when approved RelaySOUL exists, it remains authoritative over conflicting client persona text.

Current managed profile compilation requires configured `soul` and `output_policy` files. A missing configured profile is an error, not permission to promote the client prompt into SOUL.

## History behavior

Target managed routes use:

- validated current turn,
- RelayLM-owned selected recent context,
- approved RelayMEM evidence,
- approved RelaySOUL and durable policies,
- normalized RelaySCN state,
- minimum active transaction state.

Current bounded behavior:

```text
default memory_light compatibility
  -> prior frontend user/assistant history may remain backend-bound

client_history_exclusion_apply.v0
  -> default-off and dry-run-only by default
  -> bounded no-instruction requests

client_history_exclusion_apply.v1
  -> default-off and dry-run-only by default
  -> bounded instruction-bearing requests
  -> exact client_instruction_source.v1 provenance required

missing or invalid v1 provenance
  -> fail closed
  -> no raw-history fallback
```

Frontend visible history may remain in the frontend UI/storage. Do not claim it has been excluded from backend context unless the exact apply gates, request shape, and provenance have been verified.

## Minimal frontend configuration

Existing users should normally change only the OpenAI-compatible provider endpoint and route model.

```yaml
character_config:
  agent_config:
    agent_settings:
      basic_memory_agent:
        llm_provider: openai_compatible_llm
    llm_configs:
      openai_compatible_llm:
        base_url: http://localhost:8090/v1
        llm_api_key: relaylm
        model: relaylm-mili
        temperature: 1.0
        interrupt_method: user
```

The exact Open-LLM-VTuber configuration structure is frontend-version-dependent. RelayLM requires an OpenAI-compatible Chat Completions connection to `/v1/chat/completions` and a route model ID published by `/v1/models`.

A frontend that cannot emit the reserved v1 provenance envelope should leave instruction-bearing actual apply disabled or dry-run-only. The basic proxy path does not require v1 actual apply.

## RelayLM routing

Persona paths belong under `characters`, not `model_routes`.

```yaml
backends:
  local_main:
    type: openai_compatible
    base_url: http://127.0.0.1:1234/v1
    api_key: relaylm
    default_model: local-model

model_routes:
  relaylm-mili:
    backend: local_main
    backend_model: local-model
    character_id: mili
    mode: memory_light
    cache_namespace: character/mili
    memory_namespace: character/mili

characters:
  mili:
    soul: ./characters/mili/SOUL.md
    output_policy: ./characters/mili/OUTPUT_POLICY.md
    relationship_anchor: ./characters/mili/RELATIONSHIP_ANCHOR.md
    scene_state: ./scenes/default/SCENE_STATE.md
```

The route selects approved character configuration. It must not infer durable identity from arbitrary system-prompt contents.

Per-character instances remain an optional performance/isolation mode.

## Compatibility modes

### `pass_through`

Connection testing or explicit delegated-authority integration. Compatible messages remain client-owned except for route/model/header mapping.

### Current `memory_light`

Current profile compilation is apply-capable. History-exclusion actual apply is a separate default-off boundary:

- v0 handles bounded no-instruction requests,
- v1 handles bounded explicit-provenance instruction-bearing requests,
- active tool transactions and unsupported compatibility shapes fail closed.

### Target managed lightweight/full modes

RelayLM canonicalizes client evidence and reconstructs backend context according to the client history and instruction authority contracts as ordinary managed behavior.

Mode names and current runtime behavior are defined in [Runtime Architecture](runtime_architecture.md) and [Project Status](../PROJECT_STATUS.md).

## Streaming output boundary

Current default path:

```text
backend stream
  -> compatible SSE forwarding
```

Current optional Phase 5.5 path:

```text
backend stream
  -> B2 internal-sentinel suppression when explicitly enabled
  -> C0 TTS-safe segmentation metadata
  -> C1/C2 adapter-handoff planning and runtime observation
  -> C3/C4 adapter-facing transport-envelope metadata
  -> unchanged safe visible SSE output
```

The target realtime path is:

```text
backend stream
  -> RelayCTX Stream Unpack
  -> Output Segmenter
  -> RelayREF
  -> Return-side RelayEMO hints
  -> Output-side RelaySCN current-response gate / next-turn observation
  -> RelayRUN approved output
  -> external TTS / Avatar adapters / captions
```

Current Phase 5.5 does not provide complete RelayREF/Output-side RelaySCN processing, adapter delivery, TTS/audio execution, avatar control, or generalized partial-stream resume.

Internal markers and malformed candidates must remain blocked before external speech/avatar consumers receive them.

## Adapter boundary

RelayLM Core emits engine-neutral hints and runtime-private metadata only.

- TTS adapter maps text chunks and style hints to the selected engine.
- Avatar adapter maps expression/motion hints to the selected Live2D/runtime configuration.
- RelayEMO does not call or control those engines directly.
- Phase 5.5 transport envelopes are not proof of transport delivery.
- SOUL Lab Runtime owns later audio queueing, TTS invocation, timing, lip-sync, and avatar execution.

## Non-goals

This integration does not:

- make the incoming persona prompt durable authority,
- claim current prior-history exclusion when the apply gate is disabled,
- infer instruction provenance from message role or wording,
- require Open-LLM-VTuber code changes for the basic proxy path,
- take ownership of ASR/TTS/Live2D execution,
- rewrite tool or structured protocol payloads as persona text,
- enable heavy synchronous retrieval by default,
- implement `/v1/responses`.

## References

- [Client History Authority Contract](client_history_authority_contract.md)
- [Client Instruction Authority Contract](client_instruction_authority_contract.md)
- [Open-LLM-VTuber Current / Target Boundary](open_llm_vtuber_current_target.md)
- [Phase 5.5 Stream Unpack Bounded Slice](phase5_5_stream_unpack_bounded_slice.md)
- [AI VTuber Pipeline Profile](ai_vtuber_pipeline_profile.md)
- [Pipeline Responsibility Design](pipeline_responsibility_design.md)
- [Project Status](../PROJECT_STATUS.md)
