# RelayLM Profiles, API, and Starters

This Starter knowledge is a bounded projection of shipped documentation. It describes only the current documented surfaces named below.

## Cognitive Profile and the OpenAI-compatible model field

Source: `docs/contracts/openai-api.md`

For RelayLM's OpenAI-compatible Chat Completions boundary, the public `model` field selects a configured Cognitive Profile. It does not directly name or override the physical inference model.

A Cognitive Profile resolves to a Cognitive Package root and effective physical provider/model configuration. Multiple Profiles may share the same physical provider/model while keeping separate package roots and therefore separate State, Event, and MEMORY persistence authority.

`GET /v1/models` projects configured public Cognitive Profile IDs, not physical provider model IDs.

The supported top-level Chat Completions request fields are exactly `model`, `messages`, and `stream`. Unsupported extra controls are rejected rather than silently treated as no-ops.

## Client history is not package authority

Source: `docs/contracts/openai-api.md`

RelayLM selects the last non-empty user message as the current governed input. Earlier client-supplied system, assistant, and user messages are not automatically replayed into Cognitive Context or appended to the Event Journal. Governed continuity comes from the selected Cognitive Package and RelayLM-owned context.

## Starter Cognitive Packages

Source: `docs/reference/starter-packages.md`

First-party Starter Packages are installed resources that users can inspect, materialize into ordinary filesystem directories, edit, and bind as Cognitive Package roots. Materialization must not overwrite an existing destination and unknown Starter names fail closed.

Starter semantic content does not contain provider endpoints, physical model IDs, secrets, server bind policy, host-specific paths, tokenizer settings, or calibration settings. Those remain runtime/operator configuration.

The catalog demonstrates that Character is one Cognitive Package specialization rather than the only role. `Blank` is the neutral authoring vessel, `ReLM` is the complete approachable Character example, `fact-summarizer` is a minimal non-personal machine example, and `RelayLM-FAQ` is the bounded onboarding/reference machine carrying this KNOWLEDGE.

## RelayLM-FAQ authority boundary

Sources: `docs/reference/knowledge.md`, `docs/reference/starter-packages.md`

RelayLM-FAQ may explain only what its supplied KNOWLEDGE supports. It must not use model prior knowledge as RelayLM release authority and must not invent missing release behavior. If a question depends on details outside these bounded assets, the supported response is to say the supplied knowledge does not establish the answer and point the user to current shipped documentation or operator authority.
