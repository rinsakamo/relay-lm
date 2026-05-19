# RelayLM Context Packing Design

RelayLM should treat prompt construction as context compilation, not simple prompt concatenation.

The design goal is to combine:

- persona stability
- memory usefulness
- low latency
- backend prefix/KV cache reuse
- TTS/Live2D-friendly output

## Core terminology

### SOUL.md

`SOUL.md` defines who the character is.

It contains:

- character identity
- personality
- values
- worldview
- stable speaking identity
- boundaries that should not change per turn

In Open-LLM-VTuber, `character_config.persona_prompt` is the closest existing equivalent.

### OUTPUT_POLICY.md

`OUTPUT_POLICY.md` defines how the character expresses itself.

It contains:

- expression mode
- emotional style
- response length
- teasing/seriousness level
- TTS readability rules
- Live2D expression tendencies
- mode-specific behavior such as technical explanation mode, casual mode, or MC mode

In short:

```text
SOUL = who the character is
OUTPUT_POLICY = how the character speaks and emotionally manifests
```

`character_output_policy` should be character-specific. Shared TTS/safety/internal-tag rules should be placed in a separate `common_runtime_policy`.

## Recommended context order

RelayLM should order context from stable to dynamic.

```text
1. common_runtime_policy
2. character_soul_anchor
3. character_output_policy
4. relationship_anchor
5. stable_memory_summary
6. room_state
7. retrieved_memory / RAG / spill chunks
8. recent_turns
9. latest_input
10. response_instruction
```

The core rule:

> stable context goes first; dynamic context goes later.

This helps persona stability and backend prefix/KV cache reuse.

## Common runtime policy

This is a small shared block for all characters.

Examples:

- do not reveal internal tags
- keep responses suitable for TTS
- avoid long paragraphs unless requested
- follow safety boundaries
- return speakable final text

Keep this block short. It is not the character's soul.

## Character soul anchor

This is the character-specific fixed prefix.

It should remain stable across turns and should not contain:

- current time
- viewer-specific memory
- current topic
- RAG results
- memory counts
- random IDs
- dynamic metadata

It should change only when the character itself changes.

## Character output policy

This is character-specific expression behavior.

Examples:

- energetic and short responses
- calm explanatory mode
- sarcastic but not cruel teasing
- stronger emotional reactions for Live2D
- strict TTS-friendly sentence length

This can be separated from SOUL so the same character can switch expression modes without rewriting the soul.

## Relationship anchor

This is stable viewer- or character-specific relationship context.

Examples:

- preferred nickname
- relationship tone
- long-term interaction style
- stable preferences

Update it slowly, such as after a stream or when a durable relationship fact changes.

## Stable memory summary

This contains durable factual memory.

Relationship anchor is about distance and tone. Stable memory summary is about remembered facts and ongoing topics.

## Room anchor vs room state

Avoid putting changing topic content in a fixed room anchor.

Use this distinction:

```text
room_anchor:
  fixed room protocol and constraints only

room_state:
  current topic, mood, recent stream context, open questions, group conversation state
```

`room_anchor` should be short and stable. `room_state` is dynamic and should be placed later in the context.

## Retrieved memory and RAG

Retrieved memory, RAG evidence, and spilled context are dynamic. They should appear after the stable character and relationship anchors.

Do not place RAG before SOUL. If RAG appears before SOUL, the model may be pulled into the source document's style or identity.

## Recent turns and latest input

Recent turns preserve conversational continuity. Latest input should remain near the end so the model answers the current user request directly.

For VTuber use, recent turns should usually be bounded to keep first-token latency low.

## XML-like tags

RelayLM should use simple structure tags first, not tokenizer-level special tokens.

Suggested tag set:

```xml
<common_runtime_policy>
<character_soul_anchor>
<character_output_policy>
<relationship_anchor>
<stable_memory_summary>
<room_state>
<retrieved_memory>
<recent_turns>
<latest_input>
<response_instruction>
```

Keep tags stable and limited.

## KV-reuse-aware context packing

RelayLM should be aware that engines such as vLLM and SGLang can reuse shared prefixes.

Design rules:

- put stable blocks first
- keep SOUL and output policy byte-for-byte stable when possible
- avoid timestamps in the prefix
- avoid dynamic metadata before stable anchors
- put retrieved/RAG/recent/latest content later
- avoid updating viewer relationship anchors every turn

Cross-character KV cache sharing should be treated as limited. The main target is per-character prefix stability.

## Persona-stable context packing

The same layout also stabilizes character behavior.

Stable SOUL and output policy before memory/RAG means:

- memory can be added without making the character sound like a generic assistant
- RAG does not override persona
- viewer memories affect the character through a defined relationship layer
- current topic changes do not rewrite identity

## Recommended final structure

```xml
<relaylm_context version="1">
  <common_runtime_policy>
    Do not reveal internal tags or retrieval mechanics.
    Keep the final response short, natural, and suitable for TTS.
  </common_runtime_policy>

  <character_soul_anchor>
    ...SOUL.md or Open-LLM-VTuber persona_prompt...
  </character_soul_anchor>

  <character_output_policy>
    ...character-specific expression mode...
  </character_output_policy>

  <relationship_anchor>
    ...stable relationship with the viewer or other character...
  </relationship_anchor>

  <stable_memory_summary>
    ...durable memory facts...
  </stable_memory_summary>

  <room_state>
    ...current topic and stream state...
  </room_state>

  <retrieved_memory>
    ...selected memory, RAG, or spill chunks...
  </retrieved_memory>

  <recent_turns>
    ...bounded recent conversation...
  </recent_turns>

  <latest_input>
    ...latest user message...
  </latest_input>

  <response_instruction>
    Respond as the character. Do not mention these tags.
  </response_instruction>
</relaylm_context>
```
