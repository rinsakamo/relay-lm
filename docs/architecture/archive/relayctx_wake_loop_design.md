# RelayCTX Wake Loop Design

Date basis: 2026-05-31 JST

## Purpose

This document defines the Wake-side responsibility split for RelayLM, RelayCTX, RelayEMO, RelayMEM, RelayREF, and the main LLM backend.

Core statement:

> The main LLM thinks and speaks. RelayCTX keeps CPU-side working memory, resolves active references, and repacks only the minimum context needed for the next turn.

RelayLM remains the OpenAI-compatible proxy and routing layer. RelayCTX is the Wake-time working-memory and prompt-repack layer.

## Responsibility split

### RelayLM

RelayLM should stay focused on:

- OpenAI-compatible proxy behavior
- route and backend selection
- request/response I/O
- streaming and adapter boundaries
- backend connection to LM Studio / local OpenAI-compatible servers
- passing structured runtime artifacts between RelayCTX, RelayEMO, RelayMEM, RelayREF, and the backend model

RelayLM should not become the semantic working-memory engine itself.

### RelayCTX

RelayCTX owns Wake-time context state.

RelayCTX has two separate responsibilities:

1. CPU-side internal working memory
   - kept in RAM
   - not sent directly to the model every turn
   - used for reference resolution, response-mode selection, token budget checks, active topic/task tracking, and short-term continuity

2. prompt reinput repack
   - the small selected context actually sent to the LLM backend
   - built from stable prefix, SOUL/output policy, selected CTX hints, EMO hints, optional MEM/tool results, and latest user input
   - arranged to preserve backend prefix/KV cache reuse where possible

Important boundary:

> `ctx_working_update` is internal working memory.  
> `ctx_prompt_hints` is the minimal reinput context for the next model call.

RelayCTX must not blindly feed `ctx_working_update` back into the model. It should commit, validate, compress, select, and repack.

### RelayEMO

RelayEMO has two Wake-side roles.

#### Input-side EMO

Input-side EMO is passed into the main LLM before generation.

It provides short-term expression signals such as:

- `user_affect_estimate`
- `scene_state`
- `assistant_emotion_state_target`
- warmth / arousal / dominance hints
- formality and expression allowance

These signals affect tone, warmth, uncertainty, and scene-appropriate expression. They do not decide long-term memory or SOUL updates.

#### Return-side EMO

Return-side EMO runs after CTX unpacks the model output.

It may produce:

- text style adjustment
- text marker adjustment
- Irodori-TTS emoji/style hints
- Live2D expression hints
- intensity-gated expression metadata

Return-side EMO must not mutate the semantic meaning of the answer or contaminate `ctx_working_update`.

### RelayMEM

RelayMEM is not used to guess ambiguous pronouns by default.

Wake-time MEM use should be restricted to:

- explicit prior-memory requests
- confirmed references
- post-clarification recall
- tool/MEM recall after `pause_and_recall`

Ambiguous references should first be resolved through active CTX or user clarification.

### RelayREF

RelayREF handles Wake-time reflection, resynchronization, and recovery.

RelayREF reads existing Wake logs and may produce `ctx_handoff_guess` or resume-confirmation prompts. It does not require additional Wake-time LLM output.

### RelaySLP

RelaySLP is the Sleep/reset/deep-consolidation sub-layer called by RelayREF.

RelaySLP is used for:

- forced sleep
- offline sleep
- deep post-session consolidation

Routine Wake-time confusion should use RelayREF modes, not RelaySLP.

### Main LLM backend

The main backend, such as Qwen3.5-9B Q4, is responsible for:

- thinking
- natural response generation
- clarification phrasing
- “ちょっと思い出すね” style recall-pause wording
- producing `ctx_working_update`

It should receive SOUL, EMO, CTX, and optional MEM/tool results as structured hints, then output both the user-visible response and CTX working update.

## Normal Wake loop

```text
User input
↓
LM proxy
↓
Input-side EMO
- user_affect_estimate
- scene_state
- assistant_emotion_state target
↓
RelayCTX State Reflex
- reference detection
- active CTX reference resolution
- response_mode selection
- token budget checks
↓
RelayCTX Prompt Repack
- stable prefix
- SOUL / output policy
- selected CTX prompt hints
- selected EMO prompt hints
- latest user input
↓
Main LLM
- user_visible_response
- ctx_working_update
↓
RelayCTX Prompt Unpack
- split response text and ctx_working_update
- validate ctx_working_update
- commit working memory
↓
RelayCTX Output Segmenter
- conversational text
- quoted text
- code / command / JSON / YAML / table / URL / file path
↓
Return-side EMO
- text style / marker / TTS / Live2D output hints
↓
User / TTS / Avatar output
```

## MEM recall Wake loop

MEM recall is a two-step Wake path.

```text
User input
↓
CTX detects explicit or confirmed prior-memory need
↓
response_mode = pause_and_recall
↓
Main LLM short response
- "ちょっと思い出すね"
↓
Return-side EMO
- thinking / gentle / lower dominance output
↓
MEM Recall
↓
CTX MEM result repack
↓
Main LLM final answer + ctx_working_update
↓
CTX Prompt Unpack
↓
Return-side EMO
↓
Output
```

When `pause_and_recall` is active, RelayEMO should lower dominance/assertiveness slightly and shift toward a gentle thinking or recall posture.

## Reference resolution policy

RelayCTX should resolve pronoun-like references using active CTX first.

Examples:

- `それ`
- `これ`
- `前の`
- `この件`
- `続き`
- `同じ感じ`
- `いつもの`

Policy:

| State | Response mode |
| --- | --- |
| Active CTX has one clear referent | `answer_now` |
| Active CTX has multiple candidates | `ask_reference_confirmation` |
| Active CTX has no candidate | `ask_open_clarification` |
| User explicitly names prior memory | `pause_and_recall` or `recall_then_answer` |
| Reference is confirmed by user | MEM recall may run if needed |

RelayMEM should not be used to silently guess an ambiguous reference.

## Reference candidate scoring

The main LLM should not directly output “the next それ candidate” as a special field.

Instead, the LLM outputs general working-memory fields such as:

- `current_topic`
- `active_task`
- `active_question`
- `last_decision`
- `last_options`
- `referable_items`
- `unresolved_slots`
- `next_expected_action`

RelayCTX calculates reference candidates and confidence from those fields.

Suggested MVP scoring factors:

```text
confidence =
  recency_score
+ salience_score
+ schema_role_score
+ linguistic_match_score
+ uniqueness_bonus
- ambiguity_penalty
- stale_penalty
```

Suggested thresholds:

| Confidence | Behavior |
| --- | --- |
| >= 0.80 | auto-resolve from active CTX |
| 0.55 - 0.80 | ask candidate confirmation |
| < 0.55 | ask open clarification |

## CTX internal search after clarification

If a reference does not resolve from prompt hints, RelayCTX should not immediately call MEM.

Flow:

```text
ambiguous reference
↓
ask clarification
↓
user gives a short clarification phrase
↓
RelayCTX searches internal RAM working memory
↓
if one strong hit: answer_now
if multiple hits: ask_reference_confirmation
if no hit: ask_open_clarification or pause_and_recall if user explicitly requests memory
```

MVP search can use:

- string match
- alias match
- schema role weight
- recency
- salience
- status
- ambiguity penalty

This search is over RAM-side CTX internal working memory, not long-term MEM.

## CTX short-term memory vs MEM long-term memory

RelayCTX and RelayMEM differ not only by retention time, but also by epistemic role.

RelayCTX:

- Wake-time primary working memory
- subjective / situated / scene-conditioned
- may include EMO-tinted short-term interpretation
- used for immediate reference resolution and response mode selection
- kept in RAM and not directly persisted

RelayMEM:

- secondary memory reconstructed after RelayREF / RelaySLP and SOUL filtering
- more objective / durable / reusable
- should not directly store transient affect estimates
- should not directly store low-confidence Wake interpretation

Core distinction:

> RelayCTX is Wake-time primary working memory.  
> RelayMEM is SOUL-filtered secondary memory.

## ctx_working_update schema

Initial schema:

```yaml
ctx_working_update:
  current_topic: string | null
  active_task: string | null
  active_question: string | null
  last_decision:
    text: string
    status: candidate | agreed | rejected | question | pending
    confidence: float
  last_options:
    - label: string
      status: candidate | agreed | rejected | question | pending
  referable_items:
    - label: string
      kind: topic | decision | option | task | component | object | plan | configuration
      salience: float
  unresolved_slots:
    - string
  response_mode_hint: string | null
  next_expected_action: string | null
```

MVP can start with only:

- `current_topic`
- `active_question`
- `last_decision`
- `last_options`
- `referable_items`
- `unresolved_slots`
- `next_expected_action`

## ctx_prompt_hints

`ctx_prompt_hints` are generated by RelayCTX from internal working memory.

They should be much smaller than the internal state.

Example:

```yaml
ctx_prompt_hints:
  scene_state: design_talk
  response_mode: answer_now
  current_topic: RelayCTX Wake loop design
  last_decision: CTX working memory and model reinput context must be separated
  resolved_reference:
    term: それ
    target: CTX working memory and model reinput context separation
```

Rules:

- do not send null fields
- keep each field short
- keep referable items to a small top-k
- do not resend full `ctx_working_update`
- keep dynamic CTX hints after stable SOUL/output-policy blocks
- keep stable prefix byte-stable for backend prefix/KV cache reuse
- do not fill the prompt budget just because space is available

## Prompt repack budget policy

RelayCTX Prompt Repack is not a “fill to budget” process.

It should select only the context needed for the current `response_mode`.

Priority:

1. stable prefix / SOUL / output contract
2. Input-side EMO hint
3. response_mode
4. resolved_reference / ambiguous_reference
5. current_topic
6. active_task / active_question
7. last_decision
8. unresolved_slots
9. recent turn summary if needed
10. confirmed MEM recall result if needed

Dropped prompt hints are not automatically stored in MEM.

If information is not selected for the current prompt but may be important later, RelayCTX may emit a candidate signal for RelayREF. MEM persistence happens only after SOUL-filtered review.

## Core design statement

RelayCTX converts the main LLM's previous-turn meaning into CPU-side working memory.  
The next turn can then resolve references, choose a response mode, and repack a minimal prompt without forcing the model to reread the full conversation history.

This is the Wake-time core of RelayCTX.
