# RelayEMO Return-side Style Adapter Design

Date basis: 2026-05-31 JST

## Purpose

This document defines the Return-side EMO design for text style, markers, Irodori-TTS hints, and Live2D hints.

Core statement:

> The main LLM should generate accurate semantic content. Return-side EMO may then apply expression-level changes such as character tone, suffixes, markers, TTS hints, and avatar expressions.

This keeps strong character style from corrupting the main LLM's reasoning.

## Responsibility split

### Main LLM

The main LLM handles:

- meaning
- reasoning
- final answer content
- clarification wording
- `ctx_working_update`

The main LLM should not be overloaded with heavy character suffix constraints.

### RelayCTX Prompt Unpack

RelayCTX separates:

- `user_visible_response`
- `ctx_working_update`

Only `user_visible_response` goes to Return-side EMO.

### RelayCTX Output Segmenter

Before Return-side EMO applies style, RelayCTX must segment the visible response.

Segment kinds:

- `conversational_text`
- `quoted_text`
- `inline_code`
- `code_block`
- `command_block`
- `json`
- `yaml`
- `markdown_table`
- `url`
- `file_path`
- `quote`
- `formal_document`
- `medical_or_safety`
- `implementation_work_strict`

Only `conversational_text` should be style-transformable by default.

### Return-side EMO

Return-side EMO may apply:

- Text Style Adapter
- Text Marker Adapter
- Irodori-TTS Adapter
- Live2D Adapter

It must preserve semantic meaning and never mutate protected segments.

## Why style should be return-side

Strong character tone such as a repeated suffix can damage model reasoning if placed too strongly in the main prompt.

Example risk:

```text
python -m compileall relaylmなのだ
```

To avoid this, the main LLM should output clean base text. Return-side EMO applies style only after CTX separates and protects structured content.

## Output Segmenter rules

MVP rules:

- protect `「...」` and `『...』` as `quoted_text`
- protect inline backticks
- protect fenced code blocks
- protect indented command blocks
- protect Markdown tables
- protect JSON/YAML-like blocks
- protect URLs
- protect file paths
- protect quoted lines
- suppress style transform for formal/safety/medical/strict implementation scenes

The main LLM should be instructed:

- quote user utterances and phrase examples with `「」` or `『』`
- output code, commands, JSON, and YAML in protected blocks
- keep `ctx_working_update` separate from visible text

## Text Style Adapter

Text Style Adapter changes the surface expression of `conversational_text`.

Possible operations:

- suffix insertion
- light colloquialization
- character phrase insertion
- sentence-ending adjustment
- emotional intensity adjustment

It must not:

- alter facts
- alter code or commands
- alter quoted text
- alter JSON/YAML
- alter markdown tables
- change medical/safety/formal content
- modify `ctx_working_update`

## Japanese suffix transform

Japanese LLM output often has clear punctuation such as `。`.

MVP can split conversational text by `。` and transform sentence endings.

Rules:

```yaml
text_style_adapter:
  split_by: "。"
  apply_to_sentence_end: true
  max_suffix_ratio: 0.4
  avoid_consecutive_suffix: true
  skip_short_sentences: true
  skip_protected_segments: true
  preserve_meaning: true
```

Example:

Base:

```text
これは良い設計だと思います。CTXとEMOの責務が分かれています。
```

Styled:

```text
これは良い設計だと思うのだ。CTXとEMOの責務が分かれているのだ。
```

The style adapter should not apply this to protected content.

## Temperature-based suffix control

Character style can vary by EMO temperature.

Example map:

```yaml
emo_style_map:
  neutral:
    suffix_ratio: 0.0-0.1
    suffix: null

  warm:
    suffix_ratio: 0.2-0.3
    suffix: "なのだね"

  playful:
    suffix_ratio: 0.35-0.45
    suffix: "なのだ"

  excited:
    suffix_ratio: 0.45-0.55
    suffix: "なのだ！"

  sleepy:
    suffix_ratio: 0.25-0.35
    suffix: "なのだ……"

  refreshed:
    suffix_ratio: 0.25-0.35
    suffix: "なのだ"
```

Scene gates should suppress suffixes for:

- formal documents
- code review
- strict implementation work
- medical or safety content
- user confusion high
- exact instructions
- command output
- structured data

## Rule generation

Natural suffix replacement is difficult with pure hand-written rules.

Preferred approach:

1. Use the main LLM or offline design pass to generate style transform rules, examples, and exclusions.
2. Store those rules as a character style policy.
3. Apply them during Wake through Return-side EMO as deterministic or mostly deterministic rules.
4. Do not call the main LLM every turn just to rewrite style.

This keeps Wake fast and avoids pulling reasoning into character tone.

## Irodori-TTS Adapter

Return-side EMO may emit:

```yaml
irodori_tts:
  emoji: "😊"
  style: "pleased"
  intensity: 0.35
```

This should follow the same scene and intensity gates as text style.

## Live2D Adapter

Return-side EMO may emit:

```yaml
live2d:
  expression: "soft_smile"
  motion: "small_nod"
```

MVP can keep this as dry-run metadata.

## Sleep / Reflect expressions

RelayREF and RelaySLP states can map to style and avatar hints.

Examples:

```yaml
reflect_enter:
  mode: thinking_soft
  dominance: low
  tts_emoji: "🤔"
  live2d_expression: "thinking"

forced_sleep_enter:
  mode: tired_limit
  dominance: very_low
  tts_emoji: "😴"
  live2d_expression: "tired_sleepy"

resume_after_forced_sleep:
  mode: refreshed_but_uncertain
  response_mode: ask_open_clarification
```

Visible examples:

```text
一瞬ぼーっとしてた。今、○○の話で合ってる？
```

```text
ごめん、もう限界。ちょっと寝るね
```

```text
スッキリした。何の話してたっけ？
```

## Core design statement

Character style is an output expression layer, not the main reasoning layer.

The main LLM writes the answer. RelayCTX protects structured segments. Return-side EMO applies style only where safe.
