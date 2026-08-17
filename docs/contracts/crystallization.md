# Crystallization Contract

Crystallization is an **off-turn semantic synthesis process**. It is not a new truth authority and is not part of the ordinary synchronous cognitive turn.

## Current core

The current provider-agnostic orchestration is:

```text
Identity
+ Canonical State
+ bounded recent Events
+ optional prior memory/MEMORY.md
        |
        v
one off-turn Crystallizer.generate(...)
        |
        v
CrystallizationOutput
  ├─ memory_markdown
  └─ StateCandidate[]
        |
        +--> memory/MEMORY.md
        |
        +--> existing Validator / State engine
                    |
                    v
             Canonical State
```

`memory/MEMORY.md` is portable readable synthesis. `memory/state.json` remains the accepted current machine understanding, and `memory/events.jsonl` remains occurrence/provenance history.

## CrystallizationInput

The current input contains:

- authoritative character Identity;
- current Canonical State;
- a bounded recent Event snapshot selected by count;
- optional prior `memory/MEMORY.md` content.

`max_events` defaults to 100, may be set to zero, and must not be negative. The bounded snapshot constrains what is sent to the crystallizer; it does not delete or rewrite older persisted Events.

State records may refer to Event provenance older than the recent snapshot. Candidate validation therefore checks source IDs against the full persisted Event Journal, not only the bounded crystallizer Event window.

## CrystallizationOutput

The current output shape is logically:

```text
memory_markdown: non-empty Markdown
state_candidates: StateCandidate[]
```

The Markdown body is the readable synthesis produced by the crystallizer. Provenance should be represented in the Markdown when the synthesis depends on specific Events or accepted State, but readable Markdown does not gain Canonical State authority merely by mentioning a source.

`StateCandidate[]` uses the existing RelayLM StateCandidate contract. The crystallizer has no privileged mutation path.

## Governed State write-back

Candidate write-back follows the existing deterministic Validator/State engine:

- candidate source IDs must resolve to persisted Events;
- user State still requires user-authored provenance;
- unsupported classes/keys/value forms are rejected by existing rules;
- equal accepted values remain noops;
- accepted changes persist through the normal Canonical State writer.

Crystallization does not reinterpret Validator rejection as success and does not promote Markdown prose into State automatically.

## Markdown persistence

`memory/MEMORY.md` is optional. Missing readable memory is represented as no prior crystallized memory.

Writes use temporary-file replacement at the filesystem boundary. If the generated Markdown is byte-for-byte unchanged from the existing file, RelayLM does not rewrite it and reports `memory_changed = false`.

This stability rule avoids needless Markdown churn on unchanged crystallization output. It does not claim semantic equivalence detection between differently worded prose.

## Ordinary-turn boundary

Crystallization is explicitly off-turn. Adding a Crystallizer protocol does not change the ordinary-turn invariant:

> one ordinary user turn targets exactly one cognitive LLM generation.

A future crystallizer provider may itself use an LLM, but that invocation is a separate crystallization operation, not a hidden second call inside ordinary conversation.

## Deferred work

Still owned by #1260:

- an actual OpenAI-compatible / local-model crystallizer adapter and prompt/schema contract;
- richer provenance conventions inside Markdown;
- `memory/notes/*.md` splitting, linking, and wiki organization;
- autonomous scheduling or background crystallization policy;
- manual/external Markdown import and governed write-back;
- richer idempotence/semantic churn evaluation.

Retrieval of crystallized memory into ordinary cognitive Context remains owned by #1267.
