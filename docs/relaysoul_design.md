# RelaySOUL Design

RelaySOUL is the working name for RelayLM's persona source calibration layer.

RelayLM is the runtime proxy that compiles persona, memory, scene state, recent turns, and retrieved context into a token-budgeted prompt for a backend model. RelaySOUL sits one step upstream: it helps create, calibrate, version, and roll back the persona source files that RelayLM later compiles.

## Definition

RelaySOUL is a human-in-the-loop persona source optimization layer for RelayLM.

It collects natural-language preference examples from the user, asks a model to convert those preferences into patch candidates for persona source files, versions approved persona revisions, and lets RelayLM test the updated persona until the perceived persona converges.

RelaySOUL does not train model weights. It optimizes prompt-space persona source artifacts.

## Relationship to RelayLM

```text
RelaySOUL
  -> generates and calibrates persona source files
  -> versions approved persona revisions
  -> produces stable persona source artifacts

RelayLM
  -> compiles those artifacts into tagged context
  -> sends the compiled prompt to a backend model
  -> observes runtime diagnostics and user feedback
```

RelaySOUL should keep the same persona file boundaries used by RelayLM:

- `SOUL.md`: persona core, values, worldview, and durable identity.
- `OUTPUT_POLICY.md`: expression mode, tone, emotional manifestation, TTS-friendly style, and response style.
- `RELATIONSHIP_ANCHOR.md`: slow-changing relationship state between the character and the user/viewer.
- `STABLE_MEMORY_SUMMARY.md`: durable memory summary and long-term context.
- `SCENE_STATE.md`: current situation, topic, mood, and temporary conversational context.

`SCENE_STATE.md` is the preferred name for dynamic situation state. `room_id` identifies where the conversation is hosted, such as a channel, room, stream, or frontend conversation space. `scene_id` and `SCENE_STATE.md` identify what situation the conversation is in.

## Core idea

RelaySOUL should expose persona editing as natural example calibration.

The user does not need to tune numeric sliders such as `warmth=0.65`. Instead, RelaySOUL presents natural-language response samples, lets the user pick what feels right, and then asks a model to translate those preferences into minimal persona file patch candidates.

```text
user selects preferred natural-language examples
  -> RelaySOUL builds a patch-generation prompt
  -> model proposes file-specific patch candidates
  -> user reviews and approves
  -> RelaySOUL creates a new persona revision
  -> RelayLM tests the updated persona in conversation
  -> user repeats until the perceived persona converges
```

This makes RelaySOUL look like a character creation loop, but its implementation target is persona source optimization.

## Natural example calibration

RelaySOUL should calibrate persona traits through concrete conversation examples.

Example question:

```text
When the user is stuck, which response feels closer to the intended character?

A. "うん、それは少し詰まりやすいところだね。一緒に切り分けよう。"
B. "問題を整理します。原因は3点あります。"
C. "またそこか〜。でも今回は前より原因が見えてると思うよ。"
D. "失敗ではありません。次の改善点は3つあります。"
```

A user's preference is more informative than a raw numeric parameter. RelaySOUL may store numeric hints internally, but the canonical patch target should remain natural-language persona source files.

Preferred and rejected examples should be stored with reason labels when available:

```json
{
  "calibration_id": "calib_004",
  "prompt_kind": "stuck_user_response",
  "preferred_response": "うん、それは少し詰まりやすいところだね。一緒に切り分けよう。",
  "rejected_response": "問題を整理します。原因は3点あります。",
  "feedback_labels": ["warm", "not_businesslike", "still_useful"]
}
```

## Patch generation workflow

After collecting preference examples, RelaySOUL should ask a model to propose minimal patches.

The patch-generation prompt should include:

- current `SOUL.md`
- current `OUTPUT_POLICY.md`
- current `RELATIONSHIP_ANCHOR.md`
- optional `STABLE_MEMORY_SUMMARY.md`
- optional `SCENE_STATE.md`
- preferred examples
- rejected examples
- feedback labels and freeform notes
- current mode

The model should be instructed to:

- prefer `OUTPUT_POLICY.md` for tone, style, warmth, verbosity, memory disclosure, and response shape
- prefer `RELATIONSHIP_ANCHOR.md` for distance, familiarity, trust, and user-specific relational expectations
- prefer `SOUL.md` only for durable persona core, values, worldview, identity, and invariants
- prefer `SCENE_STATE.md` or runtime overlay for temporary mood or situation changes
- propose no change when the current files already explain the preference
- explain why each patch belongs to the chosen file
- avoid full rewrites unless explicitly requested

Example model output:

```text
Patch target: OUTPUT_POLICY.md
Reason: The user preferred a warmer technical response, but the character core does not need to change.
Patch:
- Before technical troubleshooting, add one short acknowledgement of the user's situation.
- Keep the analysis concise and avoid long reassurance.
- Avoid purely businesslike openings such as "問題を整理します" when the user sounds frustrated.

Patch target: RELATIONSHIP_ANCHOR.md
Reason: The preference indicates a stable relationship expectation.
Patch:
- The user prefers calm technical help with a short, warm acknowledgement before analysis.

Patch target: SOUL.md
Reason: Not needed. This is an expression-policy change, not a persona-core change.
```

## Update modes

RelaySOUL should separate persona mutation from stable persona execution.

### character_creation

Character creation mode is a sandbox for persona mutation.

Purpose:

- create or heavily reshape a persona
- converge quickly from user preferences
- allow aggressive `SOUL.md` patching
- allow broad `OUTPUT_POLICY.md` and `RELATIONSHIP_ANCHOR.md` changes

Rules:

- revision snapshot is required before applying changes
- rollback must be available
- user approval is required before applying a patch
- patch reasons and source feedback should be preserved
- `SOUL.md` may be updated aggressively because the user is explicitly editing the persona

### calibration

Calibration mode refines an existing persona.

Purpose:

- tune response style
- tune relationship distance
- tune memory disclosure
- reduce user irritation
- increase conversation comfort

Rules:

- prefer `OUTPUT_POLICY.md` and `RELATIONSHIP_ANCHOR.md`
- produce `SOUL.md` patch candidates only when style/relationship changes cannot explain the preference
- use natural-language samples and user preference labels as primary evidence

### normal_chat

Normal chat mode is the stable runtime for persona execution.

Purpose:

- run the current persona consistently
- preserve conversation flow
- avoid surprise persona mutation

Rules:

- do not directly rewrite `SOUL.md`
- do not silently apply core persona changes
- use low-rate, candidate-based updates for durable memory and relationship state
- route explicit core-persona correction requests to `character_creation` or `calibration`
- latent core-persona correction signals may trigger a push-style proposal, but patch generation should only run after user permission

Example push-style proposal:

```text
This feedback may require a persona-core adjustment rather than a tone-only change.
Do you want to open character creation mode and review a SOUL.md patch candidate?
```

## Update target selection

RelaySOUL should classify feedback before patching.

| Feedback type | Preferred target |
| --- | --- |
| response is too cold, too verbose, too businesslike, too cute, or too direct | `OUTPUT_POLICY.md` |
| memory recall feels creepy, too specific, or too vague | `OUTPUT_POLICY.md` or memory disclosure policy |
| distance, familiarity, trust, or user-specific expectations changed | `RELATIONSHIP_ANCHOR.md` |
| durable user or character facts changed | `STABLE_MEMORY_SUMMARY.md` |
| current mood, event, situation, or temporary direction changed | `SCENE_STATE.md` or runtime overlay |
| core identity, values, worldview, or durable persona invariants changed | `SOUL.md` |

`SOUL.md` should not become a dumping ground for style changes. `OUTPUT_POLICY.md` should not become a hidden persona core. `RELATIONSHIP_ANCHOR.md` should not accumulate general values that belong in `SOUL.md`.

## Persona revision and rollback

Persona source files should be versioned as profile-level revisions, not just individual file edits.

Suggested metadata:

```json
{
  "revision_id": "0017",
  "parent_revision_id": "0016",
  "mode": "character_creation",
  "changed_files": ["SOUL.md", "OUTPUT_POLICY.md"],
  "change_reason": "User preferred warmer but still technical responses.",
  "feedback_ids": ["calib_004"],
  "patch_prompt_id": "patch_prompt_0017",
  "model_response_id": "patch_model_response_0017",
  "applied_at": "2026-05-25T00:00:00+09:00",
  "applied_by": "user",
  "rollback_available": true
}
```

Revision snapshots enable aggressive exploration in `character_creation` while preserving stability in `normal_chat`.

## Persona renderer dependency

The backend model is a persona renderer, not just an execution target.

The same persona source files may produce different perceived personas across models, tokenizers, decoding policies, and context layouts. RelaySOUL should therefore treat the user-facing output as the final evidence, not the source text alone.

```text
SOUL.md / OUTPUT_POLICY.md / RELATIONSHIP_ANCHOR.md
  -> RelayLM tagged context
  -> backend model as persona renderer
  -> Persona Anchor KV
  -> generated response
  -> perceived persona
  -> user preference feedback
```

A future Persona Renderer Matrix may record which backend models are better at particular persona styles, languages, memory disclosure behavior, and verbosity control.

## Safety and responsibility boundary

RelaySOUL should not present unsafe or adult-oriented persona generation as an official product direction.

For an open-source proxy, the practical boundary is:

- official presets should be safe and general-purpose
- custom backend models are user-controlled
- custom local persona files are user-controlled
- forks and modified code are outside the official support boundary
- RelaySOUL should not distribute unsafe presets or unsafe model recommendations

RelaySOUL may provide policy files and warnings, but it should not pretend to fully control arbitrary user-provided backend models.

## MVP scope

Initial RelaySOUL work should be docs-first and dry-run-first.

Suggested MVP:

1. document the persona source calibration loop
2. add example calibration prompts and outputs
3. define revision metadata schema
4. build a dry-run script that reads persona files and feedback examples
5. emit patch candidates without applying them
6. add explicit apply/rollback only after the dry-run path is stable

No runtime RelayLM behavior is required for the initial design document.

## Future work

- UI for natural example calibration
- LLM judge-assisted feedback classification
- Persona Renderer Matrix
- stable-prefix hash comparison across persona revisions
- revision diff viewer
- safe sharing format for persona source packages
- custom memory-system reconciliation events
- import from character cards into RelaySOUL source files
- export to RelayLM-compatible persona packages