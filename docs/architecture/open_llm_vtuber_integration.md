# Open-LLM-VTuber Integration Design

## Purpose

RelayLM integrates with Open-LLM-VTuber as an optional OpenAI-compatible frontend path.

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> OpenAI-compatible backend
```

RelayLM does not own Open-LLM-VTuber's UI, display history, ASR, TTS engine, or avatar runtime. On managed routes, RelayLM does own the backend-bound context authority and the visible/internal output safety boundary.

The primary local MVP path remains OpenWebUI -> RelayLM -> LM Studio. Open-LLM-VTuber is an optional realtime profile.

## Current implementation boundary

Current behavior:

- streaming is primarily backend SSE forwarding,
- current `memory_light` compatibility compilation may retain prior frontend user/assistant history,
- the implemented `client_history_exclusion_apply.v0` is default-off and supports no client system/developer messages only,
- Stream Unpack, output segmentation, RelayREF, and complete Output-side RelaySCN are not implemented,
- incoming persona/system text is not durable RelaySOUL authority.

The target current-turn-only managed reconstruction path described below is broader than current implementation. See [Open-LLM-VTuber Current / Target Boundary](open_llm_vtuber_current_target.md) and [Project Status](../PROJECT_STATUS.md).

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
  -> extract bounded current system/developer evidence
  -> preserve minimum active transaction state
  -> exclude prior client history and raw instructions
  -> RelaySCN normalization
  -> RelayLM-owned context reconstruction
```

The complete target flow is not yet current runtime behavior. Current default `memory_light` compatibility compilation may still retain prior client history.

## Persona prompt handling

Open-LLM-VTuber's `persona_prompt` or equivalent incoming system prompt is not automatically RelaySOUL.

```text
incoming persona prompt
  -> bounded low-trust client instruction evidence
  -> current compatibility block or future RelaySCN normalization
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
- never place it above RelayLM-owned durable policy on a managed route,
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

Current limitation:

```text
current default memory_light compatibility path
  -> prior frontend user/assistant history may remain backend-bound

client_history_exclusion_apply.v0
  -> default-off
  -> dry-run-only by default
  -> no client system/developer messages only
```

Frontend visible history may remain in the frontend UI/storage. Do not claim it has been excluded from backend context unless the exact current apply gates and request shape have been verified.

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

Current profile compilation is apply-capable. History-exclusion actual apply is a separate default-off boundary and currently supports only no-instruction requests.

### Target managed lightweight/full modes

RelayLM canonicalizes client evidence and reconstructs backend context according to the client history and instruction authority contracts.

Mode names and current runtime behavior are defined in [Runtime Architecture](runtime_architecture.md) and [Project Status](../PROJECT_STATUS.md).

## Streaming output boundary

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

This path is not yet implemented. Current streaming is primarily backend SSE forwarding.

Internal markers and malformed candidates must be blocked before external speech/avatar consumers receive them when Stream Unpack is introduced.

## Adapter boundary

RelayLM emits engine-neutral hints only.

- TTS adapter maps text chunks and style hints to the selected engine.
- Avatar adapter maps expression/motion hints to the selected Live2D/runtime configuration.
- RelayEMO does not call or control those engines directly.

## Non-goals

This integration does not:

- make the incoming persona prompt durable authority,
- claim current prior-history exclusion when the apply gate is disabled,
- require Open-LLM-VTuber code changes for the basic proxy path,
- take ownership of ASR/TTS/Live2D execution,
- rewrite tool or structured protocol payloads as persona text,
- enable heavy synchronous retrieval by default,
- implement `/v1/responses`.

## References

- [Client History Authority Contract](client_history_authority_contract.md)
- [Client Instruction Authority Contract](client_instruction_authority_contract.md)
- [Open-LLM-VTuber Current / Target Boundary](open_llm_vtuber_current_target.md)
- [AI VTuber Pipeline Profile](ai_vtuber_pipeline_profile.md)
- [Pipeline Responsibility Design](pipeline_responsibility_design.md)
- [Project Status](../PROJECT_STATUS.md)
