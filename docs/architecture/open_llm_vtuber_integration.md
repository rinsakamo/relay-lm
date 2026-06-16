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

## Required API surface

RelayLM exposes:

```text
POST /v1/chat/completions
GET  /v1/models
```

Streaming must be preserved for realtime speech latency.

Common request fields such as `model`, `stream`, `temperature`, tools, structured-output settings, and current multimodal parts are preserved or explicitly blocked by compatibility preflight.

## Request authority boundary

Open-LLM-VTuber may send:

- a client `system` persona prompt,
- previous user/assistant messages,
- frontend summaries,
- the current user turn,
- tool or multimodal transaction state.

For an explicit `pass_through` route, delegated client authority is preserved.

For a RelayLM-managed route:

```text
client messages
  -> extract validated current user turn
  -> extract bounded current system/developer evidence
  -> preserve minimum active transaction state
  -> exclude prior client history and raw instructions
  -> RelaySCN normalization
  -> RelayLM-owned context reconstruction
```

The original message array is request evidence, not the backend context.

## Persona prompt handling

Open-LLM-VTuber's `persona_prompt` or equivalent incoming system prompt is not automatically RelaySOUL.

```text
incoming persona prompt
  -> bounded low-trust client instruction evidence
  -> RelaySCN scene_role / scene_context / scene_constraints
  -> current request behavior

optional explicit import path
  -> RelaySOUL initialization candidate
  -> target-source classification
  -> review / approval
  -> versioned approved SOUL.md / OUTPUT_POLICY.md / RELATIONSHIP_ANCHOR.md
```

Rules:

- never copy the raw prompt wholesale into `SOUL.md`,
- never place it directly in the stable persona prefix on a managed route,
- do not use it as fallback durable persona authority,
- durable import is an explicit migration/calibration workflow,
- when approved RelaySOUL exists, it remains authoritative over conflicting client persona text.

When no approved RelaySOUL exists, RelaySCN may create a safe temporary current-scene role and constraints. This does not create a durable persona revision.

## History behavior

Managed routes do not retain a bounded window of frontend-supplied history as canonical context.

They use:

- validated current turn,
- RelayLM-owned selected recent context,
- approved RelayMEM evidence,
- approved RelaySOUL and durable policies,
- normalized RelaySCN state,
- minimum active transaction state.

Frontend visible history may remain in the frontend UI/storage, but it is not backend-authoritative context.

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

## Routing

Model-name routing selects approved RelayLM configuration.

```yaml
model_routes:
  relaylm-mili:
    character_id: mili
    backend: local_main
    cache_namespace: mili
    soul: ./characters/mili/SOUL.md
    output_policy: ./characters/mili/OUTPUT_POLICY.md
    relationship_anchor: ./characters/mili/RELATIONSHIP_ANCHOR.md
```

The route may point to approved persona sources. It must not infer durable identity from arbitrary system-prompt contents.

Per-character instances remain an optional performance/isolation mode.

## Compatibility modes

### `pass_through`

Connection testing or explicit delegated-authority integration. Messages remain unchanged except compatible model/header mapping.

### managed lightweight/full modes

RelayLM canonicalizes client evidence and reconstructs backend context according to the client history and instruction authority contracts.

Mode names and current runtime behavior are defined in [Runtime Architecture](runtime_architecture.md) and [Project Status](../PROJECT_STATUS.md).

## Streaming output boundary

The optional realtime path is:

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

Internal markers and malformed candidates must be blocked before external speech/avatar consumers receive them.

## Adapter boundary

RelayLM emits engine-neutral hints only.

- TTS adapter maps text chunks and style hints to the selected engine.
- Avatar adapter maps expression/motion hints to the selected Live2D/runtime configuration.
- RelayEMO does not call or control those engines directly.

## Non-goals

This integration does not:

- make the incoming persona prompt durable authority,
- preserve frontend history as managed backend context,
- require Open-LLM-VTuber code changes for the basic proxy path,
- take ownership of ASR/TTS/Live2D execution,
- rewrite tool or structured protocol payloads as persona text,
- enable heavy synchronous retrieval by default.

## References

- [Client History Authority Contract](client_history_authority_contract.md)
- [Client Instruction Authority Contract](client_instruction_authority_contract.md)
- [AI VTuber Pipeline Profile](ai_vtuber_pipeline_profile.md)
- [Pipeline Responsibility Design](pipeline_responsibility_design.md)
- [Project Status](../PROJECT_STATUS.md)
