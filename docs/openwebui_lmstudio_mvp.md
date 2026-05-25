# OpenWebUI + LM Studio MVP

## MVP topology

RelayLM standard MVP UI/backend topology is:

```text
OpenWebUI
  -> RelayLM /v1/chat/completions
  -> LM Studio /v1/chat/completions
```

## Positioning

- OpenWebUI is the standard MVP frontend.
- LM Studio is the standard MVP local OpenAI-compatible backend.
- RelayLM is the OpenAI-compatible persona/memory context proxy between them.
- Open-LLM-VTuber remains an optional frontend and example integration path.

## OpenWebUI usage policy

OpenWebUI model preset / avatar should be used as a character-card-like or use-case-card UI layer.

Recommended route-like model IDs (abstract names, no concrete character names):

- `relaylm-companion`
- `relaylm-work-assistant`
- `relaylm-code-reviewer`

OpenWebUI model selector/model preset should map these model IDs to RelayLM routes.

## RelayLM responsibilities

RelayLM owns context and routing control:

- route resolution
- `character_id` or persona profile id resolution
- `SOUL` / `OUTPUT_POLICY` persona anchors
- `memory_light` context insertion
- recent turns shaping
- token budget safety

## OpenWebUI responsibilities

OpenWebUI owns lightweight presentation and interaction scaffolding:

- model card / avatar / display name
- prompt suggestions and launch UX
- model selector and preset switching

To avoid duplication/conflict, heavy system prompt steering should stay thin in OpenWebUI and not duplicate RelayLM persona policy blocks.

## LM Studio responsibilities

LM Studio owns backend inference runtime:

- local OpenAI-compatible backend endpoint
- actual model inference execution

## Open-LLM-VTuber position

Open-LLM-VTuber is supported as an optional frontend / example integration.

It is not the default MVP standard UI in this positioning update.
