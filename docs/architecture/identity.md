# Identity

RelayLM persists character identity outside the language model.

## Identity Core

The portable, human-authored representation is `SOUL.md`.

`SOUL.md` describes who the character is: values, enduring commitments, character-defining traits, and other normative anchors intended to survive model replacement and session boundaries.

Normal runtime cognition must not autonomously rewrite `SOUL.md`.

## Separation

```text
SOUL.md
  = who I am

Canonical State
  = what I currently understand

Event Journal
  = what happened
```

Identity is not a special State class and must not be silently mutated through StateCandidate output.

Provider models, model names, endpoints, API keys, GPU choices, and host-specific runtime configuration are not Identity.
