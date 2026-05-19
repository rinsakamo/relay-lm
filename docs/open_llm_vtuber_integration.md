# Open-LLM-VTuber Integration Design

RelayLM should integrate with Open-LLM-VTuber as an OpenAI-compatible proxy.

The integration goal is simple:

> Existing Open-LLM-VTuber users should be able to point the OpenAI-compatible API URL at RelayLM and keep using their character configuration.

## Basic topology

```text
Open-LLM-VTuber
  -> RelayLM /v1/chat/completions
  -> LLM backend /v1/chat/completions
```

RelayLM should initially support any OpenAI-compatible backend. vLLM and SGLang are the preferred long-term runtime targets because their prefix/KV cache behavior aligns with RelayKV and KV-reuse-aware packing.

## Required API surface

RelayLM should first implement:

```text
POST /v1/chat/completions
GET  /v1/models
```

The chat completions endpoint must support streaming because Open-LLM-VTuber expects streamed chunks for low-latency speech.

RelayLM should preserve or forward:

- `model`
- `messages`
- `stream`
- `temperature`
- `tools` when present

Tool handling can initially be transparent pass-through. Later versions may support tool-aware packing.

## Open-LLM-VTuber request shape

Open-LLM-VTuber's OpenAI-compatible provider sends normal chat completion requests. RelayLM should expect requests like:

```json
{
  "model": "relaylm-mili",
  "messages": [
    {"role": "system", "content": "persona prompt..."},
    {"role": "user", "content": "past user message"},
    {"role": "assistant", "content": "past assistant message"},
    {"role": "user", "content": [{"type": "text", "text": "latest user input"}]}
  ],
  "stream": true,
  "temperature": 1.0,
  "tools": []
}
```

RelayLM should handle text-only first. Vision content can be passed through or treated as non-repackable content until explicit support is added.

## Minimal Open-LLM-VTuber config

Existing users should only need to change the OpenAI-compatible API settings.

```yaml
character_config:
  agent_config:
    agent_settings:
      basic_memory_agent:
        llm_provider: 'openai_compatible_llm'
    llm_configs:
      openai_compatible_llm:
        base_url: 'http://localhost:8090/v1'
        llm_api_key: 'relaylm'
        organization_id: null
        project_id: null
        model: 'relaylm-mili'
        temperature: 1.0
        interrupt_method: 'user'
```

## Routing

RelayLM should support routing by model name.

```yaml
model_routes:
  relaylm-mili:
    character_id: mili
    backend: vllm_main
    cache_namespace: mili
    soul: ./characters/mili/SOUL.md
    output_policy: ./characters/mili/OUTPUT_POLICY.md

  relaylm-zero:
    character_id: zero
    backend: vllm_main
    cache_namespace: zero
    soul: ./characters/zero/SOUL.md
    output_policy: ./characters/zero/OUTPUT_POLICY.md
```

This allows one RelayLM proxy to serve many characters.

For performance-sensitive setups, RelayLM should also support per-character instances:

```text
Mili -> http://localhost:8091/v1 -> backend A
Zero -> http://localhost:8092/v1 -> backend B
```

## Mapping Open-LLM-VTuber persona to SOUL

Open-LLM-VTuber already has `character_config.persona_prompt` in character YAML files. RelayLM should treat the incoming system prompt or configured persona file as the character SOUL.

Optional future mapping:

```text
Open-LLM-VTuber characters/mili.yaml persona_prompt
  <-> RelayLM characters/mili/SOUL.md
```

For the MVP, do not require users to create `SOUL.md` manually if the incoming persona prompt is sufficient.

## Memory and context behavior

Suggested initial behavior:

1. Preserve the persona/system prompt as the character soul anchor.
2. Detect character route from `model`.
3. Keep a bounded recent turn window.
4. Add optional lightweight viewer or character memory.
5. Pack the context with stable XML-like blocks.
6. Forward the packed request to the backend with streaming.

## Compatibility modes

RelayLM should provide modes for safe onboarding.

```yaml
mode: pass_through
```

For connection testing.

```yaml
mode: memory_light
```

For lightweight memory insertion.

```yaml
mode: memory_full
```

For full context repacking, retrieval, compression, and budget control.

## Implementation notes

- Do not require Open-LLM-VTuber code changes for the first integration.
- Do not require users to change ASR/TTS/Live2D settings.
- Preserve streaming behavior.
- Keep tool calls transparent in the first implementation.
- Avoid heavy synchronous retrieval in the default realtime profile.
- Use model-name routing before system-prompt inference.
- Treat per-character cache namespaces as a first-class concept.
